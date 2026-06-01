#!/usr/bin/env python
"""Match source-backed permit/equipment rows to tracker-backed projects."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.ingestion.physical import (
    match_physical_records_to_projects,
    write_physical_record_match_summary,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--permit-input",
        type=Path,
        default=Path("data/source_acquisition/source_rows/permit_records.csv"),
    )
    parser.add_argument(
        "--equipment-input",
        type=Path,
        default=Path("data/source_acquisition/source_rows/equipment_records.csv"),
    )
    parser.add_argument("--projects-input", type=Path, default=Path("data/physical/projects.csv"))
    parser.add_argument(
        "--permit-matches-output",
        type=Path,
        default=Path("data/physical/permit_project_matches.csv"),
    )
    parser.add_argument(
        "--equipment-matches-output",
        type=Path,
        default=Path("data/physical/equipment_project_matches.csv"),
    )
    parser.add_argument("--permits-output", type=Path, default=Path("data/physical/permits.csv"))
    parser.add_argument(
        "--equipment-output", type=Path, default=Path("data/physical/equipment.csv")
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("data/reports/physical_record_match_summary.json"),
    )
    parser.add_argument("--max-workers", type=int, default=32)
    args = parser.parse_args()

    summary = match_physical_records_to_projects(
        permit_rows_csv=args.permit_input,
        equipment_rows_csv=args.equipment_input,
        projects_csv=args.projects_input,
        permit_matches_output=args.permit_matches_output,
        equipment_matches_output=args.equipment_matches_output,
        permits_output=args.permits_output,
        equipment_output=args.equipment_output,
        max_workers=args.max_workers,
    )
    summary_path = write_physical_record_match_summary(summary, args.summary_output)
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    print(f"\nPermit match audit: {args.permit_matches_output}")
    print(f"Equipment match audit: {args.equipment_matches_output}")
    print(f"Matched physical permits: {args.permits_output}")
    print(f"Matched physical equipment: {args.equipment_output}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
