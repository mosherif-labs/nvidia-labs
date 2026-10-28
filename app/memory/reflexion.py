import json
import sys
from pathlib import Path

from app.tools import agent
from app.eval.run_evals import score
from app.memory.memory import open_store, remember, recall

GOLDEN = Path(__file__).resolve().parent.parent / "eval" / "golden.jsonl"


def solve(store, task):  # Actor: Day 4's agent + recalled lessons
    notes = recall(store, "lessons", task["question"]) + recall(
        store, "semantic", task["question"]
    )
    memo = "\n".join(f"- {n}" for n in notes) or "- none yet"
    return agent.run(
        f"Lessons and facts from past cases:\n{memo}\n\nTask: {task['question']}",
        verbose=False,
    )


def reflect(task, result) -> str:  # Self-reflection: sees the failure, never the key
    prompt = (
        f"Task: {task['question']}\nYour answer: {result['answer']}\n"
        f"Tools you used: {result['tools_used']}\n"
        "This answer was judged WRONG. In two sentences, write a general lesson for "
        "similar tasks: which tool or check you should have used. "
        "Do not guess the right answer."
    )
    return (
        agent.client.chat.completions.create(
            model=agent.MODEL,
            temperature=1.0,
            top_p=0.95,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
            # A two-sentence lesson needs no reasoning, and reasoning would eat max_tokens
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        .choices[0]
        .message.content
    ) or ""  # empty reply (budget ran out): no lesson


if __name__ == "__main__":
    run = sys.argv[1]  # "1" writes lessons, "2" only reads them
    if len(sys.argv) > 2:
        agent.MAX_STEPS = int(sys.argv[2])  # a tight budget makes failures
    tasks = [json.loads(l) for l in GOLDEN.read_text().splitlines() if l.strip()]
    with open_store() as store:
        passed = 0
        print("| run | task | result | steps | lesson |\n|---|---|---|---|---|")
        for t in tasks:
            r = solve(store, t)
            ok = score(t, r)  # Evaluator: Day 8's deterministic scorer
            passed += ok
            lesson = ""
            if not ok and run == "1":
                lesson = reflect(t, r)
                if lesson.strip():  # never store an empty lesson
                    remember(store, "lessons", lesson, task=t["id"])
            row = f"| {run} | {t['id']} | {'PASS' if ok else 'FAIL'} | {r['steps']} |"
            print(f"{row} {lesson.strip().replace(chr(10), ' ')} |")
        print(f"\nrun {run}: {passed}/{len(tasks)}")
