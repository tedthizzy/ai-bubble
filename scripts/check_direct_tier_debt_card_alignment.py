#!/usr/bin/env python
"""Compare direct-tier metric survivors against normalized debt-service cards.

This is a read-only QA surface. It does not change final metric totals; it
shows where the current materiality metric for direct AI/data-center issuers is
larger than the debt facilities already carded for that issuer. Those gaps are
review targets for economic-event dedupe, source quote reselection, or more
primary debt-service extraction.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from bubble.analysis.materiality_adjudication_results import (
    FINAL_METRIC_DECISIONS,
    MaterialityAdjudicationDecision,
    _final_metric_representative_decisions,
    _json_list,
)

ENTITY_ALIASES: dict[str, tuple[str, ...]] = {
    "Applied Digital": ("applied digital",),
    "CleanSpark": ("cleanspark",),
    "CoreWeave": ("coreweave",),
    "Hut 8": ("hut 8",),
    "IREN": ("iren",),
    "MARA Holdings": ("mara holdings",),
    "Nebius": ("nebius",),
    "TeraWulf": ("terawulf",),
}


@dataclass(frozen=True)
class DirectTierAlignment:
    entity: str
    survivor_count: int
    current_metric_usd: float
    all_carded_facility_usd: float
    primary_verified_carded_usd: float
    unverified_carded_usd: float
    metric_less_all_carded_usd: float
    metric_less_primary_verified_usd: float
    status: str

    def to_row(self) -> dict[str, str]:
        row = asdict(self)
        return {
            key: f"{value:.2f}" if isinstance(value, float) else str(value)
            for key, value in row.items()
        }


def load_decisions(path: Path) -> list[MaterialityAdjudicationDecision]:
    with path.open(newline="", errors="ignore") as handle:
        return [_row_to_decision(row) for row in csv.DictReader(handle)]


def load_carded_facilities(
    path: Path,
) -> dict[str, tuple[float, float, float]]:
    all_carded: defaultdict[str, float] = defaultdict(float)
    primary_carded: defaultdict[str, float] = defaultdict(float)
    unverified_carded: defaultdict[str, float] = defaultdict(float)
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            entity = _canonical_card_entity(row.get("entity", ""))
            if not entity:
                continue
            amount = _float(row.get("facility_size_usd"))
            if amount <= 0:
                continue
            all_carded[entity] += amount
            if row.get("verification_status") == "primary_verified":
                primary_carded[entity] += amount
            else:
                unverified_carded[entity] += amount
    return {
        entity: (
            all_carded[entity],
            primary_carded[entity],
            unverified_carded[entity],
        )
        for entity in sorted(all_carded)
    }


def build_alignment_rows(
    decisions: list[MaterialityAdjudicationDecision],
    carded: dict[str, tuple[float, float, float]],
) -> list[DirectTierAlignment]:
    survivors = _final_metric_representative_decisions(decisions)
    survivor_amounts: defaultdict[str, float] = defaultdict(float)
    survivor_counts: defaultdict[str, int] = defaultdict(int)
    for decision in survivors:
        if decision.metric_use_status not in FINAL_METRIC_DECISIONS:
            continue
        entity = _canonical_decision_entity(decision.entity)
        if not entity:
            continue
        survivor_amounts[entity] += decision.supported_amount_usd
        survivor_counts[entity] += 1

    rows: list[DirectTierAlignment] = []
    for entity in sorted(set(carded) | set(survivor_amounts)):
        all_carded, primary_carded, unverified_carded = carded.get(entity, (0.0, 0.0, 0.0))
        current_metric = survivor_amounts.get(entity, 0.0)
        rows.append(
            DirectTierAlignment(
                entity=entity,
                survivor_count=survivor_counts.get(entity, 0),
                current_metric_usd=round(current_metric, 2),
                all_carded_facility_usd=round(all_carded, 2),
                primary_verified_carded_usd=round(primary_carded, 2),
                unverified_carded_usd=round(unverified_carded, 2),
                metric_less_all_carded_usd=round(current_metric - all_carded, 2),
                metric_less_primary_verified_usd=round(current_metric - primary_carded, 2),
                status=_alignment_status(current_metric, all_carded, primary_carded),
            )
        )
    return sorted(rows, key=lambda row: row.metric_less_all_carded_usd, reverse=True)


def _alignment_status(current_metric: float, all_carded: float, primary_carded: float) -> str:
    if current_metric <= 0:
        return "no_metric_survivor"
    if all_carded <= 0:
        return "missing_debt_card"
    if current_metric > all_carded * 1.1:
        return "review_metric_exceeds_carded_facilities"
    if current_metric > primary_carded * 1.1:
        return "needs_primary_verification"
    return "aligned_to_primary_cards"


def _canonical_card_entity(entity: str) -> str:
    lowered = entity.lower()
    for canonical, aliases in ENTITY_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            return canonical
    return ""


def _canonical_decision_entity(entity: str) -> str:
    lowered = entity.lower()
    if "marathon petroleum" in lowered:
        return ""
    return _canonical_card_entity(entity)


def _row_to_decision(row: dict[str, str]) -> MaterialityAdjudicationDecision:
    return MaterialityAdjudicationDecision(
        packet_id=row["packet_id"],
        rank=_int(row["rank"]),
        review_id=row["review_id"],
        review_group_id=row["review_group_id"],
        priority=row["priority"],
        category=row["category"],
        subcategory=row["subcategory"],
        ecosystem_relevance=row["ecosystem_relevance"],
        entity=row["entity"],
        counterparty=row["counterparty"],
        exposure_basis_usd=_float(row["exposure_basis_usd"]),
        decision=row["decision"],
        metric_use_status=row["metric_use_status"],
        source_support=row["source_support"],
        confidence=_float(row["confidence"]),
        supported_amount_usd=_float(row["supported_amount_usd"]),
        metric_group_id=row["metric_group_id"],
        metric_snapshot_date=row["metric_snapshot_date"],
        metric_aggregation_policy=row["metric_aggregation_policy"],
        duplicate_or_aggregate=row["duplicate_or_aggregate"],
        ai_data_center_linkage=row["ai_data_center_linkage"],
        risk_bearer=row["risk_bearer"],
        remaining_gap=row["remaining_gap"],
        required_next_extraction=row["required_next_extraction"],
        metric_dedupe_quote=row["metric_dedupe_quote"],
        evidence_quote=row["evidence_quote"],
        evidence_quote_refs=tuple(_json_list(row["evidence_quote_refs"])),
        rationale=row["rationale"],
        adjudicator_id=row["adjudicator_id"],
        adjudicated_at=row["adjudicated_at"],
        source_uri=row["source_uri"],
        source_uris=tuple(_json_list(row["source_uris"])),
        content_hash=row["content_hash"],
        content_hashes=tuple(_json_list(row["content_hashes"])),
        packet_reason=row["packet_reason"],
    )


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _write_rows(path: Path, rows: list[DirectTierAlignment]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(DirectTierAlignment.__annotations__))
        writer.writeheader()
        writer.writerows(row.to_row() for row in rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--decisions",
        type=Path,
        default=Path("data/reports/materiality_adjudication_decisions.csv"),
    )
    parser.add_argument(
        "--terms",
        type=Path,
        default=Path("handoffs/fixtures/direct_tier_debt_service_terms_20260602.csv"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rows = build_alignment_rows(
        load_decisions(args.decisions),
        load_carded_facilities(args.terms),
    )
    if args.output:
        _write_rows(args.output, rows)
    print(
        json.dumps(
            {
                "entity_count": len(rows),
                "current_metric_usd": round(sum(row.current_metric_usd for row in rows), 2),
                "all_carded_facility_usd": round(
                    sum(row.all_carded_facility_usd for row in rows), 2
                ),
                "primary_verified_carded_usd": round(
                    sum(row.primary_verified_carded_usd for row in rows), 2
                ),
                "review_metric_exceeds_carded_facilities": sum(
                    row.status == "review_metric_exceeds_carded_facilities" for row in rows
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
