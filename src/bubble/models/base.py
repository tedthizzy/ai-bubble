"""
Core domain primitives for bubble.

Provenance is attached to EVERY scalar, node, relationship, and inference.
This is the non-negotiable foundation of forensic rigor.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceType(StrEnum):
    """Primary source categories (expand as new layers come online)."""

    SEC_EDGAR = "sec_edgar"
    PR_NEWSWIRE = "pr_newswire"
    BUSINESS_WIRE = "business_wire"
    EARNINGS_TRANSCRIPT = "earnings_transcript"
    COMPANY_IR = "company_ir"
    PROJECT_TRACKER = "project_tracker"  # cleanview, SemiAnalysis, etc.
    FERC = "ferc"
    EIA = "eia"
    EPA = "epa"
    GLEIF = "gleif"
    STATE_PUC = "state_puc"
    STATE_DEQ = "state_deq"  # air permits
    LOCAL_PLANNING = "local_planning"
    GRID_QUEUE = "grid_interconnection_queue"
    SATELLITE = "satellite"
    FOIA = "foia"
    MANUAL_CURATED = "manual_curated"
    INFERRED = "inferred"


class HumanReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    OVERRIDDEN = "overridden"
    REJECTED = "rejected"


class Provenance(BaseModel):
    """
    Immutable lineage record attached to every piece of data.

    This is what allows a human analyst (or future automated auditor)
    to trace any conclusion back to its exact source, prompt, model, and time.
    """

    model_config = ConfigDict(frozen=True)

    source_uri: str
    source_type: SourceType
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    page_or_section: str | None = None
    model_id: str | None = None  # e.g. "claude-4-sonnet-20250514"
    prompt_hash: str | None = None  # sha256 of the exact prompt template + version
    rule_id: str | None = None  # for deterministic red-flag rules
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    human_review_status: HumanReviewStatus = HumanReviewStatus.PENDING
    human_notes: str | None = None
    content_hash: str  # sha256 of the raw evidence (text, table, image hash, etc.)

    @field_validator("confidence")
    @classmethod
    def confidence_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        return v

    @staticmethod
    def compute_content_hash(data: bytes | str) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.sha256(data).hexdigest()


class BubbleBaseModel(BaseModel):
    """
    All bubble domain models inherit from this.

    - Frozen after creation where possible (immutability for audit)
    - Strict extra = 'forbid' (no silent data loss)
    - Every instance carries provenance
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        frozen=False,  # allow human overrides to mutate review status etc.
        populate_by_name=True,
    )

    id: UUID = Field(default_factory=uuid4)
    provenance: Provenance
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)

    def with_human_override(
        self,
        new_confidence: float | None = None,
        notes: str | None = None,
        status: HumanReviewStatus = HumanReviewStatus.OVERRIDDEN,
    ) -> BubbleBaseModel:
        """Return a copy with human review fields updated (immutable style)."""
        new_prov = self.provenance.model_copy(
            update={
                "human_review_status": status,
                "human_notes": notes or self.provenance.human_notes,
                "confidence": new_confidence or self.provenance.confidence,
            }
        )
        # Pydantic v2 way to create updated frozen-ish copy
        return self.model_copy(
            update={"provenance": new_prov, "confidence": new_confidence or self.confidence}
        )


# Type aliases used across models
EntityRef = Annotated[str, "Stable reference to an Entity (UUID or normalized name + type)"]
DealRef = Annotated[str, "Stable reference to a Deal"]
NodeRef = EntityRef | DealRef | str


class EntityType(StrEnum):
    HYPERSCALER = "hyperscaler"
    AI_PUREPLAY = "ai_pureplay"
    CLOUD_PROVIDER = "cloud_provider"
    DATA_CENTER_REIT = "data_center_reit"
    AI_INFRA_PUREPLAY = "ai_infra_pureplay"  # CoreWeave, Vantage, etc.
    FINANCIER = "financier"  # Apollo, Blackstone, etc.
    PRIVATE_CREDIT = "private_credit"
    SPV = "spv"
    PROJECT = "project"
    UTILITY = "utility"
    POWER_GENERATOR = "power_generator"
    EQUIPMENT_SUPPLIER = "equipment_supplier"  # turbines, transformers
    GOVERNMENT = "government"
    UNKNOWN = "unknown"


class DealType(StrEnum):
    LEASE = "lease"
    DEBT_FACILITY = "debt_facility"
    BOND = "bond"
    PPA = "ppa"  # power purchase agreement
    LAND_ACQUISITION = "land_acquisition"
    CONSTRUCTION_CONTRACT = "construction_contract"
    PREFERRED_EQUITY = "preferred_equity"
    COMMON_EQUITY = "common_equity"
    GUARANTEE = "guarantee"
    INTERCONNECTION_AGREEMENT = "interconnection_agreement"
    OTHER = "other"


class RiskCategory(StrEnum):
    UTILIZATION = "utilization"
    POWER_AVAILABILITY = "power_availability"
    GPU_DEPRECIATION = "gpu_depreciation"
    REFINANCING = "refinancing"
    INTEREST_RATE = "interest_rate"
    REGULATORY = "regulatory"
    PERMIT_DELAY = "permit_delay"
    EQUIPMENT_BOTTLENECK = "equipment_bottleneck"
    CONCENTRATION = "concentration"
    RELATED_PARTY = "related_party"
    OFF_BALANCE_SHEET = "off_balance_sheet"
    COUNTERPARTY = "counterparty"
    PHYSICAL_CONSTRAINT = "physical_constraint"
    TAIL_RISK = "tail_risk"
