"""Forward refinancing-wall split (the "when_cracks" forward signal).

The ``capital_refinancing_usd_2024_2030`` / debt-service maturity walls span 2024-2030
and so bundle already-passed maturities into a number read as forward stress. This
splits a quarter→amount wall at an as-of quarter into historical vs forward, and
surfaces the forward concentration (peak quarter, near-term sum) — the genuine
"when do cracks appear" signal. Pure functions; the production windowing is Codex's.
"""

from __future__ import annotations

import re
from typing import Any

_QUARTER_RE = re.compile(r"^(\d{4})-?Q?([1-4])$", re.IGNORECASE)


def _quarter_tuple(quarter: str) -> tuple[int, int] | None:
    match = _QUARTER_RE.match((quarter or "").strip())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def split_maturity_wall(
    quarter_amounts: dict[str, float],
    *,
    as_of_quarter: str,
    near_term_quarters: int = 4,
) -> dict[str, Any]:
    """Split a quarter→USD wall at ``as_of_quarter`` into historical vs forward.

    ``forward`` = quarters >= as_of. ``near_term`` = the first ``near_term_quarters``
    forward quarters. Returns totals, the forward-by-quarter map, and the peak forward
    quarter. Unparseable quarter keys are ignored.
    """

    cutoff = _quarter_tuple(as_of_quarter)
    if cutoff is None:
        raise ValueError(f"invalid as_of_quarter: {as_of_quarter!r}")

    historical = 0.0
    forward: dict[str, float] = {}
    for quarter, amount in quarter_amounts.items():
        qt = _quarter_tuple(quarter)
        value = float(amount or 0.0)
        if qt is None:
            continue
        if qt < cutoff:
            historical += value
        else:
            forward[quarter] = forward.get(quarter, 0.0) + value

    total = historical + sum(forward.values())
    forward_total = sum(forward.values())
    ordered = sorted(forward.items(), key=lambda kv: _quarter_tuple(kv[0]) or (0, 0))
    near_term = sum(v for _, v in ordered[:near_term_quarters])
    peak_quarter, peak_amount = (max(forward.items(), key=lambda kv: kv[1]) if forward else ("", 0.0))
    return {
        "total_usd": round(total, 2),
        "historical_usd": round(historical, 2),
        "forward_usd": round(forward_total, 2),
        "historical_pct": round(historical / total * 100, 1) if total else 0.0,
        "near_term_usd": round(near_term, 2),
        "forward_peak_quarter": peak_quarter,
        "forward_peak_usd": round(peak_amount, 2),
        "forward_by_quarter": {q: round(v, 2) for q, v in ordered},
    }


def wall_from_signals(
    rows: list[dict[str, str]],
    *,
    category: str = "capital",
    amount_key: str = "amount_usd",
) -> dict[str, float]:
    """Build a quarter→amount wall from timing-signal rows of a category."""

    wall: dict[str, float] = {}
    for row in rows:
        if (row.get("category") or "").strip().lower() != category:
            continue
        quarter = (row.get("quarter") or row.get("signal_date") or "")[:7]
        try:
            amount = float(row.get(amount_key) or 0.0)
        except ValueError:
            amount = 0.0
        if quarter:
            wall[quarter] = wall.get(quarter, 0.0) + amount
    return wall
