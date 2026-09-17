"""Unit tests for the verdict decomposition tree (src/bubble/verdict_tree.py)."""

from __future__ import annotations

from datetime import date

from bubble.verdict_tree import (
    LEAVES,
    P_REAL_WINDOW_END,
    PROMOTED,
    STRUCTURAL_CONFIDENCE,
    TIMING_KILL_ADJUDICATION_QUARTER,
    Leaf,
    brier_score,
    realization_forecast,
    realization_outcome,
)


class TestShadowMode:
    def test_starts_in_shadow_mode(self) -> None:
        assert PROMOTED is False
        assert realization_forecast()["promoted"] is False

    def test_structural_confidence_unchanged_and_separate(self) -> None:
        out = realization_forecast()
        assert out["structural_confidence_unchanged"] == STRUCTURAL_CONFIDENCE == 0.67
        # the forecast is a DIFFERENT quantity, and lower than the structural confidence
        assert out["p_real"] < out["structural_confidence_unchanged"]


class TestFactorization:
    def test_two_pathways_present(self) -> None:
        out = realization_forecast()
        assert "pathway_operations_first" in out
        assert "pathway_funding_first" in out

    def test_window_first_is_a_first_class_leaf(self) -> None:
        # the fiber-1999 sequence must be representable as its own pathway
        assert "window_closes_first" in LEAVES
        assert "event_given_window_first" in LEAVES

    def test_noisy_or_combination(self) -> None:
        out = realization_forecast()
        a, b = out["pathway_operations_first"], out["pathway_funding_first"]
        assert abs(out["p_real"] - (1 - (1 - a) * (1 - b))) < 1e-9

    def test_funding_first_pathway_nonzero_without_op_distress(self) -> None:
        # window-first must contribute even if operations are fine -> pathway B > 0 standalone
        out = realization_forecast()
        assert out["pathway_funding_first"] > 0


class TestSignalWiring:
    def test_base_forecast_is_moderate(self) -> None:
        assert 0.35 < realization_forecast()["p_real"] < 0.5

    def test_all_confirming_raises_forecast(self) -> None:
        base = realization_forecast()["p_real"]
        confirming = realization_forecast(
            {
                "S1_new_issue_spread": "confirming",
                "S1b_failed_print": "confirming",
                "S2_ccc_divergence": "confirming",
                "S3_bdc_discount_differential": "confirming",
                "S4_demand_trajectory": "confirming",
            }
        )["p_real"]
        assert confirming > base

    def test_contra_lowers_forecast(self) -> None:
        base = realization_forecast()["p_real"]
        contra = realization_forecast(
            {"S1_new_issue_spread": "contra", "S4_demand_trajectory": "contra"}
        )["p_real"]
        assert contra < base

    def test_s4_confirming_raises_op_distress(self) -> None:
        # demand stalling (S4 confirming) must RAISE the op-distress leaf, not lower it
        leaf = LEAVES["op_distress"]
        assert leaf.adjusted_p({"S4_demand_trajectory": "confirming"}) > leaf.base_p
        assert leaf.adjusted_p({"S4_demand_trajectory": "contra"}) < leaf.base_p

    def test_leaf_probability_clamped(self) -> None:
        lf = Leaf("x", "x", 0.99, "r", "p", {"S1": "up"})
        # even stacked confirming can't exceed the clamp
        assert lf.adjusted_p({"S1": "confirming"}) <= 0.98
        lo = Leaf("y", "y", 0.03, "r", "p", {"S1": "up"})
        assert lo.adjusted_p({"S1": "contra"}) >= 0.02


class TestBrier:
    def test_empty_is_none(self) -> None:
        assert brier_score([])["brier"] is None

    def test_perfect_forecast_scores_zero(self) -> None:
        assert brier_score([(1.0, 1), (0.0, 0)])["brier"] == 0.0

    def test_coin_flip_scores_quarter(self) -> None:
        assert brier_score([(0.5, 1), (0.5, 0)])["brier"] == 0.25

    def test_ignores_unresolved_outcomes(self) -> None:
        # outcomes not in {0,1} are treated as unresolved and dropped
        out = brier_score([(0.5, 1), (0.5, 2)])
        assert out["n"] == 1


class TestRealizationResolution:
    def test_forecast_declares_separate_dates(self) -> None:
        out = realization_forecast()
        assert out["p_real_outcome_window_end"] == "2027-09-30"
        assert out["timing_kill_adjudication_quarter"] == "2026-Q4"

    def test_elapsed_q2_pressure_peak_is_not_an_event(self) -> None:
        # June's 0.8738 timing score measures scheduled inputs, not issuer distress.
        outcome = realization_outcome(as_of=date(2026, 9, 16))
        assert outcome is None
        assert brier_score([(0.39, outcome)])["n"] == 0

    def test_event_free_q4_does_not_resolve_negative(self) -> None:
        assert TIMING_KILL_ADJUDICATION_QUARTER == "2026-Q4"
        assert (
            realization_outcome(as_of=date(2026, 12, 31), issuer_event_coverage_complete=True)
            is None
        )

    def test_filing_verified_event_resolves_early_positive(self) -> None:
        assert (
            realization_outcome(
                as_of=date(2026, 9, 16),
                filing_verified_qualifying_event_date=date(2026, 8, 20),
            )
            == 1
        )

    def test_negative_requires_window_close_and_complete_audit(self) -> None:
        assert realization_outcome(as_of=P_REAL_WINDOW_END) is None
        assert (
            realization_outcome(as_of=P_REAL_WINDOW_END, issuer_event_coverage_complete=True) == 0
        )

    def test_out_of_window_or_future_events_do_not_resolve_positive(self) -> None:
        assert (
            realization_outcome(
                as_of=date(2027, 10, 1),
                filing_verified_qualifying_event_date=date(2027, 10, 1),
            )
            is None
        )
        try:
            realization_outcome(
                as_of=date(2026, 9, 16),
                filing_verified_qualifying_event_date=date(2026, 9, 17),
            )
        except ValueError:
            pass
        else:
            raise AssertionError("future issuer events cannot be scored")
