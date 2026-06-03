"""Debt-side private-credit funding-routing aggregation."""

from __future__ import annotations

from bubble.analysis.private_credit_funding import aggregate_private_credit_funding


def _source(stype, *, verdict="filing_verified", share=None):
    return {
        "source_type": stype,
        "approx_share_pct": share,
        "source_filing": "10-K",
        "verdict": verdict,
    }


def _rec(lender, *, sources, ins_share=None, overall="source_backed"):
    return {
        "lender": lender,
        "verified_funding_sources": sources,
        "insurance_funded_share_pct": ins_share,
        "overall": overall,
    }


def test_blocks_without_source_backed() -> None:
    out = aggregate_private_credit_funding(
        [_rec("X", sources=[_source("pension")], overall="unreliable")]
    )
    assert out["status"] == "blocked_no_source_backed_private_credit_funding"


def test_rejected_sources_excluded() -> None:
    out = aggregate_private_credit_funding(
        [
            _rec(
                "Apollo",
                sources=[
                    _source("insurance_annuity_balance_sheet"),
                    _source("pension", verdict="rejected_unsourced"),
                ],
                ins_share=60,
            )
        ]
    )
    assert out["total_kept_sources"] == 1
    assert out["filing_verified_sources"] == 1


def test_routes_to_households_read() -> None:
    out = aggregate_private_credit_funding(
        [
            _rec(
                "Apollo / Athene",
                sources=[_source("insurance_annuity_balance_sheet", share=60)],
                ins_share=60,
            ),
            _rec(
                "Blue Owl",
                sources=[_source("insurance_annuity_balance_sheet", share=30), _source("pension", share=20)],
                ins_share=30,
            ),
            _rec(
                "Sixth Street",
                sources=[_source("sovereign_wealth", share=40), _source("endowment_or_foundation", share=30)],
            ),
        ]
    )
    assert out["status"] == "source_backed"
    assert out["lenders_with_household_routed_funding"] == 2
    assert "Apollo" in out["insurance_funded_lenders"]
    assert out["median_insurance_funded_share_pct"] == 45.0  # median of [60, 30]
    assert "debt_side_routes_to_households" in out["debt_side_downside_read"]
    # Highest insurance share sorts first.
    assert out["per_lender"][0]["lender"] == "Apollo"


def test_mixed_read_when_minority_household() -> None:
    out = aggregate_private_credit_funding(
        [
            _rec("Apollo", sources=[_source("insurance_annuity_balance_sheet")], ins_share=55),
            _rec("Sixth Street", sources=[_source("sovereign_wealth")]),
            _rec("Generic", sources=[_source("bank_or_other_institutional")]),
        ]
    )
    assert out["lenders_with_household_routed_funding"] == 1
    assert "debt_side_mixed" in out["debt_side_downside_read"]
