#!/usr/bin/env python
"""Materialize acquired EDGAR lease candidates into a source-backed lease corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.ingestion.capital.lease_extraction import extract_lease_agreements


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--deals",
        type=Path,
        default=Path("data/edgar_acquisition/deals.csv"),
        help="Source-backed EDGAR deal candidates.",
    )
    parser.add_argument(
        "--inventory",
        type=Path,
        default=Path("data/edgar_acquisition/edgar_document_inventory.csv"),
        help="Acquired EDGAR document inventory with retrieval timestamps and hashes.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/capital/lease_agreements.csv"),
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=32,
        help="Local row normalization workers. This does not make network requests.",
    )
    args = parser.parse_args()

    summary = extract_lease_agreements(
        deals_csv=args.deals,
        inventory_csv=args.inventory,
        output_csv=args.output,
        max_workers=args.max_workers,
    )
    summary_path = args.output.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    print(summary_path.read_text())
    print(f"\nLease agreement corpus written to: {args.output}")
    print(f"Summary JSON: {summary_path}")


if __name__ == "__main__":
    main()
