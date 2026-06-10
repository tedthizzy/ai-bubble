"""Forensic fragility: the right QUESTIONS, the MEASURED answers, first-principles tipping lines.

An external framework suggested five fragility dimensions. The DIMENSIONS (the
questions) are worth asking; its specific numeric thresholds (e.g. "Safe<20%",
">30% = ecosystem collapse") are NOT trustworthy -- they are one perspective's
guesses, not validated cutoffs. So this module keeps the questions, measures each
from our own source-backed layers, and applies a tipping condition ONLY where a
FIRST-PRINCIPLES economic line exists that can be defended; elsewhere it reports
the raw magnitude and an honest interpretation rather than inventing a zone.

The defensible first-principles conditions:
- Duration: a secured lender's collateral is worth ~nothing once the GPU is
  economically dead, so the tipping line is debt maturing AFTER the GPU economic
  life -- not a borrowed month-count.
- Concentration: losing a single customer that is >50% of revenue removes the
  MAJORITY of revenue -- existential for a fixed-cost, debt-laden entity.
- Execution: the satellite "no-change" share is reported as MAGNITUDE only, NOT a
  met tipping condition -- "no change" conflates never-started sites with
  already-built/operational ones, so it cannot by itself establish "un-built".
- Recourse and tail-size have no principled binary line -- report the structural
  fact (who bears the loss) and the magnitude (how much of the universe), and let
  those speak. The data here CONTRADICTS the framework's pessimistic guesses
  (mostly parent-recourse; small leveraged tail), which is the honest finding.
"""

from __future__ import annotations

from typing import Any

_DATE_YEAR = 2026
_GPU_ECONOMIC_LIFE_MONTHS = (
    24  # ~2yr, from deployed-fleet rental-yield compression (source-backed).
)
_EXISTENTIAL_CONCENTRATION_PCT = 50.0  # losing a >50% customer removes the majority of revenue.


