#!/usr/bin/env python
"""Normalize acquired PPA rows into capital/deal evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.ingestion.capital.ppa_extraction import extract_ppa_deals


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/source_acquisition/source_rows/ppas.csv"),
    )
    parser.add_argument("--output", type=Path, default=Path("data/capital/deals.csv"))
    parser.add_argument("--max-workers", type=int, default=32)
    args = parser.parse_args()

    summary = extract_ppa_deals(args.input, args.output, max_workers=args.max_workers)
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    print(f"\nExtracted PPA deals: {args.output}")


if __name__ == "__main__":
    main()
