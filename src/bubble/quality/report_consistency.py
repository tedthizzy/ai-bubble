"""Read-only consistency checks between generated reports and the docs/metrics
that cite them.

This module is intentionally side-effect free: it never rebuilds reports, never
writes shared artifacts, and only reads text that callers hand to it. The CLI
wrapper (`scripts/check_report_consistency.py`) wires the real file locations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

_REPORT_STEM_RE = re.compile(r"BURRY_REPORT_EvidenceGated_\d{8}-\d{4}")


@dataclass(frozen=True)
class CountExpectation:
    """An authoritative number plus the doc regex (one capture group) that should
    state the same value."""

    key: str
    pattern: str
    authoritative: float


@dataclass(frozen=True)
class ConsistencyFinding:
    """One detected inconsistency between a report/metric source and a doc."""

    check: str
    severity: str  # "error" | "warning"
    doc: str
    message: str
    expected: str | None = None
    actual: str | None = None


def build_expectations(
    *,
    report: dict[str, Any],
    decision_summary: dict[str, Any],
    invariant_audit: dict[str, Any],
) -> list[CountExpectation]:
    """Map authoritative values from the summary JSONs to the doc regexes that
    should state them.

    Patterns use ``\\s+`` between words so they match line-wrapped prose. Money
    is normalized to trillions (3 dp) because the docs cite ``$N.NNNT``.
    """

    exps: list[CountExpectation] = _report_expectations(report)

    ia = invariant_audit
    if ia.get("files_scanned") is not None:
        exps.append(
            CountExpectation(
                "invariant.files_scanned", r"([\d][\d,]*)\s+CSV files", ia["files_scanned"]
            )
        )
    if ia.get("rows_scanned") is not None:
        exps.append(
            CountExpectation("invariant.rows_scanned", r"([\d][\d,]*)\s+rows", ia["rows_scanned"])
        )

    ds = decision_summary
    if ds.get("decisions") is not None:
        exps.append(
            CountExpectation("decisions.total", r"([\d][\d,]*)\s+decisions", ds["decisions"])
        )
    if ds.get("supported_as_material_blocker") is not None:
        exps.append(
            CountExpectation(
                "decisions.supported_as_material_blocker",
                r"([\d][\d,]*)\s+supported(?:\s+as\s+material)?\s+blockers",
                ds["supported_as_material_blocker"],
            )
        )
    if ds.get("needs_deeper_extraction") is not None:
        exps.append(
            CountExpectation(
                "decisions.needs_deeper_extraction",
                r"([\d][\d,]*)\s+(?:still\s+)?requiring deeper\s+extraction",
                ds["needs_deeper_extraction"],
            )
        )
    if ds.get("approved_for_metric_use") is not None:
        exps.append(
            CountExpectation(
                "decisions.approved_for_metric_use",
                r"([\d][\d,]*)\s+(?:source-backed rows\s+approved|approved\s+metric rows)",
                ds["approved_for_metric_use"],
            )
        )
    if ds.get("final_metric_group_count") is not None:
        exps.append(
            CountExpectation(
                "decisions.final_metric_group_count",
                r"([\d][\d,]*)\s+(?:latest-snapshot\s+)?metric groups",
                ds["final_metric_group_count"],
            )
        )
    if ds.get("final_metric_supported_amount_usd") is not None:
        exps.append(
            CountExpectation(
                "decisions.final_metric_supported_usd_trillions",
                r"\$([\d.]+)T\s+deduped final metric support",
                _trillions(ds["final_metric_supported_amount_usd"]),
            )
        )

    return exps


def _report_expectations(report: dict[str, Any]) -> list[CountExpectation]:
    exps: list[CountExpectation] = []
    key_metrics = report.get("key_metrics", {})
    evidence_summary = report.get("evidence_quality", {}).get("summary", {})
    audited_claims = evidence_summary.get("audited_claims")
    if audited_claims is not None:
        exps.append(
            CountExpectation(
                "report.audited_claims",
                r"Evidence audit coverage(?::| now includes)?\s*([\d,]+)\s+claim audits",
                audited_claims,
            )
        )
    final_metric_usd = key_metrics.get("materiality_adjudication_final_metric_supported_amount_usd")
    if final_metric_usd is not None:
        exps.append(
            CountExpectation(
                "report.final_metric_supported_usd_trillions",
                r"\$([\d.]+)T\s+deduped final metric support",
                _trillions(final_metric_usd),
            )
        )
    final_metric_group_count = key_metrics.get("materiality_adjudication_final_metric_group_count")
    if final_metric_group_count is not None:
        exps.append(
            CountExpectation(
                "report.final_metric_group_count",
                (
                    r"deduped final metric support across\s+([\d,]+)\s+"
                    r"(?:[A-Za-z0-9_/-]+\s+)*metric"
                ),
                final_metric_group_count,
            )
        )
    established_ai_usd = key_metrics.get("materiality_relevance_established_ai_linked_usd")
    if established_ai_usd is not None:
        exps.append(
            CountExpectation(
                "report.established_ai_linked_usd_trillions",
                (
                    r"\$([\d.]+)T(?:\s+established\s+direct/watchlist|"
                    r"\s+on\s+the\s+same\s+[\d,]+-group)"
                ),
                _trillions(established_ai_usd),
            )
        )
    not_established_pct = key_metrics.get("materiality_relevance_not_established_linkage_pct")
    if not_established_pct is not None:
        exps.append(
            CountExpectation(
                "report.not_established_linkage_pct",
                (
                    r"([\d.]+)%\s+remains(?:\s+source-backed\s+but)?\s+"
                    r"(?:not[- ]established|not yet thesis-linked)"
                ),
                _display_pct(float(not_established_pct)),
            )
        )
    _append_key_metric_count(
        exps,
        key="report.compute_gpu_depreciation_blocked_generation_count",
        key_metrics=key_metrics,
        metric_name="compute_gpu_depreciation_blocked_generation_count",
        pattern=(
            r"(?:([\d,]+)\s+GPU\s+generations\s+(?:lack|missing)|"
            r"GPU\s+generations\s+missing\s+comparable\s+depreciation\s+inputs:\s*([\d,]+))"
        ),
    )
    _append_key_metric_count(
        exps,
        key="report.compute_tam_blocked_claim_count",
        key_metrics=key_metrics,
        metric_name="compute_tam_blocked_claim_count",
        pattern=(
            r"(?:([\d,]+)\s+TAM\s+claims\s+(?:lack|missing)|"
            r"TAM\s+claims\s+missing\s+realized-revenue\s+comparators:\s*([\d,]+))"
        ),
    )
    _append_key_metric_count(
        exps,
        key="report.compute_payback_blocked_case_count",
        key_metrics=key_metrics,
        metric_name="compute_payback_blocked_case_count",
        pattern=(
            r"(?:([\d,]+)\s+(?:is\s+)?blocked by missing cash-flow|"
            r"Payback\s+cases\s+blocked\s+by\s+missing\s+cash-flow\s+inputs:\s*([\d,]+))"
        ),
    )
    _append_key_metric_count(
        exps,
        key="report.compute_payback_missing_debt_service_count",
        key_metrics=key_metrics,
        metric_name="compute_payback_missing_debt_service_count",
        pattern=(
            r"(?:([\d,]+)\s+(?:are\s+missing|lack)\s+debt-service|"
            r"Payback\s+cases\s+missing\s+debt-service\s+coverage\s+inputs:\s*([\d,]+))"
        ),
    )
    _append_key_metric_count(
        exps,
        key="report.compute_eps_blocked_impact_count",
        key_metrics=key_metrics,
        metric_name="compute_eps_blocked_impact_count",
        pattern=(
            r"(?:([\d,]+)\s+EPS\s+impacts\s+(?:lack|missing)|"
            r"EPS\s+impacts\s+missing\s+modeled\s+economic\s+depreciation:\s*([\d,]+))"
        ),
    )
    _append_key_metric_count(
        exps,
        key="report.compute_chip_supply_blocked_observation_count",
        key_metrics=key_metrics,
        metric_name="compute_chip_supply_blocked_observation_count",
        pattern=(
            r"(?:([\d,]+)\s+[Cc]hip[- ]supply\s+observations\s+(?:lack|missing)|"
            r"Chip\s+supply\s+observations\s+missing\s+delivered-count\s+comparators:\s*"
            r"([\d,]+))"
        ),
    )
    return exps


def _append_key_metric_count(
    expectations: list[CountExpectation],
    *,
    key: str,
    key_metrics: dict[str, Any],
    metric_name: str,
    pattern: str,
) -> None:
    value = key_metrics.get(metric_name)
    if value is None:
        return
    expectations.append(CountExpectation(key, pattern, float(value)))


def _trillions(value: float) -> float:
    return round(float(value) / 1e12, 3)


def _display_pct(value: float) -> float:
    return round(value * 100 if value <= 1 else value, 1)


def latest_report_stem(report_dir: Path) -> str | None:
    """Return the newest ``BURRY_REPORT_EvidenceGated_<ts>`` stem in report_dir.

    Filenames carry zero-padded ``YYYYMMDD-HHMM`` timestamps, so lexical max is
    chronological max.
    """

    stems = sorted(p.stem for p in report_dir.glob("BURRY_REPORT_EvidenceGated_*.json"))
    return stems[-1] if stems else None


def check_report_path_freshness(
    *,
    doc_text: str,
    doc_name: str,
    latest_stem: str,
) -> list[ConsistencyFinding]:
    """Flag references to a non-latest BURRY report stem in a doc.

    Each distinct stale stem produces one finding, even when the doc cites both
    the `.md` and `.json` for it.
    """

    findings: list[ConsistencyFinding] = []
    seen: set[str] = set()
    for match in _REPORT_STEM_RE.finditer(doc_text):
        stem = match.group(0)
        if stem == latest_stem or stem in seen:
            continue
        seen.add(stem)
        findings.append(
            ConsistencyFinding(
                check="stale_report_path",
                severity="error",
                doc=doc_name,
                message=(
                    f"{doc_name} references report {stem}, "
                    f"but the latest report on disk is {latest_stem}."
                ),
                expected=latest_stem,
                actual=stem,
            )
        )
    return findings


def check_labeled_counts(
    *,
    doc_text: str,
    doc_name: str,
    expectations: list[CountExpectation],
) -> list[ConsistencyFinding]:
    """Compare authoritative numbers against the values a doc states for them.

    A drifted value is an ``error``; a label that no longer matches (the doc was
    reworded) is a ``warning`` so silent non-checks are visible.
    """

    findings: list[ConsistencyFinding] = []
    for exp in expectations:
        match = re.search(exp.pattern, doc_text)
        if match is None:
            findings.append(
                ConsistencyFinding(
                    check="count_label_missing",
                    severity="warning",
                    doc=doc_name,
                    message=(
                        f"Could not locate the '{exp.key}' figure in {doc_name}; "
                        "the doc may have been reworded — this check did not run."
                    ),
                    expected=_format_number(exp.authoritative),
                    actual=None,
                )
            )
            continue
        stated_raw = next(group for group in match.groups() if group and group.strip())
        if _parse_number(stated_raw) != float(exp.authoritative):
            findings.append(
                ConsistencyFinding(
                    check="stale_count",
                    severity="error",
                    doc=doc_name,
                    message=(
                        f"{doc_name} states {exp.key} = {stated_raw}, but the "
                        f"authoritative value is {_format_number(exp.authoritative)}."
                    ),
                    expected=_format_number(exp.authoritative),
                    actual=stated_raw,
                )
            )
    return findings


_HCF_RE = re.compile(r"high[_ -]?confidence[_ -]?final[:*\s]+(true|false)", re.IGNORECASE)
_BUBBLE_PCT_RE = re.compile(r"bubble[_ -]?confidence[^0-9]{0,20}?([0-9]{1,3})\s*%", re.IGNORECASE)


def check_confidence_flags(
    *,
    high_confidence_final: bool,
    bubble_confidence: float,
    doc_text: str,
    doc_name: str,
) -> list[ConsistencyFinding]:
    """Flag a doc whose stated high_confidence_final / bubble_confidence disagrees
    with the latest report's actual values."""

    findings: list[ConsistencyFinding] = []
    hcf_match = _HCF_RE.search(doc_text)
    if hcf_match:
        stated = hcf_match.group(1).lower() == "true"
        if stated != high_confidence_final:
            findings.append(
                ConsistencyFinding(
                    check="stale_high_confidence_final",
                    severity="error",
                    doc=doc_name,
                    message=(
                        f"{doc_name} states high_confidence_final={stated}, but the "
                        f"latest report is {high_confidence_final}."
                    ),
                    expected=str(high_confidence_final),
                    actual=str(stated),
                )
            )
    bubble_match = _BUBBLE_PCT_RE.search(doc_text)
    if bubble_match:
        stated_pct = int(bubble_match.group(1))
        actual_pct = round(bubble_confidence * 100)
        if stated_pct != actual_pct:
            findings.append(
                ConsistencyFinding(
                    check="stale_bubble_confidence",
                    severity="error",
                    doc=doc_name,
                    message=(
                        f"{doc_name} states bubble confidence {stated_pct}%, but the "
                        f"latest report is {actual_pct}%."
                    ),
                    expected=f"{actual_pct}%",
                    actual=f"{stated_pct}%",
                )
            )
    return findings


