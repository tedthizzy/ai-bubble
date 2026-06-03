#!/usr/bin/env python
"""Run Neo4j Graph Data Science (GDS) over the loaded capital-exposure graph.

Computes the graph-theoretic structure the in-code analytics can only approximate:
  - betweenness centrality  -> structural CHOKEPOINTS (who sits on the most
    exposure-propagation paths) on BOTH the full graph and the ai_infra subgraph;
  - notional-weighted PageRank -> systemic IMPORTANCE;
  - Louvain community detection -> emergent COMMUNITY structure (count + modularity).

Writes handoffs/ai_gds_graph_analytics_<date>.json (a source-backed fixture; the
graph itself is MERGEd from the source-backed capital-exposure CSVs). Connection
comes from .env via bubble.config.settings. Requires the GDS plugin (see
scripts/install_gds_neo4j_desktop.sh). Re-runnable: projections are dropped first.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase

from bubble.config import settings

_OUT = Path("handoffs/ai_gds_graph_analytics_20260603.json")
_TOP_N = 15

_PROJECT_FULL = (
    "MATCH (s:Entity)-[r:EXPOSED_TO]->(t:Entity) "
    "RETURN gds.graph.project('expo', s, t, "
    "{relationshipProperties: {notional: coalesce(r.notional_usd, 0.0)}})"
)
_PROJECT_AI = (
    "MATCH (s:Entity)-[r:EXPOSED_TO]->(t:Entity) WHERE r.ai_infra = true "
    "RETURN gds.graph.project('ai', s, t, "
    "{relationshipProperties: {notional: coalesce(r.notional_usd, 0.0)}})"
)


def _drop(session: Any, name: str) -> None:
    session.run(
        "CALL gds.graph.exists($n) YIELD exists WITH exists WHERE exists "
        "CALL gds.graph.drop($n) YIELD graphName RETURN graphName",
        n=name,
    ).consume()


def _betweenness(session: Any, graph: str) -> list[dict[str, Any]]:
    rows = session.run(
        "CALL gds.betweenness.stream($g) YIELD nodeId, score "
        "WITH gds.util.asNode(nodeId) AS n, score WHERE score > 0 "
        "RETURN n.name AS name, n.roles AS roles, score "
        "ORDER BY score DESC LIMIT $k",
        g=graph,
        k=_TOP_N,
    )
    return [{"name": r["name"], "roles": r["roles"], "betweenness": round(r["score"], 1)} for r in rows]


def _pagerank(session: Any, graph: str) -> list[dict[str, Any]]:
    rows = session.run(
        "CALL gds.pageRank.stream($g, {relationshipWeightProperty: 'notional'}) "
        "YIELD nodeId, score WITH gds.util.asNode(nodeId) AS n, score "
        "RETURN n.name AS name, n.roles AS roles, score ORDER BY score DESC LIMIT $k",
        g=graph,
        k=_TOP_N,
    )
    return [{"name": r["name"], "roles": r["roles"], "pagerank": round(r["score"], 4)} for r in rows]


def _louvain(session: Any, graph: str) -> dict[str, Any]:
    rec = session.run(
        "CALL gds.louvain.stats($g) YIELD communityCount, modularity "
        "RETURN communityCount, modularity",
        g=graph,
    ).single()
    return {
        "community_count": rec["communityCount"] if rec else None,
        "modularity": round(rec["modularity"], 4) if rec else None,
    }


def _node_rank(rows: list[dict[str, Any]], key: str, name_substr: str) -> dict[str, Any] | None:
    for i, r in enumerate(rows):
        if name_substr.lower() in str(r.get("name") or "").lower():
            return {"name": r["name"], "rank": i + 1, key: r.get(key)}
    return None


def _analyze(session: Any, graph: str, project_query: str) -> dict[str, Any]:
    _drop(session, graph)
    proj = session.run(project_query).single()
    betw = _betweenness(session, graph)
    return {
        "graph": graph,
        "node_count": proj[0]["nodeCount"] if proj else None,
        "relationship_count": proj[0]["relationshipCount"] if proj else None,
        "top_betweenness_chokepoints": betw,
        "top_pagerank_systemic": _pagerank(session, graph),
        "louvain": _louvain(session, graph),
        "coreweave_betweenness": _node_rank(betw, "betweenness", "coreweave"),
    }


def main() -> int:
    driver = GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
    try:
        driver.verify_connectivity()
        with driver.session(database=settings.neo4j_database) as session:
            ver = session.run("RETURN gds.version() AS v").single()["v"]
            payload = {
                "status": "source_backed",
                "gds_version": ver,
                "full_exposure_graph": _analyze(session, "expo", _PROJECT_FULL),
                "ai_infra_subgraph": _analyze(session, "ai", _PROJECT_AI),
            }
            _drop(session, "expo")
            _drop(session, "ai")
    finally:
        driver.close()

    _OUT.write_text(json.dumps(payload, indent=2))
    full = payload["full_exposure_graph"]
    ai = payload["ai_infra_subgraph"]
    print(f"GDS {ver}: wrote {_OUT}")
    print(f"  full graph: {full['node_count']} nodes; top chokepoint: "
          f"{full['top_betweenness_chokepoints'][0]['name'] if full['top_betweenness_chokepoints'] else 'n/a'}")
    print(f"  ai subgraph: {ai['node_count']} nodes; top chokepoint: "
          f"{ai['top_betweenness_chokepoints'][0]['name'] if ai['top_betweenness_chokepoints'] else 'n/a'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
