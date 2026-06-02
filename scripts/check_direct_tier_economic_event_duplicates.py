#!/usr/bin/env python
"""Audit direct-tier metric survivors for repeated economic-event candidates.

This is read-only. It inspects the current final-metric survivor set and groups
direct AI/data-center issuers by canonical entity and supported amount. The
output is a review queue for possible economic-event dedupe, with explicit
negative controls when same-amount rows carry conflicting maturity/coupon
evidence.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bubble.analysis.materiality_adjudication_results import (
    FINAL_METRIC_DECISIONS,
    MaterialityAdjudicationDecision,
    _final_metric_representative_decisions,
    _instrument_descriptor_tokens,
    _metric_amount_key,
    _sec_accession,
)

from scripts.check_direct_tier_debt_card_alignment import (
    _canonical_decision_entity,
    load_decisions,
)


@dataclass(frozen=True)
class DirectTierEconomicEventCluster:
    entity: str
    amount_key: str
    row_count: int
    accession_count: int
    current_metric_usd: float
    max_single_event_usd: float
    possible_duplicate_excess_usd: float
    classification: str
    years: str
    coupons: str
    packet_ids: str
    accessions: str
    source_uris: str
    quote_snippets: str

    def to_row(self) -> dict[str, str]:
        row = asdict(self)
        return {
            key: f"{value:.2f}" if isinstance(value, float) else str(value)
            for key, value in row.items()
        }


def build_event_clusters(
    decisions: list[MaterialityAdjudicationDecision],
) -> list[DirectTierEconomicEventCluster]:
    survivors = [
        decision
        for decision in _final_metric_representative_decisions(decisions)
        if decision.metric_use_status in FINAL_METRIC_DECISIONS
    ]
    grouped: defaultdict[tuple[str, str], list[MaterialityAdjudicationDecision]] = defaultdict(list)
    for decision in survivors:
        entity = _canonical_decision_entity(decision.entity)
        amount_key = _metric_amount_key(decision.supported_amount_usd)
        if not entity or not amount_key or amount_key == "0":
            continue
        grouped[(entity, amount_key)].append(decision)

    clusters = [
        _cluster_from_decisions(entity, amount_key, cluster)
        for (entity, amount_key), cluster in grouped.items()
        if len(cluster) > 1
    ]
    return sorted(
        clusters,
        key=lambda row: (row.possible_duplicate_excess_usd, row.current_metric_usd),
        reverse=True,
    )


def _cluster_from_decisions(
    entity: str,
    amount_key: str,
    decisions: list[MaterialityAdjudicationDecision],
) -> DirectTierEconomicEventCluster:
    amount = max(decision.supported_amount_usd for decision in decisions)
    accessions = sorted(
        {_sec_accession(decision.source_uri) for decision in decisions if decision.source_uri}
    )
    descriptors = [_descriptor_parts(decision) for decision in decisions]
    years = sorted({year for descriptor in descriptors for year in descriptor[0]})
    coupons = sorted({coupon for descriptor in descriptors for coupon in descriptor[1]})
    current_metric = sum(decision.supported_amount_usd for decision in decisions)
    classification = _classify_cluster(decisions, years, coupons)
    return DirectTierEconomicEventCluster(
        entity=entity,
        amount_key=amount_key,
        row_count=len(decisions),
        accession_count=len(accessions),
        current_metric_usd=round(current_metric, 2),
        max_single_event_usd=round(amount, 2),
        possible_duplicate_excess_usd=round(current_metric - amount, 2),
        classification=classification,
        years=";".join(years),
        coupons=";".join(coupons),
        packet_ids=";".join(decision.packet_id for decision in decisions),
        accessions=";".join(accessions),
        source_uris=";".join(
            sorted({decision.source_uri for decision in decisions if decision.source_uri})
        ),
        quote_snippets=" || ".join(_quote_snippet(decision) for decision in decisions),
    )


def _descriptor_parts(decision: MaterialityAdjudicationDecision) -> tuple[set[str], set[str]]:
    text = " ".join(
        value
        for value in (
            decision.metric_dedupe_quote,
            decision.evidence_quote,
            decision.packet_reason,
        )
        if value
    )
    tokens = _instrument_descriptor_tokens(text)
    years = {token[1:] for token in tokens if token.startswith("y")}
    coupons = _coupon_descriptor_tokens(text)
    years.update(
        match.group(1)
        for match in re.finditer(
            r"\b(20[2-4]\d)\s+(?:notes?|senior\s+notes?|convertible\s+notes?)\b",
            text,
            re.I,
        )
    )
    return years, coupons


def _coupon_descriptor_tokens(text: str) -> set[str]:
    coupons: set[str] = set()
    lowered = text.lower()
    for match in re.finditer(r"\b(\d{1,2}\.\d{2,3})\s?%", text):
        context = lowered[max(0, match.start() - 90) : match.end() + 120]
        if re.search(r"\b(issue|offering)\s+price\b|\bpremium\b", context):
            continue
        if re.search(r"\b(coupon|interest|senior|secured|unsecured|notes?\s+due)\b", context):
            coupons.add(match.group(1))
    return coupons


def _classify_cluster(
    decisions: list[MaterialityAdjudicationDecision],
    years: list[str],
    coupons: list[str],
) -> str:
    accessions = {
        _sec_accession(decision.source_uri) for decision in decisions if decision.source_uri
    }
    if len(years) > 1 or len(coupons) > 1:
        return "distinct_facility_negative_control"
    if len(accessions) <= 1:
        return "same_accession_review"
    if years or coupons:
        return "probable_same_instrument_review"
    return "amount_only_review"


def _quote_snippet(decision: MaterialityAdjudicationDecision, *, max_len: int = 220) -> str:
    text = re.sub(
        r"\s+",
        " ",
        (decision.metric_dedupe_quote or decision.evidence_quote or decision.packet_reason).strip(),
    )
    snippet = text if len(text) <= max_len else text[: max_len - 3].rstrip() + "..."
    return f"{decision.packet_id}: {snippet}"


def _write_rows(path: Path, rows: list[DirectTierEconomicEventCluster]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(DirectTierEconomicEventCluster.__annotations__),
        )
        writer.writeheader()
        writer.writerows(row.to_row() for row in rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--decisions",
        type=Path,
        default=Path("data/reports/materiality_adjudication_decisions.csv"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rows = build_event_clusters(load_decisions(args.decisions))
    if args.output:
        _write_rows(args.output, rows)
    by_classification: defaultdict[str, int] = defaultdict(int)
    excess_by_classification: defaultdict[str, float] = defaultdict(float)
    for row in rows:
        by_classification[row.classification] += 1
        excess_by_classification[row.classification] += row.possible_duplicate_excess_usd
    print(
        json.dumps(
            {
                "cluster_count": len(rows),
                "possible_duplicate_excess_usd": round(
                    sum(row.possible_duplicate_excess_usd for row in rows), 2
                ),
                "by_classification": dict(sorted(by_classification.items())),
                "excess_by_classification": {
                    key: round(value, 2) for key, value in sorted(excess_by_classification.items())
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
