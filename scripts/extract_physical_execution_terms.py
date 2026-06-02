#!/usr/bin/env python
"""Extract source-backed physical execution terms from acquired source rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.ingestion.physical.execution_extraction import (
    extract_physical_execution_terms_from_csvs,
    write_physical_execution_extraction_summary,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        action="append",
        type=Path,
        dest="inputs",
        default=None,
        help="Input source-row CSV. May be provided multiple times.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/physical/physical_execution_terms.csv"),
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("data/reports/physical_execution_terms_extraction.summary.json"),
    )
    args = parser.parse_args()

    inputs = args.inputs or [
        Path("data/source_acquisition/source_rows/tracker_records.csv"),
        Path("data/source_acquisition/source_rows/queue_records.csv"),
        Path("data/source_acquisition/source_rows/permit_records.csv"),
    ]
    summary = extract_physical_execution_terms_from_csvs(inputs, args.output)
    summary_path = write_physical_execution_extraction_summary(summary, args.summary_output)
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    print(f"\nPhysical execution terms: {args.output}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
