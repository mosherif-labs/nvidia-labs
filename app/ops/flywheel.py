"""Weekly job: thumbs-down feedback with a correction -> golden-set candidates -> a human reviews them."""

import json, sqlite3
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLDEN = HERE.parent / "eval" / "golden.jsonl"
known = {
    json.loads(l)["question"] for l in GOLDEN.read_text().splitlines() if l.strip()
}
db = sqlite3.connect(HERE / "feedback.db")
rows = db.execute(
    "SELECT id, case_id, trace_id, question, correction, reason FROM feedback "
    "WHERE rating < 0 AND correction IS NOT NULL"
).fetchall()

cands = []
for fid, case_id, trace_id, question, correction, reason in rows:
    if question in known:
        continue  # already covered by the golden set
    known.add(question)
    cands.append(
        {
            "id": f"fb-{fid}-{case_id}",  # row id: one case can get several thumbs-down
            "question": question,
            "must_include": [c.strip() for c in correction.split(";") if c.strip()],
            "tools": [],
            "source": {"trace_id": trace_id, "reason": reason},
        }
    )

out = HERE / "golden-candidates.jsonl"
out.write_text("".join(json.dumps(c) + "\n" for c in cands))
print(
    f"{len(rows)} thumbs-down with corrections -> {len(cands)} new candidates in {out.name}"
)
print("by reason:", dict(Counter(c["source"]["reason"] for c in cands)))
print(
    "Next: review each candidate (fill 'tools'), append the approved ones to golden.jsonl, "
    "then run the Day 8 gate on the current and the next version."
)
