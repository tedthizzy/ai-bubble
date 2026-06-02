"""Cluster interest-coverage / DSCR from source-backed issuer financials.

The Burry cash-flow mismatch question for the AI-direct cluster: can the issuers
cover their debt service out of operations? Computed only from source-backed
figures; issuers missing the needed inputs are named, not assumed.
"""

from __future__ import annotations

from bubble.analysis.cluster_dscr import IssuerFinancials, compute_cluster_interest_coverage


def _issuer(
    entity: str,
    *,
    ebitda: float | None = None,
    operating_income: float | None = None,
    revenue: float | None = None,
    annual_interest: float | None = None,
    annual_debt_service: float | None = None,
    source_backed: bool = True,
) -> IssuerFinancials:
    return IssuerFinancials(
        entity=entity,
        revenue_usd=revenue,
        ebitda_usd=ebitda,
        operating_income_usd=operating_income,
        annual_interest_expense_usd=annual_interest,
        annual_debt_service_usd=annual_debt_service,
        source_backed=source_backed,
    )


def test_blocks_when_no_source_backed_issuers() -> None:
    result = compute_cluster_interest_coverage(
        [_issuer("X", ebitda=1.0, annual_interest=1.0, source_backed=False)]
    )
    assert result["status"] == "blocked_no_source_backed_inputs"
    assert result["issuers_with_usable_inputs"] == 0


def test_loss_making_cluster_coverage_is_below_one() -> None:
    # Two loss-making issuers (negative EBITDA) with real interest expense.
    issuers = [
        _issuer("TeraWulf", ebitda=-50_000_000, annual_interest=200_000_000),
        _issuer("IREN", ebitda=-30_000_000, annual_interest=100_000_000),
    ]
    result = compute_cluster_interest_coverage(issuers)

    assert result["status"] == "source_backed"
    assert result["issuers_with_usable_inputs"] == 2
    assert result["aggregate_ebitda_usd"] == -80_000_000
    assert result["aggregate_annual_interest_usd"] == 300_000_000
    # Negative EBITDA over positive interest -> coverage well below 1 (negative).
    assert result["cluster_ebitda_interest_coverage"] < 0
    assert result["issuers_with_ebitda_coverage_below_1"] == 2
    assert result["loss_making_issuer_count"] == 2


def test_positive_coverage_issuer_counted_correctly() -> None:
    issuers = [
        _issuer("Profitable", ebitda=500_000_000, annual_interest=100_000_000),  # 5.0x
        _issuer("Thin", ebitda=80_000_000, annual_interest=100_000_000),  # 0.8x < 1
    ]
    result = compute_cluster_interest_coverage(issuers)

    assert result["cluster_ebitda_interest_coverage"] == round(580_000_000 / 200_000_000, 2)
    assert result["issuers_with_ebitda_coverage_below_1"] == 1
    assert result["loss_making_issuer_count"] == 0


def test_names_issuers_excluded_for_missing_inputs() -> None:
    issuers = [
        _issuer("HasInputs", ebitda=-10.0, annual_interest=100.0),
        _issuer("NoInterest", ebitda=-10.0),  # missing interest -> excluded from coverage
        _issuer("NoEbitda", annual_interest=100.0),  # missing ebitda -> excluded
    ]
    result = compute_cluster_interest_coverage(issuers)

    assert result["issuers_with_usable_inputs"] == 1
    excluded = {e["entity"]: e["missing"] for e in result["issuers_excluded_missing_inputs"]}
    assert "annual_interest_expense_usd" in excluded["NoInterest"]
    assert "ebitda_usd" in excluded["NoEbitda"]


def test_interest_to_revenue_burden_when_revenue_present() -> None:
    issuers = [
        _issuer("A", ebitda=-10.0, revenue=1_000_000_000, annual_interest=300_000_000),
    ]
    result = compute_cluster_interest_coverage(issuers)
    # 30% of revenue consumed by interest alone.
    assert result["aggregate_interest_to_revenue_pct"] == 30.0
