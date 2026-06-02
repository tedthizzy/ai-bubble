"""Cross-filing duplication: the residual RC2 that the per-hash dedup misses.

The metric dedups by ``metric_group_id`` (``source-instrument:hashes:<hash>:amount:<amt>``),
so the same aggregate obligation extracted from N different filings of the same issuer -- each
filing a distinct content hash, hence a distinct group -- is counted N times. The signature is
a same issuer + an identical ``supported_amount_usd`` across >=3 distinct groups (e.g. a
$18.4B aggregate-debt figure pulled from a company's Series A-E note prospectuses, not five
$18.4B deals).

``summarize_cross_filing_duplication`` flags those families and estimates the removable excess
(``amount x (distinct_groups - 1)``). Confidence is ``high`` for an odd-precision amount or
many repeats (an exact figure repeated is almost certainly one obligation re-extracted) and
``medium`` for a round amount repeated few times (could be genuinely distinct facilities).
Pure function; collapsing these is an extension of the economic-obligation dedup.
"""

from __future__ import annotations

import collections
import re
from typing import Any

_SPV_SUFFIX = re.compile(
    r"\b(holdco|landco|opco|computeco|hpc holdings|eln-?\d+|far-?\d+|spv|borrower|holdings|llc"
    r"|inc|corp|co|l\.?p\.?|ltd|plc|finance|funding|trust|series \w+)\b",
    re.I,
)


def _root(name: str) -> str:
    stripped = _SPV_SUFFIX.sub("", (name or "").lower())
    return re.sub(r"[^a-z0-9]", "", stripped)[:12]


def _amount(value: str) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _confidence(amount: float, groups: int) -> str:
    # An odd-precision figure (sub-billion digits, e.g. $18.4B / $2.35B) repeated across
    # filings is near-certainly one obligation re-extracted -- high confidence. A round
    # amount ($4B / $10B) could be genuinely distinct facilities -> medium, verify per case.
    odd_precision = round(amount) % 1_000_000_000 != 0
    return "high" if odd_precision else "medium"


_DESCR = re.compile(r"(\d\.\d{2,3})\s?%|due (\d{4})", re.I)


def _descriptor(quote: str) -> frozenset[str]:
    """Instrument fingerprint from a quote: coupon rate(s) + maturity year(s)."""

    parts: set[str] = set()
    for coupon, year in _DESCR.findall(quote or ""):
        if coupon:
            parts.add("c" + coupon)
        if year:
            parts.add("y" + year)
    return frozenset(parts)


def _tier(group_descriptors: list[frozenset[str]]) -> str:
    """Tier a family by whether its groups describe the SAME instrument.

    ``confirmed_same_instrument`` -- the groups that carry a coupon/maturity fingerprint share
    a common one (one instrument re-extracted across filings). ``likely_distinct_instruments``
    -- groups carry different fingerprints (genuinely different same-size deals -> NOT a dup).
    ``uncertain_no_descriptor`` -- no fingerprints to judge (e.g. boilerplate-quote aggregates
    like a company's total-debt figure; needs another signal).
    """

    described = [d for d in group_descriptors if d]
    if not described:
        return "uncertain_no_descriptor"
    if set.intersection(*(set(d) for d in described)):
        return "confirmed_same_instrument"
    if len(described) >= 2:
        return "likely_distinct_instruments"
    return "uncertain_no_descriptor"


