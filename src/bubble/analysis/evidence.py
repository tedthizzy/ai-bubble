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


class SemanticEvidenceBucket(StrEnum):
    """Whether source text is semantically consistent with the claim domain."""

    NOT_EVALUATED = "not_evaluated"
    COMMITTED_DEBT = "committed_debt"
    ASSET_OR_CAPACITY = "asset_or_capacity"
    EQUITY_OR_PRODUCTION = "equity_or_production"
    BOILERPLATE_ONLY = "boilerplate_only"
    INDETERMINATE = "indeterminate"


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

COMMITTED_DEBT_MARKERS = (
    "credit agreement",
    "credit and guaranty agreement",
    "term loan",
    "revolving credit",
    "revolving facility",
    "senior notes",
    "secured notes",
    "unsecured notes",
    "senior unsecured",
    "indenture",
    "underwriting agreement",
    "first mortgage bond",
    "aggregate principal amount",
    "principal amount of",
    "payment of principal",
    "bridge facility",
    "bridge loan",
    "loan facility",
    "debt facility",
    "promissory note",
    "debentures",
    "the notes were issued",
    "the notes will be",
    "new notes will be",
    "new notes",
    "notes due",
    "fixed-to-floating subordinated notes",
    "notes will be fully and unconditionally guaranteed",
    "notes and related guarantees",
    "full and unconditional guarantees of the principal, interest, premium",
    "debt securities of the series",
    "direct, unsecured obligations",
    "all bonds issued",
    "new bonds offered",
    "collateral trust mortgage bonds",
    "administrative agent",
    "collateral agent",
    "lenders party hereto",
    "banks party thereto",
    "first priority lien",
    "first-priority liens",
    "long-term hpc lease agreements",
    "aggregate contractual value",
    "convertible notes",
    "convertible senior",
    "conversion price",
    "convertible debentures",
    "total committed amount",
    "facility size",
    "borrowing base",
    "senior secured debt",
    "borrowings under the company's facility",
    "facility agreement",
)

ASSET_OR_CAPACITY_MARKERS = (
    "held for investment",
    "unpaid principal balance",
    "upb",
    " upb",
    "servicing portfolio",
    "total loans of",
    "total assets of",
    "assets under management",
    " aum",
    "mortgage servicing rights",
    " msr",
    "net asset value",
    "financing capacity",
    "enterprise valuation",
    "purchase price paid",
    "aggregate purchase price",
    "completion of acquisition or disposition of assets",
    "net income of",
    "return on average assets",
    "return on average tangible common equity",
    "tangible book value",
    "market capitalization",
    "efficiency ratio",
    "loan growth",
    "gross credit losses",
    "loans / loans hfi",
    "loan-to-deposit",
    "loan - to - deposit",
    "client deposits",
    "core deposits",
    "gross loan portfolio",
)

EQUITY_OR_PRODUCTION_MARKERS = (
    "shares of our common stock",
    "shares of series",
    "common stock dividends",
    "market stand-off",
    "ordinary shares",
    "repurchase program",
    "share repurchase",
    "stock purchase agreement",
    "into shares of",
    "class a common stock",
    "per share",
    "last reported sale price",
    "loan production",
    "mortgage closed loan",
    "closed loan production",
    "origination volume",
)

BOILERPLATE_ONLY_MARKERS = (
    "webcast",
    "forward-looking",
    "earnings report",
    "press release",
    "results of operations and financial condition",
    "reports first quarter",
    "reports second quarter",
    "reports third quarter",
    "reports fourth quarter",
    "net income attributable to",
    "conference call, conference id",
    "does not constitute part of this prospectus",
    "information contained on",
    "replay will be available",
    "available for certain fee-based wrap accounts",
    "fee-based wrap accounts",
    "entity name tax id number",
    "authorized signatory",
    "unless otherwise defined herein",
    "same meanings as in the prospectus",
)

