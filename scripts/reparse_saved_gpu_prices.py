#!/usr/bin/env python3
"""Reparse saved public prices into a new output while keeping source dates."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from bubble.ingestion.compute.gpu_pricing import acquire_gpu_pricing


def no_fetch(url: str) -> bytes:
    raise RuntimeError(f"Saved-source reparse must not fetch: {url}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    raw = args.output / "raw_gpu_pricing"
    raw.mkdir()
    for path in sorted((args.source / "raw_gpu_pricing").glob("*.html")):
        (raw / path.name).symlink_to(os.path.relpath(path.resolve(), raw.resolve()))
    result = acquire_gpu_pricing(output_dir=args.output, fetch_bytes=no_fetch, max_workers=4)
    print(json.dumps(result.summary.to_dict()), flush=True)
    return 1 if result.summary.errors else 0


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget(512)
    raise SystemExit(main())
