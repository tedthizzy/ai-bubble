"""CSV loader for source-backed compute economics evidence."""

from __future__ import annotations

import csv
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from bubble.analysis.compute_economics import ComputeEconomicsBatch, empty_compute_economics_batch
from bubble.models.base import HumanReviewStatus, Provenance, SourceType
from bubble.models.compute import (
    CapexPaybackCase,
    ChipSupplyObservation,
    ComputeAsset,
    DepreciationPolicy,
    EpsDepreciationImpact,
    GpuPriceObservation,
    TamClaim,
)
from bubble.quality.source_invariants import assert_source_row

if TYPE_CHECKING:
    from collections.abc import Sequence


def load_compute_economics(directory: str | Path) -> ComputeEconomicsBatch:
    """Load source-backed compute economics CSVs from a directory."""

    base = Path(directory)
    if not base.exists():
        return empty_compute_economics_batch()
    return ComputeEconomicsBatch(
        assets=[_asset_from_row(row) for row in _read_csv(base / "compute_assets.csv")],
        gpu_price_observations=[
            _gpu_price_observation_from_row(row)
            for row in _read_csv(base / "gpu_price_observations.csv")
        ],
        depreciation_policies=[
            _depreciation_policy_from_row(row)
            for row in _read_csv(base / "depreciation_policies.csv")
        ],
        tam_claims=[_tam_claim_from_row(row) for row in _read_csv(base / "tam_claims.csv")],
        payback_cases=[
            _payback_case_from_row(row) for row in _read_csv(base / "capex_payback_cases.csv")
        ],
        eps_impacts=[
            _eps_impact_from_row(row) for row in _read_csv(base / "eps_depreciation_impacts.csv")
        ],
        chip_supply_observations=[
            _chip_supply_observation_from_row(row)
            for row in _read_csv(base / "chip_supply_observations.csv")
        ],
    )


