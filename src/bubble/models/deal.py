"""
Deal model — the central relationship and cash-flow vehicle in the ecosystem.

Every lease, debt facility, PPA, land deal, construction contract, etc. is a Deal.
Deals connect Entities and generate CashFlows, Risks, and Assumptions.
"""

from __future__ import annotations

import datetime as dt  # noqa: TC003 - Pydantic needs date available for runtime schema rebuilds.
from typing import Any

from pydantic import Field

from .base import BubbleBaseModel, DealType, EntityRef


class DebtTranche(BubbleBaseModel):
    """A single tranche within a larger debt facility (senior, mezz, etc.)."""

    name: str
    seniority: int = 1  # 1 = most senior
    notional_usd: float
    interest_rate: float | None = None
    maturity: dt.date | None = None
    recourse: bool = False
    collateral_description: str | None = None
    guarantors: list[EntityRef] = Field(default_factory=list)


class Deal(BubbleBaseModel):
    """
    A contractual or economic arrangement between parties.

    This is deliberately rich because the majority of Burry-style insights live here:
    - Who is on the hook if utilization misses?
    - Is the debt recourse or non-recourse to the parent?
    - What are the hidden guarantees or related-party terms?
    """

    deal_type: DealType
    source_deal_id: str | None = None
    title: str | None = None

    # Parties (roles are explicit)
    parties: list[EntityRef] = Field(..., min_length=1)
    counterparty_roles: dict[str, list[EntityRef]] = Field(default_factory=dict)
    # Example: {"lessor": [...], "lessee": [...], "lender": [...], "guarantor": [...] }

    # Timing
    announced_date: dt.date | None = None
    effective_date: dt.date | None = None
    maturity_date: dt.date | None = None

    # Economics (always in USD for simplicity; store original + fx if needed)
    notional_amount_usd: float | None = None
    currency: str = "USD"

    # Debt-specific richness (populated for DEBT_FACILITY / BOND)
    debt_tranches: list[DebtTranche] = Field(default_factory=list)
    is_non_recourse: bool | None = None
    bankruptcy_remote_spv: bool | None = None

    # Key terms (free but structured — LLM extracts these into consistent keys)
    key_terms: dict[str, Any] = Field(default_factory=dict)
    # Common keys we aim for: "utilization_requirement", "take_or_pay", "escalator",
    # "prepayment_penalty", "change_of_control", "gpu_depreciation_assumption", etc.

    collateral: list[str] = Field(default_factory=list)
    guarantees: list[EntityRef] = Field(default_factory=list)

    # Linkages to other nodes
    linked_projects: list[EntityRef] = Field(default_factory=list)  # Physical sites
    linked_assets: list[EntityRef] = Field(default_factory=list)

    # Flags for rapid querying
    is_related_party: bool = False
    concentration_risk_flag: bool = False  # >35% of revenue from one tenant, etc.

    def primary_counterparty(self) -> EntityRef | None:
        """Heuristic for the most important other party."""
        for role in ("lessee", "borrower", "counterparty"):
            if entities := self.counterparty_roles.get(role):
                return entities[0]
        return self.parties[0] if self.parties else None

    def __str__(self) -> str:
        return f"Deal({self.deal_type}, parties={len(self.parties)}, notional={self.notional_amount_usd})"
