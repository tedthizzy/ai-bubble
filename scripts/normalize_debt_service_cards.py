#!/usr/bin/env python
"""Normalize long-form debt-service source cards into facility-level rows.

The input format is the handoff-card shape used for direct AI/data-center debt
terms: ``entity,facility,field,value,source_tier,source`` with optional
``source_uri``, ``filing_accession``, and ``source_quote`` columns. The script is
read-only unless ``--output`` is provided.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from bubble.ingestion.compute import (
    DEBT_SERVICE_TERM_FIELDS,
    normalize_debt_service_card_rows,
    summarize_debt_service_terms,
)


def _read_rows(paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        with path.open(newline="") as handle:
            rows.extend(dict(row) for row in csv.DictReader(handle))
    return rows


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=DEBT_SERVICE_TERM_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        action="append",
        required=True,
        type=Path,
        help="Long-form debt-service card CSV. Repeat for multiple files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional normalized facility-level CSV output path.",
    )
    args = parser.parse_args()

    rows = _read_rows(args.input)
    terms = normalize_debt_service_card_rows(rows)
    normalized_rows = [term.to_row() for term in terms]
    if args.output:
        _write_rows(args.output, normalized_rows)

    print(json.dumps(summarize_debt_service_terms(terms), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