def summarize_cross_filing_duplication(
    rows: list[dict[str, str]],
    *,
    min_groups: int = 3,
    min_amount: float = 5e8,
    amount_key: str = "supported_amount_usd",
    group_key: str = "metric_group_id",
    entity_key: str = "entity",
) -> dict[str, Any]:
    """Flag same-(issuer, amount) obligations repeated across >=min_groups distinct groups."""

    # (entity_root, rounded_amount) -> group_id -> instrument descriptor (union over its rows)
    families: dict[tuple[str, int], dict[str, set[str]]] = collections.defaultdict(
        lambda: collections.defaultdict(set)
    )
    name_for: dict[tuple[str, int], str] = {}
    for row in rows:
        if row.get("metric_use_status") != "approved_for_metric_use":
            continue
        group = row.get(group_key) or ""
        if not group.startswith("source-instrument:"):
            continue
        amount = _amount(row.get(amount_key, ""))
        if amount < min_amount:
            continue
        key = (_root(row.get(entity_key, "")), round(amount))
        families[key][group].update(_descriptor(row.get("evidence_quote", "")))
        name_for.setdefault(key, row.get(entity_key, ""))

    suspects: list[dict[str, Any]] = []
    removable = 0.0
    by_tier: dict[str, float] = collections.defaultdict(float)
    for (root, amount), group_descr in families.items():
        if len(group_descr) < min_groups:
            continue
        excess = amount * (len(group_descr) - 1)
        removable += excess
        tier = _tier([frozenset(d) for d in group_descr.values()])
        by_tier[tier] += excess
        suspects.append(
            {
                "entity": name_for[(root, amount)],
                "entity_root": root,
                "amount_usd": float(amount),
                "distinct_groups": len(group_descr),
                "removable_excess_usd": round(excess, 2),
                "confidence": _confidence(amount, len(group_descr)),
                "tier": tier,
            }
        )

    suspects.sort(key=lambda s: s["removable_excess_usd"], reverse=True)
    high = sum(s["removable_excess_usd"] for s in suspects if s["confidence"] == "high")
    return {
        "suspect_families": len(suspects),
        "removable_excess_usd": round(removable, 2),
        "removable_excess_high_confidence_usd": round(high, 2),
        "confirmed_same_instrument_usd": round(by_tier["confirmed_same_instrument"], 2),
        "likely_distinct_instruments_usd": round(by_tier["likely_distinct_instruments"], 2),
        "uncertain_no_descriptor_usd": round(by_tier["uncertain_no_descriptor"], 2),
        "top_suspects": suspects[:30],
    }


def summarize_cross_filing_collapse(
    rows: list[dict[str, Any]],
    *,
    entity_key: str = "entity",
    amount_key: str = "amount_usd",
    accession_key: str = "accession",
    quote_key: str = "evidence_quote",
) -> dict[str, Any]:
    """Strict cross-filing collapse: the verified -$48.8B rule (reference implementation).

    Operates on within-filing-collapsed rows (one per entity/amount/accession). Groups by
    (entity_root, rounded_amount); a bucket spanning >=2 distinct accessions collapses to ONE
    representative ONLY IF every member has a non-empty coupon/maturity descriptor AND a single token
    is common to ALL of them. This is deliberately stricter than ``_tier`` (which ignores
    empty-descriptor members) and than pairwise union-find (which chains members that do not all share
    one instrument and over-collapses); both are rejected by the test negative-controls.
    """

    families: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in rows:
        entity = str(row.get(entity_key, "") or "")
        amount = _amount(str(row.get(amount_key, "") or "0"))
        accession = str(row.get(accession_key, "") or "")
        if not entity or amount <= 0 or not accession:
            continue
        families.setdefault((_root(entity), round(amount)), []).append(row)

    collapsed_excess = 0.0
    collapsed_groups = 0
    for (_root_key, amount_key_value), members in families.items():
        accessions = {str(m.get(accession_key, "") or "") for m in members}
        if len(accessions) < 2:
            continue  # single filing -> within-filing pass handles it
        descriptors = [_descriptor(str(m.get(quote_key, "") or "")) for m in members]
        if not all(descriptors):
            continue  # strict: every member must carry a fingerprint
        if set.intersection(*(set(d) for d in descriptors)):
            collapsed_excess += (len(accessions) - 1) * amount_key_value
            collapsed_groups += 1

    return {
        "collapsed_group_count": collapsed_groups,
        "collapsed_excess_usd": round(collapsed_excess, 2),
    }
