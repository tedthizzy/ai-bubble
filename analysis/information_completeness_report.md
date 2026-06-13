# Information-completeness report — the overnight deep dive

**2026-06-13, autonomous run.** Ted asked: *if you were omniscient, what would you want to know — and can a persistent, internet-connected agent actually get it?* This is the capstone after working the question to exhaustion: a full EDGAR exhibit dive across the cluster + a six-thread scuttlebutt sweep, all committed incrementally (commits `10e4c81` → `1e07324`, with `5a952fe` the highest-value find). Companion: [information_edge_map.md](information_edge_map.md) (the item-by-item FILING/SCUTTLEBUTT/DARK map) and [filing_verifications.md](filing_verifications.md) (verbatim provenance).

## The answer in one line

**The *structure* is fully gettable and now exhaustively verified; the *context* is gettable and gathered; the *timing* is held in four genuinely-dark places — and one of them (the covenant) was partly pried open tonight and pushed the fuse to ~late 2027.** Omniscience would buy you the date, not the diagnosis.

## What was GOTTEN at filing tier (the structure — comprehensively verified)

- **CoreWeave**: 67% Microsoft / 77% top-two concentration; take-or-pay framework; $21.6B total debt (YE2025) + the full note/DDTL stack; the existence of a Consolidated Leverage Ratio covenant; **the Dec-31-2025 First Amendment (DSCR testing postponed to Oct-31-2027, min-liquidity cut to $100M, unlimited equity cures through Oct-2026)**; the OpenAI **$350M equity stake + SPV lien**; NVIDIA's **$2B Jan-2026 equity**; three credit-agreement amendments in eight weeks; Magnetar relinquishing its board seat and its 5% option expiring.
- **Cluster-wide (12 issuers + 2 BDCs)**: the CoreWeave customer-hub cascade (CORZ 100%, GLXY single-customer, APLD ~$11B — all verbatim); overwhelmingly loss-making (only CLSK +$364M, IREN +$86.9M); the convert-vs-secured debt-structure split; IREN's GAAP RPO $710M vs its ~$13B headline; Cipher's $2B Black Pearl SPV; **going-concern false alarm rejected airtight** (all six flagged auditor opinions clean; zero red-flag 8-Ks cluster-wide in 90 days).
- **SpaceX 424B4**: the Anthropic terms, the *withdrawn* Google contract, Cursor, Terafab.

## What was GOTTEN at scuttlebutt tier (the context — gathered)

Microsoft is customer-only and decaying-share (no backstop obligation); OpenAI's funding fragility + **visible counterparty CDS stress** (Oracle ~198bp record, bondholder suit); the private-credit chain **buckling at the retail end but held-at-par at the loan end**; NVIDIA's vendor-financing ledger (real, but breaks the Lucent parallel); the **GPU renewal test passing in 2026** (rates rebounded, first cohort re-leased at signing rates) **but deferred to 2027**; the insurance architecture; **regulators now naming the mechanism** (Fed, FSB, IMF, BoE, ECB, BIS); NAIC mark-recognition rules **deferred to 2027**.

## What is genuinely DARK (the irreducible residual — only a counterparty source gets these)

1. **CoreWeave's covenant *level* / current headroom** — the Consolidated Leverage Ratio threshold is redacted. *(Partly pried open: the Dec-31 amendment reveals the DSCR test is off until Oct-2027 with unlimited equity cures — so the near-term trip is defused regardless of the level.)*
2. **Whether the OpenAI/Microsoft take-or-pay survives a customer funding failure** — the master agreements are not filed quotably; the prospectus only admits *some* contracts are terminable "with limited notice."
3. **Real neocloud occupancy %** — CoreWeave and peers do not disclose it; the load-bearing solvency number (~70–80% break-even) is third-party estimate only.
4. **The actual marks and terms on the cluster's *private* debt** — found tonight: CoreWeave's DDTLs, Cipher's $2B Black Pearl, and the Blackstone/Magnetar/Apollo holdings sit in **private SPVs and private funds whose terms and fair-value marks are not in any public filing** (Black Pearl's indenture isn't filed at all). This is *the* "mark-to-myth" question, and it is structurally private — obtainable only from a fund's LP report or the deal data room.

## What remains gettable-but-not-timeline-decisive (examined-in-category, deliberately not exhausted)

- **Registered HY-note indentures** (CRWV 9.25%/9.00%, TeraWulf 7.75%, Hut 8) carry standard change-of-control puts / restricted-payment / cross-default covenants — gettable, but the *timeline-decisive* covenant (CoreWeave's DSCR) is already in hand, and these add waterfall detail, not a new conclusion. (The *private* SPV indentures, which would matter more, aren't public — see DARK #4.)
- **FCC / FERC-ISO interconnection-queue / EPA permit data** — gettable, but bears on physical-execution magnitude (already a confounded, magnitude-only engine input), not on the credit/timing question that this exercise targets.

These are flagged honestly rather than ground through, because the marginal information they add does not move the answer.

## The deepened bottom line (what the night changed)

The picture is **more balanced and more precisely timed** than where the day began:

- The bear *structure* is confirmed and **mainstream-regulator-acknowledged** — but four things genuinely cut against *near-term* unraveling: GPU contracts **re-leased at signing rates** in 2026; AI-infra loans **held at par** with rising ratings and record IG-anchored appetite; NVIDIA's circularity **breaks the Lucent parallel**; and mark-forcing regulation is **deferred to 2027**.
- Tonight's decisive find: CoreWeave's own 8-K **postponed its DSCR covenant test to Oct-31-2027** with unlimited equity cures — so the most plausible near-term *forced-recognition* trigger is contractually **pushed ~18 months out**, converging with the **2027 GPU-resale normalization** (Blackwell glut + Rubin). Two of the three recognition triggers now point to **2027**; the third (OpenAI/Oracle funding) is exogenous and already the only one moving.
- So the honest synthesis: **the cluster is structurally fragile, witnessed, regulator-flagged — and deliberately fused past 2027 by its own lenders.** The stress is real but latent; the marks are held at par in rooms we can't see; and the engine's pre-registered signals (issuance window, CCC divergence, BDC differential, demand trajectory) remain the right instrument to catch the moment the latency breaks — most likely in **2027**, unless an OpenAI/Oracle funding event pulls it forward.

**On Ted's question, definitively:** a persistent agent *can* get the entire structure and nearly all the context — far more than expected, because most of the "private" wishlist turned out to be buried in exhibits, not hidden. What it *cannot* get is the covenant headroom level, the contract-cancellability clause, real occupancy, and the private-debt marks — four numbers in four rooms. Those are the irreducible information edge, and three of the four would only sharpen a date the structure already makes inevitable in direction.

---

*Loop status: high-value gettable surface exhausted; remaining items are DARK or non-decisive (documented above). Standing the self-audit loop down. The pre-registered signals + the 2027 convergence are the live watch items.*
