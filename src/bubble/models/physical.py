"""
PhysicalAsset model — the real-world infrastructure.

This is where announced capacity meets satellite, permits, and equipment reality.
"""

from __future__ import annotations

import datetime as dt  # noqa: TC003 - Pydantic needs date available for runtime schema rebuilds.
from enum import StrEnum
from typing import Any

from pydantic import Field

from .base import BubbleBaseModel, EntityRef


class AssetType(StrEnum):
    DATA_CENTER_CAMPUS = "data_center_campus"
    DATA_CENTER_BUILDING = "data_center_building"
    POWER_GENERATION = "power_generation"
    GAS_TURBINE_ARRAY = "gas_turbine_array"
    SUBSTATION = "substation"
    TRANSMISSION_LINE = "transmission_line"
    COOLING_FACILITY = "cooling_facility"
    LAND_PARCEL = "land_parcel"
    NUCLEAR_SMR = "nuclear_smr"


class ConstructionStatus(StrEnum):
    ANNOUNCED = "announced"
    PERMITTED = "permitted"
    UNDER_CONSTRUCTION = "under_construction"
    MECHANICAL_COMPLETION = "mechanical_completion"
    IN_SERVICE = "in_service"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


class GridRegion(StrEnum):
    ERCOT = "ercot"
    PJM = "pjm"
    MISO = "miso"
    CAISO = "caiso"
    NYISO = "nyiso"
    SPP = "spp"
    ISO_NE = "iso_ne"
    WECC = "wecc"
    OTHER = "other"
    UNKNOWN = "unknown"


class InterconnectionStatus(StrEnum):
    NOT_SUBMITTED = "not_submitted"
    REQUESTED = "requested"
    STUDY = "study"
    FACILITY_STUDY = "facility_study"
    AGREEMENT_PENDING = "agreement_pending"
    AGREEMENT_EXECUTED = "agreement_executed"
    IN_SERVICE = "in_service"
    DELAYED = "delayed"
    WITHDRAWN = "withdrawn"
    UNKNOWN = "unknown"


class PermitDecisionStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    NOT_FOUND = "not_found"
    APPLIED = "applied"
    DRAFT = "draft"
    ISSUED = "issued"
    CONTESTED = "contested"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    UNKNOWN = "unknown"


class EquipmentType(StrEnum):
    TRANSFORMER = "transformer"
    GAS_TURBINE = "gas_turbine"
    SWITCHGEAR = "switchgear"
    COOLING = "cooling"
    GENERATOR = "generator"
    OTHER = "other"


class EquipmentStatus(StrEnum):
    NOT_ORDERED = "not_ordered"
    ORDERED = "ordered"
    ALLOCATED = "allocated"
    DELAYED = "delayed"
    DELIVERED = "delivered"
    INSTALLED = "installed"
    UNKNOWN = "unknown"


class PhysicalRiskLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class PhysicalAsset(BubbleBaseModel):
    """
    A physical piece of infrastructure with location and status.

    Cross-referenced against Deals (who owns/leases it) and Entities.
    Later: satellite-derived updates to capacity and construction progress.
    """

    name: str
    asset_type: AssetType
    source_project_id: str | None = None
    location_lat: float | None = None
    location_lon: float | None = None
    address: str | None = None
    jurisdiction: str | None = None  # county/state for permit lookups

    capacity_mw: float | None = None
    it_load_mw: float | None = None  # critical for data centers

    owner: EntityRef | None = None
    operator: EntityRef | None = None
    tenants: list[EntityRef] = Field(default_factory=list)

    permit_status: str | None = None
    construction_status: ConstructionStatus = ConstructionStatus.ANNOUNCED
    announced_in_service_date: str | None = None
    actual_in_service_date: str | None = None

    # Equipment reality (transformers, turbines, switchgear)
    major_equipment: dict[str, Any] = Field(default_factory=dict)
    equipment_lead_time_months: int | None = None

    # Link back to financial layer
    linked_deals: list[EntityRef] = Field(default_factory=list)

    # Satellite / CV derived (Phase 5+)
    satellite_last_observed: str | None = None
    visible_building_footprint_m2: float | None = None
    visible_cooling_towers: int | None = None
    visible_turbines: int | None = None


class InterconnectionQueueItem(BubbleBaseModel):
    """Source-backed grid queue or large-load interconnection record."""

    project_ref: EntityRef | None = None
    queue_id: str
    region: GridRegion = GridRegion.UNKNOWN
    status: InterconnectionStatus = InterconnectionStatus.UNKNOWN
    requested_mw: float | None = None
    firm_service_mw: float | None = None
    requested_in_service_date: dt.date | None = None
    expected_in_service_date: dt.date | None = None
    delay_months: int | None = None
    network_upgrade_cost_usd: float | None = None
    study_phase: str | None = None
    notes: str | None = None

    def has_firm_power(self, required_mw: float | None = None) -> bool:
        if self.status in {
            InterconnectionStatus.AGREEMENT_EXECUTED,
            InterconnectionStatus.IN_SERVICE,
        }:
            if required_mw is None or self.firm_service_mw is None:
                return True
            return self.firm_service_mw >= required_mw * 0.8
        return False


class PermitRecord(BubbleBaseModel):
    """Source-backed permit record for power, air, zoning, or construction."""

    project_ref: EntityRef | None = None
    permit_id: str
    authority: str
    permit_type: str
    status: PermitDecisionStatus = PermitDecisionStatus.UNKNOWN
    application_date: dt.date | None = None
    issued_date: dt.date | None = None
    capacity_mw: float | None = None
    related_generation: bool = False
    public_opposition: bool = False
    notes: str | None = None


class EquipmentRecord(BubbleBaseModel):
    """Source-backed long-lead equipment status record."""

    project_ref: EntityRef | None = None
    equipment_type: EquipmentType
    status: EquipmentStatus = EquipmentStatus.UNKNOWN
    vendor: str | None = None
    capacity_mw: float | None = None
    ordered_date: dt.date | None = None
    expected_delivery_date: dt.date | None = None
    actual_delivery_date: dt.date | None = None
    lead_time_months: int | None = None
    notes: str | None = None


class ConstructionObservation(BubbleBaseModel):
    """Observed physical progress from satellite, local filings, or site records."""

    project_ref: EntityRef | None = None
    observed_on: dt.date
    construction_status: ConstructionStatus
    progress_pct: float | None = Field(default=None, ge=0.0, le=1.0)
    visible_indicators: list[str] = Field(default_factory=list)
    notes: str | None = None


class PhysicalRiskAssessment(BubbleBaseModel):
    """Deterministic physical deliverability risk score for a project or campus."""

    project_ref: EntityRef | None = None
    asset_ref: EntityRef | None = None
    score: float = Field(ge=0.0, le=1.0)
    risk_level: PhysicalRiskLevel
    components: dict[str, float] = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    expected_delay_months: int | None = None
    evidence_tier: str
    evidence_source_count: int
    evidence_source_types: list[str] = Field(default_factory=list)
    high_confidence_eligible: bool = False
    supporting_evidence: list[str] = Field(default_factory=list)
    methodology_version: str = "physical-risk-v1"
    attributes: dict[str, Any] = Field(default_factory=dict)
