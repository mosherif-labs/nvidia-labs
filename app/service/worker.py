import asyncio, json, os
import redis.asyncio as redis
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.team.team import g  # Day 18's team, not yet compiled


async def handle(job: dict, graph, r) -> None:
    cid = job["case_id"]
    await r.set(f"{cid}:status", "running")
    config = {"configurable": {"thread_id": cid}, "recursion_limit": 40}
    state = {
        "messages": [("user", job["alert_text"])],
        "turns": 0,
        "route_log": [],
        "stopped_by": "",
    }
    async for chunk in graph.astream(state, config, stream_mode="updates"):
        await r.publish(
            f"{cid}:events",
            json.dumps({node: list(upd or {}) for node, upd in chunk.items()}),
        )
    final = (await graph.aget_state(config)).values
    await r.set(
        f"{cid}:result",
        json.dumps(
            {
                "route": final["route_log"],
                "stopped_by": final["stopped_by"],
                "narrative": final["messages"][-1].content,
            }
        ),
    )
    await r.set(f"{cid}:status", "done")


async def main():
    r = redis.from_url(
        os.environ.get("REDIS_URL", "redis://redis:6379/0"), decode_responses=True
    )
    async with AsyncPostgresSaver.from_conn_string(os.environ["POSTGRES_URI"]) as saver:
        await saver.setup()  # creates the checkpoint tables once
        graph = g.compile(
            checkpointer=saver
        )  # thread_id = case_id: a crash resumes, not restarts
        while True:
            _, raw = await r.brpop("cases:queue")
            await handle(json.loads(raw), graph, r)


if __name__ == "__main__":
    asyncio.run(main())
