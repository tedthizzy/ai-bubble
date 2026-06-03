"""Weighted-PageRank systemic centrality."""

from __future__ import annotations

from bubble.analysis.graph_centrality import weighted_pagerank


def _edge(s, t, name_s=None, name_t=None, notional=None):
    return {
        "source_id": s,
        "target_id": t,
        "source_name": name_s or s,
        "target_name": name_t or t,
        "notional_usd": notional,
    }


def test_blocks_no_edges() -> None:
    assert weighted_pagerank([])["status"] == "blocked_no_edges"


def test_hub_node_ranks_highest() -> None:
    # A star: many sources point at one hub -> hub has highest PageRank.
    edges = [_edge(f"src{i}", "HUB", name_t="NVIDIA") for i in range(6)]
    out = weighted_pagerank(edges)
    assert out["status"] == "source_backed"
    assert out["node_count"] == 7
    assert out["top_systemic_nodes"][0]["node_id"] == "HUB"
    assert out["top_systemic_nodes"][0]["name"] == "NVIDIA"


def test_deterministic_and_self_loops_ignored() -> None:
    edges = [_edge("A", "B"), _edge("B", "C"), _edge("C", "B"), _edge("X", "X")]
    out1 = weighted_pagerank(edges)
    out2 = weighted_pagerank(edges)
    assert out1["top_systemic_nodes"] == out2["top_systemic_nodes"]
    # Self-loop X->X is ignored, so X never appears.
    names = {n["node_id"] for n in out1["top_systemic_nodes"]}
    assert "X" not in names


def test_notional_weighting_splits_rank_toward_heavy_edge() -> None:
    # A splits its rank between B (heavy) and C (light); B should get the larger share.
    edges = [
        _edge("A", "B", notional=50_000_000_000),
        _edge("A", "C", notional=1_000_000),
    ]
    out = weighted_pagerank(edges)
    scores = {n["node_id"]: n["centrality"] for n in out["top_systemic_nodes"]}
    assert scores["B"] > scores["C"]
