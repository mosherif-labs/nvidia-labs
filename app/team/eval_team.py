"""Day 8's golden set through the whole team. Exit 1 below the gate, like run_evals.py."""

import json, os, sys, time
from pathlib import Path
import numpy as np
from app.team.team import team

HERE = Path(__file__).resolve().parent
from app.eval.run_evals import norm  # same number normalisation as Day 8

MIN_PASS, RUNS = (
    float(os.environ.get("MIN_PASS", "0.7")),
    int(os.environ.get("RUNS", "1")),
)

tasks = [
    json.loads(l)
    for l in (HERE.parent / "eval" / "golden.jsonl").read_text().splitlines()
    if l.strip()
]
rates, lat, loops = [], [], 0
for run in range(RUNS):
    passed = 0
    for t in tasks:
        t0 = time.perf_counter()
        out = team.invoke(
            {
                "messages": [("user", t["question"])],
                "turns": 0,
                "route_log": [],
                "stopped_by": "",
            },
            {"recursion_limit": 40},
        )
        lat.append(time.perf_counter() - t0)
        loops += out["stopped_by"] != "FINISH"
        ok = all(
            norm(m) in norm(out["messages"][-1].content) for m in t["must_include"]
        )
        passed += ok
        print(
            f"run {run} {t['id']}  {'PASS' if ok else 'FAIL'}  {' > '.join(out['route_log'])}  {out['stopped_by']}"
        )
    rates.append(passed / len(tasks))
print(
    f"\nteam success {np.mean(rates):.0%} over {RUNS} run(s), p95 {np.percentile(lat, 95):.1f}s, "
    f"non-FINISH stops {loops} (gate {MIN_PASS:.0%})"
)
sys.exit(0 if np.mean(rates) >= MIN_PASS else 1)
