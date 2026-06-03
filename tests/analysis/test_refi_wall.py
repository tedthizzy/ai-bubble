"""Named refinancing-wall synthesis."""

from __future__ import annotations

from bubble.analysis.refi_wall import aggregate_refi_wall


def _stack(entity, facilities):
    return {"stack": {"entity": entity, "facilities": facilities}}


def _fac(name, year, principal):
    return {"name": name, "maturity_year": year, "principal_usd": principal}


def test_blocks_without_dated_facilities() -> None:
    out = aggregate_refi_wall([_stack("X", [_fac("F", None, None)])])
    assert out["status"] == "blocked_no_dated_facilities"


def test_builds_named_wall_and_near_term() -> None:
    census = [
        _stack(
            "CoreWeave, Inc.",
            [
                _fac("DDTL 1.0", 2026, 1_000_000_000),
                _fac("DDTL 2.0", 2030, 4_000_000_000),
            ],
        ),
        _stack(
            "IREN Limited",
            [
                _fac("2029 Convert", 2027, 500_000_000),
                _fac("2031 Convert", 2031, 1_000_000_000),
            ],
        ),
    ]
    out = aggregate_refi_wall(census)
    assert out["status"] == "source_backed"
    assert out["facility_count"] == 4
    assert out["total_dated_debt_usd"] == 6_500_000_000
    # Near-term 2025-2027 = DDTL 1.0 (2026, 1B) + IREN 2029 Convert (2027, 0.5B) = 1.5B
    assert out["near_term_2025_2027_usd"] == 1_500_000_000
    # Peak year is 2030 ($4B).
    assert out["peak_maturity_year"] == 2030
    # Most-exposed near-term issuer is CoreWeave ($1B).
    assert out["near_term_most_exposed_issuers"][0]["issuer"] == "CoreWeave"
    # Named near-term facilities present and sorted by size.
    assert out["near_term_named_facilities"][0]["facility"] == "DDTL 1.0"
    assert "refi_wall_named" in out["wall_read"]


def test_year_string_and_range_parsing() -> None:
    out = aggregate_refi_wall([_stack("Y", [_fac("F", "due 2026", 100), _fac("G", "2027-2028", 50)])])
    years = {r["year"] for r in out["wall_by_year"]}
    assert 2026 in years and 2027 in years
