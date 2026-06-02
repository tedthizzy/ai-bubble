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
