import csv, time
import numpy as np
from pymilvus import MilvusClient, DataType

N, D, NQ, K = 100_000, 768, 500, 10
rng = np.random.default_rng(0)
centers = rng.normal(size=(1000, D)).astype(np.float32)
X = centers[rng.integers(0, 1000, N)] + 0.3 * rng.normal(size=(N, D)).astype(np.float32)
Q = centers[rng.integers(0, 1000, NQ)] + 0.3 * rng.normal(size=(NQ, D)).astype(
    np.float32
)
X /= np.linalg.norm(X, axis=1, keepdims=True)
Q /= np.linalg.norm(Q, axis=1, keepdims=True)
truth = np.argpartition(-(Q @ X.T), K, axis=1)[:, :K]  # exact top-10 (set)

c = MilvusClient("http://localhost:19530")
INDEXES = {
    "flat": ("FLAT", {}, None, [None]),
    "hnsw": (
        "HNSW",
        {"M": 16, "efConstruction": 200},
        "ef",
        [10, 16, 32, 64, 128, 256, 512],
    ),
    "ivfpq": (
        "IVF_PQ",
        {"nlist": 1024, "m": 96, "nbits": 8},
        "nprobe",
        [1, 4, 8, 16, 32, 64, 128],
    ),
}


def build(name, itype, params):
    col = f"bench_{name}"
    if c.has_collection(col):
        c.drop_collection(col)
    schema = c.create_schema(auto_id=False)
    schema.add_field("id", DataType.INT64, is_primary=True)
    schema.add_field("vec", DataType.FLOAT_VECTOR, dim=D)
    c.create_collection(col, schema=schema)
    for s in range(0, N, 5000):
        c.insert(
            col, [{"id": i, "vec": X[i].tolist()} for i in range(s, min(s + 5000, N))]
        )
    c.flush(col)
    ip = c.prepare_index_params()
    ip.add_index(field_name="vec", index_type=itype, metric_type="IP", params=params)
    t = time.perf_counter()
    c.create_index(col, ip)
    print(f"{name}: index built in {time.perf_counter() - t:.1f} s")
    c.load_collection(col)
    return col


def run(col, knob, value):
    sp = {"metric_type": "IP", "params": {knob: value} if knob else {}}
    lat, hits = [], []
    for q in Q:
        t = time.perf_counter()
        r = c.search(
            col, data=[q.tolist()], limit=K, anns_field="vec", search_params=sp
        )
        lat.append((time.perf_counter() - t) * 1e3)
        hits.append({h["id"] for h in r[0]})
    recall = np.mean([len(h & set(t)) / K for h, t in zip(hits, truth)])
    return recall, np.percentile(lat, 95)


with open("results.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["index", "knob", "value", "recall_at_10", "p95_ms"])
    for name, (itype, params, knob, values) in INDEXES.items():
        col = build(name, itype, params)
        for v in values:
            recall, p95 = run(col, knob, v)
            print(
                f"{name:6} {knob or '-':6} {v!s:>4}  recall@10={recall:.3f}  p95={p95:.2f} ms"
            )
            w.writerow([name, knob, v, round(recall, 4), round(p95, 3)])
        c.release_collection(col)
