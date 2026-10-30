import hashlib, json, os, re, sys, unicodedata
from pathlib import Path

from app.tools import agent
from app.tools.registry import registry

MIN_PASS = float(os.environ.get("MIN_PASS", "0.8"))
HERE = Path(__file__).resolve().parent


def norm(s: str) -> str:
    # NFKC: narrow/no-break spaces -> " ", curly quotes stay; then unicode hyphens/dashes -> "-"
    s = unicodedata.normalize("NFKC", s or "").lower().replace("\u2019", "'")
    s = re.sub(r"[\u2010-\u2015\u2212]", "-", s)
    return re.sub(r"(?<=\d)[, ](?=\d{3}\b)", "", s)  # 28,500 / 28\u202f500 -> 28500


def version() -> str:
    """Prompt + tool schemas + model are ONE versioned unit: change any of them, the version changes."""
    blob = json.dumps(
        {"system": agent.SYSTEM, "tools": registry.schemas(), "model": agent.MODEL},
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def score(task, result) -> bool:
    answer = norm(result["answer"])
    answer_ok = all(norm(m) in answer for m in task["must_include"])
    if task.get("any_of"):  # several fair phrasings: at least one must appear
        answer_ok = answer_ok and any(norm(m) in answer for m in task["any_of"])
    tools_ok = set(task["tools"]) <= set(result["tools_used"])
    return answer_ok and tools_ok


if __name__ == "__main__":
    tasks = [
        json.loads(l)
        for l in (HERE / "golden.jsonl").read_text().splitlines()
        if l.strip()
    ]
    rows = []
    for t in tasks:
        r = agent.run(t["question"], verbose=False)
        rows.append(
            {
                "id": t["id"],
                "pass": score(t, r),
                "steps": r["steps"],
                "tools": r["tools_used"],
                "answer": r["answer"],  # kept so a FAIL can be judged: agent vs scorer
            }
        )
        print(
            f"{t['id']}  {'PASS' if rows[-1]['pass'] else 'FAIL'}  steps={r['steps']}  tools={r['tools_used']}"
        )
        if not rows[-1]["pass"]:
            print(f"     answer: {r['answer']!r}")
    rate = sum(r["pass"] for r in rows) / len(rows)
    report = {
        "version": version(),
        "model": agent.MODEL,
        "pass_rate": rate,
        "rows": rows,
    }
    (HERE / f"report-{report['version']}.json").write_text(json.dumps(report, indent=2))
    print(f"\nagent version {report['version']}: {rate:.0%} (gate {MIN_PASS:.0%})")
    sys.exit(0 if rate >= MIN_PASS else 1)
