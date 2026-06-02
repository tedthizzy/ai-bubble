#!/usr/bin/env python
"""Read-only provenance-integrity scan of the acquired EDGAR corpus.

Novel checks beyond the existing source-invariant audit:
- `divergent_document_hash` — one document (accession/primary_document) carrying
  more than one content_hash (re-fetch drift / corruption) — ERROR.
- `invalid_content_hash` / `missing_content_hash` — non-sha256 or blank hash on a
  sourced row — ERROR.
- `hash_conflicting_document_ids` — one content_hash under multiple document_ids
  (duplicate content across filings; relevant to extraction double-counting) — WARNING.

Reads only. Rebuilds nothing. Exit code non-zero on any error-severity finding.

    PYTHONPATH=src uv run scripts/check_provenance_integrity.py \
        --repo-root /Users/ted/Documents/dev-archive/bubble
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from bubble.quality.provenance_audit import (
    ProvenanceFinding,
    check_divergent_document_hashes,
    check_hash_conflicting_document_ids,
    check_invalid_hashes,
)


def _inventory_rows(inventory_csv: Path) -> list[dict[str, str]]:
    with inventory_csv.open() as handle:
        return [
            {
                "document_id": f"{record.get('accession_number', '')}/{record.get('primary_document', '')}",
                "content_hash": record.get("content_hash", ""),
                "source_uri": record.get("filing_url", ""),
            }
            for record in csv.DictReader(handle)
        ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Checkout whose data/ to scan (default: this checkout).",
    )
    args = parser.parse_args()
    inventory_csv = args.repo_root / "data" / "edgar_acquisition" / "edgar_document_inventory.csv"

    print(f"Provenance-integrity scan: {inventory_csv}")
    if not inventory_csv.exists():
        print("  inventory not found (point --repo-root at the checkout that holds data/).")
        return 0

    rows = _inventory_rows(inventory_csv)
    label = "edgar_document_inventory.csv"
    findings: list[ProvenanceFinding] = []
    findings += check_divergent_document_hashes(rows, source_label=label)
    findings += check_invalid_hashes(rows, source_label=label)
    findings += check_hash_conflicting_document_ids(rows, source_label=label)

    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]
    print(f"  rows scanned: {len(rows)}")
    print(f"  errors: {len(errors)}  warnings: {len(warnings)}")
    for finding in errors[:50]:
        print(f"  ERROR [{finding.check}] {finding.message}")
    for finding in warnings[:20]:
        print(f"  warn  [{finding.check}] {finding.message}")
    if len(warnings) > 20:
        print(f"  … and {len(warnings) - 20} more warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
