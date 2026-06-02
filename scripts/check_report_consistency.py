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
import json
import sys
from pathlib import Path
from typing import Any

from bubble.quality.report_consistency import (
    build_expectations,
    check_invariant_audit_status,
    check_labeled_counts,
    check_metric_total_agreement,
    check_report_path_freshness,
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

    findings = []
    findings.extend(check_invariant_audit_status(invariant_audit))
    findings.extend(check_metric_total_agreement(report=report, decision_summary=decision_summary))
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
