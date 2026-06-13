# Information-edge map — what's gettable vs genuinely dark

**Started 2026-06-13.** Answers the question: *of the "omniscient wishlist" (the private intentions and hidden states that govern the **timing** of any cluster unraveling), what can an internet-connected, persistent agent actually retrieve — and what is irreducibly private?* Three tiers per item:

- **FILING** — obtained at filing tier (SEC EDGAR exhibits), already in the repo's evidence.
- **SCUTTLEBUTT** — not in filings, but obtainable as a usable approximation from the open web / channel checks (the WS2.4 Fisher-protocol surface).
- **DARK** — genuinely private; redacted in filings or never disclosed; obtainable only from inside the counterparty's rooms.

The headline result (developed below): **EDGAR comprehensively resolves the *structure*; the two variables that most govern *timing* — CoreWeave's covenant headroom and the OpenAI/Microsoft contract cancellability — are DARK even inside the filed exhibits.** Most of the rest is SCUTTLEBUTT, partially retrievable.

## Master table

| # | wishlist item | tier | status |
|---|---|---|---|
| 1a | CoreWeave customer concentration | **FILING** | 67% Microsoft, 77% top-two — verbatim ([filing_verifications.md](filing_verifications.md)) |
| 1b | CoreWeave take-or-pay *structure* | **FILING** | disclosed ("vast majority… take-or-pay") |
| 1c | OpenAI/MS contract *cancellation conditions* (MAC, survives-funding-failure?) | **DARK** | master agreements not filed quotably; 424B4 discloses *some* contracts are terminable "with limited notice" but not which |
| 2a | CoreWeave leverage covenant *exists* | **FILING** | Consolidated Leverage Ratio = Total Debt / Consolidated EBITDA (EX-10.14) |
| 2b | Covenant *threshold* + current headroom | **DARK → partly FILING** | leverage threshold still redacted, BUT the Dec-31-2025 First Amendment (8-K) discloses DSCR testing **postponed to Oct-31-2027**, min-liquidity cut to $100M, **unlimited equity cures** through Oct-2026 — the near-term covenant trip is defused to ~2027 |
| 2c | CoreWeave liquidity runway / burn-vs-draw | **FILING/SCUTTLEBUTT** | $21.6B debt + $3.7B undrawn (YE2025), $31–35B/yr capex guide — runway is *derivable* from disclosed figures; exact monthly schedule is DARK |
| 3 | Microsoft posture (backstop intent + in-sourcing) | **SCUTTLEBUTT** | DONE — customer-only (no stake/backstop), has walked from incremental capacity before; 67%→<50% by design; Maia is inference-only; capex plateauing on power/supply not demand. The real backstop is NVIDIA, not Microsoft. |
| 4 | OpenAI funding state (cash, burn, next raise, funded-vs-framework) | **SCUTTLEBUTT** | DONE — $122B round closed (Mar-26) but burn revised up twice (~$665B/2030), needs ~$207B more by 2030 (HSBC); NVIDIA "$100B"→$30B; IPO filed ~Jun-26. Counterparty CDS stress visible (Oracle ~198bp record, bondholder lawsuit). |
| 5 | Private-credit redemptions + AI-DC marks + appetite | **SCUTTLEBUTT** | DONE — first link BUCKLED (Q1-26 first-ever net outflow + industry proration wave, still accelerating); but far link HELD AT PAR ("mark-to-myth"), ratings rising, record IG-anchored appetite; non-IG neoclouds frozen out. Latency, not realized loss. |
| 6 | NVIDIA roadmap + vendor-financing | **SCUTTLEBUTT** | DONE — >$40B equity into customers in 2026; $6.3B CoreWeave backstop confirmed; Rubin ships fall-26, annual cadence. Lucent parallel real in form but BREAKS (equity not loans; DSO falling 45d; ~5-7% of rev). Fragility pushed to 3rd-party GPU debt. |
| 7 | GPU rental rates + real utilization | **SCUTTLEBUTT** | DONE — rates CRASHED then REBOUNDED +40%; first-cohort H100 contracts re-leasing at SAME rate (renewal test PASSED 2026) — but a transition-gap artifact; resale already −85%; real test deferred to 2027 (Blackwell glut + Rubin). Break-even ~70-80% occupancy, no margin. Occupancy % undisclosed = DARK. |

## 1–2 · CoreWeave itself (EDGAR exhibit dive — done)

