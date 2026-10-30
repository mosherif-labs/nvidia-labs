import operator, os, sqlite3, sys
from pathlib import Path
from typing import Annotated
from typing_extensions import TypedDict
from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver

from app.tools import registry as reg  # Day 4's tools

load_dotenv()  # nearest .env, searching up from this file


@tool
def get_alert(alert_id: str) -> str:
    """Fetch ONE transaction-monitoring alert by id (customer, pattern, amounts, window). Read-only."""
    return reg.get_alert(alert_id)


@tool
def search_policy(query: str) -> str:
    """Search internal AML policies by keywords; returns the 2 best matches with policy ids."""
    return reg.search_policy(query)


@tool
def calculator(expression: str) -> str:
    """Exact arithmetic on numbers only. Use for every sum or comparison of amounts."""
    return reg.calculator(expression)


TOOLS = [get_alert, search_policy, calculator]
MAX_STEPS = int(os.environ.get("MAX_STEPS", "8"))
base_llm = ChatOpenAI(
    model=os.environ.get("AGENT_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b"),
    base_url=os.environ.get("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key=os.environ["NVIDIA_API_KEY"],
    temperature=1.0,
    top_p=0.95,
)
llm = base_llm.bind_tools(TOOLS)


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    case_id: str
    steps: Annotated[int, operator.add]


def agent(state: State):
    if os.environ.get("CRASH_AT_STEP") == str(state["steps"] + 1):
        os._exit(1)  # simulate a hard crash (no cleanup)
    system = SystemMessage(  # prompt assembled from state on every call
        f"You investigate case {state['case_id']}. This is step {state['steps'] + 1} of {MAX_STEPS}. "
        "Get every fact and number from a tool. When you can answer, reply without a tool call."
    )
    return {"messages": [llm.invoke([system] + state["messages"])], "steps": 1}


def route(state: State):
    # Day 2's two exits: the step budget is spent, or the model answered (no tool_calls)
    if state["steps"] >= MAX_STEPS or not state["messages"][-1].tool_calls:
        return END
    return "tools"


def build():
    g = StateGraph(State)
    g.add_node("agent", agent)
    g.add_node("tools", ToolNode(TOOLS))
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", route, ["tools", END])
    g.add_edge("tools", "agent")
    return g


DB = str(Path(__file__).with_name("checkpoints.db"))
checkpointer = SqliteSaver(sqlite3.connect(DB, check_same_thread=False))
graph = build().compile(checkpointer=checkpointer)

if __name__ == "__main__":
    thread, question = sys.argv[1], " ".join(sys.argv[2:])
    config = {"configurable": {"thread_id": thread}}
    inp = (
        None
        if question == "--resume"
        else {"messages": [("user", question)], "case_id": thread, "steps": 0}
    )
    # "sync": each checkpoint is on disk before the next step starts (default is "async")
    out = graph.invoke(inp, config, durability="sync")
    print(out["messages"][-1].content, f"\n[steps={out['steps']}]")
