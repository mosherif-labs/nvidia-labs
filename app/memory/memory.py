import os, time, uuid
from dotenv import load_dotenv
from openai import OpenAI
from langgraph.store.postgres import PostgresStore

load_dotenv()  # nearest .env, searching up from this file

DB_URI = os.environ.get(
    "MEMORY_DB",
    "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable",
)
DECAY = float(
    os.environ.get("MEMORY_DECAY", "0.01")
)  # per hour, as in LangChain's retriever
nim = OpenAI(
    base_url=os.environ.get("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key=os.environ["NVIDIA_API_KEY"],
)
# NVIDIA retriever embedders are asymmetric: "passage" to index, "query" to search
_input_type = {"value": "passage"}


def embed(texts: list[str]) -> list[list[float]]:
    r = nim.embeddings.create(
        model="nvidia/nemotron-3-embed-1b",
        input=texts,
        extra_body={"input_type": _input_type["value"]},
    )
    return [d.embedding for d in r.data]


def open_store():
    dims = len(embed(["probe"])[0])
    return PostgresStore.from_conn_string(
        DB_URI,
        index={
            "embed": embed,
            "dims": dims,
            "fields": ["text"],
            # pgvector's HNSW index caps `vector` at 2,000 dims; this model returns more.
            # halfvec (16-bit floats) allows up to 4,000 and halves the storage.
            "ann_index_config": {"vector_type": "halfvec"},
        },
    )


def remember(
    store, kind: str, text: str, **meta
):  # kind: "episodic" | "semantic" | "lessons"
    # Same kind + text -> same key, so rerunning the seed overwrites instead of duplicating
    key = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{kind}:{text}"))
    store.put(
        ("investigator", kind),
        key,
        {"text": text, "last_accessed": time.time(), **meta},
    )


def recall(store, kind: str, query: str, k: int = 3) -> list[str]:
    now = time.time()
    # PostgresStore embeds the search text with the same function as stored items,
    # so switch it to "query" for this one call (not thread-safe; fine for a script).
    _input_type["value"] = "query"
    try:
        items = store.search(("investigator", kind), query=query, limit=20)
    finally:
        _input_type["value"] = "passage"

    def score(it):  # similarity + (1 - decay) ** hours_since_access
        return (it.score or 0.0) + (1 - DECAY) ** (
            (now - it.value["last_accessed"]) / 3600
        )

    top = sorted(items, key=score, reverse=True)[:k]
    for it in top:  # being recalled resets the clock
        store.put(it.namespace, it.key, {**it.value, "last_accessed": now})
    return [it.value["text"] for it in top]