def merge_compute_economics_batches(
    batches: Sequence[ComputeEconomicsBatch],
) -> ComputeEconomicsBatch:
    """Merge batches from multiple data directories."""

    return ComputeEconomicsBatch(
        assets=[item for batch in batches for item in batch.assets],
        gpu_price_observations=[item for batch in batches for item in batch.gpu_price_observations],
        depreciation_policies=[item for batch in batches for item in batch.depreciation_policies],
        tam_claims=[item for batch in batches for item in batch.tam_claims],
        payback_cases=[item for batch in batches for item in batch.payback_cases],
        eps_impacts=[item for batch in batches for item in batch.eps_impacts],
        chip_supply_observations=[
            item for batch in batches for item in batch.chip_supply_observations
        ],
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return [
            {key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(f)
        ]


def _asset_from_row(row: dict[str, str]) -> ComputeAsset:
    asset_id = _required(row, "asset_id")
    return ComputeAsset(
        source_asset_id=asset_id,
        entity=_required(row, "entity"),
        project_or_cluster_id=_optional_str(row.get("project_or_cluster_id")),
        gpu_generation=_required(row, "gpu_generation"),
        gpu_count=_optional_int(row.get("gpu_count")),
        purchase_date=_optional_date(row.get("purchase_date")),
        capex_usd=_optional_float(row.get("capex_usd")),
        original_price_per_gpu_usd=_optional_float(row.get("original_price_per_gpu_usd")),
        accounting_useful_life_years=_optional_float(row.get("accounting_useful_life_years")),
        modeled_economic_life_years=_optional_float(row.get("modeled_economic_life_years")),
        notes=_optional_str(row.get("notes")),
        provenance=_provenance_from_row(row, context=f"compute_asset:{asset_id}"),
        confidence=_optional_float(row.get("confidence")) or 0.85,
    )


def _gpu_price_observation_from_row(row: dict[str, str]) -> GpuPriceObservation:
    observation_id = _required(row, "observation_id")
    return GpuPriceObservation(
        source_observation_id=observation_id,
        gpu_generation=_required(row, "gpu_generation"),
        observed_date=_required_date(row, "observed_date"),
        observed_secondary_price_usd=_optional_float(row.get("observed_secondary_price_usd")),
        observed_cloud_rental_rate_usd_per_hour=_optional_float(
            row.get("observed_cloud_rental_rate_usd_per_hour")
        ),
        original_price_usd=_optional_float(row.get("original_price_usd")),
        peak_price_usd=_optional_float(row.get("peak_price_usd")),
        provider_or_marketplace=_optional_str(row.get("provider_or_marketplace")),
        region=_optional_str(row.get("region")),
        contract_term=_optional_str(row.get("contract_term")),
        provenance=_provenance_from_row(row, context=f"gpu_price:{observation_id}"),
        confidence=_optional_float(row.get("confidence")) or 0.85,
    )


def _depreciation_policy_from_row(row: dict[str, str]) -> DepreciationPolicy:
    policy_id = _required(row, "policy_id")
    return DepreciationPolicy(
        source_policy_id=policy_id,
        entity=_required(row, "entity"),
        asset_class=_required(row, "asset_class"),
        accounting_useful_life_years=_required_float(row, "accounting_useful_life_years"),
        depreciation_method=_optional_str(row.get("depreciation_method")),
        effective_date=_optional_date(row.get("effective_date")),
        source_quote=_optional_str(row.get("source_quote")),
        provenance=_provenance_from_row(row, context=f"depreciation_policy:{policy_id}"),
        confidence=_optional_float(row.get("confidence")) or 0.85,
    )


def _tam_claim_from_row(row: dict[str, str]) -> TamClaim:
    claim_id = _required(row, "claim_id")
    return TamClaim(
        source_claim_id=claim_id,
        entity=_required(row, "entity"),
        claimed_market=_required(row, "claimed_market"),
        claim_date=_optional_date(row.get("claim_date")),
        stated_tam_usd=_required_float(row, "stated_tam_usd"),
        realized_revenue_usd=_optional_float(row.get("realized_revenue_usd")),
        implied_revenue_capture_assumption_pct=_optional_float(
            row.get("implied_revenue_capture_assumption_pct")
        ),
        source_quote=_optional_str(row.get("source_quote")),
        provenance=_provenance_from_row(row, context=f"tam_claim:{claim_id}"),
        confidence=_optional_float(row.get("confidence")) or 0.85,
    )


def _payback_case_from_row(row: dict[str, str]) -> CapexPaybackCase:
    case_id = _required(row, "case_id")
    return CapexPaybackCase(
        source_case_id=case_id,
        entity=_required(row, "entity"),
        project_or_cluster_id=_optional_str(row.get("project_or_cluster_id")),
        capex_usd=_required_float(row, "capex_usd"),
        annual_revenue_run_rate_usd=_optional_float(row.get("annual_revenue_run_rate_usd")),
        contracted_revenue_usd=_optional_float(row.get("contracted_revenue_usd")),
        utilization_pct=_optional_float(row.get("utilization_pct")),
        gross_margin_pct=_optional_float(row.get("gross_margin_pct")),
        annual_power_cost_usd=_optional_float(row.get("annual_power_cost_usd")),
        annual_debt_service_usd=_optional_float(row.get("annual_debt_service_usd")),
        depreciation_life_years=_optional_float(row.get("depreciation_life_years")),
        notes=_optional_str(row.get("notes")),
        provenance=_provenance_from_row(row, context=f"capex_payback:{case_id}"),
        confidence=_optional_float(row.get("confidence")) or 0.85,
    )


def _eps_impact_from_row(row: dict[str, str]) -> EpsDepreciationImpact:
    impact_id = _required(row, "impact_id")
    return EpsDepreciationImpact(
        source_impact_id=impact_id,
        entity=_required(row, "entity"),
        fiscal_year=_required_int(row, "fiscal_year"),
        annual_ai_capex_usd=_optional_float(row.get("annual_ai_capex_usd")),
        data_center_capex_usd=_optional_float(row.get("data_center_capex_usd")),
        gpu_capex_estimate_usd=_optional_float(row.get("gpu_capex_estimate_usd")),
        disclosed_depreciation_usd=_optional_float(row.get("disclosed_depreciation_usd")),
        disclosed_net_income_impact_usd=_optional_float(row.get("disclosed_net_income_impact_usd")),
        disclosed_eps_impact_usd=_optional_float(row.get("disclosed_eps_impact_usd")),
        accounting_useful_life_years=_optional_float(row.get("accounting_useful_life_years")),
        modeled_economic_life_years=_optional_float(row.get("modeled_economic_life_years")),
        tax_rate_pct=_optional_float(row.get("tax_rate_pct")),
        diluted_shares=_optional_float(row.get("diluted_shares")),
        reported_eps=_optional_float(row.get("reported_eps")),
        impact_direction=_optional_str(row.get("impact_direction")),
        source_quote=_optional_str(row.get("source_quote")),
        provenance=_provenance_from_row(row, context=f"eps_impact:{impact_id}"),
        confidence=_optional_float(row.get("confidence")) or 0.85,
    )


def _chip_supply_observation_from_row(row: dict[str, str]) -> ChipSupplyObservation:
    observation_id = _required(row, "observation_id")
    return ChipSupplyObservation(
        source_observation_id=observation_id,
        entity=_required(row, "entity"),
        project_or_cluster_id=_optional_str(row.get("project_or_cluster_id")),
        gpu_generation=_required(row, "gpu_generation"),
        announced_gpu_count=_optional_int(row.get("announced_gpu_count")),
        delivered_gpu_count=_optional_int(row.get("delivered_gpu_count")),
        announced_mw=_optional_float(row.get("announced_mw")),
        disclosed_purchase_commitment_usd=_optional_float(
            row.get("disclosed_purchase_commitment_usd")
        ),
        supplier=_optional_str(row.get("supplier")),
        delivery_window=_optional_str(row.get("delivery_window")),
        observed_deployment_date=_optional_date(row.get("observed_deployment_date")),
        source_quote=_optional_str(row.get("source_quote")),
        provenance=_provenance_from_row(row, context=f"chip_supply:{observation_id}"),
        confidence=_optional_float(row.get("confidence")) or 0.85,
    )


def _provenance_from_row(row: dict[str, str], *, context: str) -> Provenance:
    assert_source_row(row, context=context)
    return Provenance(
        source_uri=_required(row, "source_uri"),
        source_type=_enum_value(SourceType, row.get("source_type"), SourceType.SEC_EDGAR),
        retrieved_at=_required_datetime(row, "retrieved_at"),
        page_or_section=_optional_str(row.get("page_or_section")),
        confidence=_optional_float(row.get("source_confidence")) or 0.85,
        human_review_status=_enum_value(
            HumanReviewStatus,
            row.get("human_review_status"),
            HumanReviewStatus.PENDING,
        ),
        content_hash=_required(row, "content_hash"),
    )


def _required(row: dict[str, str], key: str) -> str:
    value = row.get(key)
    if not value:
        raise ValueError(f"CSV row missing required field: {key}")
    return value


def _required_float(row: dict[str, str], key: str) -> float:
    value = _optional_float(row.get(key))
    if value is None:
        raise ValueError(f"CSV row missing required numeric field: {key}")
    return value


def _required_int(row: dict[str, str], key: str) -> int:
    value = _optional_int(row.get(key))
    if value is None:
        raise ValueError(f"CSV row missing required integer field: {key}")
    return value


def _required_date(row: dict[str, str], key: str) -> date:
    value = _optional_date(row.get(key))
    if value is None:
        raise ValueError(f"CSV row missing required date field: {key}")
    return value


def _required_datetime(row: dict[str, str], key: str) -> datetime:
    raw = _required(row, key)
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _optional_str(value: str | None) -> str | None:
    return value if value else None


def _optional_float(value: str | None) -> float | None:
    if not value:
        return None
    return float(value.replace(",", "").replace("$", ""))


def _optional_int(value: str | None) -> int | None:
    parsed = _optional_float(value)
    return int(parsed) if parsed is not None else None


def _optional_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def _enum_value[EnumT: StrEnum](enum_cls: type[EnumT], value: str | None, default: EnumT) -> EnumT:
    if not value:
        return default
    normalized = value.strip().lower()
    try:
        return enum_cls(normalized)
    except ValueError:
        by_name = enum_cls.__members__.get(value.strip().upper())
        if by_name is not None:
            return by_name
        return default