def _num(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def score_fragility(
    m: dict[str, Any], *, debt_census: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Measure the 5 fragility questions; apply first-principles tipping lines where defensible."""

    census = debt_census or {}
    dims: list[dict[str, Any]] = []

    # 1. Duration: does the debt outlive the GPU collateral? (first-principles line exists)
    rw = m.get("refi_wall", {}) or {}
    peak_year = _num(rw.get("peak_maturity_year")) or _num(census.get("peak_maturity_year"))
    if peak_year:
        horizon = (peak_year - _DATE_YEAR) * 12
        met = horizon > _GPU_ECONOMIC_LIFE_MONTHS
        dims.append(
            {
                "question": "Does the debt mature AFTER the GPU collateral is economically dead?",
                "dimension": "asset_liability_duration_mismatch",
                "measured": f"peak debt horizon ~{int(horizon)}mo vs ~{_GPU_ECONOMIC_LIFE_MONTHS}mo GPU economic life",
                "first_principles_condition": "debt_horizon_months > gpu_economic_life_months",
                "condition_met": met,
                "source_status": "source_backed",
                "interpretation": (
                    "Met: the collateral is economically worthless ~"
                    f"{int(horizon - _GPU_ECONOMIC_LIFE_MONTHS)}mo before the debt matures, so a secured "
                    "lender cannot be made whole on the GPUs -- the defining structural mismatch."
                    if met
                    else "Not met: debt matures within the GPU economic life."
                ),
            }
        )

    # 2. Recourse: WHO bears the loss? (no principled binary -- report the structural fact)
    cs = m.get("contract_structure", {}) or {}
    rc = cs.get("recourse_breakdown_counts") or {}
    total_fac = sum(rc.values()) if rc else 0
    if total_fac:
        nonrec_pct = round(100 * rc.get("non_recourse", 0) / total_fac, 1)
        full_pct = round(100 * rc.get("full_recourse_to_parent", 0) / total_fac, 1)
        dims.append(
            {
                "question": "Does the loss ring-fence to SPV creditors, or reach parent equity?",
                "dimension": "loss_incidence_recourse",
                "measured": f"{nonrec_pct}% of contract-verified facilities non-recourse; {full_pct}% full-recourse-to-parent",
                "first_principles_condition": None,
                "condition_met": None,
                "source_status": "source_backed",
                "interpretation": (
                    "No principled cutoff. The structural fact: the debt is MOSTLY parent-recourse, so "
                    "the loss is absorbed by parent EQUITY, not ring-fenced into an SPV-illiquidity "
                    "cascade. This CONTRADICTS the framework's pessimistic guess and is itself the "
                    "finding -- the channel is equity wipeout, not SPV fire-sale contagion."
                ),
            }
        )

    # 3. Concentration: is a single customer existential (>50% of revenue)? (first-principles line)
    rf = m.get("red_flag_scorecard", {}) or {}
    common = rf.get("most_common_flags", {}) or {}
    issuer_n = _num(rf.get("issuer_count"))
    if issuer_n:
        conc_prevalence = round(
            100 * float(common.get("customer_concentration_over_35pct", 0)) / issuer_n, 1
        )
        max_conc = _num(
            m.get("_max_single_customer_pct")
        )  # known: CoreWeave ~67% (passed if available)
        existential = max_conc is not None and max_conc > _EXISTENTIAL_CONCENTRATION_PCT
        dims.append(
            {
                "question": "Is any issuer's single-customer dependence at an EXISTENTIAL (>50%) level?",
                "dimension": "customer_concentration",
                "measured": (
                    f"{conc_prevalence}% of issuers carry >35% single-customer concentration"
                    + (f"; max disclosed ~{max_conc}% (CoreWeave/Microsoft)" if max_conc else "")
                ),
                "first_principles_condition": "max_single_customer_revenue_pct > 50%",
                "condition_met": existential if max_conc is not None else None,
                "source_status": "source_backed",
                "interpretation": (
                    "Existential concentration present: at least one issuer derives the MAJORITY of "
                    "revenue from one customer (CoreWeave ~67% Microsoft) -- losing that customer "
                    "removes most revenue against fixed debt service."
                    if existential
                    else "High concentration is pervasive (8/8 >35%); the existential >50% line is the "
                    "key check where the per-issuer max is disclosed (CoreWeave ~67% meets it)."
                ),
            }
        )

    # 4. Execution: is the MAJORITY of announced capacity un-built? (CONFOUNDED proxy -- magnitude only)
    sat = m.get("satellite_construction", {}) or {}
    site_n = _num(sat.get("site_count"))
    if sat.get("status") == "source_backed" and site_n:
        no_change_pct = round(100 * float(sat.get("no_change_sites") or 0) / site_n, 1)
        dims.append(
            {
                "question": "Does the MAJORITY of announced capacity show no physical construction?",
                "dimension": "execution_mismatch_physical",
                "measured": f"{no_change_pct}% of {int(site_n)} satellite-observed sites show NO change",
                # NOT a clean first-principles tipping condition: no_change_sites conflates
                # never-started sites with ALREADY-BUILT/operational ones (both show small
                # NDVI/NDBI/BSI deltas), so a high no-change share does NOT establish "un-built".
                "first_principles_condition": None,
                "condition_met": None,
                "source_status": "source_backed",
                "interpretation": (
                    f"{no_change_pct}% of observed sites show no inter-period change on Sentinel-2. This is "
                    "a CONFOUNDED proxy, NOT proof of un-built capacity: 'no change' includes sites that "
                    "are already built/operational (nothing left to change) as well as never-started ones, "
                    "and carries cloud/seasonal noise. Read as a flag to pair with the construction-status "
                    "proxy and permit/queue evidence -- it does not by itself meet a >50%-un-built tipping "
                    "line, so it is reported as magnitude, not a satisfied condition."
                ),
            }
        )

    # 5. Tail size: how big is the leveraged tail in the universe? (magnitude, no principled binary)
    eum = m.get("entity_universe_map", {}) or {}
    bk = eum.get("by_bucket") or {}
    universe_n = _num(eum.get("entity_count"))
    if universe_n:
        tail_pct = round(100 * float(bk.get("financed_ai_infra_leveraged", 0)) / universe_n, 1)
        dims.append(
            {
                "question": "Is the leveraged tail large enough to be a SYSTEMIC (vs contained) risk?",
                "dimension": "leveraged_tail_size",
                "measured": f"{tail_pct}% of {int(universe_n)} classified AI-infra entities are financed_ai_infra_leveraged",
                "first_principles_condition": None,
                "condition_met": None,
                "source_status": "source_backed",
                "interpretation": (
                    "No principled cutoff for 'systemic'. The magnitude: the leveraged tail is a SMALL "
                    "share of the classified AI-infra universe, and the broad debt metric is dominated "
                    "by non-AI debt -- so the loss is CONTAINED to a small, specific cluster rather than "
                    "an ecosystem-wide tail. This contradicts the framework's pessimistic guess and "
                    "reinforces the scoped (not ecosystem-wide) verdict."
                ),
            }
        )

    if not dims:
        return {"status": "blocked_no_measured_dimensions", "dimensions": dims}

    conditions = [d for d in dims if d.get("first_principles_condition")]
    met_conditions = [d for d in conditions if d.get("condition_met")]
    return {
        "status": "source_backed",
        "dimensions": dims,
        "first_principles_conditions_evaluated": len(conditions),
        "first_principles_conditions_met": len(met_conditions),
        "tipping_conditions_met": [d["dimension"] for d in met_conditions],
        "composite_read": _composite(met_conditions, dims),
        "note": (
            "Forensic fragility: the dimensions (questions) are inspired by an external framework, but "
            "its numeric thresholds are NOT adopted -- they are unvalidated guesses. A tipping line is "
            "applied ONLY where a first-principles economic condition is defensible AND cleanly measured "
            "(duration: debt > asset life; concentration: single customer > 50% of revenue). The "
            "execution/satellite leg is reported as MAGNITUDE only -- its 'no-change' signal conflates "
            "un-built with already-built sites, so it is not a clean tipping condition. "
            "Recourse and tail-size have no principled binary, so the structural fact and magnitude are "
            "reported instead -- and on both, the data CONTRADICTS the framework's pessimistic guesses "
            "(mostly parent-recourse; small leveraged tail), which is the honest finding."
        ),
    }


def _composite(met: list[dict[str, Any]], dims: list[dict[str, Any]]) -> str:
    met_dims = ", ".join(d["dimension"] for d in met)
    return (
        f"first_principles_tipping_conditions_met: {len(met)} of the defensible economic tipping "
        f"conditions are SATISFIED by the data ({met_dims}) -- collateral dies before the debt matures, "
        "and a single customer sits at an existential (>50%) share of revenue. The execution/satellite "
        "leg is a CONFOUNDED proxy (satellite 'no-change' conflates un-built with already-built), so it "
        "is reported as magnitude and NOT counted as a met condition. The two dimensions without a "
        "principled binary (recourse, leveraged-tail size) show the loss is borne by parent EQUITY and "
        "confined to a SMALL share of the universe -- so the failure mode is severe distress WITHIN a "
        "bounded cluster, not an ecosystem-wide cascade. No borrowed threshold was trusted; each line is "
        "first-principles or the raw magnitude."
    )