The actual filed exhibits (10-K acc 0001769628-26-000104; 424B4 acc 0001193125-25-067651) give up the structure and redact the timing-critical numbers:

- **Concentration (FILING):** 41%/73% top-three (2022/2023) → 77% top-two (2024) → 67% Microsoft (2025). The dependence is real, disclosed, and rising-then-concentrating on Microsoft.
- **Take-or-pay (FILING, with a caveat):** "the vast majority of our revenue today is from multi-year committed contracts… on a take-or-pay basis" — *but* "some of our customer contracts are on-demand… permit the customer to terminate their contracts or decrease usage… with limited notice." So CoreWeave's book is **mixed**, and the prospectus does not say which bucket the OpenAI/Microsoft contracts sit in or what conditions void the take-or-pay.
- **Covenant (FILING structure / DARK level):** EX-10.14 (4th Amendment to the Parent Credit Agreement) defines a Consolidated Leverage Ratio covenant — but the threshold is redacted. **Covenant headroom, the single most timing-relevant number, is DARK.**
- **Governance signal (FILING):** EX-10.33 (Nov 2025) — Magnetar relinquished its board-nomination right. A private-credit anchor stepping back from governance.
- **Runway (DERIVABLE):** $21.6B total debt + $3.7B undrawn at YE2025 against $31–35B/yr capex guidance and a −$1.2B net loss. The *direction* is unambiguous (cannot self-fund; depends on continuous issuance); the *exact* monthly burn-vs-draw schedule is DARK.

## 3–7 · The counterparty/market threads

Six parallel research agents retrieving the SCUTTLEBUTT-tier approximations; this section fills as they complete.

### Thread 3 — Microsoft posture (DONE) + a backstop reframe

The "Microsoft cures CoreWeave" assumption — which I'd flagged as the single biggest *extender* of the timeline — **needs correcting, and the correction cuts against the bull:**