SEMANTIC_CONFIDENCE_CAPS = {
    SemanticEvidenceBucket.NOT_EVALUATED: 1.0,
    SemanticEvidenceBucket.COMMITTED_DEBT: 1.0,
    SemanticEvidenceBucket.ASSET_OR_CAPACITY: 0.3,
    SemanticEvidenceBucket.EQUITY_OR_PRODUCTION: 0.3,
    SemanticEvidenceBucket.BOILERPLATE_ONLY: 0.25,
    SemanticEvidenceBucket.INDETERMINATE: 0.5,
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
    effective_confidence: float
    source_count: int
    source_types: list[str]
    sources: list[EvidenceRecord]
    semantic_bucket: SemanticEvidenceBucket
    semantic_confidence_cap: float
    blocking_issues: list[str]
    eligible_for_high_confidence: bool

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["tier"] = self.tier.value
        data["semantic_bucket"] = self.semantic_bucket.value
        return data


@dataclass(frozen=True)
class EvidenceSummary:
    """Rollup across the audits attached to a report."""

    audited_claims: int
    measured_claims: int
    corroborated_claims: int
    inferred_claims: int
    unsupported_claims: int
    semantic_evaluated_claims: int
    semantic_committed_debt_claims: int
    semantic_asset_or_capacity_claims: int
    semantic_equity_or_production_claims: int
    semantic_boilerplate_claims: int
    semantic_indeterminate_claims: int
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
        semantic_text: str | None = None,
        semantic_required: bool = False,
    ) -> ClaimEvidenceAudit:
        records = [EvidenceRecord.from_provenance(p) for p in self._dedupe(evidence or [])]
        source_count = len(records)
        source_types = sorted({record.source_type for record in records})
        confidence = round(min((record.confidence for record in records), default=0.0), 4)
        tier = self._classify(records)
        semantic_bucket = classify_claim_semantics(semantic_text)
        semantic_confidence_cap = SEMANTIC_CONFIDENCE_CAPS[semantic_bucket]
        effective_confidence = round(min(confidence, semantic_confidence_cap), 4)

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
        if semantic_bucket in {
            SemanticEvidenceBucket.ASSET_OR_CAPACITY,
            SemanticEvidenceBucket.EQUITY_OR_PRODUCTION,
            SemanticEvidenceBucket.BOILERPLATE_ONLY,
        }:
            blocking_issues.append(
                f"Claim source text is semantic bucket {semantic_bucket.value}, "
                "not committed-debt evidence."
            )
        if semantic_required and semantic_bucket == SemanticEvidenceBucket.INDETERMINATE:
            blocking_issues.append(
                "Claim source text is semantically indeterminate and needs deeper review."
            )
        if effective_confidence < confidence:
            blocking_issues.append(
                f"Semantic confidence cap {semantic_confidence_cap:.2f} lowers effective "
                f"claim confidence to {effective_confidence:.2f}."
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
            blocking_issues.append("High-impact claim has not been adjudicated and approved.")

        eligible = (
            not blocking_issues
            and tier
            in {
                EvidenceTier.MEASURED,
                EvidenceTier.CORROBORATED_ESTIMATE,
                EvidenceTier.SINGLE_SOURCE_ESTIMATE,
            }
            and effective_confidence >= self.min_high_confidence
        )

        return ClaimEvidenceAudit(
            claim_id=claim_id,
            claim=claim,
            value=value,
            unit=unit,
            tier=tier,
            confidence=confidence,
            effective_confidence=effective_confidence,
            source_count=source_count,
            source_types=source_types,
            sources=records,
            semantic_bucket=semantic_bucket,
            semantic_confidence_cap=semantic_confidence_cap,
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
            semantic_evaluated_claims=sum(
                audit.semantic_bucket != SemanticEvidenceBucket.NOT_EVALUATED
                for audit in audit_list
            ),
            semantic_committed_debt_claims=sum(
                audit.semantic_bucket == SemanticEvidenceBucket.COMMITTED_DEBT
                for audit in audit_list
            ),
            semantic_asset_or_capacity_claims=sum(
                audit.semantic_bucket == SemanticEvidenceBucket.ASSET_OR_CAPACITY
                for audit in audit_list
            ),
            semantic_equity_or_production_claims=sum(
                audit.semantic_bucket == SemanticEvidenceBucket.EQUITY_OR_PRODUCTION
                for audit in audit_list
            ),
            semantic_boilerplate_claims=sum(
                audit.semantic_bucket == SemanticEvidenceBucket.BOILERPLATE_ONLY
                for audit in audit_list
            ),
            semantic_indeterminate_claims=sum(
                audit.semantic_bucket == SemanticEvidenceBucket.INDETERMINATE
                for audit in audit_list
            ),
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
        weakest_effective_confidence = min(audit.effective_confidence for audit in audits)
        if any(audit.blocking_issues for audit in audits):
            return min(0.6, weakest_effective_confidence)
        return min(0.95, weakest_effective_confidence)

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


def classify_claim_semantics(text: str | None) -> SemanticEvidenceBucket:
    """Classify whether source text supports committed-debt style use."""

    if not text or not text.strip():
        return SemanticEvidenceBucket.NOT_EVALUATED
    normalized = " ".join(text.lower().split())
    if any(marker in normalized for marker in ASSET_OR_CAPACITY_MARKERS):
        return SemanticEvidenceBucket.ASSET_OR_CAPACITY
    if any(marker in normalized for marker in COMMITTED_DEBT_MARKERS):
        return SemanticEvidenceBucket.COMMITTED_DEBT
    if any(marker in normalized for marker in EQUITY_OR_PRODUCTION_MARKERS):
        return SemanticEvidenceBucket.EQUITY_OR_PRODUCTION
    if any(marker in normalized for marker in BOILERPLATE_ONLY_MARKERS):
        return SemanticEvidenceBucket.BOILERPLATE_ONLY
    return SemanticEvidenceBucket.INDETERMINATE


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
