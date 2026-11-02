import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path += [str(HERE.parent / "baseline"), str(HERE.parent / "hybrid")]
import baseline  # Day 13
from baseline import NIM, LLM
import hybrid  # Day 26; importable since its evaluation sits under __main__

SYSTEM = (
    "Answer only from the numbered context. Cite every claim like [2]. "
    "If the context does not contain the answer, say you don't know."
)


def retrieve(q, config="best"):
    if config == "baseline":  # Day 13: dense top 5
        return [
            {"chunk_id": c["chunk_id"], "text": c["text"]} for c in baseline.retrieve(q)
        ]
    ids = hybrid.rerank(
        q, hybrid.rrf(hybrid.dense(q), hybrid.sparse(q))
    )  # Day 26 winner; change if yours differed
    return [{"chunk_id": i, "text": hybrid.text[i]} for i in ids]


def generate(q, ctx):
    context = "\n\n".join(
        f"[{i}] ({c['chunk_id']}) {c['text']}" for i, c in enumerate(ctx, 1)
    )
    out = NIM.chat.completions.create(
        model=LLM,
        temperature=1.0,
        top_p=0.95,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {q}"},
        ],
        # A cited answer from given context needs no reasoning, and reasoning would eat max_tokens
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    text = out.choices[0].message.content
    if not text:  # don't let Ragas score an empty answer as a real one
        raise RuntimeError(f"empty reply, finish_reason={out.choices[0].finish_reason}")
    return text


def run(q, config="best"):
    ctx = retrieve(q, config)
    return generate(q, ctx), ctx
