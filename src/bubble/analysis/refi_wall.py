"""Named refinancing wall — the specific maturities, by year, with most-exposed issuers.

The Final Burry Report needs a specific crack timeline: which dollars come due
when, in which named facilities, and which issuers are most exposed near-term. The
debt census already carries per-facility maturity_year + principal; this turns
that into a year-by-year wall with the SPECIFIC named facilities and a near-term
(2026-2027) focus, plus the per-issuer near-term exposure ranking.

It is a deterministic synthesis of the primary-sourced census -- it adds no new
assumption, only re-shapes verified facility maturities into the refinancing-wall
view, so a thin or negative-carry issuer's near-term maturities are named rather
than buried in a yearly total.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_NEAR_TERM_YEARS = {2025, 2026, 2027}


def load_debt_census_raw(path: str | Path) -> list[dict[str, Any]]:
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


def _year(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    text = str(value or "")
    for token in text.replace("-", " ").split():
        if token.isdigit() and 2024 <= int(token) <= 2040:
            return int(token)
    return None


def aggregate_refi_wall(census_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the year-by-year named refinancing wall from the debt census facilities."""

    facilities: list[dict[str, Any]] = []
    for rec in census_records:
        stack = rec.get("stack") or rec
        issuer = _short(stack.get("entity", ""))
        for f in stack.get("facilities") or []:
            principal = _num(f.get("principal_usd"))
            year = _year(f.get("maturity_year"))
            if not issuer or principal is None or year is None:
                continue
            facilities.append(
                {
                    "issuer": issuer,
                    "facility": str(f.get("name") or "")[:80],
                    "principal_usd": principal,
                    "maturity_year": year,
                }
            )

    if not facilities:
        return {"status": "blocked_no_dated_facilities", "facility_count": 0}

    total = sum(f["principal_usd"] for f in facilities)
    by_year: dict[int, dict[str, Any]] = {}
    for f in facilities:
        y = f["maturity_year"]
        slot = by_year.setdefault(y, {"total_usd": 0.0, "facilities": []})
        slot["total_usd"] += f["principal_usd"]
        slot["facilities"].append(
            {"issuer": f["issuer"], "facility": f["facility"], "principal_usd": f["principal_usd"]}
        )

    year_rows = []
    for y in sorted(by_year):
        slot = by_year[y]
        slot["facilities"].sort(key=lambda x: x["principal_usd"], reverse=True)
        year_rows.append(
            {
                "year": y,
                "total_usd": round(slot["total_usd"], 2),
                "pct_of_dated_debt": round(100 * slot["total_usd"] / total, 1) if total else None,
                "facility_count": len(slot["facilities"]),
                "facilities": slot["facilities"][:6],
            }
        )

    near_facs = [f for f in facilities if f["maturity_year"] in _NEAR_TERM_YEARS]
    near_total = sum(f["principal_usd"] for f in near_facs)
    near_by_issuer: dict[str, float] = {}
    for f in near_facs:
        near_by_issuer[f["issuer"]] = near_by_issuer.get(f["issuer"], 0.0) + f["principal_usd"]
    peak = max(year_rows, key=lambda r: r["total_usd"]) if year_rows else None

    return {
        "status": "source_backed",
        "facility_count": len(facilities),
        "total_dated_debt_usd": round(total, 2),
        "wall_by_year": year_rows,
        "peak_maturity_year": peak["year"] if peak else None,
        "peak_year_usd": peak["total_usd"] if peak else None,
        "near_term_2025_2027_usd": round(near_total, 2),
        "near_term_pct_of_dated_debt": round(100 * near_total / total, 1) if total else None,
        "near_term_most_exposed_issuers": [
            {"issuer": k, "near_term_maturities_usd": round(v, 2)}
            for k, v in sorted(near_by_issuer.items(), key=lambda kv: -kv[1])[:5]
        ],
        "near_term_named_facilities": sorted(
            (
                {
                    "issuer": f["issuer"],
                    "facility": f["facility"],
                    "principal_usd": f["principal_usd"],
                    "maturity_year": f["maturity_year"],
                }
                for f in near_facs
            ),
            key=lambda x: x["principal_usd"],
            reverse=True,
        )[:8],
        "wall_read": _read(year_rows, near_total, total, peak),
        "note": (
            "Named refinancing wall from the primary-sourced debt census: per-facility maturities "
            "re-shaped into a year-by-year wall with the specific named facilities and the near-term "
            "(2025-2027) most-exposed issuers. Deterministic synthesis -- no new assumption; it names "
            "which dollars come due when so the crack timeline is specific, not a yearly total."
        ),
    }


def _read(
    year_rows: list[dict[str, Any]], near_total: float, total: float, peak: dict[str, Any] | None
) -> str:
    if not peak or not total:
        return "indeterminate"
    near_pct = round(100 * near_total / total, 1)
    return (
        f"refi_wall_named: ${round(total / 1e9, 1)}B of dated cluster debt; peak maturity year "
        f"{peak['year']} (${round(peak['total_usd'] / 1e9, 1)}B). Near-term 2025-2027 maturities are "
        f"${round(near_total / 1e9, 1)}B ({near_pct}% of dated debt) -- the specific facilities and "
        "most-exposed issuers are named, so the crack timeline is a concrete refinancing schedule on "
        "negative-carry debt, not a yearly aggregate."
    )
