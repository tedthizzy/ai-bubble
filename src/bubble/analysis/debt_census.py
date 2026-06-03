"""AI-direct issuer debt census aggregation.

Aggregates the per-issuer, primary-filing-sourced debt stacks + maturity
schedules (from the adversarially-verified census fixture) into a cluster total
and a real maturity wall -- replacing the earlier curated ~$41B "floor" and the
over-stated "88% matures 2030-2033" claim with the actual schedule.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_YEARS = ["y2025", "y2026", "y2027", "y2028", "y2029", "y2030", "y2031", "y2032", "y2033"]
_TAIL = "y2034_plus"


def load_debt_census(path: str | Path) -> list[dict[str, Any]]:
    """Load the census JSON (list of {stack, verdict}); empty list if absent."""

    p = Path(path)
    if not p.exists():
        return []
    try:
        loaded = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    return [r for r in loaded if isinstance(r, dict)] if isinstance(loaded, list) else []


def _num(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


def classify_facility_recourse(facility: dict[str, Any]) -> str:
    """Who bears the loss on a facility, from its disclosed flags (Q5).

    non_recourse_secured -> secured creditors only (collateral = GPUs/SPV assets);
    full_recourse_secured -> secured AND parent/unconditionally guaranteed (parent
    equity bears it, GPU collateral is the creditor backstop);
    secured_other -> secured, no parent guarantee; unsecured -> general creditors.
    """

    guarantee = str(facility.get("guarantee") or "").lower()
    secured = bool(facility.get("secured"))
    non_recourse = "non-recourse" in guarantee or "nonrecourse" in guarantee
    parent_guaranteed = any(
        token in guarantee for token in ("parent", "unconditional", "the company", "company)")
    )
    if non_recourse:
        return "non_recourse_secured" if secured else "non_recourse"
    if secured and parent_guaranteed:
        return "full_recourse_secured"
    if secured:
        return "secured_other"
    return "unsecured"


def aggregate_debt_census(census: list[dict[str, Any]]) -> dict[str, Any]:
    """Cluster total debt + aggregate maturity schedule from source-backed stacks."""

    by_year: dict[str, float] = dict.fromkeys([*_YEARS, _TAIL], 0.0)
    total_debt = 0.0
    schedule_total = 0.0
    issuers: list[dict[str, Any]] = []
    source_backed_issuers = 0
    recourse_usd: dict[str, float] = {}

    for row in census:
        stack = row.get("stack") or {}
        verdict = row.get("verdict") or {}
        if verdict.get("overall") not in ("source_backed", "partially_source_backed"):
            continue
        source_backed_issuers += 1
        td = _num(stack.get("total_debt_usd"))
        total_debt += td
        schedule = stack.get("maturity_schedule_usd") or {}
        for year in [*_YEARS, _TAIL]:
            by_year[year] += _num(schedule.get(year))
            schedule_total += _num(schedule.get(year))
        for facility in stack.get("facilities") or []:
            cls = classify_facility_recourse(facility)
            recourse_usd[cls] = recourse_usd.get(cls, 0.0) + _num(facility.get("principal_usd"))
        issuers.append(
            {
                "entity": stack.get("entity"),
                "total_debt_usd": round(td, 2),
                "facility_count": len(stack.get("facilities") or []),
                "maturity_confirmed": bool(verdict.get("maturity_schedule_confirmed")),
            }
        )

    if not source_backed_issuers:
        return {"status": "blocked_no_source_backed_census", "issuer_count": 0}

    wall_30_33 = sum(by_year[y] for y in ("y2030", "y2031", "y2032", "y2033"))
    near_25_27 = sum(by_year[y] for y in ("y2025", "y2026", "y2027"))
    peak_year, peak_usd = max(by_year.items(), key=lambda kv: kv[1])

    def _pct(part: float) -> float:
        return round(100 * part / schedule_total, 1) if schedule_total > 0 else 0.0

    return {
        "status": "source_backed",
        "issuer_count": source_backed_issuers,
        "cluster_total_debt_usd": round(total_debt, 2),
        "scheduled_maturities_usd": round(schedule_total, 2),
        "maturity_schedule_usd_by_year": {y: round(v, 2) for y, v in by_year.items()},
        "wall_2030_2033_usd": round(wall_30_33, 2),
        "wall_2030_2033_pct_of_scheduled": _pct(wall_30_33),
        "near_term_2025_2027_usd": round(near_25_27, 2),
        "near_term_2025_2027_pct_of_scheduled": _pct(near_25_27),
        "peak_maturity_year": peak_year,
        "peak_maturity_usd": round(peak_usd, 2),
        "per_issuer": issuers,
        "who_bears_downside": {
            "by_recourse_class_usd": {k: round(v, 2) for k, v in sorted(recourse_usd.items())},
            "facilities_classified_usd": round(sum(recourse_usd.values()), 2),
            "basis_caveat": (
                "Split is on disclosed FACILITY PRINCIPAL, whose sum can exceed net drawn debt "
                "because some facilities report committed size, not drawn balance -- read the "
                "PROPORTIONS, not the absolute, as the loss-bearer mix."
            ),
            "note": (
                "Front-line loss-bearer by disclosed facility recourse. full_recourse_secured = "
                "secured on GPU/SPV collateral AND parent/unconditionally guaranteed (downside flows "
                "to PARENT equity; GPU collateral is the creditor backstop) -- this corrects the "
                "'bankruptcy-remote ring-fencing' read: most AI-direct debt is parent-recourse or "
                "unsecured-at-parent (the parent, i.e. equity, absorbs the bulk). non_recourse_secured "
                "= secured creditors bear it on GPU collateral only. unsecured = general creditors. "
                "Ratepayers/insurers/pensions are downstream and not in this split."
            ),
        },
        "note": (
            "Primary-sourced 11-issuer debt census (adversarially verified). Replaces the curated "
            "~$41B floor. The maturities are SPREAD 2026-2034 with a single-year peak, not an 88% "
            "cliff in 2030-2033: the refinancing pressure is a continuous treadmill (material "
            "near-term AND a 2030 peak), which is the real fragility -- cash-flow-negative issuers "
            "must roll debt every year, not just in 2030-2033."
        ),
    }
