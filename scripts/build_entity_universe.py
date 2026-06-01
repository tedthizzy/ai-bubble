#!/usr/bin/env python
"""Build a source-backed entity universe and expanded EDGAR CIK list."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.ingestion.entities import build_entity_universe


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/entity_universe"))
    parser.add_argument("--sec-reference-json", type=Path, default=None)
    parser.add_argument("--no-fetch-sec-reference", action="store_true")
    parser.add_argument("--identity", default=None)
    parser.add_argument("--min-mentions-for-expanded-cik", type=int, default=1)
    parser.add_argument("--max-expanded-ciks", type=int, default=None)
    args = parser.parse_args()

    summary = build_entity_universe(
        args.data_dir,
        output_dir=args.output_dir,
        sec_reference_json=args.sec_reference_json,
        fetch_sec_reference=not args.no_fetch_sec_reference,
        identity=args.identity,
        min_mentions_for_expanded_cik=args.min_mentions_for_expanded_cik,
        max_expanded_ciks=args.max_expanded_ciks,
    )
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
