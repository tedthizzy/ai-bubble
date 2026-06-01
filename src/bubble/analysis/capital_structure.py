"""
Capital-structure analysis for Burry-style ecosystem questions.

This module turns source-backed Deal objects into quantified leverage,
refinancing-wall, off-balance-sheet, concentration, and downside-bearer metrics.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from typing import TYPE_CHECKING, Any

from bubble.analysis.entity_filters import canonical_entity_key, is_generic_entity_name
from bubble.analysis.evidence import ClaimEvidenceAudit, EvidenceGate
from bubble.models.base import DealType, EntityRef, HumanReviewStatus, Provenance, SourceType

if TYPE_CHECKING:
    from bubble.models.deal import Deal


DEBT_LIKE_DEAL_TYPES = {
    DealType.DEBT_FACILITY,
    DealType.BOND,
    DealType.LEASE,
    DealType.PREFERRED_EQUITY,
    DealType.GUARANTEE,
}

OFF_BALANCE_KEY_TERMS = {
    "off_balance_sheet",
    "spv",
    "insurance_wrapper",
    "synthetic_lease",
    "sale_leaseback",
}

RISK_BEARER_ROLES = {
    "lender",
    "lessor",
    "guarantor",
    "insurer",
    "noteholder",
    "bondholder",
    "financier",
}

CAPITAL_NOTIONAL_REVIEW_THRESHOLD_USD = 25_000_000_000


@dataclass(frozen=True)
class ExposureConcentration:
    entity_ref: str
    exposure_usd: float
    pct_of_total: float
    roles: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapitalReviewItem:
    deal_ref: str
    title: str | None
    deal_type: str
    notional_usd: float
    source_uri: str
    page_or_section: str | None
    human_review_status: str
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapitalDuplicateGroup:
    economic_key: str
    representative_deal_ref: str
    duplicate_deal_count: int
    raw_notional_usd: float
    distinct_notional_usd: float
    duplicate_notional_usd: float
    source_uris: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DownsideBearerRollup:
    named_bearers: list[ExposureConcentration]
    unmapped_downside_bearer_deal_count: int
    unmapped_downside_bearer_mention_count: int
    unmapped_downside_bearer_usd: float


@dataclass(frozen=True)
class CapitalStructureMetrics:
    as_of: date
    deal_count: int
    debt_like_deal_count: int
    total_notional_usd: float
    debt_like_notional_usd: float
    distinct_deal_count: int
    distinct_total_notional_usd: float
    distinct_debt_like_deal_count: int
    distinct_debt_like_notional_usd: float
    duplicate_candidate_deal_count: int
    duplicate_candidate_notional_usd: float
    top_duplicate_candidate_groups: list[CapitalDuplicateGroup]
    aggregate_obligation_deal_count: int
    aggregate_obligation_notional_usd: float
    aggregate_obligation_distinct_deal_count: int
    aggregate_obligation_distinct_notional_usd: float
    off_balance_sheet_usd: float
    off_balance_sheet_pct: float
    guarantee_linked_deal_count: int
    guarantee_linked_usd: float
    spv_or_non_recourse_deal_count: int
    spv_or_non_recourse_usd: float
    reviewed_deal_count: int
    reviewed_total_notional_usd: float
    reviewed_debt_like_deal_count: int
    reviewed_debt_like_notional_usd: float
    pending_review_deal_count: int
    pending_review_total_notional_usd: float
    pending_review_debt_like_deal_count: int
    pending_review_debt_like_notional_usd: float
    notional_review_required_deal_count: int
    notional_review_required_usd: float
    notional_review_required_distinct_deal_count: int
    notional_review_required_distinct_usd: float
    top_notional_review_items: list[CapitalReviewItem]
    top_notional_review_distinct_items: list[CapitalReviewItem]
    refinancing_wall_by_quarter: dict[str, float]
    near_term_refinancing_usd: float
    top_10_concentration_pct: float
    top_exposures: list[ExposureConcentration]
    downside_bearers: list[ExposureConcentration]
    unmapped_downside_bearer_deal_count: int
    unmapped_downside_bearer_mention_count: int
    unmapped_downside_bearer_usd: float
    evidence_summary: dict[str, Any]
    claim_audits: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "as_of": self.as_of.isoformat(),
            "deal_count": self.deal_count,
            "debt_like_deal_count": self.debt_like_deal_count,
            "total_notional_usd": self.total_notional_usd,
            "debt_like_notional_usd": self.debt_like_notional_usd,
            "distinct_deal_count": self.distinct_deal_count,
            "distinct_total_notional_usd": self.distinct_total_notional_usd,
            "distinct_debt_like_deal_count": self.distinct_debt_like_deal_count,
            "distinct_debt_like_notional_usd": self.distinct_debt_like_notional_usd,
            "duplicate_candidate_deal_count": self.duplicate_candidate_deal_count,
            "duplicate_candidate_notional_usd": self.duplicate_candidate_notional_usd,
            "top_duplicate_candidate_groups": [
                group.to_dict() for group in self.top_duplicate_candidate_groups
            ],
            "aggregate_obligation_deal_count": self.aggregate_obligation_deal_count,
            "aggregate_obligation_notional_usd": self.aggregate_obligation_notional_usd,
            "aggregate_obligation_distinct_deal_count": (
                self.aggregate_obligation_distinct_deal_count
            ),
            "aggregate_obligation_distinct_notional_usd": (
                self.aggregate_obligation_distinct_notional_usd
            ),
            "off_balance_sheet_usd": self.off_balance_sheet_usd,
            "off_balance_sheet_pct": self.off_balance_sheet_pct,
            "guarantee_linked_deal_count": self.guarantee_linked_deal_count,
            "guarantee_linked_usd": self.guarantee_linked_usd,
            "spv_or_non_recourse_deal_count": self.spv_or_non_recourse_deal_count,
            "spv_or_non_recourse_usd": self.spv_or_non_recourse_usd,
            "reviewed_deal_count": self.reviewed_deal_count,
            "reviewed_total_notional_usd": self.reviewed_total_notional_usd,
            "reviewed_debt_like_deal_count": self.reviewed_debt_like_deal_count,
            "reviewed_debt_like_notional_usd": self.reviewed_debt_like_notional_usd,
            "pending_review_deal_count": self.pending_review_deal_count,
            "pending_review_total_notional_usd": self.pending_review_total_notional_usd,
            "pending_review_debt_like_deal_count": self.pending_review_debt_like_deal_count,
            "pending_review_debt_like_notional_usd": self.pending_review_debt_like_notional_usd,
            "notional_review_required_deal_count": self.notional_review_required_deal_count,
            "notional_review_required_usd": self.notional_review_required_usd,
            "notional_review_required_distinct_deal_count": (
                self.notional_review_required_distinct_deal_count
            ),
            "notional_review_required_distinct_usd": (self.notional_review_required_distinct_usd),
            "top_notional_review_items": [
                item.to_dict() for item in self.top_notional_review_items
            ],
            "top_notional_review_distinct_items": [
                item.to_dict() for item in self.top_notional_review_distinct_items
            ],
            "refinancing_wall_by_quarter": self.refinancing_wall_by_quarter,
            "near_term_refinancing_usd": self.near_term_refinancing_usd,
            "top_10_concentration_pct": self.top_10_concentration_pct,
            "top_exposures": [exposure.to_dict() for exposure in self.top_exposures],
            "downside_bearers": [exposure.to_dict() for exposure in self.downside_bearers],
            "unmapped_downside_bearer_deal_count": self.unmapped_downside_bearer_deal_count,
            "unmapped_downside_bearer_mention_count": self.unmapped_downside_bearer_mention_count,
            "unmapped_downside_bearer_usd": self.unmapped_downside_bearer_usd,
            "evidence_summary": self.evidence_summary,
            "claim_audits": self.claim_audits,
        }


class CapitalStructureAnalyzer:
    """Compute capital-structure metrics from source-backed deals."""

    VERSION = "capital-structure-v1"

    def __init__(self, evidence_gate: EvidenceGate | None = None) -> None:
        self.evidence_gate = evidence_gate or EvidenceGate()

    def analyze(
        self,
        deals: list[Deal],
        *,
        as_of: date | None = None,
        near_term_end: date | None = None,
    ) -> CapitalStructureMetrics:
        as_of = as_of or date.today()
        near_term_end = near_term_end or date(as_of.year + 3, 12, 31)

        debt_like = [deal for deal in deals if self._is_debt_like(deal)]
        distinct_deals, duplicate_groups = self._distinct_deals(deals)
        distinct_debt_like = [deal for deal in distinct_deals if self._is_debt_like(deal)]
        duplicate_candidate_notional = sum(
            group.duplicate_notional_usd for group in duplicate_groups
        )
        aggregate_obligations = [deal for deal in deals if self._is_aggregate_obligation(deal)]
        aggregate_obligations_distinct = [
            deal for deal in distinct_deals if self._is_aggregate_obligation(deal)
        ]
        total_notional = sum(self._deal_notional(deal) for deal in deals)
        debt_like_notional = sum(self._deal_notional(deal) for deal in debt_like)
        distinct_total_notional = sum(self._deal_notional(deal) for deal in distinct_deals)
        distinct_debt_like_notional = sum(self._deal_notional(deal) for deal in distinct_debt_like)
        aggregate_obligation_notional = sum(
            self._deal_notional(deal) for deal in aggregate_obligations
        )
        aggregate_obligation_distinct_notional = sum(
            self._deal_notional(deal) for deal in aggregate_obligations_distinct
        )
        guarantee_linked = [deal for deal in debt_like if self._guarantee_entities(deal)]
        guarantee_linked_usd = sum(self._deal_notional(deal) for deal in guarantee_linked)
        spv_or_non_recourse = [deal for deal in debt_like if self._is_spv_or_non_recourse(deal)]
        spv_or_non_recourse_usd = sum(self._deal_notional(deal) for deal in spv_or_non_recourse)
        reviewed = [deal for deal in deals if self._is_human_reviewed(deal)]
        reviewed_debt_like = [deal for deal in reviewed if self._is_debt_like(deal)]
        pending_review = [deal for deal in deals if not self._is_human_reviewed(deal)]
        pending_review_debt_like = [deal for deal in pending_review if self._is_debt_like(deal)]
        notional_review_required = [
            deal
            for deal in pending_review_debt_like
            if self._deal_notional(deal) >= CAPITAL_NOTIONAL_REVIEW_THRESHOLD_USD
        ]
        notional_review_required_distinct = [
            deal
            for deal in distinct_debt_like
            if not self._is_human_reviewed(deal)
            and self._deal_notional(deal) >= CAPITAL_NOTIONAL_REVIEW_THRESHOLD_USD
        ]
        review_items = self._notional_review_items(notional_review_required)
        review_items_distinct = self._notional_review_items(notional_review_required_distinct)
        reviewed_total_notional = sum(self._deal_notional(deal) for deal in reviewed)
        reviewed_debt_like_notional = sum(self._deal_notional(deal) for deal in reviewed_debt_like)
        pending_review_total_notional = sum(self._deal_notional(deal) for deal in pending_review)
        pending_review_debt_like_notional = sum(
            self._deal_notional(deal) for deal in pending_review_debt_like
        )
        notional_review_required_usd = sum(
            self._deal_notional(deal) for deal in notional_review_required
        )
        notional_review_required_distinct_usd = sum(
            self._deal_notional(deal) for deal in notional_review_required_distinct
        )
        off_balance_sheet = sum(
            self._deal_notional(deal) for deal in debt_like if self._is_off_balance_sheet(deal)
        )
        refinancing_wall = self._refinancing_wall(debt_like)
        near_term_refinancing = sum(
            amount
            for quarter, amount in refinancing_wall.items()
            if as_of <= self._quarter_start(quarter) <= near_term_end
        )
        top_exposures = self._concentration(debt_like, total=debt_like_notional)
        downside_bearers = self._downside_bearers(debt_like, total=debt_like_notional)

        audits = self._audit_claims(
            debt_like=debt_like,
            total_notional=total_notional,
            debt_like_notional=debt_like_notional,
            distinct_debt_like_notional=distinct_debt_like_notional,
            duplicate_candidate_notional=duplicate_candidate_notional,
            aggregate_obligation_distinct_notional=aggregate_obligation_distinct_notional,
            off_balance_sheet=off_balance_sheet,
            guarantee_linked_usd=guarantee_linked_usd,
            spv_or_non_recourse_usd=spv_or_non_recourse_usd,
            reviewed_debt_like_notional=reviewed_debt_like_notional,
            pending_review_debt_like_notional=pending_review_debt_like_notional,
            notional_review_required_usd=notional_review_required_usd,
            notional_review_required_distinct_usd=notional_review_required_distinct_usd,
            review_items=review_items,
            review_items_distinct=review_items_distinct,
            refinancing_wall=refinancing_wall,
            top_10_concentration_pct=sum(exposure.pct_of_total for exposure in top_exposures[:10]),
            downside_bearers=downside_bearers.named_bearers,
            unmapped_downside_bearer_usd=downside_bearers.unmapped_downside_bearer_usd,
            unmapped_downside_bearer_mention_count=(
                downside_bearers.unmapped_downside_bearer_mention_count
            ),
        )

        return CapitalStructureMetrics(
            as_of=as_of,
            deal_count=len(deals),
            debt_like_deal_count=len(debt_like),
            total_notional_usd=round(total_notional, 2),
            debt_like_notional_usd=round(debt_like_notional, 2),
            distinct_deal_count=len(distinct_deals),
            distinct_total_notional_usd=round(distinct_total_notional, 2),
            distinct_debt_like_deal_count=len(distinct_debt_like),
            distinct_debt_like_notional_usd=round(distinct_debt_like_notional, 2),
            duplicate_candidate_deal_count=sum(
                max(0, group.duplicate_deal_count) for group in duplicate_groups
            ),
            duplicate_candidate_notional_usd=round(duplicate_candidate_notional, 2),
            top_duplicate_candidate_groups=duplicate_groups[:25],
            aggregate_obligation_deal_count=len(aggregate_obligations),
            aggregate_obligation_notional_usd=round(aggregate_obligation_notional, 2),
            aggregate_obligation_distinct_deal_count=len(aggregate_obligations_distinct),
            aggregate_obligation_distinct_notional_usd=round(
                aggregate_obligation_distinct_notional, 2
            ),
            off_balance_sheet_usd=round(off_balance_sheet, 2),
            off_balance_sheet_pct=self._pct(off_balance_sheet, debt_like_notional),
            guarantee_linked_deal_count=len(guarantee_linked),
            guarantee_linked_usd=round(guarantee_linked_usd, 2),
            spv_or_non_recourse_deal_count=len(spv_or_non_recourse),
            spv_or_non_recourse_usd=round(spv_or_non_recourse_usd, 2),
            reviewed_deal_count=len(reviewed),
            reviewed_total_notional_usd=round(reviewed_total_notional, 2),
            reviewed_debt_like_deal_count=len(reviewed_debt_like),
            reviewed_debt_like_notional_usd=round(reviewed_debt_like_notional, 2),
            pending_review_deal_count=len(pending_review),
            pending_review_total_notional_usd=round(pending_review_total_notional, 2),
            pending_review_debt_like_deal_count=len(pending_review_debt_like),
            pending_review_debt_like_notional_usd=round(pending_review_debt_like_notional, 2),
            notional_review_required_deal_count=len(notional_review_required),
            notional_review_required_usd=round(notional_review_required_usd, 2),
            notional_review_required_distinct_deal_count=len(notional_review_required_distinct),
            notional_review_required_distinct_usd=round(notional_review_required_distinct_usd, 2),
            top_notional_review_items=review_items,
            top_notional_review_distinct_items=review_items_distinct,
            refinancing_wall_by_quarter=refinancing_wall,
            near_term_refinancing_usd=round(near_term_refinancing, 2),
            top_10_concentration_pct=round(
                sum(exposure.pct_of_total for exposure in top_exposures[:10]), 4
            ),
            top_exposures=top_exposures[:10],
            downside_bearers=downside_bearers.named_bearers[:15],
            unmapped_downside_bearer_deal_count=(
                downside_bearers.unmapped_downside_bearer_deal_count
            ),
            unmapped_downside_bearer_mention_count=(
                downside_bearers.unmapped_downside_bearer_mention_count
            ),
            unmapped_downside_bearer_usd=round(downside_bearers.unmapped_downside_bearer_usd, 2),
            evidence_summary=self.evidence_gate.summarize(audits).to_dict(),
            claim_audits=[audit.to_dict() for audit in audits],
        )

    def _audit_claims(
        self,
        *,
        debt_like: list[Deal],
        total_notional: float,
        debt_like_notional: float,
        distinct_debt_like_notional: float,
        duplicate_candidate_notional: float,
        aggregate_obligation_distinct_notional: float,
        off_balance_sheet: float,
        guarantee_linked_usd: float,
        spv_or_non_recourse_usd: float,
        reviewed_debt_like_notional: float,
        pending_review_debt_like_notional: float,
        notional_review_required_usd: float,
        notional_review_required_distinct_usd: float,
        review_items: list[CapitalReviewItem],
        review_items_distinct: list[CapitalReviewItem],
        refinancing_wall: dict[str, float],
        top_10_concentration_pct: float,
        downside_bearers: list[ExposureConcentration],
        unmapped_downside_bearer_usd: float,
        unmapped_downside_bearer_mention_count: int,
    ) -> list[ClaimEvidenceAudit]:
        evidence = self._provenance_for_deals(debt_like)
        return [
            self.evidence_gate.audit_claim(
                claim_id="capital.total_notional",
                claim="Total notional exposure across analyzed deals",
                value=total_notional,
                unit="USD",
                evidence=evidence,
                requires_corroboration=True,
                high_impact=True,
            ),
            self.evidence_gate.audit_claim(
                claim_id="capital.debt_like_notional",
                claim="Debt-like exposure across analyzed deals",
                value=debt_like_notional,
                unit="USD",
                evidence=evidence,
                requires_corroboration=True,
                high_impact=True,
            ),
            self.evidence_gate.audit_claim(
                claim_id="capital.distinct_debt_like_notional",
                claim="Deduplicated debt-like exposure across analyzed candidate deals",
                value=distinct_debt_like_notional,
                unit="USD",
                evidence=evidence,
                requires_corroboration=True,
                high_impact=True,
            ),
            self.evidence_gate.audit_claim(
                claim_id="capital.duplicate_candidate_notional",
                claim="Debt-like candidate notional removed by economic deduplication",
                value=duplicate_candidate_notional,
                unit="USD",
                evidence=evidence,
                requires_corroboration=True,
                high_impact=True,
            ),
            self.evidence_gate.audit_claim(
                claim_id="capital.aggregate_obligation_distinct",
                claim="Distinct aggregate obligation exposure separated from individual deal records",
                value=aggregate_obligation_distinct_notional,
                unit="USD",
                evidence=evidence,
                requires_corroboration=True,
                high_impact=True,
            ),
            self.evidence_gate.audit_claim(
                claim_id="capital.off_balance_sheet",
                claim="Off-balance-sheet, SPV-linked, non-recourse, or guarantee-linked debt-like exposure",
                value=off_balance_sheet,
                unit="USD",
                evidence=evidence,
                requires_corroboration=True,
                high_impact=True,
            ),
            self.evidence_gate.audit_claim(
                claim_id="capital.guarantee_linked",
                claim="Debt-like exposure with explicit guarantee or guarantor roles",
                value=guarantee_linked_usd,
                unit="USD",
                evidence=evidence,
                requires_corroboration=True,
                high_impact=True,
            ),
            self.evidence_gate.audit_claim(
                claim_id="capital.spv_or_non_recourse",
                claim="Debt-like exposure flagged as SPV-linked, non-recourse, synthetic lease, or sale-leaseback",
                value=spv_or_non_recourse_usd,
                unit="USD",
                evidence=evidence,
                requires_corroboration=True,
                high_impact=True,
            ),
            self.evidence_gate.audit_claim(
                claim_id="capital.reviewed_debt_like_notional",
                claim="Human-reviewed debt-like exposure across analyzed deals",
                value=reviewed_debt_like_notional,
                unit="USD",
                evidence=evidence,
                requires_corroboration=True,
                high_impact=True,
            ),
            self.evidence_gate.audit_claim(
                claim_id="capital.pending_review_debt_like_notional",
                claim="Pending-review candidate debt-like exposure across analyzed deals",
                value=pending_review_debt_like_notional,
                unit="USD",
                evidence=evidence,
                requires_corroboration=True,
                high_impact=True,
            ),
            self.evidence_gate.audit_claim(
                claim_id="capital.notional_review_required",
                claim="High-notional pending-review debt-like extraction candidates",
                value={
                    "notional_usd": notional_review_required_usd,
                    "distinct_notional_usd": notional_review_required_distinct_usd,
                    "items": [item.to_dict() for item in review_items[:25]],
                    "distinct_items": [item.to_dict() for item in review_items_distinct[:25]],
                },
                unit="USD",
                evidence=evidence,
                requires_corroboration=True,
                high_impact=True,
            ),
            self.evidence_gate.audit_claim(
                claim_id="capital.refinancing_wall",
                claim="Debt-like maturities by calendar quarter",
                value=refinancing_wall,
                unit="USD by quarter",
                evidence=evidence,
                requires_corroboration=True,
                high_impact=True,
            ),
            self.evidence_gate.audit_claim(
                claim_id="capital.concentration",
                claim="Top 10 counterparty exposure concentration",
                value=top_10_concentration_pct,
                unit="ratio",
                evidence=evidence,
                requires_corroboration=True,
                high_impact=True,
            ),
            self.evidence_gate.audit_claim(
                claim_id="capital.downside_bearers",
                claim="Identified entities bearing downside exposure",
                value={
                    "named_bearers": [bearer.to_dict() for bearer in downside_bearers[:15]],
                    "unmapped_downside_bearer_usd": round(unmapped_downside_bearer_usd, 2),
                    "unmapped_downside_bearer_mention_count": (
                        unmapped_downside_bearer_mention_count
                    ),
                },
                unit="USD by role",
                evidence=evidence,
                requires_corroboration=True,
                high_impact=True,
            ),
        ]

    @staticmethod
    def _is_debt_like(deal: Deal) -> bool:
        return deal.deal_type in DEBT_LIKE_DEAL_TYPES or bool(deal.debt_tranches)

    @staticmethod
    def _deal_notional(deal: Deal) -> float:
        tranche_total = sum(tranche.notional_usd for tranche in deal.debt_tranches)
        if tranche_total:
            return tranche_total
        return float(deal.notional_amount_usd or 0.0)

    @staticmethod
    def _is_human_reviewed(deal: Deal) -> bool:
        reviewed_statuses = {HumanReviewStatus.APPROVED, HumanReviewStatus.OVERRIDDEN}
        if deal.provenance.human_review_status not in reviewed_statuses:
            return False
        return all(
            tranche.provenance.human_review_status in reviewed_statuses
            for tranche in deal.debt_tranches
        )

    @classmethod
    def _distinct_deals(
        cls,
        deals: list[Deal],
    ) -> tuple[list[Deal], list[CapitalDuplicateGroup]]:
        grouped: dict[str, list[Deal]] = defaultdict(list)
        for deal in deals:
            grouped[cls._economic_key(deal)].append(deal)

        distinct: list[Deal] = []
        duplicate_groups: list[CapitalDuplicateGroup] = []
        for key, group in grouped.items():
            representative = max(
                group,
                key=lambda deal: (
                    cls._deal_notional(deal),
                    deal.provenance.confidence,
                    deal.provenance.human_review_status
                    in {HumanReviewStatus.APPROVED, HumanReviewStatus.OVERRIDDEN},
                ),
            )
            distinct.append(representative)
            if len(group) <= 1:
                continue
            raw_notional = sum(cls._deal_notional(deal) for deal in group)
            distinct_notional = cls._deal_notional(representative)
            duplicate_groups.append(
                CapitalDuplicateGroup(
                    economic_key=key,
                    representative_deal_ref=representative.source_deal_id or str(representative.id),
                    duplicate_deal_count=len(group) - 1,
                    raw_notional_usd=round(raw_notional, 2),
                    distinct_notional_usd=round(distinct_notional, 2),
                    duplicate_notional_usd=round(raw_notional - distinct_notional, 2),
                    source_uris=sorted({deal.provenance.source_uri for deal in group})[:20],
                )
            )
        duplicate_groups.sort(key=lambda group: group.duplicate_notional_usd, reverse=True)
        return distinct, duplicate_groups

    @classmethod
    def _economic_key(cls, deal: Deal) -> str:
        notional = round(cls._deal_notional(deal), 2)
        if notional <= 0:
            return f"source:{deal.source_deal_id or deal.provenance.source_uri}"
        party = cls._normalize_key_part(deal.parties[0] if deal.parties else "")
        maturity = deal.maturity_date.isoformat() if deal.maturity_date else ""
        context_kind = cls._notional_context_kind(deal)
        if context_kind.startswith("aggregate_"):
            return "|".join(
                [
                    "aggregate",
                    party,
                    context_kind,
                    deal.deal_type.value,
                    f"{notional:.2f}",
                ]
            )
        accession = str(deal.key_terms.get("accession_number") or "").strip()
        if accession:
            return "|".join(
                [
                    "accession",
                    party,
                    accession,
                    deal.deal_type.value,
                    f"{notional:.2f}",
                    maturity,
                ]
            )
        return f"source:{deal.source_deal_id or deal.provenance.source_uri}"

    @staticmethod
    def _notional_context_kind(deal: Deal) -> str:
        return str(deal.key_terms.get("notional_context_kind") or "")

    @classmethod
    def _is_aggregate_obligation(cls, deal: Deal) -> bool:
        return cls._notional_context_kind(deal).startswith("aggregate_")

    @staticmethod
    def _normalize_key_part(value: str) -> str:
        return " ".join(value.lower().split())

    @classmethod
    def _is_off_balance_sheet(cls, deal: Deal) -> bool:
        return cls._is_spv_or_non_recourse(deal) or bool(cls._guarantee_entities(deal))

    @staticmethod
    def _is_spv_or_non_recourse(deal: Deal) -> bool:
        if deal.bankruptcy_remote_spv or deal.is_non_recourse:
            return True
        title = (deal.title or "").lower()
        title_terms = (
            "spv",
            "special purpose",
            "off-balance",
            "off balance",
            "synthetic lease",
            "sale-leaseback",
            "sale leaseback",
        )
        if any(term in title for term in title_terms):
            return True
        return any(bool(deal.key_terms.get(term)) for term in OFF_BALANCE_KEY_TERMS)

    @staticmethod
    def _guarantee_entities(deal: Deal) -> list[str]:
        guarantors: list[str] = [str(guarantor) for guarantor in deal.guarantees]
        for role, entities in deal.counterparty_roles.items():
            normalized_role = role.lower().replace("_", " ")
            if "guarant" in normalized_role or "guarantee" in normalized_role:
                guarantors.extend(str(entity) for entity in entities)
        for tranche in deal.debt_tranches:
            guarantors.extend(str(guarantor) for guarantor in tranche.guarantors)
        return sorted({guarantor.strip() for guarantor in guarantors if guarantor.strip()})

    def _refinancing_wall(self, deals: list[Deal]) -> dict[str, float]:
        wall: dict[str, float] = defaultdict(float)
        for deal in deals:
            if deal.debt_tranches:
                for tranche in deal.debt_tranches:
                    maturity = tranche.maturity or deal.maturity_date
                    if maturity:
                        wall[self._quarter(maturity)] += tranche.notional_usd
                continue
            if deal.maturity_date:
                wall[self._quarter(deal.maturity_date)] += self._deal_notional(deal)
        return {quarter: round(wall[quarter], 2) for quarter in sorted(wall)}

    @classmethod
    def _notional_review_items(cls, deals: list[Deal]) -> list[CapitalReviewItem]:
        return [
            cls._notional_review_item(deal)
            for deal in sorted(deals, key=cls._deal_notional, reverse=True)
        ]

    @classmethod
    def _notional_review_item(cls, deal: Deal) -> CapitalReviewItem:
        notional = cls._deal_notional(deal)
        return CapitalReviewItem(
            deal_ref=deal.source_deal_id or str(deal.id),
            title=deal.title,
            deal_type=deal.deal_type.value,
            notional_usd=round(notional, 2),
            source_uri=deal.provenance.source_uri,
            page_or_section=deal.provenance.page_or_section,
            human_review_status=deal.provenance.human_review_status.value,
            reasons=cls._review_reasons(deal, notional=notional),
        )

    @staticmethod
    def _review_reasons(deal: Deal, *, notional: float) -> list[str]:
        reasons: list[str] = []
        if deal.provenance.human_review_status not in {
            HumanReviewStatus.APPROVED,
            HumanReviewStatus.OVERRIDDEN,
        }:
            reasons.append(f"human_review_status:{deal.provenance.human_review_status.value}")
        if notional >= CAPITAL_NOTIONAL_REVIEW_THRESHOLD_USD:
            reasons.append(
                f"notional_usd_above_{CAPITAL_NOTIONAL_REVIEW_THRESHOLD_USD:,.0f}_threshold"
            )
        if deal.key_terms.get("requires_human_review"):
            reasons.append("source_extraction_marked_requires_human_review")
        extraction_method = str(deal.key_terms.get("extraction_method") or "")
        if deal.provenance.source_type == SourceType.SEC_EDGAR and extraction_method.startswith(
            "deterministic_edgar"
        ):
            reasons.append("deterministic_sec_extraction_candidate")
        return reasons

    def _concentration(self, deals: list[Deal], *, total: float) -> list[ExposureConcentration]:
        exposures: dict[str, float] = defaultdict(float)
        roles: dict[str, set[str]] = defaultdict(set)
        labels: dict[str, str] = {}
        for deal in deals:
            notional = self._deal_notional(deal)
            parties = self._exposure_parties(deal)
            if not parties:
                continue
            split_notional = notional / len(parties)
            for role, entity in parties:
                entity_name = str(entity).strip()
                if not entity_name or is_generic_entity_name(entity_name):
                    continue
                entity_key = canonical_entity_key(entity_name)
                labels.setdefault(entity_key, entity_name)
                exposures[entity_key] += split_notional
                roles[entity_key].add(role)
        return self._ranked_exposures(exposures, roles, total=total, labels=labels)

    def _downside_bearers(self, deals: list[Deal], *, total: float) -> DownsideBearerRollup:
        exposures: dict[str, float] = defaultdict(float)
        roles: dict[str, set[str]] = defaultdict(set)
        labels: dict[str, str] = {}
        unmapped_deals: set[str] = set()
        unmapped_mentions = 0
        unmapped_exposure = 0.0
        for deal in deals:
            notional = self._deal_notional(deal)
            bearers = self._risk_bearer_parties(deal)
            if not bearers:
                continue
            entity_roles: dict[str, set[str]] = defaultdict(set)
            unmapped_entities: set[str] = set()
            for role, entity in bearers:
                entity_name = str(entity).strip()
                if not entity_name or is_generic_entity_name(entity_name):
                    unmapped_entities.add(entity_name or "<empty>")
                    continue
                entity_key = canonical_entity_key(entity_name)
                labels.setdefault(entity_key, entity_name)
                entity_roles[entity_key].add(role)
            participant_count = len(entity_roles) + len(unmapped_entities)
            if participant_count == 0:
                continue
            split_notional = notional / participant_count
            if unmapped_entities:
                unmapped_mentions += len(unmapped_entities)
                unmapped_deals.add(deal.source_deal_id or str(deal.id))
                unmapped_exposure += split_notional * len(unmapped_entities)
            for entity, deal_roles in entity_roles.items():
                exposures[entity] += split_notional
                roles[entity].update(deal_roles)
        return DownsideBearerRollup(
            named_bearers=self._ranked_exposures(exposures, roles, total=total, labels=labels),
            unmapped_downside_bearer_deal_count=len(unmapped_deals),
            unmapped_downside_bearer_mention_count=unmapped_mentions,
            unmapped_downside_bearer_usd=unmapped_exposure,
        )

    @staticmethod
    def _exposure_parties(deal: Deal) -> list[tuple[str, EntityRef]]:
        parties: list[tuple[str, EntityRef]] = []
        for role, entities in deal.counterparty_roles.items():
            parties.extend((role, entity) for entity in entities)
        if not parties:
            parties = [("party", entity) for entity in deal.parties]
        return parties

    @classmethod
    def _risk_bearer_parties(cls, deal: Deal) -> list[tuple[str, EntityRef]]:
        bearers: list[tuple[str, EntityRef]] = []
        for role, entities in deal.counterparty_roles.items():
            if role.lower() in RISK_BEARER_ROLES:
                bearers.extend((role, entity) for entity in entities)
        bearers.extend(("guarantor", guarantor) for guarantor in cls._guarantee_entities(deal))
        return bearers

    @staticmethod
    def _ranked_exposures(
        exposures: dict[str, float],
        roles: dict[str, set[str]],
        *,
        total: float,
        labels: dict[str, str] | None = None,
    ) -> list[ExposureConcentration]:
        labels = labels or {}
        ranked = sorted(exposures.items(), key=lambda item: item[1], reverse=True)
        return [
            ExposureConcentration(
                entity_ref=labels.get(entity, entity),
                exposure_usd=round(exposure, 2),
                pct_of_total=CapitalStructureAnalyzer._pct(exposure, total),
                roles=sorted(roles[entity]),
            )
            for entity, exposure in ranked
        ]

    @staticmethod
    def _provenance_for_deals(deals: list[Deal]) -> list[Provenance]:
        evidence = []
        for deal in deals:
            evidence.append(deal.provenance)
            evidence.extend(tranche.provenance for tranche in deal.debt_tranches)
        return evidence

    @staticmethod
    def _quarter(maturity: date) -> str:
        quarter = ((maturity.month - 1) // 3) + 1
        return f"{maturity.year}-Q{quarter}"

    @staticmethod
    def _quarter_start(quarter: str) -> date:
        year_str, quarter_str = quarter.split("-Q", maxsplit=1)
        month = (int(quarter_str) - 1) * 3 + 1
        return date(int(year_str), month, 1)

    @staticmethod
    def _pct(numerator: float, denominator: float) -> float:
        if denominator <= 0:
            return 0.0
        return round(numerator / denominator, 4)
