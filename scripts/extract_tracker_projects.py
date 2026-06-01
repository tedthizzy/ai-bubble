#!/usr/bin/env python
"""Normalize acquired project tracker rows into physical project evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.ingestion.physical.tracker_extraction import (
    extract_tracker_projects,
    write_tracker_project_summary,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/source_acquisition/source_rows/tracker_records.csv"),
    )
    parser.add_argument("--output", type=Path, default=Path("data/physical/projects.csv"))
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("data/reports/tracker_project_extraction_summary.json"),
    )
    parser.add_argument("--max-workers", type=int, default=32)
    args = parser.parse_args()

    summary = extract_tracker_projects(args.input, args.output, max_workers=args.max_workers)
    summary_path = write_tracker_project_summary(summary, args.summary_output)
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    print(f"\nTracker project evidence: {args.output}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
