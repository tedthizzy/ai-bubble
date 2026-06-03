"""Neo4j loader: pure row-shaping + Cypher builders (no live DB)."""

from __future__ import annotations

from bubble.graph import neo4j_loader as nl


def test_node_row_shaping() -> None:
    row = nl.node_row(
        {"node_id": " e1 ", "name": "CoreWeave", "roles": "borrower", "exposure_usd": "1.5e9",
         "deal_count": "3"}
    )
    assert row == {
        "node_id": "e1",
        "name": "CoreWeave",
        "roles": "borrower",
        "exposure_usd": 1.5e9,
        "deal_count": 3,
    }
    assert nl.valid_node(row)
    assert not nl.valid_node(nl.node_row({"node_id": ""}))


def test_edge_row_shaping_and_ai_infra_flag() -> None:
    row = nl.edge_row(
        {
            "source_id": "e1",
            "target_id": "e2",
            "relationship_type": "OWES_OR_BORROWS_FROM",
            "deal_type": "debt_facility",
            "notional_usd": "25000000000",
            "ppa_capacity_mw": "",
            "relevance_tags": "direct:compute watchlist:nvidia",
        }
    )
    assert row["ai_infra"] is True
    assert row["rel_key"] == "e1|e2|OWES_OR_BORROWS_FROM|debt_facility"
    assert row["notional_usd"] == 25_000_000_000
    assert nl.valid_edge(row)


def test_edge_validation_rejects_self_loop_and_missing() -> None:
    assert not nl.valid_edge(nl.edge_row({"source_id": "x", "target_id": "x"}))
    assert not nl.valid_edge(nl.edge_row({"source_id": "x", "target_id": ""}))


def test_non_ai_edge_flag_false() -> None:
    row = nl.edge_row({"source_id": "a", "target_id": "b", "relevance_tags": "legalfamily:x"})
    assert row["ai_infra"] is False


def test_batching() -> None:
    rows = [{"i": i} for i in range(2500)]
    batches = nl._batches(rows, 1000)
    assert [len(b) for b in batches] == [1000, 1000, 500]


def test_schema_and_merge_cypher_are_wellformed() -> None:
    assert any("CONSTRAINT" in s for s in nl.SCHEMA_CYPHER)
    assert "UNWIND $rows" in nl.NODE_MERGE_CYPHER
    assert "MERGE" in nl.EDGE_MERGE_CYPHER
    assert "EXPOSED_TO" in nl.CONTAGION_HUBS_CYPHER
