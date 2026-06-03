"""Demand-side (hyperscaler/offtaker) AI funding aggregation.

The financed AI-direct core is a leveraged bet on hyperscaler demand. This
aggregates the demand side's own economics to test the bear case directly: are
the hyperscalers funding AI capex from OPERATING CASH FLOW (rational,
self-funding growth) or DEBT (leverage)? It also totals their compute
commitments to the core -- the take-or-pay backstop that IS the core's revenue.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_demand_side(path: str | Path) -> list[dict[str, Any]]:
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


def aggregate_demand_side(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate demand-side capex + funding to test self-funding vs leverage."""

    usable = [
        r
        for r in records
        if (r.get("verdict") or {}).get("overall") in ("source_backed", "partially_source_backed")
    ]
    if not usable:
        return {"status": "blocked_no_source_backed_demand_side", "player_count": 0}

    agg_capex = 0.0
    agg_ocf = 0.0
    agg_ai_debt = 0.0
    agg_commitments = 0.0
    funding_mix: dict[str, int] = {}
    cash_funded = 0
    per_player: list[dict[str, Any]] = []

    for row in usable:
        data = row.get("data") or {}
        capex = _num(data.get("ai_datacenter_capex_usd"))
        if capex is None:
            capex = _num(data.get("total_capex_usd"))
        ocf = _num(data.get("operating_cash_flow_usd"))
        ai_debt = _num(data.get("ai_related_debt_or_financing_usd")) or 0.0
        commitments = _num(data.get("compute_purchase_commitments_usd")) or 0.0
        funding = str(data.get("funding_source") or "unknown")

        agg_capex += capex or 0.0
        agg_ocf += ocf or 0.0
        agg_ai_debt += ai_debt
        agg_commitments += commitments
        funding_mix[funding] = funding_mix.get(funding, 0) + 1
        if funding == "predominantly_operating_cash_flow":
            cash_funded += 1
        per_player.append(
            {
                "entity": str(data.get("entity") or "").split("(")[0].split("/")[0].strip(),
                "ai_or_total_capex_usd": capex,
                "operating_cash_flow_usd": ocf,
                "ai_related_debt_usd": ai_debt or None,
                "compute_commitments_to_core_usd": commitments or None,
                "funding_source": funding,
            }
        )

    cash_coverage = round(agg_ocf / agg_capex, 2) if agg_capex > 0 else None
    debt_funded = len(usable) - cash_funded - funding_mix.get("unknown", 0)

    return {
        "status": "source_backed",
        "player_count": len(usable),
        "aggregate_ai_capex_usd": round(agg_capex, 2),
        "aggregate_operating_cash_flow_usd": round(agg_ocf, 2),
        "cash_coverage_of_capex": cash_coverage,
        "aggregate_ai_related_debt_usd": round(agg_ai_debt, 2),
        "aggregate_compute_commitments_to_core_usd": round(agg_commitments, 2),
        "funding_mix": funding_mix,
        "cash_funded_players": cash_funded,
        "debt_funded_players": debt_funded,
        "per_player": per_player,
        "bear_case_read": _bear_case_read(cash_coverage, cash_funded, len(usable), agg_ai_debt),
        "note": (
            "Demand-side (hyperscaler/offtaker) economics. cash_coverage_of_capex = aggregate "
            "operating cash flow / aggregate AI(-or-total) capex; >1 means the demand side can "
            "self-fund its buildout. aggregate_compute_commitments_to_core_usd is the take-or-pay "
            "backstop these players owe the financed core (the core's contracted revenue). "
            "Capex figures mix AI-specific and total where AI is not separately disclosed."
        ),
    }


def _bear_case_read(
    cash_coverage: float | None, cash_funded: int, total: int, ai_debt: float
) -> str:
    if cash_coverage is None:
        return "indeterminate_pending_capex_and_cashflow"
    if cash_coverage >= 1.0 and cash_funded >= total / 2:
        return (
            "demand_side_largely_self_funding: the hyperscalers cover AI capex from operating cash "
            "flow, so the bubble/leverage risk is NOT on the cash-rich demand side -- it is "
            "concentrated in the FINANCED supply intermediaries (the neoclouds) that borrowed to "
            "build capacity for this demand and bear the loss if it softens. Supports the tiered "
            "verdict (core fragile; ecosystem not a uniform bubble)."
        )
    if cash_coverage < 1.0:
        return (
            "demand_side_capex_exceeds_cash_flow: even the hyperscalers are out-spending operating "
            "cash flow on AI capex (financing the gap), so leverage is spreading from the financed "
            "core toward the demand side -- a stronger, broader bubble signal."
        )
    return "mixed: demand side partially debt-funded; monitor the cash-coverage trend."
