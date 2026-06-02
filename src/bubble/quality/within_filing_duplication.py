"""Within-filing duplication detector for the final-metric survivor set.

The final-metric dedup collapses representatives by source-hash, by (entity, amount, quote), and by
(entity, amount, subcategory, snapshot_month, counterparty). Running the real aggregation shows that
the SAME instrument in a SINGLE SEC filing can still survive multiple times, because intra-filing
drift defeats those keys: multiple content-hashes for the same instrument, the same amount
reclassified across subcategories, and an empty ``metric_snapshot_date`` on one copy. The result is
112 (entity, amount, accession) groups counted 2+ times in the metric (~$220B of excess).

This detector groups final-metric survivors by (entity, rounded-amount, SEC accession) -- a key
invariant to all that drift -- and reports the excess from the extra copies. ``excess_usd`` assumes
every copy beyond the first in a group is a duplicate, which spot-checks support (0/6 false
positives on the largest groups); a single filing describing two genuinely distinct instruments of
the identical amount is the rare false positive to confirm per-group. Pure functions; the proposed
production fix is an (entity, amount, accession) collapse key, which is Codex's to add.
"""

from __future__ import annotations

import re
from typing import Any

_ACCESSION = re.compile(r"/(\d{18})/")


def accession_from_uri(uri: str) -> str:
    """Extract the 18-digit SEC accession from an EDGAR document URI ('' if absent)."""

    match = _ACCESSION.search(uri or "")
    return match.group(1) if match else ""


def _amount(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def summarize_within_filing_duplication(
    rows: list[dict[str, Any]],
    *,
    entity_key: str = "entity",
    amount_key: str = "amount_usd",
    accession_key: str = "accession",
) -> dict[str, Any]:
    """Group final-metric survivors by (entity, amount, accession); report duplicate excess."""

    groups: dict[tuple[str, int, str], float] = {}
    for row in rows:
        entity = str(row.get(entity_key, "") or "")
        amount = _amount(row.get(amount_key))
        accession = str(row.get(accession_key, "") or "")
        if not entity or amount <= 0 or not accession:
            continue
        key = (entity, round(amount), accession)
        groups[key] = groups.get(key, 0.0) + 1

    duplicates = {key: count for key, count in groups.items() if count >= 2}
    excess = sum((count - 1) * key[1] for key, count in duplicates.items())
    detail = [
        {
            "entity": key[0],
            "amount_usd": key[1],
            "accession": key[2],
            "copies": int(count),
            "excess_usd": round((count - 1) * key[1], 2),
        }
        for key, count in sorted(duplicates.items(), key=lambda kv: -(kv[1] - 1) * kv[0][1])
    ]
    return {
        "duplicate_group_count": len(duplicates),
        "excess_usd": round(excess, 2),
        "groups": detail,
    }


def collapse_within_filing(
    rows: list[dict[str, Any]],
    *,
    entity_key: str = "entity",
    amount_key: str = "amount_usd",
    accession_key: str = "accession",
) -> dict[str, Any]:
    """Reference implementation of the within-filing fix: keep one row per (entity, amount, accession).

    Returns the corrected total and the kept rows -- the apply-ready collapse the production
    ``(entity, rounded-amount, accession)`` key performs. Rows lacking an entity/positive-amount/
    accession are passed through unchanged (they cannot form a within-filing group).
    """

    seen: set[tuple[str, int, str]] = set()
    kept: list[dict[str, Any]] = []
    raw_total = 0.0
    collapsed_total = 0.0
    for row in rows:
        entity = str(row.get(entity_key, "") or "")
        amount = _amount(row.get(amount_key))
        accession = str(row.get(accession_key, "") or "")
        raw_total += amount
        if not entity or amount <= 0 or not accession:
            kept.append(row)
            collapsed_total += amount
            continue
        key = (entity, round(amount), accession)
        if key in seen:
            continue
        seen.add(key)
        kept.append(row)
        collapsed_total += amount
    return {
        "raw_total_usd": round(raw_total, 2),
        "collapsed_total_usd": round(collapsed_total, 2),
        "removed_excess_usd": round(raw_total - collapsed_total, 2),
        "kept_rows": kept,
    }
