"""Verdict decomposition tree (WS1.3) — shadow mode until [TED] promotes it.

The published core verdict is a flat `bubble_dynamics_present @ 0.67`. That number is a
*structural-confidence* measurement (filings-derived; not killable by price — see the scope
guard in analysis/preregistered_signals.md). It is NOT a forecast that resolves on a date, so
it is not Brier-scoreable as written. Conflating a structural confidence with a realization
forecast was a latent imprecision; this module fixes it by giving the **forecastable**
quantity its own decomposed, signal-wired estimate. The 2026-Q4 TIMING-KILL adjudication
tests a separate registered criterion; P_real resolves on a qualifying issuer event through
2027-Q3 or, if no event occurs, after that window closes with complete event coverage.

The quantity decomposed here:
    P_real = P(a realized cluster financial-distress event within the crack window
              2025-Q3..2027-Q3) — covenant breach / going-concern / distressed exchange /
              failed refinancing at a core cluster issuer.

CRITICAL factorization requirement (raised on review): the tree must represent the fiber-1999
sequence where the funding **window closes first and causes** the distress, not only the
distress→window ordering. It does so with TWO pathways combined by noisy-OR, so window-first
is a first-class route, not an afterthought:

    Pathway A (operations-first): op-distress → window closes on the stressed name → event
    Pathway B (funding-first):    window closes (redemptions / marginal-buyer strike) → event
    P_real = 1 - (1 - P_A)(1 - P_B)

Each leaf is a STATED probability with a rationale, a base-rate prior citation, and the
pre-registered signals that move it. `apply_signals()` updates leaves mechanically from live
signal states, so the forecast changes because the evidence changed — not because the prose
was rewritten. Pure functions; shadow mode means nothing here overrides the gated 0.67.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

PROMOTED = False  # shadow mode: the gated report keeps the flat 0.67 until [TED] flips this
STRUCTURAL_CONFIDENCE = 0.67  # the engine's measurement; kept separate, NOT a forecast
P_REAL_WINDOW_START = date(2025, 7, 1)
P_REAL_WINDOW_END = date(2027, 9, 30)
TIMING_KILL_ADJUDICATION_QUARTER = "2026-Q4"

# How far one confirming/contra signal nudges a wired leaf (clamped to [0.02, 0.98]).
_SIGNAL_DELTA = 0.05


@dataclass
class Leaf:
    """One conditional probability in the decomposition."""

    key: str
    label: str
    base_p: float
    rationale: str
    prior: str  # base-rate citation (analysis/base_rates.json)
    # signal_id -> direction it pushes THIS leaf's probability when confirming
    signal_wiring: dict[str, str] = field(default_factory=dict)

    def adjusted_p(self, signal_status: dict[str, str]) -> float:
        p = self.base_p
        for sid, direction in self.signal_wiring.items():
            status = signal_status.get(sid)
            if status == "confirming":
                p += _SIGNAL_DELTA if direction == "up" else -_SIGNAL_DELTA
            elif status == "contra":
                p -= _SIGNAL_DELTA if direction == "up" else -_SIGNAL_DELTA
        return max(0.02, min(0.98, round(p, 4)))


# --- The leaves. base_p values are stated priors, base-rate-informed, deliberately not crisp. ---
LEAVES: dict[str, Leaf] = {
    "op_distress": Leaf(
        key="op_distress",
        label="operational distress (zero-shock coverage breach bites as cash) by 2027-Q3",
        base_p=0.70,
        rationale="7/11 issuers breach debt-service coverage at the zero-shock base; aggregate "
        "1.35x is a CoreWeave masking artifact (negative ex-CoreWeave). High prior the bleed is "
        "real; <1.0 because hyperscaler offtake + equity raises can fund the gap a while.",
        prior="failure-sequence stage 2 (most-levered fringe bleeds first); telecom/shale both",
        # S4 confirming = demand stalling -> raises op-distress; S4 contra (strong demand) lowers it
        signal_wiring={"S4_demand_trajectory": "up"},
    ),
    "window_closes_given_op": Leaf(
        key="window_closes_given_op",
        label="funding window closes on a stressed name | it is already operationally distressed",
        base_p=0.45,
        rationale="Today the window is wide open (S1 contra, 9.75% paper at par, 3x books), which "
        "is upside reflexivity actively refinancing the wall. But a name visibly bleeding cash is "
        "where access is withdrawn first; conditional on op-distress this is materially > base.",
        prior="capex-peak→default lag ~6-8 quarters; access withdrawn from the fringe first",
        signal_wiring={"S1_new_issue_spread": "up", "S1b_failed_print": "up"},
    ),
    "event_given_both": Leaf(
        key="event_given_both",
        label="distress event | operationally distressed AND window closed",
        base_p=0.80,
        rationale="If a name is bleeding and cannot refinance, a covenant/going-concern/exchange "
        "event is the near-mechanical result; <1.0 only for a backstop acquisition (the bull's "
        "strongest leg — Microsoft-cures-CoreWeave).",
        prior="incumbent-absorption stage 4 can pre-empt the event in a minority of cases",
        signal_wiring={},
    ),
    "window_closes_first": Leaf(
        key="window_closes_first",
        label="funding window closes FIRST (private-credit redemptions / marginal-buyer strike)",
        base_p=0.30,
        rationale="The fiber-1999 route: the window slams shut for contagion/redemption reasons "
        "and CAUSES the distress. Funding-chain proxies are already converging (BDC redemptions, "
        "CCC diverging from flat HY), but new issuance is still clearing — so a moderate, not "
        "high, prior on the window closing exogenously before operations force it.",
        prior="funding-structure break: private-credit marks/redemptions can move before spreads",
        signal_wiring={"S2_ccc_divergence": "up", "S3_bdc_discount_differential": "up"},
    ),
    "event_given_window_first": Leaf(
        key="event_given_window_first",
        label="distress event | the window closed first",
        base_p=0.75,
        rationale="A cluster that must continuously access the market to cover negative carry "
        "hits the wall fast once funding is withdrawn, even if operations were limping along.",
        prior="fiber CLECs: funding withdrawal converted thin operations into defaults quickly",
        signal_wiring={},
    ),
}


def _path_a(status: dict[str, str]) -> float:
    return (
        LEAVES["op_distress"].adjusted_p(status)
        * LEAVES["window_closes_given_op"].adjusted_p(status)
        * LEAVES["event_given_both"].adjusted_p(status)
    )


def _path_b(status: dict[str, str]) -> float:
    return LEAVES["window_closes_first"].adjusted_p(status) * LEAVES[
        "event_given_window_first"
    ].adjusted_p(status)


def realization_forecast(signal_status: dict[str, str] | None = None) -> dict[str, Any]:
    """The Brier-scoreable forecast P_real, decomposed, with both pathways and live leaf values.

    signal_status maps pre-registered signal ids -> 'confirming'|'contra'|'neutral' (from
    viz/live.json's `signals`). With none supplied, returns the base (registration-day) forecast.
    """
    status = signal_status or {}
    p_a = _path_a(status)
    p_b = _path_b(status)
    p_real = 1.0 - (1.0 - p_a) * (1.0 - p_b)
    return {
        "promoted": PROMOTED,
        "structural_confidence_unchanged": STRUCTURAL_CONFIDENCE,
        "p_real": round(p_real, 4),
        "p_real_outcome_window_end": P_REAL_WINDOW_END.isoformat(),
        "timing_kill_adjudication_quarter": TIMING_KILL_ADJUDICATION_QUARTER,
        "pathway_operations_first": round(p_a, 4),
        "pathway_funding_first": round(p_b, 4),
        "leaves": {
            k: {
                "label": lf.label,
                "p": lf.adjusted_p(status),
                "base_p": lf.base_p,
                "prior": lf.prior,
                "signals": list(lf.signal_wiring),
            }
            for k, lf in LEAVES.items()
        },
        "note": "Shadow mode: this forecast runs ALONGSIDE the gated 0.67 structural confidence "
        "and does not replace it until promoted. 2026-Q4 adjudicates TIMING-KILL, not p_real. "
        "The p_real outcome window runs through 2027-09-30; the flat 0.67 is a structural "
        "measurement, not a forecast.",
    }


def realization_outcome(
    *,
    as_of: date,
    filing_verified_qualifying_event_date: date | None = None,
    issuer_event_coverage_complete: bool = False,
) -> int | None:
    """Resolve P_real only from a verified issuer event or a complete closed-window audit.

    The caller must verify that the event is a qualifying core-issuer covenant breach,
    going-concern qualifier, distressed exchange, or failed refinancing in an issuer filing.
    A scheduled Q2 pressure peak, a signal state, or the Q4 TIMING-KILL adjudication is not
    such an event. Negative resolution requires coverage of all qualifying issuer events
    through September 30, 2027, even if TIMING-KILL was adjudicated in 2026-Q4.
    """
    event_date = filing_verified_qualifying_event_date
    if event_date is not None:
        if event_date > as_of:
            raise ValueError("qualifying event date cannot be after as_of")
        if P_REAL_WINDOW_START <= event_date <= P_REAL_WINDOW_END:
            return 1
    if as_of >= P_REAL_WINDOW_END and issuer_event_coverage_complete:
        return 0
    return None


def brier_score(forecasts: list[tuple[float, int | None]]) -> dict[str, Any]:
    """Brier score of resolved (probability, outcome) pairs (outcome in {0,1}).

    Returns the mean squared error and the count; an empty set scores None (nothing has
    resolved yet). Use realization_outcome() to gate P_real outcomes: 2026-Q4 TIMING-KILL
    alone does not resolve P_real. Lower is better; a forecast of 0.5 on every binary
    outcome scores 0.25 (the coin-flip benchmark).
    """
    resolved = [(p, o) for p, o in forecasts if o in (0, 1)]
    if not resolved:
        return {"brier": None, "n": 0, "note": "no resolved predictions yet"}
    sse = sum((p - o) ** 2 for p, o in resolved)
    return {
        "brier": round(sse / len(resolved), 4),
        "n": len(resolved),
        "coin_flip_benchmark": 0.25,
    }
