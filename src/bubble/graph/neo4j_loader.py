"""Load the source-backed capital-exposure graph into a production Neo4j store.

Makes Neo4j the AUTHORITATIVE graph engine: it MERGEs the capital-exposure nodes
(entities, with exposure/roles) and edges (financing relationships, with notional/
type/relevance) under uniqueness constraints + indexes, in batched transactions,
then runs native-Cypher analytics (weighted-degree systemic centrality, AI-infra
subgraph, shared-counterparty contagion neighbourhoods) directly in the database.

The Cypher builders and the row-shaping logic are PURE and unit-tested (no live DB
needed for the gate); the driver-using ``load_*`` / ``query_*`` functions are run
against the live instance by ``scripts/load_graph_to_neo4j.py``. Native Cypher is
used (no GDS/APOC dependency) so it runs on a stock Neo4j Desktop instance; the
in-code weighted PageRank (graph_centrality.py) covers the GDS-algorithm side.
"""

from __future__ import annotations

from typing import Any

NODE_LABEL = "Entity"
REL_TYPE = "EXPOSED_TO"

# Schema: unique entity id + lookup indexes.
SCHEMA_CYPHER: tuple[str, ...] = (
    f"CREATE CONSTRAINT entity_id IF NOT EXISTS "
    f"FOR (n:{NODE_LABEL}) REQUIRE n.node_id IS UNIQUE",
    f"CREATE INDEX entity_name IF NOT EXISTS FOR (n:{NODE_LABEL}) ON (n.name)",
    f"CREATE INDEX entity_exposure IF NOT EXISTS FOR (n:{NODE_LABEL}) ON (n.exposure_usd)",
)

NODE_MERGE_CYPHER = (
    f"UNWIND $rows AS row "
    f"MERGE (n:{NODE_LABEL} {{node_id: row.node_id}}) "
    f"SET n.name = row.name, n.roles = row.roles, n.exposure_usd = row.exposure_usd, "
    f"n.deal_count = row.deal_count"
)

EDGE_MERGE_CYPHER = (
    f"UNWIND $rows AS row "
    f"MATCH (s:{NODE_LABEL} {{node_id: row.source_id}}) "
    f"MATCH (t:{NODE_LABEL} {{node_id: row.target_id}}) "
    f"MERGE (s)-[r:{REL_TYPE} {{rel_key: row.rel_key}}]->(t) "
    f"SET r.relationship_type = row.relationship_type, r.deal_type = row.deal_type, "
    f"r.notional_usd = row.notional_usd, r.ppa_capacity_mw = row.ppa_capacity_mw, "
    f"r.relevance_tags = row.relevance_tags, r.ai_infra = row.ai_infra"
)


