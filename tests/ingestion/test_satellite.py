"""Satellite construction-progress change detection (pure band math)."""

from __future__ import annotations

from bubble.ingestion import satellite as sat


def test_band_indices() -> None:
    # Healthy vegetation: high NIR, low Red -> high NDVI.
    veg = {"B8": 0.4, "B4": 0.05, "B11": 0.1, "B2": 0.03}
    assert sat.ndvi(veg) > 0.7
    # Bare/built: high SWIR vs NIR -> positive NDBI.
    built = {"B8": 0.2, "B11": 0.35, "B4": 0.25, "B2": 0.2}
    assert sat.ndbi(built) > 0


def test_active_construction_signal() -> None:
    before = {"B8": 0.40, "B4": 0.05, "B11": 0.10, "B2": 0.03}  # vegetated
    after = {"B8": 0.20, "B4": 0.25, "B11": 0.35, "B2": 0.20}  # cleared / bare-built
    out = sat.classify_construction(before, after)
    assert out["construction_signal"] == "active_construction_or_clearing"
    assert out["ndvi_delta"] < -0.1
    assert out["bsi_delta"] > 0.05 or out["ndbi_delta"] > 0.05


def test_no_change_signal() -> None:
    same = {"B8": 0.3, "B4": 0.2, "B11": 0.25, "B2": 0.18}
    out = sat.classify_construction(same, dict(same))
    assert out["construction_signal"] == "no_significant_change"
    assert out["ndvi_delta"] == 0.0


def test_aggregate_blocks_empty() -> None:
    assert aggregate_status([]) == "blocked_no_satellite_observations"


def aggregate_status(records):  # helper
    return sat.aggregate_satellite_observations(records)["status"]


def _obs(site, signal, mw=0, ndvi_delta=0.0):
    return {
        "site": site,
        "capacity_mw": mw,
        "classification": {
            "construction_signal": signal,
            "ndvi_delta": ndvi_delta,
            "ndbi_delta": 0.0,
        },
    }


def test_aggregate_lagging_read() -> None:
    recs = [
        _obs("A", "active_construction_or_clearing", mw=1000),
        _obs("B", "no_significant_change", mw=5000),
        _obs("C", "no_significant_change", mw=3000),
    ]
    out = sat.aggregate_satellite_observations(recs)
    assert out["status"] == "source_backed"
    assert out["active_construction_sites"] == 1
    assert out["no_change_sites"] == 2
    assert "buildout_lagging_announcements" in out["physical_read"]
    # Highest-capacity no-change site surfaces first.
    assert out["high_capacity_no_change_sites"][0]["site"] == "B"


def test_aggregate_underway_read() -> None:
    recs = [
        _obs("A", "active_construction_or_clearing", mw=1000),
        _obs("B", "built_up_increase", mw=2000),
        _obs("C", "no_significant_change", mw=500),
    ]
    out = sat.aggregate_satellite_observations(recs)
    assert "buildout_visibly_underway" in out["physical_read"]
    assert out["active_construction_sites"] == 2
