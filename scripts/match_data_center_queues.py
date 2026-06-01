#!/usr/bin/env python
"""Match data-center queue rows to tracker-backed physical project records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.ingestion.physical import (
    match_data_center_queues_to_projects,
    write_queue_project_match_summary,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--queue-input",
        type=Path,
        default=Path("data/source_acquisition/source_rows/queue_records.csv"),
    )
    parser.add_argument("--projects-input", type=Path, default=Path("data/physical/projects.csv"))
    parser.add_argument(
        "--matches-output",
        type=Path,
        default=Path("data/physical/queue_project_matches.csv"),
    )
    parser.add_argument("--queues-output", type=Path, default=Path("data/physical/queues.csv"))
    parser.add_argument(
        "--queue-projects-output",
        type=Path,
        default=Path("data/physical/queue_projects.csv"),
        help=(
            "Pending-adjudication physical project rows created from unmatched direct load "
            "and data-center-driven supporting generation queue records"
        ),
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("data/reports/queue_project_match_summary.json"),
    )
    parser.add_argument("--loader-min-confidence", type=float, default=0.72)
    args = parser.parse_args()

    summary = match_data_center_queues_to_projects(
        queue_rows_csv=args.queue_input,
        projects_csv=args.projects_input,
        matches_output=args.matches_output,
        queues_output=args.queues_output,
        queue_projects_output=args.queue_projects_output,
        loader_min_confidence=args.loader_min_confidence,
    )
    summary_path = write_queue_project_match_summary(summary, args.summary_output)
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    print(f"\nQueue/project matches: {args.matches_output}")
    print(f"Matched physical queues: {args.queues_output}")
    print(f"Queue-derived physical projects: {args.queue_projects_output}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
