"""Sub-threshold asset/capacity leakage sweep (root cause 1, below the mega guard).

Codex's mega-amount guard blocks asset/capacity figures > $50B, but smaller
financial-sector asset figures still leak into the metric. This sweep flags approved
``source-instrument`` groups whose ``evidence_quote`` contains a **high-confidence**
asset-side marker — unambiguous balance-sheet terms only (UPB, total loans/assets,
servicing portfolio, AUM, MSR), NOT boilerplate like "forward-looking" that co-occurs
with legitimate debt prospectuses (verified: that over-flags Honeywell debt and real
first-mortgage bonds). Pure functions; the production extraction guard is Codex's.
"""

from __future__ import annotations

from typing import Any

# Unambiguous asset-side / capacity markers. Deliberately excludes boilerplate
# ("forward-looking", "webcast", "earnings report") that appears in real debt filings.
HIGH_CONFIDENCE_ASSET_MARKERS = (
    "held for investment",
    "servicing portfolio",
    "unpaid principal balance",
    " upb",
    "financing capacity",
    "loans eligible for repurchase",
    "assets under management",
    "total assets of",
    "total loans of",
    "loans and leases held",
    "net asset value",
    "mortgage servicing rights",
)


def quote_is_asset_side(text: str) -> bool:
    """True when the quote unambiguously describes an asset/capacity figure."""

    lowered = (text or "").lower()
    return any(marker in lowered for marker in HIGH_CONFIDENCE_ASSET_MARKERS)


def _amount(row: dict[str, str]) -> float:
    try:
        return float(row.get("supported_amount_usd") or 0.0)
    except ValueError:
        return 0.0


def summarize_asset_leakage(
    rows: list[dict[str, str]],
    *,
    mega_threshold: float = 50e9,
) -> dict[str, Any]:
    """Flag approved source-instrument groups <= mega_threshold whose quote is asset-side."""

    groups: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("metric_use_status") != "approved_for_metric_use":
            continue
        gid = row.get("metric_group_id") or ""
        if not gid.startswith("source-instrument:"):
            continue
        if gid not in groups or _amount(row) > _amount(groups[gid]):
            groups[gid] = row

    leaked = [
        r
        for r in groups.values()
        if _amount(r) <= mega_threshold and quote_is_asset_side(r.get("evidence_quote") or "")
    ]
    leaked.sort(key=_amount, reverse=True)
    return {
        "leaked_count": len(leaked),
        "leaked_gross_usd": round(sum(_amount(r) for r in leaked), 2),
        "leaked_packets": [
            {
                "packet_id": r.get("packet_id", ""),
                "entity": r.get("entity", ""),
                "supported_amount_usd": _amount(r),
            }
            for r in leaked
        ],
    }
