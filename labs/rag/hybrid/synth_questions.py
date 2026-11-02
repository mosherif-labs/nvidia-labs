"""Draft eval questions from random chunks: one question per chunk, and that chunk is the gold id."""

import json, random, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "baseline"
sys.path.append(str(BASE))
from baseline import COL, LLM, NIM  # Day 13: same collection, same model
from pymilvus import MilvusClient

PROMPT = (
    "Write one question an AML analyst might ask that this passage alone answers, "
    "a short reference answer, and the exact sentence from the passage that proves it. "
    'Return JSON only: {"question": "...", "reference_answer": "...", "evidence": "..."}\n\n'
    "Passage:\n"
)

db = MilvusClient(str(BASE / "rag.db"))
db.load_collection(COL)  # reopened Milvus Lite collections start out released
chunks = db.query(
    COL, filter="id >= 0", output_fields=["chunk_id", "source", "text"], limit=16384
)
random.seed(26)
with open("eval-candidates.jsonl", "w", encoding="utf-8") as out:
    for c in random.sample(chunks, 30):
        r = NIM.chat.completions.create(
            model=LLM,
            temperature=1.0,  # the Nemotron 3 Super model card's values, as on every lab day
            top_p=0.95,
            max_tokens=2048,
            messages=[{"role": "user", "content": PROMPT + c["text"]}],
        )
        try:
            qa = json.loads(
                (r.choices[0].message.content or "")
                .strip()
                .strip("`")
                .removeprefix("json")
            )
            row = {
                "question": qa["question"],
                "reference_answer": qa["reference_answer"],
                "gold_chunk_ids": [c["chunk_id"]],
                "gold_source": c["source"],
                "evidence": qa["evidence"],
                "type": "synthetic",
            }
        except (json.JSONDecodeError, KeyError, TypeError):
            continue  # skip a malformed draft: you only need 20 of 30
        out.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(c["chunk_id"], "->", row["question"])
