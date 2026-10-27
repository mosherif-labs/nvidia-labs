import os, re, sys, pathlib
from openai import OpenAI
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pymilvus import MilvusClient
from dotenv import load_dotenv

load_dotenv()  # nearest .env, searching up from this file

NIM = OpenAI(
    base_url=os.environ.get("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key=os.environ["NVIDIA_API_KEY"],
)
EMBED = "nvidia/nemotron-3-embed-1b"  # NeMo Retriever embedding model, 2048-dim
LLM = os.environ.get("AGENT_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
DB, COL = "rag.db", "aml_baseline"
HERE = pathlib.Path(__file__).resolve().parent


def embed(texts, kind):  # kind: "passage" to index, "query" to search
    r = NIM.embeddings.create(
        model=EMBED,
        input=texts,
        encoding_format="float",
        extra_body={"input_type": kind, "truncate": "END"},
    )
    return [d.embedding for d in r.data]


def load(corpus=HERE.parent / "corpus"):
    for p in sorted(corpus.rglob("*")):
        if p.suffix == ".pdf":
            for i, page in enumerate(PdfReader(p).pages, 1):
                yield p.name, i, page.extract_text() or "", "current"
        # SOURCES.md is your provenance list, not content: never index it
        elif p.suffix in (".md", ".txt") and p.name != "SOURCES.md":
            text = p.read_text(encoding="utf-8")
            m = re.search(
                r"^status:\s*(\w+)", text, re.M
            )  # freshness metadata from the file header
            yield p.name, 1, text, (m.group(1) if m else "current")


def ingest():
    split = RecursiveCharacterTextSplitter(
        chunk_size=2000, chunk_overlap=300
    )  # ~500 tokens, 15% overlap
    rows = [
        {
            "chunk_id": f"{src}#p{page}-c{j}",
            "source": src,
            "page": page,
            "status": status,
            "text": chunk,
        }
        for src, page, text, status in load()
        for j, chunk in enumerate(split.split_text(text))
    ]
    db = MilvusClient(str(HERE / DB))
    if db.has_collection(COL):
        db.drop_collection(COL)
    dim = len(embed(["probe"], "passage")[0])
    db.create_collection(COL, dimension=dim, metric_type="COSINE")
    for k in range(0, len(rows), 16):
        batch = rows[k : k + 16]
        vecs = embed([r["text"] for r in batch], "passage")
        db.insert(
            COL,
            [
                {"id": k + n, "vector": v, **r}
                for n, (r, v) in enumerate(zip(batch, vecs))
            ],
        )
    print(f"indexed {len(rows)} chunks")


def retrieve(q, k=5, current_only=False):
    db = MilvusClient(str(HERE / DB))
    db.load_collection(COL)  # a reopened Milvus Lite collection starts out released
    hits = db.search(
        COL,
        data=embed([q], "query"),
        limit=k,
        output_fields=["chunk_id", "source", "page", "status", "text"],
        filter='status == "current"' if current_only else "",
    )[0]
    return [h["entity"] for h in hits]


def answer(q, current_only=False):
    ctx = retrieve(q, current_only=current_only)
    context = "\n\n".join(
        f"[{i}] ({c['chunk_id']}) {c['text']}" for i, c in enumerate(ctx, 1)
    )
    msgs = [
        {
            "role": "system",
            "content": "Answer only from the numbered context. Cite every claim like [2]. "
            "If the context does not contain the answer, say you don't know.",
        },
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {q}"},
    ]
    # 1.0 / 0.95 are the Nemotron 3 Super model card's recommended values for all tasks
    out = NIM.chat.completions.create(
        model=LLM,
        messages=msgs,
        temperature=1.0,
        top_p=0.95,
        max_tokens=1024,
        # A cited answer from given context needs no reasoning, and reasoning would eat max_tokens
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    text = out.choices[0].message.content
    if (
        not text
    ):  # budget ran out before the answer: fail loudly, don't score an empty answer
        raise RuntimeError(f"empty reply, finish_reason={out.choices[0].finish_reason}")
    return text, [(c["chunk_id"], c["status"]) for c in ctx]


if __name__ == "__main__":
    if sys.argv[1] == "ingest":
        ingest()
    else:
        current = sys.argv[1] == "ask-current"
        text, retrieved = answer(" ".join(sys.argv[2:]), current_only=current)
        print(text, "\n\nretrieved:", retrieved)
