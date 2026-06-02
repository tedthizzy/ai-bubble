from bubble.analysis.evidence import (
    EvidenceGate,
    EvidenceTier,
    SemanticEvidenceBucket,
    inferred_estimate_provenance,
)
from bubble.models.base import HumanReviewStatus, Provenance, SourceType


def _provenance(
    source_type: SourceType,
    *,
    source_uri: str = "https://www.sec.gov/test",
    confidence: float = 0.9,
    status: HumanReviewStatus = HumanReviewStatus.APPROVED,
) -> Provenance:
    return Provenance(
        source_uri=source_uri,
        source_type=source_type,
        confidence=confidence,
        human_review_status=status,
        content_hash=Provenance.compute_content_hash(f"{source_uri}:{source_type}:{confidence}"),
    )


def test_inferred_claim_is_not_high_confidence_eligible():
    gate = EvidenceGate()
    audit = gate.audit_claim(
        claim_id="total_leverage",
        claim="Total leverage",
        value=2_000_000_000_000,
        unit="USD",
        evidence=[
            inferred_estimate_provenance(
                claim_id="total_leverage",
                rationale="Seed-count scale estimate",
                confidence=0.4,
            )
        ],
        requires_corroboration=True,
        high_impact=True,
    )

    assert audit.tier == EvidenceTier.INFERRED
    assert audit.eligible_for_high_confidence is False
    assert any("inference" in issue for issue in audit.blocking_issues)
    assert gate.cap_report_confidence(0.82, [audit]) == 0.45


def test_measured_approved_primary_source_can_support_claim():
    gate = EvidenceGate()
    audit = gate.audit_claim(
        claim_id="debt_maturity",
        claim="Debt maturity from 10-K",
        value="2027-09-30",
        evidence=[_provenance(SourceType.SEC_EDGAR)],
        high_impact=True,
    )

    assert audit.tier == EvidenceTier.MEASURED
    assert audit.eligible_for_high_confidence is True
    assert audit.blocking_issues == []


def test_corroboration_requirement_blocks_single_source_claim():
    gate = EvidenceGate()
    audit = gate.audit_claim(
        claim_id="power_risk",
        claim="Project has firm power",
        value=False,
        evidence=[_provenance(SourceType.GRID_QUEUE)],
        requires_corroboration=True,
        high_impact=True,
    )

    assert audit.tier == EvidenceTier.MEASURED
    assert audit.eligible_for_high_confidence is False
    assert any("independent sources" in issue for issue in audit.blocking_issues)


def test_semantic_gate_caps_source_backed_asset_claim():
    gate = EvidenceGate()
    audit = gate.audit_claim(
        claim_id="capital.asset_misread",
        claim="Claimed debt-like amount from asset disclosure",
        value=33_600_000_000,
        unit="USD",
        evidence=[_provenance(SourceType.SEC_EDGAR, confidence=0.92)],
        high_impact=True,
        semantic_text=(
            "The unpaid principal balance of loans held for investment was "
            "$33.6 billion as of quarter end."
        ),
    )

    assert audit.tier == EvidenceTier.MEASURED
    assert audit.confidence == 0.92
    assert audit.semantic_bucket == SemanticEvidenceBucket.ASSET_OR_CAPACITY
    assert audit.effective_confidence == 0.3
    assert audit.eligible_for_high_confidence is False
    assert any("asset_or_capacity" in issue for issue in audit.blocking_issues)
    assert gate.cap_report_confidence(0.82, [audit]) == 0.3


def test_semantic_gate_preserves_committed_debt_claim():
    gate = EvidenceGate()
    audit = gate.audit_claim(
        claim_id="capital.real_debt",
        claim="Claimed debt-like amount from credit agreement",
        value=5_000_000_000,
        unit="USD",
        evidence=[_provenance(SourceType.SEC_EDGAR, confidence=0.9)],
        high_impact=True,
        semantic_text=(
            "The borrower entered into a senior secured term loan credit "
            "agreement with an aggregate principal amount of $5.0 billion."
        ),
    )

    assert audit.semantic_bucket == SemanticEvidenceBucket.COMMITTED_DEBT
    assert audit.effective_confidence == 0.9
    assert audit.eligible_for_high_confidence is True
    assert audit.blocking_issues == []