_TIMESTAMP_RE = re.compile(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})")


def check_summary_csv_counts(
    checks: list[tuple[str, int | None, int | None]],
) -> list[ConsistencyFinding]:
    """Flag a summary-JSON count that disagrees with its source CSV row count.

    ``checks`` is a list of ``(label, summary_count, csv_row_count)``. Warning-level
    (counts can transiently diverge mid-rebuild). Addresses "summary CSV/JSON
    mismatches" / "stale materiality packet/decision mismatches"."""

    findings: list[ConsistencyFinding] = []
    for label, summary_count, csv_count in checks:
        if summary_count is None or csv_count is None:
            continue
        if int(summary_count) != int(csv_count):
            findings.append(
                ConsistencyFinding(
                    check="summary_csv_count_mismatch",
                    severity="warning",
                    doc=label,
                    message=(
                        f"{label}: summary count {summary_count} disagrees with the source "
                        f"CSV ({csv_count} rows) — one was regenerated without the other."
                    ),
                    expected=str(summary_count),
                    actual=str(csv_count),
                )
            )
    return findings


def check_artifact_freshness(
    mtimes: dict[str, float],
    *,
    dependencies: list[tuple[str, str]],
) -> list[ConsistencyFinding]:
    """Flag a generated artifact older than an artifact it is built from.

    ``dependencies`` is a list of ``(dependent, dependency)`` pairs; the dependent
    should be at least as new as its dependency (built after it). Warning-level —
    artifact mtimes are noisy across rebuilds. Addresses "generated artifacts older
    than their dependencies / stale graph-report mismatches"."""

    findings: list[ConsistencyFinding] = []
    for dependent, dependency in dependencies:
        if dependent not in mtimes or dependency not in mtimes:
            continue
        if mtimes[dependent] < mtimes[dependency]:
            findings.append(
                ConsistencyFinding(
                    check="stale_artifact",
                    severity="warning",
                    doc=dependent,
                    message=(
                        f"{dependent} is older than its dependency {dependency} — it was "
                        "built from a stale input; regenerate it."
                    ),
                    expected=f"newer than {dependency}",
                    actual=f"older than {dependency}",
                )
            )
    return findings


