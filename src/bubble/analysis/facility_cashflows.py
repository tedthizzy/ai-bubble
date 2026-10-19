"""Connect dated site, contract and debt facts without inventing missing cash flows.

Contract averages are arithmetic over the base term, not a payment schedule.
Coupon coverage excludes principal and costs; it is never labeled DSCR.
Debt-service coverage requires explicit cash available and complete debt service.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bubble.models.facility import FacilityCase, FacilityDebt, FacilityFact


def _number(facts: dict[str, FacilityFact], key: str) -> float | None:
    fact = facts.get(key)
    return float(fact.value) if fact is not None and isinstance(fact.value, (int, float)) else None


def _text(facts: dict[str, FacilityFact], key: str) -> str | None:
    fact = facts.get(key)
    return str(fact.value) if fact is not None else None


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    return (
        numerator / denominator
        if numerator is not None and denominator and denominator > 0
        else None
    )


def _contract_date(facts: dict[str, FacilityFact], key: str) -> date:
    value = _text(facts, key)
    if value is None:
        raise ValueError(f"Fixed-rate payment schedule lacks {key}")
    try:
        return date.fromisoformat(value)
    except ValueError:
        return datetime.strptime(value, "%B %d, %Y").date()


def fixed_rate_payments(debt: FacilityDebt) -> list[dict[str, Any]]:
    """Original contractual schedule; no optional prepayments or additional issuance.

    Applies only with a complete dated principal table and explicit 30/360 terms.
    The first coupon accrues from issuance, including an irregular initial period.
    """
    if not debt.principal_payments:
        return []
    facts = debt.facts
    face = _number(facts, "original_principal_usd")
    rate = _number(facts, "coupon_pct")
    if face is None or rate is None or _text(facts, "interest_day_count") != "30/360":
        raise ValueError("A dated principal table needs original face, fixed coupon and day count")
    original = Decimal(str(face))
    total = sum(Decimal(str(payment.amount.value)) for payment in debt.principal_payments)
    maturity = _contract_date(facts, "maturity")
    if total != original or debt.principal_payments[-1].due_on != maturity:
        raise ValueError("Principal table does not repay original face at stated maturity")
    previous = _contract_date(facts, "issue_date")
    due = _contract_date(facts, "first_interest_payment")
    if due <= previous:
        raise ValueError("First interest payment must follow issuance")
    payments = {
        payment.due_on: Decimal(str(payment.amount.value)) for payment in debt.principal_payments
    }
    balance = original
    result = []
    while due <= maturity:
        start_day = min(previous.day, 30)
        end_day = min(due.day, 30) if start_day == 30 else due.day
        days = (
            (due.year - previous.year) * 360
            + (due.month - previous.month) * 30
            + end_day
            - start_day
        )
        interest = (balance * Decimal(str(rate)) / 100 * Decimal(days) / 360).quantize(
            Decimal("0.01")
        )
        principal = payments.pop(due, Decimal(0))
        balance -= principal
        result.append(
            {
                "due_on": due.isoformat(),
                "principal_usd": float(principal),
                "interest_usd": float(interest),
                "debt_service_usd": float(principal + interest),
                "remaining_principal_usd": float(balance),
            }
        )
        previous = due
        month = due.month + 6
        due = date(due.year + (month - 1) // 12, (month - 1) % 12 + 1, due.day)
    if payments or balance != 0:
        raise ValueError("Principal installments do not align with the coupon calendar")
    return result


def _instrument(debt: FacilityDebt) -> dict[str, Any]:
    facts = debt.facts
    principal = _number(facts, "principal_usd")
    coupon = _number(facts, "coupon_pct")
    # A reported effective rate can include noncash financing-cost amortization.
    # Keep it as evidence; do not substitute it for a contractual cash coupon.
    interest = principal * coupon / 100 if principal is not None and coupon is not None else None
    # A contractual spread alone is insufficient to infer a floating-rate payment.
    service = _number(facts, "annual_debt_service_usd")
    amortization = _number(facts, "annual_principal_usd")
    period_interest = _number(facts, "annual_interest_usd")
    interest_period = facts["annual_interest_usd"].period if period_interest is not None else None
    principal_period = facts["annual_principal_usd"].period if amortization is not None else None
    if (
        service is None
        and period_interest is not None
        and amortization is not None
        and interest_period
        and interest_period == principal_period
    ):
        service = period_interest + amortization
    period_fact = facts.get("annual_debt_service_usd") or facts.get("annual_principal_usd")
    schedule = fixed_rate_payments(debt)
    return {
        "id": debt.id,
        "borrower": debt.borrower,
        "principal_usd": principal,
        "principal_as_of": facts["principal_usd"].observed_on.isoformat()
        if principal is not None
        else None,
        "commitment_usd": _number(facts, "commitment_usd"),
        "annual_interest_run_rate_usd": interest,
        "annual_debt_service_usd": service,
        "maturity": _text(facts, "maturity"),
        "amortization": debt.amortization,
        "annual_payment_total_complete": service is not None,
        "original_contractual_schedule_complete": bool(schedule),
        "scheduled_cash_payments": schedule,
        "schedule_assumption": "Original indenture terms; no optional redemptions, additional notes or payment-schedule amendments"
        if schedule
        else None,
        "principal_payments": [
            payment.model_dump(mode="json") for payment in debt.principal_payments
        ],
        "service_period": period_fact.period if period_fact is not None else None,
        "loss_route": [fact.model_dump(mode="json") for fact in debt.loss_route],
        "facts": {key: fact.model_dump(mode="json") for key, fact in facts.items()},
    }


def _annualize_payments(instruments: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    yearly: dict[str, dict[str, Any]] = {}
    for instrument in instruments:
        for payment in instrument["scheduled_cash_payments"]:
            year = payment["due_on"][:4]
            annual = yearly.setdefault(
                year,
                {"year": year, "principal_usd": 0.0, "interest_usd": 0.0, "debt_service_usd": 0.0},
            )
            for key in ("principal_usd", "interest_usd", "debt_service_usd"):
                annual[key] += payment[key]
    return dict(sorted(yearly.items()))


def analyze_facility(case: FacilityCase, as_of: date) -> dict[str, Any]:  # noqa: PLR0912
    """Derive only ratios supported at the same facility and measurement scope."""
    if any(fact.observed_on > as_of for fact in case.evidence()):
        raise ValueError(f"Facility evidence postdates cutoff: {case.id}")
    facts = case.facts
    revenue = _number(facts, "annual_revenue_usd")
    total = _number(facts, "base_contract_value_usd")
    years = _number(facts, "base_contract_years")
    average = total / years if total is not None and years and years > 0 else None
    noi = _number(facts, "annual_noi_usd")
    cfads = _number(facts, "annual_cfads_usd")
    instruments = [_instrument(debt) for debt in case.debts]
    coupons_complete = bool(instruments) and all(
        debt["annual_interest_run_rate_usd"] is not None for debt in instruments
    )
    services_complete = bool(instruments) and all(
        debt["annual_debt_service_usd"] is not None for debt in instruments
    )
    original_schedule_complete = bool(instruments) and all(
        instrument["original_contractual_schedule_complete"] for instrument in instruments
    )
    yearly = _annualize_payments(instruments) if original_schedule_complete else {}
    coupon = (
        sum(debt["annual_interest_run_rate_usd"] for debt in instruments)
        if coupons_complete
        else None
    )
    known_interest = [
        debt["annual_interest_run_rate_usd"]
        for debt in instruments
        if debt["annual_interest_run_rate_usd"] is not None
    ]
    known_interest_floor = sum(known_interest) if known_interest else None
    service = (
        sum(debt["annual_debt_service_usd"] for debt in instruments) if services_complete else None
    )
    # Complete payments on the listed debt do not prove that all facility obligations are listed.
    debt_scope_complete = _text(facts, "debt_scope_complete") == "yes"
    cash_period = facts["annual_cfads_usd"].period if cfads is not None else None
    periods_match = bool(cash_period) and all(
        debt["service_period"] == cash_period for debt in instruments
    )
    dscr = _ratio(cfads, service) if debt_scope_complete and periods_match else None
    gaps = []
    if _number(facts, "energized_it_mw") is None:
        gaps.append("Energized critical IT MW unmeasured")
    if revenue is None:
        gaps.append("Annual operating revenue unmeasured")
    if cfads is None:
        gaps.append("Cash available after operating costs and maintenance reserves unmeasured")
    if not services_complete and not original_schedule_complete:
        gaps.append("Complete principal and interest payment schedule unmeasured")
    if not debt_scope_complete:
        gaps.append("Complete facility debt perimeter unverified")
    if cfads is not None and services_complete and not periods_match:
        gaps.append("Cash-flow and debt-service periods are unmatched")
    if case.role == "compute_operator" and _number(facts, "gpu_economic_life_years") is None:
        gaps.append("GPU economic life unmeasured")
    if _text(facts, "ultimate_creditors") is None:
        gaps.append("Ultimate creditor holdings unmeasured")
    timeline = [
        {"event": key, **facts[key].model_dump(mode="json")}
        for key in ("power_ready", "service_start", "service_full", "contract_end")
        if key in facts
    ]
    timeline.extend(
        {
            "event": "debt_maturity",
            "instrument": instrument["id"],
            **instrument["facts"]["maturity"],
        }
        for instrument in instruments
        if instrument["maturity"]
    )
    base_revenue = revenue if revenue is not None else average
    for annual in yearly.values():
        annual["cash_margin_on_contract_average_pct"] = (
            100 * annual["debt_service_usd"] / average if average and average > 0 else None
        )
    thresholds = {
        "cash_margin_required_for_interest_pct": 100 * coupon / base_revenue
        if coupon is not None and base_revenue and base_revenue > 0
        else None,
        "cash_margin_required_for_listed_debt_service_pct": 100 * service / base_revenue
        if service is not None and base_revenue and base_revenue > 0
        else None,
        "revenue_basis": "reported annual revenue"
        if revenue is not None
        else "base-term contract average",
        "note": "Thresholds exclude unlisted debt. A contract average is not a current cash receipt or a utilization measure.",
    }
    sensitivities = []
    # A cash margin is an explicit sensitivity assumption, never a measured NOI margin.
    if base_revenue is not None and coupon is not None:
        for cash_margin in (0.2, 0.4, 0.6, 0.8):
            for revenue_factor in (1.0, 0.75, 0.5):
                # Hold baseline operating costs/reserves fixed as receipts fall.
                # The margin and fixed-cost behavior are explicit assumptions.
                modeled_cash = base_revenue * revenue_factor - base_revenue * (1 - cash_margin)
                sensitivities.append(
                    {
                        "assumptions": {
                            "cash_margin_pct": cash_margin * 100,
                            "revenue_factor": revenue_factor,
                            "cost_behavior": "fixed baseline cash costs and reserves",
                        },
                        "modeled_cash_usd": modeled_cash,
                        "interest_coverage": _ratio(modeled_cash, coupon),
                        "listed_debt_service_coverage": _ratio(modeled_cash, service),
                    }
                )
    return {
        "id": case.id,
        "entity": case.entity,
        "ticker": case.ticker,
        "project": case.project,
        "scope": case.scope,
        "role": case.role,
        "counterparties": case.counterparties,
        "as_of": as_of.isoformat(),
        "facts": {key: fact.model_dump(mode="json") for key, fact in facts.items()},
        "instruments": instruments,
        "annual_contract_average_usd": average,
        "annual_interest_run_rate_usd": coupon,
        "known_cash_interest_floor_usd": known_interest_floor,
        "annual_listed_debt_service_usd": service,
        "noi_interest_coverage_proxy": _ratio(noi, coupon),
        "debt_service_coverage_ratio": dscr,
        "debt_service_coverage_basis": facts["annual_cfads_usd"].kind if dscr is not None else None,
        "cash_after_listed_debt_service_usd": cfads - service
        if cfads is not None and service is not None and periods_match
        else None,
        "thresholds": thresholds,
        "monthly_interest_run_rate_usd": coupon / 12 if coupon is not None else None,
        "monthly_contract_average_usd": average / 12 if average is not None else None,
        "annual_scheduled_debt_service": list(yearly.values()),
        "timeline": timeline,
        "sensitivities": sensitivities,
        "missing_inputs": gaps,
        "notes": case.notes,
        "interpretation": {
            "interest": "Annualized on the stated principal and rate snapshots; excludes amortization, fees and future draws.",
            "noi_proxy": "NOI/coupon excludes principal, reserves and costs outside the stated NOI definition; it is not DSCR.",
            "delay": "Monthly run rates are exposure measures, not measured delay losses. Lost rent, credits and construction carry require their own schedules.",
            "loss": "Contractual collateral and guarantee routes are reported. No expected loss or ultimate-holder allocation is inferred.",
        },
    }
