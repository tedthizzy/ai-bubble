"""AI-datacenter power exposure + ratepayer cost-allocation.

Completes the supply->demand->POWER triangle and quantifies the ratepayer leg of
"who bears the downside": how much of the new generation/grid built for AI
data-center load is socialized to RATEPAYERS (general rate base) vs borne by the
AI customer (special tariff / minimum-take), and whether ratepayers are
protected against a stranded asset if the data-center cancels. Utilities can
claim "customer pays" while the tariff actually socializes cost, so the
adversarially-verified cost_allocation is the load-bearing field.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_RATEPAYER = "ratepayers_bear_via_rate_base"
_CUSTOMER = "ai_customer_bears_via_special_tariff_or_min_take"
_MIXED = "mixed"


def load_power_exposure(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        loaded = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    return [r for r in loaded if isinstance(r, dict)] if isinstance(loaded, list) else []


def _num(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def aggregate_power_exposure(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate utility AI-load + generation build by who bears the cost."""

    usable = [
        r
        for r in records
        if (r.get("verdict") or {}).get("overall") in ("source_backed", "partially_source_backed")
    ]
    if not usable:
        return {"status": "blocked_no_source_backed_power_exposure", "utility_count": 0}

    total_load_mw = 0.0
    build_by_allocation: dict[str, float] = {}
    count_by_allocation: dict[str, int] = {}
    customers: set[str] = set()
    per_utility: list[dict[str, Any]] = []

    for row in usable:
        data = row.get("data") or {}
        load = _num(data.get("ai_datacenter_load_mw")) or 0.0
        build = _num(data.get("generation_build_for_ai_usd")) or 0.0
        alloc = str(data.get("cost_allocation") or "unknown")
        total_load_mw += load
        build_by_allocation[alloc] = build_by_allocation.get(alloc, 0.0) + build
        count_by_allocation[alloc] = count_by_allocation.get(alloc, 0) + 1
        for c in data.get("named_ai_customers") or []:
            if c:
                customers.add(str(c))
        per_utility.append(
            {
                "entity": str(data.get("entity") or "").split("(")[0].split("/")[0].strip(),
                "ai_datacenter_load_mw": load or None,
                "generation_build_for_ai_usd": build or None,
                "cost_allocation": alloc,
                "min_take_protection": str(data.get("min_take_or_collateral_protection") or "")[
                    :160
                ],
            }
        )

    # Ratepayer-socialized cost = full rate-base + half of mixed (conservative).
    ratepayer_socialized = build_by_allocation.get(_RATEPAYER, 0.0) + 0.5 * build_by_allocation.get(
        _MIXED, 0.0
    )
    customer_borne = build_by_allocation.get(_CUSTOMER, 0.0) + 0.5 * build_by_allocation.get(
        _MIXED, 0.0
    )
    total_build = sum(build_by_allocation.values())
    ratepayer_pct = round(100 * ratepayer_socialized / total_build, 1) if total_build > 0 else None
    ratepayer_utilities = count_by_allocation.get(_RATEPAYER, 0) + count_by_allocation.get(
        _MIXED, 0
    )

    return {
        "status": "source_backed",
        "utility_count": len(usable),
        "total_ai_datacenter_load_mw": round(total_load_mw, 1),
        "total_generation_build_for_ai_usd": round(total_build, 2),
        "ratepayer_socialized_usd": round(ratepayer_socialized, 2),
        "ai_customer_borne_usd": round(customer_borne, 2),
        "ratepayer_socialized_pct": ratepayer_pct,
        "utilities_socializing_to_ratepayers": ratepayer_utilities,
        "named_ai_customers": sorted(customers),
        "cost_allocation_counts": count_by_allocation,
        "per_utility": per_utility,
        "ratepayer_downside_read": _ratepayer_read(ratepayer_pct, ratepayer_utilities, len(usable)),
        "note": (
            "Ratepayer leg of who-bears-downside. cost_allocation = whether the AI-datacenter "
            "generation/grid cost is borne by the AI customer (special tariff / minimum-take) or "
            "SOCIALIZED to ratepayers (general rate base). ratepayer_socialized counts full rate-base "
            "plus half of 'mixed'. A high ratepayer share + weak min-take protection means ordinary "
            "utility customers, not the AI buildout, bear the stranded-asset risk if AI demand softens."
        ),
    }


def _ratepayer_read(pct: float | None, ratepayer_utilities: int, total: int) -> str:
    if pct is None:
        return "indeterminate_pending_generation_build_figures"
    if pct >= 50 or ratepayer_utilities >= total / 2:
        return (
            "material_ratepayer_socialization: a substantial share of AI-datacenter generation/grid "
            "cost is in the general rate base, so ORDINARY RATEPAYERS -- not the AI buildout -- bear "
            "the stranded-asset risk if demand softens. This is a hidden, politically charged "
            "downside leg distinct from the issuer-creditor and parent-equity legs, and a leading "
            "indicator (rate cases, docket fights) of where the unwind hits first outside the cluster."
        )
    return (
        "ratepayers_largely_protected: AI-datacenter power cost is mostly borne by the customer via "
        "special tariffs / minimum-take with collateral, limiting ratepayer stranded-asset exposure. "
        "Verify the min-take actually survives a customer pullback (carve-outs)."
    )
