#!/usr/bin/env python
"""Build automated decisions for materiality-ranked adjudication packets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.analysis.materiality_adjudication_results import (
    build_materiality_adjudication_decisions,
    write_materiality_adjudication_decisions,
)


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
    parser.add_argument("--max-workers", type=int, default=32)
    args = parser.parse_args()

    data_dirs = args.data_dir or [Path("data")]
    batch = build_materiality_adjudication_decisions(data_dirs, max_workers=args.max_workers)
    outputs = write_materiality_adjudication_decisions(batch, args.output_dir)
    print(json.dumps({**batch.summary.to_dict(), "outputs": outputs}, indent=2))


if __name__ == "__main__":
    main()
