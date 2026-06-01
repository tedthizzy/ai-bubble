from __future__ import annotations

from datetime import date

from bubble.analysis.debt_service import analyze_debt_service
from bubble.models.base import DealType, HumanReviewStatus, Provenance, SourceType
from bubble.models.compute import CapexPaybackCase
from bubble.models.deal import Deal


def _prov(source_uri: str) -> Provenance:
    return Provenance(
        source_uri=source_uri,
        source_type=SourceType.SEC_EDGAR,
        confidence=0.9,
        human_review_status=HumanReviewStatus.APPROVED,
        content_hash=Provenance.compute_content_hash(source_uri),
    )


def test_debt_service_counts_only_explicit_plausible_rates_and_surfaces_gaps() -> None:  # noqa: PLR0915
    deals = [
        Deal(
            source_deal_id="facility-1",
            deal_type=DealType.DEBT_FACILITY,
            title="GPU collateral credit facility",
            parties=["issuer", "bank"],
            counterparty_roles={"borrower": ["issuer"], "lender": ["bank"]},
            notional_amount_usd=1_000_000_000,
            maturity_date=date(2028, 6, 30),
            key_terms={"interest_rate": 0.05},
            provenance=_prov("sec:facility-1"),
        ),
        Deal(
            source_deal_id="bond-1",
            deal_type=DealType.BOND,
            title="Data center senior notes with missing coupon extraction",
            parties=["issuer", "noteholders"],
            counterparty_roles={"issuer": ["issuer"], "noteholder": ["noteholders"]},
            notional_amount_usd=500_000_000,
            maturity_date=date(2030, 1, 15),
            provenance=_prov("sec:bond-1"),
        ),
        Deal(
            source_deal_id="lease-1",
            deal_type=DealType.LEASE,
            title="AI infrastructure lease with outlier extracted rate",
            parties=["tenant", "lessor"],
            counterparty_roles={"lessee": ["tenant"], "lessor": ["lessor"]},
            notional_amount_usd=200_000_000,
            maturity_date=date(2031, 1, 15),
            key_terms={"interest_rate": 0.85},
            provenance=_prov("sec:lease-1"),
        ),
    ]
    payback_cases = [
        CapexPaybackCase(
            source_case_id="case-1",
            entity="issuer",
            capex_usd=2_000_000_000,
            annual_revenue_run_rate_usd=100_000_000,
            gross_margin_pct=50,
            annual_power_cost_usd=10_000_000,
            annual_debt_service_usd=60_000_000,
            provenance=_prov("sec:payback-1"),
        ),
        CapexPaybackCase(
            source_case_id="case-2",
            entity="issuer",
            capex_usd=1_000_000_000,
            annual_revenue_run_rate_usd=200_000_000,
            gross_margin_pct=50,
            provenance=_prov("sec:payback-2"),
        ),
    ]

    metrics = analyze_debt_service(deals, payback_cases)

    assert metrics.status == "measured_partial"
    assert metrics.scoped_deal_count == 3
    assert metrics.out_of_scope_deal_count == 0
    assert metrics.debt_like_deal_count == 3
    assert metrics.out_of_scope_debt_like_deal_count == 0
    assert metrics.obligations_count == 3
    assert metrics.distinct_obligations_count == 3
    assert metrics.duplicate_candidate_obligation_count == 0
    assert metrics.duplicate_candidate_notional_usd == 0
    assert metrics.explicit_rate_obligation_count == 2
    assert metrics.measured_rate_obligation_count == 1
    assert metrics.missing_rate_obligation_count == 1
    assert metrics.rate_outlier_obligation_count == 1
    assert metrics.debt_like_notional_usd == 1_700_000_000
    assert metrics.out_of_scope_debt_like_notional_usd == 0
    assert metrics.scope_inclusion_reason_counts == {"direct_ai_data_center_keyword": 3}
    assert metrics.explicit_rate_notional_usd == 1_200_000_000
    assert metrics.measured_rate_notional_usd == 1_000_000_000
    assert metrics.missing_rate_notional_usd == 500_000_000
    assert metrics.rate_outlier_notional_usd == 200_000_000
    assert metrics.measured_annual_interest_usd == 50_000_000
    assert metrics.measured_rate_notional_coverage_pct == 58.82
    assert metrics.distinct_measured_rate_notional_usd == 1_000_000_000
    assert metrics.distinct_missing_rate_notional_usd == 500_000_000
    assert metrics.distinct_measured_annual_interest_usd == 50_000_000
    assert metrics.distinct_measured_rate_notional_coverage_pct == 58.82
    assert metrics.obligations_missing_maturity_count == 0
    assert metrics.notional_missing_maturity_usd == 0
    assert metrics.distinct_obligations_missing_maturity_count == 0
    assert metrics.distinct_notional_missing_maturity_usd == 0
    assert metrics.maturity_wall_notional_usd_2024_2030 == 1_500_000_000
    assert metrics.maturity_wall_measured_annual_interest_usd_2024_2030 == 50_000_000
    assert metrics.maturity_wall_missing_rate_notional_usd_2024_2030 == 500_000_000
    assert metrics.distinct_maturity_wall_notional_usd_2024_2030 == 1_500_000_000
    assert metrics.distinct_maturity_wall_measured_annual_interest_usd_2024_2030 == 50_000_000
    assert metrics.distinct_maturity_wall_missing_rate_notional_usd_2024_2030 == 500_000_000
    assert metrics.debt_service_wall_by_quarter == {
        "2028-Q2": {
            "obligation_count": 1,
            "measured_rate_obligation_count": 1,
            "missing_rate_obligation_count": 0,
            "maturing_notional_usd": 1_000_000_000,
            "measured_rate_notional_usd": 1_000_000_000,
            "missing_rate_notional_usd": 0,
            "measured_annual_interest_usd": 50_000_000,
        },
        "2030-Q1": {
            "obligation_count": 1,
            "measured_rate_obligation_count": 0,
            "missing_rate_obligation_count": 1,
            "maturing_notional_usd": 500_000_000,
            "measured_rate_notional_usd": 0,
            "missing_rate_notional_usd": 500_000_000,
            "measured_annual_interest_usd": 0,
        },
    }
    assert metrics.distinct_debt_service_wall_by_quarter == metrics.debt_service_wall_by_quarter
    assert metrics.top_debt_service_quarters[0].quarter == "2028-Q2"
    assert metrics.top_distinct_debt_service_quarters[0].quarter == "2028-Q2"
    assert metrics.top_entity_debt_service_risks[0].entity == "issuer"
    assert metrics.top_entity_debt_service_risks[0].distinct_obligation_count == 2
    assert metrics.top_entity_debt_service_risks[0].measured_annual_interest_usd == 50_000_000
    assert (
        metrics.top_entity_debt_service_risks[0].maturity_wall_notional_usd_2024_2030
        == 1_500_000_000
    )
    assert metrics.top_entity_debt_service_risks[0].peak_maturity_quarter == "2028-Q2"
    assert metrics.top_entity_debt_service_risks[0].review_priority_reasons == [
        "measured_debt_service",
        "missing_interest_rate",
        "peak_maturity_quarter:2028-Q2",
    ]
    assert metrics.top_debt_service_quarters[0].measured_annual_interest_usd == 50_000_000
    assert metrics.top_debt_service_obligations[0].interest_rate_pct == 5
    assert metrics.top_debt_service_obligations[0].annual_interest_usd == 50_000_000
    assert metrics.top_debt_service_coverage_gaps[0].flags == ["missing_interest_rate"]
    assert metrics.top_debt_service_coverage_gaps[1].flags == ["rate_out_of_range"]
    assert metrics.payback_case_count == 2
    assert metrics.payback_cases_with_debt_service == 1
    assert metrics.payback_cases_missing_debt_service == 1
    assert metrics.payback_cases_with_gross_cash_flow == 2
    assert metrics.cash_flow_mismatch_red_flag_count == 1
    assert metrics.top_cash_flow_mismatch_cases[0].debt_service_coverage_ratio == 0.67
    assert metrics.top_cash_flow_mismatch_cases[0].cash_after_debt_service_usd == -20_000_000


