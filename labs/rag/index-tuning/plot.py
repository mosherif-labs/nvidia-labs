import csv
from collections import defaultdict
import matplotlib.pyplot as plt

rows = defaultdict(list)
for r in csv.DictReader(open("results.csv")):
    rows[r["index"]].append((float(r["p95_ms"]), float(r["recall_at_10"]), r["value"]))
for name, pts in rows.items():
    x, y, labels = zip(*pts)
    plt.plot(x, y, marker="o", label=name)
    for xi, yi, l in pts:
        plt.annotate(l, (xi, yi), fontsize=7)
plt.axhline(0.95, ls="--", c="gray")
plt.xlabel("p95 latency (ms)")
plt.ylabel("recall@10")
plt.legend()
plt.grid(alpha=0.3)
plt.title("100k x 768, Milvus standalone")
plt.savefig("recall_vs_latency.png", dpi=150)
