"""Entity-level utilization vs debt-service mismatch aggregation."""

from __future__ import annotations

from bubble.analysis.utilization_debt_service import aggregate_utilization_debt_service


def _rec(issuer, metrics, overall="source_backed"):
    return {"issuer": issuer, "verified_metrics": metrics, "overall": overall}


def test_blocks_without_source_backed() -> None:
    out = aggregate_utilization_debt_service(
        [_rec("X", {"annual_revenue_usd": 100}, overall="unreliable")]
    )
    assert out["status"] == "blocked_no_source_backed_utilization"


def test_contracted_coverage_below_1_read() -> None:
    out = aggregate_utilization_debt_service(
        [
            _rec(
                "Thinco",
                {
                    "contracted_revenue_run_rate_usd": 800,
                    "annual_debt_service_usd": 1000,  # coverage 0.8x
                    "contracted_or_committed_capacity_pct": 90,
                },
            ),
            _rec(
                "Weakco",
                {
                    "contracted_revenue_run_rate_usd": 500,
                    "annual_debt_service_usd": 1000,  # 0.5x
                },
            ),
        ]
    )
    assert out["status"] == "source_backed"
    assert out["issuers_with_contracted_coverage"] == 2
    assert out["issuers_contracted_coverage_below_1"] == 2
    assert out["median_contracted_coverage_ratio"] == 0.65
    # Both have full debt service and revenue below it -> the hard mismatch surfaces first.
    assert out["issuers_revenue_below_debt_service"] == 2
    assert "revenue_below_debt_service" in out["mismatch_read"]
    assert set(out["revenue_below_debt_service_issuers"]) == {"Thinco", "Weakco"}
    # break-even utilization = 90 / 0.8 = 112.5 (i.e. already underwater at full util)
    thinco = next(p for p in out["per_issuer"] if p["issuer"] == "Thinco")
    assert thinco["breakeven_utilization_pct"] == 112.5
    assert thinco["coverage_denominator"] == "debt_service"


def test_interest_only_fallback_labeled_and_not_in_break_stat() -> None:
    out = aggregate_utilization_debt_service(
        [
            _rec(
                "Revco",
                {
                    "annual_revenue_usd": 1200,  # no contracted rev -> total_revenue numerator
                    "annual_interest_expense_usd": 100,  # no debt service -> interest_only
                },
            )
        ]
    )
    p = out["per_issuer"][0]
    assert p["coverage_numerator"] == "total_revenue"
    assert p["coverage_denominator"] == "interest_only"
    assert p["coverage_ratio"] == 12.0
    # total-revenue/interest proxy must NOT count in the contracted break statistic.
    assert out["issuers_with_contracted_coverage"] == 0
    assert "indeterminate_contracted_coverage" in out["mismatch_read"]


def test_indeterminate_when_no_inputs() -> None:
    out = aggregate_utilization_debt_service([_rec("Empty", {})])
    assert out["status"] == "source_backed"
    assert out["per_issuer"][0]["coverage_ratio"] is None
    assert "indeterminate_contracted_coverage" in out["mismatch_read"]
