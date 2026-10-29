import json, os, random, time
from pathlib import Path

from prometheus_client import Counter, Histogram, start_http_server

from app.tools import agent  # Day 4's agent
from app.tools.registry import registry
from app.eval.run_evals import score, version  # Day 8's scorer and version hash

HERE = Path(__file__).resolve().parent

if os.environ.get("AGENT_SYSTEM"):  # v2 = a different system prompt
    agent.SYSTEM = os.environ["AGENT_SYSTEM"]
V = os.environ.get("AGENT_VERSION_LABEL", "v1")
# CHAOS_RATE = share of tool calls that fail on purpose (Day 9's idea)
CHAOS = float(os.environ.get("CHAOS_RATE", "0"))
PORT = int(os.environ.get("METRICS_PORT", "9101"))
ROUNDS = int(os.environ.get("ROUNDS", "1"))

TASKS = Counter("agent_tasks", "Golden tasks run", ["version", "result"])
STOPS = Counter(
    "agent_stops", "How tasks ended (answer | max_steps)", ["version", "stopped"]
)
LLM_CALLS = Counter("agent_llm_calls", "LLM calls: the cost proxy", ["version"])
TOOL_CALLS = Counter("agent_tool_calls", "Tool calls", ["version", "tool", "status"])
ESCALATIONS = Counter("agent_escalations", "flag_alert side effects", ["version"])
TASK_LAT = Histogram(
    "agent_task_latency_seconds",
    "End-to-end task latency",
    ["version"],
    buckets=(1, 2, 5, 10, 20, 40, 80, 160),
)
TOOL_LAT = Histogram("agent_tool_latency_seconds", "Tool latency", ["version", "tool"])


def call(name: str, raw: str) -> str:
    t0 = time.perf_counter()
    try:
        if random.random() < CHAOS:
            raise TimeoutError("chaos: tool timed out")
        out = registry.call(name, raw)
        TOOL_CALLS.labels(V, name, "ok").inc()
        if name == "flag_alert":
            ESCALATIONS.labels(V).inc()
        return out
    except Exception:
        TOOL_CALLS.labels(V, name, "error").inc()
        raise  # agent.run turns it into an ERROR observation
    finally:
        TOOL_LAT.labels(V, name).observe(time.perf_counter() - t0)


if __name__ == "__main__":
    start_http_server(PORT)
    tasks = [
        json.loads(l)
        for l in (HERE.parent / "eval" / "golden.jsonl").read_text().splitlines()
        if l.strip()
    ]
    passed = 0
    for _ in range(ROUNDS):
        for t in tasks:
            t0 = time.perf_counter()
            r = agent.run(t["question"], call=call, verbose=False)
            TASK_LAT.labels(V).observe(time.perf_counter() - t0)
            LLM_CALLS.labels(V).inc(r["steps"])
            STOPS.labels(V, r["stopped"]).inc()
            ok = score(t, r)
            passed += ok
            TASKS.labels(V, "pass" if ok else "fail").inc()
            print(f"{t['id']} {'PASS' if ok else 'FAIL'} steps={r['steps']}")
    print(
        f"{V} (agent version {version()}): {passed}/{len(tasks) * ROUNDS} passed. "
        f"Metrics on http://localhost:{PORT}/metrics. Ctrl+C when you're done looking."
    )
    while True:
        time.sleep(60)  # keep /metrics up for Prometheus
