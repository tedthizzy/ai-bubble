"""Compute economics analysis for GPU depreciation, TAM, payback, EPS, and supply risk."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from bubble.analysis.evidence import EvidenceGate

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from bubble.models.base import Provenance
    from bubble.models.compute import (
        CapexPaybackCase,
        ChipSupplyObservation,
        ComputeAsset,
        DepreciationPolicy,
        EpsDepreciationImpact,
        GpuPriceObservation,
        TamClaim,
    )


@dataclass(frozen=True)
class GpuDepreciationRisk:
    """Observed value/rental compression for one GPU generation."""

    gpu_generation: str
    observation_count: int
    latest_observed_date: str | None
    peak_price_usd: float | None
    latest_secondary_price_usd: float | None
    price_depreciation_pct: float | None
    peak_rental_rate_usd_per_hour: float | None
    latest_rental_rate_usd_per_hour: float | None
    rental_rate_decline_pct: float | None
    accounting_useful_life_years: float | None
    modeled_economic_life_years: float | None
    useful_life_gap_years: float | None
    red_flag: bool
    evidence_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TamRealityCheck:
    """Stated TAM versus realized revenue comparator."""

    entity: str
    claimed_market: str
    stated_tam_usd: float
    realized_revenue_usd: float | None
    tam_to_revenue_multiple: float | None
    implied_revenue_capture_assumption_pct: float | None
    red_flag: bool
    source_uri: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaybackStressResult:
    """Payback and coverage math for one capex case."""

    entity: str
    project_or_cluster_id: str | None
    capex_usd: float
    annual_gross_cash_flow_usd: float | None
    payback_years: float | None
    depreciation_life_years: float | None
    debt_service_coverage_ratio: float | None
    red_flag: bool
    blocking_issues: list[str]
    source_uri: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EpsImpactResult:
    """Accelerated depreciation impact for one fiscal year/entity."""

    entity: str
    fiscal_year: int
    accounting_depreciation_usd: float | None
    economic_depreciation_usd: float | None
    incremental_depreciation_usd: float | None
    after_tax_income_drag_usd: float | None
    eps_drag: float | None
    disclosed_depreciation_usd: float | None
    disclosed_net_income_impact_usd: float | None
    disclosed_eps_impact_usd: float | None
    impact_direction: str | None
    red_flag: bool
    source_uri: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ChipSupplyGap:
    """Announced versus observed GPU delivery gap."""

    entity: str
    project_or_cluster_id: str | None
    gpu_generation: str
    announced_gpu_count: int | None
    delivered_gpu_count: int | None
    delivery_gap_count: int | None
    announced_mw: float | None
    disclosed_purchase_commitment_usd: float | None
    implied_gpus_per_mw: float | None
    red_flag: bool
    source_uri: str
    source_quote: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ComputeEconomicsMetrics:
    """Rollup for the compute economics layer."""

    compute_asset_count: int
    gpu_price_observation_count: int
    depreciation_policy_count: int
    tam_claim_count: int
    payback_case_count: int
    payback_blocked_case_count: int
    payback_missing_debt_service_count: int
    eps_impact_count: int
    chip_supply_observation_count: int
    total_gpu_capex_usd: float
    gpu_depreciation_red_flag_count: int
    gpu_depreciation_blocked_generation_count: int
    tam_red_flag_count: int
    tam_blocked_claim_count: int
    payback_red_flag_count: int
    eps_red_flag_count: int
    eps_blocked_impact_count: int
    chip_supply_red_flag_count: int
    chip_supply_blocked_observation_count: int
    top_gpu_depreciation_risks: list[GpuDepreciationRisk]
    top_tam_reality_checks: list[TamRealityCheck]
    top_payback_stress_cases: list[PaybackStressResult]
    top_eps_impacts: list[EpsImpactResult]
    top_chip_supply_gaps: list[ChipSupplyGap]
    evidence_summary: dict[str, Any]
    status: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["top_gpu_depreciation_risks"] = [
            item.to_dict() for item in self.top_gpu_depreciation_risks
        ]
        data["top_tam_reality_checks"] = [item.to_dict() for item in self.top_tam_reality_checks]
        data["top_payback_stress_cases"] = [
            item.to_dict() for item in self.top_payback_stress_cases
        ]
        data["top_eps_impacts"] = [item.to_dict() for item in self.top_eps_impacts]
        data["top_chip_supply_gaps"] = [item.to_dict() for item in self.top_chip_supply_gaps]
        return data


@dataclass(frozen=True)
class ComputeEconomicsBatch:
    """Source-backed compute economics rows."""

    assets: list[ComputeAsset]
    gpu_price_observations: list[GpuPriceObservation]
    depreciation_policies: list[DepreciationPolicy]
    tam_claims: list[TamClaim]
    payback_cases: list[CapexPaybackCase]
    eps_impacts: list[EpsDepreciationImpact]
    chip_supply_observations: list[ChipSupplyObservation]

    @property
    def row_count(self) -> int:
        return (
            len(self.assets)
            + len(self.gpu_price_observations)
            + len(self.depreciation_policies)
            + len(self.tam_claims)
            + len(self.payback_cases)
            + len(self.eps_impacts)
            + len(self.chip_supply_observations)
        )


class ComputeEconomicsAnalyzer:
    """Deterministic compute-economics stress analysis."""

    def analyze(self, batch: ComputeEconomicsBatch) -> ComputeEconomicsMetrics:
        gpu_risks = self._gpu_depreciation_risks(
            batch.gpu_price_observations,
            batch.assets,
            batch.depreciation_policies,
        )
        tam_checks = self._tam_reality_checks(batch.tam_claims)
        payback_results = self._payback_results(batch.payback_cases)
        eps_results = self._eps_results(batch.eps_impacts)
        chip_supply_gaps = self._chip_supply_gaps(batch.chip_supply_observations)
        evidence_summary = self._evidence_summary(batch)
        return ComputeEconomicsMetrics(
            compute_asset_count=len(batch.assets),
            gpu_price_observation_count=len(batch.gpu_price_observations),
            depreciation_policy_count=len(batch.depreciation_policies),
            tam_claim_count=len(batch.tam_claims),
            payback_case_count=len(batch.payback_cases),
            payback_blocked_case_count=sum(
                bool(item.blocking_issues) or item.payback_years is None for item in payback_results
            ),
            payback_missing_debt_service_count=sum(
                item.debt_service_coverage_ratio is None for item in payback_results
            ),
            eps_impact_count=len(batch.eps_impacts),
            chip_supply_observation_count=len(batch.chip_supply_observations),
            total_gpu_capex_usd=round(
                sum(asset.capex_usd or 0.0 for asset in batch.assets),
                2,
            ),
            gpu_depreciation_red_flag_count=sum(item.red_flag for item in gpu_risks),
            gpu_depreciation_blocked_generation_count=sum(
                item.price_depreciation_pct is None
                and item.rental_rate_decline_pct is None
                and item.useful_life_gap_years is None
                for item in gpu_risks
            ),
            tam_red_flag_count=sum(item.red_flag for item in tam_checks),
            tam_blocked_claim_count=sum(
                item.tam_to_revenue_multiple is None
                and item.implied_revenue_capture_assumption_pct is None
                for item in tam_checks
            ),
            payback_red_flag_count=sum(item.red_flag for item in payback_results),
            eps_red_flag_count=sum(item.red_flag for item in eps_results),
            eps_blocked_impact_count=sum(
                item.economic_depreciation_usd is None or item.eps_drag is None
                for item in eps_results
            ),
            chip_supply_red_flag_count=sum(item.red_flag for item in chip_supply_gaps),
            chip_supply_blocked_observation_count=sum(
                item.delivery_gap_count is None for item in chip_supply_gaps
            ),
            top_gpu_depreciation_risks=sorted(
                gpu_risks,
                key=lambda item: (
                    item.red_flag,
                    item.price_depreciation_pct or 0.0,
                    item.rental_rate_decline_pct or 0.0,
                ),
                reverse=True,
            )[:10],
            top_tam_reality_checks=sorted(
                tam_checks,
                key=lambda item: (
                    item.red_flag,
                    item.tam_to_revenue_multiple or 0.0,
                    item.implied_revenue_capture_assumption_pct or 0.0,
                ),
                reverse=True,
            )[:10],
            top_payback_stress_cases=sorted(
                payback_results,
                key=lambda item: (
                    item.red_flag,
                    item.payback_years or 0.0,
                    -(item.debt_service_coverage_ratio or 999.0),
                ),
                reverse=True,
            )[:10],
            top_eps_impacts=sorted(
                eps_results,
                key=lambda item: (
                    item.red_flag,
                    item.incremental_depreciation_usd or 0.0,
                    item.disclosed_depreciation_usd or 0.0,
                ),
                reverse=True,
            )[:10],
            top_chip_supply_gaps=sorted(
                chip_supply_gaps,
                key=lambda item: (item.red_flag, item.delivery_gap_count or 0),
                reverse=True,
            )[:10],
            evidence_summary=evidence_summary,
            status="measured" if batch.row_count else "blocked_missing_compute_economics_evidence",
        )

    def _gpu_depreciation_risks(
        self,
        observations: Sequence[GpuPriceObservation],
        assets: Sequence[ComputeAsset],
        policies: Sequence[DepreciationPolicy],
    ) -> list[GpuDepreciationRisk]:
        by_generation: dict[str, list[GpuPriceObservation]] = defaultdict(list)
        for observation in observations:
            by_generation[_normalize_generation(observation.gpu_generation)].append(observation)

        assets_by_generation: dict[str, list[ComputeAsset]] = defaultdict(list)
        for asset in assets:
            assets_by_generation[_normalize_generation(asset.gpu_generation)].append(asset)

        policy_life_by_entity = {
            _normalize_key(policy.entity): policy.accounting_useful_life_years
            for policy in policies
            if "gpu" in policy.asset_class.lower() or "server" in policy.asset_class.lower()
        }

        risks: list[GpuDepreciationRisk] = []
        for generation, generation_observations in by_generation.items():
            ordered = sorted(generation_observations, key=lambda item: item.observed_date)
            latest_observed_date = max(item.observed_date for item in ordered)
            peak_price, latest_price, price_depreciation = _price_depreciation_summary(ordered)
            peak_rental, latest_rental, rental_decline = _rental_decline_summary(ordered)
            accounting_life = _min_optional(
                [
                    *(
                        asset.accounting_useful_life_years
                        for asset in assets_by_generation[generation]
                    ),
                    *(
                        policy_life_by_entity.get(_normalize_key(asset.entity))
                        for asset in assets_by_generation[generation]
                    ),
                ]
            )
            economic_life = _min_optional(
                [asset.modeled_economic_life_years for asset in assets_by_generation[generation]]
            )
            useful_life_gap = (
                round(accounting_life - economic_life, 2)
                if accounting_life is not None and economic_life is not None
                else None
            )
            red_flag = any(
                (
                    price_depreciation is not None and price_depreciation >= 50,
                    rental_decline is not None and rental_decline >= 40,
                    useful_life_gap is not None and useful_life_gap >= 2,
                )
            )
            risks.append(
                GpuDepreciationRisk(
                    gpu_generation=generation,
                    observation_count=len(generation_observations),
                    latest_observed_date=latest_observed_date.isoformat(),
                    peak_price_usd=peak_price,
                    latest_secondary_price_usd=latest_price,
                    price_depreciation_pct=price_depreciation,
                    peak_rental_rate_usd_per_hour=peak_rental,
                    latest_rental_rate_usd_per_hour=latest_rental,
                    rental_rate_decline_pct=rental_decline,
                    accounting_useful_life_years=accounting_life,
                    modeled_economic_life_years=economic_life,
                    useful_life_gap_years=useful_life_gap,
                    red_flag=red_flag,
                    evidence_count=len({item.provenance.source_uri for item in ordered}),
                )
            )
        return risks

    def _tam_reality_checks(self, claims: Sequence[TamClaim]) -> list[TamRealityCheck]:
        checks: list[TamRealityCheck] = []
        for claim in claims:
            multiple = (
                round(claim.stated_tam_usd / claim.realized_revenue_usd, 2)
                if claim.realized_revenue_usd
                else None
            )
            red_flag = any(
                (
                    multiple is not None and multiple >= 10,
                    (claim.implied_revenue_capture_assumption_pct or 0.0) >= 20,
                )
            )
            checks.append(
                TamRealityCheck(
                    entity=claim.entity,
                    claimed_market=claim.claimed_market,
                    stated_tam_usd=claim.stated_tam_usd,
                    realized_revenue_usd=claim.realized_revenue_usd,
                    tam_to_revenue_multiple=multiple,
                    implied_revenue_capture_assumption_pct=(
                        claim.implied_revenue_capture_assumption_pct
                    ),
                    red_flag=red_flag,
                    source_uri=claim.provenance.source_uri,
                )
            )
        return checks

    def _payback_results(self, cases: Sequence[CapexPaybackCase]) -> list[PaybackStressResult]:
        results: list[PaybackStressResult] = []
        for case in cases:
            blocking_issues: list[str] = []
            annual_gross_cash_flow = None
            revenue = case.annual_revenue_run_rate_usd
            gross_margin = case.gross_margin_pct
            if revenue is None:
                blocking_issues.append("Missing annual revenue run rate.")
            if gross_margin is None:
                blocking_issues.append("Missing gross margin.")
            if revenue is not None and gross_margin is not None:
                annual_gross_cash_flow = (revenue * (gross_margin / 100)) - (
                    case.annual_power_cost_usd or 0.0
                )
            payback_years = (
                round(case.capex_usd / annual_gross_cash_flow, 2)
                if annual_gross_cash_flow and annual_gross_cash_flow > 0
                else None
            )
            debt_service_coverage = (
                round(annual_gross_cash_flow / case.annual_debt_service_usd, 2)
                if annual_gross_cash_flow
                and case.annual_debt_service_usd
                and case.annual_debt_service_usd > 0
                else None
            )
            red_flag = any(
                (
                    payback_years is not None
                    and case.depreciation_life_years is not None
                    and payback_years > case.depreciation_life_years,
                    debt_service_coverage is not None and debt_service_coverage < 1.2,
                    annual_gross_cash_flow is not None and annual_gross_cash_flow <= 0,
                )
            )
            results.append(
                PaybackStressResult(
                    entity=case.entity,
                    project_or_cluster_id=(
                        str(case.project_or_cluster_id) if case.project_or_cluster_id else None
                    ),
                    capex_usd=case.capex_usd,
                    annual_gross_cash_flow_usd=(
                        round(annual_gross_cash_flow, 2)
                        if annual_gross_cash_flow is not None
                        else None
                    ),
                    payback_years=payback_years,
                    depreciation_life_years=case.depreciation_life_years,
                    debt_service_coverage_ratio=debt_service_coverage,
                    red_flag=red_flag,
                    blocking_issues=blocking_issues,
                    source_uri=case.provenance.source_uri,
                )
            )
        return results

    def _eps_results(self, impacts: Sequence[EpsDepreciationImpact]) -> list[EpsImpactResult]:
        results: list[EpsImpactResult] = []
        for impact in impacts:
            accounting_depreciation = None
            economic_depreciation = None
            incremental = None
            after_tax_drag = None
            eps_drag = None
            if (
                impact.gpu_capex_estimate_usd is not None
                and impact.accounting_useful_life_years is not None
                and impact.modeled_economic_life_years is not None
            ):
                accounting_depreciation = (
                    impact.gpu_capex_estimate_usd / impact.accounting_useful_life_years
                )
                economic_depreciation = (
                    impact.gpu_capex_estimate_usd / impact.modeled_economic_life_years
                )
                incremental = max(0.0, economic_depreciation - accounting_depreciation)
                tax_rate = (impact.tax_rate_pct or 0.0) / 100
                after_tax_drag = incremental * (1 - tax_rate)
                eps_drag = after_tax_drag / impact.diluted_shares if impact.diluted_shares else None
            results.append(
                EpsImpactResult(
                    entity=impact.entity,
                    fiscal_year=impact.fiscal_year,
                    accounting_depreciation_usd=(
                        round(accounting_depreciation, 2)
                        if accounting_depreciation is not None
                        else None
                    ),
                    economic_depreciation_usd=(
                        round(economic_depreciation, 2)
                        if economic_depreciation is not None
                        else None
                    ),
                    incremental_depreciation_usd=(
                        round(incremental, 2) if incremental is not None else None
                    ),
                    after_tax_income_drag_usd=(
                        round(after_tax_drag, 2) if after_tax_drag is not None else None
                    ),
                    eps_drag=round(eps_drag, 4) if eps_drag is not None else None,
                    disclosed_depreciation_usd=impact.disclosed_depreciation_usd,
                    disclosed_net_income_impact_usd=impact.disclosed_net_income_impact_usd,
                    disclosed_eps_impact_usd=impact.disclosed_eps_impact_usd,
                    impact_direction=impact.impact_direction,
                    red_flag=(incremental or 0.0) > 0
                    or (impact.disclosed_depreciation_usd or 0.0) >= 1_000_000_000,
                    source_uri=impact.provenance.source_uri,
                )
            )
        return results

    def _chip_supply_gaps(
        self,
        observations: Sequence[ChipSupplyObservation],
    ) -> list[ChipSupplyGap]:
        gaps: list[ChipSupplyGap] = []
        for observation in observations:
            delivery_gap = (
                observation.announced_gpu_count - (observation.delivered_gpu_count or 0)
                if observation.announced_gpu_count is not None
                else None
            )
            implied_gpus_per_mw = (
                round(observation.announced_gpu_count / observation.announced_mw, 2)
                if observation.announced_gpu_count and observation.announced_mw
                else None
            )
            red_flag = delivery_gap is not None and delivery_gap > 0
            gaps.append(
                ChipSupplyGap(
                    entity=observation.entity,
                    project_or_cluster_id=(
                        str(observation.project_or_cluster_id)
                        if observation.project_or_cluster_id
                        else None
                    ),
                    gpu_generation=observation.gpu_generation,
                    announced_gpu_count=observation.announced_gpu_count,
                    delivered_gpu_count=observation.delivered_gpu_count,
                    delivery_gap_count=delivery_gap,
                    announced_mw=observation.announced_mw,
                    disclosed_purchase_commitment_usd=observation.disclosed_purchase_commitment_usd,
                    implied_gpus_per_mw=implied_gpus_per_mw,
                    red_flag=red_flag,
                    source_uri=observation.provenance.source_uri,
                    source_quote=observation.source_quote,
                )
            )
        return gaps

    def _evidence_summary(self, batch: ComputeEconomicsBatch) -> dict[str, Any]:
        gate = EvidenceGate(min_high_confidence=0.75, min_corroborating_sources=2)
        claim_inputs = [
            (
                "compute.assets",
                "Source-backed compute assets",
                len(batch.assets),
                "rows",
                _provenance(batch.assets),
            ),
            (
                "compute.gpu_price_observations",
                "Source-backed GPU price/rental observations",
                len(batch.gpu_price_observations),
                "rows",
                _provenance(batch.gpu_price_observations),
            ),
            (
                "compute.tam_claims",
                "Source-backed TAM claims",
                len(batch.tam_claims),
                "rows",
                _provenance(batch.tam_claims),
            ),
            (
                "compute.payback_cases",
                "Source-backed capex payback cases",
                len(batch.payback_cases),
                "rows",
                _provenance(batch.payback_cases),
            ),
            (
                "compute.eps_impacts",
                "Source-backed EPS depreciation impact cases",
                len(batch.eps_impacts),
                "rows",
                _provenance(batch.eps_impacts),
            ),
            (
                "compute.chip_supply_observations",
                "Source-backed chip supply observations",
                len(batch.chip_supply_observations),
                "rows",
                _provenance(batch.chip_supply_observations),
            ),
        ]
        audits = [
            gate.audit_claim(
                claim_id=claim_id,
                claim=claim,
                value=value,
                unit=unit,
                evidence=evidence,
                high_impact=False,
            )
            for claim_id, claim, value, unit, evidence in claim_inputs
        ]
        return {
            "summary": gate.summarize(audits).to_dict(),
            "claim_audits": [audit.to_dict() for audit in audits],
        }


def analyze_compute_economics(
    batch: ComputeEconomicsBatch,
    *,
    analyzer: ComputeEconomicsAnalyzer | None = None,
) -> ComputeEconomicsMetrics:
    """Run compute economics analysis."""

    return (analyzer or ComputeEconomicsAnalyzer()).analyze(batch)


def empty_compute_economics_batch() -> ComputeEconomicsBatch:
    """Return an empty batch for report generation when the corpus is not loaded yet."""

    return ComputeEconomicsBatch(
        assets=[],
        gpu_price_observations=[],
        depreciation_policies=[],
        tam_claims=[],
        payback_cases=[],
        eps_impacts=[],
        chip_supply_observations=[],
    )


def _pct_decline(peak: float | None, latest: float | None) -> float | None:
    if peak is None or latest is None or peak <= 0:
        return None
    return round(max(0.0, (peak - latest) / peak) * 100, 2)


def _price_depreciation_summary(
    observations: Sequence[GpuPriceObservation],
) -> tuple[float | None, float | None, float | None]:
    priced = [item for item in observations if item.observed_secondary_price_usd is not None]
    latest_price = _latest_min_value(
        priced,
        lambda item: item.observed_secondary_price_usd,
    )
    explicit_peak = _max_optional(
        [
            *(item.peak_price_usd for item in observations),
            *(item.original_price_usd for item in observations),
        ]
    )
    dated_price_count = len({item.observed_date for item in priced})
    peak_price: float | None
    if explicit_peak is not None:
        peak_price = explicit_peak
    elif dated_price_count >= 2:
        peak_price = _max_optional(item.observed_secondary_price_usd for item in priced)
    else:
        peak_price = None
    return peak_price, latest_price, _pct_decline(peak_price, latest_price)


def _rental_decline_summary(
    observations: Sequence[GpuPriceObservation],
) -> tuple[float | None, float | None, float | None]:
    rental_observations = [
        item for item in observations if item.observed_cloud_rental_rate_usd_per_hour is not None
    ]
    latest_rental = _latest_min_value(
        rental_observations,
        lambda item: item.observed_cloud_rental_rate_usd_per_hour,
    )
    best_peak: float | None = None
    best_latest: float | None = None
    best_decline: float | None = None
    series_by_key: dict[tuple[str, str, str], list[GpuPriceObservation]] = defaultdict(list)
    for item in rental_observations:
        series_by_key[_rental_series_key(item)].append(item)

    for series in series_by_key.values():
        if len({item.observed_date for item in series}) < 2:
            continue
        peak = _max_optional(item.observed_cloud_rental_rate_usd_per_hour for item in series)
        comparable_latest = _latest_min_value(
            series,
            lambda item: item.observed_cloud_rental_rate_usd_per_hour,
        )
        decline = _pct_decline(peak, comparable_latest)
        if decline is not None and (best_decline is None or decline > best_decline):
            best_peak = peak
            best_latest = comparable_latest
            best_decline = decline

    if best_decline is None:
        return None, latest_rental, None
    return best_peak, best_latest, best_decline


def _latest_min_value(
    observations: Sequence[GpuPriceObservation],
    getter: Any,
) -> float | None:
    if not observations:
        return None
    latest_date = max(item.observed_date for item in observations)
    values = [getter(item) for item in observations if item.observed_date == latest_date]
    return _min_optional(values)


def _rental_series_key(observation: GpuPriceObservation) -> tuple[str, str, str]:
    return (
        _normalize_key(observation.provider_or_marketplace or ""),
        _normalize_key(observation.region or ""),
        _normalize_key(observation.contract_term or ""),
    )


def _max_optional(values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _min_optional(values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return min(present) if present else None


def _normalize_generation(value: str) -> str:
    return value.strip().upper().replace(" ", "")


def _normalize_key(value: str) -> str:
    return value.strip().lower()


def _provenance(items: Sequence[Any]) -> list[Provenance]:
    return [item.provenance for item in items]
