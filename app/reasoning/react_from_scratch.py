"""NCP-AAI W1 D6 (AAI Day 2): ReAct from scratch, no framework.

Source: ReAct (arXiv 2210.03629) section 2. Native tool calling replaces the text parsing used in the paper.
"""

import json, os, sys
from dotenv import load_dotenv
from openai import OpenAI
from app.data import TOOLS, SCHEMAS

load_dotenv()  # nearest .env, searching up from this file

client = OpenAI(
    base_url=os.environ.get("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key=os.environ["NVIDIA_API_KEY"],
)
MODEL = os.environ.get("AGENT_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b")
MAX_STEPS = int(os.environ.get("MAX_STEPS", "8"))

SYSTEM = (
    "You are a financial-crime investigation agent. Before each action, write one short "
    "thought about what you know and what you still need. Get every number from a tool; "
    "never guess. When you can answer, reply with the answer and no tool call."
)


def run(question: str):
    """ReAct: THINK (model text) -> ACT (tool call) -> OBSERVE (tool result), repeat.

    The loop has exactly TWO exits: a final answer, or MAX_STEPS.
    Return shape: {"answer": str|None, "steps": int, "stopped": "answer"|"max_steps"}
    """
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question},
    ]
    for step in range(1, MAX_STEPS + 1):
        # 1. THINK: one LLM call; the model sees the whole history plus the tool schemas.
        msg = (
            client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=SCHEMAS,
                tool_choice="auto",
                temperature=1.0,
                top_p=0.95,
            )
            .choices[0]
            .message
        )
        messages.append(msg)  # the model must see its own tool calls on the next turn
        # Reasoning models (e.g. Nemotron 3) put their thought in a separate field and leave
        # `content` empty when they call a tool; show it so the THINK step is visible.
        extra = getattr(msg, "model_extra", None) or {}
        thought = (
            extra.get("reasoning_content") or extra.get("reasoning") or msg.content
        )
        if thought:
            print(f"[{step}] THINK   {thought.strip()[:1000]}")

        # 2. EXIT #1: no tool calls means the model is answering.
        if not msg.tool_calls:
            return {"answer": msg.content, "steps": step, "stopped": "answer"}

        # 3. ACT + OBSERVE: run every requested tool locally, feed each result back.
        for call in msg.tool_calls:
            try:
                args = json.loads(call.function.arguments)
                obs = TOOLS[call.function.name](**args)
            except Exception as e:  # bad args, unknown tool, tool error: show the model
                obs = f"ERROR: {type(e).__name__}: {e}"
            print(f"[{step}] ACT     {call.function.name}({call.function.arguments})")
            print(f"[{step}] OBSERVE {obs[:200]}")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": obs})

    # 4. EXIT #2: the budget ran out. Never loop forever.
    return {"answer": None, "steps": MAX_STEPS, "stopped": "max_steps"}


if __name__ == "__main__":
    print(json.dumps(run(" ".join(sys.argv[1:])), indent=2))
