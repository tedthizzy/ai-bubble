"""Tests for the forward refinancing-wall split."""

from __future__ import annotations

import pytest

from bubble.quality.forward_refinancing import split_maturity_wall, wall_from_signals


def test_split_separates_past_from_forward() -> None:
    wall = {
        "2025-Q4": 112.6e9,  # past
        "2026-Q1": 23.0e9,  # past
        "2026-Q2": 24.2e9,  # forward (peak)
        "2026-Q4": 14.0e9,  # forward
        "2030-Q1": 5.9e9,  # forward
    }
    s = split_maturity_wall(wall, as_of_quarter="2026-Q2")

    assert s["historical_usd"] == round(112.6e9 + 23.0e9, 2)
    assert s["forward_usd"] == round(24.2e9 + 14.0e9 + 5.9e9, 2)
    assert s["forward_peak_quarter"] == "2026-Q2"
    assert s["forward_peak_usd"] == 24.2e9
    # near-term = first 4 forward quarters (all 3 here).
    assert s["near_term_usd"] == round(24.2e9 + 14.0e9 + 5.9e9, 2)
    assert s["historical_pct"] == round((112.6e9 + 23.0e9) / (112.6e9 + 23.0e9 + 44.1e9) * 100, 1)


def test_unparseable_quarters_ignored_and_invalid_as_of_raises() -> None:
    s = split_maturity_wall({"n/a": 5e9, "2027-Q1": 9.6e9}, as_of_quarter="2026-Q2")
    assert s["forward_usd"] == 9.6e9
    assert s["historical_usd"] == 0.0
    with pytest.raises(ValueError, match="invalid as_of_quarter"):
        split_maturity_wall({}, as_of_quarter="nope")


def test_wall_from_signals_filters_category() -> None:
    rows = [
        {"category": "capital", "quarter": "2026-Q2", "amount_usd": "10e9"},
        {"category": "capital", "quarter": "2026-Q2", "amount_usd": "5e9"},
        {"category": "compute", "quarter": "2026-Q2", "amount_usd": "99e9"},
    ]
    wall = wall_from_signals(rows)
    assert wall == {"2026-Q2": 15e9}
