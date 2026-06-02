#!/usr/bin/env python
"""Read-only consistency verifier for the evidence-gated report + its docs.

Compares the latest ``BURRY_REPORT_EvidenceGated_*`` on disk and the canonical
summary JSONs (source-invariant audit, materiality adjudication decision
summary) against the prose metrics/paths cited in ``docs/acquisition_status.md``
and ``FINAL_DELIVERY.md``.

It NEVER regenerates reports or writes any artifact — it only reads. Exit code is
non-zero when any error-severity drift is found, so it can gate a doc refresh.

Run against another checkout's live data (the artifacts live in the main
checkout, since ``data/`` is gitignored)::

    PYTHONPATH=src uv run scripts/check_report_consistency.py \
        --repo-root /Users/ted/Documents/dev-archive/bubble
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

from bubble.quality.report_consistency import (
    build_expectations,
    check_artifact_freshness,
    check_confidence_flags,
    check_invariant_audit_status,
    check_labeled_counts,
    check_metric_audit_coverage,
    check_metric_total_agreement,
    check_report_path_freshness,
    check_summary_csv_counts,
    check_timestamp_freshness,
    latest_report_stem,
)

DOC_RELATIVE_PATHS = ("docs/acquisition_status.md", "FINAL_DELIVERY.md")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _artifact_freshness_findings(report_dir: Path, root: Path, latest_stem: str) -> list[Any]:
    artifact_paths = {
        "latest report": report_dir / f"{latest_stem}.json",
        "decision_summary": report_dir / "materiality_adjudication_decision_summary.json",
        "invariant_audit": report_dir / "source_invariant_audit.json",
        "capital_exposure_graph_summary": report_dir / "capital_exposure_graph_summary.json",
        "contract_contagion_summary": report_dir / "contract_contagion_summary.json",
        "timing_signal_summary": report_dir / "timing_signal_summary.json",
        "decisions_csv": report_dir / "materiality_adjudication_decisions.csv",
        "deals_csv": root / "data" / "edgar_acquisition" / "deals.csv",
    }
    mtimes = {name: p.stat().st_mtime for name, p in artifact_paths.items() if p.exists()}
    return check_artifact_freshness(
        mtimes,
        dependencies=[
            ("latest report", "decision_summary"),
            ("latest report", "invariant_audit"),
            ("latest report", "capital_exposure_graph_summary"),
            ("latest report", "contract_contagion_summary"),
            ("latest report", "timing_signal_summary"),
            ("decision_summary", "decisions_csv"),
            ("capital_exposure_graph_summary", "deals_csv"),
        ],
    )


def _summary_csv_findings(report_dir: Path, decision_summary: dict[str, Any]) -> list[Any]:
    decisions_csv = report_dir / "materiality_adjudication_decisions.csv"
    if not (decisions_csv.exists() and decision_summary):
        return []
    with decisions_csv.open() as handle:
        decision_rows = list(csv.DictReader(handle))
    approved = sum(
        1 for r in decision_rows if r.get("metric_use_status") == "approved_for_metric_use"
    )
    return check_summary_csv_counts(
        [
            ("decisions", decision_summary.get("decisions"), len(decision_rows)),
            ("approved_for_metric_use", decision_summary.get("approved_for_metric_use"), approved),
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Checkout whose data/reports + docs to verify (default: this checkout).",
    )
    args = parser.parse_args()
    root: Path = args.repo_root
    report_dir = root / "data" / "reports"

    print(f"Report consistency check (repo-root: {root})")

    latest_stem = latest_report_stem(report_dir)
    if latest_stem is None:
        print(f"  No BURRY_REPORT_EvidenceGated_*.json found under {report_dir}.")
        print("  Nothing to verify (point --repo-root at the checkout that holds data/).")
        return 0
    print(f"  Latest report on disk: {latest_stem}")

    decision_summary = _load_json(report_dir / "materiality_adjudication_decision_summary.json")
    invariant_audit = _load_json(report_dir / "source_invariant_audit.json")
    report = _load_json(report_dir / f"{latest_stem}.json")

    expectations = build_expectations(
        report=report,
        decision_summary=decision_summary,
        invariant_audit=invariant_audit,
    )

    high_confidence_final = report.get("metadata", {}).get("high_confidence_final")
    bubble_confidence = report.get("executive_summary", {}).get("bubble_confidence")

    findings = []
    findings.extend(check_invariant_audit_status(invariant_audit))
    findings.extend(check_metric_total_agreement(report=report, decision_summary=decision_summary))
    findings.extend(check_metric_audit_coverage(report))

    findings.extend(_artifact_freshness_findings(report_dir, root, latest_stem))
    findings.extend(_summary_csv_findings(report_dir, decision_summary))

    for rel in DOC_RELATIVE_PATHS:
        doc_path = root / rel
        if not doc_path.exists():
            print(f"  (skipped — not found: {rel})")
            continue
        doc_text = doc_path.read_text()
        findings.extend(
            check_report_path_freshness(doc_text=doc_text, doc_name=rel, latest_stem=latest_stem)
        )
        findings.extend(
            check_labeled_counts(doc_text=doc_text, doc_name=rel, expectations=expectations)
        )
        if isinstance(high_confidence_final, bool) and isinstance(bubble_confidence, int | float):
            findings.extend(
                check_confidence_flags(
                    high_confidence_final=high_confidence_final,
                    bubble_confidence=float(bubble_confidence),
                    doc_text=doc_text,
                    doc_name=rel,
                )
            )
        if invariant_audit.get("generated_at"):
            findings.extend(
                check_timestamp_freshness(
                    doc_text=doc_text,
                    doc_name=rel,
                    label="Source invariant audit",
                    authoritative_iso=str(invariant_audit["generated_at"]),
                )
            )

    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]

    for finding in errors:
        scope = f" [{finding.check}]"
        print(f"\nERROR {finding.doc}{scope}")
        print(f"  {finding.message}")
        if finding.expected is not None or finding.actual is not None:
            print(f"  expected={finding.expected!r} actual={finding.actual!r}")

    if warnings:
        print(f"\n{len(warnings)} warning(s) (label not found — check did not run):")
        for finding in warnings:
            print(f"  - {finding.doc}: {finding.message}")

    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
