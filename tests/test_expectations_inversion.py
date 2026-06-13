"""Unit tests for the expectations-inversion math (src/bubble/expectations/inversion.py)."""

from __future__ import annotations

import math

from bubble.expectations.inversion import (
    NameInputs,
    annuity_factor,
    contracted_pv,
    implied_perpetual_revenue,
    implied_revenue_multiple,
    invert_all,
    invert_name,
    renewal_dependent_share,
)
from bubble.expectations.names import NAMES


def _name(**over: object) -> NameInputs:
    base: dict = {
        "ticker": "TST",
        "name": "Test",
        "ev_usd_b": 100.0,
        "current_annualized_revenue_usd_b": 10.0,
        "revenue_basis": "test",
        "backlog_usd_b": 40.0,
        "backlog_tenor_years": 4.0,
        "backlog_basis": "test",
        "net_debt_usd_b": 0.0,
        "is_landlord": False,
        "notes": "",
    }
    base.update(over)
    return NameInputs(**base)  # type: ignore[arg-type]


class TestMath:
    def test_annuity_factor_basic(self) -> None:
        # 1/yr for 1yr at 10% = 1/1.1 ~ 0.909
        assert math.isclose(annuity_factor(0.10, 1), 1 / 1.1)

    def test_annuity_factor_zero_rate_is_years(self) -> None:
        assert annuity_factor(0.0, 5) == 5

    def test_implied_perpetual_revenue_gordon(self) -> None:
        # EV 100, r 0.12, g 0.04, margin 0.25 -> 100*0.08/0.25 = 32
        assert math.isclose(implied_perpetual_revenue(100.0, 0.12, 0.04, 0.25), 32.0)

    def test_implied_perpetual_revenue_guard(self) -> None:
        assert implied_perpetual_revenue(100.0, 0.04, 0.04, 0.25) == float("inf")
        assert implied_perpetual_revenue(100.0, 0.12, 0.04, 0.0) == float("inf")

    def test_implied_revenue_multiple(self) -> None:
        inp = _name(ev_usd_b=100.0, current_annualized_revenue_usd_b=10.0)
        # required perpetual rev 32 / current 10 = 3.2x
        assert math.isclose(implied_revenue_multiple(inp, 0.12, 0.04, 0.25), 3.2)

    def test_renewal_share_clamped_unit_interval(self) -> None:
        inp = _name(ev_usd_b=100.0, backlog_usd_b=40.0, backlog_tenor_years=4.0)
        share = renewal_dependent_share(inp, 0.12, 0.25)
        assert 0.0 <= share <= 1.0

    def test_renewal_share_high_when_backlog_small_vs_ev(self) -> None:
        thin = _name(ev_usd_b=100.0, backlog_usd_b=4.0, backlog_tenor_years=4.0)
        fat = _name(ev_usd_b=100.0, backlog_usd_b=400.0, backlog_tenor_years=4.0)
        assert renewal_dependent_share(thin, 0.12, 0.25) > renewal_dependent_share(fat, 0.12, 0.25)

    def test_renewal_share_fully_covered_floors_at_zero(self) -> None:
        # huge backlog over a long tenor easily covers EV -> share clamps to 0
        covered = _name(ev_usd_b=10.0, backlog_usd_b=500.0, backlog_tenor_years=10.0)
        assert renewal_dependent_share(covered, 0.10, 0.35) == 0.0


class TestInvertName:
    def test_band_structure(self) -> None:
        out = invert_name(_name())
        for key in ("implied_revenue_multiple", "renewal_dependent_share"):
            band = out[key]
            assert band["low"] <= band["median"] <= band["high"]

    def test_backlog_cover_ratio(self) -> None:
        # backlog 40 / 4yr = 10/yr; current rev 10 -> 1.0x
        out = invert_name(
            _name(
                backlog_usd_b=40.0, backlog_tenor_years=4.0, current_annualized_revenue_usd_b=10.0
            )
        )
        assert out["annual_backlog_vs_current_revenue_x"] == 1.0

    def test_zero_revenue_multiple_is_infinite_not_crash(self) -> None:
        out = invert_name(_name(current_annualized_revenue_usd_b=0.0))
        assert out["implied_revenue_multiple"]["low"] == float("inf")
        assert out["annual_backlog_vs_current_revenue_x"] is None


class TestCardedNames:
    def test_all_four_present(self) -> None:
        tickers = {n.ticker for n in NAMES}
        assert tickers == {"CRWV", "NBIS", "IREN", "APLD"}

    def test_inversion_runs_on_carded_inputs(self) -> None:
        results = invert_all(NAMES)
        assert len(results) == 4
        for r in results:
            # every carded name's renewal-dependent share is a real number in [0,1]
            med = r["renewal_dependent_share"]["median"]
            assert 0.0 <= med <= 1.0 and not math.isinf(med)
            # and the implied multiple band is finite (all four have positive current revenue)
            assert not math.isinf(r["implied_revenue_multiple"]["low"])

    def test_every_carded_name_is_majority_renewal_dependent(self) -> None:
        # The thesis-level finding: across all four, the median renewal-dependent share of EV
        # exceeds 50% -- the price rests mostly on re-contracting, not the signed backlog.
        # (Note: under EQUAL margins the long-tenor landlord APLD is NOT mechanically lower than
        # the GPU clouds -- a long tenor spreads rent thin per year and discounts it more; the
        # honest caveat about a landlord's higher true margin is carded in the doc, not asserted
        # here.)
        for r in invert_all(NAMES):
            assert r["renewal_dependent_share"]["median"] > 0.50


class TestContractedPv:
    def test_longer_tenor_covers_more_at_equal_annual_backlog(self) -> None:
        # same $/yr backlog over a longer tenor yields a larger PV (more EV covered)
        short = _name(backlog_usd_b=40.0, backlog_tenor_years=4.0)
        long = _name(backlog_usd_b=120.0, backlog_tenor_years=12.0)  # both $10B/yr
        assert contracted_pv(long, 0.10, 0.25) > contracted_pv(short, 0.10, 0.25)
