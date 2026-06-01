"""
CashFlow model — time-series economics attached to Deals or Projects.

Used for DSCR, IRR, refinancing risk, and sensitivity analysis.
"""

from __future__ import annotations

import datetime as dt  # noqa: TC003 - Pydantic needs date available for runtime schema rebuilds.
from enum import StrEnum

from .base import BubbleBaseModel, NodeRef


class FlowType(StrEnum):
    CONTRACTED_REVENUE = "contracted_revenue"
    PROJECTED_REVENUE = "projected_revenue"
    DEBT_SERVICE = "debt_service"
    CAPEX = "capex"
    OPEX_POWER = "opex_power"
    OPEX_OTHER = "opex_other"
    INTEREST = "interest"
    PRINCIPAL_REPAYMENT = "principal_repayment"
    DIVIDEND = "dividend"
    GUARANTEE_PAYOUT = "guarantee_payout"


class CashFlow(BubbleBaseModel):
    """
    A single period cash flow (or projection).

    Multiple CashFlows roll up into a full project or entity model.
    """

    flow_type: FlowType
    period_start: dt.date
    period_end: dt.date
    amount_usd: float
    currency: str = "USD"

    source: str = "extracted"  # "contracted", "guidance", "inferred", "scenario"
    is_actual: bool = False

    linked_deal: NodeRef | None = None
    linked_entity: NodeRef | None = None
    linked_project: NodeRef | None = None

    # Sensitivity / scenario linkage
    sensitivity_to_utilization: float | None = None
    sensitivity_to_power_price: float | None = None
    sensitivity_to_interest_rate: float | None = None

    notes: str | None = None
