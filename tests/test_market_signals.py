"""Unit tests for the pre-registered signal evaluation (src/bubble/market_signals.py).

Fixture values mirror the 2026-06-12 registration/amendment-day readings documented in
analysis/preregistered_signals.md, so the tests double as a record of what the signals
read on the day their semantics were fixed.
"""

from __future__ import annotations

from datetime import date

from bubble.market_signals import (
    BDC_CONTROL,
    BDC_EXPOSED,
    eval_s1,
    eval_s1b,
    eval_s2,
    eval_s3,
    eval_s4,
    evaluate_signals,
)

TODAY = date(2026, 6, 12)


def _deal(spread_bp: int | None = 332, deal_date: str = "2026-06-02", **extra: object) -> dict:
    d: dict = {"issuer": "Elk Grove Village Property LLC", "date": deal_date}
    if spread_bp is not None:
        d["spread_vs_5y_bp"] = spread_bp
    d.update(extra)
    return d


class TestS1:
    def test_fresh_tight_print_is_contra(self) -> None:
        sig = eval_s1(_deal(332), TODAY)
        assert sig is not None
        assert sig["status"] == "contra"
        assert sig["print_age_days"] == 10

    def test_crack_band_is_confirming(self) -> None:
        sig = eval_s1(_deal(820), TODAY)
        assert sig is not None and sig["status"] == "confirming"

    def test_between_thresholds_is_neutral(self) -> None:
        sig = eval_s1(_deal(700), TODAY)
        assert sig is not None and sig["status"] == "neutral"

    def test_stale_print_never_reads_contra(self) -> None:
        # amendment A4: a 332bp print >45 days old must NOT count as window-open evidence
        sig = eval_s1(_deal(332, deal_date="2026-04-14"), TODAY)
        assert sig is not None
        assert sig["status"] == "stale"
        assert sig["print_age_days"] == 59

    def test_stale_beats_even_a_confirming_spread(self) -> None:
        sig = eval_s1(_deal(900, deal_date="2026-01-02"), TODAY)
        assert sig is not None and sig["status"] == "stale"

    def test_no_deal_or_no_spread_yields_none(self) -> None:
        assert eval_s1(None, TODAY) is None
        assert eval_s1(_deal(spread_bp=None), TODAY) is None


class TestS1b:
    def test_all_priced_is_neutral(self) -> None:
        sig = eval_s1b([{"status": "priced", "date": "2026-04-14"}])
        assert sig is not None
        assert sig["status"] == "neutral"
        assert sig["event"] is None

    def test_missing_status_treated_as_priced(self) -> None:
        # pre-amendment cards have no status field; they were completed prints
        sig = eval_s1b([{"date": "2026-04-14"}])
        assert sig is not None and sig["status"] == "neutral"

    def test_any_pulled_print_is_confirming(self) -> None:
        sig = eval_s1b(
            [
                {"status": "priced", "date": "2026-04-14", "issuer": "A"},
                {"status": "pulled", "date": "2026-07-01", "issuer": "B"},
            ]
        )
        assert sig is not None
        assert sig["status"] == "confirming"
        assert sig["event"] == {"issuer": "B", "date": "2026-07-01", "status": "pulled"}

    def test_no_cards_yields_none(self) -> None:
        assert eval_s1b([]) is None


def _credit(
    ccc_ytd: float | None = 0.68,
    hy_ytd: float | None = -0.05,
    bb_ytd: float | None = -0.02,
) -> dict:
    out: dict = {}
    if ccc_ytd is not None:
        out["ccc_oas"] = {"value": 9.56, "ytd_chg": ccc_ytd}
    if hy_ytd is not None:
        out["hy_oas"] = {"value": 2.78, "ytd_chg": hy_ytd}
    if bb_ytd is not None:
        out["bb_oas"] = {"value": 1.69, "ytd_chg": bb_ytd}
    return out


class TestS2:
    def test_amendment_day_reading_is_neutral(self) -> None:
        sig = eval_s2(_credit())
        assert sig is not None
        assert sig["status"] == "neutral"
        assert sig["ccc_minus_hy_ytd_pp"] == 0.73
        assert sig["market_wide_flag"] is False

    def test_differential_widening_is_confirming(self) -> None:
        sig = eval_s2(_credit(ccc_ytd=2.0, hy_ytd=0.3))
        assert sig is not None and sig["status"] == "confirming"

    def test_parallel_hy_selloff_does_not_fire(self) -> None:
        # the A2 rationale: CCC +2pp with HY +2pp is a market move, not tail divergence
        sig = eval_s2(_credit(ccc_ytd=2.0, hy_ytd=2.0))
        assert sig is not None and sig["status"] == "contra"

    def test_bb_control_sets_market_wide_flag(self) -> None:
        sig = eval_s2(_credit(ccc_ytd=2.0, hy_ytd=0.2, bb_ytd=1.3))
        assert sig is not None
        assert sig["status"] == "confirming"
        assert sig["market_wide_flag"] is True
        assert "market-wide" in sig["desc"]

    def test_missing_series_yields_none(self) -> None:
        assert eval_s2({}) is None
        assert eval_s2(_credit(hy_ytd=None)) is None

    def test_missing_bb_is_tolerated(self) -> None:
        sig = eval_s2(_credit(bb_ytd=None))
        assert sig is not None
        assert sig["bb_ytd_chg_pp"] is None
        assert sig["market_wide_flag"] is False


def _bdc_quotes(**discounts: float) -> dict[str, dict]:
    return {sym: {"discount_pct": pct} for sym, pct in discounts.items()}


