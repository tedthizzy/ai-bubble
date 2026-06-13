# Total economic fragility dive — find mispricing and hidden leverage across the whole economy, no sector prior

**2026-06-13.** The object of this project is **not "AI."** AI/data-center was a useful *starting point* — case zero — but the actual instrument is a **general forensic engine for financial fragility and mispricing**: wherever in the economy capital and valuation have run ahead of the cash flows and physical reality that would justify them, financed with leverage that is hidden, mismatched, or circular, such that the price is wrong and no one has marked it yet. This plan points that engine at its true scope — **the entire economy** — and lets the fragility concentrations reveal *their own* location, rather than presupposing where they are.

**AI-compute is a finding, not the frame.** It is the current brightest *known* concentration and the case that validated the method — but the same engine's fingerprints are already in this repo's [base-rate book](base_rates.md): **fiber/telecom (1999), shale (2014).** The method is sector- and era-agnostic; "is the AI-compute cluster a bubble?" was one query against a general detector. This is the generalization.

## Progress ledger (live — updated as the dive runs)

**As of 2026-06-13 (~midday).** Execution started this morning on Ted's go; the storage gate (≈54 GiB free, since enlarged) is cleared. This section is the live status so a context-lost agent knows what is done vs pending. **Everything below is a PRELIMINARY first pass, not a verified conclusion** — see the caveat at the end.

- **✅ Phase 1 — sector-agnostic signature scan** (`scripts/economy_wide_signature_scan.py` → [economy_wide_fragility_map.md](economy_wide_fragility_map.md)). 2,091 entities scored on the 8 §2 signatures, NO AI filter. **Headline: AI's top entity ranks #14; only 3 AI names in the top 50.** Plus a **canary lens** (1,078 small-debt, high-non-size-signal names — the fails-first tail).
- **✅ Phase 2 — sector classification** ([fragility_by_sector.md](fragility_by_sector.md)) + **SIC ground-truthing** ([fragility_by_sic.md](fragility_by_sic.md), 131/140 CIKs resolved from data.sec.gov). **Finding: no single epicenter** — fragility is broadly distributed; largest concentrations are SIC 67 (REITs/mortgage-REITs/BDCs, $373B), SIC 48 telecom, SIC 49 utilities. Banks reclassified off the corporate-leverage axis.
- **🔄 Phase 3 — deep-agent fan-out** (`scripts/build_phase3_targets.py` → 143 targets; `scripts/workflows/phase3_deep_dive.workflow.js`; findings extractor `scripts/extract_phase3_findings.py` → [phase3_findings.md](phase3_findings.md), [phase3_plan.md](phase3_plan.md)). Per-target forensic profile + adversarial refutation. **Interim: ~half of verified flags refuted as data artifacts / stale signals — the scan is high-recall, low-precision; the verification layer is what makes it trustworthy.** Confirmed already-distressed canaries: Celularity, Perfect Moment, SunPower, Hyperscale Data, NextNRG, Humacyte, Southland.
- **⏳ Phase 4 — synthesis + forward projection** (`PENDING`): the concise current-state read + base-rate-anchored timing, written once Phase 3 completes and the surviving theses are EDGAR-confirmed locally.
- **⏳ Queued refinements** (cleared by storage, not yet run): XBRL net-debt/EBITDA join (notional → true leverage), Form-4/8-K/NT **distress §2.8 extraction** (the one unpopulated signature), deepening past the first 143 into the canary tail.

> **Caveat (binding for anyone reading the results):** nothing here is filing-verified *by the orchestrator* yet — the per-entity claims are the deep agents' work, pending local EDGAR confirmation. The ~47% artifact rate in Phase 1 means the "confirmed" set also likely contains residual errors. This is a high-quality **direction-setter**, not a proven verdict. Calibrate accordingly.

## Operating principle (binding — see the README's Operating Doctrine)

> **Broad AND deep. Not shallow. Uncapped. No sector prior. Limited only by physics.**

- **No presupposed core.** Do *not* scope by "exposed to CoreWeave" (presupposes the epicenter) or "touches AI" (presupposes the sector). Both bake in an answer. Scope by **economic substance**, scan by **forensic signature**, and let the epicenter be an *output*.
- **Broad** = the whole economy. The repo's 7,708-entity field is a *floor*; the true total is an **output of enumeration**, plausibly **low millions** (every public company, debt issuer, fund, and materially-financed private/SPV globally).
- **Deep** = every retrievable dimension for every in-scope entity, to the maximum each source allows — the obscure $1M-debt shell gets the same treatment as a mega-cap.
- **Limited only by physics** = the single legitimate stop is that the data *does not publicly exist* (§7) — and even then we *estimate* it from proxies. Effort, volume, breadth, tedium, run time, subagent count: never reasons to narrow, sample, cap, or triage. Thousands of subagents and hundreds of hours for one pass is the expectation.
- **One-time, not real-time.** A single exhaustive pass that captures the full history sitting in the record today. Continuous monitoring is the hourly overlay's job, out of scope here.

