import json, os, sys
from dotenv import load_dotenv
from openai import OpenAI
from app.tools.registry import registry

load_dotenv()  # nearest .env, searching up from this file

client = OpenAI(
    base_url=os.environ.get("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key=os.environ["NVIDIA_API_KEY"],
    max_retries=6,  # the shared hosted NIM returns 429 under eval load; SDK backs off exponentially
)
MODEL = os.environ.get("AGENT_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b")
MAX_STEPS = int(os.environ.get("MAX_STEPS", "8"))
SYSTEM = (
    "You are a financial-crime investigation agent. Get every fact and number from a tool; "
    "never guess. When you can answer, reply with the answer and no tool call."
)
SYSTEM = os.environ.get("AGENT_SYSTEM", SYSTEM)  # candidate prompt (v2) for evals


def run(question: str, schemas=None, call=None, verbose=True):
    schemas = schemas or registry.schemas()
    call = call or registry.call
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question},
    ]
    used = []
    for step in range(1, MAX_STEPS + 1):
        msg = (
            client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=schemas,
                tool_choice="auto",
                temperature=1.0,
                top_p=0.95,
            )
            .choices[0]
            .message
        )
        messages.append(msg)
        if not msg.tool_calls:
            return {
                "answer": msg.content,
                "steps": step,
                "tools_used": used,
                "stopped": "answer",
            }
        for tc in msg.tool_calls:
            used.append(tc.function.name)
            try:
                obs = call(tc.function.name, tc.function.arguments)
            except Exception as e:  # ValidationError, unknown tool, tool error
                obs = f"ERROR: {type(e).__name__}: {e}"
            if verbose:
                print(
                    f"[{step}] {tc.function.name}({tc.function.arguments}) -> {obs[:160]}"
                )
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": obs})
    return {
        "answer": None,
        "steps": MAX_STEPS,
        "tools_used": used,
        "stopped": "max_steps",
    }


if __name__ == "__main__":
    print(json.dumps(run(" ".join(sys.argv[1:])), indent=2))
