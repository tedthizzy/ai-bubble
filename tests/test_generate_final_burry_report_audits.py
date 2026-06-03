from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from bubble.quality.report_consistency import check_metric_audit_coverage

if TYPE_CHECKING:
    from collections.abc import Callable

_REPORT_MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "generate_final_burry_report.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "generate_final_burry_report_for_test",
    _REPORT_MODULE_PATH,
)
assert _SPEC is not None
assert _SPEC.loader is not None
_REPORT_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _REPORT_MODULE
_SPEC.loader.exec_module(_REPORT_MODULE)

merge_evidence_audits = cast(
    "Callable[..., list[dict[str, Any]]]",
    _REPORT_MODULE.merge_evidence_audits,
)
summarize_evidence_audit_dicts = cast(
    "Callable[[list[dict[str, Any]]], dict[str, Any]]",
    _REPORT_MODULE.summarize_evidence_audit_dicts,
)
report_answer_metric_audits = cast(
    "Callable[..., list[dict[str, Any]]]",
    _REPORT_MODULE.report_answer_metric_audits,
)
capital_materiality_scope_fields = cast(
    "Callable[..., dict[str, Any]]",
    _REPORT_MODULE.capital_materiality_scope_fields,
)
materiality_relevance_scope_fields = cast(
    "Callable[[dict[str, Any]], dict[str, Any]]",
    _REPORT_MODULE.materiality_relevance_scope_fields,
)
debt_service_timing_coverage_fields = cast(
    "Callable[[dict[str, Any]], dict[str, Any]]",
    _REPORT_MODULE.debt_service_timing_coverage_fields,
)
graph_parity_basis_fields = cast(
    "Callable[..., dict[str, Any]]",
    _REPORT_MODULE.graph_parity_basis_fields,
)
compute_burry_mismatch_ratios = cast(
    "Callable[..., dict[str, Any]]",
    _REPORT_MODULE.compute_burry_mismatch_ratios,
)


def _audit(
    claim_id: str,
    value: object,
    *,
    tier: str = "measured",
    confidence: float = 0.9,
    effective_confidence: float | None = None,
    semantic_bucket: str = "not_evaluated",
    eligible: bool = True,
) -> dict[str, object]:
    return {
        "claim_id": claim_id,
        "claim": claim_id,
        "value": value,
        "unit": "USD",
        "tier": tier,
        "confidence": confidence,
        "effective_confidence": (
            confidence if effective_confidence is None else effective_confidence
        ),
        "source_count": 1,
        "source_types": ["sec_edgar"],
        "sources": [],
        "semantic_bucket": semantic_bucket,
        "semantic_confidence_cap": 1.0,
        "blocking_issues": [],
        "eligible_for_high_confidence": eligible,
    }


def test_merge_evidence_audits_includes_top_level_and_nested_analyzer_audits() -> None:
    base = [
        _audit(
            "final.bubble_conclusion",
            "blocked",
            tier="unsupported",
            confidence=0.0,
            eligible=False,
        )
    ]
    capital = {"claim_audits": [_audit("capital.debt_like_notional", 1_200_000_000_000)]}
    debt_service = {
        "evidence_summary": {
            "claim_audits": [_audit("debt_service.missing_rate_notional", 689_881_283_165.74)]
        }
    }

    merged = merge_evidence_audits(base, capital, debt_service)

    assert [audit["claim_id"] for audit in merged] == [
        "final.bubble_conclusion",
        "capital.debt_like_notional",
        "debt_service.missing_rate_notional",
    ]
    summary = summarize_evidence_audit_dicts(merged)
    assert summary["audited_claims"] == 3
    assert summary["unsupported_claims"] == 1
    assert summary["max_permitted_report_confidence"] == 0.25


