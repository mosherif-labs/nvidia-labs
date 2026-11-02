# Day 26 (W04 D07): index wars: recall, latency, memory

Code: [`labs/rag/index-tuning/`](../labs/rag/index-tuning/) · `bench.py` (FLAT / HNSW / IVF_PQ on Milvus Standalone), `plot.py`, `cagra_bench.py` (side quest, GPU).

> **Not run yet.** The lab needs Milvus Standalone in Docker, which this session couldn't reach. §3 has the commands and the paper numbers to check against; fill the measured columns after the run.

## §1 Bets

| Bet | Prompt | Guess | Actual | Result |
|---|---|---|---|---|
| A | IVF_PQ (m = 96, nbits = 8) on 768-dim: memory as % of FLAT | _yours_ | ≈ **3%** on paper (96 B vs 3,072 B/vector, 32×); confirm with `docker stats` | |
| B | Smallest HNSW `ef` for recall@10 ≥ 0.95 on 100k | _yours_ | from `results.csv` | |
| C | 1B vectors, 50 ms p95, 95% recall: your index | _yours_ | IVF_PQ + refine (see §4) | |
| D | Recall@5 points the reranker adds on top of dense | _yours_ | from [d26-rag-hybrid.md](d26-rag-hybrid.md) §2 | |

## §2 Index cheat table

| Index | How it searches | Build knobs | Search knob | Recall | Memory |
|---|---|---|---|---|---|
| **FLAT** | Exact brute-force scan of every vector | – | – | 100% | Full vectors (d × 4 B) |
| **IVF_FLAT** | k-means into `nlist` clusters; scan only the `nprobe` closest clusters, full vectors | `nlist` | `nprobe` | High, rises with `nprobe` | Full vectors + centroids |
| **IVF_PQ** | IVF + each vector split into `m` sub-vectors, each stored as an `nbits` codebook index | `nlist`, `m`, `nbits` | `nprobe` | Lower ("minor compromise"), fix with a refine step | m × nbits bits/vector (96 B here) |
| **HNSW** | Multi-layer graph: sparse top layers for long jumps, greedy descent to the bottom layer (all points) | `M` (edges/node), `efConstruction` | `ef` | Very high | Vectors + M × 2 × 4 B links: **large** |
| **GPU CAGRA** | kNN graph built on GPU (IVF-PQ or NN-Descent), pruned; search keeps a working set of best candidates | `graph_degree`, `intermediate_graph_degree` | `itopk_size` (≥ k) | Very high | Must fit in GPU memory; can export to HNSW for CPU search |

**Metric:** on **normalized** vectors IP = cosine, and L2 ranks identically. Normalize once and use **IP** (cheapest: one dot product, no norms). Milvus's L2 skips the square root, so raw L2 scores look odd but rank correctly.

## §3 Results

Run (WSL 2 / Docker Desktop):

```bash
cd nvidia-labs/labs/rag/index-tuning
curl -sfL https://raw.githubusercontent.com/milvus-io/milvus/master/scripts/standalone_embed.sh -o standalone_embed.sh
bash standalone_embed.sh start
uv run python bench.py | tee bench_run1.txt
uv run python plot.py
# memory, one collection loaded at a time (repeat for bench_flat, bench_ivfpq):
uv run python -c "from pymilvus import MilvusClient; c = MilvusClient('http://localhost:19530'); [c.release_collection(x) for x in c.list_collections()]; c.load_collection('bench_hnsw')"
docker stats --no-stream milvus-standalone
bash standalone_embed.sh stop
```

![recall vs latency](../labs/rag/index-tuning/recall_vs_latency.png)

| Index | Smallest knob reaching recall@10 ≥ 0.95 | p95 there (ms) | Memory on paper | Measured RAM delta |
|---|---|---|---|---|
| FLAT | – (1.0 by definition) | | ≈ 307 MB | |
| HNSW (M = 16, efC = 200) | `ef` = | | ≈ 320 MB (the graph is cheap; vectors are the cost) | |
| IVF_PQ (nlist 1024, m 96, nbits 8) | `nprobe` = (may never reach 0.95: PQ caps recall) | | ≈ 9.6 MB + codebooks/centroids (~3% of FLAT) | |

Expect the ordering to hold even if the container deltas are noisy (segments, caches, raw data Milvus keeps). Data is clustered around 1,000 centres on purpose: uniform random vectors have no structure and make every ANN index look bad.

## §4 The billion-vector decision

**1B × 768 dims, 50 ms p95, 95% recall.**

- **Memory first:** 1B × 3,072 B ≈ **3 TB** raw; HNSW (M = 16) ≈ **3.2 TB** of RAM. FLAT is out on latency (exact scan of 1B per query).
- **Pick: IVF_PQ + refine.** ~64–96 B/vector ≈ **64–96 GB** of codes: fits in a few nodes' RAM. FAISS's guideline at 100M–1B is IVF with ~1M clusters (`IVF1048576_HNSW32`: an HNSW over the centroids so finding the `nprobe` lists is fast). A **refine** step re-scores the top candidates on full-precision vectors (SSD or a separate tier) to climb back to 95% recall.
- **Knobs:** `nlist` ≈ 1M, `m` = 64–96, `nbits` = 8; tune `nprobe` and the refine depth on a real sample against the 50 ms p95, exactly like today's sweep.
- **Nodes:** shard the codes over ~4–8 query nodes to parallelize each query; add **replicas** for QPS and HA.
- **On GPUs:** CAGRA or GPU IVF-PQ when the index fits in aggregate GPU memory and you need high **batched** throughput or fast rebuilds; build CAGRA on GPU and export to HNSW if search must stay on CPU.
- The exam rewards the reasoning from memory → latency → recall, not one "right" index.

## Side quest: GPU CAGRA on an L4

`cagra_bench.py` runs cuVS CAGRA straight from Python (Milvus GPU needs Docker Compose, and a RunPod pod is itself a container). Rent an L4, `pip install cuvs-cu12 cupy-cuda12x`, run, **destroy the pod**. Record recall@10, batch-500 QPS and p95 at nq = 1 per `itopk_size`: GPU indexes shine on batches, not single queries.

| itopk | recall@10 | batch 500 (ms) | QPS | p95 nq=1 (ms) |
|---|---|---|---|---|
| 16 | | | | |
| 64 | | | | |
| 256 | | | | |
