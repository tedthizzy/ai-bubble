#!/usr/bin/env python
"""Review mixed-evidence same-document final-metric collision candidates."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from bubble.quality.mixed_evidence_collisions import summarize_mixed_evidence_collisions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--decisions",
        type=Path,
        default=Path("data/reports/materiality_adjudication_decisions.csv"),
        help="Materiality adjudication decisions CSV.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full JSON summary instead of a compact text summary.",
    )
    args = parser.parse_args()

    rows = _load_rows(args.decisions)
    summary = summarize_mixed_evidence_collisions(rows)
    if args.json:
        print(json.dumps(summary, indent=2))
        return 0

    print(f"Mixed-evidence collision review: {args.decisions}")
    print(f"  candidate groups: {summary['candidate_group_count']}")
    print(f"  aggregate/component candidates: {summary['aggregate_component_candidate_count']}")
    print(f"  distinct-facility candidates: {summary['distinct_facility_candidate_count']}")
    print(f"  candidate total: ${summary['candidate_total_usd']:,.2f}")
    print(
        "  aggregate-candidate excess if confirmed: "
        f"${summary['aggregate_candidate_excess_usd']:,.2f}"
    )
    print(f"  AI-linked candidates: {summary['ai_linked_candidate_count']}")
    print(f"  AI-linked aggregate candidates: {summary['ai_linked_aggregate_candidate_count']}")
    print()
    for candidate in summary["candidates"][:15]:
        _print_candidate(candidate)
    return 0


def _load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise SystemExit(f"No decisions CSV found: {path}")
    with path.open() as handle:
        return list(csv.DictReader(handle))


def _print_candidate(candidate: dict[str, Any]) -> None:
    print(
        "  - "
        f"{candidate['classification']}: {candidate['entity']} "
        f"largest=${candidate['largest_amount_usd']:,.2f} "
        f"sum_rest=${candidate['sum_of_rest_usd']:,.2f} "
        f"excess=${candidate['excess_if_aggregate_collapsed_usd']:,.2f} "
        f"ai_linked={candidate['ai_linked']}"
    )
    print(f"    packets={candidate['packet_ids']}")


if __name__ == "__main__":
    raise SystemExit(main())