## §0 — The scope floor (the one legitimate exclusion)

An entity is **in scope** if it has **economic substance ≥ $1M on *any* material financial dimension** — debt, financing raised, deal/contract value, assets, revenue, *or* committed capital — **and** leaves a retrievable public-record footprint.

- **Relative size never excludes.** A $50M entity is small only next to the giants; it is firmly in. The $1M floor is the established repo materiality line (deals were always ≥$1M); it is *low on purpose*.
- **Inclusive across dimensions** — a pre-revenue $1M-debt SPV with ~$0 revenue is **in** (it is exactly the obscure thing that detonates). The floor is never "revenue ≥ $1M," which would filter out the most interesting canaries.
- **"Small" = strictly below $1M on every dimension.** Such an entity drops out only because it is *both* immaterial *and* record-less — physics, not judgment (the corner dentist that uses an AI tool: no $1M footprint, no financing record → out).

**Geographic scope: US-primary.** US entities are covered exhaustively. International entities are included **in proportion to (connectedness to the core economy / a flagged concentration) × (data accessibility)** — a materially-connected, reasonably-public foreign player (e.g. TSMC, SK Hynix, Bermuda reinsurers, foreign-domiciled neoclouds/SPVs) is **in**; a far-removed entity behind an obscure-language, low-disclosure regime is not worth the translation/extraction cost. This is **partly a physics limit, not a choice** — many jurisdictions publish minimal corporate disclosure, so the data simply doesn't exist to pull. A relevance-and-accessibility gradient, never a hard omission of "international."

## §1 — Enumerate the substrate: every ≥$1M entity, economy-wide

Phase one builds the most complete economy-wide entity list the public record allows — no sector filter. Enumeration sources (the entity census, before any signature scan):

- **All SEC/EDGAR registrants** (every 10-K/Q/8-K/S-1/424B/Form-D/13F filer) — public companies + funds, economy-wide.
- **All debt/credit issuers** — bond issuers (TRACE/EDGAR), syndicated-loan borrowers, ABS/CLO trusts, muni issuers.
- **All UCC-1 debtors** (every secured borrower in every state) — the broadest census of *financed* private entities that exists.
- **State corporate/LLC registries + registered-agent reverse-lookup** — the SPV/shell layer.
- **Fund formation** (Form D, ADV, BDC/interval-fund filings) — the credit/PE/insurance vehicle layer.
- **Regulated-entity rolls** — NAIC (insurers), bank call reports, FERC/ISO (power), REITs, etc.
- **Court/PACER** (bankruptcy + commercial litigation parties), **property records** (material real-estate owners), **customs/bills-of-lading** (material importers).
- Within any concentration the scan later flags, **decompose into roles** — issuer / SPV / lender / fund / end-holder / supplier / customer / counterparty — exactly as the AI-compute case did (see §8, case zero).

## §2 — The discovery engine: scan the substrate for the forensic SIGNATURES

This is what turns an atlas into an analysis. The epicenter is wherever these **cluster** — sector falls out as a result, not in as an assumption. The signatures (the engine's fragility conditions, generalized):

1. **Leverage ahead of cash flow** — debt/EBITDA, interest coverage, negative carry (paying more on debt than the asset earns), capex-running-ahead-of-revenue.
2. **Asset-liability *duration* mismatch** — debt outliving the economic life of the collateral it's secured on (the GPU-vs-debt finding, generalized to *any* short-lived-asset-financed-with-long-debt structure).
3. **Circular / vendor financing** — a supplier funding its own customers' purchases (the NVIDIA/Lucent tell, generalized); round-tripping; investor-as-customer.
4. **Concentration** — single-customer / single-funder / single-counterparty dependence above existential thresholds.
5. **Valuation / narrative ahead of fundamentals** — price implying economics the cash flows don't support (expectations-inversion, generalized economy-wide).
6. **Hidden / off-balance-sheet leverage** — SPVs, guarantees, lease structures, redemption-gated funds, mark-to-myth private credit.
7. **Refinancing walls** — maturity stacks on assets that will be impaired before the debt comes due.
8. **Distress leading indicators** — insider selling, covenant amendments/waivers, late filings, layoffs, non-payment litigation/liens, redemption gates, executive departures, rating actions.

Every ≥$1M entity is scored on every signature; the **graph of where they co-occur** is the map of the economy's fragility concentrations. AI-compute is then one cluster on that map — validated as the epicenter, or *demoted* because the real stress concentration is elsewhere (private credit broadly, CRE, a levered corner nobody's named).

