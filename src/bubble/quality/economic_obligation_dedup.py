"""Economic-obligation dedup (root cause 2 fix harness).

The metric groups by ``source-instrument:hashes:<content_hash>`` — the document — so
the same obligation re-disclosed across N filings is counted N times. The fix is to
group on **economic-obligation identity** instead. ``economic_obligation_key`` derives
that key from the entity + rounded amount (+ optional maturity / counterparty
discriminators when present), so the same TeraWulf $3.2B note across 8 filings
collapses to one group while two genuinely distinct obligations stay separate.

``summarize_economic_dedup`` simulates the fix: it reports the raw approved
source-instrument sum, the deduped sum under economic-obligation keys, and the excess
removed — i.e. how much the headline drops once RC2 is fixed. Pure functions; the
production grouping change is Codex's.
"""

from __future__ import annotations

import re
from typing import Any


def _amount(row: dict[str, str]) -> float:
    try:
        return float(row.get("supported_amount_usd") or 0.0)
    except ValueError:
        return 0.0


def _norm_entity(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def economic_obligation_key(row: dict[str, str], *, use_discriminators: bool = True) -> str:
    """Identity key for one economic obligation, independent of which filing disclosed it.

    Primary key is ``entity | rounded_amount``. When ``use_discriminators`` and the
    fields are present, a maturity/snapshot-date and counterparty discriminator is
    appended so two distinct same-amount obligations of one entity are not merged.
    """

    entity = _norm_entity(row.get("entity", ""))
    amount = round(_amount(row))
    parts = [entity, str(amount)]
    if use_discriminators:
        maturity = (row.get("metric_snapshot_date") or row.get("maturity") or "").strip()[:7]
        counterparty = _norm_entity(row.get("counterparty", ""))[:24]
        if maturity:
            parts.append(maturity)
        if counterparty:
            parts.append(counterparty)
    return "|".join(parts)


def summarize_economic_dedup(
    rows: list[dict[str, str]],
    *,
    use_discriminators: bool = False,
) -> dict[str, Any]:
    """Simulate RC2: raw vs economic-obligation-deduped approved source-instrument sum.

    ``use_discriminators=False`` is the aggressive (entity+amount) bound; True is the
    conservative bound that also splits on maturity/counterparty when available.
    """

    groups: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("metric_use_status") != "approved_for_metric_use":
            continue
        gid = row.get("metric_group_id") or ""
        if not gid.startswith("source-instrument:"):
            continue
        if gid not in groups or _amount(row) > _amount(groups[gid]):
            groups[gid] = row

    raw_sum = sum(_amount(r) for r in groups.values())
    deduped: dict[str, float] = {}
    cluster_sizes: dict[str, int] = {}
    for row in groups.values():
        key = economic_obligation_key(row, use_discriminators=use_discriminators)
        deduped[key] = max(deduped.get(key, 0.0), _amount(row))
        cluster_sizes[key] = cluster_sizes.get(key, 0) + 1
    deduped_sum = sum(deduped.values())
    collapsed = sorted(
        ((k, cluster_sizes[k], deduped[k]) for k in cluster_sizes if cluster_sizes[k] > 1),
        key=lambda t: t[2] * (t[1] - 1),
        reverse=True,
    )
    return {
        "source_instrument_groups": len(groups),
        "economic_obligations": len(deduped),
        "raw_sum_usd": round(raw_sum, 2),
        "deduped_sum_usd": round(deduped_sum, 2),
        "dedup_excess_usd": round(raw_sum - deduped_sum, 2),
        "top_collapsed": [
            {"key": k, "filings": n, "amount_usd": amt} for k, n, amt in collapsed[:10]
        ],
    }