- **Microsoft is a *customer only* — no equity stake, warrants, or ROFR over CoreWeave** (searched directly; confirmed negative). So there is **no contractual Microsoft obligation to backstop** CoreWeave in stress; the bull's "incumbent absorbs the fringe" leg has no equity mechanism behind it here.
- **Microsoft has already demonstrated willingness to walk.** In early 2025 it withdrew from CoreWeave agreements citing "delivery problems and missed deadlines" (FT) and walked ~2GW of projects (TD Cowen) — though SemiAnalysis corrected that this was *largely non-binding LOIs* and an OpenAI-driven reshuffle (as Microsoft's OpenAI exclusivity loosened, OpenAI contracted directly with CoreWeave). Microsoft retained ~5GW binding. **Mechanism: a swap, not a collapse — but it proves Microsoft treats incremental CoreWeave capacity as discretionary.**
- **The 67% is a *decaying-share* anchor, declining by design.** CoreWeave's Q1-2026 call didn't mention Microsoft; management guides Microsoft <50% of revenue through 2026 as OpenAI (~$22.4B), Meta (~$35B), Anthropic, and Jane Street ramp. *Re-risking nuance:* diversification shifts the backlog *away from durable Microsoft toward more capital-markets-funded counterparties (OpenAI, Anthropic)* — the fragile-demand share grows even as the Microsoft number falls.
- **In-sourcing is "build-AND-rent," not "build-instead."** Maia 200 (launched ~Jan 2026, TSMC 3nm) is an *inference* cost-optimizer, behind Google TPU / Amazon Trainium, not a frontier-training-GPU replacement. Microsoft kept renting third-party GPU well after the CoreWeave noise (Nebius $17.4B, Sept 2025). Nadella: *"I'm thrilled that I'm going to be leasing a lot of capacity in '27, '28."*
- **Capex is plateauing on *supply*, not demand.** Q2 FY26 $37.5B → Q3 $31.9B sequential decline, but framed as power/component-constrained (Nadella: *"chips sitting in inventory that I can't plug in… that is my problem today"*); CY2026 guide ~$190B (~$25B of it memory-price inflation). Backlog doubled to $625B (OpenAI $250B commitment).

**The real backstop is NVIDIA, and it's circular.** Filing-confirmed: **NVIDIA invested $2B in CoreWeave Class A at $87.20/share in January 2026** (10-K subsequent events). Press-reported (NOT yet found in the 10-K — queued for an 8-K check): a **~$6.3B NVIDIA unsold-capacity backstop through 2032** and **OpenAI's $350M equity stake** in CoreWeave. So the entity actually standing behind CoreWeave's demand is its *chip supplier* (vendor-financing / round-trip — the Lucent-Nortel tell), not its largest customer. Separately, **Magnetar's 5%-at-IPO-price option expired unexercised** and it relinquished its board seat — a second private-credit anchor stepping back.

**Net for the timeline:** the biggest *extender* I'd posited (Microsoft backstop) is weaker than assumed — Microsoft is discretionary and decaying-share — while the actual backstop (NVIDIA capacity guarantee) is *circular* and therefore not an independent source of strength. This modestly *shortens* the plausible timeline relative to the prior read.

### Thread 4 — OpenAI funding (the fragile demand leg)

- **The $122B round closed** (Mar 31 2026, $852B post) — real liquidity. But **burn was revised UP twice in ~3 months** (~$665B training+operating through 2030); HSBC: needs **~$207B of *additional* financing by 2030** even at >$200B revenue. Cash-flow positive not before 2029–30; 2025 gross margin ~33% and falling.
- **The headline backers are heavily conditional/framework:** NVIDIA's "$100B" LOI shrank to a **$30B equity check** (Huang: "probably not in the cards"; never definitive); Amazon's $50B is only **$15B firm** ($35B AGI/IPO-contingent); SoftBank tranched. **OpenAI confidentially filed for an IPO (~Jun 8 2026)**, targeting >$1T — the next required capital event.
- **Compute-commitment stack ≈ $1.1–1.4T** (Oracle ~$300B Stargate, Microsoft ~$250B, Broadcom ~$350B, AMD ~$90B+warrant, AWS $38B→~$100B, CoreWeave ~$22.4B) vs **~1.9 GW deployed** of ~30 GW committed. Funded by equity rounds + IPO + *counterparties raising debt against OpenAI's contracts* + circular vendor financing.
- **Counterparty credit stress is now VISIBLE (confirming):** **Oracle 5-yr CDS hit a record ~198bp**; Oracle bondholders (Ohio Carpenters' Pension) **sued** over OpenAI-linked debt (Jan 2026); ≥$300B of Oracle's ~$523–638B RPO is OpenAI. CoreWeave CDS reportedly spiked into the 600s bp at peak. The market is starting to price the fragile leg.
- **Correction carried into the repo:** OpenAI is **~20–33% of CoreWeave's backlog, not 56%** (10-K: ~$11.9B of $60.7B RPO; ~33% all-in). The fragile leg is real but *smaller* than the engine carried.

### Thread 5 — Private credit (the transmission chain) — the most important nuance

The funding chain is **stressed at the near end, latent at the far end:**

- **First link BUCKLED:** Q1-2026 was the **first quarter ever** where non-traded-BDC redemptions ($6.9B) exceeded fundraising ($4.9B); the **first industry-wide proration wave** (Apollo 45.2%, Ares 43.1%, Blue Owl OTIC 40.7% requested→~12% filled, HPS first gate, BCRED's first true gate in Q2). Sector redemptions tripled Q4→Q1 and **were still accelerating** through the latest data (BofA *forecasts* a Q2 peak — not yet realized). Verified across Stanger/Bloomberg/Benzinga.
- **But the far link is HELD AT PAR:** **no documented fair-value markdown on any named neocloud/GPU loan** (CoreWeave, Lambda, Crusoe, Nebius…). The confirmed write-downs are **SaaS/software** (a different "AI-disrupts-SaaS" thesis — Medallia, BlackRock's aggregator loan), not AI-infra. CAIA/BIS call it "mark-to-myth": "loans held at par… no mechanism by which deterioration surfaces until a hard event forces recognition… the secondary market is pricing closer to the shadow figures." **This is the latency the whole thesis hinges on.**
- **Appetite has BIFURCATED, not collapsed:** record IG-anchored deals still closing (**$35B Apollo/Blackstone Broadcom-Anthropic SPV, Jun 9 2026**; Meta Hyperion ~$27–30B; CoreWeave $8.5B IG DDTL) while **non-IG neoclouds are frozen out at origination** ("IG-or-nothing"; a fully-prepaid 15-yr neocloud lease *failed* to close). The credit window is open for hyperscaler-wrapped paper, shut for standalone neoclouds.
- **The IG rating is a hyperscaler-credit wrapper, not GPU validation:** CoreWeave's $8.5B DDTL is **A3 only because Meta's Aa2 take-or-pay (~$19–21B, non-terminable-for-convenience, with step-in rights) backs it** — the "Trophy Deal Trap." CoreWeave's *corporate* ratings stay speculative (Moody's Ba3 / S&P B+ / Fitch BB-). The "first investment-grade GPU loan" milestone is really "Meta's balance sheet financing."
- **Regulators are now naming the mechanism (strong external validation):** Fed Gov. Cook (May 27 2026, the richest source) cited ">$1.5T data-center plans, only a small portion realized," smaller developers "raising debt from private debt funds and asset-backed credit markets," and "the wave of redemptions… on perpetual BDCs"; FSB (May 6): **AI was >⅓ of private-credit deals in 2025 (from 17%)**; IMF GFSR: "circular financing structures that may artificially amplify reported revenues"; BoE/ECB/BIS all flagging.

### Thread 6 — NVIDIA (the circular backstop)

- **Vendor-financing ledger is large and growing:** **>$40B of NVIDIA equity into its own customers in 2026 alone** — CoreWeave ($2B Jan-26, filing-confirmed + the **$6.3B unsold-capacity backstop through 2032**, confirmed), Nebius ($2B), xAI ($2B), IREN ($2.1B right), Lambda, Nscale, Crusoe, Anthropic ($10B), OpenAI ($30B). The chip supplier, not the customer, is what stands behind cluster demand — the **Lucent/Nortel vendor-financing tell** (Burry: "not Enron… clearly Cisco").
- **But the Lucent parallel BREAKS in three measurable ways (a genuine bull point):** NVIDIA's support is **equity + capacity backstops, not direct vendor loans**; its **DSO is *falling* (45 days, improving)**, not ballooning like Lucent's receivables; and the equity is **~5–7% of revenue**, vs telecom vendors at >100% of earnings. The fragility is real but **pushed one layer out** to the third-party GPU-backed debt market — which is exactly where a Rubin-accelerated resale collapse would bite first.
- **Roadmap sets the 2027 clock:** Rubin unveiled GTC (Mar 2026), production ships **fall 2026**; Rubin Ultra 2027, Feynman 2028 — an **annual frontier cadence** that strands each prior generation faster. First Rubin partners: CoreWeave, Lambda, Oracle. NVIDIA Q1-FY27 revenue $81.6B (+85%), Data Center $75.2B — the supplier is booming while its customers bleed.

### Thread 7 — GPU economics (the renewal clock) — the strongest *bull* data point

- **The renewal test PASSED in 2026 — empirically.** H100 rental **crashed ~70–80%** (2023→Oct-25 trough $1.70) then **rebounded +40% to $2.35**, and — the load-bearing fact (SemiAnalysis primary) — **expiring H100 contracts are renewing at the *same rate* they were signed at 2–3 years ago**, some extended to 2028. A100s (the 6-yr-precedent gen) still earn ~$0.93/hr at >70% margin. The first cohort *re-leased*.
- **But it's a transition-gap artifact, not durable competitiveness:** the rebound is NVIDIA cutting Hopper supply + Blackwell sold out + an inference surge — Blackwell still crushes Hopper 2× training / 10–35× inference-cost-per-token at frontier scale. **Resale value has already stranded ~85%** ($50k→$17–20k used H100). The deferred softening reloads in **2027** (Blackwell abundance + Rubin volume).
- **The economics have no margin of safety:** debt-financed clusters break even at **~70–80% occupancy** (a ~$670k/mo swing on a 30-pt move); break-even *rate* ~$1.65/hr sits *below* the recent trough. And **neocloud occupancy % is undisclosed** (CoreWeave doesn't report it) — genuinely DARK; the "70–80%" is a third-party estimate.
- **Depreciation divergence is filing-visible and contested:** CoreWeave 6yr, Amazon *cut* to 5yr, Meta *extended* to 5.5yr, Nebius 4yr. Burry: real life 2–3yr; ~$176B understated depreciation 2026–28. The book lives the lenders accepted "now look smarter" *for this cycle* — the question is the next supply normalization.

### Thread (insurance) — the ultimate downside-bearer (architecture confirmed)

- **Confirmed by structure:** Apollo-managed funds did a **$3.5B capital solution for Valor/xAI** GB200 compute (triple-net lease, NVIDIA anchor LP); **Blackstone Credit & Insurance anchored CoreWeave's $8.5B**. Private credit is **~35% of US insurer portfolios**; insurer CLO holdings $276.8B. Data-center ABS **~$25B (2025)→$30B+ (2026)**; GPU-ABS senior spreads compressed 150→105–110bp, with **residual-value insurance often guaranteeing ~40% of GPU value**.
- **The recognition-forcing regulation is DEFERRED:** NAIC's CLO/rated-note capital-charge rulemaking slipped to **2027** — so the capital incentive that would force insurers to mark or sell is a year-plus away. Stress is appearing first at the **sub-IG neocloud tenant layer** (deals failing on credit), exactly the cascade entry point, while the IG-rated paper holds.

## Conclusion — the answer, and the deepened picture

**Your question: can a persistent agent get the omniscient wishlist?** The answer is now precise and three-tiered:

- **The *structure* is fully FILING-legible** and, tonight, comprehensively verified: 67% Microsoft, the take-or-pay framework, the loss-making base, the CoreWeave customer-hub cascade, the leverage magnitude, the circular NVIDIA financing, three late-2025 covenant amendments.
- **The *context* is SCUTTLEBUTT-gettable** and now gathered: OpenAI's funding fragility and visible counterparty CDS stress; the private-credit chain buckling at the retail end but held-at-par at the loan end; NVIDIA's vendor-financing ledger; the GPU-rate rebound; the insurance architecture; the regulators now naming it.
- **Four things stay genuinely DARK** — (1) **CoreWeave's covenant headroom *level*** (redacted; but the Dec-31 amendment reveals the DSCR test is off until Oct-2027); (2) **whether the OpenAI/Microsoft take-or-pay survives a customer funding failure** (undisclosed); (3) **real neocloud occupancy %** (undisclosed; the ~70–80% break-even number is third-party estimate only); and (4) found tonight — **the marks and terms on the cluster's *private* debt** (CoreWeave DDTLs, Cipher's $2B Black Pearl, the Blackstone/Magnetar/Apollo holdings sit in private SPVs/funds not in any public filing; Black Pearl's indenture isn't filed at all). These live in a credit-committee room, a contract data-room, and a fund's LP report — obtainable only by a counterparty source. Full capstone: [information_completeness_report.md](information_completeness_report.md).

**The deepened analytical picture is more *balanced* than the prior read, and the change is honest:** the bear *structure* is confirmed and now **mainstream-regulator-acknowledged** (Fed, FSB, IMF, BoE, ECB, BIS) — but four things genuinely cut *against* near-term unraveling: (1) the first-cohort GPU contracts **re-leased at signing rates** in 2026; (2) the AI-infra loans are **held at par with rising ratings and record IG-anchored appetite**; (3) NVIDIA's circular financing, while real, **breaks the Lucent parallel** (equity not loans, DSO falling); and (4) the regulation that would force mark recognition is **deferred to 2027**. The stress is **real but latent** — concentrated at the retail-redemption and counterparty-CDS layers, not yet at the loan-mark layer.

**So the timing reduces to a single question the DARK items would answer:** *when do the held-at-par marks get forced into recognition?* The three triggers, now sharpened by tonight's filing finds — and notably **converging on 2027:**
- A **CoreWeave covenant event** — but the Dec-31-2025 First Amendment (filing-confirmed) **postpones DSCR testing to Oct-31-2027** and grants **unlimited equity cures through Oct-2026**, so this trigger is **defused near-term and re-armed in late 2027.** (That lenders granted the relief confirms the bleed is real; that they granted it at all buys ~18 months.)
- The **2027 GPU-resale normalization** (Blackwell abundance + Rubin volume) hitting a cohort whose 6-year book lives the secondary market has already repudiated (resale −85%) — the renewal test that *passed* in 2026 re-runs in 2027 without the supply-squeeze tailwind.
- An **OpenAI/Oracle funding event** — the only trigger already *moving* (Oracle CDS ~198bp, bondholder suit), and the least calendar-bound (OpenAI's IPO and burn are the variables).

Two of the three now point to **2027**, and the third is exogenous. The structure is damning and witnessed; the fuse was just shown (by CoreWeave's own 8-K) to be **~18 months longer than a naive read assumed** — the covenant that would force the event was contractually pushed to late 2027. That is the most precise answer to what omniscience would buy you: *not the diagnosis (legible now), only the date (held in the two rooms we can't see — and, per the amendment, deliberately set past 2027).*
