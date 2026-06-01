"""Compute economics models for GPU depreciation, TAM, payback, EPS, and supply risk."""

from __future__ import annotations

import datetime as dt  # noqa: TC003 - Pydantic needs date available for runtime schema rebuilds.

from pydantic import Field

from .base import BubbleBaseModel, EntityRef, NodeRef


class ComputeAsset(BubbleBaseModel):
    """A source-backed AI compute asset, cluster, or GPU purchase disclosure."""

    source_asset_id: str
    entity: EntityRef
    project_or_cluster_id: NodeRef | None = None
    gpu_generation: str
    gpu_count: int | None = Field(default=None, ge=0)
    purchase_date: dt.date | None = None
    capex_usd: float | None = Field(default=None, ge=0)
    original_price_per_gpu_usd: float | None = Field(default=None, ge=0)
    accounting_useful_life_years: float | None = Field(default=None, gt=0)
    modeled_economic_life_years: float | None = Field(default=None, gt=0)
    notes: str | None = None


class GpuPriceObservation(BubbleBaseModel):
    """A dated GPU price or rental-rate observation."""

    source_observation_id: str
    gpu_generation: str
    observed_date: dt.date
    observed_secondary_price_usd: float | None = Field(default=None, ge=0)
    observed_cloud_rental_rate_usd_per_hour: float | None = Field(default=None, ge=0)
    original_price_usd: float | None = Field(default=None, ge=0)
    peak_price_usd: float | None = Field(default=None, ge=0)
    provider_or_marketplace: str | None = None
    region: str | None = None
    contract_term: str | None = None


class DepreciationPolicy(BubbleBaseModel):
    """Disclosed accounting depreciation policy for compute or data center assets."""

    source_policy_id: str
    entity: EntityRef
    asset_class: str
    accounting_useful_life_years: float = Field(gt=0)
    depreciation_method: str | None = None
    effective_date: dt.date | None = None
    source_quote: str | None = None


class TamClaim(BubbleBaseModel):
    """A stated TAM claim and any source-backed realized revenue comparator."""

    source_claim_id: str
    entity: EntityRef
    claimed_market: str
    claim_date: dt.date | None = None
    stated_tam_usd: float = Field(ge=0)
    realized_revenue_usd: float | None = Field(default=None, ge=0)
    implied_revenue_capture_assumption_pct: float | None = Field(default=None, ge=0)
    source_quote: str | None = None


class CapexPaybackCase(BubbleBaseModel):
    """A deterministic payback case backed by source rows."""

    source_case_id: str
    entity: EntityRef
    project_or_cluster_id: NodeRef | None = None
    capex_usd: float = Field(ge=0)
    annual_revenue_run_rate_usd: float | None = Field(default=None, ge=0)
    contracted_revenue_usd: float | None = Field(default=None, ge=0)
    utilization_pct: float | None = Field(default=None, ge=0, le=100)
    gross_margin_pct: float | None = Field(default=None, ge=0, le=100)
    annual_power_cost_usd: float | None = Field(default=None, ge=0)
    annual_debt_service_usd: float | None = Field(default=None, ge=0)
    depreciation_life_years: float | None = Field(default=None, gt=0)
    notes: str | None = None


class EpsDepreciationImpact(BubbleBaseModel):
    """Inputs for accelerated depreciation impact on earnings per share."""

    source_impact_id: str
    entity: EntityRef
    fiscal_year: int
    annual_ai_capex_usd: float | None = Field(default=None, ge=0)
    data_center_capex_usd: float | None = Field(default=None, ge=0)
    gpu_capex_estimate_usd: float | None = Field(default=None, ge=0)
    disclosed_depreciation_usd: float | None = Field(default=None, ge=0)
    disclosed_net_income_impact_usd: float | None = Field(default=None, ge=0)
    disclosed_eps_impact_usd: float | None = None
    accounting_useful_life_years: float | None = Field(default=None, gt=0)
    modeled_economic_life_years: float | None = Field(default=None, gt=0)
    tax_rate_pct: float | None = Field(default=None, ge=0, le=100)
    diluted_shares: float | None = Field(default=None, gt=0)
    reported_eps: float | None = None
    impact_direction: str | None = None
    source_quote: str | None = None


class ChipSupplyObservation(BubbleBaseModel):
    """A source-backed observation of announced versus delivered GPU supply."""

    source_observation_id: str
    entity: EntityRef
    project_or_cluster_id: NodeRef | None = None
    gpu_generation: str
    announced_gpu_count: int | None = Field(default=None, ge=0)
    delivered_gpu_count: int | None = Field(default=None, ge=0)
    announced_mw: float | None = Field(default=None, ge=0)
    disclosed_purchase_commitment_usd: float | None = Field(default=None, ge=0)
    supplier: str | None = None
    delivery_window: str | None = None
    observed_deployment_date: dt.date | None = None
    source_quote: str | None = None