## §3 — The dimensions (the columns): every attribute, every entity

The universal financial-forensic columns (sector-agnostic), filled for every in-scope entity:

**A. Identity & structure** (aliases, jurisdiction, registered agent, full parent/sub/SPV tree). **B. Capital structure** (every instrument — coupon, maturity, seniority, collateral, covenants, every amendment, *and who holds it*; reconstructed for privates from UCC-1s). **C. Financials** (revenue, margins, EBITDA, cash, burn, runway, capex, backlog/RPO; XBRL public, triangulated private). **D. Solvency** (coverage, leverage, covenant headroom + test schedule). **E. Counterparty graph** (customers/suppliers/lenders/guarantors/funders + concentration; directed who-owes-whom edges). **F. Ownership & control** (holders, cap table, **board interlocks**, related-party deals, insider holdings). **G. Market signals** (equity, short interest, options skew, bond/loan price, CDS, rating + outlook). **H. Distress / leading indicators** (signature §2.8 in full). **I. Physical execution** *(where applicable to the sector — capacity claimed vs built, permits, construction, metered throughput; data-center MW/GPU/power-queue is one sector's instantiation)*. **J. Operational reality** (utilization, churn, headcount trajectory, shipment flow, footprint). **K. Relationship/network** (shared auditors/counsel/lenders/agents/**registered agents+addresses** → SPV detection; co-investment; interlocks). **L. People** (rosters, backgrounds, **prior failures**, inter-entity movement, departures). **M. IP** (patents, IP pledged as collateral). **N. Tax/subsidy** (incentive dependence). **O. Real estate/land**. **P. Supply-chain position** (bottleneck dependence, lead times, order backlogs). **Q. Hedges/derivatives**. **R. Legal/regulatory** (investigations, AG/SEC actions, dockets). **S. Historical trajectory** (the **full multi-year** record — the *trend* is the signal). **T. Workforce/sentiment** (reviews, departures, traffic, usage proxies).

## §4 — The sources (where each dimension lives)

EDGAR's **full** taxonomy (10-K/Q, 8-K + EX-10/EX-4 exhibits, **Form 4 insider sales, comment letters, 13D/G, 13F, Form D, NT, S-1/424B, XBRL, DEF 14A**). Off-EDGAR (where the financed long tail lives): **state UCC databases**, **WARN portals**, **PACER + state courts**, **county property records**, **customs/bills-of-lading**, **FINRA TRACE + loan pricing**, **NAIC/BMA statutory + bank call reports**, **USPTO/patents**, **subsidy (Good Jobs First) + lobbying (Senate LDA)**, **state corp registries + registered-agent reverse-lookup**, **rating-agency reports**, **short-seller/activist archives**, **Glassdoor/workforce**, **web/app traffic**, **news/trade-press**. Sector-specific sources are added wherever a *physical-infrastructure* concentration is flagged (for data centers: FERC + the 7 ISO queues, EPA/local permits, GPU marketplaces, BGP/peering, satellite — these are *one sector's* physical layer, not the scope).

- **Realtime X / social, via Grok** (operator-invoked — Ted can call Grok, an AI with live X access): the *earliest* layer, where brokers/insiders/credit-desks/short-sellers post before any filing. Point it at (a) early-distress rumors on the obscure long tail, (b) **triangulating the DARK items** (§7), (c) sentiment/positioning. Everything from it is `rumor`-tier — a lead to corroborate, never standalone evidence, but often *first*.
- **Our own 54GB local corpus + the 18MB published report** — mine what we already have before re-pulling.

## §5 — Rigor methodology (an exhaustive pile of data kept honest)

1. **Entity resolution** — match every alias across SEC/UCC/court/registry/press into one canonical node (name + address + registered agent + officers + cross-refs; record match confidence; keep unresolved candidates, never drop). Without this the graph fragments and the SPV tail stays invisible. 2. **Conflict resolution** — explicit rules on source disagreement: prefer higher tier, **show both**, flag the delta + cause. 3. **Triangulation requirement** — ≥2 independent sources for any load-bearing claim. 4. **Coverage metrics** — % of dimensions filled per entity, % of entities per dimension; "exhaustive" must be *measured*, and the gaps become the next work. 5. **Uncertainty quantification** — every estimate ships a range + method. 6. **Negative-space logging** — **absence is information** (no liens, no queue, no filings = a finding); log the null, never confuse it with "not yet checked." 7. **Pre-registration of estimate methods** — commit the proxy set + method + band *before* computing. 8. **Adversarial red-team pass** — independent agents try to *refute* every load-bearing finding. 9. **Reproducibility** — every cell re-derivable from its cited source. 10. **Bias awareness** — name what the method systematically under-sees (fully-private offshore shells with no US nexus, cash-financed players that leave no record). 11. **Time-alignment** — as-of date everything. 12. **Base-rate anchoring** — every fragility/timing estimate checked against the historical outside view ([base_rates.md](base_rates.md)).

