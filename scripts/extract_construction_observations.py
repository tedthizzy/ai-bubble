#!/usr/bin/env python
"""Extract source-backed construction observations from normalized project records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.ingestion.physical.construction_observations import (
    extract_construction_observations_from_projects,
    write_construction_observation_summary,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/physical/projects.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/physical/observations.csv"))
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("data/reports/construction_observation_extraction_summary.json"),
    )
    parser.add_argument("--max-workers", type=int, default=32)
    args = parser.parse_args()

    summary = extract_construction_observations_from_projects(
        args.input,
        args.output,
        max_workers=args.max_workers,
    )
    summary_path = write_construction_observation_summary(summary, args.summary_output)
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    print(f"\nConstruction observations: {args.output}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
