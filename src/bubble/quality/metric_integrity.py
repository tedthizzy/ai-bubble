"""Approved-group metric-integrity over-count checker (read-only QA).

Quantifies broad over-count signals in approved materiality groups. This is a
diagnostic screen over source-instrument / aggregate-snapshot groups, not the
authoritative final representative metric. Use it to find residual suspect
families, then reproduce any dollar impact against the production
``_final_metric_representative_decisions`` pipeline before changing reported
totals.

* ``mega_misextraction``: approved ``source-instrument`` groups whose single
  "obligation" exceeds ``mega_threshold`` (default $50B). Almost all are
  financial-sector asset/capacity/boilerplate figures mis-extracted as debt
  (root cause 1). Watch ``mega_gross_usd`` → 0 as the amount-plausibility guard
  and asset/capacity classifier land.
* ``crossfiling_excess_usd``: the same obligation re-disclosed across N filings is
  counted N times because the group key is the document ``content_hash`` (root
  cause 2). Reported as the identical-quote floor (conservative).
* ``aggregate_snapshot_dup_usd``: an ``aggregate-obligation-snapshot`` group whose
  ``content_hash`` matches a ``source-instrument`` group is the same obligation
  counted twice (root cause 2, cross-namespace).

``implied_overcount_usd`` sums the three broad signals (the cross-filing/snapshot
terms are computed on ``<= mega_threshold`` groups, so they are disjoint from the
mega term). All inputs are materiality decision rows; nothing here reaches the
graph (root cause 3 lives in a separate checker).
"""

from __future__ import annotations

import re
from typing import Any

APPROVED = "approved_for_metric_use"
SOURCE_INSTRUMENT = "source-instrument:"
AGGREGATE_SNAPSHOT = "aggregate-obligation-snapshot:"


def _amount(row: dict[str, str], key: str = "supported_amount_usd") -> float:
    try:
        return float(row.get(key) or 0.0)
    except ValueError:
        return 0.0


def _quote_key(row: dict[str, str]) -> str:
    return re.sub(r"[^a-z0-9]", "", (row.get("evidence_quote") or "").lower())[:60]


def _representative_groups(rows: list[dict[str, str]], prefix: str) -> dict[str, dict[str, str]]:
    """One row per ``metric_group_id`` with the given prefix (max supported amount)."""

    groups: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("metric_use_status") != APPROVED:
            continue
        gid = row.get("metric_group_id") or ""
        if not gid.startswith(prefix):
            continue
        current = groups.get(gid)
        if current is None or _amount(row) > _amount(current):
            groups[gid] = row
    return groups


def summarize_metric_integrity(
    rows: list[dict[str, str]],
    *,
    mega_threshold: float = 50e9,
) -> dict[str, Any]:
    """Summarise the three verified over-count signals from the decision rows."""

    si_groups = _representative_groups(rows, SOURCE_INSTRUMENT)
    snap_groups = _representative_groups(rows, AGGREGATE_SNAPSHOT)

    # Root cause 1: mega single-obligation groups.
    mega = [r for r in si_groups.values() if _amount(r) > mega_threshold]
    mega_gross = sum(_amount(r) for r in mega)

    # Root cause 2a: identical-quote cross-filing duplication among <= threshold groups.
    plausible = [r for r in si_groups.values() if _amount(r) <= mega_threshold]
    clusters: dict[tuple[str, int, str], list[dict[str, str]]] = {}
    for row in plausible:
        key = (row.get("entity", "").strip().lower(), round(_amount(row)), _quote_key(row))
        clusters.setdefault(key, []).append(row)
    crossfiling_excess = sum(
        key[1] * (len(members) - 1) for key, members in clusters.items() if len(members) > 1
    )

    # Root cause 2b: aggregate-snapshot group sharing a content_hash with a source-instrument group.
    si_hashes = {(r.get("content_hash") or "").strip() for r in si_groups.values()}
    si_hashes.discard("")
    snapshot_dup = sum(
        _amount(r) for r in snap_groups.values() if (r.get("content_hash") or "").strip() in si_hashes
    )

    base = sum(_amount(r) for r in si_groups.values()) + sum(_amount(r) for r in snap_groups.values())
    implied = mega_gross + crossfiling_excess + snapshot_dup
    return {
        "approved_source_instrument_groups": len(si_groups),
        "aggregate_snapshot_groups": len(snap_groups),
        "base_metric_usd": round(base, 2),
        "mega_misextraction_count": len(mega),
        "mega_gross_usd": round(mega_gross, 2),
        "crossfiling_excess_usd": round(crossfiling_excess, 2),
        "aggregate_snapshot_dup_usd": round(snapshot_dup, 2),
        "implied_overcount_usd": round(implied, 2),
    }
