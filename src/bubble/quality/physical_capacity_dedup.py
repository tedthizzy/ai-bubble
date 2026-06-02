"""Physical data-center capacity dedup (root cause 2, capacity dimension).

The capacity metric is ~98.5% clean, but a few projects are split into multiple rows
by **state-name format** (`PA` vs `Pennsylvania`) or a **border city** (Kansas City
recorded in both MO and KS), inflating the MW total. Keying on
``(normalized_name, normalized_city)`` collapses the same campus while keeping a
multi-site operator's genuinely separate locations (e.g. Cielo Digital's three
different-state 500MW sites) distinct — so dedup must NOT key on name+capacity.

``summarize_physical_capacity_dedup`` reports the raw vs deduped MW and the collapsed
clusters. Pure functions; the production dedup is Codex's.
"""

from __future__ import annotations

import re
from typing import Any


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _capacity_mw(row: dict[str, str]) -> float:
    for key in ("capacity_mw_high", "capacity_mw"):
        try:
            value = float(row.get(key) or 0.0)
        except ValueError:
            value = 0.0
        if value:
            return value
    return 0.0


def physical_dedup_key(row: dict[str, str]) -> str:
    """Same-campus key: normalized project name + city (state-format / border-city safe).

    Deliberately ignores state (``PA`` ≡ ``Pennsylvania``; a border city straddling two
    states is one campus) and capacity (a multi-site operator builds many same-size
    sites), keying on name + city so genuinely separate sites stay distinct.
    """

    return f"{_norm(row.get('name', ''))}|{_norm(row.get('city', ''))}"


def summarize_physical_capacity_dedup(rows: list[dict[str, str]]) -> dict[str, Any]:
    """Report raw vs deduped capacity MW and the collapsed same-campus clusters."""

    raw = sum(_capacity_mw(r) for r in rows)
    groups: dict[str, float] = {}
    sizes: dict[str, int] = {}
    label: dict[str, dict[str, str]] = {}
    for row in rows:
        mw = _capacity_mw(row)
        if mw <= 0:
            continue
        key = physical_dedup_key(row)
        groups[key] = max(groups.get(key, 0.0), mw)
        sizes[key] = sizes.get(key, 0) + 1
        label.setdefault(key, {"name": row.get("name", ""), "city": row.get("city", "")})
    deduped = sum(groups.values())
    multi = [(k, sizes[k], groups[k]) for k in sizes if sizes[k] > 1]
    multi.sort(key=lambda t: t[2] * (t[1] - 1), reverse=True)
    collapsed: list[dict[str, Any]] = [
        {"name": label[k]["name"], "city": label[k]["city"], "rows": n, "capacity_mw": mw}
        for k, n, mw in multi
    ]
    return {
        "projects": len([r for r in rows if _capacity_mw(r) > 0]),
        "distinct_campuses": len(groups),
        "raw_capacity_mw": round(raw, 1),
        "deduped_capacity_mw": round(deduped, 1),
        "dup_excess_mw": round(raw - deduped, 1),
        "top_collapsed": collapsed[:10],
    }