def test_semantic_gate_preserves_terse_note_issuance_claim():
    gate = EvidenceGate()
    audit = gate.audit_claim(
        claim_id="capital.note_issuance",
        claim="Claimed note amount from offering document",
        value=6_000_000_000,
        unit="USD",
        evidence=[_provenance(SourceType.SEC_EDGAR, confidence=0.9)],
        high_impact=True,
        semantic_text=(
            "The Notes were issued pursuant to an Underwriting Agreement "
            "among the Company and the underwriters."
        ),
    )

    assert audit.semantic_bucket == SemanticEvidenceBucket.COMMITTED_DEBT
    assert audit.effective_confidence == 0.9
    assert audit.eligible_for_high_confidence is True


def test_semantic_gate_preserves_new_note_global_note_claim():
    gate = EvidenceGate()
    audit = gate.audit_claim(
        claim_id="capital.new_notes",
        claim="Claimed note amount from exchange document",
        value=7_800_000_000,
        unit="USD",
        evidence=[_provenance(SourceType.SEC_EDGAR, confidence=0.9)],
        high_impact=True,
        semantic_text=(
            "The New Notes will be evidenced by a global note deposited "
            "with the trustee for the New Notes, as custodian for DTC."
        ),
    )

    assert audit.semantic_bucket == SemanticEvidenceBucket.COMMITTED_DEBT
    assert audit.effective_confidence == 0.9
    assert audit.eligible_for_high_confidence is True


def test_semantic_gate_preserves_bond_and_guarantee_terms_claim():
    gate = EvidenceGate()
    audit = gate.audit_claim(
        claim_id="capital.bond_guarantee",
        claim="Claimed bond amount from prospectus supplement",
        value=7_000_000_000,
        unit="USD",
        evidence=[_provenance(SourceType.SEC_EDGAR, confidence=0.9)],
        high_impact=True,
        semantic_text=(
            "All bonds issued or to be issued under the Mortgage, including "
            "the New Bonds offered by this prospectus, are referred to herein "
            "as Collateral Trust Mortgage Bonds. Full and unconditional "
            "guarantees of the principal, interest, premium, if any, are "
            "given by the parent guarantors."
        ),
    )

    assert audit.semantic_bucket == SemanticEvidenceBucket.COMMITTED_DEBT
    assert audit.effective_confidence == 0.9
    assert audit.eligible_for_high_confidence is True


def test_semantic_gate_preserves_credit_and_guaranty_facility_claim():
    gate = EvidenceGate()
    audit = gate.audit_claim(
        claim_id="capital.credit_guaranty",
        claim="Claimed facility amount from credit agreement",
        value=2_350_000_000,
        unit="USD",
        evidence=[_provenance(SourceType.SEC_EDGAR, confidence=0.9)],
        high_impact=True,
        semantic_text=(
            "Credit and Guaranty Agreement by and among the borrower, "
            "subsidiary guarantors, lenders party thereto and Sumitomo "
            "Mitsui Banking Corporation as administrative agent."
        ),
    )

    assert audit.semantic_bucket == SemanticEvidenceBucket.COMMITTED_DEBT
    assert audit.effective_confidence == 0.9
    assert audit.eligible_for_high_confidence is True


def test_semantic_gate_caps_bank_financial_metric_claim():
    gate = EvidenceGate()
    audit = gate.audit_claim(
        claim_id="capital.bank_presentation_metric",
        claim="Claimed note amount from bank financial metric slide",
        value=41_594_000_000,
        unit="USD",
        evidence=[_provenance(SourceType.SEC_EDGAR, confidence=0.9)],
        high_impact=True,
        semantic_text=(
            "Net income of $109.8 million, return on average assets of "
            "1.65%, tangible book value growth and efficiency ratio improved."
        ),
    )

    assert audit.semantic_bucket == SemanticEvidenceBucket.ASSET_OR_CAPACITY
    assert audit.effective_confidence == 0.3
    assert audit.eligible_for_high_confidence is False


