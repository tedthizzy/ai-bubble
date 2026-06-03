"""Filing-verified forensic red-flag scorecard aggregation."""

from __future__ import annotations

from bubble.analysis.red_flag_scorecard import aggregate_red_flag_scorecard


def _flag(ftype, *, present="present", verdict="filing_verified"):
    return {
        "flag_type": ftype,
        "present": present,
        "detail": "d",
        "source_filing": "10-K",
        "verdict": verdict,
    }


def _rec(issuer, flags, overall="source_backed"):
    return {"issuer": issuer, "verified_flags": flags, "overall": overall}


def test_blocks_without_source_backed() -> None:
    out = aggregate_red_flag_scorecard(
        [_rec("X", [_flag("negative_operating_cash_flow")], overall="unreliable")]
    )
    assert out["status"] == "blocked_no_source_backed_red_flags"


def test_absent_and_rejected_flags_do_not_score() -> None:
    out = aggregate_red_flag_scorecard(
        [
            _rec(
                "CoreWeave",
                [
                    _flag("customer_concentration_over_35pct"),  # present, weight 3
                    _flag("going_concern_doubt", present="absent"),  # absent -> 0
                    _flag("restatement", verdict="rejected_unsourced"),  # rejected -> 0
                ],
            )
        ]
    )
    assert out["per_issuer"][0]["red_flag_score"] == 3.0
    assert out["per_issuer"][0]["present_flag_count"] == 1
    assert out["issuers_with_serious_accounting_flag"] == []


def test_serious_flags_dominate_and_rank() -> None:
    out = aggregate_red_flag_scorecard(
        [
            _rec(
                "Weakco",
                [_flag("going_concern_doubt"), _flag("material_weakness_icfr")],  # 5 + 4 = 9
            ),
            _rec(
                "Midco",
                [
                    _flag("customer_concentration_over_35pct"),  # 3
                    _flag("negative_operating_cash_flow"),  # 2
                    _flag("insider_net_selling"),  # 1
                ],
            ),
        ]
    )
    assert out["status"] == "source_backed"
    # Weakco (serious flags) ranks first despite fewer flags.
    assert out["per_issuer"][0]["issuer"] == "Weakco"
    assert out["per_issuer"][0]["red_flag_score"] == 9.0
    assert "Weakco" in out["issuers_with_serious_accounting_flag"]
    assert "serious_accounting_flags_present" in out["red_flag_read"]


def test_partial_flag_half_weights() -> None:
    out = aggregate_red_flag_scorecard(
        [_rec("Partialco", [_flag("related_party_or_circular_financing", present="partial")])]
    )
    # weight 3 * 0.5 = 1.5
    assert out["per_issuer"][0]["red_flag_score"] == 1.5


def test_pervasive_structural_flags_read() -> None:
    out = aggregate_red_flag_scorecard(
        [
            _rec("A", [_flag("negative_operating_cash_flow")]),
            _rec("B", [_flag("negative_operating_cash_flow")]),
        ]
    )
    assert "no_serious_accounting_flag_in_window" in out["red_flag_read"]
    assert "PERVASIVE" in out["red_flag_read"]