def test_empty_debt_service_inputs_block_conclusion() -> None:
    metrics = analyze_debt_service([], [])

    assert metrics.status == "blocked_missing_debt_service_evidence"
    assert metrics.measured_annual_interest_usd == 0
    assert metrics.evidence_summary["summary"]["unsupported_claims"] == 5


def test_debt_service_excludes_out_of_scope_corporate_debt() -> None:
    deals = [
        Deal(
            source_deal_id="edgar:0001467858:000000000000000000:debt_facility:gm",
            deal_type=DealType.DEBT_FACILITY,
            title="Automotive corporate credit facility",
            parties=["General Motors Co", "bank"],
            counterparty_roles={"borrower": ["General Motors Co"], "lender": ["bank"]},
            notional_amount_usd=2_000_000_000,
            maturity_date=date(2027, 12, 31),
            key_terms={"interest_rate": 0.06},
            provenance=_prov("sec:gm-facility"),
        ),
        Deal(
            source_deal_id="edgar:0001083301:000000000000000000:debt_facility:wulf",
            deal_type=DealType.DEBT_FACILITY,
            title="Corporate credit facility",
            parties=["TERAWULF INC.", "bank"],
            counterparty_roles={"borrower": ["TERAWULF INC."], "lender": ["bank"]},
            notional_amount_usd=300_000_000,
            maturity_date=date(2027, 12, 31),
            key_terms={"interest_rate": 0.08},
            provenance=_prov("sec:wulf-facility"),
        ),
    ]

    metrics = analyze_debt_service(deals, [])

    assert metrics.deal_count_scanned == 2
    assert metrics.scoped_deal_count == 1
    assert metrics.out_of_scope_deal_count == 1
    assert metrics.debt_like_deal_count == 1
    assert metrics.out_of_scope_debt_like_deal_count == 1
    assert metrics.debt_like_notional_usd == 300_000_000
    assert metrics.out_of_scope_debt_like_notional_usd == 2_000_000_000
    assert metrics.measured_annual_interest_usd == 24_000_000
    assert metrics.scope_inclusion_reason_counts == {
        "core_ai_data_center_cik": 1,
        "core_ai_data_center_entity": 1,
    }


