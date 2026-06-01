"""
Evidence quality gates for Burry-style claims.

The final system cannot allow inferred scale estimates to masquerade as measured
facts. This module classifies evidence behind each claim and caps confidence when
the backing data is too weak for a professional-investor-grade conclusion.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from bubble.models.base import HumanReviewStatus, Provenance, SourceType

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


class EvidenceTier(StrEnum):
    """Forensic strength of the evidence supporting a claim."""

    MEASURED = "measured"
    CORROBORATED_ESTIMATE = "corroborated_estimate"
    SINGLE_SOURCE_ESTIMATE = "single_source_estimate"
    INFERRED = "inferred"
    UNSUPPORTED = "unsupported"


PRIMARY_OR_REGULATORY_SOURCE_TYPES = {
    SourceType.SEC_EDGAR,
    SourceType.FERC,
    SourceType.EIA,
    SourceType.EPA,
    SourceType.GLEIF,
    SourceType.STATE_PUC,
    SourceType.STATE_DEQ,
    SourceType.LOCAL_PLANNING,
    SourceType.GRID_QUEUE,
    SourceType.FOIA,
}


@dataclass(frozen=True)
class EvidenceRecord:
    """A compact, serializable view of a provenance record."""

    source_uri: str
    source_type: str
    confidence: float
    retrieved_at: str
    page_or_section: str | None
    human_review_status: str
    content_hash: str

    @classmethod
    def from_provenance(cls, provenance: Provenance) -> EvidenceRecord:
        return cls(
            source_uri=provenance.source_uri,
            source_type=provenance.source_type.value,
            confidence=provenance.confidence,
            retrieved_at=provenance.retrieved_at.isoformat(),
            page_or_section=provenance.page_or_section,
            human_review_status=provenance.human_review_status.value,
            content_hash=provenance.content_hash,
        )


@dataclass(frozen=True)
class ClaimEvidenceAudit:
    """Forensic audit result for one report claim or metric."""

    claim_id: str
    claim: str
    value: Any
    unit: str | None
    tier: EvidenceTier
    confidence: float
    source_count: int
    source_types: list[str]
    sources: list[EvidenceRecord]
    blocking_issues: list[str]
    eligible_for_high_confidence: bool

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["tier"] = self.tier.value
        return data


@dataclass(frozen=True)
class EvidenceSummary:
    """Rollup across the audits attached to a report."""

    audited_claims: int
    measured_claims: int
    corroborated_claims: int
    inferred_claims: int
    unsupported_claims: int
    high_confidence_eligible_claims: int
    blocking_issue_count: int
    max_permitted_report_confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EvidenceGate:
    """Classify claim evidence and enforce confidence caps."""

    def __init__(
        self,
        *,
        min_high_confidence: float = 0.75,
        min_corroborating_sources: int = 2,
    ) -> None:
        self.min_high_confidence = min_high_confidence
        self.min_corroborating_sources = min_corroborating_sources

    def audit_claim(
        self,
        *,
        claim_id: str,
        claim: str,
        value: Any,
        evidence: Sequence[Provenance] | None,
        unit: str | None = None,
        requires_corroboration: bool = False,
        high_impact: bool = True,
    ) -> ClaimEvidenceAudit:
        records = [EvidenceRecord.from_provenance(p) for p in self._dedupe(evidence or [])]
        source_count = len(records)
        source_types = sorted({record.source_type for record in records})
        confidence = round(min((record.confidence for record in records), default=0.0), 4)
        tier = self._classify(records)

        blocking_issues: list[str] = []
        if tier == EvidenceTier.UNSUPPORTED:
            blocking_issues.append("No source evidence is attached to this claim.")
        if tier == EvidenceTier.INFERRED:
            blocking_issues.append("Claim is based on inference or scaling, not measured evidence.")
        if confidence < self.min_high_confidence:
            blocking_issues.append(
                f"Evidence confidence {confidence:.2f} is below high-confidence threshold "
                f"{self.min_high_confidence:.2f}."
            )
        if requires_corroboration and source_count < self.min_corroborating_sources:
            blocking_issues.append(
                f"Claim needs {self.min_corroborating_sources} independent sources; "
                f"only {source_count} attached."
            )
        if (
            high_impact
            and records
            and not any(
                record.human_review_status == HumanReviewStatus.APPROVED.value for record in records
            )
        ):
            blocking_issues.append("High-impact claim has not been approved by a human reviewer.")

        eligible = (
            not blocking_issues
            and tier
            in {
                EvidenceTier.MEASURED,
                EvidenceTier.CORROBORATED_ESTIMATE,
                EvidenceTier.SINGLE_SOURCE_ESTIMATE,
            }
            and confidence >= self.min_high_confidence
        )

        return ClaimEvidenceAudit(
            claim_id=claim_id,
            claim=claim,
            value=value,
            unit=unit,
            tier=tier,
            confidence=confidence,
            source_count=source_count,
            source_types=source_types,
            sources=records,
            blocking_issues=blocking_issues,
            eligible_for_high_confidence=eligible,
        )

    def summarize(self, audits: Iterable[ClaimEvidenceAudit]) -> EvidenceSummary:
        audit_list = list(audits)
        blocking_issue_count = sum(len(audit.blocking_issues) for audit in audit_list)
        max_confidence = self.max_permitted_report_confidence(audit_list)
        return EvidenceSummary(
            audited_claims=len(audit_list),
            measured_claims=sum(audit.tier == EvidenceTier.MEASURED for audit in audit_list),
            corroborated_claims=sum(
                audit.tier == EvidenceTier.CORROBORATED_ESTIMATE for audit in audit_list
            ),
            inferred_claims=sum(audit.tier == EvidenceTier.INFERRED for audit in audit_list),
            unsupported_claims=sum(audit.tier == EvidenceTier.UNSUPPORTED for audit in audit_list),
            high_confidence_eligible_claims=sum(
                audit.eligible_for_high_confidence for audit in audit_list
            ),
            blocking_issue_count=blocking_issue_count,
            max_permitted_report_confidence=max_confidence,
        )

    def max_permitted_report_confidence(self, audits: Sequence[ClaimEvidenceAudit]) -> float:
        """Conservative cap for report-level confidence based on weakest critical claims."""
        if not audits:
            return 0.2
        if any(audit.tier == EvidenceTier.UNSUPPORTED for audit in audits):
            return 0.25
        if any(audit.tier == EvidenceTier.INFERRED for audit in audits):
            return 0.45
        if any(audit.blocking_issues for audit in audits):
            return 0.6
        return min(0.95, *(audit.confidence for audit in audits))

    def cap_report_confidence(
        self,
        candidate_confidence: float,
        audits: Sequence[ClaimEvidenceAudit],
    ) -> float:
        return round(min(candidate_confidence, self.max_permitted_report_confidence(audits)), 4)

    def _classify(self, records: Sequence[EvidenceRecord]) -> EvidenceTier:
        if not records:
            return EvidenceTier.UNSUPPORTED

        non_inferred = [
            record for record in records if record.source_type != SourceType.INFERRED.value
        ]
        if not non_inferred:
            return EvidenceTier.INFERRED

        primary_records = [
            record
            for record in non_inferred
            if SourceType(record.source_type) in PRIMARY_OR_REGULATORY_SOURCE_TYPES
        ]
        if len(primary_records) == len(non_inferred) and len(primary_records) == 1:
            return EvidenceTier.MEASURED
        if len(non_inferred) >= self.min_corroborating_sources:
            return EvidenceTier.CORROBORATED_ESTIMATE
        return EvidenceTier.SINGLE_SOURCE_ESTIMATE

    @staticmethod
    def _dedupe(evidence: Sequence[Provenance]) -> list[Provenance]:
        seen: set[tuple[str, str, str | None]] = set()
        deduped: list[Provenance] = []
        for provenance in evidence:
            key = (
                provenance.source_uri,
                provenance.content_hash,
                provenance.page_or_section,
            )
            if key not in seen:
                seen.add(key)
                deduped.append(provenance)
        return deduped


def inferred_estimate_provenance(
    *,
    claim_id: str,
    rationale: str,
    confidence: float = 0.45,
) -> Provenance:
    """Create explicit low-confidence provenance for a scaled or unsupported estimate."""
    source_uri = f"model:inferred_estimate:{claim_id}"
    return Provenance(
        source_uri=source_uri,
        source_type=SourceType.INFERRED,
        page_or_section=rationale,
        confidence=confidence,
        human_review_status=HumanReviewStatus.PENDING,
        content_hash=Provenance.compute_content_hash(f"{claim_id}:{rationale}:{confidence}"),
    )
