from bubble.analysis.evidence import EvidenceGate, EvidenceTier, inferred_estimate_provenance
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
