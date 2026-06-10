"""Unsupervised cluster-discovery pipeline."""

from __future__ import annotations

from bubble.analysis import cluster_discovery as cd


def _issuer(name, rev, ebitda, net, debt, interest, cash):
    return {
        "entity": name,
        "revenue_usd": rev,
        "ebitda_usd": ebitda,
        "net_income_usd": net,
        "total_debt_usd": debt,
        "annual_interest_expense_usd": interest,
        "cash_and_equivalents_usd": cash,
    }


def test_feature_matrix_drops_incomplete() -> None:
    rows = [
        _issuer("A", 1000, 300, 100, 2000, 100, 200),
        _issuer("NoRev", 0, 0, 0, 100, 10, 10),  # rev<=0 -> dropped
        {"entity": "NoDebt", "revenue_usd": 500},  # debt None -> dropped
    ]
    names, feats, x = cd.build_feature_matrix(rows)
    assert names == ["A"]
    assert feats == cd.FEATURE_NAMES
    assert x.shape == (1, 5)
    # leverage = debt/rev = 2.0
    assert abs(x[0][0] - 2.0) < 1e-9


def test_retro_label_fragile_vs_healthy() -> None:
    fragile = {"leverage_debt_to_revenue": 3.0, "ebitda_margin": -0.2, "interest_coverage": 0.5}
    healthy = {"leverage_debt_to_revenue": 0.3, "ebitda_margin": 0.4, "interest_coverage": 8.0}
    assert cd._retro_label(fragile).startswith("cash_flow_negative_fragile")
    assert "high_leverage" in cd._retro_label(fragile)
    assert cd._retro_label(healthy).startswith("profitable_self_funding")


def test_discover_blocks_small_n() -> None:
    rows = [_issuer(f"E{i}", 1000, 100, 50, 500, 50, 100) for i in range(4)]
    assert cd.discover_structure(rows)["status"] == "blocked_insufficient_n"


def test_discover_separable_two_groups() -> None:
    # Group 1: healthy (high margin, low leverage). Group 2: fragile (negative margin, high leverage).
    healthy = [_issuer(f"H{i}", 1000, 350 + i * 10, 200, 300, 20, 400) for i in range(5)]
    fragile = [_issuer(f"F{i}", 1000, -150 - i * 10, -250, 3000, 250, 50) for i in range(5)]
    out = cd.discover_structure(healthy + fragile, bootstrap=30)
    assert out["status"] == "source_backed"
    assert out["n"] == 10
    # Two well-separated groups -> silhouette should be strong and k=2 chosen.
    assert out["chosen_k"] == 2
    assert out["chosen_k_silhouette"] > 0.5
    # The fragile cluster collects the F* names.
    frag = set(out["fragile_cluster_members"])
    assert all(name.startswith("F") for name in frag)
    assert len(frag) == 5
    assert "discovered_2_clusters" in out["discovery_read"]
