"""Illustrative operating-earnings and interest-coverage stress on verified inputs.

Revenue and refinancing shocks are assumptions. Incremental depreciation is
an accounting sensitivity, kept separate from EBITDA and operating cash flow.
This does not calculate facility DSCR or determine covenant defaults.
"""

from __future__ import annotations

import math
from typing import Any

# Stress parameters per scenario (aligned with the ScenarioEngine):
# utilization_miss -> fraction of revenue lost; rate_shock_bps -> added to refi
# rate; depr_accel -> separate illustrative depreciation expense.
_SCENARIOS: list[dict[str, Any]] = [
    {"name": "base", "utilization_miss": 0.0, "rate_shock_bps": 0, "depr_accel": 0.0},
    {"name": "adverse", "utilization_miss": 0.25, "rate_shock_bps": 200, "depr_accel": 0.5},
    {"name": "severe", "utilization_miss": 0.40, "rate_shock_bps": 300, "depr_accel": 1.0},
    {"name": "tail", "utilization_miss": 0.55, "rate_shock_bps": 400, "depr_accel": 2.0},
]
# Proxy average all-in rate (bps) used to translate a rate shock into a % change
# in interest expense (the AI-direct cluster runs ~6-10% fixed / SOFR+225-400).
_AVG_RATE_BPS = 800.0


def _num(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


def _stress_issuer(issuer: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    revenue = _num(issuer.get("revenue_usd"))
    ebitda = _num(issuer.get("ebitda_usd"))
    interest = _num(issuer.get("annual_interest_expense_usd"))

    miss = float(scenario["utilization_miss"])
    rate_shock_bps = float(scenario["rate_shock_bps"])
    depr_accel = float(scenario["depr_accel"])

    # Assumed revenue loss flows to EBITDA with no variable-cost relief.
    # Depreciation is excluded from EBITDA. Keep the illustrative accounting
    # sensitivity separate from operating cash flow and interest coverage.
    stressed_ebitda = ebitda - miss * revenue
    incremental_depreciation = depr_accel * 0.05 * revenue
    # Rate shock reprices debt at refinancing: interest rises by shock/avg-rate.
    stressed_interest = interest * (1 + rate_shock_bps / _AVG_RATE_BPS)
    coverage = round(stressed_ebitda / stressed_interest, 2) if stressed_interest > 0 else None
    return {
        "entity": str(issuer.get("entity") or "").split(",")[0].split("(")[0].strip(),
        "stressed_ebitda_usd": round(stressed_ebitda, 2),
        "modeled_incremental_depreciation_usd": round(incremental_depreciation, 2),
        "stressed_interest_usd": round(stressed_interest, 2),
        "stressed_interest_coverage": coverage,
        "breaches": (coverage is not None and coverage < 1.0) or stressed_ebitda < 0,
        "negative_ebitda": stressed_ebitda < 0,
    }


def stress_cluster(issuers: list[dict[str, Any]]) -> dict[str, Any]:
    """Run the Base/Adverse/Severe/Tail earnings and interest stress over the cluster."""

    usable = []
    excluded = []
    for issuer in issuers:
        verified = (
            str(issuer.get("verification_overall") or issuer.get("overall") or "")
            == "source_backed"
        )
        values = [
            issuer.get(key) for key in ("revenue_usd", "ebitda_usd", "annual_interest_expense_usd")
        ]
        complete = all(
            isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
            for value in values
        )
        if verified and complete:
            usable.append(issuer)
        else:
            excluded.append(str(issuer.get("entity") or "unnamed"))
    if not usable:
        return {
            "status": "blocked_no_source_backed_financials",
            "issuer_count": 0,
            "excluded_issuers": excluded,
        }

    scenarios: list[dict[str, Any]] = []
    for scenario in _SCENARIOS:
        per = [_stress_issuer(i, scenario) for i in usable]
        agg_ebitda = sum(p["stressed_ebitda_usd"] for p in per)
        agg_interest = sum(p["stressed_interest_usd"] for p in per)
        coverage = round(agg_ebitda / agg_interest, 2) if agg_interest > 0 else None
        scenarios.append(
            {
                "scenario": scenario["name"],
                "params": {
                    "utilization_miss_pct": int(scenario["utilization_miss"] * 100),
                    "rate_shock_bps": scenario["rate_shock_bps"],
                    "gpu_depreciation_acceleration": scenario["depr_accel"],
                },
                "cluster_stressed_ebitda_usd": round(agg_ebitda, 2),
                "cluster_modeled_incremental_depreciation_usd": sum(
                    p["modeled_incremental_depreciation_usd"] for p in per
                ),
                "cluster_stressed_interest_coverage": coverage,
                "issuers_breaching": sum(p["breaches"] for p in per),
                "issuers_negative_ebitda": sum(p["negative_ebitda"] for p in per),
                "issuer_count": len(per),
            }
        )

    # First-distress read: the mildest scenario where a majority breach -- INCLUDING base
    # (base applies zero shock, so a majority breach there means the core is already fragile).
    majority = next(
        (s for s in scenarios if s["issuers_breaching"] >= len(usable) / 2),
        None,
    )
    at_base = bool(majority and majority["scenario"] == "base")
    return {
        "status": "source_backed",
        "issuer_count": len(usable),
        "excluded_issuers": excluded,
        "scenarios": scenarios,
        "first_majority_breach_scenario": majority["scenario"] if majority else None,
        "majority_breach_at_base_zero_shock": at_base,
        "note": (
            "Cluster interest-coverage stress uses the supplied verified financial observations; the "
            "stress PARAMETERS (utilization miss, rate shock, GPU-life compression) are labeled "
            "assumptions. EBITDA falls ~1:1 with the revenue lost to a utilization miss (high fixed "
            "cost), interest reprices at refinancing by shock/avg-rate (~8%). 'Breaching' = stressed "
            "interest coverage < 1 or negative EBITDA; this is not a covenant default test or DSCR. "
            "Illustrative incremental depreciation is reported separately and does not reduce EBITDA "
            "or operating cash flow. Results describe only the supplied issuer observations."
        ),
    }
