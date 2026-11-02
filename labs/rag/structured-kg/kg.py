import sys, sqlite3
import networkx as nx


def build_graph(db="aml.db"):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    G = nx.DiGraph()
    for cid, name, country, risk in con.execute("SELECT * FROM customers"):
        G.add_node(cid, kind="customer", name=name, country=country, risk=risk)
    for xid, name, country in con.execute("SELECT * FROM counterparties"):
        G.add_node(xid, kind="counterparty", name=name, country=country)
    for aid, cid, opened, flagged in con.execute("SELECT * FROM accounts"):
        G.add_node(aid, kind="account", flagged=bool(flagged))
        G.add_edge(cid, aid, rel="OWNS")
    for src, dst, n, total in con.execute(
        "SELECT from_account, to_party, COUNT(*), ROUND(SUM(amount), 2) FROM transactions GROUP BY 1, 2"
    ):
        G.add_edge(src, dst, rel="SENT_TO", n_txn=n, total=total)
    return G


def two_hops(G, node, radius=2):
    """Every node within `radius` hops of `node` (either direction), with one shortest path each."""
    paths = nx.single_source_shortest_path(
        G.to_undirected(as_view=True), node, cutoff=radius
    )
    return {n: p for n, p in paths.items() if n != node}


if __name__ == "__main__":
    G = build_graph()
    print(G.number_of_nodes(), "nodes,", G.number_of_edges(), "edges")
    ego = nx.ego_graph(G, sys.argv[1], radius=2, undirected=True)
    print(ego.number_of_nodes() - 1, "nodes within 2 hops")
    for n, p in sorted(two_hops(G, sys.argv[1]).items(), key=lambda kv: len(kv[1])):
        print(" -> ".join(p), G.nodes[n].get("country", ""))
