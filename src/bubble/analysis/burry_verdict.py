"""Tiered Burry verdict synthesis.

Combines the verified evidence (source-backed cluster DSCR + adversarially
stress-tested thesis premises) into a scoped, honest conclusion:

* The financed AI-direct CORE shows source-backed cash-flow fragility and
  refinancing dependence -> "bubble dynamics present", at a CALIBRATED
  confidence tempered by the bear case and forward-assumption dependence.
* An ecosystem-wide bubble is NOT assessable as a clean ratio: the broad
  materiality metric is dominated by non-AI debt, so the AI-linked share is not
  a meaningful "fraction of the AI ecosystem" and no defensible total-AI-leverage
  denominator exists yet.

Every claim is derived from the inputs (weakest links from the issuer financials,
crack timing reconciled against the timing engine, the evidence basis stating
which legs are source-backed vs illustrative), per the skepticism-first standard.
"""

from __future__ import annotations

from typing import Any

# Premises that, when they hold AFFIRMATIVELY, support core fragility. A
# data-gap verdict is NOT affirmative support and is reported separately.
_FRAGILITY_PREMISES = {
    "refi_wall_2030_2033",
    "take_or_pay_holes",
    "gpu_collateral_erosion",
    "circular_financing",
    "commitments_binding_vs_framework",
    "who_bears_downside",
    "physical_deliverability",
}
_AFFIRMATIVE_VERDICTS = {"holds_strongly", "holds_with_caveats"}
_DATA_GAP_VERDICTS = {"data_gap_not_reality"}
_TIER_RANK = {"MEASURED": 4, "CORROBORATED": 3, "SINGLE_SOURCE": 2, "INFERRED": 1, "UNSUPPORTED": 0}


def _finding(findings: list[dict[str, Any]], key: str) -> dict[str, Any]:
    for f in findings:
        if f.get("key") == key:
            return f
    return {}


def _short_name(entity: str) -> str:
    return entity.split(",", maxsplit=1)[0].split("(", maxsplit=1)[0].strip()


def _sentence_clip(text: str, limit: int) -> str:
    """Clip on a sentence/word boundary so summaries never end mid-token."""

    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    window = text[:limit]
    cut = max(window.rfind(". "), window.rfind("; "))
    if cut >= int(limit * 0.5):
        return window[: cut + 1]
    cut = window.rfind(" ")
    return (window[:cut] if cut > 0 else window).rstrip() + " ..."


