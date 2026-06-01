#!/usr/bin/env python
"""Acquire raw artifacts and extracted rows from a real source catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.ingestion.sources import acquire_source_catalog


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog_csv", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("data/source_acquisition"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-workers", type=int, default=64)
    parser.add_argument("--sec-requests-per-second", type=float, default=8.0)
    parser.add_argument("--sec-domain-concurrency", type=int, default=8)
    parser.add_argument("--other-requests-per-second", type=float, default=16.0)
    parser.add_argument("--other-domain-concurrency", type=int, default=16)
    parser.add_argument("--retry-attempts", type=int, default=3)
    parser.add_argument("--retry-backoff-seconds", type=float, default=0.5)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()

    batch = acquire_source_catalog(
        args.catalog_csv,
        output_dir=args.output_dir,
        limit=args.limit,
        max_workers=args.max_workers,
        sec_requests_per_second=args.sec_requests_per_second,
        sec_domain_concurrency=args.sec_domain_concurrency,
        other_requests_per_second=args.other_requests_per_second,
        other_domain_concurrency=args.other_domain_concurrency,
        retry_attempts=args.retry_attempts,
        retry_backoff_seconds=args.retry_backoff_seconds,
        resume=not args.no_resume,
        write_outputs=False,
    )
    outputs = batch.write_outputs(args.output_dir)
    print(json.dumps(batch.summary.to_dict(), indent=2, sort_keys=True))
    print("\nOutputs:")
    for name, value in outputs.items():
        print(f"  {name}: {value}")


if __name__ == "__main__":
    main()
