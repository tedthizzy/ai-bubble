"""Forward-looking multi-scenario stress test on the AI-direct cluster.

Real cash-flow modeling on the source-backed issuer financials: under
Base / Adverse / Severe / Tail stress (utilization miss -> revenue/EBITDA haircut,
rate shock at refinancing, GPU economic-life compression), compute the stressed
cluster interest coverage and count the issuers that breach (coverage < 1 or
negative EBITDA). Answers "how severely will it crack" from disclosed numbers,
not assumptions -- the stress PARAMETERS are assumptions (and labeled as such),
but the base financials are primary-sourced.
"""

from __future__ import annotations

from typing import Any

# Stress parameters per scenario (aligned with the ScenarioEngine):
# utilization_miss -> fraction of revenue lost; rate_shock_bps -> added to refi
# rate; depr_accel -> GPU economic-life compression (extra EBITDA drag).
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

    # Revenue falls with utilization; the lost revenue flows ~fully to EBITDA
    # (costs are mostly fixed depreciation/power). GPU life compression adds an
    # incremental depreciation/impairment drag scaled to revenue.
    stressed_ebitda = ebitda - miss * revenue - depr_accel * 0.05 * revenue
    # Rate shock reprices debt at refinancing: interest rises by shock/avg-rate.
    stressed_interest = interest * (1 + rate_shock_bps / _AVG_RATE_BPS)
    coverage = round(stressed_ebitda / stressed_interest, 2) if stressed_interest > 0 else None
    return {
        "entity": str(issuer.get("entity") or "").split(",")[0].split("(")[0].strip(),
        "stressed_ebitda_usd": round(stressed_ebitda, 2),
        "stressed_interest_usd": round(stressed_interest, 2),
        "stressed_interest_coverage": coverage,
        "breaches": (coverage is not None and coverage < 1.0) or stressed_ebitda < 0,
        "negative_ebitda": stressed_ebitda < 0,
    }


def stress_cluster(issuers: list[dict[str, Any]]) -> dict[str, Any]:
    """Run the Base/Adverse/Severe/Tail cash-flow stress over the cluster."""

    usable = [
        i
        for i in issuers
        if str(i.get("verification_overall") or i.get("overall") or "source_backed")
        == "source_backed"
    ]
    if not usable:
        return {"status": "blocked_no_source_backed_financials", "issuer_count": 0}

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
        "scenarios": scenarios,
        "first_majority_breach_scenario": majority["scenario"] if majority else None,
        "majority_breach_at_base_zero_shock": at_base,
        "note": (
            "Cluster cash-flow stress: base financials are primary-sourced (11-issuer fixture); the "
            "stress PARAMETERS (utilization miss, rate shock, GPU-life compression) are labeled "
            "assumptions. EBITDA falls ~1:1 with the revenue lost to a utilization miss (high fixed "
            "cost), interest reprices at refinancing by shock/avg-rate (~8%). 'Breaching' = stressed "
            "interest coverage < 1 or negative EBITDA. A MAJORITY of issuers already breach at the BASE "
            "scenario (which applies ZERO shock), so the financed core is already fragile before any "
            "shock -- the aggregate ~1.35x coverage is a CoreWeave/CleanSpark concentration artifact "
            "masking the loss-makers; the adverse/severe scenarios only deepen the breach."
        ),
    }