def test_semantic_gate_caps_quarterly_earnings_header_claim():
    gate = EvidenceGate()

    for semantic_text in (
        "PennyMac Mortgage Investment Trust Reports Fourth Quarter and Full-Year 2025 Results",
        "Results of Operations and Financial Condition. On October 28, 2025, Carrier Global Corp.",
        "Today reported net income attributable to common shareholders of $312.4 million.",
    ):
        audit = gate.audit_claim(
            claim_id="capital.earnings_header",
            claim="Claimed debt-like amount from earnings-release header",
            value=5_500_000_000,
            unit="USD",
            evidence=[_provenance(SourceType.SEC_EDGAR, confidence=0.9)],
            high_impact=True,
            semantic_text=semantic_text,
        )

        assert audit.semantic_bucket == SemanticEvidenceBucket.BOILERPLATE_ONLY
        assert audit.effective_confidence == 0.25
        assert audit.eligible_for_high_confidence is False


def test_semantic_gate_keeps_notes_due_negative_control_committed():
    gate = EvidenceGate()
    audit = gate.audit_claim(
        claim_id="capital.notes_due",
        claim="Claimed note amount from offering terms",
        value=1_000_000_000,
        unit="USD",
        evidence=[_provenance(SourceType.SEC_EDGAR, confidence=0.9)],
        high_impact=True,
        semantic_text=(
            "Senior notes due 2030 in an aggregate principal amount of "
            "$1.0 billion."
        ),
    )

    assert audit.semantic_bucket == SemanticEvidenceBucket.COMMITTED_DEBT
    assert audit.effective_confidence == 0.9
    assert audit.eligible_for_high_confidence is True


def test_semantic_gate_caps_equity_or_mortgage_production_claim():
    gate = EvidenceGate()
    equity_audit = gate.audit_claim(
        claim_id="capital.equity_misread",
        claim="Claimed debt-like amount from equity snippet",
        value=12_023_000_000,
        unit="USD",
        evidence=[_provenance(SourceType.SEC_EDGAR, confidence=0.92)],
        high_impact=True,
        semantic_text=(
            "The bonds convert into Shares of Alibaba Health Information "
            "Technology Limited."
        ),
    )
    production_audit = gate.audit_claim(
        claim_id="capital.production_misread",
        claim="Claimed debt-like amount from mortgage production volume",
        value=6_260_000_000,
        unit="USD",
        evidence=[_provenance(SourceType.SEC_EDGAR, confidence=0.92)],
        high_impact=True,
        semantic_text="Mortgage closed loan production for the year ended December 31.",
    )

    assert equity_audit.semantic_bucket == SemanticEvidenceBucket.EQUITY_OR_PRODUCTION
    assert equity_audit.effective_confidence == 0.3
    assert equity_audit.eligible_for_high_confidence is False
    assert any("equity_or_production" in issue for issue in equity_audit.blocking_issues)
    assert production_audit.semantic_bucket == SemanticEvidenceBucket.EQUITY_OR_PRODUCTION
    assert production_audit.effective_confidence == 0.3


def test_semantic_gate_preserves_convertible_debt_with_share_language():
    gate = EvidenceGate()
    audit = gate.audit_claim(
        claim_id="capital.convertible_notes",
        claim="Claimed debt-like amount from convertible note clause",
        value=1_500_000_000,
        unit="USD",
        evidence=[_provenance(SourceType.SEC_EDGAR, confidence=0.9)],
        high_impact=True,
        semantic_text=(
            "The company issued senior unsecured convertible notes with a "
            "conversion price for shares of common stock."
        ),
    )

    assert audit.semantic_bucket == SemanticEvidenceBucket.COMMITTED_DEBT
    assert audit.effective_confidence == 0.9
    assert audit.eligible_for_high_confidence is True


def test_semantic_required_routes_indeterminate_claim_to_review():
    gate = EvidenceGate()
    audit = gate.audit_claim(
        claim_id="capital.fragment",
        claim="Claimed amount from fragment",
        value=1_200_000_000,
        unit="USD",
        evidence=[_provenance(SourceType.SEC_EDGAR, confidence=0.9)],
        high_impact=True,
        semantic_text="The total was $1.2 billion as of December 31.",
        semantic_required=True,
    )

    assert audit.semantic_bucket == SemanticEvidenceBucket.INDETERMINATE
    assert audit.effective_confidence == 0.5
    assert audit.eligible_for_high_confidence is False
    assert any("indeterminate" in issue for issue in audit.blocking_issues)
