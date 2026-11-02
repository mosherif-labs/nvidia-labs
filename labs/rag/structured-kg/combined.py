import json, sys

sys.path.append("../baseline")
from baseline import NIM, LLM, retrieve
from sql_tool import sql_tool
from kg import build_graph, two_hops

G = build_graph()


def answer(q):
    ev = []
    if q.get("sql"):
        r = sql_tool(q["sql"])
        ev.append(f"[SQL] {r['sql']} -> rows: {r['rows'][:20]}")
    if q.get("account"):
        ev += [
            f"[KG {' -> '.join(p)}]"
            for p in two_hops(G, q["account"]).values()
            if len(p) > 2
        ]
    ev += [
        f"[DOC {c['chunk_id']}] {c['text'][:800]}"
        for c in retrieve(q.get("docs", q["question"]))
    ]
    msgs = [
        {
            "role": "system",
            "content": "Answer from the evidence only. Cite every claim with its tag: "
            "[SQL], [KG a -> b -> c] or [DOC chunk_id]. Say what the evidence does not show.",
        },
        {
            "role": "user",
            "content": "Evidence:\n" + "\n".join(ev) + f"\n\nQuestion: {q['question']}",
        },
    ]
    out = NIM.chat.completions.create(
        model=LLM,
        messages=msgs,
        temperature=1.0,
        top_p=0.95,
        max_tokens=1024,
        # The evidence is already gathered, and reasoning would eat max_tokens
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    return out.choices[0].message.content or (
        f"(empty reply, finish_reason={out.choices[0].finish_reason})"
    )


for q in json.load(open("questions.json", encoding="utf-8")):
    print(f"## {q['question']}\n\n{answer(q)}\n")
