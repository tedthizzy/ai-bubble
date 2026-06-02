#!/usr/bin/env python3
"""Check arithmetic invariants inside the latest evidence-gated report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bubble.quality.report_invariants import check_report_invariants


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports-dir", default="data/reports")
    parser.add_argument("--report", help="Specific report JSON path. Defaults to latest.")
    parser.add_argument("--strict", action="store_true", help="Exit nonzero on violations.")
    args = parser.parse_args()

    reports_dir = Path(args.reports_dir)
    report_path = Path(args.report) if args.report else _latest_report(reports_dir)
    if report_path is None:
        raise SystemExit(f"No BURRY_REPORT_EvidenceGated_*.json found in {reports_dir}")

    report = _load_json(report_path)
    decision_summary = _load_json(
        reports_dir / "materiality_adjudication_decision_summary.json"
    )
    invariants = check_report_invariants(report, decision_summary)
    violations = [invariant for invariant in invariants if invariant.ok is False]

    print(f"Report invariant check: {report_path.name}")
    for invariant in invariants:
        status = "PASS" if invariant.ok is True else "MISSING" if invariant.ok is None else "FAIL"
        print(f"  [{status}] {invariant.name}: {invariant.detail}")
    print(f"\n{len(violations)} violation(s).")

    if args.strict and violations:
        raise SystemExit(1)


def _latest_report(reports_dir: Path) -> Path | None:
    reports = sorted(reports_dir.glob("BURRY_REPORT_EvidenceGated_*.json"))
    return reports[-1] if reports else None


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return data if isinstance(data, dict) else {}


if __name__ == "__main__":
    main()
