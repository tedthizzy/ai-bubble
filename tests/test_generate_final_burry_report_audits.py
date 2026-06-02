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


def _audit(
    claim_id: str,
    value: object,
    *,
    tier: str = "measured",
    confidence: float = 0.9,
    eligible: bool = True,
) -> dict[str, object]:
    return {
        "claim_id": claim_id,
        "claim": claim_id,
        "value": value,
        "unit": "USD",
        "tier": tier,
        "confidence": confidence,
        "source_count": 1,
        "source_types": ["sec_edgar"],
        "sources": [],
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
            "claim_audits": [
                _audit("debt_service.missing_rate_notional", 689_881_283_165.74)
            ]
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


def test_merged_scalar_audit_clears_high_impact_metric_warning() -> None:
    report = {
        "evidence_quality": {
            "claim_audits": merge_evidence_audits(
                [],
                {
                    "claim_audits": [
                        _audit("capital.debt_like_notional", 1_200_000_000_000)
                    ]
                },
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
    )
    report = {
        "evidence_quality": {"claim_audits": audits},
        "burry_question_answers": {
            "when_cracks": {
                "current_timing_capital_refinancing_usd_2024_2030": (
                    5_756_305_034_829.88
                ),
                "current_timing_ai_infra_capital_refinancing_usd_2024_2030": (
                    292_289_419_740.72
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
                "top_distinct_capital_review_queue_items": [
                    {"notional_amount_usd": 734_000_000_000}
                ]
            },
        },
    }

    assert check_metric_audit_coverage(report, threshold=100e9) == []
