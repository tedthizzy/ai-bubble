"""Graph notional-dedup: turn an inflated edge-notional sum into a real exposure figure.

A capital/contract graph stores each obligation's notional on every edge that touches it --
a single deal/tranche appears on its obligor edge, each collateral edge, each risk-bearer
edge, and each risk-flag edge. Naively summing ``notional_usd`` therefore over-counts by the
average edge-multiplicity (the contract graph shows ``spv_signal`` = "$49T", non_recourse =
"$7.3T" -- non-additive artifacts, not exposure).

``summarize_graph_notional`` collapses to one notional per distinct obligation (deal+tranche)
and reports raw vs deduped + the inflation factor, overall and per relationship_type. Pure
function; deduping by economic obligation is the same RC2 principle applied at the graph layer.
"""

from __future__ import annotations

import collections
from typing import Any


def _amount(value: str) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def summarize_graph_notional(
    edges: list[dict[str, str]],
    *,
    deal_key: str = "deal_id",
    tranche_key: str = "tranche_id",
    amount_key: str = "notional_usd",
    relationship_key: str = "relationship_type",
) -> dict[str, Any]:
    """Raw vs obligation-deduped notional + inflation factor, overall and per relationship."""

    raw = 0.0
    seen: set[tuple[str, str, int]] = set()
    deduped = 0.0
    by_rel: dict[str, dict[str, Any]] = collections.defaultdict(
        lambda: {"edges": 0, "raw_notional_usd": 0.0, "_seen": set(), "deduped_notional_usd": 0.0}
    )

    for edge in edges:
        amount = _amount(edge.get(amount_key, ""))
        obligation = (
            edge.get(deal_key) or "",
            edge.get(tranche_key) or "",
            round(amount),
        )
        raw += amount
        if obligation not in seen:
            seen.add(obligation)
            deduped += amount

        rel = edge.get(relationship_key) or "?"
        bucket = by_rel[rel]
        bucket["edges"] += 1
        bucket["raw_notional_usd"] += amount
        if obligation not in bucket["_seen"]:
            bucket["_seen"].add(obligation)
            bucket["deduped_notional_usd"] += amount

    by_relationship: dict[str, dict[str, Any]] = {}
    for rel, bucket in by_rel.items():
        by_relationship[rel] = {
            "edges": bucket["edges"],
            "raw_notional_usd": round(bucket["raw_notional_usd"], 2),
            "deduped_notional_usd": round(bucket["deduped_notional_usd"], 2),
        }

    return {
        "edges": len(edges),
        "distinct_obligations": len(seen),
        "raw_notional_usd": round(raw, 2),
        "deduped_notional_usd": round(deduped, 2),
        "inflation_factor": round(raw / deduped, 4) if deduped else 1.0,
        "by_relationship": by_relationship,
    }