## §6 — The unified data model

One graph (Neo4j-authoritative), schema **entity × dimension × signature × source × timestamp**, every cell tiered (`filing`/`agency`/`market`/`triangulated`/`estimate`/`rumor`) with provenance and the full history each source exposes. The relationship edges (§3-K) make it traversable; the signature scores (§2) make it rankable. The output is **the map of the economy's fragility concentrations**, with each concentration decomposable into its roles and contagion paths.

## §7 — The DARK residual, and deriving it

The only "physics" wall is data that doesn't publicly exist — and **none is left blank; each is estimated from proxies** (tier `triangulated`/`estimate`, pre-registered method + range, §5.7). The four recurring DARK classes (generalizing the AI-case examples): **redacted covenant levels** (reverse-engineer from disclosed cash/debt/interest vs comparable-deal norms; the *amendment behavior* is itself the estimate); **private-contract cancellability** (the disclosed-firm-fraction gap, e.g. GAAP RPO vs headline, is the estimate); **undisclosed real utilization/occupancy** (metered throughput ÷ capacity, marketplace idle-availability, revenue ÷ per-unit benchmark); **private-debt marks** (read-across from public-vehicle marks on comparable credits + where the issuer's own bonds/CDS trade vs par). See [information_edge_map.md](information_edge_map.md).

## §8 — Architecture: one massive parallel pass

- **Acquisition:** one resilient, polite, rate-limited connector per source (§4); politeness rate-limits are the *only* throttle (etiquette/physics, not budget). No UA-spoofing; FOIA/robots respected.
- **Per-entity deep agents on EVERY in-scope entity** (the full ≥$1M economy-wide substrate), thousands of subagents in parallel, each assembling its target's full profile + signature scores. Run time and subagent count are not constraints.
- **Entity-resolution + graph-build** continuously as profiles land (§5.1).
- **Signature scan + concentration detection + contagion traversal** over the assembled matrix → the ranked map of fragility concentrations, each red-teamed (§5.8) and base-rate-anchored (§5.12). **This is where the epicenter reveals itself — AI-compute confirmed or demoted against everything else.**
- **Provenance/coverage gate** — every cell tiered; coverage measured; DARK estimates labeled.

**Case zero (the worked template):** the AI/data-center cluster is the first concentration profiled to depth — its decomposition (levered operators → SPVs → lenders → funds → insurers/end-holders, with the circular NVIDIA financing and the OpenAI/Microsoft demand legs) is the *template* for how any flagged concentration on the economy-wide map gets taken apart. The night's work ([filing_verifications.md](filing_verifications.md), [information_edge_map.md](information_edge_map.md)) is that template, executed once.

## §9 — Sequencing (latency-to-first-signal, NOT triage — everything gets built)

1. **Mine the local corpus + full EDGAR taxonomy** → seed the graph. 2. **Enumerate the ≥$1M economy-wide substrate** (§1). 3. **Run the cheapest broad signatures across the whole substrate first** — leverage, negative carry, concentration, circular financing, the distress leading-indicators (§2) — to get an early fragility map. 4. **Per-entity deep agents across the whole substrate** (§8), continuously until coverage saturates. 5. **The remaining dimensions + sector-specific physical/market layers** wherever concentrations flag. 6. **Grok rumor sweep + the §7 DARK estimates.** 7. **Entity resolution → graph → signature scan → contagion + red-team pass → the ranked output:** *where the economy's fragility actually is.*

## §10 — Scale

The whole economy (floor 7,708, true total an output of §1 — plausibly **low millions** of ≥$1M-footprint entities) × ~**60 dimensions (A–T)** × **8 signature scores (§2)** × ~**25 sources** (incl. Grok + own corpus + the §7 estimates) × the history each exposes = the full matrix, in one exhaustive pass, governed by §5, bounded only by §7 (data that doesn't exist) and §0 (the $1M substance floor). Large, finite, uncapped, no sector prior. This is the engine the repo was always building — pointed, finally, at everything.
