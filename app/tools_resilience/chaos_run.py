import json, os
from pathlib import Path
from app.tools_resilience.resilient_agent import investigate

from app.eval.run_evals import score

tasks = [
    json.loads(l)
    for l in (Path(__file__).resolve().parent.parent / "eval" / "golden.jsonl")
    .read_text()
    .splitlines()
    if l.strip()
][:10]  # g01-g10, the bar and bets are "of 10"; g11-g14 are Day 8's adversarial set
print(
    f"| task | solved | steps | escalated |  (CHAOS_RATE={os.environ.get('CHAOS_RATE', '0')}, RESILIENT={os.environ.get('RESILIENT', '1')})"
)
print("|---|---|---|---|")
solved = 0
for t in tasks:
    r = investigate(t["question"], case_id=t["id"])
    ok = score(t, r)
    solved += ok
    print(
        f"| {t['id']} | {'yes' if ok else 'no'} | {r['steps']} | {'yes' if r.get('escalated') else ''} |"
    )
print(f"\n**{solved}/{len(tasks)} solved**")
