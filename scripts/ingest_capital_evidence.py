#!/usr/bin/env python
"""Load source-backed capital/deal CSVs and generate capital-structure metrics."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from bubble.ingestion.capital import ingest_capital_evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path, help="Directory containing capital evidence CSVs")
    parser.add_argument("--as-of", type=date.fromisoformat, default=None)
    parser.add_argument("--near-term-end", type=date.fromisoformat, default=None)
    args = parser.parse_args()

    summary = ingest_capital_evidence(
        args.directory,
        as_of=args.as_of,
        near_term_end=args.near_term_end,
    )
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