def test_debt_service_surfaces_distinct_obligations_and_duplicate_candidates() -> None:
    deals = [
        Deal(
            source_deal_id="edgar:0001083301:000110465925101866:bond:measured",
            deal_type=DealType.BOND,
            title="TERAWULF INC. - convertible notes",
            parties=["TERAWULF INC.", "noteholders"],
            counterparty_roles={"issuer": ["TERAWULF INC."], "noteholder": ["noteholders"]},
            notional_amount_usd=3_200_000_000,
            maturity_date=date(2025, 10, 16),
            key_terms={"interest_rate": 0.0775},
            provenance=_prov("sec:wulf-8k"),
        ),
        Deal(
            source_deal_id="edgar:0001083301:000110465925101866:debt_facility:missing",
            deal_type=DealType.DEBT_FACILITY,
            title="TERAWULF INC. - indenture exhibit",
            parties=["TERAWULF INC.", "trustee"],
            counterparty_roles={"issuer": ["TERAWULF INC."], "trustee": ["trustee"]},
            notional_amount_usd=3_200_000_000,
            maturity_date=date(2025, 10, 23),
            provenance=_prov("sec:wulf-exhibit"),
        ),
    ]

    metrics = analyze_debt_service(deals, [])

    assert metrics.obligations_count == 2
    assert metrics.distinct_obligations_count == 1
    assert metrics.duplicate_candidate_obligation_count == 1
    assert metrics.duplicate_candidate_notional_usd == 3_200_000_000
    assert metrics.debt_like_notional_usd == 6_400_000_000
    assert metrics.measured_rate_notional_usd == 3_200_000_000
    assert metrics.missing_rate_notional_usd == 3_200_000_000
    assert metrics.distinct_measured_rate_notional_usd == 3_200_000_000
    assert metrics.distinct_missing_rate_notional_usd == 0
    assert metrics.distinct_measured_annual_interest_usd == 248_000_000
    assert metrics.maturity_wall_notional_usd_2024_2030 == 6_400_000_000
    assert metrics.distinct_maturity_wall_notional_usd_2024_2030 == 3_200_000_000
    assert metrics.distinct_debt_service_wall_by_quarter == {
        "2025-Q4": {
            "obligation_count": 1,
            "measured_rate_obligation_count": 1,
            "missing_rate_obligation_count": 0,
            "maturing_notional_usd": 3_200_000_000,
            "measured_rate_notional_usd": 3_200_000_000,
            "missing_rate_notional_usd": 0,
            "measured_annual_interest_usd": 248_000_000,
        }
    }
    assert metrics.top_duplicate_candidate_groups[0].representative_deal_ref.endswith(
        ":bond:measured"
    )
    assert metrics.top_duplicate_candidate_groups[0].deal_refs == [
        "edgar:0001083301:000110465925101866:bond:measured",
        "edgar:0001083301:000110465925101866:debt_facility:missing",
    ]
    assert metrics.top_entity_debt_service_risks[0].entity == "TERAWULF INC."
    assert metrics.top_entity_debt_service_risks[0].distinct_obligation_count == 1
    assert metrics.top_entity_debt_service_risks[0].missing_rate_notional_usd == 0
