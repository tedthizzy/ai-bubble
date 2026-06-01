#!/usr/bin/env python
"""Load source-backed physical evidence CSVs and generate risk assessments."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from bubble.ingestion.physical import ingest_physical_evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path, help="Directory containing physical evidence CSVs")
    parser.add_argument("--as-of", type=date.fromisoformat, default=None)
    args = parser.parse_args()

    summary = ingest_physical_evidence(args.directory, as_of=args.as_of)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
