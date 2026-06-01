"""Source-backed debt-service and cash-flow mismatch analysis."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Any

from bubble.analysis.capital_structure import DEBT_LIKE_DEAL_TYPES
from bubble.analysis.ecosystem_scope import scope_deals
from bubble.analysis.entity_filters import canonical_entity_key
from bubble.analysis.evidence import EvidenceGate

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bubble.models.base import Provenance
    from bubble.models.compute import CapexPaybackCase
    from bubble.models.deal import Deal, DebtTranche


MAX_MEASURED_RATE_DECIMAL = 0.20
START_YEAR = 2024
END_YEAR = 2030
RATE_KEY_CANDIDATES = (
    "interest_rate",
    "coupon_rate",
    "coupon",
    "effective_interest_rate",
    "stated_interest_rate",
)


@dataclass(frozen=True)
class DebtServiceObligation:
    """One source-backed debt-like obligation row."""

    deal_ref: str
    title: str | None
    entity: str | None
    deal_type: str
    tranche_name: str | None
    notional_usd: float
    interest_rate_pct: float | None
    annual_interest_usd: float | None
    maturity_date: str | None
    source_uri: str
    retrieved_at: str
    content_hash: str
    human_review_status: str
    rate_source: str
    flags: list[str]
    source_provenance: Provenance = field(repr=False, compare=False)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("source_provenance", None)
        return data


@dataclass(frozen=True)
class CashFlowMismatchCase:
    """One source-backed utilization/payback case with debt-service math."""

    entity: str
    project_or_cluster_id: str | None
    capex_usd: float
    annual_revenue_run_rate_usd: float | None
    contracted_revenue_usd: float | None
    utilization_pct: float | None
    gross_margin_pct: float | None
    annual_power_cost_usd: float | None
    annual_debt_service_usd: float | None
    annual_gross_cash_flow_usd: float | None
    debt_service_coverage_ratio: float | None
    cash_after_debt_service_usd: float | None
    red_flag: bool
    blocking_issues: list[str]
    source_uri: str
    retrieved_at: str
    content_hash: str
    human_review_status: str
    source_provenance: Provenance = field(repr=False, compare=False)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("source_provenance", None)
        return data


@dataclass(frozen=True)
class DebtServiceQuarter:
    """Measured debt-service and missing-rate wall for one maturity quarter."""

    quarter: str
    obligation_count: int
    measured_rate_obligation_count: int
    missing_rate_obligation_count: int
    maturing_notional_usd: float
    measured_rate_notional_usd: float
    missing_rate_notional_usd: float
    measured_annual_interest_usd: float
    top_obligations: list[DebtServiceObligation]
    top_coverage_gaps: list[DebtServiceObligation]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["top_obligations"] = [item.to_dict() for item in self.top_obligations]
        data["top_coverage_gaps"] = [item.to_dict() for item in self.top_coverage_gaps]
        return data


@dataclass(frozen=True)
class DebtServiceDuplicateGroup:
    """Candidate duplicate source rows for one economic debt-service obligation."""

    economic_key: str
    representative_deal_ref: str
    duplicate_obligation_count: int
    raw_notional_usd: float
    distinct_notional_usd: float
    duplicate_notional_usd: float
    source_uris: list[str]
    deal_refs: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DebtServiceEntityRisk:
    """Entity-level debt-service stress and coverage-gap rollup."""

    entity: str
    distinct_obligation_count: int
    measured_rate_obligation_count: int
    missing_rate_obligation_count: int
    rate_outlier_obligation_count: int
    distinct_notional_usd: float
    measured_rate_notional_usd: float
    missing_rate_notional_usd: float
    rate_outlier_notional_usd: float
    measured_annual_interest_usd: float
    maturity_wall_notional_usd_2024_2030: float
    maturity_wall_measured_annual_interest_usd_2024_2030: float
    maturity_wall_missing_rate_notional_usd_2024_2030: float
    obligations_missing_maturity_count: int
    notional_missing_maturity_usd: float
    peak_maturity_quarter: str | None
    peak_maturity_notional_usd: float
    peak_measured_annual_interest_usd: float
    debt_service_wall_by_quarter: dict[str, dict[str, float | int]]
    review_priority_reasons: list[str]
    top_obligations: list[DebtServiceObligation]
    top_coverage_gaps: list[DebtServiceObligation]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["top_obligations"] = [item.to_dict() for item in self.top_obligations]
        data["top_coverage_gaps"] = [item.to_dict() for item in self.top_coverage_gaps]
        return data


@dataclass(frozen=True)
class DebtServiceMetrics:
    """Rollup of explicit-rate debt service and capex payback coverage gaps."""

    deal_count_scanned: int
    scoped_deal_count: int
    out_of_scope_deal_count: int
    debt_like_deal_count: int
    out_of_scope_debt_like_deal_count: int
    debt_like_notional_usd: float
    out_of_scope_debt_like_notional_usd: float
    scope_inclusion_reason_counts: dict[str, int]
    obligations_count: int
    distinct_obligations_count: int
    duplicate_candidate_obligation_count: int
    duplicate_candidate_notional_usd: float
    explicit_rate_obligation_count: int
    measured_rate_obligation_count: int
    missing_rate_obligation_count: int
    rate_outlier_obligation_count: int
    explicit_rate_notional_usd: float
    measured_rate_notional_usd: float
    missing_rate_notional_usd: float
    rate_outlier_notional_usd: float
    measured_annual_interest_usd: float
    measured_rate_notional_coverage_pct: float
    distinct_measured_rate_notional_usd: float
    distinct_missing_rate_notional_usd: float
    distinct_measured_annual_interest_usd: float
    distinct_measured_rate_notional_coverage_pct: float
    obligations_missing_maturity_count: int
    notional_missing_maturity_usd: float
    distinct_obligations_missing_maturity_count: int
    distinct_notional_missing_maturity_usd: float
    maturity_wall_notional_usd_2024_2030: float
    maturity_wall_measured_annual_interest_usd_2024_2030: float
    maturity_wall_missing_rate_notional_usd_2024_2030: float
    distinct_maturity_wall_notional_usd_2024_2030: float
    distinct_maturity_wall_measured_annual_interest_usd_2024_2030: float
    distinct_maturity_wall_missing_rate_notional_usd_2024_2030: float
    debt_service_wall_by_quarter: dict[str, dict[str, float | int]]
    distinct_debt_service_wall_by_quarter: dict[str, dict[str, float | int]]
    payback_case_count: int
    payback_cases_with_debt_service: int
    payback_cases_missing_debt_service: int
    payback_cases_with_gross_cash_flow: int
    cash_flow_mismatch_red_flag_count: int
    top_debt_service_obligations: list[DebtServiceObligation]
    top_debt_service_coverage_gaps: list[DebtServiceObligation]
    top_debt_service_quarters: list[DebtServiceQuarter]
    top_distinct_debt_service_quarters: list[DebtServiceQuarter]
    top_duplicate_candidate_groups: list[DebtServiceDuplicateGroup]
    top_entity_debt_service_risks: list[DebtServiceEntityRisk]
    top_cash_flow_mismatch_cases: list[CashFlowMismatchCase]
    evidence_summary: dict[str, Any]
    status: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["top_debt_service_obligations"] = [
            item.to_dict() for item in self.top_debt_service_obligations
        ]
        data["top_debt_service_coverage_gaps"] = [
            item.to_dict() for item in self.top_debt_service_coverage_gaps
        ]
        data["top_debt_service_quarters"] = [
            item.to_dict() for item in self.top_debt_service_quarters
        ]
        data["top_distinct_debt_service_quarters"] = [
            item.to_dict() for item in self.top_distinct_debt_service_quarters
        ]
        data["top_duplicate_candidate_groups"] = [
            item.to_dict() for item in self.top_duplicate_candidate_groups
        ]
        data["top_entity_debt_service_risks"] = [
            item.to_dict() for item in self.top_entity_debt_service_risks
        ]
        data["top_cash_flow_mismatch_cases"] = [
            item.to_dict() for item in self.top_cash_flow_mismatch_cases
        ]
        return data


class DebtServiceAnalyzer:
    """Compute measured debt-service exposure from source-backed rows only."""

    VERSION = "debt-service-v1"

    def __init__(self, evidence_gate: EvidenceGate | None = None) -> None:
        self.evidence_gate = evidence_gate or EvidenceGate()

    def analyze(
        self,
        deals: Sequence[Deal],
        payback_cases: Sequence[CapexPaybackCase],
    ) -> DebtServiceMetrics:
        scoped_deals, scope_summary = scope_deals(deals)
        debt_like = [deal for deal in scoped_deals if _is_debt_like(deal)]
        obligations = [
            obligation
            for deal in debt_like
            for obligation in self._obligations_for_deal(deal)
            if obligation.notional_usd > 0
        ]
        distinct_obligations, duplicate_groups = _distinct_obligations(obligations)
        measured_obligations = [
            obligation
            for obligation in obligations
            if obligation.annual_interest_usd is not None
            and "rate_out_of_range" not in obligation.flags
        ]
        explicit_rate_obligations = [
            obligation for obligation in obligations if obligation.interest_rate_pct is not None
        ]
        missing_rate_obligations = [
            obligation for obligation in obligations if "missing_interest_rate" in obligation.flags
        ]
        rate_outlier_obligations = [
            obligation for obligation in obligations if "rate_out_of_range" in obligation.flags
        ]
        distinct_measured_obligations = [
            obligation
            for obligation in distinct_obligations
            if obligation.annual_interest_usd is not None
            and "rate_out_of_range" not in obligation.flags
        ]
        distinct_missing_rate_obligations = [
            obligation
            for obligation in distinct_obligations
            if "missing_interest_rate" in obligation.flags
        ]
        cash_flow_cases = [self._cash_flow_case(case) for case in payback_cases]
        debt_service_quarters = _quarter_rollups(obligations)
        distinct_debt_service_quarters = _quarter_rollups(distinct_obligations)
        entity_risks = _entity_rollups(distinct_obligations)
        obligations_missing_maturity = [
            obligation for obligation in obligations if _maturity_date(obligation) is None
        ]
        distinct_obligations_missing_maturity = [
            obligation for obligation in distinct_obligations if _maturity_date(obligation) is None
        ]

        measured_rate_notional = sum(item.notional_usd for item in measured_obligations)
        distinct_debt_like_notional = sum(item.notional_usd for item in distinct_obligations)
        distinct_measured_rate_notional = sum(
            item.notional_usd for item in distinct_measured_obligations
        )
        distinct_missing_rate_notional = sum(
            item.notional_usd for item in distinct_missing_rate_obligations
        )
        debt_like_notional = sum(_deal_notional(deal) for deal in debt_like)
        measured_annual_interest = sum(
            item.annual_interest_usd or 0.0 for item in measured_obligations
        )
        distinct_measured_annual_interest = sum(
            item.annual_interest_usd or 0.0 for item in distinct_measured_obligations
        )
        evidence_summary = self._evidence_summary(
            measured_obligations=measured_obligations,
            missing_rate_obligations=missing_rate_obligations,
            cash_flow_cases=cash_flow_cases,
            measured_annual_interest=measured_annual_interest,
            missing_rate_notional=sum(item.notional_usd for item in missing_rate_obligations),
            distinct_measured_annual_interest=distinct_measured_annual_interest,
            duplicate_candidate_notional=sum(
                group.duplicate_notional_usd for group in duplicate_groups
            ),
        )
        status = (
            "measured_partial"
            if measured_obligations or any(case.annual_debt_service_usd for case in payback_cases)
            else "blocked_missing_debt_service_evidence"
        )
        return DebtServiceMetrics(
            deal_count_scanned=len(deals),
            scoped_deal_count=scope_summary.in_scope_deal_count,
            out_of_scope_deal_count=scope_summary.out_of_scope_deal_count,
            debt_like_deal_count=len(debt_like),
            out_of_scope_debt_like_deal_count=scope_summary.out_of_scope_debt_like_deal_count,
            debt_like_notional_usd=round(debt_like_notional, 2),
            out_of_scope_debt_like_notional_usd=scope_summary.out_of_scope_debt_like_notional_usd,
            scope_inclusion_reason_counts=scope_summary.inclusion_reason_counts,
            obligations_count=len(obligations),
            distinct_obligations_count=len(distinct_obligations),
            duplicate_candidate_obligation_count=sum(
                group.duplicate_obligation_count for group in duplicate_groups
            ),
            duplicate_candidate_notional_usd=round(
                sum(group.duplicate_notional_usd for group in duplicate_groups),
                2,
            ),
            explicit_rate_obligation_count=len(explicit_rate_obligations),
            measured_rate_obligation_count=len(measured_obligations),
            missing_rate_obligation_count=len(missing_rate_obligations),
            rate_outlier_obligation_count=len(rate_outlier_obligations),
            explicit_rate_notional_usd=round(
                sum(item.notional_usd for item in explicit_rate_obligations),
                2,
            ),
            measured_rate_notional_usd=round(measured_rate_notional, 2),
            missing_rate_notional_usd=round(
                sum(item.notional_usd for item in missing_rate_obligations),
                2,
            ),
            rate_outlier_notional_usd=round(
                sum(item.notional_usd for item in rate_outlier_obligations),
                2,
            ),
            measured_annual_interest_usd=round(measured_annual_interest, 2),
            measured_rate_notional_coverage_pct=_pct(measured_rate_notional, debt_like_notional),
            distinct_measured_rate_notional_usd=round(distinct_measured_rate_notional, 2),
            distinct_missing_rate_notional_usd=round(distinct_missing_rate_notional, 2),
            distinct_measured_annual_interest_usd=round(distinct_measured_annual_interest, 2),
            distinct_measured_rate_notional_coverage_pct=_pct(
                distinct_measured_rate_notional,
                distinct_debt_like_notional,
            ),
            obligations_missing_maturity_count=len(obligations_missing_maturity),
            notional_missing_maturity_usd=round(
                sum(item.notional_usd for item in obligations_missing_maturity),
                2,
            ),
            distinct_obligations_missing_maturity_count=len(distinct_obligations_missing_maturity),
            distinct_notional_missing_maturity_usd=round(
                sum(item.notional_usd for item in distinct_obligations_missing_maturity),
                2,
            ),
            maturity_wall_notional_usd_2024_2030=round(
                sum(quarter.maturing_notional_usd for quarter in debt_service_quarters),
                2,
            ),
            maturity_wall_measured_annual_interest_usd_2024_2030=round(
                sum(quarter.measured_annual_interest_usd for quarter in debt_service_quarters),
                2,
            ),
            maturity_wall_missing_rate_notional_usd_2024_2030=round(
                sum(quarter.missing_rate_notional_usd for quarter in debt_service_quarters),
                2,
            ),
            distinct_maturity_wall_notional_usd_2024_2030=round(
                sum(quarter.maturing_notional_usd for quarter in distinct_debt_service_quarters),
                2,
            ),
            distinct_maturity_wall_measured_annual_interest_usd_2024_2030=round(
                sum(
                    quarter.measured_annual_interest_usd
                    for quarter in distinct_debt_service_quarters
                ),
                2,
            ),
            distinct_maturity_wall_missing_rate_notional_usd_2024_2030=round(
                sum(
                    quarter.missing_rate_notional_usd for quarter in distinct_debt_service_quarters
                ),
                2,
            ),
            debt_service_wall_by_quarter={
                quarter.quarter: {
                    "obligation_count": quarter.obligation_count,
                    "measured_rate_obligation_count": quarter.measured_rate_obligation_count,
                    "missing_rate_obligation_count": quarter.missing_rate_obligation_count,
                    "maturing_notional_usd": quarter.maturing_notional_usd,
                    "measured_rate_notional_usd": quarter.measured_rate_notional_usd,
                    "missing_rate_notional_usd": quarter.missing_rate_notional_usd,
                    "measured_annual_interest_usd": quarter.measured_annual_interest_usd,
                }
                for quarter in sorted(debt_service_quarters, key=lambda item: item.quarter)
            },
            distinct_debt_service_wall_by_quarter={
                quarter.quarter: {
                    "obligation_count": quarter.obligation_count,
                    "measured_rate_obligation_count": quarter.measured_rate_obligation_count,
                    "missing_rate_obligation_count": quarter.missing_rate_obligation_count,
                    "maturing_notional_usd": quarter.maturing_notional_usd,
                    "measured_rate_notional_usd": quarter.measured_rate_notional_usd,
                    "missing_rate_notional_usd": quarter.missing_rate_notional_usd,
                    "measured_annual_interest_usd": quarter.measured_annual_interest_usd,
                }
                for quarter in sorted(
                    distinct_debt_service_quarters,
                    key=lambda item: item.quarter,
                )
            },
            payback_case_count=len(payback_cases),
            payback_cases_with_debt_service=sum(
                case.annual_debt_service_usd is not None for case in payback_cases
            ),
            payback_cases_missing_debt_service=sum(
                case.annual_debt_service_usd is None for case in payback_cases
            ),
            payback_cases_with_gross_cash_flow=sum(
                case.annual_gross_cash_flow_usd is not None for case in cash_flow_cases
            ),
            cash_flow_mismatch_red_flag_count=sum(case.red_flag for case in cash_flow_cases),
            top_debt_service_obligations=sorted(
                measured_obligations,
                key=lambda item: item.annual_interest_usd or 0.0,
                reverse=True,
            )[:25],
            top_debt_service_coverage_gaps=sorted(
                [*missing_rate_obligations, *rate_outlier_obligations],
                key=lambda item: item.notional_usd,
                reverse=True,
            )[:25],
            top_debt_service_quarters=sorted(
                debt_service_quarters,
                key=lambda item: (
                    item.measured_annual_interest_usd,
                    item.missing_rate_notional_usd,
                    item.maturing_notional_usd,
                ),
                reverse=True,
            )[:12],
            top_distinct_debt_service_quarters=sorted(
                distinct_debt_service_quarters,
                key=lambda item: (
                    item.measured_annual_interest_usd,
                    item.missing_rate_notional_usd,
                    item.maturing_notional_usd,
                ),
                reverse=True,
            )[:12],
            top_duplicate_candidate_groups=duplicate_groups[:25],
            top_entity_debt_service_risks=entity_risks[:25],
            top_cash_flow_mismatch_cases=sorted(
                cash_flow_cases,
                key=lambda item: (
                    item.red_flag,
                    len(item.blocking_issues),
                    -(item.debt_service_coverage_ratio or 999.0),
                    item.capex_usd,
                ),
                reverse=True,
            )[:25],
            evidence_summary=evidence_summary,
            status=status,
        )

    def _obligations_for_deal(self, deal: Deal) -> list[DebtServiceObligation]:
        deal_rate = _coerce_rate(_first_key_term(deal.key_terms, RATE_KEY_CANDIDATES))
        if deal.debt_tranches:
            return [
                self._obligation_for_tranche(deal=deal, tranche=tranche, deal_rate=deal_rate)
                for tranche in deal.debt_tranches
            ]
        return [
            self._obligation_from_parts(
                deal=deal,
                tranche_name=None,
                notional=_deal_notional(deal),
                raw_rate=deal_rate,
                rate_source="deal_key_terms" if deal_rate is not None else "missing",
                maturity_date=deal.maturity_date.isoformat() if deal.maturity_date else None,
                provenance=deal.provenance,
            )
        ]

    def _obligation_for_tranche(
        self,
        *,
        deal: Deal,
        tranche: DebtTranche,
        deal_rate: float | None,
    ) -> DebtServiceObligation:
        tranche_rate = _coerce_rate(tranche.interest_rate)
        raw_rate = tranche_rate if tranche_rate is not None else deal_rate
        rate_source = "tranche" if tranche_rate is not None else "deal_key_terms"
        if raw_rate is None:
            rate_source = "missing"
        return self._obligation_from_parts(
            deal=deal,
            tranche_name=tranche.name,
            notional=tranche.notional_usd,
            raw_rate=raw_rate,
            rate_source=rate_source,
            maturity_date=(
                tranche.maturity.isoformat()
                if tranche.maturity
                else deal.maturity_date.isoformat()
                if deal.maturity_date
                else None
            ),
            provenance=tranche.provenance,
        )

    def _obligation_from_parts(
        self,
        *,
        deal: Deal,
        tranche_name: str | None,
        notional: float,
        raw_rate: float | None,
        rate_source: str,
        maturity_date: str | None,
        provenance: Provenance,
    ) -> DebtServiceObligation:
        flags: list[str] = []
        annual_interest = None
        if raw_rate is None:
            flags.append("missing_interest_rate")
        elif raw_rate <= 0 or raw_rate > MAX_MEASURED_RATE_DECIMAL:
            flags.append("rate_out_of_range")
        else:
            annual_interest = notional * raw_rate
        return DebtServiceObligation(
            deal_ref=deal.source_deal_id or str(deal.id),
            title=deal.title,
            entity=_primary_entity(deal),
            deal_type=deal.deal_type.value,
            tranche_name=tranche_name,
            notional_usd=round(notional, 2),
            interest_rate_pct=round(raw_rate * 100, 4) if raw_rate is not None else None,
            annual_interest_usd=round(annual_interest, 2) if annual_interest is not None else None,
            maturity_date=maturity_date,
            source_uri=provenance.source_uri,
            retrieved_at=provenance.retrieved_at.isoformat(),
            content_hash=provenance.content_hash,
            human_review_status=provenance.human_review_status.value,
            rate_source=rate_source,
            flags=flags,
            source_provenance=provenance,
        )

    @staticmethod
    def _cash_flow_case(case: CapexPaybackCase) -> CashFlowMismatchCase:
        blocking_issues: list[str] = []
        if case.annual_revenue_run_rate_usd is None:
            blocking_issues.append("missing_annual_revenue_run_rate")
        if case.gross_margin_pct is None:
            blocking_issues.append("missing_gross_margin")
        if case.annual_debt_service_usd is None:
            blocking_issues.append("missing_annual_debt_service")

        annual_gross_cash_flow = None
        debt_service_coverage = None
        cash_after_debt_service = None
        if case.annual_revenue_run_rate_usd is not None and case.gross_margin_pct is not None:
            annual_gross_cash_flow = (
                case.annual_revenue_run_rate_usd * (case.gross_margin_pct / 100)
            ) - (case.annual_power_cost_usd or 0.0)
        if (
            annual_gross_cash_flow is not None
            and case.annual_debt_service_usd is not None
            and case.annual_debt_service_usd > 0
        ):
            debt_service_coverage = annual_gross_cash_flow / case.annual_debt_service_usd
            cash_after_debt_service = annual_gross_cash_flow - case.annual_debt_service_usd

        red_flag = any(
            (
                debt_service_coverage is not None and debt_service_coverage < 1.2,
                cash_after_debt_service is not None and cash_after_debt_service <= 0,
                annual_gross_cash_flow is not None and annual_gross_cash_flow <= 0,
            )
        )
        return CashFlowMismatchCase(
            entity=case.entity,
            project_or_cluster_id=(
                str(case.project_or_cluster_id) if case.project_or_cluster_id else None
            ),
            capex_usd=case.capex_usd,
            annual_revenue_run_rate_usd=case.annual_revenue_run_rate_usd,
            contracted_revenue_usd=case.contracted_revenue_usd,
            utilization_pct=case.utilization_pct,
            gross_margin_pct=case.gross_margin_pct,
            annual_power_cost_usd=case.annual_power_cost_usd,
            annual_debt_service_usd=case.annual_debt_service_usd,
            annual_gross_cash_flow_usd=round(annual_gross_cash_flow, 2)
            if annual_gross_cash_flow is not None
            else None,
            debt_service_coverage_ratio=round(debt_service_coverage, 2)
            if debt_service_coverage is not None
            else None,
            cash_after_debt_service_usd=round(cash_after_debt_service, 2)
            if cash_after_debt_service is not None
            else None,
            red_flag=red_flag,
            blocking_issues=blocking_issues,
            source_uri=case.provenance.source_uri,
            retrieved_at=case.provenance.retrieved_at.isoformat(),
            content_hash=case.provenance.content_hash,
            human_review_status=case.provenance.human_review_status.value,
            source_provenance=case.provenance,
        )

    def _evidence_summary(
        self,
        *,
        measured_obligations: Sequence[DebtServiceObligation],
        missing_rate_obligations: Sequence[DebtServiceObligation],
        cash_flow_cases: Sequence[CashFlowMismatchCase],
        measured_annual_interest: float,
        missing_rate_notional: float,
        distinct_measured_annual_interest: float,
        duplicate_candidate_notional: float,
    ) -> dict[str, Any]:
        measured_sources = _source_provenance_from_obligations(measured_obligations)
        missing_sources = _source_provenance_from_obligations(missing_rate_obligations)
        cash_flow_sources = _source_provenance_from_cases(cash_flow_cases)
        audits = [
            self.evidence_gate.audit_claim(
                claim_id="debt_service.measured_annual_interest",
                claim="Annual interest/debt-service proxy from explicit source-backed rate and notional terms",
                value=round(measured_annual_interest, 2),
                unit="USD/year",
                evidence=measured_sources,
                requires_corroboration=True,
                high_impact=True,
            ),
            self.evidence_gate.audit_claim(
                claim_id="debt_service.missing_rate_notional",
                claim="Debt-like notional with no explicit source-backed rate available",
                value=round(missing_rate_notional, 2),
                unit="USD",
                evidence=missing_sources,
                requires_corroboration=True,
                high_impact=True,
            ),
            self.evidence_gate.audit_claim(
                claim_id="cash_flow.debt_service_coverage",
                claim="Project/cluster cash-flow coverage of disclosed debt service",
                value=[case.to_dict() for case in cash_flow_cases[:25]],
                unit="case-level DSCR",
                evidence=cash_flow_sources,
                requires_corroboration=False,
                high_impact=True,
            ),
            self.evidence_gate.audit_claim(
                claim_id="debt_service.distinct_measured_annual_interest",
                claim=(
                    "Deduplicated annual interest/debt-service proxy from explicit "
                    "source-backed rate and notional terms"
                ),
                value=round(distinct_measured_annual_interest, 2),
                unit="USD/year",
                evidence=measured_sources,
                requires_corroboration=True,
                high_impact=True,
            ),
            self.evidence_gate.audit_claim(
                claim_id="debt_service.duplicate_candidate_notional",
                claim=(
                    "Candidate duplicate debt-service notional removed from distinct "
                    "obligation rollups"
                ),
                value=round(duplicate_candidate_notional, 2),
                unit="USD",
                evidence=measured_sources + missing_sources,
                requires_corroboration=True,
                high_impact=True,
            ),
        ]
        return {
            "summary": self.evidence_gate.summarize(audits).to_dict(),
            "claim_audits": [audit.to_dict() for audit in audits],
            "methodology": (
                "Annual debt service is counted only when source-backed rows include positive "
                "notional and an explicit plausible rate between 0% and 20%. Missing or outlier "
                "rates are reported as coverage gaps, not imputed. Distinct rollups collapse "
                "candidate duplicate obligation rows by accession/entity/notional when available, "
                "and keep raw rows visible for audit."
            ),
        }


def analyze_debt_service(
    deals: Sequence[Deal],
    payback_cases: Sequence[CapexPaybackCase],
    *,
    analyzer: DebtServiceAnalyzer | None = None,
) -> DebtServiceMetrics:
    """Analyze debt-service coverage from source-backed capital and compute rows."""

    return (analyzer or DebtServiceAnalyzer()).analyze(deals, payback_cases)


def _is_debt_like(deal: Deal) -> bool:
    return deal.deal_type in DEBT_LIKE_DEAL_TYPES or bool(deal.debt_tranches)


def _deal_notional(deal: Deal) -> float:
    tranche_total = sum(tranche.notional_usd for tranche in deal.debt_tranches)
    if tranche_total:
        return tranche_total
    return float(deal.notional_amount_usd or 0.0)


def _primary_entity(deal: Deal) -> str | None:
    for role in ("borrower", "issuer", "lessee", "obligor", "counterparty"):
        entities = deal.counterparty_roles.get(role)
        if entities:
            return str(entities[0])
    return str(deal.parties[0]) if deal.parties else None


def _first_key_term(key_terms: dict[str, Any], keys: Sequence[str]) -> Any | None:
    for key in keys:
        value = key_terms.get(key)
        if value is not None and value != "":
            return value
    return None


def _coerce_rate(raw_rate: Any | None) -> float | None:
    if raw_rate is None:
        return None
    if isinstance(raw_rate, bool):
        return None
    if isinstance(raw_rate, int | float):
        rate = float(raw_rate)
    elif isinstance(raw_rate, str):
        stripped = raw_rate.strip()
        if not re.fullmatch(r"\d+(\.\d+)?\s*%?", stripped):
            return None
        rate = float(stripped.rstrip("%").strip())
    else:
        return None
    if rate > 1:
        rate = rate / 100
    return rate


def _pct(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def _quarter_rollups(obligations: Sequence[DebtServiceObligation]) -> list[DebtServiceQuarter]:
    by_quarter: dict[str, list[DebtServiceObligation]] = {}
    for obligation in obligations:
        quarter = _maturity_quarter(obligation)
        if quarter is None:
            continue
        by_quarter.setdefault(quarter, []).append(obligation)

    quarters: list[DebtServiceQuarter] = []
    for quarter, items in by_quarter.items():
        measured_items = [item for item in items if item.annual_interest_usd is not None]
        missing_items = [item for item in items if item.annual_interest_usd is None]
        quarters.append(
            DebtServiceQuarter(
                quarter=quarter,
                obligation_count=len(items),
                measured_rate_obligation_count=len(measured_items),
                missing_rate_obligation_count=len(missing_items),
                maturing_notional_usd=round(sum(item.notional_usd for item in items), 2),
                measured_rate_notional_usd=round(
                    sum(item.notional_usd for item in measured_items),
                    2,
                ),
                missing_rate_notional_usd=round(
                    sum(item.notional_usd for item in missing_items),
                    2,
                ),
                measured_annual_interest_usd=round(
                    sum(item.annual_interest_usd or 0.0 for item in measured_items),
                    2,
                ),
                top_obligations=sorted(
                    measured_items,
                    key=lambda item: item.annual_interest_usd or 0.0,
                    reverse=True,
                )[:10],
                top_coverage_gaps=sorted(
                    missing_items,
                    key=lambda item: item.notional_usd,
                    reverse=True,
                )[:10],
            )
        )
    return quarters


def _distinct_obligations(
    obligations: Sequence[DebtServiceObligation],
) -> tuple[list[DebtServiceObligation], list[DebtServiceDuplicateGroup]]:
    grouped: dict[str, list[DebtServiceObligation]] = {}
    for obligation in obligations:
        grouped.setdefault(_obligation_economic_key(obligation), []).append(obligation)

    distinct: list[DebtServiceObligation] = []
    duplicate_groups: list[DebtServiceDuplicateGroup] = []
    for key, group in grouped.items():
        representative = max(group, key=_representative_rank)
        distinct.append(representative)
        if len(group) <= 1:
            continue
        raw_notional = sum(item.notional_usd for item in group)
        distinct_notional = representative.notional_usd
        duplicate_groups.append(
            DebtServiceDuplicateGroup(
                economic_key=key,
                representative_deal_ref=representative.deal_ref,
                duplicate_obligation_count=len(group) - 1,
                raw_notional_usd=round(raw_notional, 2),
                distinct_notional_usd=round(distinct_notional, 2),
                duplicate_notional_usd=round(raw_notional - distinct_notional, 2),
                source_uris=sorted({item.source_uri for item in group})[:20],
                deal_refs=sorted({item.deal_ref for item in group})[:20],
            )
        )
    duplicate_groups.sort(key=lambda group: group.duplicate_notional_usd, reverse=True)
    return distinct, duplicate_groups


def _entity_rollups(obligations: Sequence[DebtServiceObligation]) -> list[DebtServiceEntityRisk]:
    grouped: dict[str, list[DebtServiceObligation]] = {}
    labels: dict[str, str] = {}
    for obligation in obligations:
        entity = obligation.entity or "Unknown"
        key = canonical_entity_key(entity)
        labels.setdefault(key, entity)
        grouped.setdefault(key, []).append(obligation)

    risks: list[DebtServiceEntityRisk] = []
    for entity_key, items in grouped.items():
        measured_items = [
            item
            for item in items
            if item.annual_interest_usd is not None and "rate_out_of_range" not in item.flags
        ]
        missing_rate_items = [item for item in items if "missing_interest_rate" in item.flags]
        rate_outlier_items = [item for item in items if "rate_out_of_range" in item.flags]
        missing_maturity_items = [item for item in items if _maturity_date(item) is None]
        quarters = _quarter_rollups(items)
        peak_quarter = _peak_quarter(quarters)
        maturity_wall_notional = sum(quarter.maturing_notional_usd for quarter in quarters)
        maturity_wall_interest = sum(quarter.measured_annual_interest_usd for quarter in quarters)
        maturity_wall_missing_rate = sum(quarter.missing_rate_notional_usd for quarter in quarters)
        risks.append(
            DebtServiceEntityRisk(
                entity=labels[entity_key],
                distinct_obligation_count=len(items),
                measured_rate_obligation_count=len(measured_items),
                missing_rate_obligation_count=len(missing_rate_items),
                rate_outlier_obligation_count=len(rate_outlier_items),
                distinct_notional_usd=round(sum(item.notional_usd for item in items), 2),
                measured_rate_notional_usd=round(
                    sum(item.notional_usd for item in measured_items),
                    2,
                ),
                missing_rate_notional_usd=round(
                    sum(item.notional_usd for item in missing_rate_items),
                    2,
                ),
                rate_outlier_notional_usd=round(
                    sum(item.notional_usd for item in rate_outlier_items),
                    2,
                ),
                measured_annual_interest_usd=round(
                    sum(item.annual_interest_usd or 0.0 for item in measured_items),
                    2,
                ),
                maturity_wall_notional_usd_2024_2030=round(maturity_wall_notional, 2),
                maturity_wall_measured_annual_interest_usd_2024_2030=round(
                    maturity_wall_interest,
                    2,
                ),
                maturity_wall_missing_rate_notional_usd_2024_2030=round(
                    maturity_wall_missing_rate,
                    2,
                ),
                obligations_missing_maturity_count=len(missing_maturity_items),
                notional_missing_maturity_usd=round(
                    sum(item.notional_usd for item in missing_maturity_items),
                    2,
                ),
                peak_maturity_quarter=peak_quarter.quarter if peak_quarter else None,
                peak_maturity_notional_usd=peak_quarter.maturing_notional_usd
                if peak_quarter
                else 0.0,
                peak_measured_annual_interest_usd=(
                    peak_quarter.measured_annual_interest_usd if peak_quarter else 0.0
                ),
                debt_service_wall_by_quarter={
                    quarter.quarter: {
                        "obligation_count": quarter.obligation_count,
                        "measured_rate_obligation_count": quarter.measured_rate_obligation_count,
                        "missing_rate_obligation_count": quarter.missing_rate_obligation_count,
                        "maturing_notional_usd": quarter.maturing_notional_usd,
                        "measured_rate_notional_usd": quarter.measured_rate_notional_usd,
                        "missing_rate_notional_usd": quarter.missing_rate_notional_usd,
                        "measured_annual_interest_usd": quarter.measured_annual_interest_usd,
                    }
                    for quarter in sorted(quarters, key=lambda item: item.quarter)
                },
                review_priority_reasons=_entity_review_reasons(
                    missing_rate_items=missing_rate_items,
                    rate_outlier_items=rate_outlier_items,
                    missing_maturity_items=missing_maturity_items,
                    measured_items=measured_items,
                    peak_quarter=peak_quarter,
                ),
                top_obligations=sorted(
                    measured_items,
                    key=lambda item: item.annual_interest_usd or 0.0,
                    reverse=True,
                )[:10],
                top_coverage_gaps=sorted(
                    [*missing_rate_items, *rate_outlier_items, *missing_maturity_items],
                    key=lambda item: item.notional_usd,
                    reverse=True,
                )[:10],
            )
        )

    risks.sort(key=_entity_risk_rank, reverse=True)
    return risks


def _peak_quarter(quarters: Sequence[DebtServiceQuarter]) -> DebtServiceQuarter | None:
    if not quarters:
        return None
    return max(
        quarters,
        key=lambda quarter: (
            quarter.measured_annual_interest_usd,
            quarter.missing_rate_notional_usd,
            quarter.maturing_notional_usd,
        ),
    )


def _entity_risk_rank(risk: DebtServiceEntityRisk) -> tuple[float, float, float, float, float]:
    return (
        risk.maturity_wall_measured_annual_interest_usd_2024_2030,
        risk.maturity_wall_missing_rate_notional_usd_2024_2030,
        risk.notional_missing_maturity_usd,
        risk.measured_annual_interest_usd,
        risk.distinct_notional_usd,
    )


def _entity_review_reasons(
    *,
    missing_rate_items: Sequence[DebtServiceObligation],
    rate_outlier_items: Sequence[DebtServiceObligation],
    missing_maturity_items: Sequence[DebtServiceObligation],
    measured_items: Sequence[DebtServiceObligation],
    peak_quarter: DebtServiceQuarter | None,
) -> list[str]:
    reasons: list[str] = []
    missing_rate_notional = sum(item.notional_usd for item in missing_rate_items)
    rate_outlier_notional = sum(item.notional_usd for item in rate_outlier_items)
    missing_maturity_notional = sum(item.notional_usd for item in missing_maturity_items)
    measured_interest = sum(item.annual_interest_usd or 0.0 for item in measured_items)
    if measured_interest > 0:
        reasons.append("measured_debt_service")
    if missing_rate_notional > 0:
        reasons.append("missing_interest_rate")
    if rate_outlier_notional > 0:
        reasons.append("rate_outlier")
    if missing_maturity_notional > 0:
        reasons.append("missing_maturity")
    if peak_quarter is not None:
        reasons.append(f"peak_maturity_quarter:{peak_quarter.quarter}")
    return reasons


def _obligation_economic_key(obligation: DebtServiceObligation) -> str:
    if obligation.notional_usd <= 0:
        return f"source:{obligation.deal_ref}"
    entity = canonical_entity_key(obligation.entity or "unknown")
    notional = f"{obligation.notional_usd:.2f}"
    if obligation.tranche_name:
        return "|".join(
            [
                "tranche",
                entity,
                _normalized_key(obligation.tranche_name),
                obligation.deal_type,
                notional,
                obligation.maturity_date or "",
            ]
        )
    accession = _accession_from_deal_ref(obligation.deal_ref)
    if accession:
        return "|".join(["accession", entity, accession, notional])
    return "|".join(
        [
            "terms",
            entity,
            obligation.deal_type,
            notional,
            obligation.maturity_date or "",
        ]
    )


def _representative_rank(obligation: DebtServiceObligation) -> tuple[int, int, int, float, float]:
    reviewed = 1 if obligation.human_review_status in {"approved", "overridden"} else 0
    measured = 1 if obligation.annual_interest_usd is not None else 0
    has_maturity = 1 if _maturity_date(obligation) is not None else 0
    plausible_rate = 0 if "rate_out_of_range" in obligation.flags else 1
    return (
        measured,
        has_maturity,
        plausible_rate,
        obligation.notional_usd,
        reviewed,
    )


def _accession_from_deal_ref(deal_ref: str) -> str | None:
    match = re.match(r"^edgar:\d{1,10}:(?P<accession>\d{18}):", deal_ref)
    if not match:
        return None
    return match.group("accession")


def _normalized_key(value: str) -> str:
    return " ".join(value.lower().split())


def _maturity_quarter(obligation: DebtServiceObligation) -> str | None:
    maturity = _maturity_date(obligation)
    if maturity is None:
        return None
    if not START_YEAR <= maturity.year <= END_YEAR:
        return None
    quarter = ((maturity.month - 1) // 3) + 1
    return f"{maturity.year}-Q{quarter}"


def _maturity_date(obligation: DebtServiceObligation) -> date | None:
    if not obligation.maturity_date:
        return None
    try:
        return date.fromisoformat(obligation.maturity_date)
    except ValueError:
        return None


def _source_provenance_from_obligations(
    obligations: Sequence[DebtServiceObligation],
) -> list[Provenance]:
    return [obligation.source_provenance for obligation in obligations]


def _source_provenance_from_cases(cases: Sequence[CashFlowMismatchCase]) -> list[Provenance]:
    return [case.source_provenance for case in cases]
