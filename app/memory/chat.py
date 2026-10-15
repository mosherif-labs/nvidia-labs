import json, os

from app.tools import agent

MODE = os.environ.get("MEMORY_MODE", "buffer")  # buffer | summary_buffer
KEEP = 4  # recent messages kept verbatim (2 question/answer pairs)


def render(history, summary):
    turns = "\n".join(f"{who}: {text}" for who, text in history)
    return (f"Summary of earlier conversation: {summary}\n" if summary else "") + turns


def compact(history, summary):
    """Summary + buffer: fold everything but the last KEEP messages into a running summary."""
    if len(history) <= KEEP:
        return history, summary
    old, recent = history[:-KEEP], history[-KEEP:]
    prompt = (
        f"Summarise this analyst conversation in 3 lines. Keep alert ids, amounts, policy ids, decisions.\n"
        f"Previous summary: {summary}\n" + "\n".join(f"{w}: {t}" for w, t in old)
    )
    summary = (
        agent.client.chat.completions.create(
            model=agent.MODEL,
            temperature=1.0,
            top_p=0.95,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
            # A short summary needs no reasoning, and reasoning would eat max_tokens
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        .choices[0]
        .message.content
    ) or summary  # empty reply (budget ran out): keep the previous summary
    return recent, summary


TURNS = [
    "What happened in alert A-1001?",
    "Which policy applies to it?",
    "And A-1002?",
    "What's the deadline there?",
    "Is A-1003 suspicious?",
    "Remind me: what was the total in the first alert, and its policy?",
]

history, summary, prompt_chars = [], "", []
for q in TURNS:
    context = render(history, summary)
    prompt_chars.append(len(context))
    r = agent.run(
        f"Conversation so far:\n{context}\n\nNew question: {q}" if context else q,
        verbose=False,
    )
    history += [("analyst", q), ("agent", (r["answer"] or "")[:400])]
    if MODE == "summary_buffer":
        history, summary = compact(history, summary)
    print(f"Q: {q}\nA: {(r['answer'] or '')[:200]}\n")
print(json.dumps({"mode": MODE, "context_chars_per_turn": prompt_chars}))
