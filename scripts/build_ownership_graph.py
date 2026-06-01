#!/usr/bin/env python
"""Build source-backed ownership/consolidation graph artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.analysis.ownership_graph import (
    build_ownership_graph,
    load_ownership_rows,
    write_ownership_graph,
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
    parser.add_argument("--output-dir", type=Path, default=Path("data/graph"))
    args = parser.parse_args()

    data_dirs = args.data_dir or [Path("data")]
    rows = load_ownership_rows(data_dirs)
    graph = build_ownership_graph(rows)
    outputs = write_ownership_graph(graph, args.output_dir)
    print(json.dumps({**graph.summary.to_dict(), "outputs": outputs}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
