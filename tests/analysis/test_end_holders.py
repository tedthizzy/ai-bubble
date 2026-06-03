"""Ultimate end-holder aggregation (who really bears the downside)."""

from __future__ import annotations

from bubble.analysis.end_holders import aggregate_end_holders


def _holder(name, htype, *, value=None, verdict="filing_verified", sec="common_equity"):
    return {
        "holder_name": name,
        "holder_type": htype,
        "security_type": sec,
        "approx_value_usd": value,
        "source_filing": "13F-HR",
        "verdict": verdict,
    }


def _rec(entity, holders, overall="source_backed"):
    return {"entity": entity, "verified_holders": holders, "overall": overall}


def test_blocks_without_source_backed() -> None:
    out = aggregate_end_holders([_rec("X", [_holder("A", "insurer")], overall="unreliable")])
    assert out["status"] == "blocked_no_source_backed_end_holders"


def test_rejected_holders_are_excluded() -> None:
    out = aggregate_end_holders(
        [
            _rec(
                "CoreWeave",
                [
                    _holder("Vanguard", "index_fund_passive"),
                    _holder("Ghost", "insurer", verdict="rejected_unsourced"),
                ],
            )
        ]
    )
    assert out["total_kept_holders"] == 1
    assert out["count_by_holder_type"].get("insurer") is None


def test_household_socialized_read_and_value_weighting() -> None:
    recs = [
        _rec(
            "CoreWeave",
            [
                _holder("Vanguard Index", "index_fund_passive", value=2e9),
                _holder("BlackRock Index", "index_fund_passive", value=1e9),
                _holder("Athene (Apollo)", "insurer", value=1e9),
                _holder("Tiger Global", "hedge_fund", value=1e9),
            ],
        ),
    ]
    out = aggregate_end_holders(recs)
    assert out["status"] == "source_backed"
    # 3 of 4 disclosed holders route to households.
    assert out["household_routed_count_pct"] == 75.0
    # value: household 4e9 of 5e9 total = 80%
    assert out["household_routed_value_pct"] == 80.0
    assert "household_socialized" in out["ultimate_downside_read"]
    assert out["count_by_routing_bucket"]["household_routed"] == 3
    assert out["count_by_routing_bucket"]["risk_capital"] == 1


def test_risk_capital_held_read() -> None:
    recs = [
        _rec(
            "Applied Digital",
            [
                _holder("HF One", "hedge_fund"),
                _holder("PE Two", "private_equity"),
                _holder("VC Three", "venture_capital"),
                _holder("Some Bank", "bank"),
            ],
        ),
    ]
    out = aggregate_end_holders(recs)
    assert "risk_capital_held" in out["ultimate_downside_read"]
    assert out["household_routed_value_pct"] is None  # no disclosed values
