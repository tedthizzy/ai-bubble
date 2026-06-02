#!/usr/bin/env python
"""Read-only metric-aggregation simulator.

Reads the materiality adjudication decisions CSV (approved-for-metric rows) and
compares the final approved-metric total under several grouping keys, so the
effect of the dedup key can be monitored after each rebuild. Reads only.

    PYTHONPATH=src uv run scripts/simulate_metric_aggregation.py \
        --repo-root /Users/ted/Documents/dev-archive/bubble
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

from bubble.quality.metric_aggregation_sim import simulate

_ACCESSION_RE = re.compile(r"/data/\d+/([0-9-]+)/")

STRATEGIES: list[tuple[str, tuple[str, ...]]] = [
    ("metric_group_id (current)", ("metric_group_id",)),
    ("content_hash + amount", ("content_hash", "supported_amount_usd")),
    ("source_uri + amount", ("source_uri", "supported_amount_usd")),
    ("accession + amount", ("accession", "supported_amount_usd")),
    ("instrument-key (hash+amount+category)", ("content_hash", "supported_amount_usd", "category")),
    ("content_hash alone (over-collapses)", ("content_hash",)),
]


def _approved_rows(decisions_csv: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with decisions_csv.open() as handle:
        for record in csv.DictReader(handle):
            if record.get("metric_use_status") != "approved_for_metric_use":
                continue
            match = _ACCESSION_RE.search(record.get("source_uri", ""))
            record["accession"] = match.group(1) if match else ""
            rows.append(record)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Checkout whose decisions CSV to read (default: this checkout).",
    )
    args = parser.parse_args()
    decisions_csv = args.repo_root / "data" / "reports" / "materiality_adjudication_decisions.csv"

    print(f"Metric-aggregation simulator: {decisions_csv}")
    if not decisions_csv.exists():
        print("  decisions CSV not found (point --repo-root at the checkout that holds data/).")
        return 0

    rows = _approved_rows(decisions_csv)
    results = simulate(rows, STRATEGIES)
    print(f"  approved_for_metric_use rows: {len(rows)}\n")
    print(f"  {'strategy':40s} {'total($T)':>11s} {'groups':>8s} {'Δ vs current($B)':>18s}")
    for result in results:
        print(
            f"  {result.strategy:40s} {result.total_usd / 1e12:11.3f} "
            f"{result.group_count:8d} {result.delta_vs_baseline_usd / 1e9:18.1f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
