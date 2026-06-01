#!/usr/bin/env python
"""Build source-backed human review queue artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.analysis.review_queue import build_review_queue, write_review_queue


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        action="append",
        type=Path,
        default=None,
        help="Data root to scan; may be supplied more than once.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/reports"))
    parser.add_argument(
        "--capital-review-threshold-usd",
        type=float,
        default=1_000_000_000,
        help="Minimum pending debt-like notional amount to queue for capital review.",
    )
    args = parser.parse_args()

    data_dirs = args.data_dir or [Path("data")]
    batch = build_review_queue(
        data_dirs,
        capital_review_threshold_usd=args.capital_review_threshold_usd,
    )
    outputs = write_review_queue(batch, args.output_dir)
    print(json.dumps({**batch.summary.to_dict(), "outputs": outputs}, indent=2))


if __name__ == "__main__":
    main()
