"""Builds etl/inputs/: real PDFs, a policy table, a note with seeded fake PII, and planted duplicates."""

import csv, json, pathlib, random, shutil

IN = pathlib.Path("inputs")
IN.mkdir(exist_ok=True)
pdfs = sorted(pathlib.Path("../corpus/public").glob("*.pdf"))[:3]
for p in pdfs:
    shutil.copy(p, IN / p.name)
shutil.copy(pdfs[0], IN / f"copy_of_{pdfs[0].name}")  # planted duplicate file

random.seed(27)
with open(IN / "policy_table.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["jurisdiction", "risk_rating", "edd_required", "review_cycle_months"])
    for j in ["US", "GB", "DE", "AE", "PA", "CY", "SG", "MX", "CH", "HK", "NG", "KY"]:
        risk = random.choice(["low", "medium", "high"])
        w.writerow(
            [j, risk, risk == "high", {"low": 36, "medium": 24, "high": 12}[risk]]
        )

# All invented. Test-number card, ISO example IBANs, a documentation IP range, example.com emails.
SEEDS = {
    "names": ["Marek Holloway", "Priya Raman", "Tomas Lindqvist"],
    "emails": ["m.holloway@example.com", "priya.raman@example.org"],
    "phones": ["+44 20 7946 0958", "+1 202-555-0147"],
    "ibans": ["GB82 WEST 1234 5698 7654 32", "DE89 3704 0044 0532 0130 00"],
    "card": ["4111 1111 1111 1111"],
    "ssn": ["512-48-3907"],
    "ip": ["203.0.113.42"],
    "accounts": ["ACC-00482913", "ACC-00591027"],
}
s = SEEDS
note = f"""Case note, alert A-2231 (synthetic)

Subject {s["names"][0]} (email {s["emails"][0]}, phone {s["phones"][0]}) holds internal
account {s["accounts"][0]} and received four cash deposits just under the reporting threshold.
Funds moved to IBAN {s["ibans"][0]} and then to {s["ibans"][1]}, held by {s["names"][1]}
({s["emails"][1]}, {s["phones"][1]}). A card, {s["card"][0]}, was used online
from IP {s["ip"][0]}. The second subject's SSN on file is {s["ssn"][0]}; linked account
{s["accounts"][1]}. Reviewed by {s["names"][2]}. Recommendation: escalate to the MLRO.
"""
(IN / "case_notes_synthetic.md").write_text(note, encoding="utf-8")
json.dump(
    [v for vs in SEEDS.values() for v in vs], open("pii_seeds.json", "w"), indent=2
)

para = (
    "Policy 4.2: cash deposits structured to stay below the reporting threshold must be "
    "escalated to the MLRO within one business day, whatever the customer's risk rating."
)
for name in ("policy_extract_a.md", "policy_extract_b.md"):  # same text, two files
    (IN / name).write_text(para + "\n", encoding="utf-8")
print(sorted(x.name for x in IN.iterdir()))
