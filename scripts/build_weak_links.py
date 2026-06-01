#!/usr/bin/env python
"""Build source-backed weak-link ranking artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.analysis.weak_links import build_weak_link_batch, write_weak_link_batch


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
    parser.add_argument("--top-physical-limit", type=int, default=250)
    args = parser.parse_args()

    data_dirs = args.data_dir or [Path("data")]
    batch = build_weak_link_batch(data_dirs, top_physical_limit=args.top_physical_limit)
    outputs = write_weak_link_batch(batch, args.output_dir)
    print(json.dumps({**batch.summary.to_dict(), "outputs": outputs}, indent=2))


if __name__ == "__main__":
    main()
