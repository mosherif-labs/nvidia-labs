import json, sqlite3, sys
from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.sqlite import SqliteSaver
from app.langgraph.graph import base_llm, build


class Plan(BaseModel):
    steps: list[str] = Field(
        description="Ordered steps, each doable with one or two tool calls"
    )


class S(TypedDict, total=False):
    question: str
    plan: list[str]
    findings: list[str]
    answer: str
    reviewer: str


planner = base_llm.with_structured_output(Plan, method="function_calling")
executor = build().compile()  # the ReAct graph, as a subroutine


def plan(s: S):
    return {
        "plan": planner.invoke(
            f"Make a short step-by-step plan to answer: {s['question']}"
        ).steps
    }


def approve(s: S) -> Command[Literal["execute", "__end__"]]:
    # Nothing before interrupt() has side effects: on resume this node runs again from the top.
    decision = interrupt({"question": s["question"], "plan": s["plan"]})
    if decision.get("approved"):
        return Command(
            goto="execute", update={"reviewer": decision.get("reviewer", "?")}
        )
    return Command(
        goto=END,
        update={
            "answer": f"REJECTED by {decision.get('reviewer', '?')}: nothing executed"
        },
    )


def execute(s: S):
    findings = []
    for step in s["plan"]:
        out = executor.invoke(
            {
                "messages": [("user", f"{step}\nFindings so far: {findings}")],
                "case_id": "exec",
                "steps": 0,
            }
        )
        findings.append(out["messages"][-1].content)
    answer = base_llm.invoke(
        f"Question: {s['question']}\nFindings: {findings}\nAnswer in two lines."
    ).content
    return {"findings": findings, "answer": answer}


g = StateGraph(S)
g.add_node("plan", plan)
g.add_node("approve", approve)
g.add_node("execute", execute)
g.add_edge(START, "plan")
g.add_edge("plan", "approve")
g.add_edge("execute", END)
DB = str(Path(__file__).with_name("approvals.db"))
app = g.compile(checkpointer=SqliteSaver(sqlite3.connect(DB, check_same_thread=False)))

if __name__ == "__main__":
    # start:   python approval_graph.py case-9 start "<question>"
    # decide:  python approval_graph.py case-9 approve|reject <reviewer>
    thread, verb = sys.argv[1], sys.argv[2]
    config = {"configurable": {"thread_id": thread}}
    if verb == "start":
        out = app.invoke({"question": " ".join(sys.argv[3:])}, config)
    else:
        out = app.invoke(
            Command(resume={"approved": verb == "approve", "reviewer": sys.argv[3]}),
            config,
        )
    if "__interrupt__" in out:
        print(
            "WAITING FOR APPROVAL:", json.dumps(out["__interrupt__"][0].value, indent=2)
        )
    else:
        print(out.get("answer"))
