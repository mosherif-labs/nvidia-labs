import sqlite3, time
from enum import Enum
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

DB = sqlite3.connect(Path(__file__).with_name("feedback.db"), check_same_thread=False)
DB.execute("""CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY, ts TEXT, case_id TEXT, trace_id TEXT,
              agent_version TEXT, question TEXT, answer TEXT, rating INTEGER, reason TEXT, correction TEXT, reviewer TEXT)""")


class Reason(str, Enum):  # reason codes make feedback countable, not just "bad"
    good = "good"
    wrong_fact = "wrong_fact"
    wrong_policy = "wrong_policy"
    missed_red_flag = "missed_red_flag"
    unsupported_claim = "unsupported_claim"
    too_slow = "too_slow"


class Feedback(BaseModel):
    case_id: str
    trace_id: str = Field(
        description="The Phoenix trace of the run being rated (Day 15)"
    )
    agent_version: str = Field(description="The version hash from Day 8's run_evals.py")
    question: str
    answer: str
    rating: int = Field(ge=-1, le=1, description="+1 thumbs up, -1 thumbs down")
    reason: Reason
    correction: str | None = Field(
        None, description="Facts the right answer must contain, separated by ';'"
    )
    reviewer: str


app = FastAPI(title="Agent feedback")


@app.post("/feedback")
def add(f: Feedback):
    if f.rating < 0 and f.reason is Reason.good:
        raise HTTPException(422, "a thumbs-down needs a reason code other than 'good'")
    DB.execute(
        "INSERT INTO feedback VALUES (NULL,?,?,?,?,?,?,?,?,?,?)",
        (
            time.strftime("%Y-%m-%dT%H:%M:%S"),
            f.case_id,
            f.trace_id,
            f.agent_version,
            f.question,
            f.answer,
            f.rating,
            f.reason.value,
            f.correction,
            f.reviewer,
        ),
    )
    DB.commit()
    return {"stored": True}


@app.get("/feedback/summary")
def summary():
    rows = DB.execute(
        "SELECT agent_version, reason, COUNT(*), AVG(rating) FROM feedback "
        "GROUP BY agent_version, reason ORDER BY agent_version"
    ).fetchall()
    return [
        {"agent_version": v, "reason": r, "count": n, "avg_rating": round(a, 2)}
        for v, r, n, a in rows
    ]