def _num(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def node_row(raw: dict[str, Any]) -> dict[str, Any]:
    """Shape a capital_exposure_nodes.csv row into a Neo4j MERGE parameter row."""

    return {
        "node_id": str(raw.get("node_id") or "").strip(),
        "name": str(raw.get("name") or "").strip(),
        "roles": str(raw.get("roles") or "").strip(),
        "exposure_usd": _num(raw.get("exposure_usd")),
        "deal_count": int(_num(raw.get("deal_count"))),
    }


def edge_row(raw: dict[str, Any]) -> dict[str, Any]:
    """Shape a capital_exposure_edges.csv row into a Neo4j MERGE parameter row."""

    src = str(raw.get("source_id") or "").strip()
    tgt = str(raw.get("target_id") or "").strip()
    rel = str(raw.get("relationship_type") or "").strip()
    deal_type = str(raw.get("deal_type") or "").strip()
    tags = str(raw.get("relevance_tags") or "")
    return {
        "source_id": src,
        "target_id": tgt,
        "relationship_type": rel,
        "deal_type": deal_type,
        "notional_usd": _num(raw.get("notional_usd")),
        "ppa_capacity_mw": _num(raw.get("ppa_capacity_mw")),
        "relevance_tags": tags,
        "ai_infra": "direct:" in tags or "watchlist:" in tags,
        # Stable key so MERGE is idempotent per (src,tgt,type,deal_type).
        "rel_key": f"{src}|{tgt}|{rel}|{deal_type}",
    }


def valid_node(row: dict[str, Any]) -> bool:
    return bool(row.get("node_id"))


def valid_edge(row: dict[str, Any]) -> bool:
    return bool(row.get("source_id")) and bool(row.get("target_id")) and (
        row.get("source_id") != row.get("target_id")
    )


def _batches(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


# --- Native-Cypher analytics (no GDS/APOC) ---

# Weighted-degree systemic centrality: a node's incident notional + degree.
TOP_SYSTEMIC_CYPHER = (
    f"MATCH (n:{NODE_LABEL})-[r:{REL_TYPE}]-() "
    f"WITH n, count(r) AS degree, sum(coalesce(r.notional_usd, 0)) AS incident_notional "
    f"RETURN n.node_id AS node_id, n.name AS name, degree, incident_notional "
    f"ORDER BY incident_notional DESC, degree DESC LIMIT $limit"
)

# AI-infra subgraph mass.
AI_INFRA_MASS_CYPHER = (
    f"MATCH ()-[r:{REL_TYPE}]->() WHERE r.ai_infra "
    f"RETURN count(r) AS ai_infra_edges, sum(coalesce(r.notional_usd, 0)) AS ai_infra_notional"
)

# Shared-counterparty contagion: counterparties touching the most distinct AI-infra issuers.
CONTAGION_HUBS_CYPHER = (
    f"MATCH (issuer:{NODE_LABEL})-[r:{REL_TYPE}]->(cp:{NODE_LABEL}) WHERE r.ai_infra "
    f"WITH cp, count(DISTINCT issuer) AS issuer_count, collect(DISTINCT issuer.name)[..8] AS issuers "
    f"WHERE issuer_count > 1 "
    f"RETURN cp.name AS counterparty, issuer_count, issuers "
    f"ORDER BY issuer_count DESC LIMIT $limit"
)


def load_graph(
    driver: Any,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    database: str = "neo4j",
    batch_size: int = 1000,
) -> dict[str, Any]:
    """Load nodes + edges into Neo4j under the schema; return load counts (live DB)."""

    node_rows = [node_row(n) for n in nodes]
    node_rows = [n for n in node_rows if valid_node(n)]
    edge_rows = [edge_row(e) for e in edges]
    edge_rows = [e for e in edge_rows if valid_edge(e)]

    with driver.session(database=database) as session:
        for stmt in SCHEMA_CYPHER:
            session.run(stmt)
        for batch in _batches(node_rows, batch_size):
            session.run(NODE_MERGE_CYPHER, rows=batch)
        for batch in _batches(edge_rows, batch_size):
            session.run(EDGE_MERGE_CYPHER, rows=batch)
        node_count = session.run(f"MATCH (n:{NODE_LABEL}) RETURN count(n) AS c").single()["c"]
        edge_count = session.run(f"MATCH ()-[r:{REL_TYPE}]->() RETURN count(r) AS c").single()["c"]

    return {
        "status": "loaded",
        "nodes_sent": len(node_rows),
        "edges_sent": len(edge_rows),
        "nodes_in_db": node_count,
        "edges_in_db": edge_count,
    }


def query_analytics(driver: Any, *, database: str = "neo4j", limit: int = 15) -> dict[str, Any]:
    """Run the native-Cypher analytics against the loaded graph (live DB)."""

    with driver.session(database=database) as session:
        top = [dict(r) for r in session.run(TOP_SYSTEMIC_CYPHER, limit=limit)]
        mass = dict(session.run(AI_INFRA_MASS_CYPHER).single() or {})
        hubs = [dict(r) for r in session.run(CONTAGION_HUBS_CYPHER, limit=limit)]
    return {
        "top_systemic_nodes_by_notional": top,
        "ai_infra_mass": mass,
        "ai_infra_contagion_hubs": hubs,
    }
