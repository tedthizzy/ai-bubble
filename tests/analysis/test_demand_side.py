"""Demand-side AI funding aggregation."""

from __future__ import annotations

from bubble.analysis.demand_side import aggregate_demand_side


def _rec(entity, *, capex, ocf, funding, ai_debt=None, commitments=None, overall="source_backed"):
    return {
        "data": {
            "entity": entity,
            "ai_datacenter_capex_usd": capex,
            "operating_cash_flow_usd": ocf,
            "ai_related_debt_or_financing_usd": ai_debt,
            "compute_purchase_commitments_usd": commitments,
            "funding_source": funding,
        },
        "verdict": {"overall": overall},
    }


def test_blocks_without_source_backed() -> None:
    out = aggregate_demand_side(
        [_rec("X", capex=1, ocf=1, funding="unknown", overall="unreliable")]
    )
    assert out["status"] == "blocked_no_source_backed_demand_side"


def test_self_funding_demand_side_supports_tiered_verdict() -> None:
    recs = [
        _rec(
            "Microsoft",
            capex=80e9,
            ocf=130e9,
            funding="predominantly_operating_cash_flow",
            commitments=110e9,
        ),
        _rec("Alphabet", capex=50e9, ocf=110e9, funding="predominantly_operating_cash_flow"),
        _rec("Meta", capex=40e9, ocf=90e9, funding="predominantly_operating_cash_flow"),
    ]
    out = aggregate_demand_side(recs)

    assert out["status"] == "source_backed"
    assert out["player_count"] == 3
    assert out["aggregate_ai_capex_usd"] == 170e9
    assert out["cash_coverage_of_capex"] == round(330e9 / 170e9, 2)
    assert out["cash_funded_players"] == 3
    assert out["aggregate_datacenter_purchase_commitments_usd"] == 110e9
    assert "self_funding" in out["bear_case_read"]


def test_debt_funded_demand_side_is_broader_signal() -> None:
    recs = [
        _rec(
            "StrainedCo",
            capex=100e9,
            ocf=40e9,
            funding="predominantly_debt_or_financing",
            ai_debt=30e9,
        ),
    ]
    out = aggregate_demand_side(recs)
    assert out["cash_coverage_of_capex"] == 0.4
    assert "exceeds_cash_flow" in out["bear_case_read"]


def test_falls_back_to_total_capex_when_ai_not_broken_out() -> None:
    recs = [
        {
            "data": {
                "entity": "Amazon",
                "ai_datacenter_capex_usd": None,
                "total_capex_usd": 90e9,
                "operating_cash_flow_usd": 120e9,
                "funding_source": "predominantly_operating_cash_flow",
            },
            "verdict": {"overall": "source_backed"},
        }
    ]
    out = aggregate_demand_side(recs)
    assert out["aggregate_ai_capex_usd"] == 90e9
