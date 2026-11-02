import csv, datetime, hashlib, json, pathlib, re, sys, unicodedata
from collections import defaultdict
from pypdf import PdfReader
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_anonymizer import AnonymizerEngine
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pymilvus import MilvusClient

sys.path.append("../baseline")
from baseline import embed, EMBED

SRC, DB, COL, MANIFEST = (
    pathlib.Path("inputs"),
    "etl.db",
    "aml_etl",
    pathlib.Path("manifest.json"),
)
ENTITIES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "IBAN_CODE",
    "CREDIT_CARD",
    "US_SSN",
    "IP_ADDRESS",
]
analyzer, anonymizer = AnalyzerEngine(), AnonymizerEngine()

# Nothing built in knows the bank's internal account format
analyzer.registry.add_recognizer(
    PatternRecognizer(
        supported_entity="ACCOUNT_ID",
        patterns=[Pattern(name="acc_id", regex=r"\bACC-\d{8}\b", score=0.9)],
    )
)
ENTITIES.append("ACCOUNT_ID")
split = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=300)


def extract(p):  # -> [(page, text)]
    if p.suffix == ".pdf":
        return [
            (i, pg.extract_text() or "") for i, pg in enumerate(PdfReader(p).pages, 1)
        ]
    if p.suffix == ".csv":  # each row becomes one self-describing line
        rows = csv.DictReader(p.open(encoding="utf-8"))
        return [
            (1, "\n".join("; ".join(f"{k}: {v}" for k, v in r.items()) for r in rows))
        ]
    return [(1, p.read_text(encoding="utf-8"))]


def clean(t):
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"-\n(\w)", r"\1", t)  # re-join words hyphenated across lines
    t = re.sub(r"\n{3,}", "\n\n", t)
    return re.sub(r"[ \t]+", " ", t).strip()


def redact(t):
    hits = analyzer.analyze(text=t, entities=ENTITIES, language="en")
    return anonymizer.anonymize(text=t, analyzer_results=hits).text, len(hits)


def pk(content_hash):  # one row per distinct chunk text: duplicates share a key
    return int(content_hash[:15], 16)


def where(manifest):  # content hash -> every "file#pPAGE" that contains it
    w = defaultdict(set)
    for name, f in manifest.items():
        for h, page in f["chunks"]:
            w[h].add(f"{name}#p{page}")
    return {h: sorted(v) for h, v in w.items()}


def run():
    old = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    db = MilvusClient(DB)
    if not db.has_collection(COL):
        db.create_collection(COL, dimension=2048, metric_type="COSINE")
    db.load_collection(COL)  # a reopened Milvus Lite collection starts out released
    new, fresh = {}, {}  # file -> {digest, chunks: [[hash, page]]}; hash -> text
    stats = dict(skipped=0, processed=0, pii=0)
    for p in sorted(SRC.iterdir()):
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        if (
            old.get(p.name, {}).get("digest") == digest
        ):  # unchanged: no extract, no embed
            new[p.name] = old[p.name]
            stats["skipped"] += 1
            continue
        chunks = []
        for page, text in extract(p):
            text, n = redact(clean(text))
            stats["pii"] += n
            for c in split.split_text(text):
                h = hashlib.sha256(re.sub(r"\W+", " ", c.lower()).encode()).hexdigest()
                chunks.append([h, page])
                fresh[h] = c
        new[p.name] = {"digest": digest, "chunks": chunks}
        stats["processed"] += 1

    was, now = where(old), where(new)
    gone = was.keys() - now.keys()  # no current file contains it: delete
    added = now.keys() - was.keys()  # never indexed: embed it
    moved = {
        h for h in now.keys() & was.keys() if now[h] != was[h]
    }  # same text, new sources
    if gone:
        db.delete(COL, ids=[pk(h) for h in gone])
    texts, vecs = {h: fresh[h] for h in added}, {}
    if moved:  # reuse the stored text and vector: no embedding call
        for r in db.get(
            COL,
            ids=[pk(h) for h in moved],
            output_fields=["content_hash", "text", "vector"],
        ):
            texts[r["content_hash"]], vecs[r["content_hash"]] = r["text"], r["vector"]
    todo = sorted(added)
    for k in range(0, len(todo), 16):
        batch = todo[k : k + 16]
        vecs.update(zip(batch, embed([texts[h] for h in batch], "passage")))
    rows = [
        dict(
            id=pk(h),
            chunk_id=h[:16],
            doc_id=now[h][0].split("#")[0],  # cite the first source...
            sources=", ".join(now[h]),  # ...and keep every copy's location
            text=texts[h],
            content_hash=h,
            embed_model=EMBED,
            ingested_at=datetime.date.today().isoformat(),
            vector=vecs[h],
        )
        for h in sorted(added | moved)
    ]
    for k in range(0, len(rows), 64):
        db.upsert(COL, rows[k : k + 64])
    stats.update(
        embedded=len(added),
        relinked=len(moved),
        deleted=len(gone),
        dups=sum(len(v) - 1 for v in now.values()),
    )
    MANIFEST.write_text(json.dumps(new, indent=2))
    print(stats)


if __name__ == "__main__":
    run()
