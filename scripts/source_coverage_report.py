#!/usr/bin/env python
"""Report source corpus coverage across raw documents and extracted rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.analysis.source_coverage import (
    build_source_coverage_report,
    write_source_coverage_report,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", action="append", dest="data_dirs", default=None)
    parser.add_argument("--output", type=Path, default=Path("data/reports/source_coverage.json"))
    args = parser.parse_args()

    report = build_source_coverage_report(args.data_dirs or ["data"])
    output = write_source_coverage_report(report, args.output)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    print(f"\nCoverage report: {output}")


if __name__ == "__main__":
    main()
