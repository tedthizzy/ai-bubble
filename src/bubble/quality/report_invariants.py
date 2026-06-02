"""Internal consistency checks for generated Burry reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReportInvariant:
    """A single arithmetic/report relationship check."""

    name: str
    ok: bool | None
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "ok": self.ok, "detail": self.detail}


def check_report_invariants(
    report: dict[str, Any],
    decision_summary: dict[str, Any] | None = None,
) -> list[ReportInvariant]:
    """Check report arithmetic relationships that should always hold.

    These invariants do not prove that a source number is correct. They catch
    internal report regressions where a subset exceeds its superset, a deduped
    metric exceeds its raw input, or a grouped count exceeds its source rows.
    """

    decision_summary = decision_summary or {}
    key_metrics = _dict(report.get("key_metrics"))

    figures = {
        "capital_distinct_debt_like_notional_usd": _num(
            key_metrics.get("capital_distinct_debt_like_notional_usd")
        ),
        "capital_debt_like_notional_usd": _num(
            key_metrics.get("capital_debt_like_notional_usd")
        ),
        "capital_total_notional_usd": _num(key_metrics.get("capital_total_notional_usd")),
        "materiality_final_metric_supported_amount_usd": _num(
            key_metrics.get("materiality_adjudication_final_metric_supported_amount_usd")
            or decision_summary.get("final_metric_supported_amount_usd")
        ),
        "materiality_approved_row_supported_amount_usd": _num(
            key_metrics.get("materiality_adjudication_approved_row_supported_amount_usd")
            or decision_summary.get("approved_row_supported_amount_usd")
        ),
        "materiality_final_metric_group_count": _num(
            key_metrics.get("materiality_adjudication_final_metric_group_count")
            or decision_summary.get("final_metric_group_count")
        ),
        "materiality_approved_for_metric_use": _num(
            key_metrics.get("materiality_adjudication_approved_for_metric_use")
            or decision_summary.get("approved_for_metric_use")
        ),
        "materiality_decisions": _num(
            key_metrics.get("materiality_adjudication_decisions")
            or decision_summary.get("decisions")
        ),
        "timing_ai_infra_capital_refinancing_usd_2024_2030": _num(
            key_metrics.get("timing_signal_ai_infra_capital_refinancing_usd_2024_2030")
        ),
        "timing_capital_refinancing_usd_2024_2030": _num(
            key_metrics.get("timing_signal_capital_refinancing_usd_2024_2030")
        ),
        "timing_capital_refinancing_forward_from_as_of_usd": _num(
            key_metrics.get("timing_signal_capital_refinancing_forward_from_as_of_usd")
        ),
        "timing_ai_infra_capital_refinancing_forward_from_as_of_usd": _num(
            key_metrics.get(
                "timing_signal_ai_infra_capital_refinancing_forward_from_as_of_usd"
            )
        ),
        "tracker_distinct_capacity_high_mw": _num(
            key_metrics.get("tracker_distinct_capacity_high_mw")
        ),
        "tracker_capacity_high_mw": _num(key_metrics.get("tracker_capacity_high_mw")),
    }

    checks = [
        _le(
            "capital distinct debt-like notional <= debt-like notional",
            figures["capital_distinct_debt_like_notional_usd"],
            figures["capital_debt_like_notional_usd"],
        ),
        _le(
            "capital debt-like notional <= total capital notional",
            figures["capital_debt_like_notional_usd"],
            figures["capital_total_notional_usd"],
        ),
        _le(
            "materiality final metric <= approved row supported amount",
            figures["materiality_final_metric_supported_amount_usd"],
            figures["materiality_approved_row_supported_amount_usd"],
        ),
        _le(
            "materiality final metric groups <= approved metric rows",
            figures["materiality_final_metric_group_count"],
            figures["materiality_approved_for_metric_use"],
        ),
        _le(
            "approved metric rows <= materiality decisions",
            figures["materiality_approved_for_metric_use"],
            figures["materiality_decisions"],
        ),
        _le(
            "AI-infra timing wall <= total timing wall",
            figures["timing_ai_infra_capital_refinancing_usd_2024_2030"],
            figures["timing_capital_refinancing_usd_2024_2030"],
        ),
        _le(
            "forward timing wall <= total timing wall",
            figures["timing_capital_refinancing_forward_from_as_of_usd"],
            figures["timing_capital_refinancing_usd_2024_2030"],
        ),
        _le(
            "AI-infra forward timing wall <= forward timing wall",
            figures["timing_ai_infra_capital_refinancing_forward_from_as_of_usd"],
            figures["timing_capital_refinancing_forward_from_as_of_usd"],
        ),
        _le(
            "AI-infra forward timing wall <= AI-infra timing wall",
            figures["timing_ai_infra_capital_refinancing_forward_from_as_of_usd"],
            figures["timing_ai_infra_capital_refinancing_usd_2024_2030"],
        ),
        _le(
            "tracker distinct capacity <= raw tracker capacity",
            figures["tracker_distinct_capacity_high_mw"],
            figures["tracker_capacity_high_mw"],
        ),
    ]
    return checks


def report_invariant_violations(
    report: dict[str, Any],
    decision_summary: dict[str, Any] | None = None,
) -> list[ReportInvariant]:
    return [
        invariant
        for invariant in check_report_invariants(report, decision_summary)
        if invariant.ok is False
    ]


def _le(name: str, smaller: float | None, larger: float | None) -> ReportInvariant:
    if smaller is None or larger is None:
        return ReportInvariant(name=name, ok=None, detail=f"{smaller=} <= {larger=}")
    return ReportInvariant(
        name=name,
        ok=smaller <= larger + 1e-6,
        detail=f"{smaller:,.2f} <= {larger:,.2f}",
    )


def _num(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
