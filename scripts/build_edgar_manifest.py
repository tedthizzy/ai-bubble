#!/usr/bin/env python
"""Build a source-backed SEC filing manifest for extraction planning."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, date, datetime
from pathlib import Path

from bubble.ingestion.edgar.filing_manifest import build_edgar_filing_manifest
from bubble.ingestion.edgar.seeds import WATCHLIST_CIKS


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
        "--limit", type=int, default=20, help="Limit public watchlist CIKs when --cik is omitted"
    )
    parser.add_argument("--all-public", action="store_true", help="Use the full public watchlist")
    parser.add_argument("--since", type=date.fromisoformat, default=None)
    parser.add_argument("--until", type=date.fromisoformat, default=None)
    parser.add_argument("--max-filings-per-cik", type=int, default=80)
    parser.add_argument(
        "--include-exhibits",
        action="store_true",
        help="Append candidate exhibit documents from each filing directory index",
    )
    parser.add_argument("--max-exhibits-per-filing", type=int, default=25)
    parser.add_argument("--exhibit-index-workers", type=int, default=4)
    parser.add_argument("--max-workers", type=int, default=32)
    parser.add_argument("--sec-requests-per-second", type=float, default=8.0)
    parser.add_argument("--sec-domain-concurrency", type=int, default=8)
    parser.add_argument("--retry-attempts", type=int, default=3)
    parser.add_argument("--retry-backoff-seconds", type=float, default=0.5)
    parser.add_argument("--output-dir", type=Path, default=Path("data/manifests"))
    args = parser.parse_args()

    ciks = _combined_ciks(args.ciks, args.cik_csv, args.cik_column)
    if args.all_public:
        ciks = [*WATCHLIST_CIKS, *ciks]
    if not ciks:
        ciks = WATCHLIST_CIKS
    if not args.ciks and not args.cik_csv and not args.all_public:
        ciks = ciks[: args.limit]
    ciks = list(dict.fromkeys(ciks))

    manifest = build_edgar_filing_manifest(
        ciks,
        since=args.since,
        until=args.until,
        max_filings_per_cik=args.max_filings_per_cik,
        include_exhibits=args.include_exhibits,
        max_exhibits_per_filing=args.max_exhibits_per_filing,
        exhibit_index_workers=args.exhibit_index_workers,
        max_workers=args.max_workers,
        sec_requests_per_second=args.sec_requests_per_second,
        sec_domain_concurrency=args.sec_domain_concurrency,
        retry_attempts=args.retry_attempts,
        retry_backoff_seconds=args.retry_backoff_seconds,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    csv_path = manifest.write_csv(args.output_dir / f"edgar_filing_manifest_{timestamp}.csv")
    summary_path = manifest.write_summary_json(
        args.output_dir / f"edgar_filing_manifest_{timestamp}.summary.json"
    )

    print(json.dumps(manifest.summary.to_dict(), indent=2, sort_keys=True))
    print(f"\nManifest CSV: {csv_path}")
    print(f"Summary JSON: {summary_path}")


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
