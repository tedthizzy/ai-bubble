#!/usr/bin/env python
"""Build materiality-ranked LLM adjudication packets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.analysis.materiality_adjudication import (
    build_materiality_adjudication_packets,
    write_materiality_adjudication_packets,
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
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--snippets-per-packet", type=int, default=2)
    parser.add_argument("--snippet-chars", type=int, default=1_200)
    args = parser.parse_args()

    data_dirs = args.data_dir or [Path("data")]
    batch = build_materiality_adjudication_packets(
        data_dirs,
        limit=args.limit,
        snippets_per_packet=args.snippets_per_packet,
        snippet_chars=args.snippet_chars,
    )
    outputs = write_materiality_adjudication_packets(batch, args.output_dir)
    print(json.dumps({**batch.summary.to_dict(), "outputs": outputs}, indent=2))


if __name__ == "__main__":
    main()
