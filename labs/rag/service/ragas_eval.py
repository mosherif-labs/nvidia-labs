import asyncio, json, os, sys
from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.metrics.collections import (
    AnswerAccuracy,
    ContextRecall,
    ContextRelevance,
    Faithfulness,
)
from rag_pipeline import run

# Ideally a different model from the generator (self-preference bias); pick one your key lists.
JUDGE = os.environ.get("JUDGE_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b")
llm = llm_factory(
    JUDGE,
    client=AsyncOpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ["NVIDIA_API_KEY"],
    ),
)
# One classic + one NVIDIA metric per half of RAG: generator (faithfulness, answer accuracy),
# retriever (context recall, context relevance). Their cousins measure the same halves.
faith, crec = Faithfulness(llm=llm), ContextRecall(llm=llm)
acc, crel = AnswerAccuracy(llm=llm), ContextRelevance(llm=llm)


async def score(e, resp, ctxs):
    q, ref = e["question"], e["reference_answer"]
    calls = {
        "faithfulness": faith.ascore(
            user_input=q, response=resp, retrieved_contexts=ctxs
        ),
        "context_recall": crec.ascore(
            user_input=q, retrieved_contexts=ctxs, reference=ref
        ),
        "answer_accuracy": acc.ascore(user_input=q, response=resp, reference=ref),
        "context_relevance": crel.ascore(user_input=q, retrieved_contexts=ctxs),
    }
    out = {}
    for name, coro in calls.items():
        try:
            out[name] = (await coro).value
        except Exception as ex:
            out[name] = float("nan")
            print("judge error:", name, e["id"], ex)
    return out


async def main(runs, limit):
    evalset = [
        json.loads(line) for line in open("../eval-set.jsonl", encoding="utf-8")
    ][:limit]
    answers = {
        (cfg, e["id"]): (e, *run(e["question"], cfg))
        for cfg in ("baseline", "best")
        for e in evalset
    }
    with open("scores.jsonl", "w") as f:
        for r in range(runs):
            for (cfg, qid), (e, resp, ctx) in answers.items():
                s = await score(e, resp, [c["text"] for c in ctx])
                f.write(json.dumps({"run": r, "config": cfg, "id": qid, **s}) + "\n")
                f.flush()
                print(r, cfg, qid, {k: round(v, 2) for k, v in s.items()})


if __name__ == "__main__":
    asyncio.run(
        main(
            runs=int(sys.argv[1]), limit=int(sys.argv[2]) if len(sys.argv) > 2 else None
        )
    )
