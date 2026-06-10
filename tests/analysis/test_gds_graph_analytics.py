"""GDS graph-analytics aggregation."""

from __future__ import annotations

from bubble.analysis.gds_graph_analytics import aggregate_gds_analytics

_PAYLOAD = {
    "status": "source_backed",
    "gds_version": "2026.05.0",
    "full_exposure_graph": {
        "node_count": 5102,
        "relationship_count": 7617,
        "top_betweenness_chokepoints": [
            {
                "name": "Shell Energy North America (US), L.P.",
                "roles": ["seller"],
                "betweenness": 593947.7,
            },
            {
                "name": "Morgan Stanley Capital Group Inc.",
                "roles": ["buyer"],
                "betweenness": 550515.5,
            },
            {
                "name": "PACIFIC GAS AND ELECTRIC COMPANY",
                "roles": ["seller"],
                "betweenness": 416940.7,
            },
        ],
        "top_pagerank_systemic": [
            {"name": "JPMORGAN CHASE BANK, N.A.", "roles": ["lender"], "pagerank": 2.95},
        ],
        "louvain": {"community_count": 771, "modularity": 0.65},
        "coreweave_betweenness": None,
    },
    "ai_infra_subgraph": {
        "node_count": 216,
        "relationship_count": 232,
        "top_betweenness_chokepoints": [
            {"name": "AMAZON ENERGY LLC", "roles": ["buyer"], "betweenness": 161.0},
            {"name": "Microsoft Energy LLC", "roles": ["buyer"], "betweenness": 112.0},
            {"name": "CoreWeave", "roles": ["borrower"], "betweenness": 13.0},
        ],
        "top_pagerank_systemic": [
            {"name": "EQUINIX, INC.", "roles": ["lessor"], "pagerank": 0.53},
        ],
        "louvain": {"community_count": 28, "modularity": 0.7574},
        "coreweave_betweenness": {"name": "CoreWeave", "rank": 5, "betweenness": 13.0},
    },
}


def test_blocks_empty() -> None:
    assert aggregate_gds_analytics({})["status"] == "blocked_no_gds_analytics"


def test_aggregates_chokepoints_and_modularity() -> None:
    out = aggregate_gds_analytics(_PAYLOAD)
    assert out["status"] == "source_backed"
    assert out["gds_version"] == "2026.05.0"
    # top AI chokepoint is an energy-procurement intermediary
    ai = out["ai_subgraph"]
    assert ai["top_chokepoint"] == "AMAZON ENERGY LLC"
    assert ai["energy_chokepoints_in_top"] >= 2
    # modularity surfaced -> bounded community structure
    assert ai["modularity"] == 0.7574
    assert ai["strongly_modular"] is True


def test_coreweave_nuance_present() -> None:
    out = aggregate_gds_analytics(_PAYLOAD)
    assert out["coreweave_topological_rank"] == 5
    assert "financing" in out["coreweave_nuance"].lower()


def test_full_graph_systemic_is_banks() -> None:
    out = aggregate_gds_analytics(_PAYLOAD)
    assert "JPMORGAN" in out["full_graph"]["top_systemic_by_pagerank"][0]["name"]
