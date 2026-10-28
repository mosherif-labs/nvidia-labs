import json, sys
from collections import Counter
from pathlib import Path
from langgraph.errors import GraphRecursionError
from app.team.team import team

alerts = json.loads(Path(__file__).with_name("alerts.json").read_text())
only = set(sys.argv[1:])  # optional: run a few ids, e.g. t03 t07
rows, workers = [], Counter()
for a in alerts:
    if only and a["id"] not in only:
        continue
    try:
        out = team.invoke(
            {
                "messages": [("user", a["alert"])],
                "turns": 0,
                "route_log": [],
                "stopped_by": "",
            },
            {"recursion_limit": 40},
        )
        route, stop = out["route_log"], out["stopped_by"]
    except GraphRecursionError:
        route, stop = ["?"], "RECURSION_LIMIT"
    workers.update(route)
    rows.append((a["id"], route == a["expected"], stop))
    print(
        f"{a['id']}  {'OK ' if route == a['expected'] else 'DIFF'}  {' > '.join(route):45} turns={len(route)}  stopped_by={stop}"
        + ("" if route == a["expected"] else f"   expected {' > '.join(a['expected'])}")
    )
print(
    f"\nexpected route: {sum(r[1] for r in rows)}/{len(rows)}   stops: {dict(Counter(r[2] for r in rows))}"
)
print("calls per worker:", dict(workers))
