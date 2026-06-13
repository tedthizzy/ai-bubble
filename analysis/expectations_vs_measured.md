# What the market prices vs. what we measured

**Layer:** market-observables (press/market tier — NOT adjudicated evidence; nothing here changes the gated verdict of `bubble_dynamics_present` @ 0.67 core / 0.25 ecosystem).
**Registered:** 2026-06-12. Point-in-time levels below; the live components refresh hourly via `scripts/refresh_live_overlay.py` (the **credit** chip on the explorer, the credit dial on the banner).
**Not investment advice.** This is a research artifact about the gap between measured fundamentals and priced beliefs.

## Why this layer exists

The forensic engine measures reality: 7/11 cluster issuers breach debt-service coverage at zero shock (the aggregate 1.35x is a CoreWeave masking artifact — negative ex-CoreWeave), GPU economic life ~2–3yr vs 5–7yr debt, 88% of carded maturities stacked 2030–2033 on collateral that will be at/past economic life, and loss routing through private credit to insurance/annuity/pension balance sheets.

A truth claim is not a thesis. The thesis is the **gap** between what we measured and what the market's prices imply it believes. This document measures the second half.

## The three-layer pricing map (as of 2026-06-12)

| layer | observables | how much of the measured fragility is priced |
|---|---|---|
| **Cluster equity** | CRWV ~$98 vs $187 52-wk high (≈ −47%); short interest reported 9–16% of shares across 2026; elevated shorts across neoclouds (NBIS, IREN) | **Partially priced, and crowded.** The equity market has converged roughly halfway; being short here pays a squeeze tax (CRWV +5% on index-addition flows the same week). |
| **Cluster primary credit** | $2.75B CoreWeave 9.75% senior notes due **2031** sold at par (Apr 2026); $900M 5-yr CoreWeave-linked SPV paper at **7.5%** (Jun 2, 2026) ≈ **+330bp over 5y UST**; euro books 3x+ oversubscribed; A-rated data-center ABS ≈ +210bp and **compressing**; broad HY OAS 2.78% — near record tights | **Essentially unpriced.** These are single-B growth-credit levels priced off the $66B contracted backlog. The zero-shock coverage breaches, the 2030–33 collateral-decay wall, and who-ultimately-bears are not in these spreads. Note the second-order effect: every 9.75% refinance *deepens* the negative carry the spreads ignore — access ≠ health. |
| **Funding-chain proxies** | Top-4 listed BDC discounts to last reported NAV: **FSK −41%**, OBDC −22%, BXSL −9%, ARCC −2% (NAVs as of 2026-03-31 filings); "widespread redemption requests" across private credit since end-Dec-2025; semiliquid-fund gating episodes; CCC & lower OAS **+~70bp YTD** (8.85→9.56) while broad HY is *flat* | **Converging now.** The investors who fund the marginal buyer of cluster paper are marking the chain down and asking for money back. The dispersion (ARCC at par, FSK at −41%) shows the market discriminating book-by-book, not applying a sector haircut — stress is concentrating where the weakest assets sit. |

## The finding

**Primary deals are clearing at tight spreads from a buyer base whose own funding is being marked down 20–40% and hit with redemptions.** Layers 2 and 3 cannot both be right for long:

- If the **bull** resolves it: private-credit flows stabilize, BDC discounts close, the window stays open through the 2026–2027 coverage trough, and contracted backlog converts to cash before the 2030–33 wall. Our *timing* claim dies (the balance-sheet measurements stand — they are filings, not opinions).
- If the **measured fragility** resolves it: the private-credit bid for new cluster paper thins (redemptions force it), new-issue spreads gap, and the issuers that need continuous market access at any price to cover negative carry hit the wall early — inside the crack window (2025-Q3..2027-Q3).

One honest correction this layer forces on our own presentation: the crack window's engine peak (~2026-Q2) is **not confirmed at the issuer-credit layer** — the funding window is demonstrably open (S1 below is *contra*). The deterioration is one layer up, at fund flows. Upside reflexivity is live: the open window is actively refinancing the wall. Whether it stays open is exactly what the pre-registered signals track.

## Correction (2026-06-12, registration day — attribution at layer 3)

Carding each listed BDC's actual book ([bdc_exposure_cards.md](bdc_exposure_cards.md)) corrects the layer-3 row above, and the correction **weakens the layer-3 evidence as written**:

- **FSK's −41% is not AI attribution.** Its discount is dominated by legacy-book credit deterioration, a securities class action, and a years-long pre-AI discount; its internal review rates 86% of the book low-AI-risk. **OBDC's −22% is mostly sector beta** (spread marks, dividend reset) — Blue Owl's AI-DC lending sits at the *manager* level in other vehicles, not in the listed fund. The original reading of the dispersion ("stress concentrating where the weakest assets sit") was right about *discrimination* but wrong to imply the weakness being discriminated was AI exposure.
- The only defensibly AI/DC-exposed listed BDC, **BXSL, trades at just −9%**; the corrected, pre-registered measure (S3′: worst exposed minus non-AI control median) read **+7.5pp = neutral** on the day it was registered — not confirming.
- The structural reason the proxy is weak: **direct neocloud lending sits in private funds** (Blackstone, Blue Owl, Apollo, PIMCO, BlackRock vehicles), which have no daily price. The listed-BDC series is a window onto the private-credit *sector's* funding conditions (redemptions, marks, dividend resets — that part stands, with the Morningstar/Mercer redemption evidence), not onto AI-credit marks specifically.

What survives of layer 3: private-credit redemption pressure and semiliquid gating are real and sector-wide, CCC is diverging from flat HY and flat BB, and the marginal buyer of cluster paper is funded from exactly the vehicles experiencing redemptions. What does not survive: citing FSK/OBDC discounts as AI-specific convergence. The thesis keeps the mechanism and loses a talking point — which is the trade this project always takes.

## How this resolves

Dated confirm/kill criteria — including the conditions under which **we** are wrong — are in [preregistered_signals.md](preregistered_signals.md). The strongest case for the other side is in [bull_case.md](bull_case.md). The quantitative components evaluate automatically every hour; current status is in `viz/live.json` (`signals`).

## Sources (press/market tier)

- CoreWeave 9.75% '31 notes ($2.75B total): [Globe and Mail / company release](https://www.theglobeandmail.com/investing/markets/stocks/CRWV/pressreleases/1459647/coreweave-expands-high-yield-debt-with-additional-notes-offering/)
- $900M SPV print at 7.5% (Elk Grove Village Property LLC): [Yahoo Finance / Bloomberg](https://finance.yahoo.com/markets/stocks/articles/coreweave-crwv-subsidiary-raises-900-011330653.html)
- 3x+ oversubscribed euro books: [CoinCentral](https://coincentral.com/coreweave-crwv-stock-steady-following-3-6b-junk-bond-issuance-for-aggressive-ai-expansion/)
- Data-center ABS ≈ +210bp, compressing; $30–40B/yr issuance projection: [iCapital Market Pulse](https://icapital.com/insights/investment-market-strategy/icapital-market-pulse-data-center-infrastructure-moving-from-cash-to-debt/)
- Neocloud short interest: [Invezz](https://invezz.com/news/2026/05/21/traders-bet-against-coreweave-nebius-iren-stocks-despite-strong-growth/), [stockanalysis.com](https://stockanalysis.com/stocks/crwv/statistics/)
- BDC NAVs (Q1 2026 results): [OBDC](https://www.prnewswire.com/news-releases/blue-owl-capital-corporation-announces-march-31-2026-financial-results-302764665.html), [ARCC 10-Q](https://www.sec.gov/Archives/edgar/data/0001287750/000162828026027688/arcc-20260331.htm), [BXSL](https://www.fool.com/earnings/call-transcripts/2026/05/07/bxsl-q1-2026-earnings-transcript/), [FSK](https://www.stocktitan.net/news/FSK/fs-kkr-capital-corp-announces-first-quarter-2026-results-and-qnjwfrnvim9w.html)
- Private-credit redemptions / semiliquid stress: [Morningstar](https://www.morningstar.com/alternative-investments/blue-owls-misfire-offers-lesson-semiliquid-fund-risks), [Mercer Capital](https://mercercapital.com/insights/posts/2026/public-prices-private-marks-what-bdc-discounts-are-signaling/)
- HY OAS (BAMLH0A0HYM2), CCC OAS (BAMLH0A3HYC), 5y UST (DGS5): FRED, pulled directly (keyless CSV endpoint)