def test_serialized_audit_summary_uses_effective_semantic_confidence() -> None:
    audits = [
        _audit(
            "capital.asset_misread",
            33_600_000_000,
            confidence=0.92,
            effective_confidence=0.3,
            semantic_bucket="asset_or_capacity",
            eligible=False,
        )
    ]

    summary = summarize_evidence_audit_dicts(audits)

    assert summary["semantic_evaluated_claims"] == 1
    assert summary["semantic_asset_or_capacity_claims"] == 1
    assert summary["high_confidence_eligible_claims"] == 0
    assert summary["max_permitted_report_confidence"] == 0.3


def test_serialized_audit_summary_counts_equity_or_production_claims() -> None:
    audits = [
        _audit(
            "capital.equity_misread",
            12_023_000_000,
            confidence=0.92,
            effective_confidence=0.3,
            semantic_bucket="equity_or_production",
            eligible=False,
        )
    ]

    summary = summarize_evidence_audit_dicts(audits)

    assert summary["semantic_evaluated_claims"] == 1
    assert summary["semantic_equity_or_production_claims"] == 1
    assert summary["high_confidence_eligible_claims"] == 0
    assert summary["max_permitted_report_confidence"] == 0.3


def test_merged_scalar_audit_clears_high_impact_metric_warning() -> None:
    report = {
        "evidence_quality": {
            "claim_audits": merge_evidence_audits(
                [],
                {"claim_audits": [_audit("capital.debt_like_notional", 1_200_000_000_000)]},
            )
        },
        "burry_question_answers": {
            "capital": {"current_debt_like_notional_usd": 1_200_000_000_000}
        },
    }

    assert check_metric_audit_coverage(report, threshold=100e9) == []


