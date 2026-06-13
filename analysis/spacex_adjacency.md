# SpaceX / orbital-compute adjacency — Phase-0 extension card

**Registered: 2026-06-12 (SPCX listing day).** Adjacency extension under the same buckets and tiers as the core engine — **NOT** part of the adjudicated financed-compute cluster; nothing here changes the gated verdicts (core 0.67 / ecosystem 0.25). Inputs are press summaries of SEC filings (S-1 and amendments) plus market data — we have not yet read the S-1 directly (SEC is IP-blocked from this environment), so every S-1-derived figure below is **press_reported-tier until exhibit-verified**. Not investment advice.

## The facts (as of the 2026-06-12 close)

| item | value | tier |
|---|---|---|
| IPO | Nasdaq **SPCX**, priced $135, 555,555,555 shares, **$75B raised** — largest IPO on record; trading began 2026-06-12 | press (filing-derivable) |
| Day one | open $150, high $176.52, close **$160.95 (+19.2%)**; valuation **>$2T** at close | market |
| xAI merger | SpaceX absorbed xAI **Feb 2026** (Colossus 1, Memphis: 220k+ NVIDIA GPUs) | press |
| Anthropic contract | **$1.25B/month**, leasing **all** Colossus 1 compute capacity; ~$45B over 3 years; disclosed in the **May 20 S-1** | press summary of S-1 |
| Google contract | **$920M/month**, ~110,000 NVIDIA GPUs, **Oct 2026 – Jun 2029** (~$30B total); disclosed in the **June 5 S-1 amendment** | press summary of S-1 |
| Termination clauses | **both contracts terminable on 90 days' notice after 2026-12-31** | press summary of S-1 |
| Alphabet stake | ~$900M invested 2015; **6.11%** end-2025, **~5%** post-xAI-merger dilution ≈ **~$100B** at the IPO valuation | press (Alphabet-filing-derivable) |
| Orbital program | FCC application 2026-01-30 for up to **1,000,000** satellite data centers (500–2,000 km); **AI1** orbital-compute satellite unveiled 2026-06-08; Anthropic "considering" multi-GW orbital capacity | filing (FCC) / press |
| Roadshow projections | Goldman pitch: **$100B/yr AI revenue by 2030**; ~$474B total 2030 revenue | press |

## The forensic read (same lenses we applied to the cluster)

**1. Headline vs. firm — the same shape as the engine's 98% strip.** Combined contract headline ≈ **$75B** ($45B Anthropic + $30B Google). With both contracts terminable on 90 days' notice after 2026-12-31, the earliest effective exit is ~2027-03-31 (notice 2027-01-01). Termination-adjusted **firm minimum**: Google 2026-10-01→2027-03-31 = 6 mo × $920M ≈ **$5.5B**; Anthropic (start date not in our sources; assuming the lease was running by ~Jun 2026) ≈ 10 mo × $1.25B ≈ **$12.5B**. **Firm minimum ≈ $18B ≈ 24% of the $75B headline — a ~76% haircut**, before any view on renewal. Arithmetic is ours; the start-date assumption and clause symmetry (which party may terminate) are flagged unknowns pending the actual exhibits. This is precisely the take-or-pay-vs-cancellable distinction that separated the cluster's verified backlog from its claimed paper.

**2. Customer-as-shareholder circularity — the largest instance we have carded anywhere.** Alphabet holds ~5% of SpaceX (≈$100B at the IPO valuation) *and* pays SpaceX $920M/month. The contract was disclosed in the June 5 S-1 amendment, one week before pricing — the revenue commitment of a 5% shareholder mechanically supporting the valuation of its own stake at listing. Same signature as NVIDIA→CoreWeave/Nebius (supplier/investor validating its customer), at ~50x the equity scale. NVIDIA sits inside both contracts as the hardware (110k GPUs in the Google deal; 220k+ in Colossus).

**3. Narrative vs. signed reality.** The valuation narrative is **orbital** (1M-satellite FCC filing, AI1 unveiling four days before listing, "multiple gigawatts" of orbital capacity under *consideration* by Anthropic). The signed revenue is **terrestrial GPU leasing** — Colossus 1 in Memphis and a conventional cloud-services agreement. The $474B/2030 roadshow projection rests on execution physics (launch cadence, on-orbit power/thermal/radiation, ground-link bandwidth) for which no delivery evidence exists yet. Money is arriving ahead of physical proof — the pattern the engine documents, here in its purest form.

