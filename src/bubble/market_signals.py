"""Pre-registered market-signal evaluation -- the auto-evaluable thesis components.

Pure functions, no I/O: scripts/refresh_live_overlay.py feeds them fetched data hourly
and writes the results into viz/live.json. Thresholds and set memberships below are
REGISTERED values -- they may only change via the append-only amendment log in
analysis/preregistered_signals.md, never silently here.

Semantics (registered 2026-06-12, respecified via amendments 2026-06-12):
- confirming -- evidence the marginal buyer of cluster credit is cracking.
- contra     -- evidence the funding window is open (the timing-kill direction).
- neutral    -- between thresholds.
- stale / insufficient_data / insufficient_history -- the honest non-answers; an
  unmeasurable signal never defaults to a directional status.
"""

from __future__ import annotations

from datetime import date
from typing import Any

# --- S1: latest cluster new-issue print, spread vs 5y UST (registered 2026-06-12) ---
SPREAD_OPEN_BP = 600  # cluster prints cleared ~350-575bp at registration: window open at/below
SPREAD_CRACK_BP = 800  # pre-distress warning band (ICE distress convention ~1000bp OAS)
# Amendment A4 (2026-06-12): absence of issuance is ambiguous (window shut OR no need) --
# a print older than this reports `stale`, never `contra`. 45d > the longest gap between
# carded prints at respec time (38d, 2026-04-21 -> 2026-06-02).
STALE_DAYS = 45

# --- S2': CCC-vs-HY differential, BB control (amendment A2, 2026-06-12) ---
# Confirmation requires the TAIL to diverge from the index, not the index to move:
# measure = (CCC OAS - HY OAS) change YTD. At respec: CCC +0.68pp YTD, HY -0.05pp,
# differential +0.73pp; threshold ~2x observed = unambiguous repricing vs noise
# (same derivation logic as the original S2 registration).
DIFF_WIDEN_PP = 1.5
# BB OAS (BAMLH0A1HYBB) is the quality-end control: if BB has also widened materially
# YTD, the move is market-wide risk-off, not tail-specific -- flagged, adjudicator
# weighs it. BB sat at 1.69% (-0.02 YTD, dead flat) at respec; +1.0pp on that base
# would be a major broad-HY event.
BB_MARKET_WIDE_PP = 1.0

# --- S3': AI-exposed BDC discount differential vs non-AI control (amendment A1) ---
# The original S3 (worst absolute discount >= 30%) was confounded: FSK's -41% is
# dominated by legacy-book credit, a class action, and a years-long pre-AI discount.
# S3' = (worst exposed-set discount to reported NAV) - (control-set median discount).
# Set membership is carded evidence (analysis/bdc_exposure_cards.md), not assumption:
# only BXSL (Firmus GPU-cloud commitment; firm-wide GPU platform) and weakly ARCC
# (~0.2% Vantage DC position) show asset-side AI/DC exposure; FSK and OBDC are
# excluded from BOTH sets (minimal fund-level exposure + idiosyncratic drivers).
# Controls use the MEDIAN so the two regime outliers that bracket the sector --
# MAIN (persistent premium) and PSEC (idiosyncratic deep discount) -- cannot move it.
BDC_EXPOSED: frozenset[str] = frozenset({"BXSL", "ARCC"})
BDC_CONTROL: frozenset[str] = frozenset({"MAIN", "GBDC", "TSLX", "PSEC"})
# Normal-times BDC discounts run 0-10% sector-wide and cross-sectional dispersion of
# ~5pp is routine on idiosyncratic factors. A worst-exposed name >= 15pp wider than the
# contemporaneous non-AI median (~1.5x the entire normal-times band) is attribution-
# specific stress; <= 5pp is inside ordinary dispersion (exposed indistinguishable
# from generic BDC-sector pricing).
BDC_DIFF_STRESS_PP = 15.0
BDC_DIFF_CALM_PP = 5.0

# --- S4: AI end-demand trajectory vs the bull's required path (amendment A5) ---
# The capex-implied revenue requirement (~$500B/yr on book depreciation lives by
# ~2028-29, vs ~$100-150B/yr observable at mid-2026) needs ~70-100%/yr compounded
# growth. Below 50%/yr the demand leg cannot close even the generous (book-life)
# equation on schedule; >= 100%/yr is the bull path intact.
S4_STALL_YOY_PCT = 50.0
S4_ONPATH_YOY_PCT = 100.0
# A YoY comparison needs a basket roughly a year older; accept 270-455 days so
# quarterly carding cadence can't silently break the comparison.
S4_MIN_SPAN_DAYS = 270
S4_MAX_SPAN_DAYS = 455

