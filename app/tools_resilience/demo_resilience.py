"""Self-check for resilience.py: 3 stories, bad arguments, an outage. No API calls.

Run from this folder: uv run --with tenacity --with pydantic python demo_resilience.py
"""

import os
import tempfile

from pydantic import ValidationError

from app.tools.registry import ToolRegistry
from app.tools_resilience.resilience import (
    DEAD_LETTERS,
    CircuitBreaker,
    TransientToolError,
    resilient,
)

script: list[bool] = []  # True = this request to the tool fails with a 503
hits = 0  # requests that actually reached the tool
DLQ = os.path.join(tempfile.gettempdir(), "demo_dead_letters.jsonl")


def get_alert(alert_id: str) -> str:
    """Fake tool: fails when the script says so."""
    global hits
    hits += 1
    if script and script.pop(0):
        raise TransientToolError("get_alert: injected 503")
    return f"alert {alert_id}: OK"


def story(title, fails, args='{"alert_id": "A-1001"}', calls=1):
    global hits
    reg = ToolRegistry()  # fresh registry + breaker per story
    reg.register(get_alert)
    fn, model = reg.tools["get_alert"]
    reg.tools["get_alert"] = (resilient(fn, CircuitBreaker(), DLQ), model)
    script[:] = fails
    hits, before = 0, len(DEAD_LETTERS)
    for _ in range(calls):
        try:
            out = reg.call("get_alert", args)
        except ValidationError as e:
            out = f"ValidationError -> back to the model ({e.errors()[0]['msg']})"
    print(f"\n{title}\n  model sees:      {out}\n  requests to tool: {hits}")
    print(f"  dead letters:     {len(DEAD_LETTERS) - before}")
    return out, hits, len(DEAD_LETTERS) - before


out, n, dl = story("Story 1: lucky call", [])
assert out.endswith("OK") and n == 1 and dl == 0

out, n, dl = story("Story 2: unlucky once (retried)", [True])
assert out.endswith("OK") and n == 2 and dl == 0

out, n, dl = story("Story 3: unlucky 3 times", [True] * 3)
assert out.startswith("ERROR") and n == 3 and dl == 1

out, n, dl = story("Bad arguments (front desk)", [], args='{"alert_id": 12345}')
assert out.startswith("ValidationError") and n == 0 and dl == 0

out, n, dl = story("Outage: 3 calls to a dead service", [True] * 99, calls=3)
assert "CircuitOpenError" in out and n == 5 and dl == 3

print("\nAll checks passed.")
