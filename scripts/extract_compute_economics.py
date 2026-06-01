#!/usr/bin/env python
"""Extract source-backed compute economics evidence from acquired EDGAR documents."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.ingestion.compute.edgar_extraction import extract_compute_economics_from_edgar


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inventory",
        type=Path,
        default=Path("data/edgar_acquisition/edgar_document_inventory.csv"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/compute"))
    parser.add_argument(
        "--workers",
        type=int,
        default=32,
        help="Local document parsing workers. This does not make SEC network requests.",
    )
    args = parser.parse_args()

    summary = extract_compute_economics_from_edgar(
        inventory_csv=args.inventory,
        output_dir=args.output_dir,
        max_workers=args.workers,
    )
    summary_path = args.output_dir / "compute_economics_extraction.summary.json"
    summary_path.write_text(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    print(summary_path.read_text())
    print(f"\nCompute economics evidence written to: {args.output_dir}")
    print(f"Summary JSON: {summary_path}")


if __name__ == "__main__":
    main()
