import time
import numpy as np, cupy as cp
from cuvs.neighbors import cagra

N, D, NQ, K = 100_000, 768, 500, 10
rng = np.random.default_rng(0)
centers = rng.normal(size=(1000, D)).astype(np.float32)
X = centers[rng.integers(0, 1000, N)] + 0.3 * rng.normal(size=(N, D)).astype(np.float32)
Q = centers[rng.integers(0, 1000, NQ)] + 0.3 * rng.normal(size=(NQ, D)).astype(
    np.float32
)
X /= np.linalg.norm(X, axis=1, keepdims=True)
Q /= np.linalg.norm(Q, axis=1, keepdims=True)
Xd, Qd = cp.asarray(X), cp.asarray(Q)
truth = cp.asnumpy(cp.argpartition(-(Qd @ Xd.T), K, axis=1)[:, :K])

t = time.perf_counter()
index = cagra.build(
    cagra.IndexParams(intermediate_graph_degree=64, graph_degree=32), Xd
)
cp.cuda.Device().synchronize()
print(f"build {time.perf_counter() - t:.2f} s")

for itopk in (16, 32, 64, 128, 256):
    sp = cagra.SearchParams(itopk_size=itopk)
    cagra.search(sp, index, Qd, K)
    cp.cuda.Device().synchronize()  # warm-up
    t = time.perf_counter()
    nbrs, _ = cagra.search(sp, index, Qd, K)
    cp.cuda.Device().synchronize()
    batch_ms = (time.perf_counter() - t) * 1e3
    got = cp.asnumpy(cp.asarray(nbrs))
    recall = np.mean([len(set(g) & set(t_)) / K for g, t_ in zip(got, truth)])
    lat = []
    for i in range(200):
        t = time.perf_counter()
        cagra.search(sp, index, Qd[i : i + 1], K)
        cp.cuda.Device().synchronize()
        lat.append((time.perf_counter() - t) * 1e3)
    print(
        f"itopk={itopk:4}  recall@10={recall:.3f}  batch500={batch_ms:.2f} ms  "
        f"QPS={NQ / batch_ms * 1e3:,.0f}  p95(nq=1)={np.percentile(lat, 95):.2f} ms"
    )
