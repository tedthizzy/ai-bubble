"""Timing-wall integrity checker (root cause 1 + 2 in the timing dimension).

The whole-corpus ``capital_refinancing_usd_2024_2030`` wall inherits the same
asset/capacity mis-extraction (root cause 1) and cross-filing duplication (root
cause 2) as the materiality metric — but `build_timing_signals.py` is a separate
builder that did not receive the mega-amount guard, so the contamination persists
there. The **AI-infra-relevant subset** is verified clean.

``summarize_timing_wall_integrity`` quantifies, over the capital timing signals:
mega asset/capacity signals (>``mega_threshold``), strong asset-marker signals,
cross-filing duplication excess, and the clean AI-infra subset total — so the
contaminated whole-corpus wall can be separated from the trustworthy AI figure.
Pure function; the production builder is Codex's.
"""

from __future__ import annotations

import re
from typing import Any

# Strong markers that the signal's figure is an asset / capacity / boilerplate
# number, not the issuer's committed debt coming due.
ASSET_CAPACITY_MARKERS = (
    "held for investment",
    "servicing portfolio",
    "unpaid principal balance",
    " upb",
    "financing capacity",
    "loans eligible",
    "assets under management",
    "total assets of",
    "consolidated loans",
    "loans and leases",
    "net asset value",
    "investment portfolio",
    "webcast",
    "forward-looking",
    "earnings report",
    "msr ",
)

_AI_RELEVANCE = ("ai", "compute", "data_center", "datacenter", "hyperscal", "gpu", "chip")
_NON_AI = ("", "not_tagged", "not_established", "none")


def _amount(row: dict[str, str], key: str = "amount_usd") -> float:
    try:
        return float(row.get(key) or 0.0)
    except ValueError:
        return 0.0


def _is_ai_infra(row: dict[str, str]) -> bool:
    relevance = (row.get("ecosystem_relevance") or "").strip().lower()
    if relevance and relevance not in _NON_AI:
        return True
    tags = (row.get("relevance_tags") or "").lower()
    return any(tag in tags for tag in _AI_RELEVANCE)


def _has_asset_marker(row: dict[str, str]) -> bool:
    text = " ".join(
        [row.get("description", ""), row.get("evidence_quote", ""), row.get("signal_type", "")]
    ).lower()
    return any(marker in text for marker in ASSET_CAPACITY_MARKERS)


def summarize_timing_wall_integrity(
    rows: list[dict[str, str]],
    *,
    mega_threshold: float = 50e9,
) -> dict[str, Any]:
    """Quantify contamination of the capital timing wall and the clean AI subset."""

    capital = [r for r in rows if (r.get("category") or "").strip().lower() == "capital"]
    capital_wall = sum(_amount(r) for r in capital)

    mega = [r for r in capital if _amount(r) > mega_threshold]
    asset_marked = [r for r in capital if _has_asset_marker(r)]

    ai_rows = [r for r in capital if _is_ai_infra(r)]
    ai_wall = sum(_amount(r) for r in ai_rows)
    ai_mega = [r for r in ai_rows if _amount(r) > mega_threshold]

    # Cross-filing duplication excess among capital signals (same entity + amount).
    clusters: dict[tuple[str, int], int] = {}
    for row in capital:
        key = (row.get("entity", "").strip().lower(), round(_amount(row)))
        clusters[key] = clusters.get(key, 0) + 1
    crossfiling_excess = sum(amt * (n - 1) for (_, amt), n in clusters.items() if n > 1 and amt > 0)

    return {
        "capital_signals": len(capital),
        "capital_wall_usd": round(capital_wall, 2),
        "mega_count": len(mega),
        "mega_gross_usd": round(sum(_amount(r) for r in mega), 2),
        "asset_marker_count": len(asset_marked),
        "asset_marker_gross_usd": round(sum(_amount(r) for r in asset_marked), 2),
        "crossfiling_excess_usd": round(crossfiling_excess, 2),
        "ai_infra_wall_usd": round(ai_wall, 2),
        "ai_infra_mega_count": len(ai_mega),
    }


def _timing_obligation_key(row: dict[str, str]) -> str:
    entity = re.sub(r"[^a-z0-9]+", " ", (row.get("entity") or "").lower()).strip()
    amount = round(_amount(row))
    period = (row.get("quarter") or row.get("signal_date") or "").strip()[:7]
    return f"{entity}|{amount}|{period}"


def simulate_timing_wall_fix(
    rows: list[dict[str, str]],
    *,
    mega_threshold: float = 50e9,
) -> dict[str, Any]:
    """Simulate fixing the timing wall: apply the mega guard, then economic dedup.

    Mirrors the materiality fixes for `build_timing_signals.py`. Returns the raw wall,
    the wall after dropping mega (>``mega_threshold``) capital signals, and the wall
    after also collapsing same-obligation cross-filing/period redisclosures — plus the
    AI-infra subset (which is already clean).
    """

    capital = [r for r in rows if (r.get("category") or "").strip().lower() == "capital"]
    raw = sum(_amount(r) for r in capital)

    non_mega = [r for r in capital if _amount(r) <= mega_threshold]
    after_mega = sum(_amount(r) for r in non_mega)

    deduped: dict[str, float] = {}
    sizes: dict[str, int] = {}
    label: dict[str, str] = {}
    for row in non_mega:
        key = _timing_obligation_key(row)
        deduped[key] = max(deduped.get(key, 0.0), _amount(row))
        sizes[key] = sizes.get(key, 0) + 1
        label.setdefault(key, (row.get("entity") or "").strip())
    after_dedup = sum(deduped.values())
    multi = [(k, sizes[k], deduped[k]) for k in sizes if sizes[k] > 1]
    multi.sort(key=lambda t: t[2] * (t[1] - 1), reverse=True)
    collapsed: list[dict[str, Any]] = [
        {"entity": label[k], "period": k.split("|")[-1], "signals": n, "amount_usd": amt}
        for k, n, amt in multi
    ]

    ai_wall = sum(_amount(r) for r in capital if _is_ai_infra(r))
    return {
        "raw_capital_wall_usd": round(raw, 2),
        "after_mega_guard_usd": round(after_mega, 2),
        "mega_removed_usd": round(raw - after_mega, 2),
        "after_economic_dedup_usd": round(after_dedup, 2),
        "dedup_removed_usd": round(after_mega - after_dedup, 2),
        "corrected_capital_wall_usd": round(after_dedup, 2),
        "ai_infra_wall_usd": round(ai_wall, 2),
        "top_collapsed": collapsed[:10],
    }
