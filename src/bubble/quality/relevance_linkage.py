"""Relevance-linkage split for materiality metric rows.

The materiality metric is source-backed debt/obligation support. This module
measures a separate question: how much of that support is currently tagged as
directly or watchlist-linked to AI/data-center activity.
"""

from __future__ import annotations

import collections
import hashlib
import json
import re
from typing import Any

FINAL_METRIC_STATUSES = {"approved_for_metric_use"}
DIRECT_LINKAGES = {"direct"}
WATCHLIST_LINKAGES = {"watchlist"}
ESTABLISHED_LINKAGES = {"direct", "watchlist", "physical", "compute"}


def summarize_relevance_linkage(
    rows: list[dict[str, str]],
    *,
    amount_key: str = "supported_amount_usd",
    linkage_key: str = "ai_data_center_linkage",
    entity_key: str = "entity",
) -> dict[str, Any]:
    """Split final metric representatives by AI/data-center linkage.

    The report headline uses final metric representatives after source and
    economic-obligation dedupe, not raw approved rows. This summary applies the
    same representative-row collapse before computing linkage buckets.
    """

    representatives = final_metric_representative_rows(rows)
    direct_usd = 0.0
    watchlist_usd = 0.0
    physical_or_compute_usd = 0.0
    not_established_usd = 0.0
    not_established_by_entity: dict[str, float] = collections.defaultdict(float)

    for row in representatives:
        amount = _float(row.get(amount_key))
        if amount <= 0:
            continue
        linkage = (row.get(linkage_key) or "").strip().lower()
        if linkage in DIRECT_LINKAGES:
            direct_usd += amount
        elif linkage in WATCHLIST_LINKAGES:
            watchlist_usd += amount
        elif linkage in {"physical", "compute"}:
            physical_or_compute_usd += amount
        else:
            not_established_usd += amount
            not_established_by_entity[row.get(entity_key, "")] += amount

    established_usd = direct_usd + watchlist_usd + physical_or_compute_usd
    total = established_usd + not_established_usd
    ranked = sorted(not_established_by_entity.items(), key=lambda item: item[1], reverse=True)
    top = [{"entity": entity, "usd": round(usd, 2)} for entity, usd in ranked if entity]
    return {
        "row_count": len(rows),
        "final_metric_group_count": len(representatives),
        "total_usd": round(total, 2),
        "direct_usd": round(direct_usd, 2),
        "watchlist_usd": round(watchlist_usd, 2),
        "physical_or_compute_usd": round(physical_or_compute_usd, 2),
        "established_usd": round(established_usd, 2),
        "not_established_usd": round(not_established_usd, 2),
        "direct_pct": _pct(direct_usd, total),
        "watchlist_pct": _pct(watchlist_usd, total),
        "established_pct": _pct(established_usd, total),
        "not_established_pct": _pct(not_established_usd, total),
        "top_not_established": top[:15],
    }


