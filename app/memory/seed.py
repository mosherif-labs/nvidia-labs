import sys, time
from app.memory.memory import open_store, remember, recall

QUERY = "structuring case closed after review"

SEMANTIC = [  # facts (synthetic)
    "Northwind Trading's account ACC-11 is owned by a director who also controls Orbit Trading Ltd.",
    "Branch 12 has seen three structuring cases this quarter.",
    "Blue Harbor Imports regularly wires to a high-risk jurisdiction for its shipping business.",
    "Maple Dental runs payroll on the 1st of every month.",
    "POL-05: a human investigator must approve any SAR before filing.",
]
EPISODIC = [  # what happened (alert -> route -> outcome)
    "A-1001 (cash deposits just under 10,000) -> escalated as structuring under POL-01",
    "A-1002 (high-risk wires) -> enhanced due diligence opened, 5 business days",
    "A-1003 (equal payroll payments) -> closed with a payroll note under POL-04",
]

with open_store() as store:
    if sys.argv[1:2] == ["recall"]:  # seed.py recall [query]: recall only, no re-seed
        print(recall(store, "episodic", " ".join(sys.argv[2:]) or QUERY))
        sys.exit()
    store.setup()  # creates the tables (and pgvector index) once
    for f in SEMANTIC:
        remember(store, "semantic", f)
    for e in EPISODIC:
        remember(store, "episodic", e)
    # Two memories that match "structuring" equally well; one untouched for 7 days.
    remember(
        store,
        "episodic",
        "A-0901 structuring case, closed after review",
        last_accessed=time.time() - 7 * 24 * 3600,
    )
    remember(store, "episodic", "A-0902 structuring case, closed after review")
    print(recall(store, "episodic", QUERY))
