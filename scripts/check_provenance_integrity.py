#!/usr/bin/env python
"""Read-only provenance-integrity scan of the acquired EDGAR corpus.

Novel checks beyond the existing source-invariant audit:
- `divergent_document_hash` — one document carrying more than one content_hash
  (re-fetch drift / corruption) — ERROR.
- `invalid_content_hash` / `missing_content_hash` — non-sha256 or blank hash on a
  sourced row — ERROR.
- a per-source `content_hash -> multiple ids` fanout summary (one source document
  producing many rows) — informational, relevant to extraction/metric dedup.

Scans the EDGAR document inventory, deals.csv, and tranches.csv. Reads only,
rebuilds nothing. Exit code non-zero on any error-severity finding.

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

# (relative path, label, id columns joined by "/", hash column, uri column)
SCAN_TARGETS = (
    (
        "data/edgar_acquisition/edgar_document_inventory.csv",
        "edgar_document_inventory.csv",
        ("accession_number", "primary_document"),
        "content_hash",
        "filing_url",
    ),
    ("data/edgar_acquisition/deals.csv", "deals.csv", ("deal_id",), "content_hash", "source_uri"),
    (
        "data/edgar_acquisition/tranches.csv",
        "tranches.csv",
        ("deal_id", "tranche_id"),
        "content_hash",
        "source_uri",
    ),
)


def _read_rows(
    csv_path: Path, id_fields: tuple[str, ...], hash_field: str, uri_field: str
) -> list[dict[str, str]]:
    with csv_path.open() as handle:
        return [
            {
                "document_id": "/".join(record.get(field, "") for field in id_fields),
                "content_hash": record.get(hash_field, ""),
                "source_uri": record.get(uri_field, ""),
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
    root: Path = args.repo_root

    print(f"Provenance-integrity scan (repo-root: {root})")
    errors: list[ProvenanceFinding] = []
    for rel, label, id_fields, hash_field, uri_field in SCAN_TARGETS:
        csv_path = root / rel
        if not csv_path.exists():
            print(f"  (skipped — not found: {rel})")
            continue
        rows = _read_rows(csv_path, id_fields, hash_field, uri_field)
        divergent = check_divergent_document_hashes(rows, source_label=label)
        invalid = check_invalid_hashes(rows, source_label=label)
        fanout = check_hash_conflicting_document_ids(rows, source_label=label)
        errors.extend(divergent)
        errors.extend(invalid)
        print(
            f"  {label}: {len(rows)} rows | "
            f"divergent_document_hash={len(divergent)} | invalid/missing_hash={len(invalid)} | "
            f"content_hash->multiple_ids (fanout)={len(fanout)}"
        )
        for finding in divergent[:10]:
            print(f"    ERROR [{finding.check}] {finding.message}")
        for finding in invalid[:10]:
            print(f"    ERROR [{finding.check}] {finding.message}")

    print(f"\n{len(errors)} error-severity finding(s) across all targets.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
