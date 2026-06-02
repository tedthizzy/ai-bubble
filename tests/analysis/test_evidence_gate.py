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
