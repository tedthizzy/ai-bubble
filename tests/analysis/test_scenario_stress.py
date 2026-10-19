"""Forward-looking cluster cash-flow stress test."""

from __future__ import annotations

from bubble.analysis.scenario_stress import _stress_issuer, stress_cluster


def _issuer(entity, *, revenue, ebitda, interest, overall="source_backed"):
    return {
        "entity": entity,
        "revenue_usd": revenue,
        "ebitda_usd": ebitda,
        "annual_interest_expense_usd": interest,
        "verification_overall": overall,
    }


def test_blocks_without_source_backed() -> None:
    out = stress_cluster([_issuer("X", revenue=1, ebitda=1, interest=1, overall="unreliable")])
    assert out["status"] == "blocked_no_source_backed_financials"


def test_base_is_unstressed_and_stress_degrades_coverage() -> None:
    issuers = [
        _issuer("Healthy", revenue=1000, ebitda=300, interest=100),
        _issuer("Thin", revenue=500, ebitda=60, interest=50),
    ]
    out = stress_cluster(issuers)
    assert out["status"] == "source_backed"
    by_name = {s["scenario"]: s for s in out["scenarios"]}

    # Base: unstressed cluster coverage = (300+60)/(100+50) = 2.4
    assert by_name["base"]["cluster_stressed_interest_coverage"] == 2.4
    assert by_name["base"]["issuers_breaching"] == 0

    # Stress monotonically worsens coverage.
    base = by_name["base"]["cluster_stressed_interest_coverage"]
    adverse = by_name["adverse"]["cluster_stressed_interest_coverage"]
    severe = by_name["severe"]["cluster_stressed_interest_coverage"]
    assert base > adverse > severe


def test_revenue_miss_drives_negative_ebitda_and_breach() -> None:
    # Thin-margin, revenue-heavy issuer: a 40% utilization miss wipes EBITDA out.
    issuers = [_issuer("Miner", revenue=1000, ebitda=120, interest=80)]
    out = stress_cluster(issuers)
    by_name = {s["scenario"]: s for s in out["scenarios"]}
    # severe: EBITDA 120 - 0.40*1000 = -280; depreciation stays separate.
    assert by_name["severe"]["issuers_negative_ebitda"] == 1
    assert by_name["severe"]["issuers_breaching"] == 1
    assert out["first_majority_breach_scenario"] in {"adverse", "severe", "tail"}


def test_accounting_depreciation_does_not_change_ebitda_or_cash_interest_coverage() -> None:
    issuer = _issuer("Operator", revenue=1000, ebitda=300, interest=100)
    base = {"utilization_miss": 0, "rate_shock_bps": 0, "depr_accel": 0}
    accelerated = {**base, "depr_accel": 2}
    first = _stress_issuer(issuer, base)
    second = _stress_issuer(issuer, accelerated)
    assert first["stressed_ebitda_usd"] == second["stressed_ebitda_usd"] == 300
    assert first["stressed_interest_coverage"] == second["stressed_interest_coverage"] == 3
    assert second["modeled_incremental_depreciation_usd"] == 100


def test_missing_ebitda_does_not_become_zero_or_a_false_breach() -> None:
    issuer = _issuer("Missing", revenue=1000, ebitda=300, interest=100)
    del issuer["ebitda_usd"]
    out = stress_cluster([issuer])
    assert out["status"] == "blocked_no_source_backed_financials"
    assert out["excluded_issuers"] == ["Missing"]
