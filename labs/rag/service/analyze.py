import collections, json
import numpy as np

METRICS = ["faithfulness", "context_recall", "answer_accuracy", "context_relevance"]
rows = [json.loads(line) for line in open("scores.jsonl")]
qids = sorted({r["id"] for r in rows})
per_q = collections.defaultdict(list)
for r in rows:
    for m in METRICS:
        per_q[(r["config"], m, r["id"])].append(r[m])


def boot(x, n=2000, seed=0):
    x = np.asarray([v for v in x if v == v])  # drop NaN
    means = np.random.default_rng(seed).choice(x, (n, len(x))).mean(axis=1)
    return x.mean(), *np.percentile(means, [2.5, 97.5])


fmt = lambda t: f"{t[0]:.3f} [{t[1]:.3f}, {t[2]:.3f}]"
print(
    "| metric | baseline | best | paired delta (best - baseline) |\n|---|---|---|---|"
)
for m in METRICS:
    b = [np.nanmean(per_q[("baseline", m, q)]) for q in qids]
    h = [np.nanmean(per_q[("best", m, q)]) for q in qids]
    print(
        f"| {m} | {fmt(boot(b))} | {fmt(boot(h))} | {fmt(boot([y - x for x, y in zip(b, h)]))} |"
    )
