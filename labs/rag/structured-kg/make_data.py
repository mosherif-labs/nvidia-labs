import random, sqlite3
from datetime import date, timedelta

random.seed(7)
COUNTRIES = ["US", "GB", "DE", "AE", "PA", "CY", "SG", "MX"]
db = sqlite3.connect("aml.db")
db.executescript("""
DROP TABLE IF EXISTS transactions; DROP TABLE IF EXISTS accounts;
DROP TABLE IF EXISTS customers;    DROP TABLE IF EXISTS counterparties;
CREATE TABLE customers (customer_id TEXT PRIMARY KEY, name TEXT, country TEXT, risk_rating TEXT);
CREATE TABLE accounts (account_id TEXT PRIMARY KEY, customer_id TEXT REFERENCES customers(customer_id),
                       opened TEXT, flagged INTEGER DEFAULT 0);
CREATE TABLE counterparties (counterparty_id TEXT PRIMARY KEY, name TEXT, country TEXT);
CREATE TABLE transactions (txn_id INTEGER PRIMARY KEY, from_account TEXT REFERENCES accounts(account_id),
                           to_party TEXT, amount REAL, currency TEXT, ts TEXT, channel TEXT);
""")
today = date.today()
day = lambda d: str(today - timedelta(days=d))
cust = [
    (
        f"C{i:03}",
        f"Customer {i}",
        random.choice(COUNTRIES),
        random.choice(["low", "medium", "high"]),
    )
    for i in range(1, 41)
]
accts = [
    (f"A{i:04}", random.choice(cust)[0], day(random.randint(30, 2000)), 0)
    for i in range(1, 61)
]
cps = [
    (f"X{i:03}", f"Counterparty {i} Ltd", random.choice(COUNTRIES))
    for i in range(1, 31)
]
db.executemany("INSERT INTO customers VALUES (?,?,?,?)", cust)
db.executemany("INSERT INTO accounts VALUES (?,?,?,?)", accts)
db.executemany("INSERT INTO counterparties VALUES (?,?,?)", cps)

parties = [a[0] for a in accts] + [c[0] for c in cps]
partners = {a[0]: random.sample(parties, 2) for a in accts}
tx = [
    (
        None,
        a,
        random.choice(partners[a]),
        round(random.lognormvariate(7, 1.2), 2),
        "USD",
        day(random.randint(0, 180)),
        random.choice(["wire", "ach", "card"]),
    )
    for a in random.choices(list(partners), k=3000)
]
# planted: flagged A0007 -> mules A0011, A0012 -> offshore X005 (Panama); structuring into A0012
tx += [
    (None, "A0007", m, 48_000.0, "USD", day(d), "wire")
    for m, d in (("A0011", 20), ("A0012", 19))
]
tx += [
    (None, m, "X005", 47_500.0, "USD", day(d), "wire")
    for m, d in (("A0011", 15), ("A0012", 14))
]
tx += [
    (
        None,
        f"A{random.randint(20, 60):04}",
        "A0012",
        round(random.uniform(9000, 9900), 2),
        "USD",
        day(random.randint(5, 12)),
        "ach",
    )
    for _ in range(8)
]
db.executemany("INSERT INTO transactions VALUES (?,?,?,?,?,?,?)", tx)
db.execute("UPDATE accounts SET flagged = 1 WHERE account_id = 'A0007'")
db.execute("UPDATE counterparties SET country = 'PA' WHERE counterparty_id = 'X005'")
db.commit()
print(db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0], "transactions")