def test_report_answer_metric_audits_cover_source_backed_rollup_values() -> None:
    source_row = {
        "signal_id": "timing:test",
        "amount_usd": 165_000_000_000,
        "source_uri": "https://www.sec.gov/Archives/edgar/data/1/test.htm",
        "content_hash": "a" * 64,
        "human_review_status": "pending",
        "source_confidence": 0.8,
    }
    audits = report_answer_metric_audits(
        timing_signal_summary={
            "capital_refinancing_usd_2024_2030": 5_756_305_034_829.88,
            "ai_infra_capital_refinancing_usd_2024_2030": 292_289_419_740.72,
            "capital_refinancing_forward_from_as_of_usd": 330_000_000_000,
            "ai_infra_capital_refinancing_forward_from_as_of_usd": 110_000_000_000,
            "capital_refinancing_historical_to_as_of_usd": 5_426_305_034_829.88,
            "ai_infra_capital_refinancing_historical_to_as_of_usd": 182_289_419_740.72,
            "compute_amount_usd_2024_2030": 219_410_000_000,
            "top_quarters": [
                {
                    "quarter": "2026-Q2",
                    "capital_refinancing_usd": 220_471_841_010,
                    "compute_amount_usd": 119_000_000_000,
                }
            ],
            "top_signals": [source_row],
        },
        review_queue_summary={
            "pending_notional_amount_usd": 23_633_011_843_625.81,
            "pending_exposure_usd": 31_463_801_592_426.92,
            "pending_capital_notional_amount_usd": 12_563_069_819_492.71,
            "pending_capital_distinct_notional_amount_usd": 11_922_835_694_492.71,
            "pending_capital_duplicate_notional_amount_usd": 640_234_125_000,
            "pending_ai_infra_relevant_capital_notional_amount_usd": 1_983_466_701_225,
            "pending_ai_infra_relevant_capital_distinct_notional_amount_usd": (827_720_451_225),
            "pending_compute_claim_amount_usd": 398_240_000_000,
            "pending_contagion_path_exposure_usd": 30_027_742_282_038,
            "top_distinct_capital_items": [
                {
                    **source_row,
                    "review_id": "review:test",
                    "notional_amount_usd": 734_000_000_000,
                }
            ],
        },
        weak_link_summary={
            "ai_infra_relevant_notional_usd": 333_003_514_666.67,
            "top_weak_links": [source_row],
            "top_debt_service_weak_links": [],
        },
        debt_service_metrics_dict={
            "distinct_debt_like_notional_usd": 1_200_595_124_370.18,
            "out_of_scope_debt_like_notional_usd": 15_328_280_365_435.22,
            "notional_missing_maturity_usd": 610_861_214_126.79,
            "distinct_notional_missing_maturity_usd": 541_811_068_259.58,
            "distinct_measured_rate_notional_usd": 474_858_841_204.44,
            "distinct_missing_rate_notional_usd": 599_461_137_298.53,
            "maturity_wall_notional_usd_2024_2030": 278_383_365_879.58,
            "distinct_maturity_wall_notional_usd_2024_2030": 241_928_365_879.58,
        },
        compute_metrics_dict={
            "total_gpu_capex_usd": 270_000_000,
            "compute_asset_count": 49,
            "gpu_price_observation_count": 3,
            "gpu_depreciation_blocked_generation_count": 10,
            "tam_blocked_claim_count": 9,
            "payback_case_count": 2,
            "payback_blocked_case_count": 1,
            "payback_missing_debt_service_count": 2,
            "eps_blocked_impact_count": 2,
            "chip_supply_blocked_observation_count": 7,
        },
        capital_metrics_dict={
            "distinct_total_notional_usd": 872_828_485_956.18,
        },
        capital_scope_summary_dict={
            "out_of_scope_debt_like_notional_usd": 15_328_280_365_435.22,
            "balance_sheet_context_debt_like_notional_usd": 1_758_649_865_154.68,
        },
        capital_exposure_graph_summary={
            "total_edge_notional_usd": 864_183_460_730.37,
            "ai_infra_relevant_notional_usd": 5_158_000_000,
            "ppa_capacity_mw": 27_430.5,
            "top_ai_infra_risk_bearers": [
                {
                    "node_id": "entity:equinix",
                    "name": "EQUINIX, INC.",
                    "ai_infra_relevant_exposure_usd": 4_750_000_000,
                }
            ],
            "top_ai_infra_obligors": [
                {
                    "node_id": "entity:equinix-europe-2-financing",
                    "name": "Equinix Europe 2 Financing Corporation LLC",
                    "ai_infra_relevant_exposure_usd": 2_050_000_000,
                }
            ],
            "top_ai_infra_ppa_offtakers": [
                {
                    "node_id": "entity:amazon-energy",
                    "name": "Amazon Energy LLC",
                    "ppa_capacity_mw": 15_028.15,
                    "distinct_power_suppliers": 38,
                    "ppa_edge_count": 38,
                }
            ],
            "top_ai_infra_ppa_offtaker_families": [
                {
                    "family_id": "family:microsoft",
                    "family_name": "Microsoft legal family",
                    "ppa_capacity_mw": 6_295.3,
                    "distinct_power_suppliers": 25,
                    "ppa_edge_count": 25,
                }
            ],
        },
        contract_contagion_summary={
            "paths": 8_749,
            "total_notional_usd": 44_591_146_002_769.22,
            "ai_infra_relevant_paths": 453,
            "ai_infra_relevant_notional_usd": 1_918_982_952_450.0,
        },
        materiality_adjudication_summary={
            "total_exposure_basis_usd": 56_029_144_923_052.73,
            "packets": 6_663,
            "source_backed_packets": 6_663,
        },
        materiality_adjudication_decision_summary={
            "approved_row_supported_amount_usd": 7_416_635_302_611.83,
            "final_metric_supported_amount_usd": 4_463_000_000_000,
            "final_metric_group_count": 1591,
        },
        materiality_relevance_summary={
            "direct_usd": 120_000_000_000,
            "watchlist_usd": 480_000_000_000,
            "established_usd": 600_000_000_000,
            "not_established_usd": 3_863_000_000_000,
            "final_metric_group_count": 1591,
        },
    )
    audit_by_id = {str(audit["claim_id"]): audit for audit in audits}
    expected_rollup_values = {
        "review_queue.pending_capital_distinct_notional": 11_922_835_694_492.71,
        "review_queue.pending_notional_gross": 23_633_011_843_625.81,
        "review_queue.pending_exposure_gross": 31_463_801_592_426.92,
        "review_queue.pending_capital_notional_gross": 12_563_069_819_492.71,
        "review_queue.pending_capital_duplicate_notional": 640_234_125_000,
        "review_queue.pending_ai_infra_relevant_capital_notional_gross": (1_983_466_701_225),
        "review_queue.pending_ai_infra_relevant_capital_distinct_notional": (827_720_451_225),
        "review_queue.pending_contagion_path_exposure_path_summed": 30_027_742_282_038,
        "review_queue.pending_compute_claim_amount": 398_240_000_000,
        "weak_link.ai_infra_relevant_notional": 333_003_514_666.67,
        "debt_service.distinct_debt_like_notional": 1_200_595_124_370.18,
        "debt_service.out_of_scope_debt_like_notional": 15_328_280_365_435.22,
        "debt_service.notional_missing_maturity": 610_861_214_126.79,
        "debt_service.distinct_measured_rate_notional": 474_858_841_204.44,
        "debt_service.distinct_missing_rate_notional": 599_461_137_298.53,
        "debt_service.distinct_missing_maturity_notional": 541_811_068_259.58,
        "debt_service.distinct_maturity_wall_notional_2024_2030": 241_928_365_879.58,
        "debt_service.maturity_wall_notional_2024_2030": 278_383_365_879.58,
        "capital.distinct_total_notional": 872_828_485_956.18,
        "capital.out_of_scope_debt_like_notional": 15_328_280_365_435.22,
        "capital.balance_sheet_context_debt_like_notional": 1_758_649_865_154.68,
        "capital_exposure.total_edge_notional": 864_183_460_730.37,
        "capital_exposure.ai_infra_relevant_notional": 5_158_000_000,
        "capital_exposure.ppa_capacity_mw": 27_430.5,
        "capital_exposure.top_ai_infra_risk_bearers.entity:equinix.ai_infra_notional": (
            4_750_000_000
        ),
        "capital_exposure.top_ai_infra_obligors.entity:equinix-europe-2-financing.ai_infra_notional": (
            2_050_000_000
        ),
        "capital_exposure.top_ai_infra_ppa_offtakers.entity:amazon-energy.ppa_capacity": (
            15_028.15
        ),
        "capital_exposure.top_ai_infra_ppa_offtaker_families.family:microsoft.ppa_capacity": (
            6_295.3
        ),
        "contract_contagion.ai_infra_relevant_notional": 1_918_982_952_450.0,
        "contract_contagion.total_path_summed_notional": 44_591_146_002_769.22,
        "compute.total_gpu_capex": 270_000_000,
        "compute.gpu_depreciation_blocked_generations": 10,
        "compute.tam_blocked_claims": 9,
        "compute.payback_blocked_cases": 1,
        "compute.payback_missing_debt_service_cases": 2,
        "compute.eps_blocked_impacts": 2,
        "compute.chip_supply_blocked_observations": 7,
        "materiality_adjudication.total_exposure_basis_gross": 56_029_144_923_052.73,
        "materiality_adjudication.approved_row_supported_amount_gross": (7_416_635_302_611.83),
        "materiality_adjudication.final_metric_supported_amount": 4_463_000_000_000,
    }
    for claim_id, value in expected_rollup_values.items():
        assert audit_by_id[claim_id]["value"] == value

    report = {
        "evidence_quality": {"claim_audits": audits},
        "burry_question_answers": {
            "when_cracks": {
                "current_timing_capital_refinancing_usd_2024_2030": (5_756_305_034_829.88),
                "current_timing_ai_infra_capital_refinancing_usd_2024_2030": (292_289_419_740.72),
                "current_timing_capital_refinancing_forward_from_as_of_usd": (330_000_000_000),
                "current_timing_ai_infra_capital_refinancing_forward_from_as_of_usd": (
                    110_000_000_000
                ),
                "current_timing_capital_refinancing_historical_to_as_of_usd": (
                    5_426_305_034_829.88
                ),
                "current_timing_ai_infra_capital_refinancing_historical_to_as_of_usd": (
                    182_289_419_740.72
                ),
                "current_timing_compute_amount_usd_2024_2030": 219_410_000_000,
                "current_top_timing_quarters": [
                    {
                        "capital_refinancing_usd": 220_471_841_010,
                        "compute_amount_usd": 119_000_000_000,
                    }
                ],
                "current_top_timing_signals": [{"amount_usd": 165_000_000_000}],
            },
            "hidden_risks_and_contagion": {
                "current_contract_contagion_total_notional_usd": 44_591_146_002_769.22,
                "current_contract_contagion_ai_infra_relevant_notional_usd": (1_918_982_952_450.0),
            },
            "how_large": {
                "materiality_final_metric_supported_amount_usd": 4_463_000_000_000,
                "materiality_direct_ai_linked_usd": 120_000_000_000,
                "materiality_watchlist_ai_linked_usd": 480_000_000_000,
                "materiality_established_ai_linked_usd": 600_000_000_000,
                "materiality_not_established_linkage_usd": 3_863_000_000_000,
                "top_distinct_capital_review_queue_items": [
                    {"notional_amount_usd": 734_000_000_000}
                ],
            },
        },
    }

    assert check_metric_audit_coverage(report, threshold=100e9) == []


