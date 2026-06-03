"""Verified financed-cluster extension."""

from __future__ import annotations

from bubble.analysis.cluster_extension import aggregate_cluster_extension


def _m(name, *, cluster=True, recourse=None, total=None, overall="source_backed", rev=None):
    return {
        "name": name,
        "in_financed_cluster": cluster,
        "verified_recourse_debt_usd": recourse,
        "verified_total_debt_usd": total,
        "verified_revenue_usd": rev,
        "overall": overall,
    }


def test_blocks_without_confirmed_members() -> None:
    out = aggregate_cluster_extension([_m("X", cluster=False)])
    assert out["status"] == "blocked_no_confirmed_new_members"


def test_recourse_disentangled_from_jv() -> None:
    out = aggregate_cluster_extension(
        [
            _m("Crusoe", recourse=1_150_000_000, total=10_750_000_000),
            _m("EdgeConneX", recourse=5_500_000_000, total=None),
            _m("Edged", cluster=False, total=2_000_000_000, overall="partially_source_backed"),
        ]
    )
    assert out["status"] == "source_backed"
    assert out["member_count"] == 2  # Edged excluded (not in cluster)
    # Recourse sums only the recourse slice, not the JV-inflated total.
    assert out["new_recourse_debt_usd"] == 6_650_000_000
    assert out["new_associated_debt_usd"] == 10_750_000_000
    # EdgeConneX (5.5B recourse) ranks above Crusoe (1.15B).
    assert out["members"][0]["name"] == "EdgeConneX"
    assert "cluster_extends_by_2_verified_members" in out["extension_read"]