Signal = dict[str, Any]


def eval_s1(latest_deal: Signal | None, today: date) -> Signal | None:
    """S1: spread of the latest hand-carded cluster print vs 5y UST, with staleness guard."""
    if latest_deal is None:
        return None
    spread = latest_deal.get("spread_vs_5y_bp")
    if spread is None:
        return None
    deal_date = latest_deal.get("date", "")
    try:
        age_days = (today - date.fromisoformat(deal_date)).days
    except ValueError:
        age_days = None
    if age_days is not None and age_days > STALE_DAYS:
        status = "stale"
    elif spread >= SPREAD_CRACK_BP:
        status = "confirming"
    elif spread <= SPREAD_OPEN_BP:
        status = "contra"
    else:
        status = "neutral"
    return {
        "id": "S1_new_issue_spread",
        "status": status,
        "value_bp": spread,
        "print_age_days": age_days,
        "desc": (
            f"latest carded cluster print ({latest_deal.get('issuer', '?')} "
            f"{deal_date or '?'}) ~{spread}bp over 5y UST; "
            f"<={SPREAD_OPEN_BP}bp = window open (contra), "
            f">={SPREAD_CRACK_BP}bp = cracking (confirming); "
            f">{STALE_DAYS}d old = stale, never contra"
        ),
    }


def eval_s1b(deals: list[Signal]) -> Signal | None:
    """S1b: discrete failed-print event -- windows gap shut rather than taper.

    Any carded cluster print with status postponed/pulled/failed is confirming,
    independent of spread drift. Missing status is treated as priced (the field
    was added by amendment A3; all pre-amendment cards were completed prints).
    """
    if not deals:
        return None
    failed = [d for d in deals if d.get("status", "priced") != "priced"]
    status = "confirming" if failed else "neutral"
    worst = max(failed, key=lambda d: d.get("date", "")) if failed else None
    return {
        "id": "S1b_failed_print",
        "status": status,
        "event": (
            {
                "issuer": worst.get("issuer"),
                "date": worst.get("date"),
                "status": worst.get("status"),
            }
            if worst
            else None
        ),
        "desc": (
            "any carded cluster print postponed/pulled/failed = confirming event "
            "(issuance windows historically gap shut rather than taper); "
            "all prints priced = neutral"
        ),
    }


def eval_s2(credit: Signal) -> Signal | None:
    """S2': (CCC - HY) YTD differential widening, with BB OAS as quality-end control."""
    ccc = credit.get("ccc_oas") or {}
    hy = credit.get("hy_oas") or {}
    if ccc.get("ytd_chg") is None or hy.get("ytd_chg") is None:
        return None
    diff_ytd = round(ccc["ytd_chg"] - hy["ytd_chg"], 2)
    if diff_ytd >= DIFF_WIDEN_PP:
        status = "confirming"
    elif diff_ytd <= 0:
        status = "contra"
    else:
        status = "neutral"
    bb_ytd = (credit.get("bb_oas") or {}).get("ytd_chg")
    market_wide = bb_ytd is not None and bb_ytd >= BB_MARKET_WIDE_PP
    return {
        "id": "S2_ccc_divergence",
        "status": status,
        "ccc_minus_hy_ytd_pp": diff_ytd,
        "ccc_oas": ccc.get("value"),
        "bb_ytd_chg_pp": bb_ytd,
        "market_wide_flag": market_wide,
        "desc": (
            f"(CCC-HY) OAS differential {diff_ytd:+.2f}pp YTD; "
            f">={DIFF_WIDEN_PP}pp = tail-specific repricing (confirming), <=0pp = contra"
            + (
                f"; BB control also wide ({bb_ytd:+.2f}pp YTD) -- move may be "
                "market-wide, adjudicate before treating as tail-specific"
                if market_wide
                else ""
            )
        ),
    }


