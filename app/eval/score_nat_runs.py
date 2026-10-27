import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "workflows/hello-workflow/.tmp/eval"
gold = {
    r["id"]: r
    for r in (
        json.loads(l)
        for l in (HERE / "golden.jsonl").read_text().splitlines()
        if l.strip()
    )
}
runs = json.loads((OUT / "workflow_output.json").read_text())
judge = json.loads((OUT / "trajectory_accuracy_output.json").read_text())

ok = []
for item in runs:
    used = {
        s["payload"]["name"] or ""
        for s in item["intermediate_steps"]
        if s["payload"]["event_type"] == "TOOL_END"
    }
    need = gold[item["id"].split("_rep")[0]]["tools"]  # --reps=N suffixes ids: g01_rep0
    # MCP tools can carry the function-group prefix, e.g. fincrime__get_alert
    ok.append(all(any(u.endswith(t) for u in used) for t in need))
    print(item["id"], "tool_ok" if ok[-1] else "MISS", sorted(used))

print(f"tool_ok on NAT's runs: {sum(ok) / len(ok):.0%} ({len(ok)} items)")
print(f"judge average:         {judge['average_score']:.0%}")
for e in judge["eval_output_items"]:
    print("judge", e["id"], round(e["score"], 2))