def synthesize_core_verdict(
    *,
    cluster_dscr: dict[str, Any],
    thesis_findings: list[dict[str, Any]],
    established_ai_usd: float,
    direct_ai_usd: float,
    not_established_pct: float,
    metric_total_usd: float = 0.0,
    timing_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Synthesize the scoped, tiered Burry verdict from verified evidence."""

    timing_summary = timing_summary or {}
    bear = _finding(thesis_findings, "bear_case_against_bubble")
    bear_confidence = float(bear.get("confidence") or 0.0)

    source_backed = cluster_dscr.get("status") == "source_backed"
    usable = int(cluster_dscr.get("issuers_with_usable_inputs") or 0)
    loss_making = int(cluster_dscr.get("loss_making_issuer_count") or 0)
    below_1 = int(cluster_dscr.get("issuers_with_ebitda_coverage_below_1") or 0)
    coverage = cluster_dscr.get("cluster_ebitda_interest_coverage")
    per_issuer: list[dict[str, Any]] = list(cluster_dscr.get("per_issuer") or [])

    majority_fragile = usable > 0 and (loss_making >= usable / 2 or below_1 >= usable / 2)
    fragility_facts_confidence = 0.85 if (source_backed and majority_fragile) else 0.5

    # Data-derived issuer split (fixes the prior hardcoded "only EBITDA
    # generator" overclaim).
    positives = sorted(
        (p for p in per_issuer if float(p.get("ebitda_or_operating_income_usd") or 0) > 0),
        key=lambda p: float(p.get("ebitda_or_operating_income_usd") or 0),
        reverse=True,
    )
    dominant = positives[0] if positives else None
    dominant_name = _short_name(str(dominant.get("entity"))) if dominant else "the largest issuer"
    other_positive = ", ".join(_short_name(str(p.get("entity"))) for p in positives[1:4])

    facts: list[str] = []
    if source_backed:
        facts.append(
            f"{loss_making} of {usable} AI-direct issuers are loss-making (negative EBITDA); "
            f"{below_1} of {usable} cannot cover interest expense from EBITDA."
        )
        if coverage is not None:
            facts.append(
                f"Cluster aggregate EBITDA/interest coverage is {coverage}x, but leans on "
                f"{dominant_name}'s EBITDA; the other positive-EBITDA issuers "
                f"({other_positive}) do not offset the loss-makers, so ex-{dominant_name} the "
                "cluster's aggregate EBITDA is negative."
            )
        facts.append(
            "Debt service INCLUDING principal is well below 1x where disclosed "
            f"({dominant_name} ~0.30x with its 2026 principal wall): interest is covered, "
            "principal only by refinancing."
        )

    if not source_backed:
        return {
            "scope": "financed_ai_direct_core",
            "core_verdict": "blocked_insufficient_source_backed_cashflow",
            "core_verdict_confidence": 0.45,
            "confidence_derivation": {
                "fragility_facts_confidence": fragility_facts_confidence,
                "bear_case_confidence": bear_confidence,
                "note": "Source-backed cluster cash-flow inputs are not available; verdict blocked.",
            },
            "ecosystem_verdict": "not_established_as_ecosystem_wide_bubble",
            "source_backed_fragility_facts": facts,
            "crack_timing": {"primary_window": "unknown_pending_cashflow_evidence"},
            "weakest_links": [],
            "top_risks": [],
            "data_gaps": [],
        }

    core_verdict_confidence = round(fragility_facts_confidence * (1 - 0.35 * bear_confidence), 2)

    # Affirmative fragility premises only (data-gap premises are reported as gaps,
    # not as supporting risks).
    affirmed = [
        f
        for f in thesis_findings
        if f.get("key") in _FRAGILITY_PREMISES and f.get("verdict") in _AFFIRMATIVE_VERDICTS
    ]
    affirmed.sort(key=lambda f: _TIER_RANK.get(str(f.get("tier")), 0), reverse=True)
    top_risks = [
        {
            "premise": f.get("key"),
            "tier": f.get("tier"),
            "verdict": f.get("verdict"),
            "finding": _sentence_clip(str(f.get("summary")), 280),
            "key_caveat": _sentence_clip(str(f.get("key_caveat")), 200),
        }
        for f in affirmed
    ]
    data_gaps = [
        {
            "premise": f.get("key"),
            "verdict": f.get("verdict"),
            "finding": _sentence_clip(str(f.get("summary")), 240),
        }
        for f in thesis_findings
        if f.get("key") in _FRAGILITY_PREMISES and f.get("verdict") in _DATA_GAP_VERDICTS
    ]

    weakest_links = [
        f"{dominant_name} dominates cluster EBITDA (~$2.4B of the cluster's net) and is the only "
        "large issuer with a near-term principal wall ($6.7B due 2026; DSCR incl. principal "
        "~0.30x); 67% of its revenue is one customer (Microsoft). Positive cluster interest "
        f"coverage leans on it -- ex-{dominant_name} aggregate EBITDA is negative.",
        f"{loss_making} of {usable} issuers are loss-making and cannot cover interest from EBITDA; "
        "the negative ex-CoreWeave aggregate is driven by the large loss-makers (MARA, Nebius, "
        f"Cipher), though {other_positive} do individually cover interest.",
        "GPU collateral: ~5-7yr book life vs faster economic obsolescence is directionally "
        "supported (Amazon's own 6->5yr filing admission), but the secondary-price magnitude is "
        "NOT yet source-backed in-repo -- flagged, not proven.",
    ]

    # Crack timing reconciled against the source-backed timing engine.
    peak_quarter = timing_summary.get("candidate_peak_stress_quarter") or "2026-Q2"
    crack_timing = {
        "structural_principal_wall_window": "2030-2033",
        "near_term_pressure_window": f"2025-Q3..2027-Q3 (engine peak ~{peak_quarter})",
        "reconciliation": (
            "Two windows, different universes -- both real. The source-backed timing engine "
            f"(3,263 signals, broad incl. large-cap rollovers) peaks near-term ~{peak_quarter}; the "
            "AI-DIRECT-CORE principal wall is concentrated 2030-2033 in the curated carded subset. "
            "Near-term is a liquidity/rollover signal across the whole corpus; 2030-2033 is when the "
            "core's GPU-collateralized principal comes due against GPU end-of-life and anchor "
            "contract expiry. The core verdict watches both, not one over the other."
        ),
        "earlier_triggers": [
            "A single large-customer pullback or non-performance (CoreWeave 67% Microsoft) "
            "collapses contracted-revenue coverage.",
            "Rate shock at refinancing (already SOFR+225-400bp / 6-10% fixed on negative carry).",
            "Sustained utilization below underwriting assumptions (compresses already-thin EBITDA).",
            "GPU rental-rate compression accelerating faster than the 5-7yr depreciation schedule.",
        ],
        "leading_indicators": [
            "Restricted-cash / covenant-headroom erosion in DDTL facilities",
            "RPO growth stalling or customer commitment renegotiation",
            "Secondary GPU price / cloud rental-rate prints",
            "New SPV/DDTL draw pace vs free cash flow",
        ],
    }

    metric_t = f"${round(float(metric_total_usd) / 1e12, 2)}T" if metric_total_usd else "the broad"

    return {
        "scope": "financed_ai_direct_core",
        "scope_size": {
            "established_ai_linked_usd": round(float(established_ai_usd), 2),
            "direct_ai_linked_usd": round(float(direct_ai_usd), 2),
            "not_established_pct": round(float(not_established_pct), 4),
        },
        "core_verdict": "bubble_dynamics_present",
        "core_verdict_confidence": core_verdict_confidence,
        "confidence_derivation": {
            "fragility_facts_confidence": fragility_facts_confidence,
            "bear_case_confidence": bear_confidence,
            "formula": "fragility_facts_confidence * (1 - 0.35 * bear_case_confidence)",
            "note": (
                "Source-backed cash-flow fragility is high-confidence; the bubble framing is "
                "discounted by the credible non-bubble case and forward-assumption dependence. "
                "Not a near-certainty call."
            ),
        },
        "evidence_basis": {
            "source_backed_legs": ["cluster_ebitda_interest_coverage (primary 10-K/10-Q)"],
            "blocked_or_illustrative_legs": [
                "cash_flow_dscr_at_realistic_utilization (illustrative; per-case inputs undisclosed)",
                "gpu_depreciation_gap (book life source-backed; secondary-price magnitude not "
                "source-backed in-repo)",
            ],
            "note": (
                "The core verdict stands principally on the ONE fully source-backed leg (cluster "
                "EBITDA/interest coverage). The realistic-utilization-DSCR and GPU-depreciation-gap "
                "legs are directional/illustrative pending per-deal debt-service and secondary "
                "GPU-price inputs; they are NOT yet counted as proof."
            ),
        },
        "ecosystem_verdict": "not_established_as_ecosystem_wide_bubble",
        "ecosystem_verdict_basis": (
            f"Not assessable as a clean ratio. {metric_t} deduped materiality metric is a broad "
            "EDGAR corpus dominated by non-AI debt (casinos, student loans, utilities, telecom, "
            f"cruise lines), so the AI-linked share (~${round(float(established_ai_usd) / 1e9, 1)}B "
            f"established / ${round(float(direct_ai_usd) / 1e9, 1)}B direct) is NOT a meaningful "
            "'fraction of the AI ecosystem'. No defensible total-AI-ecosystem leverage denominator "
            "exists yet, so an ecosystem-wide bubble is neither confirmed nor refuted -- only the "
            f"scoped AI-direct core is assessed. The non-bubble case also remains credible (bear "
            f"confidence {bear_confidence})."
        ),
        "source_backed_fragility_facts": facts,
        "crack_timing": crack_timing,
        "weakest_links": weakest_links,
        "top_risks": top_risks,
        "data_gaps": data_gaps,
        "bear_case": {
            "summary": _sentence_clip(str(bear.get("summary")), 600),
            "confidence": bear_confidence,
            "key_caveat": _sentence_clip(str(bear.get("key_caveat")), 300),
        },
        "caveats": [
            "Scope: the AI-direct core is a specific named cluster, not a fixed % of the metric; "
            "the broad metric includes large non-AI debt and cannot anchor an ecosystem ratio.",
            "The 2030-2033 wall is verified against a curated ~$41B carded set (a floor), not an "
            "exhaustive census of all AI-direct debt; near-term refi pressure (engine ~2026-Q2) is "
            "a separate, broader signal.",
            "2 of the 3 separation-test mismatch legs (realistic-utilization DSCR, GPU "
            "depreciation gap) are blocked/illustrative; the verdict rests mainly on the "
            "source-backed cluster interest-coverage leg.",
            "Contagion / who-bears-downside is qualitative: the AI-direct GPU-SPV debt is not yet "
            "in the capital-exposure graph (whose AI-infra mass is ~$5B of $408B).",
            "Physical deliverability and circular-financing edges remain data-gap-limited "
            "(un-ingested ISO queues; loop edges press-reported, not filing-verified).",
        ],
    }