def test_debt_service_timing_coverage_fields_surface_maturity_limits() -> None:
    fields = debt_service_timing_coverage_fields(
        {
            "distinct_obligations_count": 439,
            "distinct_obligations_missing_maturity_count": 165,
            "distinct_debt_like_notional_usd": 1_200_595_124_370.18,
            "distinct_notional_missing_maturity_usd": 541_811_068_259.58,
            "distinct_missing_rate_notional_usd": 599_461_137_298.53,
            "distinct_measured_rate_notional_coverage_pct": 44.2,
        }
    )

    assert fields["current_distinct_debt_service_obligations"] == 439
    assert fields["current_distinct_debt_service_obligations_missing_maturity"] == 165
    assert fields["current_distinct_debt_service_maturity_obligation_coverage_pct"] == 62.41
    assert fields["current_distinct_debt_service_debt_like_notional_usd"] == (1_200_595_124_370.18)
    assert fields["current_distinct_debt_service_notional_missing_maturity_usd"] == (
        541_811_068_259.58
    )
    assert fields["current_distinct_debt_service_maturity_notional_coverage_pct"] == 54.87
    assert fields["current_distinct_debt_service_missing_rate_notional_usd"] == (599_461_137_298.53)
    assert fields["current_distinct_debt_service_measured_rate_notional_coverage_pct"] == 44.2
    assert "165 of 439" in fields["current_timing_maturity_wall_coverage_note"]
    assert "floor, not a complete schedule" in fields["current_timing_maturity_wall_coverage_note"]