**4. Demand-leg concentration, now spanning providers.** Anthropic's $15B/yr commitment to SpaceX compares to a company-stated **$47B run-rate** (2026-05-28 Series H announcement) — roughly **a third of its run-rate committed to one compute provider** *(corrected 2026-06-12: this card originally cited the April 6 ~$30B print as current, implying "roughly half")*, while Anthropic remains capital-markets-funded (the same funding class as OpenAI in our graph, where OpenAI = 56% of CoreWeave's named backlog). Anthropic now appears on both sides of our map: cluster ties (Hut 8/Google) and the SpaceX lease. A funding stumble at either frontier lab now propagates into *two* compute ecosystems.

**5. Classification — and why the cluster verdict does not move.** SpaceX/SPCX buckets as **pure-equity narrative**, not `financed_ai_infra_leveraged`: it just raised $75B of primary equity, carries no disclosed AI-infra debt burden, and has no debt-service coverage to breach. There is no Minsky solvency mechanic here — the risk axis is **expectations** (what $2T implies vs. terminable contracts and unproven orbital economics), not insolvency. Scope discipline therefore holds: this card is **pattern-extension evidence** for the ecosystem question — circular validation, narrative-forward valuation, soft-contract headline inflation — and the ecosystem verdict stays capped at 0.25 until evidence of this class passes the gate at volume.

**6. Cluster interaction (watch item).** The contracts put **~$26B/yr of compute supply** into the market from a $75B-capitalized competitor with zero debt-service pressure — direct competition for the renewals and utilization that the leveraged cluster *must* win to service debt. A well-capitalized entrant that can price below cost indefinitely is a new bear input for cluster utilization assumptions. (Goldman's pre-IPO SpaceX bridge role is already on the graph.)

## Monitoring (this card's calendar)

- **SPCX + GOOGL** quote hourly in `viz/live.json` under `adjacent` (deliberately separate from cluster `quotes`).
- **2026-10-01** — Google contract revenue start.
- **2027-01-01 → 2027-03-31** — termination-notice window opens; first quarter in which the $26B/yr run-rate is economically at-will. Renewal/termination behavior here is the single best test of whether the headline backlog was real.
- **~Dec 2026** — customary 180-day lockup expiry (assumed standard; unverified).
- AI1 launch/operational milestones vs. the FCC filing's deployment claims.
- Anthropic funding events (its capital-markets dependence now backstops ~$15B/yr of SPCX revenue).
- Exhibit-verify the S-1 contract terms (termination mechanics, party symmetry, take-or-pay vs. requirements) when SEC access is available — this card's figures upgrade from press to filing tier only then.

## Sources

[NPR — IPO pricing/raise](https://www.npr.org/2026/06/11/nx-s1-5853199/spacex-ipo-price-elon-musk) · [CNBC — day-one close](https://www.cnbc.com/2026/06/12/spacex-ipo-spcx-live-updates.html) · [CNN — $2T debut](https://www.cnn.com/2026/06/12/business/live-news/spacex-goes-public-ipo) · [TechCrunch — Google $920M/mo](https://techcrunch.com/2026/06/05/google-will-pay-spacex-920m-per-month-for-compute/) · [Tom's Hardware — Google deal detail](https://www.tomshardware.com/tech-industry/artificial-intelligence/google-signs-usd920m-monthly-compute-deal-with-spacex-companys-projected-annual-data-center-revenue-to-exceed-its-combined-proceeds-from-starlink-launch-services-and-ai-in-2025) · [KuCoin — S-1 contract disclosures + 90-day clauses](https://www.kucoin.com/news/flash/spacex-secures-26b-in-ai-compute-contracts-with-google-and-anthropic) · [MarketWise — Anthropic/Colossus lease](https://marketwise.com/investing/spacex-ipo-spcx-anthropic-deal/) · [SpaceNews — Anthropic orbital consideration](https://spacenews.com/anthropic-to-consider-using-spacex-orbital-data-center-satellites/) · [Introl — FCC 1M-satellite filing](https://introl.com/blog/spacex-1-million-orbital-data-centers-fcc-filing-2026) · [Yahoo/TradingKey/Benzinga — Alphabet stake](https://finance.yahoo.com/markets/stocks/articles/alphabet-spacex-stake-puts-fresh-170706420.html)
