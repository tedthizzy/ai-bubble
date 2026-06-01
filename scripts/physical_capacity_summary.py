#!/usr/bin/env python
"""Build source-backed physical capacity rollups from acquired source rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.analysis.physical_capacity import (
    build_physical_capacity_summary,
    write_physical_capacity_summary,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", action="append", dest="data_dirs", default=None)
    parser.add_argument(
        "--output", type=Path, default=Path("data/reports/physical_capacity_summary.json")
    )
    args = parser.parse_args()

    summary = build_physical_capacity_summary(args.data_dirs or ["data"])
    output = write_physical_capacity_summary(summary, args.output)
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    print(f"\nPhysical capacity summary: {output}")


if __name__ == "__main__":
    main()