def final_metric_representative_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return the rows that contribute to the deduped final materiality metric."""

    direct: list[dict[str, str]] = []
    grouped: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("metric_use_status") not in FINAL_METRIC_STATUSES:
            continue
        policy = row.get("metric_aggregation_policy") or ""
        if policy == "latest_snapshot_per_metric_group":
            group_key = row.get("metric_group_id") or row.get("packet_id") or ""
            current = grouped.get(group_key)
            if current is None or _snapshot_sort_key(row) > _snapshot_sort_key(current):
                grouped[group_key] = row
            continue
        if policy == "max_amount_per_source_instrument":
            group_key = row.get("metric_group_id") or row.get("packet_id") or ""
            current = grouped.get(group_key)
            if current is None or _float(row.get("supported_amount_usd")) > _float(
                current.get("supported_amount_usd")
            ):
                grouped[group_key] = row
            continue
        direct.append(row)

    representatives = [*direct, *grouped.values()]
    representatives = _collapse_metric_representatives(
        representatives,
        key_fn=_source_hash_metric_dedupe_key,
    )
    representatives = _collapse_metric_representatives(
        representatives,
        key_fn=_economic_quote_metric_dedupe_key,
    )
    representatives = _collapse_metric_representatives(
        representatives,
        key_fn=_economic_obligation_metric_dedupe_key,
    )
    representatives = _collapse_metric_representatives(
        representatives,
        key_fn=_accession_amount_metric_dedupe_key,
    )
    representatives = _collapse_content_hash_quote_collision_representatives(representatives)
    representatives = _collapse_cross_filing_exact_quote_representatives(representatives)
    return _collapse_cross_filing_instrument_representatives(representatives)


def _collapse_metric_representatives(
    representatives: list[dict[str, str]],
    *,
    key_fn: Any,
) -> list[dict[str, str]]:
    collapsed: dict[tuple[str, tuple[str, ...], str], dict[str, str]] = {}
    unkeyed: list[dict[str, str]] = []
    for row in representatives:
        dedupe_key = key_fn(row)
        if not dedupe_key:
            unkeyed.append(row)
            continue
        current = collapsed.get(dedupe_key)
        if current is None or _metric_representative_sort_key(
            row
        ) > _metric_representative_sort_key(current):
            collapsed[dedupe_key] = row
    return [*unkeyed, *collapsed.values()]


def _source_hash_metric_dedupe_key(row: dict[str, str]) -> tuple[str, tuple[str, ...], str] | None:
    hashes = tuple(sorted(hash_value for hash_value in _json_list(row.get("content_hashes"))))
    if not hashes and row.get("content_hash"):
        hashes = (row["content_hash"],)
    if not hashes:
        return None
    amount_key = _metric_amount_key(_float(row.get("supported_amount_usd")))
    if not amount_key or amount_key == "0":
        return None
    return "source-hash", hashes, amount_key


def _economic_quote_metric_dedupe_key(
    row: dict[str, str],
) -> tuple[str, tuple[str, ...], str] | None:
    if row.get("metric_aggregation_policy") != "max_amount_per_source_instrument":
        return None
    entity_key = _slug(row.get("entity", ""))
    amount_key = _metric_amount_key(_float(row.get("supported_amount_usd")))
    stable_quote = row.get("metric_dedupe_quote") or row.get("evidence_quote", "")
    quote_key = _normalized_quote_fingerprint(stable_quote)
    if not entity_key or not amount_key or amount_key == "0" or not quote_key:
        return None
    return "economic-quote", (entity_key, amount_key), quote_key


def _economic_obligation_metric_dedupe_key(
    row: dict[str, str],
) -> tuple[str, tuple[str, ...], str] | None:
    if row.get("metric_aggregation_policy") != "max_amount_per_source_instrument":
        return None
    entity_key = _slug(row.get("entity", ""))
    amount_key = _metric_amount_key(_float(row.get("supported_amount_usd")))
    if not entity_key or not amount_key or amount_key == "0":
        return None
    subcategory_key = _slug(row.get("subcategory", ""))
    snapshot_key = (row.get("metric_snapshot_date") or "")[:7]
    counterparty_key = _slug(row.get("counterparty", ""))[:48]
    discriminators = tuple(
        value for value in (subcategory_key, snapshot_key, counterparty_key) if value
    )
    return "economic-obligation", (entity_key, amount_key, *discriminators), "v1"


_SEC_ACCESSION_RE = re.compile(r"/(\d{18})/")


def _sec_accession(source_uri: str) -> str:
    match = _SEC_ACCESSION_RE.search(source_uri or "")
    return match.group(1) if match else ""


def _accession_amount_metric_dedupe_key(
    row: dict[str, str],
) -> tuple[str, tuple[str, ...], str] | None:
    if row.get("metric_aggregation_policy") != "max_amount_per_source_instrument":
        return None
    entity_key = _slug(row.get("entity", ""))
    amount_key = _metric_amount_key(_float(row.get("supported_amount_usd")))
    accession = _sec_accession(row.get("source_uri", ""))
    if not entity_key or not amount_key or amount_key == "0" or not accession:
        return None
    return "accession-amount", (entity_key, accession), amount_key


def _collapse_content_hash_quote_collision_representatives(
    representatives: list[dict[str, str]],
) -> list[dict[str, str]]:
    grouped: dict[tuple[str, tuple[str, ...], str], list[dict[str, str]]] = {}
    unkeyed: list[dict[str, str]] = []
    for row in representatives:
        dedupe_key = _content_hash_metric_quote_collision_key(row)
        if not dedupe_key:
            unkeyed.append(row)
            continue
        grouped.setdefault(dedupe_key, []).append(row)

    collapsed: list[dict[str, str]] = []
    for rows in grouped.values():
        evidence_quote_keys = {
            _normalized_quote_fingerprint(row.get("evidence_quote", "")) for row in rows
        }
        if len(rows) > 1 and len(evidence_quote_keys) == 1 and "" not in evidence_quote_keys:
            collapsed.append(max(rows, key=_metric_representative_sort_key))
        else:
            collapsed.extend(rows)
    return [*unkeyed, *collapsed]


def _content_hash_metric_quote_collision_key(
    row: dict[str, str],
) -> tuple[str, tuple[str, ...], str] | None:
    if row.get("metric_aggregation_policy") != "max_amount_per_source_instrument":
        return None
    entity_key = _slug(row.get("entity", ""))
    hashes = tuple(sorted(hash_value for hash_value in _json_list(row.get("content_hashes"))))
    if not hashes and row.get("content_hash"):
        hashes = (row["content_hash"],)
    metric_quote_key = _normalized_quote_fingerprint(row.get("metric_dedupe_quote", ""))
    if not entity_key or not hashes or not metric_quote_key:
        return None
    return "content-hash-quote-collision", (entity_key, *hashes), metric_quote_key


def _collapse_cross_filing_exact_quote_representatives(
    representatives: list[dict[str, str]],
) -> list[dict[str, str]]:
    grouped: dict[tuple[str, tuple[str, ...], str], list[dict[str, str]]] = {}
    unkeyed: list[dict[str, str]] = []
    for row in representatives:
        dedupe_key = _cross_filing_exact_quote_metric_dedupe_key(row)
        if not dedupe_key:
            unkeyed.append(row)
            continue
        grouped.setdefault(dedupe_key, []).append(row)

    collapsed: list[dict[str, str]] = []
    for rows in grouped.values():
        accessions = {_sec_accession(row.get("source_uri", "")) for row in rows}
        if len(rows) > 1 and len(accessions) > 1:
            collapsed.append(max(rows, key=_metric_representative_sort_key))
        else:
            collapsed.extend(rows)
    return [*unkeyed, *collapsed]


def _cross_filing_exact_quote_metric_dedupe_key(
    row: dict[str, str],
) -> tuple[str, tuple[str, ...], str] | None:
    if row.get("metric_aggregation_policy") != "max_amount_per_source_instrument":
        return None
    entity_key = _slug(row.get("entity", ""))
    amount_key = _metric_amount_key(_float(row.get("supported_amount_usd")))
    quote_key = _normalized_quote_fingerprint(row.get("evidence_quote", ""))
    accession = _sec_accession(row.get("source_uri", ""))
    if not entity_key or not amount_key or amount_key == "0" or not quote_key or not accession:
        return None
    return "cross-filing-exact-quote", (entity_key, amount_key), quote_key


_INSTRUMENT_DESCRIPTOR_RE = re.compile(r"(\d{1,2}\.\d{2,3})\s?%|due (\d{4})", re.I)
_ENTITY_SUFFIX_RE = re.compile(
    r"\b(holdco|landco|opco|computeco|hpc holdings|eln-?\d+|far-?\d+|spv|borrower|holdings|llc"
    r"|inc|corp|co|l\.?p\.?|ltd|plc|finance|funding|trust|series \w+)\b",
    re.I,
)


def _entity_root_key(entity: str) -> str:
    stripped = _ENTITY_SUFFIX_RE.sub("", entity.lower())
    return re.sub(r"[^a-z0-9]", "", stripped)[:12]


def _instrument_descriptor_tokens(quote: str) -> frozenset[str]:
    tokens: set[str] = set()
    for coupon, year in _INSTRUMENT_DESCRIPTOR_RE.findall(quote or ""):
        if coupon:
            tokens.add(f"c{coupon}")
        if year:
            tokens.add(f"y{year}")
    return frozenset(tokens)


def _has_strict_common_instrument_fingerprint(
    descriptors: list[frozenset[str]],
) -> bool:
    if not descriptors or not all(descriptors):
        return False
    common = set.intersection(*(set(descriptor) for descriptor in descriptors))
    return any(token.startswith("c") for token in common) and any(
        token.startswith("y") for token in common
    )


def _collapse_cross_filing_instrument_representatives(
    representatives: list[dict[str, str]],
) -> list[dict[str, str]]:
    keyed: dict[tuple[str, str], list[dict[str, str]]] = {}
    unkeyed: list[dict[str, str]] = []
    for row in representatives:
        if row.get("metric_aggregation_policy") != "max_amount_per_source_instrument":
            unkeyed.append(row)
            continue
        entity_key = _entity_root_key(row.get("entity", ""))
        amount_key = _metric_amount_key(_float(row.get("supported_amount_usd")))
        accession = _sec_accession(row.get("source_uri", ""))
        if not entity_key or not amount_key or amount_key == "0" or not accession:
            unkeyed.append(row)
            continue
        keyed.setdefault((entity_key, amount_key), []).append(row)

    collapsed: list[dict[str, str]] = []
    for rows in keyed.values():
        accessions = {_sec_accession(row.get("source_uri", "")) for row in rows}
        descriptors = [
            _instrument_descriptor_tokens(
                row.get("metric_dedupe_quote") or row.get("evidence_quote", "")
            )
            for row in rows
        ]
        if len(accessions) > 1 and _has_strict_common_instrument_fingerprint(descriptors):
            collapsed.append(max(rows, key=_metric_representative_sort_key))
        else:
            collapsed.extend(rows)
    return [*unkeyed, *collapsed]


def _metric_representative_sort_key(row: dict[str, str]) -> tuple[int, tuple[str, int], float]:
    policy_rank = {
        "max_amount_per_source_instrument": 2,
        "latest_snapshot_per_metric_group": 1,
    }.get(row.get("metric_aggregation_policy") or "", 0)
    return (
        policy_rank,
        _snapshot_sort_key(row),
        _float(row.get("supported_amount_usd")),
    )


def _snapshot_sort_key(row: dict[str, str]) -> tuple[str, int]:
    return (row.get("metric_snapshot_date") or "", int(_float(row.get("rank"))) * -1)


def _json_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if not value:
        return []
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return [item.strip() for item in value.split("|") if item.strip()]
        if isinstance(loaded, list):
            return [str(item) for item in loaded if str(item)]
    return []


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(str(value).replace(",", "").replace("$", ""))
    except ValueError:
        return 0.0


def _metric_amount_key(amount: float) -> str:
    return str(round(amount))


def _normalized_quote_fingerprint(quote: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", quote.lower()).strip()
    if len(normalized) < 80:
        return ""
    return hashlib.sha1(normalized.encode()).hexdigest()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _pct(amount: float, total: float) -> float:
    return round(amount / total, 4) if total else 0.0
