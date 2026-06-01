#!/usr/bin/env python
"""Download EDGAR source documents from a manifest and emit pending deal candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.ingestion.edgar.document_acquisition import acquire_edgar_documents_from_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_csv", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("data/edgar_acquisition"))
    parser.add_argument("--min-relevance-score", type=int, default=75)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-workers", type=int, default=32)
    parser.add_argument("--sec-requests-per-second", type=float, default=8.0)
    parser.add_argument("--sec-domain-concurrency", type=int, default=8)
    parser.add_argument("--retry-attempts", type=int, default=3)
    parser.add_argument("--retry-backoff-seconds", type=float, default=0.5)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace output CSVs instead of merging acquired rows into existing inventory/deals.",
    )
    args = parser.parse_args()

    batch = acquire_edgar_documents_from_manifest(
        args.manifest_csv,
        output_dir=args.output_dir,
        min_relevance_score=args.min_relevance_score,
        limit=args.limit,
        max_workers=args.max_workers,
        sec_requests_per_second=args.sec_requests_per_second,
        sec_domain_concurrency=args.sec_domain_concurrency,
        retry_attempts=args.retry_attempts,
        retry_backoff_seconds=args.retry_backoff_seconds,
        resume=not args.no_resume,
        write_outputs=False,
    )
    outputs = batch.write_outputs(args.output_dir, merge_existing=not args.overwrite)

    print(json.dumps(batch.summary.to_dict(), indent=2, sort_keys=True))
    print("\nOutputs:")
    for name, path in outputs.items():
        print(f"  {name}: {path}")


if __name__ == "__main__":
    main()
