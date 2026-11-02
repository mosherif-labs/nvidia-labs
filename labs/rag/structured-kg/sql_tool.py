import json, os, re, sqlite3, sys, time
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # nearest .env, like baseline.py

NIM = OpenAI(
    base_url=os.environ.get("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key=os.environ["NVIDIA_API_KEY"],
)
LLM = os.environ.get(
    "AGENT_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b"
)  # same model as the agent
_cache = {}  # question -> (expires_at, result)


def ro_conn():
    con = sqlite3.connect(
        "file:aml.db?mode=ro", uri=True
    )  # the real guard: read-only connection
    con.execute("PRAGMA query_only = ON")
    return con


SCHEMA = "\n".join(
    r[0]
    for r in ro_conn().execute("SELECT sql FROM sqlite_master WHERE type = 'table'")
)


def generate_sql(question):
    msgs = [
        {
            "role": "system",
            "content": f"Write one SQLite SELECT statement for this schema:\n{SCHEMA}\n"
            "Use date('now') for today. Return only the SQL: no prose, no code fences.",
        },
        {"role": "user", "content": question},
    ]
    # 1.0 / 0.95: the Nemotron 3 Super model card's values for all tasks. The guard against bad SQL
    # is the read-only connection and the SELECT check, not a low temperature.
    out = NIM.chat.completions.create(
        model=LLM,
        messages=msgs,
        temperature=1.0,
        top_p=0.95,
        max_tokens=1024,
        # One SELECT needs no reasoning, and reasoning would eat max_tokens
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    sql = out.choices[0].message.content
    if not sql:  # budget ran out before the answer: None has no .strip()
        raise RuntimeError(f"empty reply, finish_reason={out.choices[0].finish_reason}")
    return sql.strip().strip("`").removeprefix("sql").strip()


def run_sql(sql, max_rows=200):
    if not re.fullmatch(r"(?is)\s*(select|with)\b[^;]*;?\s*", sql):
        raise ValueError(f"refused, not a single SELECT: {sql!r}")
    return ro_conn().execute(sql).fetchmany(max_rows)


def sql_tool(question, ttl=300):
    hit = _cache.get(question)
    if hit and hit[0] > time.time():
        return hit[1]
    sql = generate_sql(question)
    result = {"sql": sql, "rows": run_sql(sql)}
    _cache[question] = (time.time() + ttl, result)
    return result


if __name__ == "__main__":
    print(json.dumps(sql_tool(" ".join(sys.argv[1:])), indent=2, default=str))
