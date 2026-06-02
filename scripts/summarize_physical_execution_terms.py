#!/usr/bin/env python3
"""Summarize source-backed physical execution terms."""

from __future__ import annotations

import argparse
from pathlib import Path

from bubble.analysis.physical_execution_summary import (
    build_physical_execution_summary,
    write_physical_execution_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        action="append",
        default=["data"],
        help="Data root to scan. May be supplied more than once.",
    )
    parser.add_argument(
        "--output",
        default="data/reports/physical_execution_summary.json",
        help="Summary JSON path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = build_physical_execution_summary([Path(data_dir) for data_dir in args.data_dir])
    output = write_physical_execution_summary(summary, args.output)
    print(f"Physical execution summary written: {output}")
    print(
        f"Terms: {summary.distinct_terms}/{summary.term_rows} distinct; "
        f"onsite MW term-sum: {summary.onsite_generation_mw_term_sum:,.1f}; "
        f"risk terms: {sum(summary.risk_term_counts.values())}"
    )


if __name__ == "__main__":
    main()
