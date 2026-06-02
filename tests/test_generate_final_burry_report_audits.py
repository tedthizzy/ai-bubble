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
            "top_distinct_capital_items": [
                {
                    **source_row,
                    "review_id": "review:test",
                    "notional_amount_usd": 734_000_000_000,
                }
            ]
        },
        weak_link_summary={"top_weak_links": [], "top_debt_service_weak_links": []},
        debt_service_metrics_dict={},
        capital_exposure_graph_summary={},
        contract_contagion_summary={},
        materiality_adjudication_decision_summary={
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
