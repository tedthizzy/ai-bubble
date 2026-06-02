"""Physical capacity dedup fixtures (root cause 2, capacity dimension).

Positive fixtures are the verified same-campus dups (state-format / border city);
the negative control is a multi-site operator whose sites must stay distinct.
"""

from __future__ import annotations

from bubble.quality.physical_capacity_dedup import (
    physical_dedup_key,
    summarize_physical_capacity_dedup,
)


def _proj(name: str, city: str, state: str, mw: float) -> dict[str, str]:
    return {"name": name, "city": city, "state": state, "capacity_mw_high": str(mw)}


def test_state_format_and_border_city_collapse_to_one_campus() -> None:
    # Homer City: same campus, state "PA" vs "Pennsylvania".
    a = _proj("Homer City Energy Campus", "Homer City", "PA", 4500)
    b = _proj("Homer City Energy Campus", "Homer City", "Pennsylvania", 4500)
    assert physical_dedup_key(a) == physical_dedup_key(b)
    # Google KC: border city recorded in MO and KS -> one campus.
    c = _proj("Google Kansas City Data Center", "Kansas City", "Missouri", 400)
    d = _proj("Google Kansas City Data Center", "Kansas City", "Kansas", 400)
    assert physical_dedup_key(c) == physical_dedup_key(d)


def test_multi_site_operator_sites_stay_distinct() -> None:
    # Cielo Digital: three genuinely separate 500MW sites in different cities -> NOT merged.
    keys = {
        physical_dedup_key(_proj("Cielo Digital Infrastructure", city, st, 500))
        for city, st in (("Minooka", "IL"), ("Mustang Ridge", "TX"), ("Kansas City", "MO"))
    }
    assert len(keys) == 3


def test_summary_dedups_same_campus_keeps_separate_sites() -> None:
    rows = [
        _proj("Homer City Energy Campus", "Homer City", "PA", 4500),
        _proj("Homer City Energy Campus", "Homer City", "Pennsylvania", 4500),  # dup -> collapse
        _proj("Cielo Digital Infrastructure", "Minooka", "IL", 500),
        _proj("Cielo Digital Infrastructure", "Mustang Ridge", "TX", 500),  # separate site
        _proj("Standalone DC", "Reno", "NV", 200),
    ]

    s = summarize_physical_capacity_dedup(rows)

    assert s["projects"] == 5
    assert s["distinct_campuses"] == 4  # Homer City collapses; 2 Cielo + standalone stay
    assert s["raw_capacity_mw"] == 4500 + 4500 + 500 + 500 + 200
    assert s["deduped_capacity_mw"] == 4500 + 500 + 500 + 200
    assert s["dup_excess_mw"] == 4500
    assert s["top_collapsed"][0]["name"] == "Homer City Energy Campus"
