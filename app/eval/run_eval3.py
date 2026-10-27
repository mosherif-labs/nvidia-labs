import json, os, statistics as st, time
from collections import defaultdict
from pathlib import Path

from app.tools import agent
from app.tools.registry import registry
from app.eval.run_evals import score, version

T_975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776}  # t critical values, 95% two-sided
HERE = Path(__file__).resolve().parent


def mean_ci(xs):
    m = st.mean(xs)
    return (
        (m, T_975[len(xs) - 1] * st.stdev(xs) / len(xs) ** 0.5)
        if len(xs) > 1
        else (m, float("nan"))
    )


def run_task(t):
    calls = []

    def logged(name, raw):  # capture the trajectory
        calls.append((name, raw))
        return registry.call(name, raw)

    t0 = time.time()
    r = agent.run(t["question"], call=logged, verbose=False)
    looped = any(
        a == b for a, b in zip(calls, calls[1:])
    )  # same tool + same args twice in a row
    return {
        "id": t["id"],
        "success": score(t, r),  # final answer + required tools
        "tool_ok": set(t["tools"]) <= {n for n, _ in calls},
        "efficiency": min(1.0, len(t["tools"]) / max(1, len(calls))),
        "looped": looped,
        "steps": r["steps"],
        "latency_s": time.time() - t0,
    }


if __name__ == "__main__":
    runs = int(os.environ.get("RUNS", "3"))
    tasks = [
        json.loads(l)
        for l in (HERE / "golden.jsonl").read_text().splitlines()
        if l.strip()
    ]
    results = [[run_task(t) for t in tasks] for _ in range(runs)]
    for key in ("success", "tool_ok", "efficiency"):
        m, half = mean_ci([sum(r[key] for r in run) / len(run) for run in results])
        print(f"{key:<11} {m:.0%} ± {half:.0%}  (95% CI, {runs} runs)")
    lat = sorted(r["latency_s"] for run in results for r in run)
    print(
        f"p95 latency {lat[int(0.95 * (len(lat) - 1))]:.1f}s · loops {sum(r['looped'] for run in results for r in run)}"
    )
    flaky = defaultdict(list)
    for run in results:
        for r in run:
            flaky[r["id"]].append(r["success"])
    print("flaky tasks:", [k for k, v in flaky.items() if 0 < sum(v) < len(v)])
    (HERE / f"report3-{version()}.json").write_text(json.dumps(results, indent=2))
