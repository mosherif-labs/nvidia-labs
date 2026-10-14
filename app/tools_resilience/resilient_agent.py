import json, os, time
from datetime import datetime, timezone
import openai

from app.tools import agent  # Day 4's loop, client and registry
from app.tools.registry import registry
from app.tools_resilience.resilience import (
    DEAD_LETTERS,
    CircuitBreaker,
    chaos,
    resilient,
)

FALLBACK_MODEL = os.environ.get(
    "FALLBACK_MODEL"
)  # a smaller tool-calling model from /v1/models
RESILIENT = os.environ.get("RESILIENT", "1") == "1"

# Wrap every tool: injected chaos inside, retries + one breaker per tool outside.
for name, (fn, model) in list(registry.tools.items()):
    wrapped = chaos(fn)
    registry.tools[name] = (
        resilient(wrapped, CircuitBreaker()) if RESILIENT else wrapped,
        model,
    )

# We own the retries (the SDK's default 2 would multiply ours) and fail in 60s, not 10 min.
agent.client = agent.client.with_options(max_retries=0, timeout=60.0)
_create = agent.client.chat.completions.create
state = {"degraded": False}


class ModelUnavailable(Exception): ...


def create_with_fallback(**kw):
    """Main model first; after 2 timeouts / rate limits / 5xx, the fallback model, marked degraded."""
    for attempt in range(2):
        try:
            return _create(**kw)
        except (
            openai.APITimeoutError,
            openai.RateLimitError,
            openai.InternalServerError,
        ):
            time.sleep(2**attempt)
    if not FALLBACK_MODEL:
        raise ModelUnavailable("main model unavailable and no FALLBACK_MODEL set")
    state["degraded"] = True
    try:
        return _create(**{**kw, "model": FALLBACK_MODEL})
    except openai.OpenAIError as e:  # fallback down too: stop and hand the case over
        raise ModelUnavailable(f"fallback failed: {type(e).__name__}") from e


agent.client.chat.completions.create = create_with_fallback


def investigate(question: str, case_id: str):
    state["degraded"] = False  # per case: one fallback must not mark every later case
    before = len(DEAD_LETTERS)
    try:
        r = agent.run(question, verbose=False)
    except ModelUnavailable as e:
        r = {"answer": None, "steps": 0, "tools_used": [], "stopped": f"model: {e}"}
    r["degraded"] = state["degraded"]
    # An explicit signal from the tool wrapper, not a word found in the answer
    r["tool_failures"] = len(DEAD_LETTERS) - before
    if r["stopped"] != "answer" or r["tool_failures"]:
        with open(
            "needs_human.jsonl", "a"
        ) as f:  # escalation: hand the case over WITH context
            f.write(
                json.dumps(
                    {
                        "case_id": case_id,
                        "at": datetime.now(timezone.utc).isoformat(),
                        "question": question,
                        "draft_answer": r["answer"],
                        "steps": r["steps"],
                        "tools_used": r["tools_used"],
                        "reason": r["stopped"],
                        "tool_failures": r["tool_failures"],
                        "degraded": r["degraded"],
                        "dead_letters": DEAD_LETTERS[before:],  # which calls failed, with args
                    }
                )
                + "\n"
            )
        r["escalated"] = True
    return r
