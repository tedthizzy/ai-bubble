# Pre-registered thesis signals — confirm/kill criteria

**Registered: 2026-06-12.** These are the dated, observable conditions under which the market-facing thesis (see [expectations_vs_measured.md](expectations_vs_measured.md)) is **confirmed** or **killed** — including the conditions under which *our own timing is wrong*. Registration discipline: thresholds are set *before* outcomes are known and may not be silently edited. Amendments are append-only in the log at the bottom, with reasons.

**Scope guard:** these signals govern the *market-facing thesis* (mispricing + timing). The engine's adjudicated balance-sheet measurements (coverage breaches, duration mismatch, maturity wall, who-holds) are filings-derived facts and are not killable by price action — only by corrected filings or corrected extraction.

## Semantics

- **confirming** — evidence the marginal buyer of cluster credit is cracking (the thesis's required transmission).
- **contra** — evidence the funding window is open (the timing-kill direction).
- **neutral** — between thresholds.

Quantitative components (S1–S3) are auto-evaluated **hourly** by `scripts/refresh_live_overlay.py` into `viz/live.json` (`signals`) and surfaced on the explorer's **credit** chip and the banner's credit dial. Compound criteria (below) are adjudicated by a human against those components — the script measures, it does not declare victory.

## Auto-evaluated components

| id | measure | confirming at | contra at | threshold derivation (registered values) |
|---|---|---|---|---|
| **S1_new_issue_spread** | latest hand-carded cluster new-issue print ([issuance_cards.json](issuance_cards.json)), coupon vs 5y UST (FRED DGS5) | ≥ **800bp** | ≤ **600bp** | At registration the cluster cleared ~330bp (SPV, Jun-2) to ~575bp (corporate 9.75% '31): ≤600bp means the window is demonstrably open at today's levels. ICE's distress convention is ~1000bp OAS; 800bp is the pre-distress band between today's prints and distress. |
| **S2_ccc_divergence** | ICE BofA CCC & Lower OAS (FRED BAMLH0A3HYC), YTD change, vs flat broad HY | ≥ **+1.5pp** YTD | ≤ **0pp** YTD | At registration CCC was +0.71pp YTD while broad HY was −0.05pp: +1.5pp ≈ 2x the observed divergence — unambiguous tail repricing rather than noise. Back to ≤0 = the divergence was noise. |
| **S3_bdc_discounts** | worst top-4 listed-BDC discount to last *reported* quarterly NAV (OBDC, ARCC, BXSL, FSK) | worst ≥ **30%** | all < **10%** | At registration: FSK −41.3%, OBDC −22.4%, BXSL −9.2%, ARCC −1.7% (NAVs as of 2026-03-31). 30% exceeded the worst pre-registration cycle level we observed when thresholds were drafted (~23%, before the FSK Q1 mark); normal-times BDC discounts run 0–10%. **Note:** S3 fired *confirming on registration day* via FSK — recorded as a registration-day fact, not a prediction. |

## Compound criteria (human-adjudicated, dated)

- **TIMING-KILL** — *our crack-window timing is wrong*: through **2026-Q4**, every new cluster 5yr+ print clears ≤600bp with >2x books (S1 stays contra, oversubscription from press carding) **and** all top-4 BDC discounts close under 10% (S3 contra). Consequence: the 2025-Q3..2027-Q3 crack window is killed; the balance-sheet claims stand; the wall analysis shifts weight to 2030–33.
- **MARGINAL-BUYER-KILL** — *the funding-chain stress read is wrong*: private-credit redemption pressure abates in trade-press coverage for two consecutive quarters and S2 returns ≤0 while issuance volume continues. Consequence: layer-3 of the pricing map is withdrawn.
- **CONFIRM-1 (window cracking)** — any cluster deal pulled/postponed, or a print ≥800bp (S1 confirming), while maturities or DDTL drawdowns are pending.
- **CONFIRM-2 (transmission)** — S2 ≥ +1.5pp **and** S3 worst ≥30% simultaneously with a widening vs broad HY: fund-flow stress reaching price-of-risk for the tail.
- **CONFIRM-3 (issuer event)** — any cluster issuer discloses a going-concern qualifier, covenant waiver request, or distressed exchange. (Filing-tier; would also feed the adjudicated engine.)

## Calendar of forced truth (manual carding)

| date | event | why it forces truth |
|---|---|---|
| each 10-Q/K season | issuer depreciation-schedule changes; utilization/coverage disclosures | book life vs ~2–3yr economic life is the contested number |
| quarterly, ~May/Aug/Nov/Feb | re-card BDC NAVs from Q results into `scripts/refresh_live_overlay.py` (`BDC_NAV`) | keeps S3 honest — close vs *reported* NAV, never estimated |
| every cluster print | append to [issuance_cards.json](issuance_cards.json) (date, coupon, tenor, size, books if reported) | keeps S1 honest and builds the spread time series |
| 2026-Q4 | TIMING-KILL adjudication date | pre-committed above |
| 2027–2028 | anchor-contract renewal/extension checkpoints | backlog quality becomes observable |
| 2029–2033 | carded maturity wall ($36.6B of $41.7B carded, 88%, in 2030–33) | refinancing vs collateral age — the terminal test |
| Oct-2030 | CoreWeave–OpenAI commitment expiry | the contract servicing the wall is itself up for renewal |

## Amendment log

- 2026-06-12 — initial registration (thresholds above; S3 noted as confirming-on-registration via FSK).
