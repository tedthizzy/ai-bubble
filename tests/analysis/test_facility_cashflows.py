"""Financial boundaries for joined facility economics."""

from datetime import date

import pytest
from pydantic import ValidationError

from bubble.analysis.facility_cashflows import analyze_facility
from bubble.models.facility import (
    FacilityCase,
    FacilityDebt,
    FacilityFact,
    FacilityPrincipalPayment,
)

AS_OF = date(2026, 10, 17)


def fact(value: float | str, **kwargs: object) -> FacilityFact:
    return FacilityFact.model_validate(
        {
            "value": value,
            "unit": "USD",
            "source_id": "source",
            "quote": "fixture",
            "observed_on": AS_OF,
            **kwargs,
        }
    )


def facility(**kwargs: object) -> FacilityCase:
    return FacilityCase.model_validate(
        {
            "id": "site",
            "entity": "Operator",
            "ticker": "OP",
            "project": "Campus",
            "role": "colocation_landlord",
            "counterparties": ["Tenant"],
            "facts": {},
            **kwargs,
        }
    )


def debt(**kwargs: object) -> FacilityDebt:
    return FacilityDebt.model_validate(
        {
            "id": "note",
            "borrower": "Project SPV",
            "facts": {
                "principal_usd": fact(1000),
                "coupon_pct": fact(10),
            },
            **kwargs,
        }
    )


def test_missing_data_remains_unknown_instead_of_zero_debt_or_zero_cost() -> None:
    result = analyze_facility(facility(), AS_OF)
    assert result["debt_service_coverage_ratio"] is None
    assert result["annual_interest_run_rate_usd"] is None
    assert result["sensitivities"] == []
    assert "Complete facility debt perimeter unverified" in result["missing_inputs"]


def test_contract_average_and_coupon_are_not_dscr_or_realized_cash() -> None:
    case = facility(
        facts={"base_contract_value_usd": fact(10_000), "base_contract_years": fact(10)},
        debts=[debt()],
    )
    result = analyze_facility(case, AS_OF)
    assert result["annual_contract_average_usd"] == 1000
    assert result["annual_interest_run_rate_usd"] == 100
    assert result["thresholds"]["cash_margin_required_for_interest_pct"] == 10
    assert result["debt_service_coverage_ratio"] is None
    assert result["annual_listed_debt_service_usd"] is None
    assert "Annual operating revenue unmeasured" in result["missing_inputs"]


def test_commitments_are_not_used_as_drawn_principal_and_floating_spread_is_not_rate() -> None:
    case = facility(debts=[debt(facts={"commitment_usd": fact(1000), "spread_pct": fact(2.25)})])
    result = analyze_facility(case, AS_OF)
    assert result["annual_interest_run_rate_usd"] is None
    assert result["instruments"][0]["principal_usd"] is None


def test_partial_debt_rates_do_not_produce_full_coverage() -> None:
    case = facility(debts=[debt(), debt(id="floating", facts={"principal_usd": fact(1000)})])
    result = analyze_facility(case, AS_OF)
    assert result["instruments"][0]["annual_interest_run_rate_usd"] == 100
    assert result["annual_interest_run_rate_usd"] is None
    assert result["known_cash_interest_floor_usd"] == 100
    assert result["thresholds"]["cash_margin_required_for_interest_pct"] is None


def test_effective_interest_rate_is_not_a_cash_coupon() -> None:
    result = analyze_facility(
        facility(debts=[debt(facts={"principal_usd": fact(1000), "interest_rate_pct": fact(7)})]),
        AS_OF,
    )
    assert result["annual_interest_run_rate_usd"] is None
    assert result["known_cash_interest_floor_usd"] is None


def test_snapshot_interest_and_future_principal_are_not_a_payment_schedule() -> None:
    result = analyze_facility(
        facility(
            debts=[
                debt(
                    facts={
                        "principal_usd": fact(1000),
                        "coupon_pct": fact(10),
                        "annual_principal_usd": fact(100, period="2027"),
                    }
                )
            ]
        ),
        AS_OF,
    )
    assert result["annual_interest_run_rate_usd"] == 100
    assert result["annual_listed_debt_service_usd"] is None


