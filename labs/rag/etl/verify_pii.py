import json
from pymilvus import MilvusClient

seeds = json.load(
    open("pii_seeds.json", encoding="utf-8")
)  # ["Jane Q. Doe", "jane.doe@example.com", ...]
db = MilvusClient("etl.db")
db.load_collection("aml_etl")
texts = [
    r["text"]
    for r in db.query("aml_etl", filter="id >= 0", output_fields=["text"], limit=16384)
]
leaks = [s for s in seeds if any(s in t for t in texts)]
print(f"{len(seeds) - len(leaks)}/{len(seeds)} seeded values redacted")
print("LEAKED:", leaks)
