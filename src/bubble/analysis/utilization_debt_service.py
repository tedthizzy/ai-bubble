"""Entity-level utilization vs debt-service mismatch (the third source-backed leg).

The Burry question at the deal/entity level: does CONTRACTED revenue actually
cover debt service, and how far would utilization have to fall before coverage
breaks? The realistic-utilization DSCR leg has been blocked/illustrative because
per-issuer utilization and full debt service (principal + interest) are rarely
cleanly disclosed. This module computes, from whatever IS filing-verified per
issuer:

- contracted-coverage ratio = contracted revenue (or RPO run-rate) / debt service,
- a revenue/interest coverage where debt service is undisclosed,
- the implied utilization break-even (how far contracted/used capacity could fall
  before coverage < 1x), where capacity utilization is disclosed.

It never invents a utilization or debt-service figure: an issuer contributes a
ratio only where its inputs are filing-verified, and the aggregate is explicit
about how many issuers had usable disclosure. This is the deal/entity-level
mismatch the engine's separation test was missing a source-backed leg for.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_utilization_debt_service(path: str | Path) -> list[dict[str, Any]]:
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


def _short(name: str) -> str:
    return str(name or "").split("(")[0].split(",")[0].strip()


def aggregate_utilization_debt_service(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute per-issuer contracted-coverage / utilization break-even and aggregate."""

    usable = [
        r
        for r in records
        if str(r.get("overall") or "") in ("source_backed", "partially_source_backed")
    ]
    if not usable:
        return {"status": "blocked_no_source_backed_utilization", "issuer_count": 0}

    per_issuer: list[dict[str, Any]] = []
    contracted_coverage_ratios: list[float] = []
    issuers_contracted_below_1 = 0
    issuers_with_debt_service = 0
    issuers_with_utilization = 0

    for rec in usable:
        issuer = _short(rec.get("issuer", ""))
        mt = rec.get("verified_metrics") or {}
        rpo = _num(mt.get("remaining_performance_obligations_usd"))
        contracted_rev = _num(mt.get("contracted_revenue_run_rate_usd"))
        revenue = _num(mt.get("annual_revenue_usd"))
        debt_service = _num(mt.get("annual_debt_service_usd"))
        interest = _num(mt.get("annual_interest_expense_usd"))
        util = _num(mt.get("contracted_or_committed_capacity_pct")) or _num(
            mt.get("disclosed_utilization_pct")
        )

        denom = debt_service if debt_service and debt_service > 0 else interest
        denom_kind = "debt_service" if (debt_service and debt_service > 0) else "interest_only"
        # Numerator: prefer contracted revenue run-rate, else total revenue.
        numer = contracted_rev if contracted_rev and contracted_rev > 0 else revenue
        numer_kind = (
            "contracted_revenue" if (contracted_rev and contracted_rev > 0) else "total_revenue"
        )

        coverage = None
        if denom and denom > 0 and numer is not None:
            coverage = round(numer / denom, 2)
            if debt_service and debt_service > 0:
                issuers_with_debt_service += 1
            # Only count contracted-revenue coverage in the break-stat (not total-rev proxy).
            if numer_kind == "contracted_revenue":
                contracted_coverage_ratios.append(coverage)
                if coverage < 1.0:
                    issuers_contracted_below_1 += 1
        if util is not None:
            issuers_with_utilization += 1

        # Utilization break-even: if coverage uses contracted revenue that scales with
        # utilization, the break-even utilization = current_util / coverage (coverage>1
        # => room to fall). Only meaningful when both util and a contracted coverage exist.
        breakeven_util = None
        if util is not None and coverage and coverage > 0 and numer_kind == "contracted_revenue":
            breakeven_util = round(util / coverage, 1)

        per_issuer.append(
            {
                "issuer": issuer,
                "coverage_ratio": coverage,
                "coverage_numerator": numer_kind,
                "coverage_denominator": denom_kind,
                "contracted_or_used_capacity_pct": util,
                "breakeven_utilization_pct": breakeven_util,
                "rpo_usd": rpo,
                "rpo_concentration_note": str(mt.get("rpo_concentration_note") or "")[:160] or None,
            }
        )

    per_issuer.sort(key=lambda r: (r["coverage_ratio"] is not None, -(r["coverage_ratio"] or 1e9)))
    median_contracted = _median(contracted_coverage_ratios)

    return {
        "status": "source_backed",
        "issuer_count": len(usable),
        "issuers_with_filing_debt_service": issuers_with_debt_service,
        "issuers_with_disclosed_utilization": issuers_with_utilization,
        "issuers_with_contracted_coverage": len(contracted_coverage_ratios),
        "issuers_contracted_coverage_below_1": issuers_contracted_below_1,
        "median_contracted_coverage_ratio": median_contracted,
        "per_issuer": per_issuer,
        "mismatch_read": _read(
            len(contracted_coverage_ratios), issuers_contracted_below_1, median_contracted
        ),
        "note": (
            "Entity-level utilization vs debt-service mismatch from filings. coverage_ratio = "
            "contracted revenue run-rate (or, where contracted is undisclosed, total revenue -- "
            "labeled) over annual debt service (or, where undisclosed, interest only -- labeled). "
            "breakeven_utilization_pct = how far contracted/used capacity could fall before coverage "
            "< 1x. Per-issuer DISCLOSURE IS THIN by construction (utilization and full debt service "
            "are rarely cleanly filed), so only issuers with filing-verified inputs contribute a ratio "
            "and the numerator/denominator kind is labeled -- no utilization or debt-service figure is "
            "invented. This is the deal/entity-level leg the separation test was missing."
        ),
    }


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[mid], 2)
    return round((ordered[mid - 1] + ordered[mid]) / 2, 2)


def _read(n_contracted: int, below_1: int, median: float | None) -> str:
    if n_contracted == 0:
        return (
            "indeterminate_contracted_coverage: no issuer filed both a contracted-revenue run-rate "
            "and debt service cleanly enough to compute a contracted-coverage ratio; the leg remains "
            "interest-coverage / revenue-proxy based until per-deal contract economics are disclosed."
        )
    if below_1 >= n_contracted / 2:
        return (
            f"contracted_revenue_under_covers_debt_service: of {n_contracted} issuers with a "
            f"computable contracted-coverage ratio, {below_1} have CONTRACTED revenue below their "
            f"debt service (coverage < 1x; median ~{median}x). Even fully-utilized contracted backlog "
            "does not cover the obligations -- the mismatch is structural, not a utilization-miss tail."
        )
    return (
        f"contracted_coverage_thin_but_positive: {n_contracted} issuers have computable contracted "
        f"coverage (median ~{median}x), {below_1} below 1x. Coverage holds at contracted utilization "
        "but the break-even utilization is the live risk -- see per-issuer breakeven_utilization_pct."
    )
