import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
rows = [
    json.loads(l) for l in (HERE / "golden.jsonl").read_text().splitlines() if l.strip()
]
nat = [
    {"id": r["id"], "question": r["question"], "answer": "; ".join(r["must_include"])}
    for r in rows
    if "flag_alert" not in r["tools"]
]  # the NAT agent can't flag (Day 6's allowlist)
out = HERE.parent / "workflows/hello-workflow/data/golden_nat.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(nat, indent=2))
print(f"wrote {len(nat)} rows to {out}")