def test_graph_parity_basis_fields_label_contract_path_sums() -> None:
    fields = graph_parity_basis_fields(
        capital_exposure_graph_summary={
            "total_edge_notional_usd": 864_183_460_730.37,
            "ai_infra_relevant_notional_usd": 4_750_000_000,
        },
        contract_contagion_summary={
            "paths": 8_749,
            "total_notional_usd": 44_591_146_002_769.22,
            "ai_infra_relevant_paths": 453,
            "ai_infra_relevant_notional_usd": 1_918_982_952_450.0,
        },
        review_queue_summary={
            "pending_ai_infra_relevant_capital_distinct_notional_amount_usd": (827_720_451_225.0)
        },
    )

    assert fields["current_capital_exposure_notional_basis"] == (
        "deduped_edge_level_financing_notional"
    )
    assert fields["current_contract_contagion_notional_basis"] == (
        "path_summed_multiplicity_inflated_not_exposure"
    )
    assert fields["current_contract_contagion_ai_infra_notional_basis"] == (
        "path_summed_multiplicity_inflated_not_exposure"
    )
    assert fields["current_contract_contagion_average_path_notional_usd"] == (5_096_713_453.28)
    assert fields["current_contract_contagion_ai_infra_average_path_notional_usd"] == (
        4_236_165_457.95
    )
    assert fields["current_ai_infra_distinct_capital_reconciler_notional_usd"] == (
        827_720_451_225.0
    )
    assert "must not be quoted as headline" in fields["current_graph_parity_note"]


