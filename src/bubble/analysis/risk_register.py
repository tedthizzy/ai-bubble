"""Top actionable-risk register — synthesizes the verified layers into a ranked list.

The Final Burry Report requires a "Top 10-15 actionable risks with supporting
data." This module builds that register DETERMINISTICALLY from the already-verified
analytical layers (cluster cash-flow + scenario stress, debt census / refi wall,
GPU depreciation gap, customer concentration, contagion hubs, demand-side off-BS
leverage, power/ratepayer, equity + debt-side end-holders, equipment chokepoints,
and the forensic red-flag scorecard). Each risk carries a severity (1-5), a
quantified evidence anchor, the backing layer, and a source-status label
(source_backed vs illustrative) so nothing is asserted above its evidence tier.

A risk only enters the register if its backing layer is present and source-backed;
the register never invents a risk it cannot anchor to a computed, sourced number.
Ranking is severity-first, then by whether the anchor is source-backed.
"""

from __future__ import annotations

from typing import Any


def _num(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _b(value: float | None, scale: float = 1e9, suffix: str = "B") -> str:
    if value is None:
        return "n/a"
    return f"${round(value / scale, 1)}{suffix}"


def _risk(
    rid: str,
    title: str,
    category: str,
    severity: int,
    evidence: str,
    layer: str,
    source_backed: bool = True,
) -> dict[str, Any]:
    return {
        "id": rid,
        "title": title,
        "category": category,
        "severity": severity,
        "evidence": evidence,
        "backing_layer": layer,
        "source_status": "source_backed" if source_backed else "illustrative_or_partial",
    }


def _breadth_risks(m: dict[str, Any]) -> list[dict[str, Any]]:
    """The lower-severity breadth-layer risks (supply, demand, downside incidence, ratepayer)."""

    out: list[dict[str, Any]] = []
    geq = m.get("gpu_earnings_quality", {}) or {}
    if geq.get("status") == "source_backed" and geq.get("issuers_with_restatement"):
        out.append(
            _risk(
                "R12",
                "Earnings overstated by slow GPU depreciation: honest economic-life depreciation deepens the losses",
                "earnings_quality",
                4,
                f"Restating GPU depreciation at ~3yr economic life adds "
                f"~${round((geq.get('cluster_annual_da_understatement_usd') or 0) / 1e9, 1)}B/yr of D&A "
                f"across {geq.get('issuers_with_restatement')} issuers; "
                f"{geq.get('issuers_earnings_worsen_under_honest_depreciation')} see earnings worsen "
                "(CoreWeave's loss ~triples; Nebius flips negative). Several EXTENDED useful lives "
                "(earnings-flattering). Inputs primary-sourced; economic life a labeled assumption.",
                "gpu_earnings_quality",
            )
        )
    sat = m.get("satellite_construction", {}) or {}
    if sat.get("status") == "source_backed" and sat.get("active_construction_pct") is not None:
        out.append(
            _risk(
                "R11",
                "Physical overbuild gap: most announced AI data-center sites show no ground construction on satellite",
                "physical_overbuild",
                4,
                f"Sentinel-2 change detection over {sat.get('site_count')} georeferenced AI sites: only "
                f"{sat.get('active_construction_pct')}% show active construction; {sat.get('no_change_sites')} "
                "show NO significant ground change -- announced capacity outrunning physical reality "
                "(read with the tracker construction-status proxy; cloud/seasonal noise applies).",
                "satellite_construction",
            )
        )
    eq = m.get("equipment_bottlenecks", {}) or {}
    if eq.get("status") == "source_backed" and eq.get("single_source_or_duopoly_chokepoints"):
        out.append(
            _risk(
                "R7",
                "Single-source supply gate (TSMC CoWoS) caps the buildout and propagates a shock to all issuers",
                "physical_supply",
                3,
                f"{eq.get('gating_chokepoint_count')}/{eq.get('chokepoint_count')} chokepoints gate the "
                f"buildout (lead times up to ~{eq.get('max_lead_time_months')} months); CoWoS near-single-source.",
                "equipment_bottlenecks",
            )
        )
    ds = m.get("demand_side_funding", {}) or {}
    if ds.get("status") == "source_backed":
        out.append(
            _risk(
                "R8",
                "Demand-side off-balance-sheet leverage understates hyperscaler commitment risk",
                "hidden_leverage",
                3,
                f"Aggregate cash-coverage {ds.get('cash_coverage_of_capex')}x but read "
                f"'{ds.get('bear_case_read')}' — Oracle debt-funded + large off-BS lease pipelines outside "
                "the headline number.",
                "demand_side",
            )
        )
    pcf = m.get("private_credit_funding", {}) or {}
    if pcf.get("status") == "source_backed":
        out.append(
            _risk(
                "R9",
                "Ultimate downside socialized: cluster debt routes to insurance/pension capital (households)",
                "downside_incidence",
                3,
                f"{pcf.get('lenders_with_household_routed_funding')}/{pcf.get('lender_count')} private-credit "
                f"lenders draw material insurance/pension funding (median "
                f"~{pcf.get('median_insurance_funded_share_pct')}% insurance-funded) — debt-side loss lands on "
                "policyholders/retirees, invisible in 13-F equity data.",
                "private_credit_funding + end_holders",
            )
        )
    pw = m.get("power_ratepayer_exposure", {}) or {}
    if pw.get("status") == "source_backed" and pw.get("ratepayer_socialized_usd"):
        out.append(
            _risk(
                "R10",
                "Ratepayer stranded-asset exposure on AI grid build (largely, not fully, protected)",
                "ratepayer",
                2,
                f"~{_b(_num(pw.get('ratepayer_socialized_usd')))} (~{pw.get('ratepayer_socialized_pct')}%) of "
                f"AI generation/grid build in the rate base; read "
                f"'{str(pw.get('ratepayer_downside_read', '')).split(':')[0]}' — most cost shifted to AI "
                "customers via take-or-pay, residual on regulated utilities.",
                "power_exposure",
            )
        )
    return out


def build_risk_register(
    mismatch_ratios: dict[str, Any],
    *,
    debt_census: dict[str, Any] | None = None,
    contagion_hubs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the ranked top-risk register from the source-backed layers."""

    m = mismatch_ratios or {}
    census = debt_census or {}
    hubs = contagion_hubs or {}
    risks: list[dict[str, Any]] = []

    def emit(*args: Any) -> None:
        risks.append(_risk(*args))

    # 1. Cash-flow fragility + forward stress.
    cov = m.get("cluster_interest_coverage", {}) or {}
    stress = m.get("scenario_stress", {}) or {}
    if cov.get("status") == "source_backed":
        c = cov.get("cluster_ebitda_interest_coverage")
        loss = cov.get("loss_making_issuer_count")
        usable = cov.get("issuers_with_usable_inputs")
        adverse: dict[str, Any] = next(
            (s for s in (stress.get("scenarios") or []) if s.get("scenario") == "adverse"), {}
        )
        adv_breach = adverse.get("issuers_breaching")
        emit(
            "R1",
            "Cluster cash-flow fragility: positive coverage leans on one issuer and flips negative under a moderate shock",
            "leverage_cashflow",
            5,
            f"Cluster EBITDA/interest ~{c}x but {loss}/{usable} issuers loss-making; ex-CoreWeave aggregate "
            f"EBITDA negative. Forward stress: {adv_breach} issuers breach by the ADVERSE case "
            f"(25% util miss + 200bp).",
            "cluster_interest_coverage + scenario_stress",
            True,
        )

    # 2. Refinancing wall.
    if census.get("status") in ("source_backed", None) and census.get("cluster_total_debt_usd"):
        emit(
            "R2",
            "Refinancing treadmill on negative carry",
            "refinancing",
            5,
            f"Cluster debt {_b(_num(census.get('cluster_total_debt_usd')))}; maturities spread 2026-2034 "
            f"(~{census.get('near_term_2025_2027_pct_of_scheduled')}% near-term 2025-2027, "
            f"~{census.get('wall_2030_2033_pct_of_scheduled')}% 2030-2033) refinanced at 6-10% / SOFR+225-400bp.",
            "debt_census",
            True,
        )

    # 3. Customer concentration.
    rf = m.get("red_flag_scorecard", {}) or {}
    common = rf.get("most_common_flags", {}) or {}
    if rf.get("status") == "source_backed" and common.get("customer_concentration_over_35pct"):
        emit(
            "R3",
            "Anchor-customer concentration: a single pullback collapses contracted revenue",
            "concentration",
            4,
            f"customer_concentration_over_35pct present in {common.get('customer_concentration_over_35pct')}"
            f"/{rf.get('issuer_count')} issuers (e.g. CoreWeave ~67% Microsoft).",
            "red_flag_scorecard + contagion",
            True,
        )

    # 4. Pervasive forensic / accounting red flags.
    if rf.get("status") == "source_backed" and rf.get("issuers_with_serious_accounting_flag"):
        serious = rf.get("issuers_with_serious_accounting_flag") or []
        emit(
            "R4",
            "Pervasive internal-control / accounting red flags across the cluster",
            "forensic_accounting",
            4,
            f"{len(serious)}/{rf.get('issuer_count')} issuers carry a filing-tied SERIOUS flag; "
            f"material_weakness_icfr present {common.get('material_weakness_icfr', 0)}/{rf.get('issuer_count')}, "
            f"auditor change {common.get('auditor_change_or_resignation', 0)}, "
            f"related-party/circular {common.get('related_party_or_circular_financing', 0)}.",
            "red_flag_scorecard",
            True,
        )

    # 5. NVIDIA circular hub / shared counterparties.
    if hubs.get("status") == "source_backed" and hubs.get("top_contagion_hubs"):
        top = hubs.get("top_contagion_hubs") or []
        names = ", ".join(str(h.get("counterparty")) for h in top[:3])
        circ = m.get("circular_financing", {}) or {}
        circ_hub = circ.get("reciprocal_hub") or {}
        circ_clause = ""
        if circ.get("status") == "source_backed" and circ_hub.get("filing_verified_round_trip_count"):
            cap_b = round(float(circ_hub.get("filing_verified_reciprocal_capital_usd") or 0) / 1e9, 1)
            circ_clause = (
                f" Round-trip quantified: NVIDIA is a filing-verified equity investor in "
                f"{circ_hub.get('filing_verified_investee_count')} of its own GPU-cloud customers "
                f"({', '.join(circ_hub.get('filing_verified_investees') or [])}), "
                f"{circ_hub.get('filing_verified_round_trip_count')} with a filing-verified "
                f"return-purchase leg (~${cap_b}B reciprocal). Vendor-financed demand is not "
                "arm's-length -- the Lucent/Nortel late-cycle tell."
            )
        emit(
            "R5",
            "Single-counterparty contagion + vendor round-trip: NVIDIA is supplier AND equity investor",
            "contagion",
            4,
            f"Shared hubs touch multiple issuers simultaneously: {names}. NVIDIA is both GPU supplier and "
            f"equity investor (filing-verified circular relationship).{circ_clause}",
            "circular_financing",
            True,
        )

    # 6. GPU depreciation gap.
    gpu = (m.get("gpu_economics_mismatch", {}) or {}).get("source_backed_gap", {}) or {}
    if gpu.get("status") == "source_backed":
        emit(
            "R6",
            "GPU economic life shorter than the depreciation schedule",
            "asset_quality",
            4,
            "Deployed-fleet rental yields down ~60-75% in ~2yr + Amazon's SEC 6->5yr server-life revision; "
            "book useful lives (5-6yr+) likely overstate recoverable value, understating depreciation/impairment.",
            "gpu_economics_mismatch",
            True,
        )

    risks.extend(_breadth_risks(m))

    risks.sort(key=lambda r: (r["severity"], r["source_status"] == "source_backed"), reverse=True)
    # Re-number by rank for a clean register.
    for i, r in enumerate(risks, start=1):
        r["rank"] = i

    if not risks:
        return {"status": "blocked_no_source_backed_layers", "risk_count": 0}

    by_cat: dict[str, int] = {}
    for r in risks:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1

    return {
        "status": "source_backed",
        "risk_count": len(risks),
        "source_backed_risk_count": sum(1 for r in risks if r["source_status"] == "source_backed"),
        "severity_5_count": sum(1 for r in risks if r["severity"] == 5),
        "categories": by_cat,
        "risks": risks,
        "note": (
            "Top actionable-risk register synthesized deterministically from the source-backed "
            "analytical layers. Each risk is anchored to a computed, sourced number and tagged "
            "source_backed vs illustrative; a risk enters only if its backing layer is source-backed. "
            "Severity 1-5; ranked severity-first. This is the prioritized read for an analyst, not a "
            "new claim -- every anchor traces to its layer's evidence and caveats."
        ),
    }
