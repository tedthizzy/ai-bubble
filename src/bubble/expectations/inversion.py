"""Consensus-inference: per-name expectations inversion (WS1.1).

The forensic engine measures reality (coverage, collateral life, maturity walls). A truth
claim is not a thesis; the thesis is the GAP between what the engine measured and what the
market's price implies it believes. This module recovers the second half: given each name's
enterprise value, it solves for the economics the price is paying for, then contrasts them
with the contracted/disclosed fundamentals.

Two inversions, both stylized on purpose (transparent assumptions beat false precision) and
both reported as SENSITIVITY BANDS across a scenario grid, never as point estimates:

1. **Implied revenue multiple** -- via a Gordon-growth perpetuity, the perpetual revenue the
   EV requires at a steady-state FCF margin, expressed as a multiple of current revenue.
   "The price implies revenue must reach ~Nx today's and hold there forever."

2. **Renewal-dependent share of EV** -- the share of EV that the *contracted* backlog cannot
   justify on its own (PV of backlog-derived FCF over its tenor), and which therefore depends
   on RE-CONTRACTING the assets after the first contract expires. This is the inversion that
   bites: a high renewal-dependent share is the market betting that GPUs get re-leased at
   healthy rates after their first term -- directly against the engine's ~2-3yr GPU economic
   life vs 5-7yr debt finding.

What the inversions deliberately DO NOT capture (carded, not hidden): uneven revenue
recognition (backlog is spread evenly over tenor), capex already sunk into EV via debt,
double-counting between current revenue and near-term backlog, and option-value of capacity.
They are comparative instruments across names and against the engine's measurements -- not
valuations. Pure functions; the script renders analysis/expectations_inversion.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import median
from typing import Any

# --- Scenario grid (the sensitivity axes; wide on purpose for high-beta levered names) ---
DISCOUNT_RATES = (0.10, 0.12, 0.15)
FCF_MARGINS = (0.15, 0.25, 0.35)  # steady-state; generous given most are FCF-negative today
TERMINAL_GROWTH = 0.04  # perpetual; the revenue-multiple frame's g in EV = FCF / (r - g)


@dataclass(frozen=True)
class NameInputs:
    """Carded inputs for one name. EV/financials are financial_press (aggregator, 2026-06-12);
    revenue/backlog/tenor are company_filing_or_release. See sources[] for per-field cites."""

    ticker: str
    name: str
    ev_usd_b: float
    current_annualized_revenue_usd_b: float
    revenue_basis: str  # what current_annualized_revenue represents
    backlog_usd_b: float
    backlog_tenor_years: float
    backlog_basis: str
    net_debt_usd_b: float
    is_landlord: bool  # leases (long-dated take-or-pay) vs GPU-cloud (short re-lease cycle)
    notes: str
    sources: dict[str, str] = field(default_factory=dict)


def annuity_factor(rate: float, years: float) -> float:
    """PV of $1/yr for `years` at `rate` (ordinary annuity)."""
    if rate <= 0:
        return years
    return float((1.0 - (1.0 + rate) ** -years) / rate)


def implied_perpetual_revenue(ev_usd_b: float, rate: float, growth: float, margin: float) -> float:
    """Gordon: EV = FCF/(r-g), FCF = margin x revenue  =>  revenue = EV(r-g)/margin."""
    if rate <= growth or margin <= 0:
        return float("inf")
    return ev_usd_b * (rate - growth) / margin


def implied_revenue_multiple(inp: NameInputs, rate: float, growth: float, margin: float) -> float:
    """How many times current revenue the price implies must be reached and held in perpetuity."""
    if inp.current_annualized_revenue_usd_b <= 0:
        return float("inf")
    req = implied_perpetual_revenue(inp.ev_usd_b, rate, growth, margin)
    return req / inp.current_annualized_revenue_usd_b


def contracted_pv(inp: NameInputs, rate: float, margin: float) -> float:
    """PV of FCF derivable from the contracted backlog alone, spread evenly over its tenor."""
    annual_backlog_revenue = inp.backlog_usd_b / inp.backlog_tenor_years
    annual_fcf = annual_backlog_revenue * margin
    return annual_fcf * annuity_factor(rate, inp.backlog_tenor_years)


def renewal_dependent_share(inp: NameInputs, rate: float, margin: float) -> float:
    """Share of EV NOT justified by the contracted backlog -> depends on re-contracting.

    Clamped to [0, 1]: a value near 1 means almost all of the price rests on cash flows that
    require re-leasing the assets after the first contract; near 0 means the signed backlog
    already covers the EV.
    """
    if inp.ev_usd_b <= 0:
        return float("nan")
    covered = contracted_pv(inp, rate, margin)
    share = 1.0 - covered / inp.ev_usd_b
    return max(0.0, min(1.0, share))


def _band(values: list[float]) -> dict[str, float]:
    finite = [v for v in values if not math.isinf(v) and not math.isnan(v)]
    if not finite:
        return {"low": float("inf"), "median": float("inf"), "high": float("inf")}
    return {"low": min(finite), "median": round(median(finite), 3), "high": max(finite)}


def invert_name(inp: NameInputs) -> dict[str, Any]:
    """Run both inversions across the full scenario grid; return banded results."""
    rev_multiples = [
        implied_revenue_multiple(inp, r, TERMINAL_GROWTH, m)
        for r in DISCOUNT_RATES
        for m in FCF_MARGINS
    ]
    renewal_shares = [
        renewal_dependent_share(inp, r, m) for r in DISCOUNT_RATES for m in FCF_MARGINS
    ]
    backlog_cover = (
        (inp.backlog_usd_b / inp.backlog_tenor_years) / inp.current_annualized_revenue_usd_b
        if inp.current_annualized_revenue_usd_b > 0
        else float("inf")
    )
    return {
        "ticker": inp.ticker,
        "name": inp.name,
        "ev_usd_b": inp.ev_usd_b,
        "current_annualized_revenue_usd_b": inp.current_annualized_revenue_usd_b,
        "revenue_basis": inp.revenue_basis,
        "backlog_usd_b": inp.backlog_usd_b,
        "backlog_tenor_years": inp.backlog_tenor_years,
        "is_landlord": inp.is_landlord,
        "implied_revenue_multiple": _band([round(v, 2) for v in rev_multiples]),
        "renewal_dependent_share": _band([round(v, 3) for v in renewal_shares]),
        "annual_backlog_vs_current_revenue_x": round(backlog_cover, 2)
        if backlog_cover != float("inf")
        else None,
        "notes": inp.notes,
        "sources": inp.sources,
    }


def invert_all(names: list[NameInputs]) -> list[dict[str, Any]]:
    return [invert_name(n) for n in names]