def eval_s3(bdc: dict[str, Signal]) -> Signal | None:
    """S3': worst AI-exposed BDC discount minus non-AI control median discount."""
    exposed = {s: v for s, v in bdc.items() if s in BDC_EXPOSED and "discount_pct" in v}
    control = sorted(
        v["discount_pct"] for s, v in bdc.items() if s in BDC_CONTROL and "discount_pct" in v
    )
    if not exposed:
        return None
    worst_sym, worst = max(exposed.items(), key=lambda kv: kv[1]["discount_pct"])
    worst_disc = worst["discount_pct"]
    if len(control) < 2:
        # fewer than two control marks -> the differential is not measurable; report
        # the absolute level for context but never a directional status from it.
        return {
            "id": "S3_bdc_discount_differential",
            "status": "insufficient_data",
            "worst": worst_sym,
            "worst_discount_pct": worst_disc,
            "desc": "control basket unquoted -- differential not measurable this run",
        }
    mid = len(control) // 2
    ctl_median = round(
        control[mid] if len(control) % 2 else (control[mid - 1] + control[mid]) / 2.0, 1
    )
    diff = round(worst_disc - ctl_median, 1)
    if diff >= BDC_DIFF_STRESS_PP:
        status = "confirming"
    elif diff <= BDC_DIFF_CALM_PP:
        status = "contra"
    else:
        status = "neutral"
    return {
        "id": "S3_bdc_discount_differential",
        "status": status,
        "worst": worst_sym,
        "worst_discount_pct": worst_disc,
        "control_median_pct": ctl_median,
        "differential_pp": diff,
        "desc": (
            f"worst AI-exposed BDC discount ({worst_sym} {worst_disc:.1f}%) minus "
            f"non-AI control median ({ctl_median:.1f}%) = {diff:+.1f}pp; "
            f">={BDC_DIFF_STRESS_PP:.0f}pp = exposure-specific stress (confirming), "
            f"<={BDC_DIFF_CALM_PP:.0f}pp = inside normal sector dispersion (contra)"
        ),
    }


def eval_s4(baskets: list[Signal]) -> Signal | None:
    """S4: trailing YoY growth of the carded AI end-demand basket vs the required path."""
    dated: list[tuple[date, Signal]] = []
    for b in baskets:
        try:
            dated.append((date.fromisoformat(b["as_of"]), b))
        except (KeyError, ValueError):
            continue
    dated.sort(key=lambda t: t[0])
    if not dated:
        return None
    latest_date, latest = dated[-1]
    base: tuple[date, Signal] | None = None
    for d, b in dated[:-1]:
        span = (latest_date - d).days
        if S4_MIN_SPAN_DAYS <= span <= S4_MAX_SPAN_DAYS:
            base = (d, b)  # keep the latest qualifying base
    common = {
        "id": "S4_demand_trajectory",
        "latest_total_usd_b": latest.get("total_usd_b"),
        "latest_as_of": latest.get("as_of"),
    }
    if base is None or not latest.get("total_usd_b") or not base[1].get("total_usd_b"):
        return {
            **common,
            "status": "insufficient_history",
            "desc": (
                "no carded basket ~1yr earlier to compute YoY growth -- "
                "S4 reports the level only until the series is long enough"
            ),
        }
    yoy = round((latest["total_usd_b"] / base[1]["total_usd_b"] - 1.0) * 100.0, 1)
    if yoy < S4_STALL_YOY_PCT:
        status = "confirming"
    elif yoy >= S4_ONPATH_YOY_PCT:
        status = "contra"
    else:
        status = "neutral"
    return {
        **common,
        "status": status,
        "yoy_growth_pct": yoy,
        "base_as_of": base[1].get("as_of"),
        "desc": (
            f"carded AI end-demand basket {yoy:+.1f}% YoY "
            f"(${base[1]['total_usd_b']:.0f}B -> ${latest['total_usd_b']:.0f}B); "
            f"<{S4_STALL_YOY_PCT:.0f}%/yr = demand leg cannot close the capex equation "
            f"(confirming), >={S4_ONPATH_YOY_PCT:.0f}%/yr = bull path intact (contra)"
        ),
    }


def evaluate_signals(
    credit: Signal,
    bdc: dict[str, Signal],
    deals: list[Signal],
    latest_deal: Signal | None,
    demand_baskets: list[Signal],
    today: date,
) -> list[Signal]:
    """All auto-evaluable signal components, in registration order; None results dropped.

    These evaluate COMPONENTS only -- the compound confirm/kill criteria (with dates)
    are defined in analysis/preregistered_signals.md and adjudicated by a human.
    """
    results = [
        eval_s1(latest_deal, today),
        eval_s1b(deals),
        eval_s2(credit),
        eval_s3(bdc),
        eval_s4(demand_baskets),
    ]
    return [r for r in results if r is not None]
