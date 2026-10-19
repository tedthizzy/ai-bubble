"""Dated operating and financing facts for one explicitly identified facility."""

from __future__ import annotations

import datetime as dt  # noqa: TC003 - Pydantic resolves these annotations at runtime.
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FacilityFact(BaseModel):
    """A quoted source value; forecasts retain their original measurement basis."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    value: float | str
    unit: str
    source_id: str
    quote: str
    kind: Literal["reported", "contractual", "issuer_forecast"] = "reported"
    observed_on: dt.date
    period: str | None = None
    # Numeric source token and multiplier make billion/thousand conversions auditable.
    source_token: str | None = None
    multiplier: float = 1

    @field_validator("value", mode="before")
    @classmethod
    def finite_value(cls, value: object) -> object:
        if isinstance(value, bool) or (
            isinstance(value, (int, float)) and not math.isfinite(value)
        ):
            raise ValueError("Facility values must be finite numbers or source text")
        return value


class FacilityPrincipalPayment(BaseModel):
    """One dated contractual installment from a primary payment table."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    due_on: dt.date
    amount: FacilityFact


class FacilityDebt(BaseModel):
    """An instrument linked by the source to this site, without parent-debt allocation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    borrower: str
    facts: dict[str, FacilityFact]
    amortization: Literal["bullet", "scheduled", "not_disclosed"] = "not_disclosed"
    loss_route: list[FacilityFact] = Field(default_factory=list)
    principal_payments: list[FacilityPrincipalPayment] = Field(default_factory=list)

    def evidence(self) -> list[FacilityFact]:
        return [
            *self.facts.values(),
            *self.loss_route,
            *(payment.amount for payment in self.principal_payments),
        ]

    @model_validator(mode="after")
    def ordered_principal_payments(self) -> FacilityDebt:
        dates = [payment.due_on for payment in self.principal_payments]
        if dates != sorted(set(dates)):
            raise ValueError("Principal payments must have unique ascending dates")
        if any(
            payment.amount.unit != "USD"
            or not isinstance(payment.amount.value, float)
            or payment.amount.value < 0
            for payment in self.principal_payments
        ):
            raise ValueError("Principal installments must be nonnegative USD amounts")
        return self


class FacilityCase(BaseModel):
    """Keep the landlord's shell cash flows separate from a tenant's GPU economics."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    entity: str
    ticker: str
    project: str
    scope: Literal["facility", "site_portfolio", "contract_portfolio"] = "facility"
    role: Literal["colocation_landlord", "compute_operator", "infrastructure_operator"]
    counterparties: list[str]
    facts: dict[str, FacilityFact]
    debts: list[FacilityDebt] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    def evidence(self) -> list[FacilityFact]:
        return [*self.facts.values(), *(fact for debt in self.debts for fact in debt.evidence())]

    @model_validator(mode="after")
    def distinct_instruments(self) -> FacilityCase:
        if len({debt.id for debt in self.debts}) != len(self.debts):
            raise ValueError("An instrument must occur only once within a facility")
        return self
