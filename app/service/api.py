import json, os
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="Investigation service")
r = redis.from_url(
    os.environ.get("REDIS_URL", "redis://redis:6379/0"), decode_responses=True
)
QUEUE = "cases:queue"


class CaseIn(BaseModel):
    alert_id: str
    alert_text: str


@app.post("/cases", status_code=202)
async def create_case(case: CaseIn):
    case_id = f"case-{case.alert_id}"  # idempotent: same alert, same case
    created = await r.set(f"{case_id}:status", "queued", nx=True)
    if created:
        await r.lpush(QUEUE, json.dumps({"case_id": case_id, **case.model_dump()}))
    return {"case_id": case_id, "duplicate": not created}


@app.get("/cases/{case_id}")
async def get_case(case_id: str):
    status = await r.get(f"{case_id}:status")
    if status is None:
        raise HTTPException(404, "unknown case")
    result = await r.get(f"{case_id}:result")
    return {
        "case_id": case_id,
        "status": status,
        "result": json.loads(result) if result else None,
    }


@app.get("/cases/{case_id}/events")
async def case_events(case_id: str):
    async def stream():
        pubsub = r.pubsub()
        await pubsub.subscribe(f"{case_id}:events")
        async for msg in pubsub.listen():
            if msg["type"] == "message":
                yield f"data: {msg['data']}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/healthz")  # liveness: the process answers
async def healthz():
    return {"ok": True}


@app.get("/readyz")  # readiness: it can reach its queue
async def readyz():
    try:
        await r.ping()
    except Exception:
        raise HTTPException(503, "redis unreachable")
    return {"ready": True}
