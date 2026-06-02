"""Cluster interest-coverage / DSCR from source-backed issuer financials.

Answers the Burry cash-flow-mismatch question for the AI-direct issuer cluster:
can these issuers service their debt out of operations? Every ratio is computed
only from source-backed figures; issuers missing the required inputs are named
and excluded rather than assumed. This is the source-backed counterpart to the
report's payback-case cash-flow mismatch (which is blocked when per-case inputs
are not disclosed).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IssuerFinancials:
    """Source-backed financials for one AI-direct issuer (USD, actual dollars)."""

    entity: str
    revenue_usd: float | None = None
    ebitda_usd: float | None = None
    operating_income_usd: float | None = None
    net_income_usd: float | None = None
    total_debt_usd: float | None = None
    annual_interest_expense_usd: float | None = None
    annual_debt_service_usd: float | None = None
    cash_and_equivalents_usd: float | None = None
    is_loss_making: bool | None = None
    period: str = ""
    source_uri: str = ""
    source_backed: bool = True


def _coverage_profit_proxy(issuer: IssuerFinancials) -> float | None:
    """Cash-generation proxy for coverage: EBITDA, else operating income."""

    if issuer.ebitda_usd is not None:
        return issuer.ebitda_usd
    return issuer.operating_income_usd


def compute_cluster_interest_coverage(
    issuers: list[IssuerFinancials],
    *,
    realistic_utilization_pct: float = 28.0,
) -> dict[str, Any]:
    """Cluster EBITDA/interest coverage + interest-to-revenue burden.

    Only source-backed issuers with both a cash-generation proxy (EBITDA or
    operating income) and annual interest expense contribute to the coverage
    ratio. Issuers missing an input are listed in
    ``issuers_excluded_missing_inputs`` with the specific missing fields.
    """

    usable: list[IssuerFinancials] = []
    excluded: list[dict[str, Any]] = []
    for issuer in issuers:
        if not issuer.source_backed:
            excluded.append({"entity": issuer.entity, "missing": ["not_source_backed"]})
            continue
        missing: list[str] = []
        if _coverage_profit_proxy(issuer) is None:
            missing.append("ebitda_usd")
        if issuer.annual_interest_expense_usd is None:
            missing.append("annual_interest_expense_usd")
        if missing:
            excluded.append({"entity": issuer.entity, "missing": missing})
        else:
            usable.append(issuer)

    if not usable:
        return {
            "status": "blocked_no_source_backed_inputs",
            "issuers_total": len(issuers),
            "issuers_with_usable_inputs": 0,
            "issuers_excluded_missing_inputs": excluded,
            "note": (
                "No source-backed cluster interest-coverage computed: no issuer has both a "
                "cash-generation proxy (EBITDA/operating income) and annual interest expense "
                "source-backed. Reported as an explicit gap, not an assumed ratio."
            ),
        }

    agg_profit = sum(float(_coverage_profit_proxy(i) or 0.0) for i in usable)
    agg_interest = sum(float(i.annual_interest_expense_usd or 0.0) for i in usable)
    per_issuer: list[dict[str, Any]] = []
    coverage_below_1 = 0
    loss_making = 0
    for issuer in usable:
        profit = float(_coverage_profit_proxy(issuer) or 0.0)
        interest = float(issuer.annual_interest_expense_usd or 0.0)
        coverage = round(profit / interest, 2) if interest > 0 else None
        if coverage is not None and coverage < 1.0:
            coverage_below_1 += 1
        if profit < 0:
            loss_making += 1
        per_issuer.append(
            {
                "entity": issuer.entity,
                "ebitda_or_operating_income_usd": profit,
                "annual_interest_expense_usd": interest,
                "interest_coverage": coverage,
                "is_loss_making": profit < 0,
                "period": issuer.period,
                "source_uri": issuer.source_uri,
            }
        )

    cluster_coverage = round(agg_profit / agg_interest, 2) if agg_interest > 0 else None

    # Interest-to-revenue burden (how much of revenue is consumed by interest
    # alone) for the subset that also disclosed revenue.
    rev_issuers = [i for i in usable if i.revenue_usd]
    agg_revenue = sum(float(i.revenue_usd or 0.0) for i in rev_issuers)
    interest_for_rev = sum(float(i.annual_interest_expense_usd or 0.0) for i in rev_issuers)
    interest_to_revenue_pct = (
        round((interest_for_rev / agg_revenue) * 100, 1) if agg_revenue > 0 else None
    )

    return {
        "status": "source_backed",
        "issuers_total": len(issuers),
        "issuers_with_usable_inputs": len(usable),
        "issuers_excluded_missing_inputs": excluded,
        "aggregate_ebitda_usd": round(agg_profit, 2),
        "aggregate_annual_interest_usd": round(agg_interest, 2),
        "cluster_ebitda_interest_coverage": cluster_coverage,
        "issuers_with_ebitda_coverage_below_1": coverage_below_1,
        "loss_making_issuer_count": loss_making,
        "aggregate_interest_to_revenue_pct": interest_to_revenue_pct,
        "realistic_utilization_pct": realistic_utilization_pct,
        "per_issuer": per_issuer,
        "note": (
            "Cluster coverage = sum(EBITDA-or-operating-income) / sum(annual interest expense) "
            "across source-backed issuers. Coverage < 1 means operations do not cover interest "
            "alone (before any principal). Loss-making issuers carry negative EBITDA, so the "
            "ratio is negative. Realistic-utilization stress is forward-looking and applied "
            "separately; these figures are as-reported."
        ),
    }
