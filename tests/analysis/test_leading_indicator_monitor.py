"""Forward leading-indicator monitor."""

from __future__ import annotations

from bubble.analysis.leading_indicator_monitor import build_leading_indicator_monitor


def test_blocks_empty() -> None:
    assert build_leading_indicator_monitor({})["status"] == "blocked_no_indicators"


def test_coverage_below_one_flashes() -> None:
    m = {"cluster_interest_coverage": {"status": "source_backed", "cluster_ebitda_interest_coverage": 0.9}}
    out = build_leading_indicator_monitor(m)
    assert out["status"] == "source_backed"
    cov = next(i for i in out["indicators"] if i["key"] == "cluster_interest_coverage")
    assert cov["current_status"] == "source_backed"
    assert cov["currently_flashing"] is True


def test_coverage_above_one_does_not_flash() -> None:
    m = {"cluster_interest_coverage": {"status": "source_backed", "cluster_ebitda_interest_coverage": 1.4}}
    out = build_leading_indicator_monitor(m)
    cov = next(i for i in out["indicators"] if i["key"] == "cluster_interest_coverage")
    assert cov["currently_flashing"] is False


def test_satellite_majority_unbuilt_flashes() -> None:
    m = {
        "satellite_construction": {
            "status": "source_backed",
            "site_count": 100,
            "no_change_sites": 53,
        }
    }
    out = build_leading_indicator_monitor(m)
    sat = next(i for i in out["indicators"] if i["key"] == "satellite_construction_stall")
    assert sat["current_reading"] == 53.0
    assert sat["currently_flashing"] is True


def test_vendor_round_trip_flashes_and_composite_counts() -> None:
    m = {
        "_max_single_customer_pct": 67,
        "circular_financing": {
            "status": "source_backed",
            "reciprocal_hub": {"filing_verified_round_trip_count": 2},
        },
    }
    out = build_leading_indicator_monitor(m)
    vrt = next(i for i in out["indicators"] if i["key"] == "vendor_round_trip_dependence")
    assert vrt["currently_flashing"] is True
    conc = next(i for i in out["indicators"] if i["key"] == "customer_concentration")
    assert conc["currently_flashing"] is True
    # composite reflects flashing indicators
    assert out["currently_flashing_count"] >= 2
    assert "vendor_round_trip_dependence" in out["currently_flashing"]
