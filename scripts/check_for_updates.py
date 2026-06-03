#!/usr/bin/env python
"""Continuous-update check: diff a fresh EDGAR submissions snapshot vs ingested filings.

The harness that lets the engine update as new data arrives. It loads the
accessions the engine has already ingested (from the filing manifests under
data/manifests/) and a FRESH submissions snapshot (a JSON list of
{cik, accession, form, filing_date}), computes the high-signal delta, and writes
data/reports/update_delta.json with a rerun_recommended flag.

Provide the snapshot via --snapshot PATH. Fetching it live from EDGAR
(data.sec.gov/submissions/CIK##########.json) is the only networked step and is
intentionally kept out of this deterministic differ; a separate fetch step (or the
raw_prep locator) produces the snapshot.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from bubble.ingestion.update_detector import detect_filing_updates


def _load_ingested_accessions(manifest_dir: Path) -> set[str]:
    accessions: set[str] = set()
    if not manifest_dir.exists():
        return accessions
    for csv_path in manifest_dir.glob("*.csv"):
        try:
            with csv_path.open(newline="") as fh:
                for row in csv.DictReader(fh):
                    acc = (row.get("accession") or row.get("accession_number") or "").strip()
                    if acc:
                        accessions.add(acc)
        except (OSError, csv.Error):
            continue
    return accessions


def _load_snapshot(path: Path) -> list[dict[str, Any]]:
    try:
        loaded = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    return [r for r in loaded if isinstance(r, dict)] if isinstance(loaded, list) else []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-dir", type=Path, default=Path("data/manifests"))
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=None,
        help="JSON list of fresh submissions [{cik, accession, form, filing_date}].",
    )
    parser.add_argument("--output", type=Path, default=Path("data/reports/update_delta.json"))
    args = parser.parse_args()

    ingested = _load_ingested_accessions(args.manifest_dir)
    if args.snapshot is None or not args.snapshot.exists():
        print(
            json.dumps(
                {
                    "status": "no_snapshot",
                    "ingested_accession_count": len(ingested),
                    "note": (
                        "Provide --snapshot with a fresh EDGAR submissions JSON to compute the delta. "
                        "Fetch from data.sec.gov/submissions/CIK##########.json for the tracked CIKs."
                    ),
                },
                indent=2,
            )
        )
        return

    snapshot = _load_snapshot(args.snapshot)
    result = detect_filing_updates(ingested, snapshot)
    result["ingested_accession_count"] = len(ingested)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "top_new_filings"}, indent=2))


if __name__ == "__main__":
    main()