AMENDMENT_DAY = {
    "BXSL": 9.2,
    "ARCC": 1.7,
    "FSK": 41.3,
    "OBDC": 22.4,
    "MAIN": -55.5,
    "GBDC": 7.4,
    "TSLX": -4.1,
    "PSEC": 62.3,
}


class TestS3:
    def test_amendment_day_reading_is_neutral(self) -> None:
        sig = eval_s3(_bdc_quotes(**AMENDMENT_DAY))
        assert sig is not None
        assert sig["status"] == "neutral"
        assert sig["worst"] == "BXSL"
        # (-4.1 + 7.4) / 2 floats to 1.6500000000000004 -> rounds to 1.7
        assert sig["control_median_pct"] == 1.7
        assert sig["differential_pp"] == 7.5

    def test_fsk_and_obdc_cannot_drive_the_signal(self) -> None:
        # the A1 fix: the confounded names are in neither set
        assert "FSK" not in BDC_EXPOSED and "FSK" not in BDC_CONTROL
        assert "OBDC" not in BDC_EXPOSED and "OBDC" not in BDC_CONTROL
        sig = eval_s3(_bdc_quotes(**{**AMENDMENT_DAY, "FSK": 80.0, "OBDC": 70.0}))
        assert sig is not None and sig["worst"] == "BXSL"

    def test_exposure_specific_stress_is_confirming(self) -> None:
        sig = eval_s3(_bdc_quotes(**{**AMENDMENT_DAY, "BXSL": 25.0}))
        assert sig is not None
        assert sig["status"] == "confirming"
        assert sig["differential_pp"] == 23.3

    def test_inside_sector_dispersion_is_contra(self) -> None:
        sig = eval_s3(_bdc_quotes(**{**AMENDMENT_DAY, "BXSL": 5.0, "ARCC": 1.0}))
        assert sig is not None and sig["status"] == "contra"

    def test_median_absorbs_the_regime_outliers(self) -> None:
        # MAIN at an extreme premium and PSEC at an extreme discount move the median not at all
        base = eval_s3(_bdc_quotes(**AMENDMENT_DAY))
        wild = eval_s3(_bdc_quotes(**{**AMENDMENT_DAY, "MAIN": -200.0, "PSEC": 95.0}))
        assert base is not None and wild is not None
        assert base["control_median_pct"] == wild["control_median_pct"]

    def test_thin_control_basket_is_insufficient_data(self) -> None:
        sig = eval_s3(_bdc_quotes(BXSL=9.2, ARCC=1.7, GBDC=7.4))
        assert sig is not None
        assert sig["status"] == "insufficient_data"

    def test_no_exposed_quotes_yields_none(self) -> None:
        assert eval_s3(_bdc_quotes(GBDC=7.4, TSLX=-4.1)) is None


def _baskets(*pairs: tuple[str, float]) -> list[dict]:
    return [{"as_of": d, "total_usd_b": t} for d, t in pairs]


class TestS4:
    def test_registration_day_reading_is_contra(self) -> None:
        sig = eval_s4(_baskets(("2025-07-01", 30.6), ("2026-06-12", 108.0)))
        assert sig is not None
        assert sig["status"] == "contra"
        assert sig["yoy_growth_pct"] == 252.9

    def test_stalled_demand_is_confirming(self) -> None:
        sig = eval_s4(_baskets(("2025-07-01", 100.0), ("2026-06-12", 130.0)))
        assert sig is not None and sig["status"] == "confirming"

    def test_between_paths_is_neutral(self) -> None:
        sig = eval_s4(_baskets(("2025-07-01", 100.0), ("2026-06-12", 175.0)))
        assert sig is not None and sig["status"] == "neutral"

    def test_single_basket_is_insufficient_history(self) -> None:
        sig = eval_s4(_baskets(("2026-06-12", 108.0)))
        assert sig is not None
        assert sig["status"] == "insufficient_history"

    def test_base_outside_yoy_window_is_insufficient(self) -> None:
        sig = eval_s4(_baskets(("2026-01-01", 80.0), ("2026-06-12", 108.0)))
        assert sig is not None and sig["status"] == "insufficient_history"

    def test_latest_qualifying_base_is_used(self) -> None:
        sig = eval_s4(_baskets(("2024-06-01", 10.0), ("2025-07-01", 30.6), ("2026-06-12", 108.0)))
        assert sig is not None
        assert sig["base_as_of"] == "2025-07-01"

    def test_no_baskets_yields_none(self) -> None:
        assert eval_s4([]) is None


class TestEvaluateSignals:
    def test_amendment_day_full_dashboard(self) -> None:
        """The 2026-06-12 post-amendment state: S1 contra, S1b/S2/S3 neutral, S4 contra."""
        sigs = evaluate_signals(
            credit=_credit(),
            bdc=_bdc_quotes(**AMENDMENT_DAY),
            deals=[{"status": "priced", "date": "2026-06-02"}],
            latest_deal=_deal(332),
            demand_baskets=_baskets(("2025-07-01", 30.6), ("2026-06-12", 108.0)),
            today=TODAY,
        )
        by_id = {s["id"]: s["status"] for s in sigs}
        assert by_id == {
            "S1_new_issue_spread": "contra",
            "S1b_failed_print": "neutral",
            "S2_ccc_divergence": "neutral",
            "S3_bdc_discount_differential": "neutral",
            "S4_demand_trajectory": "contra",
        }

    def test_unmeasurable_components_are_dropped_not_defaulted(self) -> None:
        sigs = evaluate_signals(
            credit={}, bdc={}, deals=[], latest_deal=None, demand_baskets=[], today=TODAY
        )
        assert sigs == []