def test_capital_materiality_scope_fields_label_distinct_size_metrics() -> None:
    fields = capital_materiality_scope_fields(
        capital_debt_like_notional_usd=1_200_000_000_000,
        materiality_decision_summary={
            "final_metric_supported_amount_usd": 4_463_000_000_000,
            "final_metric_group_count": 1591,
        },
    )

    assert fields["capital_metric_scope"] == "curated_capital_structure_deal_graph"
    assert fields["materiality_metric_scope"] == (
        "broader_materiality_adjudication_supported_exposure"
    )
    assert fields["materiality_final_metric_supported_amount_usd"] == 4_463_000_000_000
    assert fields["materiality_final_metric_group_count"] == 1591
    assert fields["capital_to_materiality_scope_ratio"] == 3.7192
    assert "not directly additive" in fields["metric_scope_note"]


def test_materiality_relevance_scope_fields_label_thesis_scope() -> None:
    fields = materiality_relevance_scope_fields(
        {
            "direct_usd": 120_000_000_000,
            "watchlist_usd": 480_000_000_000,
            "established_usd": 600_000_000_000,
            "not_established_usd": 3_863_000_000_000,
            "direct_pct": 0.0269,
            "established_pct": 0.1344,
            "not_established_pct": 0.8656,
        }
    )

    assert fields["materiality_relevance_scope"] == (
        "deduped_final_metric_split_by_ai_data_center_linkage"
    )
    assert fields["materiality_direct_ai_linked_usd"] == 120_000_000_000
    assert fields["materiality_established_ai_linked_usd"] == 600_000_000_000
    assert fields["materiality_not_established_linkage_usd"] == 3_863_000_000_000
    assert fields["materiality_established_ai_linked_pct"] == 0.1344
    assert "must not be described as direct AI-bubble leverage" in fields["metric_relevance_note"]


class _PaybackCase:
    """Minimal payback-case stand-in for the mismatch-ratio function."""

    def __init__(
        self,
        *,
        entity: str,
        utilization_pct: float | None = None,
        annual_revenue_run_rate_usd: float | None = None,
        annual_power_cost_usd: float | None = None,
        annual_debt_service_usd: float | None = None,
        debt_service_coverage_ratio: float | None = None,
    ) -> None:
        self.entity = entity
        self.utilization_pct = utilization_pct
        self.annual_revenue_run_rate_usd = annual_revenue_run_rate_usd
        self.contracted_revenue_usd = None
        self.annual_power_cost_usd = annual_power_cost_usd
        self.annual_debt_service_usd = annual_debt_service_usd
        self.debt_service_coverage_ratio = debt_service_coverage_ratio


def _mismatch_ratios(cases: list[Any]) -> dict[str, Any]:
    return compute_burry_mismatch_ratios(
        debt_service_metrics=object(),
        compute_metrics=object(),
        physical_capacity=object(),
        queue_match_summary={},
        physical_record_match_summary={},
        resolved_data_dirs=[],
        payback_cases=cases,
    )


