"""Capture-recapture universe-size estimation."""

from __future__ import annotations

from bubble.analysis.universe_extrapolation import _chapman, estimate_universe


def _ent(name, sources):
    return {"name": name, "sources": sources}


def test_blocks_empty() -> None:
    assert estimate_universe([])["status"] == "blocked_no_universe"


def test_chapman_formula() -> None:
    # n1=100, n2=100, overlap=50 -> ((101*101)/51)-1 ~= 199
    assert round(_chapman(100, 100, 50)) == 199


def test_capture_recapture_with_reliable_overlap() -> None:
    # Build a universe where two sources overlap substantially.
    universe = []
    # 40 in both A and B (overlap), 60 only A, 60 only B -> n1=100, n2=100, m=40
    universe += [_ent(f"both{i}", ["A", "B"]) for i in range(40)]
    universe += [_ent(f"a{i}", ["A"]) for i in range(60)]
    universe += [_ent(f"b{i}", ["B"]) for i in range(60)]
    out = estimate_universe(universe, observed_distress_count=16)
    assert out["status"] == "inferred_capped"
    assert out["max_confidence"] == 0.45
    assert out["observed_entities"] == 160
    # Chapman: (101*101/41)-1 ~= 248
    assert 240 <= out["estimated_true_universe_mid"] <= 255
    assert out["distress_robustness"]["observed_distress_pct"] == 10.0
    # distress scales: 10% of ~248 ~= 25
    assert 22 <= out["distress_robustness"]["estimated_true_distress_count"] <= 27
    assert out["forward_sensitivity_band"]


def test_near_disjoint_pair_flagged_unreliable() -> None:
    # A and B barely overlap -> flagged, no reliable estimate.
    universe = [_ent(f"a{i}", ["A"]) for i in range(100)]
    universe += [_ent(f"b{i}", ["B"]) for i in range(100)]
    universe += [_ent("both", ["A", "B"])]  # overlap=1 (< min)
    out = estimate_universe(universe)
    assert out["status"] == "no_reliable_pair"
    assert out["pair_estimates"][0]["reliable"] is False
