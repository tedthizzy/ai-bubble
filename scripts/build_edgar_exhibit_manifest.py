#!/usr/bin/env python
"""Build an exhibit-only EDGAR manifest from an existing filing manifest."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from bubble.ingestion.edgar.filing_manifest import build_edgar_exhibit_manifest_from_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_csv", type=Path)
    parser.add_argument("--min-parent-relevance-score", type=int, default=75)
    parser.add_argument("--max-parent-rows", type=int, default=None)
    parser.add_argument("--max-exhibits-per-filing", type=int, default=25)
    parser.add_argument("--exhibit-index-workers", type=int, default=16)
    parser.add_argument("--sec-requests-per-second", type=float, default=8.0)
    parser.add_argument("--sec-domain-concurrency", type=int, default=8)
    parser.add_argument("--retry-attempts", type=int, default=3)
    parser.add_argument("--retry-backoff-seconds", type=float, default=0.5)
    parser.add_argument("--progress-interval", type=int, default=0)
    parser.add_argument("--output-dir", type=Path, default=Path("data/manifests"))
    args = parser.parse_args()

    def progress(completed: int, total: int) -> None:
        print(
            json.dumps(
                {
                    "event": "edgar_exhibit_manifest_progress",
                    "completed_parent_indexes": completed,
                    "total_parent_indexes": total,
                },
                sort_keys=True,
            ),
            flush=True,
        )

    manifest = build_edgar_exhibit_manifest_from_manifest(
        args.manifest_csv,
        min_parent_relevance_score=args.min_parent_relevance_score,
        max_parent_rows=args.max_parent_rows,
        max_exhibits_per_filing=args.max_exhibits_per_filing,
        exhibit_index_workers=args.exhibit_index_workers,
        sec_requests_per_second=args.sec_requests_per_second,
        sec_domain_concurrency=args.sec_domain_concurrency,
        retry_attempts=args.retry_attempts,
        retry_backoff_seconds=args.retry_backoff_seconds,
        progress_interval=args.progress_interval,
        progress_callback=progress if args.progress_interval > 0 else None,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    csv_path = manifest.write_csv(args.output_dir / f"edgar_exhibit_manifest_{timestamp}.csv")
    summary_path = manifest.write_summary_json(
        args.output_dir / f"edgar_exhibit_manifest_{timestamp}.summary.json"
    )

    print(json.dumps(manifest.summary.to_dict(), indent=2, sort_keys=True))
    print(f"\nManifest CSV: {csv_path}")
    print(f"Summary JSON: {summary_path}")


if __name__ == "__main__":
    main()