def check_metric_audit_coverage(
    report: dict[str, Any],
    *,
    threshold: float = 100e9,
) -> list[ConsistencyFinding]:
    """Flag high-impact USD metrics shown in ``burry_question_answers`` that have
    no matching EvidenceGate audit (warning — surfaces audit-coverage gaps)."""

    audited_values: set[float] = set()
    for audit in report.get("evidence_quality", {}).get("claim_audits", []):
        value = audit.get("value")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            audited_values.add(float(value))

    findings: list[ConsistencyFinding] = []
    seen: set[str] = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and "usd" in key.lower()
                    and float(value) > threshold
                    and float(value) not in audited_values
                    and key not in seen
                ):
                    seen.add(key)
                    findings.append(
                        ConsistencyFinding(
                            check="unaudited_high_impact_metric",
                            severity="warning",
                            doc="report",
                            message=(
                                f"{key} = ${float(value) / 1e9:.1f}B is shown in "
                                "burry_question_answers with no matching EvidenceGate audit."
                            ),
                            expected="an EvidenceGate claim_audit",
                            actual=None,
                        )
                    )
                walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(report.get("burry_question_answers", {}))
    return findings


def check_timestamp_freshness(
    *,
    doc_text: str,
    doc_name: str,
    label: str,
    authoritative_iso: str,
) -> list[ConsistencyFinding]:
    """Warn when the timestamp a doc states near ``label`` is older than the
    authoritative source timestamp. Warning-level (timestamps can be noisy)."""

    index = doc_text.find(label)
    if index == -1:
        return []
    doc_match = _TIMESTAMP_RE.search(doc_text[index : index + 200])
    auth_match = _TIMESTAMP_RE.search(authoritative_iso)
    if not doc_match or not auth_match:
        return []
    doc_stamp = f"{doc_match.group(1)} {doc_match.group(2)}"
    auth_stamp = f"{auth_match.group(1)} {auth_match.group(2)}"
    if doc_stamp < auth_stamp:  # lexical order == chronological for this format
        return [
            ConsistencyFinding(
                check="stale_timestamp",
                severity="warning",
                doc=doc_name,
                message=(
                    f"{doc_name} states the {label} timestamp as {doc_stamp}, but the "
                    f"authoritative source is {auth_stamp}."
                ),
                expected=auth_stamp,
                actual=doc_stamp,
            )
        ]
    return []


