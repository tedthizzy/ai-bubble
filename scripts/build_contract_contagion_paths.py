#!/usr/bin/env python
"""Build source-backed contract/ownership contagion path artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.analysis.contract_contagion_paths import (
    build_contract_contagion_paths,
    write_contract_contagion_paths,
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
    parser.add_argument("--min-notional-usd", type=float, default=1_000_000_000)
    parser.add_argument("--max-ownership-depth", type=int, default=3)
    parser.add_argument("--max-paths", type=int, default=10_000)
    args = parser.parse_args()

    data_dirs = args.data_dir or [Path("data")]
    batch = build_contract_contagion_paths(
        data_dirs,
        min_notional_usd=args.min_notional_usd,
        max_ownership_depth=args.max_ownership_depth,
        max_paths=args.max_paths,
    )
    outputs = write_contract_contagion_paths(batch, args.output_dir)
    print(json.dumps({**batch.summary.to_dict(), "outputs": outputs}, indent=2))


if __name__ == "__main__":
    main()
