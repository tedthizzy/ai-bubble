#!/usr/bin/env python
"""Find SEC exhibit links in downloaded primary filings without network I/O."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from bubble.ingestion.edgar.offline_exhibits import discover_offline_exhibits


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_csv", type=Path)
    parser.add_argument(
        "--documents-dir",
        type=Path,
        default=Path("data/edgar_acquisition_2026-09-16/documents"),
    )
    parser.add_argument("--min-parent-relevance-score", type=int, default=75)
    parser.add_argument("--max-exhibits-per-filing", type=int, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("data/manifests"))
    args = parser.parse_args()

    result = discover_offline_exhibits(
        args.manifest_csv,
        args.documents_dir,
        min_parent_relevance_score=args.min_parent_relevance_score,
        max_exhibits_per_filing=args.max_exhibits_per_filing,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    stem = args.output_dir / f"edgar_exhibit_offline_{timestamp}"
    for path in (stem.with_suffix(".csv"), Path(f"{stem}.summary.json")):
        if path.exists():
            raise FileExistsError(path)
    csv_path = result.manifest.write_csv(stem.with_suffix(".csv"))
    summary_path = Path(f"{stem}.summary.json")
    summary_path.write_text(json.dumps(result.coverage, indent=2, sort_keys=True))
    print(json.dumps({
        "manifest_csv": str(csv_path),
        "coverage_json": str(summary_path),
        "selected_parent_filings": result.coverage["selected_parent_filings"],
        "parsed_parent_filings": result.coverage["parsed_parent_filings"],
        "discovered_exhibit_rows": result.coverage["discovered_exhibit_rows"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
