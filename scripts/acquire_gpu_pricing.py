#!/usr/bin/env python
"""Acquire source-backed public GPU rental pricing observations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.ingestion.compute.gpu_pricing import acquire_gpu_pricing


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("data/compute"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--other-requests-per-second", type=float, default=8.0)
    parser.add_argument("--other-domain-concurrency", type=int, default=4)
    parser.add_argument("--retry-attempts", type=int, default=3)
    parser.add_argument("--retry-backoff-seconds", type=float, default=0.5)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()

    result = acquire_gpu_pricing(
        output_dir=args.output_dir,
        max_workers=args.workers,
        other_requests_per_second=args.other_requests_per_second,
        other_domain_concurrency=args.other_domain_concurrency,
        retry_attempts=args.retry_attempts,
        retry_backoff_seconds=args.retry_backoff_seconds,
        resume=not args.no_resume,
    )
    summary_path = args.output_dir / "gpu_pricing_acquisition.summary.json"
    print(json.dumps(result.summary.to_dict(), indent=2, sort_keys=True))
    print(
        f"\nGPU pricing observations written to: {args.output_dir / 'gpu_price_observations.csv'}"
    )
    print(f"Raw pricing artifacts written under: {args.output_dir / 'raw_gpu_pricing'}")
    print(f"Summary JSON: {summary_path}")


if __name__ == "__main__":
    main()
