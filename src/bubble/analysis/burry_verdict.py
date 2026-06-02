"""Tiered Burry verdict synthesis.

Combines the verified evidence (source-backed cluster DSCR + adversarially
stress-tested thesis premises) into a scoped, honest conclusion:

* The financed AI-direct CORE shows source-backed cash-flow fragility and
  refinancing dependence -> "bubble dynamics present", at a CALIBRATED
  confidence that is tempered by the strength of the bear case and the
  forward-assumption dependence (never inflated to near-certainty).
* The broad ecosystem is NOT established as a bubble (only a small fraction of
  the metric is AI-linked; the non-bubble case is credible).

Confidence is derived transparently from the inputs, with the components shown,
per the skepticism-first / every-number-has-a-source standard.
"""

from __future__ import annotations

from typing import Any

# Premises whose holding supports core fragility (the bear case is handled
# separately as the explicit counterweight).
_FRAGILITY_PREMISES = {
    "refi_wall_2030_2033",
    "take_or_pay_holes",
    "gpu_collateral_erosion",
    "circular_financing",
    "commitments_binding_vs_framework",
    "who_bears_downside",
    "physical_deliverability",
}
_HOLDING_VERDICTS = {"holds_strongly", "holds_with_caveats", "data_gap_not_reality"}


def _finding(findings: list[dict[str, Any]], key: str) -> dict[str, Any]:
    for f in findings:
        if f.get("key") == key:
            return f
    return {}


def synthesize_core_verdict(
    *,
    cluster_dscr: dict[str, Any],
    thesis_findings: list[dict[str, Any]],
    established_ai_usd: float,
    direct_ai_usd: float,
    not_established_pct: float,
) -> dict[str, Any]:
    """Synthesize the scoped, tiered Burry verdict from verified evidence."""

    bear = _finding(thesis_findings, "bear_case_against_bubble")
    bear_confidence = float(bear.get("confidence") or 0.0)

    source_backed = cluster_dscr.get("status") == "source_backed"
    usable = int(cluster_dscr.get("issuers_with_usable_inputs") or 0)
    loss_making = int(cluster_dscr.get("loss_making_issuer_count") or 0)
    below_1 = int(cluster_dscr.get("issuers_with_ebitda_coverage_below_1") or 0)
    coverage = cluster_dscr.get("cluster_ebitda_interest_coverage")

    # The fragility FACTS are source-backed (primary 10-Ks, adversarially
    # verified). Their confidence is high when the cluster is majority
    # loss-making / sub-1 interest coverage.
    majority_fragile = usable > 0 and (loss_making >= usable / 2 or below_1 >= usable / 2)
    fragility_facts_confidence = 0.85 if (source_backed and majority_fragile) else 0.5

    facts: list[str] = []
    if source_backed:
        facts.append(
            f"{loss_making} of {usable} AI-direct issuers are loss-making (negative EBITDA); "
            f"{below_1} of {usable} cannot cover interest expense from EBITDA."
        )
        if coverage is not None:
            facts.append(
                f"Cluster aggregate EBITDA/interest coverage is {coverage}x, propped by one "
                "issuer (CoreWeave); ex-CoreWeave the cluster's aggregate EBITDA is negative."
            )
        facts.append(
            "Debt service including principal is well below 1x where disclosed (CoreWeave ~0.30x "
            "with its 2026 principal wall): interest is covered, principal only by refinancing."
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
        }

    # Verdict confidence: source-backed fragility, DISCOUNTED by how credible the
    # non-bubble (bear) case is. A strong bear case must pull the bubble call
    # away from certainty even when the facts are solid.
    core_verdict_confidence = round(fragility_facts_confidence * (1 - 0.35 * bear_confidence), 2)

    # Top risks = the holding fragility premises, ranked by tier strength.
    tier_rank = {
        "MEASURED": 4,
        "CORROBORATED": 3,
        "SINGLE_SOURCE": 2,
        "INFERRED": 1,
        "UNSUPPORTED": 0,
    }
    holding = [
        f
        for f in thesis_findings
        if f.get("key") in _FRAGILITY_PREMISES and f.get("verdict") in _HOLDING_VERDICTS
    ]
    holding.sort(key=lambda f: tier_rank.get(str(f.get("tier")), 0), reverse=True)
    top_risks = [
        {
            "premise": f.get("key"),
            "tier": f.get("tier"),
            "verdict": f.get("verdict"),
            "finding": (f.get("summary") or "")[:280],
            "key_caveat": (f.get("key_caveat") or "")[:200],
        }
        for f in holding
    ]

    weakest_links = [
        "CoreWeave: the cluster's only EBITDA generator carries the largest debt and a $6.7B "
        "2026 principal wall (DSCR incl. principal ~0.30x); 67% of its revenue is one customer "
        "(Microsoft). The whole cluster's positive interest coverage depends on it.",
        "The ex-CoreWeave miner/neocloud issuers run negative aggregate EBITDA and cannot cover "
        "interest from operations — pure refinancing/equity-raise dependence.",
        "GPU collateral: ~6yr book life vs faster economic obsolescence (Amazon's own 6->5yr "
        "filing admission; H100 rents roughly halved) erodes the secured creditors' coverage.",
    ]

    crack_timing = {
        "primary_window": "2030-2033",
        "rationale": (
            "Convergence: ~88% of carded AI-direct debt matures 2030-2033 (peak 2030-32), "
            "coinciding with GPU end-of-economic-life and anchor take-or-pay contract expiry, "
            "while issuers cannot retire principal from operations."
        ),
        "earlier_triggers": [
            "A single large-customer pullback or non-performance (extreme concentration: "
            "CoreWeave 67% Microsoft) collapses contracted-revenue coverage.",
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
        "ecosystem_verdict": "not_established_as_ecosystem_wide_bubble",
        "ecosystem_verdict_basis": (
            f"Only ~{round((1 - float(not_established_pct)) * 100, 1)}% of the deduped materiality "
            f"metric is AI-linked (${round(float(established_ai_usd) / 1e9, 1)}B established, "
            f"${round(float(direct_ai_usd) / 1e9, 1)}B direct); the non-bubble case is credible "
            f"(bear confidence {bear_confidence})."
        ),
        "source_backed_fragility_facts": facts,
        "crack_timing": crack_timing,
        "weakest_links": weakest_links,
        "top_risks": top_risks,
        "bear_case": {
            "summary": (bear.get("summary") or "")[:400],
            "confidence": bear_confidence,
            "key_caveat": (bear.get("key_caveat") or "")[:200],
        },
        "caveats": [
            "Scope: the AI-direct core is ~10% of the broad metric; this verdict does NOT claim an "
            "ecosystem-wide bubble.",
            "The 2030-2033 wall is verified against a curated ~$41B carded set (a floor), not an "
            "exhaustive census of all AI-direct debt.",
            "Physical deliverability and circular-financing edges remain data-gap-limited "
            "(un-ingested ISO queues; loop edges press-reported, not filing-verified).",
        ],
    }
