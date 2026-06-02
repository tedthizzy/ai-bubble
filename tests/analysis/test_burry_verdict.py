"""Tiered Burry verdict synthesis from verified evidence.

The honest answer is scoped: source-backed cash-flow fragility in the financed
AI-direct core (calibrated confidence, tempered by a credible bear case) vs a
NOT-established ecosystem-wide bubble. Confidence is derived transparently, not
hand-set, and never inflated past what the evidence + bear case support.
"""

from __future__ import annotations

from bubble.analysis.burry_verdict import synthesize_core_verdict


def _findings() -> list[dict[str, object]]:
    return [
        {
            "key": "bear_case_against_bubble",
            "verdict": "holds_with_caveats",
            "confidence": 0.62,
            "tier": "CORROBORATED",
            "summary": "Non-bubble view well supported.",
            "key_caveat": "10% AI-linked",
        },
        {
            "key": "refi_wall_2030_2033",
            "verdict": "holds_with_caveats",
            "confidence": 0.25,
            "tier": "CORROBORATED",
            "summary": "88% of carded debt 2030-33.",
            "key_caveat": "curated floor",
        },
        {
            "key": "take_or_pay_holes",
            "verdict": "holds_with_caveats",
            "confidence": 0.25,
            "tier": "MEASURED",
            "summary": "Shifts utilization risk; 67% Microsoft.",
            "key_caveat": "concentration",
        },
        {
            "key": "gpu_collateral_erosion",
            "verdict": "holds_with_caveats",
            "confidence": 0.25,
            "tier": "SINGLE_SOURCE",
            "summary": "Book 6yr vs faster obsolescence.",
            "key_caveat": "headline not local",
        },
    ]


def _cluster_dscr() -> dict[str, object]:
    return {
        "status": "source_backed",
        "issuers_with_usable_inputs": 11,
        "loss_making_issuer_count": 7,
        "issuers_with_ebitda_coverage_below_1": 7,
        "cluster_ebitda_interest_coverage": 1.35,
    }


def test_verdict_is_scoped_tiered_and_source_backed() -> None:
    v = synthesize_core_verdict(
        cluster_dscr=_cluster_dscr(),
        thesis_findings=_findings(),
        established_ai_usd=362_975_850_000,
        direct_ai_usd=142_030_000_000,
        not_established_pct=0.8998,
    )
    assert v["scope"] == "financed_ai_direct_core"
    assert v["core_verdict"] == "bubble_dynamics_present"
    assert v["ecosystem_verdict"] == "not_established_as_ecosystem_wide_bubble"
    # Source-backed cash-flow fragility is surfaced as a high-confidence fact.
    assert any(
        "cover interest" in f.lower() or "loss-making" in f.lower()
        for f in v["source_backed_fragility_facts"]
    )


def test_confidence_is_calibrated_not_inflated() -> None:
    v = synthesize_core_verdict(
        cluster_dscr=_cluster_dscr(),
        thesis_findings=_findings(),
        established_ai_usd=362_975_850_000,
        direct_ai_usd=142_030_000_000,
        not_established_pct=0.8998,
    )
    # Strong source-backed facts, but a credible bear case (0.62) must pull the
    # verdict confidence into a calibrated middle band -- never near-certainty.
    assert 0.5 <= v["core_verdict_confidence"] <= 0.8
    deriv = v["confidence_derivation"]
    assert deriv["bear_case_confidence"] == 0.62
    assert deriv["fragility_facts_confidence"] >= 0.75


def test_blocks_verdict_when_cluster_dscr_not_source_backed() -> None:
    v = synthesize_core_verdict(
        cluster_dscr={"status": "blocked_no_source_backed_inputs"},
        thesis_findings=_findings(),
        established_ai_usd=362_975_850_000,
        direct_ai_usd=142_030_000_000,
        not_established_pct=0.8998,
    )
    assert v["core_verdict"] == "blocked_insufficient_source_backed_cashflow"
    assert v["core_verdict_confidence"] <= 0.45


def test_crack_timing_and_weakest_links_present() -> None:
    v = synthesize_core_verdict(
        cluster_dscr=_cluster_dscr(),
        thesis_findings=_findings(),
        established_ai_usd=362_975_850_000,
        direct_ai_usd=142_030_000_000,
        not_established_pct=0.8998,
    )
    assert v["crack_timing"]["primary_window"] == "2030-2033"
    assert v["crack_timing"]["earlier_triggers"]
    assert len(v["weakest_links"]) >= 2
    assert len(v["top_risks"]) >= 3
