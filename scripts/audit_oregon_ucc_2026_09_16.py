#!/usr/bin/env python3
"""Audit the Oregon public UCC monthly-filings and secured-party CSV exports."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

SOURCES = {
    "august_filings": ("snfi-f79b", 5738, "FILING_DATE", "LIEN NUMBER"),
    "current_secured_parties": ("2kf7-i54h", 220136, "FILING DATE", "FILING NUMBER"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit(path: Path, date_column: str, id_column: str) -> dict:
    dates = []
    record_types: Counter[str] = Counter()
    distinct_ids: set[str] = set()
    rows = 0
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        columns = reader.fieldnames or []
        for row in reader:
            rows += 1
            dates.append(datetime.strptime(row[date_column], "%m/%d/%Y").date())
            record_types[row.get("LIEN_TYPE", row.get("LIEN TYPE", ""))] += 1
            distinct_ids.add(row[id_column])
    return {
        "raw_path": str(path),
        "raw_bytes": path.stat().st_size,
        "raw_sha256": sha256(path),
        "columns": columns,
        "row_count": rows,
        "distinct_lien_numbers": len(distinct_ids),
        "filing_date_min": min(dates).isoformat(),
        "filing_date_max": max(dates).isoformat(),
        "lien_type_counts": dict(record_types),
        "has_amount_column": any("amount" in column.lower() for column in columns),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    datasets = {}
    for name, (dataset_id, expected, date_column, id_column) in SOURCES.items():
        path = args.raw_dir / f"or_ucc_{dataset_id}_2026-09-16.csv"
        result = audit(path, date_column, id_column)
        result["api_row_count_before_download"] = expected
        result["matches_api_row_count"] = result["row_count"] == expected
        result["source_dataset_page"] = f"https://data.oregon.gov/d/{dataset_id}"
        result["source_uri"] = (
            f"https://data.oregon.gov/api/views/{dataset_id}/rows.csv?accessType=DOWNLOAD"
        )
        datasets[name] = result
    summary = {
        "as_of_pacific_date": "2026-09-16",
        "datasets": datasets,
        "caveats": [
            "The August file covers only prior-month filings, not Oregon's full historical debtor corpus.",
            "The current-secured-parties file does not provide debtor names or an amount field.",
            "A financing-statement record does not establish outstanding debt or borrower distress.",
            "Raw files include individual names and addresses; do not publish them from git.",
        ],
    }
    output = args.output_dir / "oregon_ucc_summary.json"
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({name: result["row_count"] for name, result in datasets.items()}))


if __name__ == "__main__":
    main()
