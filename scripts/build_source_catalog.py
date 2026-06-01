#!/usr/bin/env python
"""Build a real-source acquisition catalog for queued downloads."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from bubble.ingestion.edgar.seeds import WATCHLIST_CIKS
from bubble.ingestion.sources import build_seed_source_catalog


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cik", action="append", dest="ciks", help="CIK to include")
    parser.add_argument(
        "--cik-csv",
        action="append",
        type=Path,
        default=None,
        help="CSV containing CIKs to include, such as data/entity_universe/expanded_edgar_ciks.csv",
    )
    parser.add_argument("--cik-column", default="cik")
    parser.add_argument(
        "--limit", type=int, default=20, help="Limit EDGAR seed CIKs when --cik is omitted"
    )
    parser.add_argument(
        "--all-public",
        action="store_true",
        help="Use the broader public watchlist instead of the vetted EDGAR seed set",
    )
    parser.add_argument(
        "--curated-catalog",
        action="append",
        type=Path,
        default=None,
        help="Existing source catalog CSV to validate and append",
    )
    parser.add_argument(
        "--no-public-sources",
        action="store_true",
        help="Do not include built-in public non-EDGAR source targets",
    )
    parser.add_argument(
        "--resolve-dynamic-public-sources",
        action="store_true",
        help="Resolve live public source listings such as ERCOT's latest GIS workbook",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/source_catalogs/source_catalog.csv")
    )
    args = parser.parse_args()

    ciks = _combined_ciks(args.ciks, args.cik_csv, args.cik_column)
    if args.all_public:
        ciks = [*WATCHLIST_CIKS, *ciks]
    deduped_ciks = list(dict.fromkeys(ciks))
    selected_ciks: list[str] | None = deduped_ciks or None
    limit = None if args.ciks or args.cik_csv or args.all_public else args.limit
    summary = build_seed_source_catalog(
        args.output,
        ciks=selected_ciks,
        limit=limit,
        include_public_sources=not args.no_public_sources,
        include_dynamic_public_sources=args.resolve_dynamic_public_sources,
        curated_catalogs=args.curated_catalog,
    )

    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    print(f"\nSource catalog: {args.output}")


def _combined_ciks(
    cli_ciks: list[str] | None,
    csv_paths: list[Path] | None,
    cik_column: str,
) -> list[str]:
    ciks = list(cli_ciks or [])
    for path in csv_paths or []:
        with path.open(newline="") as f:
            reader = csv.DictReader(f)
            if cik_column not in (reader.fieldnames or []):
                raise ValueError(f"{path} missing CIK column '{cik_column}'")
            ciks.extend((row.get(cik_column) or "").strip() for row in reader)
    return [cik for cik in ciks if cik]


if __name__ == "__main__":
    main()
