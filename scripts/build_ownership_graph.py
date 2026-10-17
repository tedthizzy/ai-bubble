#!/usr/bin/env python
"""Build source-backed ownership/consolidation graph artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.analysis.ownership_graph import (
    iter_ownership_rows,
    load_lei_reference_rows,
)
from bubble.analysis.ownership_sqlite import write_ownership_graph_from_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        action="append",
        type=Path,
        default=None,
        help="Data root to scan; may be supplied more than once.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/graph"))
    args = parser.parse_args()

    data_dirs = args.data_dir or [Path("data")]
    if args.output_dir.exists():
        raise FileExistsError(f"Choose a new immutable output directory: {args.output_dir}")
    rows = iter_ownership_rows(data_dirs)
    lei_rows = load_lei_reference_rows(data_dirs)
    summary, outputs = write_ownership_graph_from_rows(rows, lei_rows=lei_rows, output_dir=args.output_dir)
    print(json.dumps({**summary.to_dict(), "outputs": outputs}, indent=2, sort_keys=True))


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget(1024)
    main()
