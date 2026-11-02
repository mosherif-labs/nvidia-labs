# Day 27 (W05 D01): structured data and an evidence graph

Code: [`labs/rag/structured-kg/`](../labs/rag/structured-kg/) · `make_data.py` (synthetic `aml.db`), `sql_tool.py` (read-only text-to-SQL), `kg.py` (NetworkX graph + 2-hop tool), `combined.py` + `questions.json` (SQL + KG + documents).

## §1 Bets

See [d27-rag-etl.md](d27-rag-etl.md) §1 (Bet C is scored in §6 here).

## §2 Data model

`customers` → own → `accounts` → send `transactions` → to accounts or external `counterparties`. 40 customers, 60 accounts, 30 counterparties, 3,012 transactions.

**Planted pattern (one sentence):** flagged **A0007** wires 48,000 each to mules **A0011** and **A0012**, both forward 47,500 to offshore counterparty **X005 (Panama)**, and A0012 also takes 8 ACH credits of 9,000–9,900 (structuring just under the 10,000 CTR threshold).

| Question type | Best source |
|---|---|
| Totals, counts, "how many under 10,000 in 30 days" | **SQL** |
| "Who is connected to A0007, within N hops, via whom" | **Graph** |
| "What does policy / FATF / FinCEN say" | **Documents** (RAG) |

## §3 Text-to-SQL

- The LLM sees the schema and returns one SELECT; `run_sql()` refuses anything that isn't a single `SELECT`/`WITH`, caps rows at 200, and runs on `file:aml.db?mode=ro` + `PRAGMA query_only`. Results are cached per question for 300 s.
- **Both guards, proven** (run on the synthetic DB):
  - `run_sql('DELETE FROM transactions')` → `ValueError: refused, not a single SELECT: 'DELETE FROM transactions'`
  - `ro_conn().execute('DELETE FROM transactions')` → `sqlite3.OperationalError: attempt to write a readonly database`
- The real control is the **connection** (read-only role / `mode=ro`), not the prompt. The regex and row cap are extra layers.
- **Live data through an API tool:** cache reference data (policy tables, country risk ratings, schema) for minutes to hours; cache an aggregate for a short TTL only when the answer says "as of <time>". **Never cache** anything an approval or SAR decision depends on at decision time (current balances, sanctions screening results, case status), and never cache across users with different entitlements.

## §4 Knowledge graph

Nodes: `customer`, `account`, `counterparty` (with country, risk, flagged). Edges: `OWNS` (customer → account) and one aggregated `SENT_TO` per (sender, receiver) with `n_txn` and `total`. **130 nodes, 192 edges.**

`uv run python kg.py A0007` → **28 nodes within 2 hops** (undirected). The ones that matter:

```
A0007 -> A0011            (mule 1)
A0007 -> A0012            (mule 2)
A0007 -> A0012 -> X005 PA (offshore counterparty, Panama)
A0007 -> C020 AE          (A0007's owner, UAE)
A0007 -> A0012 -> A0024, A0025, A0038, A0045, A0047, A0051, A0053, A0060, A0020 ...  (ACH senders into A0012 + its partners)
```

`two_hops()` keeps one shortest path per node, so X005 shows once, via A0012; A0011 → X005 is the second route (Cypher's `MATCH` returns both paths). `ego_graph` on a `DiGraph` without `undirected=True` would only follow money *sent*.

**Same question in Cypher (Neo4j):**

```cypher
MATCH p = (a:Account {id: 'A0007'})-[:SENT_TO|OWNS]-{1,2}(x)
RETURN DISTINCT x.id, [n IN nodes(p) | n.id] AS path
// older syntax: (a:Account {id:'A0007'})-[:SENT_TO|OWNS*1..2]-(x)
```

LLM-built KGs (NVIDIA blog): chunk text → LLM extracts entities and relations; still needs a **schema/ontology**, **entity consistency** ("USA" = "US" = "United States") and **enforced structured output**. Today's graph is built from tables, so no entity resolution was needed.

## §5 KG vs vector search

- **KG wins** for multi-hop relationships (A0007 → mule → offshore), questions about *connections* rather than *similar text*, and entity-centric aggregation (everything touching one account).
- **GraphRAG** = KG + vector retrieval: in today's questions the **graph** finds who is linked, **SQL** gives the amounts, **vectors** fetch the policy and typology text.
- **Cost of a KG:** schema design, entity resolution, and keeping it in sync with the source systems (another pipeline to monitor). A vector index just needs chunks.

## §6 Combined answers

```bash
cd nvidia-labs/labs/rag/structured-kg
uv run python make_data.py
uv run python combined.py | tee combined_answers.md
# Bet C: the same 3 against Day 13's docs-only baseline
cd ../baseline && uv run python baseline.py ask "A0007 is flagged. Who is within 2 hops, how much did it send in the last 30 days, and which policy applies?"
```

Ground truth from the synthetic DB (run today; dates are relative to the day `make_data.py` runs):

| Q | SQL truth | Only the graph knows |
|---|---|---|
| 1. A0007: 2 hops, sent in 30 days, policy | A0007 sent **106,646.50** in the last 30 days (96,000 of it the two planted wires) | that A0011/A0012 lead on to **X005 (PA)** |
| 2. A0012: small ACH credits, onward, policy | **11** ACH credits into A0012 in 30 days, **80,711.00** total (8 planted at 9,000–9,900) | A0012 → X005 onward, and that the senders are otherwise unconnected |
| 3. X005: who near A0007 paid it | A0011 **47,500**, A0012 **47,500** (plus A0043 7,539.09 and A0051 4,952.51 outside the pattern) | which payers are within 2 hops of A0007 |

Bet C expectation: the docs-only baseline can answer the **policy** part of each and **none** of the account facts (0 of 3 fully correct).

Strongest evidence for a regulator asking why A0012 looks like a mule: the **SQL rows** (exact amounts, dates, channels: verifiable records). Then the **KG path** (derived from those rows: shows the flow A0007 → A0012 → X005). Weakest: the **document chunk**: it says what structuring *is*, not that A0012 did it.

## §7 Financial-crime angle

A transaction graph is how investigators already think (fan-out, layering, round-tripping). Keeping SQL read-only and citing rows makes the agent's numbers auditable; letting an LLM write to the case database would not survive model risk review.
