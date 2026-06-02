from __future__ import annotations

from bubble.quality.report_invariants import (
    check_report_invariants,
    report_invariant_violations,
)


def test_consistent_report_has_no_invariant_violations() -> None:
    report = {
        "key_metrics": {
            "capital_distinct_debt_like_notional_usd": 900,
            "capital_debt_like_notional_usd": 1_000,
            "capital_total_notional_usd": 1_200,
            "materiality_adjudication_final_metric_supported_amount_usd": 800,
            "materiality_adjudication_approved_row_supported_amount_usd": 1_100,
            "materiality_adjudication_final_metric_group_count": 10,
            "materiality_adjudication_approved_for_metric_use": 12,
            "materiality_adjudication_decisions": 20,
            "timing_signal_ai_infra_capital_refinancing_usd_2024_2030": 400,
            "timing_signal_capital_refinancing_usd_2024_2030": 500,
            "timing_signal_capital_refinancing_forward_from_as_of_usd": 200,
            "timing_signal_ai_infra_capital_refinancing_forward_from_as_of_usd": 150,
            "tracker_distinct_capacity_high_mw": 90,
            "tracker_capacity_high_mw": 100,
            "contract_contagion_notional_basis": (
                "path_summed_multiplicity_inflated_not_exposure"
            ),
            "contract_contagion_ai_infra_notional_basis": (
                "path_summed_multiplicity_inflated_not_exposure"
            ),
        }
    }

    assert report_invariant_violations(report) == []
    assert all(item.ok is True for item in check_report_invariants(report))


def test_invariant_checker_flags_superset_violations() -> None:
    report = {
        "key_metrics": {
            "capital_distinct_debt_like_notional_usd": 1_100,
            "capital_debt_like_notional_usd": 1_000,
            "capital_total_notional_usd": 1_200,
            "materiality_adjudication_final_metric_supported_amount_usd": 1_300,
            "materiality_adjudication_approved_row_supported_amount_usd": 1_100,
            "timing_signal_capital_refinancing_usd_2024_2030": 500,
            "timing_signal_capital_refinancing_forward_from_as_of_usd": 600,
            "timing_signal_ai_infra_capital_refinancing_forward_from_as_of_usd": 550,
            "contract_contagion_notional_basis": (
                "path_summed_multiplicity_inflated_not_exposure"
            ),
            "contract_contagion_ai_infra_notional_basis": (
                "path_summed_multiplicity_inflated_not_exposure"
            ),
        }
    }

    violations = report_invariant_violations(report)

    assert {item.name for item in violations} == {
        "capital distinct debt-like notional <= debt-like notional",
        "materiality final metric <= approved row supported amount",
        "forward timing wall <= total timing wall",
    }


def test_invariant_checker_uses_decision_summary_fallback() -> None:
    report = {
        "key_metrics": {
            "capital_distinct_debt_like_notional_usd": 900,
            "contract_contagion_notional_basis": (
                "path_summed_multiplicity_inflated_not_exposure"
            ),
            "contract_contagion_ai_infra_notional_basis": (
                "path_summed_multiplicity_inflated_not_exposure"
            ),
        }
    }
    decision_summary = {
        "final_metric_supported_amount_usd": 800,
        "approved_row_supported_amount_usd": 1_100,
        "final_metric_group_count": 10,
        "approved_for_metric_use": 12,
        "decisions": 20,
    }

    by_name = {
        item.name: item
        for item in check_report_invariants(report, decision_summary=decision_summary)
    }

    assert by_name["materiality final metric <= approved row supported amount"].ok is True
    assert by_name["approved metric rows <= materiality decisions"].ok is True
    assert by_name["capital distinct debt-like notional <= debt-like notional"].ok is None


def test_invariant_checker_requires_contract_path_sum_basis_labels() -> None:
    report = {
        "key_metrics": {
            "capital_distinct_debt_like_notional_usd": 900,
            "capital_debt_like_notional_usd": 1_000,
            "capital_total_notional_usd": 1_200,
            "contract_contagion_notional_basis": "deduped_exposure",
        },
        "burry_question_answers": {
            "hidden_risks_and_contagion": {
                "current_contract_contagion_ai_infra_notional_basis": (
                    "path_summed_multiplicity_inflated_not_exposure"
                )
            }
        },
    }

    by_name = {item.name: item for item in check_report_invariants(report)}

    assert (
        by_name["contract-contagion total notional is labeled path-summed"].ok is False
    )
    assert by_name["contract-contagion AI notional is labeled path-summed"].ok is True
