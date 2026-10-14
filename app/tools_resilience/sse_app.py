import json
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from app.tools_resilience.resilient_agent import agent, registry

app = FastAPI()


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.get("/investigate")
def investigate(case_id: str, q: str):
    def events():  # the Day 4 loop, yielding as it goes
        messages = [
            {"role": "system", "content": agent.SYSTEM},
            {"role": "user", "content": q},
        ]
        for step in range(1, agent.MAX_STEPS + 1):
            msg = (
                agent.client.chat.completions.create(
                    model=agent.MODEL,
                    messages=messages,
                    tools=registry.schemas(),
                    tool_choice="auto",
                    temperature=1.0,
                    top_p=0.95,
                )
                .choices[0]
                .message
            )
            messages.append(msg)
            if msg.content and msg.tool_calls:
                yield sse("thought", {"step": step, "text": msg.content[:500]})
            if not msg.tool_calls:
                yield sse("answer", {"text": msg.content})
                break
            for tc in msg.tool_calls:
                yield sse(
                    "tool_start",
                    {
                        "step": step,
                        "name": tc.function.name,
                        "args": tc.function.arguments,
                    },
                )
                try:
                    obs = registry.call(tc.function.name, tc.function.arguments)
                except Exception as e:
                    obs = f"ERROR: {type(e).__name__}: {e}"
                yield sse(
                    "tool_end",
                    {"step": step, "name": tc.function.name, "result": obs[:300]},
                )
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": obs})
        yield sse("done", {"case_id": case_id})

    return StreamingResponse(events(), media_type="text/event-stream")
