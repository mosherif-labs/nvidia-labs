import os, sqlite3, sys
from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.sqlite import SqliteSaver

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "tools"), str(HERE.parent / "security")]
from app.team.team import team  # Day 18's team, as a subgraph
from app.tools.registry import registry  # Day 4's flag_alert (idempotent)
from app.security.audit import record  # Day 7's hash-chained audit log

KILL_SWITCH = HERE / "KILL_SWITCH"  # touch this file and no action executes


class Case(TypedDict, total=False):
    case_id: str
    alert: str
    route: list[str]
    narrative: str
    pending_action: dict
    approved_by: str
    outcome: str


def investigate(s: Case):
    out = team.invoke(
        {
            "messages": [("user", s["alert"])],
            "turns": 0,
            "route_log": [],
            "stopped_by": "",
        }
    )
    return {"route": out["route_log"], "narrative": out["messages"][-1].content}


def propose(s: Case) -> Command[Literal["approval_gate", "__end__"]]:
    if "escalat" in s["narrative"].lower():  # the narrative recommends escalation
        action = {
            "tool": "flag_alert",
            "args": {
                "alert_id": s["case_id"].removeprefix("case-"),
                "reason": "escalated after review",
                "idempotency_key": s["case_id"],
            },
        }
        return Command(goto="approval_gate", update={"pending_action": action})
    return Command(goto=END, update={"outcome": "closed: no action proposed"})


def approval_gate(s: Case) -> Command[Literal["execute_action", "__end__"]]:
    # No side effects before interrupt(): on resume this node runs again from the top.
    decision = interrupt(
        {
            "case_id": s["case_id"],
            "action": s["pending_action"],
            "route": s["route"],
            "narrative": s["narrative"],
        }
    )
    if decision.get("approved"):
        return Command(
            goto="execute_action", update={"approved_by": decision["reviewer"]}
        )
    record(
        decision.get("reviewer", "?"),
        s["pending_action"]["tool"],
        s["case_id"],
        "rejected",
    )
    return Command(
        goto=END,
        update={
            "outcome": f"rejected by {decision.get('reviewer', '?')}: "
            f"{decision.get('reason', '')}"
        },
    )


def execute_action(s: Case):
    a = s["pending_action"]
    if KILL_SWITCH.exists():
        record(s["approved_by"], a["tool"], s["case_id"], "blocked: kill switch")
        return {"outcome": "blocked by the kill switch"}
    result = registry.call(a["tool"], __import__("json").dumps(a["args"]))
    record(s["approved_by"], a["tool"], s["case_id"], f"executed: {result}")
    return {"outcome": f"{result} (approved by {s['approved_by']})"}


g = StateGraph(Case)
for name, fn in (
    ("investigate", investigate),
    ("propose", propose),
    ("approval_gate", approval_gate),
    ("execute_action", execute_action),
):
    g.add_node(name, fn)
g.add_edge(START, "investigate")
g.add_edge("investigate", "propose")
g.add_edge("execute_action", END)
app = g.compile(
    checkpointer=SqliteSaver(
        sqlite3.connect(str(HERE / "approvals.db"), check_same_thread=False)
    )
)


def cfg(case_id):
    return {"configurable": {"thread_id": case_id}}


def start(case_id: str, alert: str):
    return app.invoke({"case_id": case_id, "alert": alert}, cfg(case_id))


def decide(case_id: str, approved: bool, reviewer: str, reason: str = ""):
    return app.invoke(
        Command(resume={"approved": approved, "reviewer": reviewer, "reason": reason}),
        cfg(case_id),
    )


def waiting(case_id: str):
    """The interrupt payload if the case is paused at the gate, else None."""
    snap = app.get_state(cfg(case_id))
    return (
        snap.tasks[0].interrupts[0].value
        if snap.tasks and snap.tasks[0].interrupts
        else None
    )


if __name__ == "__main__":
    # start:  python approval.py case-A-1001 start "Alert A-1001: three cash deposits in 7 days."
    # decide: python approval.py case-A-1001 approve|reject <reviewer> [reason]
    case_id, verb = sys.argv[1], sys.argv[2]
    out = (
        start(case_id, " ".join(sys.argv[3:]))
        if verb == "start"
        else decide(case_id, verb == "approve", sys.argv[3], " ".join(sys.argv[4:]))
    )
    print(
        "WAITING FOR APPROVAL:", out["__interrupt__"][0].value["action"]
    ) if "__interrupt__" in out else print(out.get("outcome"))
