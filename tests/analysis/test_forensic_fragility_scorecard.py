"""Forensic fragility: first-principles tipping conditions (no borrowed thresholds)."""

from __future__ import annotations

from bubble.analysis.forensic_fragility_scorecard import score_fragility


def _full_mismatch():
    return {
        "refi_wall": {"peak_maturity_year": 2030},
        "_max_single_customer_pct": 67,
        "contract_structure": {
            "recourse_breakdown_counts": {
                "full_recourse_to_parent": 16,
                "limited_recourse": 1,
                "non_recourse": 2,
                "unclear": 3,
            }
        },
        "red_flag_scorecard": {
            "issuer_count": 8,
            "most_common_flags": {"customer_concentration_over_35pct": 8},
        },
        "satellite_construction": {
            "status": "source_backed",
            "site_count": 762,
            "no_change_sites": 407,
        },
        "entity_universe_map": {
            "entity_count": 649,
            "by_bucket": {"financed_ai_infra_leveraged": 28},
        },
    }


def test_blocks_when_no_dimensions() -> None:
    assert score_fragility({})["status"] == "blocked_no_measured_dimensions"


def test_first_principles_conditions_met() -> None:
    out = score_fragility(_full_mismatch())
    assert out["status"] == "source_backed"
    cond = {d["dimension"]: d.get("condition_met") for d in out["dimensions"]}
    # Duration: 48mo > 24mo -> met.
    assert cond["asset_liability_duration_mismatch"] is True
    # Concentration: 67% > 50% -> existential, met.
    assert cond["customer_concentration"] is True
    # Execution: 53.4% > 50% -> met.
    assert cond["execution_mismatch_physical"] is True
    # Recourse + tail-size have NO principled binary -> condition is None (not a borrowed zone).
    assert cond["loss_incidence_recourse"] is None
    assert cond["leveraged_tail_size"] is None
    assert out["first_principles_conditions_met"] == 3
    assert out["first_principles_conditions_evaluated"] == 3
    assert "first_principles_tipping_conditions_met" in out["composite_read"]


def test_no_borrowed_thresholds_for_recourse_and_tail() -> None:
    out = score_fragility(_full_mismatch())
    recourse = next(d for d in out["dimensions"] if d["dimension"] == "loss_incidence_recourse")
    tail = next(d for d in out["dimensions"] if d["dimension"] == "leveraged_tail_size")
    # These dimensions report a magnitude + interpretation, no fabricated cutoff.
    assert recourse["first_principles_condition"] is None
    assert tail["first_principles_condition"] is None
    assert "parent" in recourse["interpretation"].lower()
    assert "contained" in tail["interpretation"].lower()


def test_duration_not_met_when_debt_short() -> None:
    out = score_fragility({"refi_wall": {"peak_maturity_year": 2027}})  # 12mo < 24mo GPU life
    dur = next(d for d in out["dimensions"] if d["dimension"] == "asset_liability_duration_mismatch")
    assert dur["condition_met"] is False
