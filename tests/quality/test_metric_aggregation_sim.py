"""Tests for the read-only metric-aggregation simulator.

Fixture-based: synthetic approved-decision rows. Compares grouping strategies the
way the report's final-metric aggregation would, without touching live data.
"""

from __future__ import annotations

from bubble.quality.metric_aggregation_sim import aggregate_by, simulate


def _rows() -> list[dict[str, str]]:
    return [
        {"content_hash": "h1", "supported_amount_usd": "100", "metric_group_id": "g1"},
        {"content_hash": "h1", "supported_amount_usd": "100", "metric_group_id": "g2"},  # dup
        {"content_hash": "h2", "supported_amount_usd": "50", "metric_group_id": "g3"},
    ]


def test_aggregate_by_collapses_same_key_uses_max_per_group() -> None:
    res = aggregate_by(_rows(), ("content_hash", "supported_amount_usd"), strategy="hash+amount")

    assert res.strategy == "hash+amount"
    assert res.group_count == 2  # (h1,100) and (h2,50)
    assert res.total_usd == 150.0  # 100 + 50 (the duplicate h1/100 collapses)


def test_aggregate_by_metric_group_baseline_counts_each_group() -> None:
    res = aggregate_by(_rows(), ("metric_group_id",), strategy="metric_group_id")

    assert res.group_count == 3
    assert res.total_usd == 250.0  # 100 + 100 + 50 (no cross-group dedup)


def test_simulate_computes_deltas_vs_first_strategy() -> None:
    res = simulate(
        _rows(),
        [
            ("metric_group_id", ("metric_group_id",)),
            ("hash+amount", ("content_hash", "supported_amount_usd")),
        ],
    )

    assert res[0].strategy == "metric_group_id"
    assert res[0].total_usd == 250.0
    assert res[0].delta_vs_baseline_usd == 0.0
    assert res[1].strategy == "hash+amount"
    assert res[1].total_usd == 150.0
    assert res[1].delta_vs_baseline_usd == -100.0
