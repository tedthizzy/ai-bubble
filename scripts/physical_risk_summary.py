#!/usr/bin/env python
"""Build project-level physical deliverability risk rollups."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.analysis.physical_risk_summary import (
    build_physical_risk_summary,
    write_physical_risk_summary,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", action="append", dest="data_dirs")
    parser.add_argument(
        "--output", type=Path, default=Path("data/reports/physical_risk_summary.json")
    )
    parser.add_argument("--max-workers", type=int, default=None)
    args = parser.parse_args()

    summary = build_physical_risk_summary(
        args.data_dirs or ["data"],
        max_workers=args.max_workers,
    )
    output = write_physical_risk_summary(summary, args.output)
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    print(f"\nPhysical risk summary: {output}")


if __name__ == "__main__":
    main()
