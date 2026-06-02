#!/usr/bin/env python
"""Validate direct-tier debt-event classification fixtures against live decisions.

The classification fixture is a review surface for economic-event dedupe. This
script does not alter metric aggregation; it verifies that every row points to a
live materiality decision and carries the fields needed for a production guard
or manual adjudication.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_direct_tier_debt_card_alignment import load_decisions

REQUIRED_COLUMNS = (
    "entity",
    "packet_id",
    "accession",
    "amount_usd",
    "ai_linked",
    "instrument_offering",
    "classification",
    "expected_behavior",
    "source_uri",
    "quote_excerpt",
)
ALLOWED_CLASSIFICATIONS = {"same_event", "distinct_facility", "needs_human_review"}


def load_classification_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def validate_classifications(
    rows: list[dict[str, str]],
    *,
    decisions_path: Path,
) -> tuple[list[str], dict[str, Any]]:
    decisions = {decision.packet_id: decision for decision in load_decisions(decisions_path)}
    errors: list[str] = []
    classes: Counter[str] = Counter()
    expected_behaviors: Counter[str] = Counter()
    same_event_amount = 0.0
    needs_review_amount = 0.0
    distinct_amount = 0.0

    for index, row in enumerate(rows, start=2):
        missing = [column for column in REQUIRED_COLUMNS if not row.get(column)]
        if missing:
            errors.append(f"row {index}: missing required columns {','.join(missing)}")
            continue
        classification = row["classification"]
        if classification not in ALLOWED_CLASSIFICATIONS:
            errors.append(f"row {index}: invalid classification {classification!r}")
        packet_id = row["packet_id"]
        decision = decisions.get(packet_id)
        if decision is None:
            errors.append(f"row {index}: packet_id {packet_id!r} not found in decisions")
            continue
        amount = _float(row["amount_usd"])
        if abs(amount - decision.supported_amount_usd) > 1:
            errors.append(
                f"row {index}: amount {amount:.2f} does not match decision "
                f"{decision.supported_amount_usd:.2f}"
            )
        if row["source_uri"] != decision.source_uri:
            errors.append(f"row {index}: source_uri does not match decision source_uri")
        if packet_id.startswith("ion:"):
            errors.append(f"row {index}: packet_id has truncated prefix {packet_id!r}")
        classes[classification] += 1
        expected_behaviors[_expected_behavior_bucket(row["expected_behavior"])] += 1
        if classification == "same_event":
            same_event_amount += amount
        elif classification == "needs_human_review":
            needs_review_amount += amount
        elif classification == "distinct_facility":
            distinct_amount += amount

    summary = {
        "row_count": len(rows),
        "error_count": len(errors),
        "by_classification": dict(sorted(classes.items())),
        "by_expected_behavior": dict(sorted(expected_behaviors.items())),
        "same_event_amount_usd": round(same_event_amount, 2),
        "needs_human_review_amount_usd": round(needs_review_amount, 2),
        "distinct_facility_amount_usd": round(distinct_amount, 2),
    }
    return errors, summary


def _expected_behavior_bucket(value: str) -> str:
    lowered = value.lower()
    if "keep" in lowered or "must not collapse" in lowered:
        return "keep"
    if "collapse" in lowered:
        return "collapse"
    if "exclude" in lowered or "rebind" in lowered:
        return "exclude_or_rebind"
    return "other"


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("handoffs/fixtures/direct_tier_debt_events_classified_20260602.csv"),
    )
    parser.add_argument(
        "--decisions",
        type=Path,
        default=Path("data/reports/materiality_adjudication_decisions.csv"),
    )
    args = parser.parse_args()

    errors, summary = validate_classifications(
        load_classification_rows(args.input),
        decisions_path=args.decisions,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
