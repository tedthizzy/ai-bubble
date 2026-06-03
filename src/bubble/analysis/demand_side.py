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
    mixed_players = funding_mix.get("mixed_cash_and_debt", 0)
    debt_funded = funding_mix.get("predominantly_debt_or_financing", 0)

    return {
        "status": "source_backed",
        "player_count": len(usable),
        "aggregate_ai_capex_usd": round(agg_capex, 2),
        "aggregate_operating_cash_flow_usd": round(agg_ocf, 2),
        "cash_coverage_of_capex": cash_coverage,
        "aggregate_ai_related_debt_or_finance_lease_usd": round(agg_ai_debt, 2),
        "aggregate_datacenter_purchase_commitments_usd": round(agg_commitments, 2),
        "funding_mix": funding_mix,
        "cash_funded_players": cash_funded,
        "mixed_funded_players": mixed_players,
        "debt_funded_players": debt_funded,
        "per_player": per_player,
        "bear_case_read": _bear_case_read(cash_coverage, cash_funded, debt_funded, len(usable)),
        "note": (
            "Demand-side (hyperscaler/offtaker) economics. cash_coverage_of_capex = aggregate "
            "operating cash flow / aggregate AI(-or-total) capex; >1 means the demand side self-funds "
            "its CASH capex. CAVEAT (key hidden leverage): this ratio is on the income/cash-flow "
            "statement only -- it excludes the large and fast-growing OFF-BALANCE-SHEET datacenter "
            "financing (finance leases + not-yet-commenced build-to-suit leases, e.g. Microsoft's "
            "~$196.6B of not-yet-commenced datacenter leases at Q3 FY26), the principal vector by "
            "which the buildout is actually financed. aggregate_datacenter_purchase_commitments_usd "
            "is total compute/datacenter commitments (an UPPER BOUND on what flows to the financed "
            "core; the filings rarely name the neocloud recipient). Capex mixes AI-specific and "
            "total where AI is not separately disclosed."
        ),
    }


def _bear_case_read(
    cash_coverage: float | None, cash_funded: int, debt_funded: int, total: int
) -> str:
    if cash_coverage is None:
        return "indeterminate_pending_capex_and_cashflow"
    if cash_coverage >= 1.0 and cash_funded >= total / 2 and debt_funded == 0:
        return (
            "demand_side_largely_self_funding: the hyperscalers cover AI capex from operating cash "
            "flow, so the leverage/bubble risk is concentrated in the FINANCED supply intermediaries "
            "(the neoclouds), not the cash-rich demand side. Supports the tiered verdict."
        )
    if cash_coverage < 1.0:
        return (
            "demand_side_capex_exceeds_cash_flow: in aggregate the demand side out-spends operating "
            "cash flow on AI capex (financing the gap) -- leverage spreading to the demand side, a "
            "broader bubble signal."
        )
    return (
        "mixed_and_weakening: aggregate operating cash flow still covers AI cash capex "
        f"({cash_coverage}x) and the largest players (Microsoft/Meta) self-fund, BUT the demand side "
        f"is NOT uniformly cash-funded -- {debt_funded} player(s) are predominantly debt-funded (e.g. "
        "Oracle, capex > OCF), others use mixed debt, and the mega-caps carry large OFF-BALANCE-SHEET "
        "datacenter lease pipelines NOT in this ratio. So the bear/rational-growth case holds for the "
        "cash-rich core of the demand side today, but leverage is rising at the margin and via "
        "off-BS leases -- the demand side is not an unconditional backstop for the financed core."
    )
