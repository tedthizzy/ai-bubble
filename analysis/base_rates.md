# Base-rate book — outside-view priors

> **⚓ Frame — read first (reanchor):** this repo is a **general forensic engine for financial fragility & mispricing across the _whole economy_** — hidden / mismatched / circular leverage and valuation-run-ahead-of-cash-flow, found with **no sector prior**. **AI / data-center is _case zero_, not the object** (the method is sector- and era-agnostic — cf. fiber 1999, shale 2014). **Operating mode: maximum exhaustiveness — broad AND deep, uncapped, ≥ $1M-substance floor, US-primary (international by connectedness-to-core × data-accessibility); acting resource-constrained is NEVER correct; the only stop is physics (data that doesn't publicly exist → estimate it from proxies).** Full scope & doctrine: [total_ecosystem_dive.md](total_ecosystem_dive.md) · [README](../README.md).


**Compiled 2026-06-12.** The engine measures *this* episode bottom-up. This document supplies the **outside view**: base rates from the two closest prior episodes of debt-financed infrastructure overbuild, to discipline the verdict tree's priors and the crack-window timing so the conclusion is anchored to history, not just to its own internal model. Machine-readable form: [base_rates.json](base_rates.json). Every figure carries a tier; disputed numbers are flagged. **Analogies bound a prior — they do not determine the verdict; the documented breaks matter as much as the rhymes.**

## Numbers

| episode | capex peak | first major default | peak default year | capex→default lag | trough recovery | overbuild / demand stat |
|---|---|---|---|---|---|---|
| **Telecom / fiber / CLEC** | ~2000 | NorthPoint Jan 2001; Winstar Apr 2001 | **2002** (WorldCom) | **~8 quarters** | **~23%** blended; WorldCom ~20¢ | **~2.7% of fiber lit** in 2002; built for ~7–10× realized demand |
| **US shale E&P** | 2014-H2 (oil peak Jun 2014) | Sabine Jul 2015 | **2016** (70 filings, ~$56.8B) | **~7 quarters** | **~21%** blended; senior unsecured ~6¢ | exogenous OPEC price trigger |

*Tiers: Moody's default/recovery studies [agency]; Odlyzko internet-traffic [academic]; Haynes & Boone Oil Patch monitor [agency-tracker]; WSJ "lit fiber" and asset-recovery anecdotes [estimate/financial-press]. Primary URLs in the JSON.*

## The transferable pattern (the most useful part)

A consistent four-stage ordering appears in both episodes, and it is what transfers most cleanly:

1. **Equity rolls over first** — months to ~2 years *before* realized credit losses peak. (Telecom equities topped early 2000; the default peak was 2002.)
2. **The most-levered, no-/negative-cash-flow fringe defaults first** — CLECs in 2001; high-cost over-levered independents in 2015.
3. **Merchant/overbuild players and any fraud-inflated big-caps follow** — Global Crossing / Williams / WorldCom in 2002; the bulk of E&P notional in 2016.
4. **Well-capitalized incumbents survive and absorb** — the RBOCs survived intact; oil majors absorbed assets (mostly a cycle later).

**Headline lags to carry into the prior:** spend-peak → default-wave-peak ≈ **6–8 quarters**; equity-peak → default-wave-peak ≈ **8–11 quarters**. Both analogs land in the same band despite very different assets — which is exactly why it is worth treating as a base rate rather than a coincidence.

Mapped onto today: an AI-compute capex peak in ~2025–2026 would, on the telecom/shale lag alone, put a default-wave peak around **2027–2028** — *later* than the engine's operational-bleed crack window (2025-Q3..2027-Q3) but well *before* the 2030–33 maturity wall. The two-clock structure survives the outside view; if anything the base rate says the bleed-to-default transmission is a multi-quarter process, not an event.

## Where the analogies break (so the prior isn't over-fit)

- **Asset life is the decisive break.** Fiber had a ~20–25-year life and near-zero marginal cost once lit, so the overbuild *waited underground* and the next cycle's demand absorbed it — dark fiber bought for cents later powered the cloud era. **GPUs have ~2–3-year economic life and high power/opex.** AI overbuild depreciates into obsolescence rather than waiting profitably. So the severity prior on **physical-asset recovery should be worse-tailed than telecom**, even where the *timing* lag transfers cleanly. There is no 20-year option value in a stranded H100. This is also why the WS1.1 renewal-dependent-share finding is so pointed: the market is pricing re-lease economics on collateral that may not live to be re-leased.
- **Who holds the debt changed.** Telecom losses sat in public HY bonds and bank/vendor financing — price-transparent, fast to mark, default fireworks visible. Today's buildout leans on private credit, BDCs, insurance/annuity balance sheets, SPV/lease structures, and hyperscaler self-funding — **less price-transparent, slower to mark.** This could *lengthen* the realized lag and *dampen* the visible default wave relative to telecom, which is consistent with the engine's funding-chain-first read (BDC discounts and redemptions moving before any new-issue spread gaps).
- **Demand is real this time.** Telecom's "doubling every 100 days" was a fabricated curve (a 1997 best-case spreadsheet propagated as fact); actual traffic roughly doubled *annually*. AI demand is real and growing fast — the open question is **price/margin and financing-chain circularity, not whether the traffic exists.** The break is in *kind*: phantom demand then vs real demand at possibly-unrecoverable unit economics now. (This is also why S4 — the demand-trajectory signal — registered *contra*: the demand leg is, so far, delivering.)
- **Shale's trigger was exogenous; an AI bust would be endogenous.** Shale broke on an OPEC-driven price collapse — a clean external timer. An AI bust would come from demand/margin/financing disappointment with **no external trigger to time against**, which argues for signal-based adjudication (the pre-registered approach) over calendar prediction.
- **Incumbent absorption rhymes — and it's the strongest transferable pattern.** Hyperscalers with deep balance sheets (MSFT, GOOG, AMZN, META, NVDA) as the "incumbents" who survive and absorb the levered neocloud fringe matches stage 4 of both episodes. It is also the bull case's strongest leg (a Microsoft backstop of CoreWeave is the historical norm, not the exception) — which is why the steelman ([bull_case.md](bull_case.md)) leads with it.

## How this feeds the verdict

The verdict tree ([../src/bubble/verdict_tree.py](../src/bubble/verdict_tree.py)) takes these as **prior** inputs, not facts about the present: the ~6–8-quarter lag informs P(window closes | distress) timing; the worse-than-telecom asset-recovery break informs the severity branch; the funding-structure break informs why transmission may run through marks and redemptions before public-spread events. The breaks are encoded alongside the rates so the tree cannot quietly treat an analogy as a measurement.

## Follow-ups before treating any single figure as load-bearing

1. Pull the primary PDFs (Moody's 2016 E&P recovery Special Comment; the Haynes & Boone monitor) to lock the 21%/6¢ and 70-filing/$56.8B figures to source rather than press relay.
2. The single most important caveat: telecom's long, durable-asset recovery is *why the bubble didn't permanently destroy the capital* — fiber waited twenty years and won. The GPU depreciation clock removes exactly that escape hatch, so the severity prior should be worse-tailed than telecom on asset recovery even though the timing lag transfers.