def test_cash_flow_mismatch_blocks_and_names_missing_inputs_when_unbacked() -> None:
    # Cases lack the per-case debt service + utilization a DSCR needs.
    cases = [
        _PaybackCase(entity="WhiteFiber, Inc.", annual_revenue_run_rate_usd=9_696_000.0),
    ]

    ratios = _mismatch_ratios(cases)
    cf = ratios["cash_flow_mismatch"]

    assert cf["status"] == "blocked_missing_source_backed_inputs"
    assert cf["source_backed"] is False
    assert cf["cases_scanned"] == 1
    assert "annual_debt_service" in cf["missing_inputs"]
    assert "utilization_pct" in cf["missing_inputs"]
    # The stress example must not masquerade as source-backed coverage.
    sse = ratios["scenario_stress_examples"]
    assert sse["base_dscr_source_backed"] is False
    assert sse["illustrative_only"] is True
    assert "ILLUSTRATIVE ONLY" in sse["note"]


def test_cash_flow_mismatch_is_source_backed_with_full_inputs() -> None:
    cases = [
        _PaybackCase(
            entity="CoreWeave",
            utilization_pct=0.75,
            annual_revenue_run_rate_usd=1_000_000_000.0,
            annual_power_cost_usd=100_000_000.0,
            annual_debt_service_usd=500_000_000.0,
            debt_service_coverage_ratio=1.1,
        ),
    ]

    ratios = _mismatch_ratios(cases)
    cf = ratios["cash_flow_mismatch"]
    sse = ratios["scenario_stress_examples"]

    assert cf["source_backed"] is True
    assert cf["cases_with_utilization_data"] == 1
    assert "dscr_at_realistic_util" in cf["example_cases"][0]
    assert sse["base_dscr_source_backed"] is True
    assert "illustrative_only" not in sse
    assert "SOURCE-BACKED" in sse["note"]


def test_physical_mismatch_reports_honest_tracker_proxy_not_join_artifact(tmp_path) -> None:
    phys = tmp_path / "physical"
    phys.mkdir(parents=True)
    (phys / "projects.csv").write_text(
        "project_id,capacity_mw,construction_status,permit_status\n"
        "p1,100,in_service,in_service\n"
        "p2,300,under_construction,not_confirmed\n"
        "p3,600,announced,not_confirmed\n"
    )
    (phys / "queue_project_matches.csv").write_text(
        "matched_project_id,match_status,match_confidence\n"
    )
    # Fully-ingested ISO queue records (generation-side), incl. a PJM row.
    src_rows = tmp_path / "source_acquisition" / "source_rows"
    src_rows.mkdir(parents=True)
    (src_rows / "queue_records.csv").write_text(
        "source_id,region\n"
        "pjm-planning-queues-xml,pjm\n"
        "nyiso-interconnection-queue,nyiso\n"
        "ercot-gis-report,ercot\n"
    )

    ratios = compute_burry_mismatch_ratios(
        debt_service_metrics=object(),
        compute_metrics=object(),
        physical_capacity=object(),
        queue_match_summary={"data_center_queue_rows": 26, "matched_rows": 9},
        physical_record_match_summary={},
        resolved_data_dirs=[str(tmp_path)],
        payback_cases=[],
    )
    pm = ratios["physical_mismatch"]

    # The misleading "deliverable" join metric is gone; honest proxy is present.
    assert "deliverable_vs_announced_strong_queue_match_pct" not in pm
    # Corrected framing: queues ARE ingested; the gap is generation-vs-load, not parsing.
    assert pm["queue_match_status"] == "weak_lens_generation_queue_not_data_center_load"
    assert pm["in_service_mw_pct"] == 10.0  # 100 / 1000
    assert pm["under_construction_mw_pct"] == 30.0  # 300 / 1000
    assert pm["announced_only_mw_pct"] == 60.0  # 600 / 1000
    assert pm["permit_not_confirmed_mw_pct"] == 90.0  # (300 + 600) / 1000
    assert pm["iso_queue_records_ingested"] == 3
    assert pm["data_center_related_queue_records"] == 26
    assert "pjm" in pm["iso_queue_records_by_source"]
    assert "un-ingested" not in pm["note"].lower()
    assert "non_primary" in pm["deliverability_proxy_source"]
