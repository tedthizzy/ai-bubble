"""Review mixed-evidence final-metric collisions.

These checks identify same-entity, same-document, same-metric-quote groups that
survive final metric dedupe because their supporting evidence quotes differ.
That pattern can be legitimate multi-facility financing, or an
aggregate-plus-components overcount. This module only classifies review
candidates; it does not change metric totals.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from bubble.quality.relevance_linkage import final_metric_representative_rows

AGGREGATE_COMPONENT_TOLERANCE = 0.05
AI_LINKAGES = {"direct", "watchlist", "physical", "compute"}


def summarize_mixed_evidence_collisions(rows: list[dict[str, str]]) -> dict[str, Any]:
    """Summarize mixed-evidence same-document collision candidates."""

    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in final_metric_representative_rows(rows):
        key = _mixed_evidence_key(row)
        if key is None:
            continue
        grouped.setdefault(key, []).append(row)

    candidates = [
        _candidate_summary(group_rows)
        for group_rows in grouped.values()
        if _is_mixed_evidence_group(group_rows)
    ]
    candidates.sort(
        key=lambda candidate: (
            candidate["classification"] != "aggregate_component_candidate",
            -candidate["excess_if_aggregate_collapsed_usd"],
            -candidate["total_usd"],
            candidate["entity"],
        )
    )

    aggregate_candidates = [
        candidate
        for candidate in candidates
        if candidate["classification"] == "aggregate_component_candidate"
    ]
    ai_linked_candidates = [candidate for candidate in candidates if candidate["ai_linked"]]
    return {
        "candidate_group_count": len(candidates),
        "aggregate_component_candidate_count": len(aggregate_candidates),
        "distinct_facility_candidate_count": len(candidates) - len(aggregate_candidates),
        "candidate_total_usd": round(sum(c["total_usd"] for c in candidates), 2),
        "aggregate_candidate_excess_usd": round(
            sum(c["excess_if_aggregate_collapsed_usd"] for c in aggregate_candidates), 2
        ),
        "ai_linked_candidate_count": len(ai_linked_candidates),
        "ai_linked_aggregate_candidate_count": sum(
            1
            for candidate in ai_linked_candidates
            if candidate["classification"] == "aggregate_component_candidate"
        ),
        "candidates": candidates,
    }


def _mixed_evidence_key(row: dict[str, str]) -> tuple[str, str, str] | None:
    if row.get("metric_aggregation_policy") != "max_amount_per_source_instrument":
        return None
    entity_key = _slug(row.get("entity", ""))
    hashes = tuple(sorted(hash_value for hash_value in _json_list(row.get("content_hashes"))))
    content_hash = hashes[0] if hashes else row.get("content_hash", "")
    metric_quote_key = _normalized_quote_fingerprint(row.get("metric_dedupe_quote", ""))
    if not entity_key or not content_hash or not metric_quote_key:
        return None
    return entity_key, content_hash, metric_quote_key


def _is_mixed_evidence_group(rows: list[dict[str, str]]) -> bool:
    evidence_quote_keys = {
        _normalized_quote_fingerprint(row.get("evidence_quote", "")) for row in rows
    }
    return len(rows) > 1 and len(evidence_quote_keys - {""}) > 1


def _candidate_summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    amounts = [_float(row.get("supported_amount_usd")) for row in rows]
    largest = max(amounts, default=0.0)
    sum_of_rest = max(sum(amounts) - largest, 0.0)
    excess = sum_of_rest if _largest_matches_sum_of_rest(largest, sum_of_rest) else 0.0
    linkages = sorted({(row.get("ai_data_center_linkage") or "").lower() for row in rows})
    packet_ids = sorted(row.get("packet_id", "") for row in rows if row.get("packet_id"))
    source_uris = sorted({row.get("source_uri", "") for row in rows if row.get("source_uri")})
    evidence_quotes = sorted(
        {row.get("evidence_quote", "")[:220] for row in rows if row.get("evidence_quote")}
    )
    return {
        "entity": rows[0].get("entity", ""),
        "content_hash": (
            rows[0].get("content_hash") or _json_list(rows[0].get("content_hashes"))[0]
        )[:16],
        "classification": (
            "aggregate_component_candidate" if excess > 0 else "distinct_facility_candidate"
        ),
        "ai_linked": any(linkage in AI_LINKAGES for linkage in linkages),
        "ai_linkages": ";".join(linkages),
        "row_count": len(rows),
        "total_usd": round(sum(amounts), 2),
        "largest_amount_usd": round(largest, 2),
        "sum_of_rest_usd": round(sum_of_rest, 2),
        "excess_if_aggregate_collapsed_usd": round(excess, 2),
        "packet_ids": ";".join(packet_ids),
        "source_uris": ";".join(source_uris),
        "evidence_quotes": " || ".join(evidence_quotes),
    }


def _largest_matches_sum_of_rest(largest: float, sum_of_rest: float) -> bool:
    if largest <= 0 or sum_of_rest <= 0:
        return False
    return abs(largest - sum_of_rest) / largest <= AGGREGATE_COMPONENT_TOLERANCE


def _normalized_quote_fingerprint(quote: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", quote.lower()).strip()
    if len(normalized) < 80:
        return ""
    return hashlib.sha1(normalized.encode()).hexdigest()


def _json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return []
    return [str(item) for item in loaded if item]


def _float(value: str | None) -> float:
    try:
        return float(value or 0)
    except ValueError:
        return 0.0


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
