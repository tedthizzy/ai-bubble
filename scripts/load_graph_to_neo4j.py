#!/usr/bin/env python
"""Load the capital-exposure graph CSVs into the production Neo4j store + run analytics.

Reads data/graph/capital_exposure_{nodes,edges}.csv, MERGEs them into Neo4j under
the schema (constraints/indexes), then runs native-Cypher analytics and writes the
result to data/graph/neo4j_analytics.json. Connection comes from .env via
bubble.config.settings (NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase

from bubble.config import settings
from bubble.graph import neo4j_loader as nl


def _load_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def main() -> None:
    graph_dir = Path("data/graph")
    nodes = _load_csv(graph_dir / "capital_exposure_nodes.csv")
    edges = _load_csv(graph_dir / "capital_exposure_edges.csv")
    print(f"Read {len(nodes)} nodes, {len(edges)} edges from {graph_dir}")

    driver = GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
    try:
        driver.verify_connectivity()
        load = nl.load_graph(driver, nodes, edges, database=settings.neo4j_database)
        print("Load:", json.dumps(load, indent=2))
        analytics = nl.query_analytics(driver, database=settings.neo4j_database)
    finally:
        driver.close()

    out = {"load": load, "analytics": analytics}
    (graph_dir / "neo4j_analytics.json").write_text(json.dumps(out, indent=2, default=str))
    print("Top systemic nodes (by incident notional, from Neo4j):")
    for row in analytics["top_systemic_nodes_by_notional"][:10]:
        print(f"  {row.get('name')}: degree={row.get('degree')} notional={row.get('incident_notional')}")
    print("AI-infra mass:", analytics["ai_infra_mass"])
    print(f"Wrote {graph_dir / 'neo4j_analytics.json'}")


if __name__ == "__main__":
    main()
