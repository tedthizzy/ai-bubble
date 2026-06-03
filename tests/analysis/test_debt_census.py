"""AI-direct debt census aggregation."""

from __future__ import annotations

from bubble.analysis.debt_census import aggregate_debt_census


def _row(entity: str, total: float, schedule: dict[str, float], overall: str = "source_backed"):
    return {
        "stack": {
            "entity": entity,
            "total_debt_usd": total,
            "facilities": [{"name": "f1"}],
            "maturity_schedule_usd": schedule,
        },
        "verdict": {"overall": overall, "maturity_schedule_confirmed": True},
    }


def test_blocks_when_no_source_backed_issuers() -> None:
    out = aggregate_debt_census([_row("X", 1.0, {"y2030": 1.0}, overall="unreliable")])
    assert out["status"] == "blocked_no_source_backed_census"


def test_aggregates_total_and_real_maturity_wall() -> None:
    census = [
        _row("CoreWeave", 25_000_000_000, {"y2026": 6_000_000_000, "y2030": 10_000_000_000}),
        _row("IREN", 4_000_000_000, {"y2027": 2_000_000_000, "y2031": 2_000_000_000}),
    ]
    out = aggregate_debt_census(census)

    assert out["status"] == "source_backed"
    assert out["issuer_count"] == 2
    assert out["cluster_total_debt_usd"] == 29_000_000_000
    assert out["scheduled_maturities_usd"] == 20_000_000_000
    # 2030-2033 = 10 + 2 = 12 of 20 scheduled = 60%
    assert out["wall_2030_2033_usd"] == 12_000_000_000
    assert out["wall_2030_2033_pct_of_scheduled"] == 60.0
    # 2025-2027 = 6 + 2 = 8 of 20 = 40% (near-term is material, not a pure 2030-33 cliff)
    assert out["near_term_2025_2027_pct_of_scheduled"] == 40.0
    assert out["peak_maturity_year"] == "y2030"


def test_partially_source_backed_issuers_are_included() -> None:
    out = aggregate_debt_census(
        [_row("Nebius", 4_000_000_000, {"y2030": 1_000_000_000}, overall="partially_source_backed")]
    )
    assert out["issuer_count"] == 1
    assert out["cluster_total_debt_usd"] == 4_000_000_000
