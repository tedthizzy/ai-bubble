"""AI power / ratepayer exposure aggregation."""

from __future__ import annotations

from bubble.analysis.power_exposure import aggregate_power_exposure


def _rec(entity, *, load, build, alloc, customers=None, overall="source_backed"):
    return {
        "data": {
            "entity": entity,
            "ai_datacenter_load_mw": load,
            "generation_build_for_ai_usd": build,
            "cost_allocation": alloc,
            "named_ai_customers": customers or [],
        },
        "verdict": {"overall": overall},
    }


def test_blocks_without_source_backed() -> None:
    out = aggregate_power_exposure(
        [_rec("X", load=1, build=1, alloc="unknown", overall="unreliable")]
    )
    assert out["status"] == "blocked_no_source_backed_power_exposure"


def test_material_ratepayer_socialization() -> None:
    recs = [
        _rec(
            "Entergy",
            load=2000,
            build=10e9,
            alloc="ratepayers_bear_via_rate_base",
            customers=["Meta"],
        ),
        _rec("AEP", load=3000, build=8e9, alloc="mixed", customers=["Google", "Microsoft"]),
    ]
    out = aggregate_power_exposure(recs)

    assert out["status"] == "source_backed"
    assert out["total_ai_datacenter_load_mw"] == 5000
    # ratepayer = full rate-base (10) + half of mixed (4) = 14 of 18 total = 77.8%
    assert out["ratepayer_socialized_usd"] == 14e9
    assert out["ratepayer_socialized_pct"] == round(100 * 14e9 / 18e9, 1)
    assert "material_ratepayer_socialization" in out["ratepayer_downside_read"]
    assert "Meta" in out["named_ai_customers"]


def test_protected_when_customer_bears() -> None:
    recs = [
        _rec(
            "AEP Ohio",
            load=1000,
            build=5e9,
            alloc="ai_customer_bears_via_special_tariff_or_min_take",
        ),
    ]
    out = aggregate_power_exposure(recs)
    assert out["ratepayer_socialized_pct"] == 0.0
    assert "ratepayers_largely_protected" in out["ratepayer_downside_read"]
