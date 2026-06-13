# Marginal-buyer constraint cards

> **⚓ Frame — read first (reanchor):** this repo is a **general forensic engine for financial fragility & mispricing across the _whole economy_** — hidden / mismatched / circular leverage and valuation-run-ahead-of-cash-flow, found with **no sector prior**. **AI / data-center is _case zero_, not the object** (the method is sector- and era-agnostic — cf. fiber 1999, shale 2014). **Operating mode: maximum exhaustiveness — broad AND deep, uncapped, ≥ $1M-substance floor, US-primary (international by connectedness-to-core × data-accessibility); acting resource-constrained is NEVER correct; the only stop is physics (data that doesn't publicly exist → estimate it from proxies).** Full scope & doctrine: [total_ecosystem_dive.md](total_ecosystem_dive.md) · [README](../README.md).


**Compiled 2026-06-12.** The engine maps *who holds the risk*; this maps *what binds them* — the regulatory and structural rules that turn the funding chain into a **timing mechanism**. It answers the question the verdict tree's funding-first pathway needs: when the marginal buyer of AI-DC credit is forced to sell or strikes, which constraint fires first, and how fast? Machine-readable: [marginal_buyer_constraints.json](marginal_buyer_constraints.json). Tiers: `[statute]` `[agency]` `[press]` `[estimate]`. (sec.gov not fetched; some figures via secondary sources, flagged below.)

## The chain

AI-DC SPV / neocloud debt → private-credit originators (Blackstone, Blue Owl, Apollo, PIMCO, BlackRock, Ares) → securitized into rated notes / ABS / CLO tranches → held by **life-insurer general accounts** (funded by ~$2.5T of annuities), **BDCs** (~$407B of private-credit investments), and **semi-liquid funds** — with affiliated-structure leverage up to ~12:1 and ~$95B of committed bank lines. Private credit to AI went from ~$0 to **>$200B (~8% of all private credit)**; Morgan Stanley estimates private credit could supply **over half of the ~$1.5T** of data-center financing through 2028. `[agency: BIS Bulletin 120; press: FT]`

## The headline finding

**The fastest-acting constraint is already binding — in 2026.** Of the four, only the semi-liquid-fund redemption gate has actually been tripped this cycle, and it has been tripped repeatedly on AI-credit-exposed vehicles, explicitly amid "AI fears." This is direct, dated corroboration of the funding-chain-first read in [expectations_vs_measured.md](expectations_vs_measured.md) and the reason the verdict tree's **pathway B (window-closes-first) is live, not theoretical**.

## Card 1 — Insurer RBC (slowest, biggest balance sheet, highest severity)

| | |
|---|---|
| **Binding constraint** | NAIC C-1 RBC charge steps up **nonlinearly** as a bond's designation worsens `[statute]` |
| **Trigger schedule** | Aaa (1.A) 0.16% → Baa3/IG-floor (2.C) 2.17% → BB (3) 3.15–6.02% → B (4) 7.39–12.43% → Caa (5) 16.94–30% → (6) 30%. **IG→junk roughly doubles the charge; 2→5 is ~13–15×.** CLO residual/equity carries a flat **45%** (YE-2024). A proposed thickness rule would cliff a Baa3 CLO tranche **2.73% → 12.52%** if ≤4% of capital (not adopted Spring 2026; ~end-2027). |
| **Mechanical consequence** | **No automatic forced sale.** SSAP 26R lets an AVR insurer hold a downgraded bond at amortized cost up to NAIC 5 (mark only at 6); RBC is a year-end measure. So the first insurer move is a **buyers' strike** (stop buying new AI-DC paper), not selling — until a downgrade hits the nonlinear cliff. |
| **Speed / role** | Slowest fuse, but the largest balance sheet and the most dangerous channel if the cliff is hit. ~35% of NA insurer portfolios are now private credit; PE-backed insurers hold ~2× the illiquid assets of peers. |

## Card 2 — BDC leverage (second; where a mark becomes a forced sale)

| | |
|---|---|
| **Binding constraint** | 150% asset-coverage minimum = **2:1 debt:equity** (ICA §61(a)/§18, 2018 SBCAA) — but **bank facilities and borrowing bases bind far earlier** `[statute]` |
| **Trigger levels** | NAV decline to breach the statutory floor: ~25% (from 1.0× leverage), ~18% (1.2×), ~12.5% (1.4×) `[estimate, §18 formula]`. The real edge: borrowing-base advance-rate haircuts where **5–10% mark declines already force paydowns** `[press, agency]`. Current posture: 8 rated non-traded BDCs avg **0.85×** leverage (severe-stress 1.39×), so the *statutory* cap is not close — the *covenant* edge is. |
| **Mechanical consequence** | Below the floor: no new debt, restricted distributions, must delever or raise equity, RIC-status risk. The continuous ≥150% bank covenant + advance-rate haircuts is where a redemption wave (Card 4) plus AI-collateral marks converts into **actual forced delevering**. |
| **Speed / role** | Second to fire; the first place a mark-down becomes a forced sale. (This is also why S3' measures BDC discounts — though the listed-BDC caveat in [bdc_exposure_cards.md](bdc_exposure_cards.md) applies: the *private* BDCs hold the AI-DC paper.) |

## Card 3 — Annuity surrender / disintermediation (slowest, deepest tail)

| | |
|---|---|
| **Binding constraint** | Surrenderable liabilities can run faster than illiquid private credit can be sold `[agency: Fed FEDS Notes]` |
| **Trigger levels** | Surrender-charge periods 7–10yr (e.g. 7/6/5/4/3/2/1%); ~10%/yr penalty-free. **55% of life liabilities are withdrawable**; the liquid buffer is only **~6% of assets**. 2024 individual-annuity surrenders +16.3% to **$484.4B** (NAIC). |
| **Mechanical consequence** | A rate/confidence shock → surrender wave → the insurer must **sell long-duration / illiquid bonds at depressed value**. Surrender charges + market-value adjustments deliberately slow this. |
| **Speed / role** | Slowest to break (the surrender wall), but the deepest channel — it can force an insurer to dump illiquid private credit. Amplified by the Bermuda build-out: **>$1.1T of US life reserves now ceded offshore** (>2× since 2019), ~70% to affiliates. |

## Card 4 — Semi-liquid redemption gates (fastest, **already binding**)

| | |
|---|---|
| **Binding constraint** | Quarterly redemption gate (typically **5% of NAV/quarter**, ~20%/yr) with mandatory **proration** when exceeded; the unfilled remainder is **not** carried over `[statute: Rule 23c-3; press]` |
| **Gates actually hit in 2026** | **Apollo ADS Q1:** 11.2% requested → **~45% filled**. **Ares ASIF Q1:** 11.6% → **43.1% filled**. **Blue Owl OTIC Q1:** 40.7% requested vs 5% cap → ~12% prorated. **Blue Owl OCIC Q1:** 21.9% → ~23%. **BCRED Q2:** ~10% (2×cap) → **first-ever BCRED gate** (~50%, derived). Precedent: **BREIT** gated Dec-2022 → ~43%. |
| **Mechanical consequence** | Requests above the cap are prorated; holders re-tender next quarter, eroding confidence. The FSB (May 2026) found that meeting requests at the limit "**may also have stimulated further redemption pressures**" — gates **ration and signal** stress, they do not dissipate it. |
| **Speed / role** | Fastest, liability-side, retail-driven, no statutory lag — **the canary, and it is already chirping.** |

## Synthesis — the ordering, and the coupling that matters

1. **Redemption gates** (fastest, live now) — retail flight → proration → re-tender → confidence erosion; procyclical per the FSB.
2. **BDC bank-covenant / borrowing-base tightening** (second) — 5–10% marks force paydowns; where a mark-down becomes a forced sale.
3. **Insurer RBC cliff** (slower, biggest balance sheet, highest severity) — buyers' strike first, then the nonlinear cliff if AI-DC collateral is downgraded.
4. **Annuity surrenders** (slowest, deepest tail).

**The coupling is the real point.** The same managers — Apollo, Blackstone, Blue Owl, Ares — run the gated funds, the BDCs, *and* the insurers' affiliated asset management. So a stress that begins as retail redemptions and bank-line tightening lands on the **same balance sheets** that hold the rated-note AI-DC paper, at ~12:1 affiliated leverage. That coupling is exactly the transmission the verdict tree's funding-first pathway prices, and the 2026 gate data says the first link is already under load.

## Feeds

- **Verdict tree** ([verdict_tree.md](verdict_tree.md)): pathway B's `window_closes_first` prior (0.30) and `event_given_window_first` (0.75) rest on this map; the 2026 gate evidence is why the prior is moderate-and-rising rather than low.
- **Signals**: S3' (BDC discounts) and S2' (CCC divergence) are the auto-evaluated proxies for Cards 2 and 4; the gate events here are the manual-carding corroboration the compound MARGINAL-BUYER criteria adjudicate against.

## Flagged inferences (carded, not hidden)

- BCRED Q2 ~50% fill and the Blue Owl per-fund fill %s are arithmetic inferences (cap ÷ request), not printed rates.
- The BDC breach-% table is a derivation from the §18 formula (exact, but not printed together in one source).
- IMF / FSOC figures are via secondary sources (primary PDFs 403'd); re-check verbatim before any direct public quotation.
- NAIC-1 old base factor stated as ~0.40% pretax / 0.30% after-tax to avoid the pretax/after-tax confusion.