def test_dscr_requires_complete_debt_perimeter_and_matched_cash_period() -> None:
    facts = {"annual_cfads_usd": fact(300, period="2027"), "debt_scope_complete": fact("yes")}
    instrument = debt(
        facts={
            "principal_usd": fact(1000),
            "coupon_pct": fact(10),
            "annual_principal_usd": fact(100, period="2027"),
            "annual_interest_usd": fact(100, period="2027"),
        }
    )
    result = analyze_facility(facility(facts=facts, debts=[instrument]), AS_OF)
    assert result["debt_service_coverage_ratio"] == 1.5
    assert result["cash_after_listed_debt_service_usd"] == 100
    incomplete = {**facts, "debt_scope_complete": fact("not verified")}
    assert (
        analyze_facility(facility(facts=incomplete, debts=[instrument]), AS_OF)[
            "debt_service_coverage_ratio"
        ]
        is None
    )
    mismatched = {**facts, "annual_cfads_usd": fact(300, period="2028")}
    result = analyze_facility(facility(facts=mismatched, debts=[instrument]), AS_OF)
    assert result["debt_service_coverage_ratio"] is None
    assert result["cash_after_listed_debt_service_usd"] is None


def test_future_disclosures_are_rejected_and_partial_dates_are_not_invented() -> None:
    with pytest.raises(ValueError, match="postdates"):
        analyze_facility(
            facility(facts={"service_full": fact("2028", observed_on="2026-10-18")}), AS_OF
        )
    result = analyze_facility(
        facility(facts={"service_full": fact("first quarter of 2027", kind="issuer_forecast")}),
        AS_OF,
    )
    assert result["timeline"][0]["value"] == "first quarter of 2027"
    assert result["timeline"][0]["kind"] == "issuer_forecast"


def test_scenarios_show_explicit_assumptions_without_changing_source_facts() -> None:
    case = facility(facts={"annual_revenue_usd": fact(1000)}, debts=[debt()])
    result = analyze_facility(case, AS_OF)
    scenario = result["sensitivities"][0]
    assert scenario["assumptions"] == {
        "cash_margin_pct": 20,
        "revenue_factor": 1.0,
        "cost_behavior": "fixed baseline cash costs and reserves",
    }
    assert scenario["modeled_cash_usd"] == 200
    assert scenario["interest_coverage"] == 2
    assert scenario["listed_debt_service_coverage"] is None
    assert case.facts["annual_revenue_usd"].value == 1000
    reduced = result["sensitivities"][1]
    assert reduced["modeled_cash_usd"] == -50
    assert reduced["interest_coverage"] == -0.5


def test_duplicate_instruments_and_nonfinite_values_are_rejected() -> None:
    with pytest.raises(ValidationError, match="only once"):
        facility(debts=[debt(), debt()])
    for value in (float("nan"), float("inf")):
        with pytest.raises(ValidationError, match="finite"):
            fact(value)


def test_irregular_first_coupon_and_declining_balance_follow_full_principal_table() -> None:
    instrument = debt(
        facts={
            "principal_usd": fact(1000),
            "original_principal_usd": fact(1000),
            "coupon_pct": fact(6),
            "issue_date": fact("2026-04-30"),
            "first_interest_payment": fact("2026-11-15"),
            "maturity": fact("2027-11-15"),
            "interest_day_count": fact("30/360"),
        },
        principal_payments=[
            FacilityPrincipalPayment(due_on=date(2027, 5, 15), amount=fact(400)),
            FacilityPrincipalPayment(due_on=date(2027, 11, 15), amount=fact(600)),
        ],
    )
    result = analyze_facility(facility(debts=[instrument]), AS_OF)
    schedule = result["instruments"][0]["scheduled_cash_payments"]
    assert schedule[0]["interest_usd"] == 32.5  # 195/360 of 6%, not half a year.
    assert schedule[1]["interest_usd"] == 30
    assert schedule[2]["interest_usd"] == 18
    assert schedule[-1]["remaining_principal_usd"] == 0
    assert result["annual_scheduled_debt_service"][1]["debt_service_usd"] == 1048
    assert result["debt_service_coverage_ratio"] is None
    assert (
        "Complete principal and interest payment schedule unmeasured"
        not in result["missing_inputs"]
    )


def test_partial_principal_table_does_not_look_complete() -> None:
    instrument = debt(
        facts={
            "principal_usd": fact(1000),
            "original_principal_usd": fact(1000),
            "coupon_pct": fact(6),
            "issue_date": fact("2026-06-09"),
            "first_interest_payment": fact("2026-11-30"),
            "maturity": fact("2027-11-30"),
            "interest_day_count": fact("30/360"),
        },
        principal_payments=[FacilityPrincipalPayment(due_on=date(2027, 11, 30), amount=fact(900))],
    )
    with pytest.raises(ValueError, match="repay original face"):
        analyze_facility(facility(debts=[instrument]), AS_OF)
