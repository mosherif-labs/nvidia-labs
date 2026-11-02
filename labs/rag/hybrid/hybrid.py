import json, re, sys, time
import numpy as np
from rank_bm25 import BM25Okapi
from pymilvus import MilvusClient
from langchain_core.documents import Document
from langchain_nvidia_ai_endpoints import NVIDIARerank
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "baseline"
sys.path.append(str(BASE))
from baseline import (
    embed,
    COL,
    NIM,
    LLM,
)  # Day 13: same embedding model, same collection

db = MilvusClient(str(BASE / "rag.db"))
db.load_collection(COL)  # reopened Milvus Lite collections start out released
chunks = db.query(
    COL, filter="id >= 0", output_fields=["chunk_id", "text"], limit=16384
)
ids = [c["chunk_id"] for c in chunks]
text = {c["chunk_id"]: c["text"] for c in chunks}
tok = lambda s: re.findall(r"\w+", s.lower())
bm25 = BM25Okapi([tok(text[i]) for i in ids])
reranker = NVIDIARerank(model="nvidia/llama-nemotron-rerank-1b-v2", top_n=5)


def dense(q, k=20):
    hits = db.search(
        COL, data=embed([q], "query"), limit=k, output_fields=["chunk_id"]
    )[0]
    return [h["entity"]["chunk_id"] for h in hits]


def sparse(q, k=20):
    return [ids[i] for i in np.argsort(-bm25.get_scores(tok(q)))[:k]]


def hyde(q, k=20):
    """Side quest (HyDE): embed a hypothetical answer as a passage instead of the query."""
    r = NIM.chat.completions.create(
        model=LLM,
        temperature=1.0,
        top_p=0.95,
        max_tokens=1024,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        messages=[
            {
                "role": "user",
                "content": "Write a 3-sentence passage from an AML policy or guidance "
                f"document that answers: {q}",
            }
        ],
    )
    doc = r.choices[0].message.content or q  # empty reply: fall back to the query
    hits = db.search(
        COL, data=embed([doc], "passage"), limit=k, output_fields=["chunk_id"]
    )[0]
    return [h["entity"]["chunk_id"] for h in hits]


def rrf(*rankings, k=60, top=20):
    score = {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking, 1):
            score[doc] = score.get(doc, 0.0) + 1 / (k + rank)
    return sorted(score, key=score.get, reverse=True)[:top]


def rerank(q, cands):
    docs = [Document(page_content=text[c], metadata={"chunk_id": c}) for c in cands]
    return [
        d.metadata["chunk_id"]
        for d in reranker.compress_documents(query=q, documents=docs)
    ]


if __name__ == "__main__":  # importable: Day 30 reuses dense, sparse, rrf, rerank
    RETRIEVERS = {
        "dense": dense,
        "bm25": sparse,
        "hybrid_rrf": lambda q: rrf(dense(q), sparse(q)),
        "hyde": hyde,  # side quest
    }
    evalset = [json.loads(line) for line in open("../eval-set.jsonl", encoding="utf-8")]
    evalset = [e for e in evalset if e["gold_chunk_ids"]]

    print("| config | recall@5 | MRR@5 | p50 ms | p95 ms |\n|---|---|---|---|---|")
    for name, retrieve in RETRIEVERS.items():
        for use_rr in (False, True):
            recall, rr, lat = [], [], []
            for e in evalset:
                t = time.perf_counter()
                cands = retrieve(e["question"])
                top = rerank(e["question"], cands) if use_rr else cands[:5]
                lat.append((time.perf_counter() - t) * 1e3)
                gold = set(e["gold_chunk_ids"])
                recall.append(len(gold & set(top[:5])) / len(gold))
                first = next((r for r, c in enumerate(top[:5], 1) if c in gold), None)
                rr.append(1 / first if first else 0.0)
            label = name + (" + rerank" if use_rr else "")
            print(
                f"| {label} | {np.mean(recall):.3f} | {np.mean(rr):.3f} | "
                f"{np.percentile(lat, 50):.0f} | {np.percentile(lat, 95):.0f} |"
            )
