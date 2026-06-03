"""Ultimate end-holders of the AI-direct cluster's securities (who really eats it).

The final leg of "who bears the downside when it unwinds." The earlier legs trace
loss to parent equity (recourse), secured creditors (GPU collateral), and
ratepayers (socialized grid build). This layer goes one step further: WHO HOLDS
THE PAPER -- the equity, convertibles, and private-credit debt of the financed
cluster -- classified by holder type, from SEC ownership filings (13F-HR, SC
13G/13D, S-1/10-K beneficial-ownership) and the funding source of the
private-credit lenders.

The Burry read: loss routed to INSURERS, PENSIONS, and PASSIVE INDEX FUNDS lands
on policyholders, retirees, and ordinary index investors (households) -- a quiet,
broad, socialized downside -- versus loss held by HEDGE FUNDS / PE / VC, which is
risk-seeking capital that underwrote the bet knowingly. Most DDTL/SPV debt is a
private placement with NO 13-F, so disclosure is partial by construction; the
aggregate is explicit about that coverage gap rather than overclaiming.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Holder types whose losses route to households (policyholders / retirees / retail).
_HOUSEHOLD_ROUTED = {"insurer", "pension", "index_fund_passive"}
# Risk-seeking capital that underwrote the bet knowingly.
_RISK_CAPITAL = {"hedge_fund", "private_equity", "venture_capital"}
# Intermediaries / concentrated holders (active managers, banks, sovereigns, insiders).
_INTERMEDIARY = {
    "asset_manager_or_mutual_fund",
    "bank",
    "sovereign_wealth",
    "insider_or_founder",
    "unknown",
}
_KEPT_VERDICTS = {"filing_verified", "press_only_kept_flagged"}


def load_end_holders(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        loaded = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    return [r for r in loaded if isinstance(r, dict)] if isinstance(loaded, list) else []


def _bucket(holder_type: str) -> str:
    if holder_type in _HOUSEHOLD_ROUTED:
        return "household_routed"
    if holder_type in _RISK_CAPITAL:
        return "risk_capital"
    return "intermediary_or_concentrated"


def _num(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def aggregate_end_holders(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate disclosed end-holders by type / routing across the cluster."""

    usable = [
        r
        for r in records
        if str(r.get("overall") or "") in ("source_backed", "partially_source_backed")
    ]
    if not usable:
        return {"status": "blocked_no_source_backed_end_holders", "entity_count": 0}

    count_by_type: dict[str, int] = {}
    value_by_type: dict[str, float] = {}
    count_by_bucket: dict[str, int] = {}
    value_by_bucket: dict[str, float] = {}
    filing_verified = 0
    press_flagged = 0
    total_holders = 0
    holders_with_value = 0
    household_names: set[str] = set()
    entities_covered: list[str] = []

    for rec in usable:
        entities_covered.append(str(rec.get("entity") or "").split("(")[0].strip())
        for h in rec.get("verified_holders") or []:
            verdict = str(h.get("verdict") or "")
            if verdict not in _KEPT_VERDICTS:
                continue
            total_holders += 1
            if verdict == "filing_verified":
                filing_verified += 1
            else:
                press_flagged += 1
            htype = str(h.get("holder_type") or "unknown")
            bucket = _bucket(htype)
            count_by_type[htype] = count_by_type.get(htype, 0) + 1
            count_by_bucket[bucket] = count_by_bucket.get(bucket, 0) + 1
            val = _num(h.get("approx_value_usd"))
            if val is not None and val > 0:
                holders_with_value += 1
                value_by_type[htype] = value_by_type.get(htype, 0.0) + val
                value_by_bucket[bucket] = value_by_bucket.get(bucket, 0.0) + val
            if bucket == "household_routed" and h.get("holder_name"):
                household_names.add(str(h.get("holder_name")))

    if total_holders == 0:
        return {"status": "blocked_no_kept_holders", "entity_count": len(usable)}

    household_count_pct = round(100 * count_by_bucket.get("household_routed", 0) / total_holders, 1)
    total_value = sum(value_by_bucket.values())
    household_value_pct = (
        round(100 * value_by_bucket.get("household_routed", 0.0) / total_value, 1)
        if total_value > 0
        else None
    )

    return {
        "status": "source_backed",
        "entity_count": len(usable),
        "entities_covered": sorted({e for e in entities_covered if e}),
        "total_kept_holders": total_holders,
        "filing_verified_holders": filing_verified,
        "press_flagged_holders": press_flagged,
        "holders_with_disclosed_value": holders_with_value,
        "count_by_holder_type": dict(sorted(count_by_type.items(), key=lambda kv: -kv[1])),
        "count_by_routing_bucket": count_by_bucket,
        "value_by_routing_bucket_usd": {k: round(v, 2) for k, v in value_by_bucket.items()},
        "household_routed_count_pct": household_count_pct,
        "household_routed_value_pct": household_value_pct,
        "example_household_routed_holders": sorted(household_names)[:12],
        "ultimate_downside_read": _downside_read(
            household_count_pct, count_by_bucket, total_holders
        ),
        "note": (
            "Ultimate end-holder leg of who-bears-downside, from SEC ownership filings (13F-HR, "
            "SC 13G/13D, S-1/10-K beneficial ownership) + private-credit lender funding source. "
            "'household_routed' = insurers + pensions + passive index funds, whose loss lands on "
            "policyholders / retirees / ordinary index investors. 'risk_capital' = hedge funds / PE / "
            "VC that underwrote the bet knowingly. COVERAGE IS PARTIAL BY CONSTRUCTION: most DDTL/SPV "
            "debt is a private placement with no 13-F, so undisclosed holders are not counted -- this "
            "is the disclosed-holder distribution, not the full cap table. Value-weighting is shown "
            "only where 13-F dollar values are disclosed; otherwise the count distribution governs."
        ),
    }


def _downside_read(pct: float, by_bucket: dict[str, int], total: int) -> str:
    risk = by_bucket.get("risk_capital", 0)
    if pct >= 50:
        return (
            "household_socialized: a majority of DISCLOSED holders are insurers / pensions / passive "
            "index funds, so the equity/credit loss routes to policyholders, retirees, and ordinary "
            "index investors -- a quiet, broad downside few of those bearers actively chose. This is "
            "the 2008 parallel (risk sitting in 'safe' insurance/pension/retail wrappers), and the "
            "private-placement DDTL debt (undisclosed here) likely sits with insurance/annuity-funded "
            "private credit, deepening the same routing."
        )
    if risk >= total / 2:
        return (
            "risk_capital_held: most disclosed holders are hedge funds / PE / VC that underwrote the "
            "bet knowingly, so the first-loss is largely with risk-seeking capital -- a more contained "
            "downside than a household-socialized one, though the private-placement debt holders are "
            "undisclosed and may shift this."
        )
    return (
        "mixed_holding: disclosed holders span household-routed (insurance/pension/index) and "
        "risk-capital, with no majority either way; the undisclosed private-placement debt is the "
        "swing factor for where the ultimate loss concentrates."
    )
