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
        {
            "key": "physical_deliverability",
            "verdict": "data_gap_not_reality",
            "confidence": 0.9,
            "tier": "MEASURED",
            "summary": "0.5% is a join artifact; ISO queues un-ingested.",
            "key_caveat": "mechanically near-zero",
        },
    ]


def _cluster_dscr() -> dict[str, object]:
    return {
        "status": "source_backed",
        "issuers_with_usable_inputs": 11,
        "loss_making_issuer_count": 7,
        "issuers_with_ebitda_coverage_below_1": 7,
        "cluster_ebitda_interest_coverage": 1.35,
        "per_issuer": [
            {"entity": "CoreWeave, Inc.", "ebitda_or_operating_income_usd": 2_408_000_000},
            {"entity": "CleanSpark, Inc.", "ebitda_or_operating_income_usd": 667_300_000},
            {
                "entity": "Bitdeer Technologies Group (BTDR)",
                "ebitda_or_operating_income_usd": 327_800_000,
            },
            {"entity": "IREN Limited", "ebitda_or_operating_income_usd": 278_200_000},
            {"entity": "MARA Holdings, Inc.", "ebitda_or_operating_income_usd": -589_000_000},
            {"entity": "TeraWulf Inc.", "ebitda_or_operating_income_usd": -20_000_000},
        ],
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


def test_crack_timing_uses_real_census_and_corrects_the_88pct_cliff() -> None:
    census = {
        "status": "source_backed",
        "cluster_total_debt_usd": 54_800_000_000,
        "issuer_count": 11,
        "scheduled_maturities_usd": 50_300_000_000,
        "wall_2030_2033_pct_of_scheduled": 40.0,
        "near_term_2025_2027_pct_of_scheduled": 29.0,
        "peak_maturity_year": "y2030",
        "peak_maturity_usd": 10_300_000_000,
        "maturity_schedule_usd_by_year": {"y2030": 10_300_000_000},
    }
    v = synthesize_core_verdict(
        cluster_dscr=_cluster_dscr(),
        thesis_findings=_findings(),
        established_ai_usd=362_975_850_000,
        direct_ai_usd=142_030_000_000,
        not_established_pct=0.8998,
        timing_summary={"candidate_peak_stress_quarter": "2026-Q2"},
        debt_census=census,
    )
    ct = v["crack_timing"]
    # Real census: spread, not an 88% cliff.
    assert ct["pct_2030_2033"] == 40.0
    assert ct["pct_near_term_2025_2027"] == 29.0
    assert ct["peak_maturity_year"] == "2030"
    assert "88% cliff" in ct["maturity_profile"] or "NOT an 88% cliff" in ct["maturity_profile"]
    assert "2026-Q2" in ct["near_term_pressure_window"]
    assert ct["earlier_triggers"]
    # The "how large" scoped answer is now the source-backed cluster debt total.
    assert v["how_large_scoped_core"]["cluster_total_debt_usd"] == 54_800_000_000
    assert len(v["weakest_links"]) >= 2
    assert len(v["top_risks"]) >= 2


def test_data_gap_premises_are_separated_not_counted_as_support() -> None:
    v = synthesize_core_verdict(
        cluster_dscr=_cluster_dscr(),
        thesis_findings=_findings(),
        established_ai_usd=362_975_850_000,
        direct_ai_usd=142_030_000_000,
        not_established_pct=0.8998,
    )
    risk_premises = {r["premise"] for r in v["top_risks"]}
    gap_premises = {g["premise"] for g in v["data_gaps"]}
    # A data-gap premise must NOT appear among the affirmative top risks.
    assert "physical_deliverability" not in risk_premises
    assert "physical_deliverability" in gap_premises


def test_weakest_links_do_not_overclaim_only_generator() -> None:
    v = synthesize_core_verdict(
        cluster_dscr=_cluster_dscr(),
        thesis_findings=_findings(),
        established_ai_usd=362_975_850_000,
        direct_ai_usd=142_030_000_000,
        not_established_pct=0.8998,
    )
    blob = " ".join(v["weakest_links"]).lower()
    assert "only ebitda generator" not in blob
    assert "the cluster's only" not in blob
    # The other positive-EBITDA issuers are acknowledged.
    assert "cleanspark" in blob or "bitdeer" in blob or "iren" in blob


def test_ecosystem_basis_does_not_use_junk_percentage_inference() -> None:
    v = synthesize_core_verdict(
        cluster_dscr=_cluster_dscr(),
        thesis_findings=_findings(),
        established_ai_usd=362_975_850_000,
        direct_ai_usd=142_030_000_000,
        not_established_pct=0.8998,
        metric_total_usd=3_622_011_629_458.83,
    )
    basis = v["ecosystem_verdict_basis"].lower()
    # The honest framing names the denominator pollution, not a clean ratio.
    assert "non-ai" in basis or "non-ai debt" in basis
    assert "denominator" in basis


def test_bear_case_summary_is_not_truncated_mid_token() -> None:
    long_summary = (
        "The non-bubble view is well supported by primary data; after scanning 197,243 filings "
        "the engine caps confidence at 25% and concludes the final call is not yet supported, "
        "with only $362.98B established and just $142B direct AI-linked exposure remaining."
    )
    findings = _findings()
    findings[0]["summary"] = long_summary
    v = synthesize_core_verdict(
        cluster_dscr=_cluster_dscr(),
        thesis_findings=findings,
        established_ai_usd=362_975_850_000,
        direct_ai_usd=142_030_000_000,
        not_established_pct=0.8998,
    )
    summary = v["bear_case"]["summary"]
    # Never ends mid-word: either complete, or a clean boundary + ellipsis.
    assert summary.endswith(".") or summary.endswith(" ...")
    assert "$14 " not in summary and not summary.endswith("$14")


def test_gpu_leg_upgrades_evidence_basis_to_two_source_backed_legs() -> None:
    one = synthesize_core_verdict(
        cluster_dscr=_cluster_dscr(),
        thesis_findings=_findings(),
        established_ai_usd=362_975_850_000,
        direct_ai_usd=142_030_000_000,
        not_established_pct=0.8998,
        gpu_gap_source_backed=False,
    )
    two = synthesize_core_verdict(
        cluster_dscr=_cluster_dscr(),
        thesis_findings=_findings(),
        established_ai_usd=362_975_850_000,
        direct_ai_usd=142_030_000_000,
        not_established_pct=0.8998,
        gpu_gap_source_backed=True,
    )
    assert len(one["evidence_basis"]["source_backed_legs"]) == 1
    assert len(two["evidence_basis"]["source_backed_legs"]) == 2
    assert any("gpu" in leg.lower() for leg in two["evidence_basis"]["source_backed_legs"])
    assert "2 source-backed" in two["evidence_basis"]["note"]