def check_invariant_audit_status(invariant_audit: dict[str, Any]) -> list[ConsistencyFinding]:
    """Flag a source-invariant audit that is missing, not passing, or has
    violations — the provenance gate must be green before any report is trusted."""

    if not invariant_audit:
        return [
            ConsistencyFinding(
                check="invariant_audit_missing",
                severity="error",
                doc="source_invariant_audit.json",
                message="Source-invariant audit JSON is missing or empty.",
            )
        ]

    findings: list[ConsistencyFinding] = []
    if invariant_audit.get("passed") is not True:
        findings.append(
            ConsistencyFinding(
                check="invariant_audit_not_passing",
                severity="error",
                doc="source_invariant_audit.json",
                message=(
                    "Source-invariant audit 'passed' flag is "
                    f"{invariant_audit.get('passed')!r} (expected True)."
                ),
                expected="True",
                actual=repr(invariant_audit.get("passed")),
            )
        )
    violation_count = invariant_audit.get("violation_count", 0) or 0
    if violation_count:
        findings.append(
            ConsistencyFinding(
                check="invariant_audit_violations",
                severity="error",
                doc="source_invariant_audit.json",
                message=f"Source-invariant audit reports {violation_count} violation(s).",
                expected="0",
                actual=str(violation_count),
            )
        )
    return findings


def check_metric_total_agreement(
    *,
    report: dict[str, Any],
    decision_summary: dict[str, Any],
) -> list[ConsistencyFinding]:
    """Flag when the latest report's embedded final metric total disagrees with
    the standalone decision summary (i.e. report built from a stale summary)."""

    report_total = report.get("materiality_adjudication_decisions", {}).get(
        "final_metric_supported_amount_usd"
    )
    summary_total = decision_summary.get("final_metric_supported_amount_usd")
    if report_total is None or summary_total is None:
        return []
    if float(report_total) != float(summary_total):
        return [
            ConsistencyFinding(
                check="metric_total_mismatch",
                severity="error",
                doc="report_vs_decision_summary",
                message=(
                    "Latest report's final metric support disagrees with the "
                    "decision summary; the report may be built from a stale summary."
                ),
                expected=_format_number(summary_total),
                actual=_format_number(report_total),
            )
        ]
    return []


def _parse_number(raw: str) -> float:
    return float(raw.replace(",", "").replace("$", "").strip())


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,}"
