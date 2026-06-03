"""Cluster-boundary test aggregation."""

from __future__ import annotations

from bubble.analysis.cluster_boundary import aggregate_cluster_boundary


def _rec(issuer, in_scope, overall="source_backed"):
    return {"issuer": issuer, "in_scope": in_scope, "overall": overall}


def test_blocks_without_source_backed() -> None:
    out = aggregate_cluster_boundary([_rec("X", "financed_ai_infra", overall="unreliable")])
    assert out["status"] == "blocked_no_source_backed_boundary"


def test_bounded_cluster_read() -> None:
    out = aggregate_cluster_boundary(
        [
            _rec("Bit Digital", "financed_ai_infra"),
            _rec("Galaxy Digital", "crypto_only_marginal_ai"),
            _rec("Bitdeer", "crypto_only_marginal_ai"),
            _rec("Stronghold", "crypto_only_marginal_ai"),
            _rec("Soluna", "crypto_only_marginal_ai"),
            _rec("Cango", "not_relevant"),
        ]
    )
    assert out["status"] == "source_backed"
    assert out["candidate_count"] == 6
    assert out["qualified_financed_ai_infra"] == ["Bit Digital"]
    assert out["qualify_rate_pct"] == round(100 / 6, 1)
    assert "cluster_is_bounded" in out["boundary_read"]


def test_extends_read_when_majority_qualify() -> None:
    out = aggregate_cluster_boundary(
        [
            _rec("A", "financed_ai_infra"),
            _rec("B", "financed_ai_infra"),
            _rec("C", "crypto_only_marginal_ai"),
        ]
    )
    assert "cluster_extends" in out["boundary_read"]
    assert out["scope_counts"]["financed_ai_infra"] == 2
