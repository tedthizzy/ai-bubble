# Verdict decomposition tree — shadow mode

> **⚓ Frame — read first (reanchor):** this repo is a **general forensic engine for financial fragility & mispricing across the _whole economy_** — hidden / mismatched / circular leverage and valuation-run-ahead-of-cash-flow, found with **no sector prior**. **AI / data-center is _case zero_, not the object** (the method is sector- and era-agnostic — cf. fiber 1999, shale 2014). **Operating mode: maximum exhaustiveness — broad AND deep, uncapped, ≥ $1M-substance floor, US-primary (international by connectedness-to-core × data-accessibility); acting resource-constrained is NEVER correct; the only stop is physics (data that doesn't publicly exist → estimate it from proxies).** Full scope & doctrine: [total_ecosystem_dive.md](total_ecosystem_dive.md) · [README](../README.md).


**2026-06-12.** The published core verdict is a flat `bubble_dynamics_present @ 0.67`. That is a **structural-confidence measurement** — filings-derived, and by the [scope guard](preregistered_signals.md) not killable by price. It does not resolve on a date, so it is not Brier-scoreable as written. This module ([../src/bubble/verdict_tree.py](../src/bubble/verdict_tree.py)) gives the **forecastable** quantity its own decomposed, signal-wired estimate that the 2026-Q4 adjudication and later events will score. It runs in **shadow mode**: it does not replace the gated 0.67 until [TED] promotes it (`PROMOTED = False`).

Recognising that the flat 0.67 was being asked to play two roles — a structural confidence *and* an implied forecast — is itself the fix. The structural confidence stays put; the forecast gets decomposed.

## What it decomposes

**P_real = P(a realized cluster financial-distress event within the crack window 2025-Q3..2027-Q3)** — a covenant breach, going-concern qualifier, distressed exchange, or failed refinancing at a core cluster issuer.

## The factorization (and the window-closes-first requirement)

A review raised the decisive point: a factorization of the form *distress → window closes → event* **cannot represent the fiber-1999 sequence**, where the funding window slammed shut for contagion/redemption reasons and *that* caused the distress. So the tree uses **two pathways combined by noisy-OR**, making window-first a first-class route:

```
Pathway A (operations-first): op-distress → window closes on the stressed name → event
Pathway B (funding-first):    window closes (redemptions / marginal-buyer strike) → event
P_real = 1 − (1 − P_A)(1 − P_B)
```

| leaf | base p | wired signals | reading |
|---|---|---|---|
| op_distress by 2027-Q3 | 0.70 | S4 (demand) | 7/11 breach at zero shock; <1 because offtake/equity can fund the gap |
| window closes \| op-distress | 0.45 | S1, S1b | window is open *now* (S1 contra); higher conditional on visible bleed |
| event \| both | 0.80 | — | near-mechanical, minus a backstop-acquisition escape |
| **window closes FIRST** | 0.30 | S2, S3 | the fiber-1999 route; funding proxies converging but issuance still clears |
| event \| window-first | 0.75 | — | negative-carry names that must roll paper fail fast once cut off |

## Signal-wiring (mechanical, not rhetorical)

Each wired leaf moves ±0.05 per confirming/contra signal (clamped to [0.02, 0.98]); a confirming signal (marginal-buyer cracking) pushes its leaf toward the event, a contra signal away. So the forecast changes because the **evidence** changed, not because the prose was rewritten. Current readings:

- **Base (registration-day, no signal adjustment):** P_real ≈ **0.42** (pathway A 0.25, pathway B 0.23).
- **Live (S1 contra, S4 contra, S2/S3 neutral — window open, demand strong):** P_real ≈ **0.39**, leaning slightly against near-window realization. Published hourly in `viz/live.json` under `verdict_shadow`.
- **All-confirming (full transmission):** P_real ≈ **0.53**.

That P_real (~0.4) sits well below the structural 0.67 is the point, not a contradiction: "the dynamics are present" (0.67, measured) is a different claim from "a distress event realizes within the window" (~0.4, forecast). Decomposing forces that distinction into the open.

## Brier scoring

`brier_score()` scores resolved (probability, outcome) pairs; an empty set returns `None` — **nothing has resolved yet, and the first resolution is the 2026-Q4 adjudication.** A 0.5-on-everything forecaster scores 0.25 (the coin-flip benchmark the tree must beat to be worth promoting). The public scored record ([track-record page](../viz/track_record.html)) renders this ledger as it fills.

## Priors

Leaf priors are disciplined by the [base-rate book](base_rates.md): the ~6–8-quarter capex-peak→default lag, the failure-sequence ordering (fringe first, incumbents absorb), and the funding-structure break (private-credit marks/redemptions can move before public spreads — which is why pathway B is live, not theoretical). The priors are encoded next to the base-rate citations so the tree cannot quietly treat an analogy as a measurement.

## Promotion criteria (for [TED])

Promote out of shadow mode when: (1) the leaf priors have survived external adversarial review; (2) the first Brier resolution (Q4) is recorded; (3) the structural-vs-forecast distinction is reflected in the published report's language. Until then, the gated report shows 0.67 and this tree runs beside it.
