import operator, os, re
from typing import Annotated, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, AnyMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import Command

from app.langgraph.graph import base_llm, build  # Day 12's model client and ReAct graph
from app.tools import registry as reg  # Day 4's tools (graph.py put them on the path)

MAX_TURNS = int(os.environ.get("MAX_TURNS", "6"))
Worker = Literal["triage", "investigator", "report_writer"]


class Route(BaseModel):
    next: Literal["triage", "investigator", "report_writer", "FINISH"]
    reason: str = Field(description="One short sentence")


class Triage(BaseModel):
    alert_found: bool = Field(
        description="False if the alert data is missing or an error"
    )
    typology: str = Field(
        description="e.g. structuring, high-risk wires, payroll, unknown"
    )
    worth_investigating: bool
    reason: str


class Team(TypedDict):
    messages: Annotated[
        list[AnyMessage], add_messages
    ]  # shared transcript: one named message per worker turn
    turns: int
    route_log: Annotated[list[str], operator.add]
    stopped_by: str


RULES = """You supervise an AML investigation team. Workers:
- triage: classifies the alert and says whether it is worth investigating. Always first.
- investigator: gathers facts with tools (alert data, policies, sums). Only if triage says it is worth investigating.
- report_writer: writes the case narrative. Last: after investigator, or straight after triage for a false positive.
Reply FINISH when report_writer has written the narrative, or when triage found no alert data.
Never choose the same worker twice in a row."""

router = base_llm.with_structured_output(Route, method="function_calling")
triager = base_llm.with_structured_output(Triage, method="function_calling")
investigator_graph = build().compile()  # a worker is itself a ReAct agent


def transcript(s: Team) -> str:
    return "\n".join(f"[{m.name or m.type}] {m.content}" for m in s["messages"])


def supervisor(
    s: Team,
) -> Command[Literal["triage", "investigator", "report_writer", "__end__"]]:
    turns, log = (
        s.get("turns", 0),
        s.get("route_log", []),
    )  # .get: NAT's wrapper passes only messages
    if turns >= MAX_TURNS:  # guard 1: turn cap
        return Command(goto=END, update={"stopped_by": "MAX_TURNS"})
    d = router.invoke([("system", RULES), ("user", transcript(s))])
    if d.next == "FINISH":
        return Command(goto=END, update={"stopped_by": "FINISH"})
    if log and d.next == log[-1]:  # guard 2: no progress
        return Command(goto=END, update={"stopped_by": "NO_PROGRESS"})
    return Command(goto=d.next, update={"turns": turns + 1, "route_log": [d.next]})


def say(name: str, text: str) -> Command[Literal["supervisor"]]:
    return Command(goto="supervisor", update={"messages": [AIMessage(text, name=name)]})


def triage(s: Team):
    alert = s["messages"][0].content
    ids = re.findall(r"A-\d{4}", alert)
    data = reg.get_alert(ids[0]) if ids else '{"error": "no alert id in the text"}'
    t = triager.invoke(f"Alert: {alert}\nAlert data: {data}\nClassify it.")
    return say("triage", t.model_dump_json())


def investigator(s: Team):
    task = (
        f"Investigate: {s['messages'][0].content}\nTriage said: {s['messages'][-1].content}\n"
        "Get the facts, total the amounts, and name the policy that applies."
    )
    out = investigator_graph.invoke(
        {"messages": [("user", task)], "case_id": "team", "steps": 0}
    )
    return say(
        "investigator", out["messages"][-1].content
    )  # only the final answer goes back


def report_writer(s: Team):
    text = base_llm.invoke(
        [
            (
                "system",
                "Write a 4-line case narrative: alert, facts, policy, recommended action. "
                "Use only facts from the transcript.",
            ),
            ("user", transcript(s)),
        ]
    ).content
    return say("report_writer", text)


g = StateGraph(Team)
g.add_node("supervisor", supervisor)
for name, fn in (
    ("triage", triage),
    ("investigator", investigator),
    ("report_writer", report_writer),
):
    g.add_node(name, fn)
g.add_edge(START, "supervisor")
team = g.compile()
