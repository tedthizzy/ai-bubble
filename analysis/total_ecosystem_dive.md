# Total ecosystem dive — every entity, every dimension, one exhaustive pass

**2026-06-13.** A single, one-time, maximum-depth-and-breadth forensic profile of the **entire** AI / data-center / financing ecosystem — every entity, every relationship, every retrievable dimension, assembled once at full depth. Finding the earliest cracks (the small, obscure, private players that fail first) is *one output* of knowing everything, not the limiting purpose. This is not monitoring and not surveillance — the hourly overlay handles real-time if ever wanted. This is one maximal dive.

## Operating principle (binding — see the README's Operating Doctrine)

> **Broad AND deep. Not shallow. Uncapped. Limited only by physics.**

- **Broad** = *every* entity in the ecosystem — no target number, no "top N." The repo's field already holds **7,708 entities / 62,939 deals**; that is the **floor**, not the goal. The true total (with the un-filed long tail of private neoclouds, financing SPVs, queue positions, and counterparties) is **unknown until enumerated and is an OUTPUT, not an input** — plausibly five figures. Any cap below the real total is the resource-constrained error this repo rejects.
- **Deep** = every retrievable dimension for every entity, to the maximum each source allows — the obscure 50-person private SPV gets the same treatment as CoreWeave.
- **Limited only by physics** = the single legitimate stop is that the data *does not publicly exist* (§7) — and even then we *estimate* it from proxies. Effort, volume, breadth, tedium, run time, and subagent count are **never** reasons to narrow, sample, or triage. Thousands of subagents and hundreds of hours for one pass is the expectation.
- **A private entity that files nothing is still profiled in full** from the public-record exhaust it cannot avoid generating (UCC liens → its debt; customs → its hardware; power queues/permits → its buildout; courts → its disputes; job boards/WARN → its headcount; marketplaces/BGP → its utilization). No 10-K required.

## §1 — The entity universe (the rows): enumerate ALL, no cap

Phase one is building the most complete entity list the public record allows — you cannot profile what you haven't found. Layers (per-layer magnitudes are **floors, not caps**):

| layer | rough floor | mostly SEC-visible? | how to enumerate (incl. the dark tail) |
|---|---|---|---|
| Listed cluster issuers | ~12 | yes | have |
| Private / long-tail neoclouds & GPU clouds | 100–300+ | no | DC trackers (DCD/Baxtel/Cloudscene/DataCenterMap/DataCenterHawk), GPU-marketplace provider lists, NVIDIA Cloud-Partner directories, VC round announcements, BGP/ASN registries |
| Financing shells / SPVs | hundreds–thousands | rarely | UCC debtor names, state LLC registries, ABS-trust filings, credit-agreement borrower entities, **registered-agent reverse-lookups** |
| Lenders / private-credit funds | 50–100+ | partly | BDC filings, Form D, LP-disclosure trails, press |
| DC developers / landlords / REITs | 100–200+ | partly | trackers, permit + interconnection-queue applicants |
| Demand leg (labs, hyperscalers, enterprise) | 20–50+ | mixed | known + customer disclosures |
| End-holders (insurers/annuity/pension/Bermuda re) | 50–100+ | yes (statutory) | NAIC blanks, BMA, 13F |
| Hardware & **chip supply chain** | 50+ | mixed | NVIDIA/AMD/Broadcom + TSMC, HBM (SK Hynix/Samsung/Micron), CoWoS/packaging, substrate, optics/networking |
| ODM / cooling / electrical / **EPC construction** | 50–100+ | partly | SMCI/Dell/HPE/Lenovo, Vertiv, switchgear, the firms physically building the sites |
| **Power**: utilities, IPPs, turbine/gen makers | 50+ | partly | ISO queues, PPAs, GE/Siemens turbine order books (lead times), gas suppliers |
| **Service layer**: auditors, deal counsel, underwriters, trustees, collateral agents, RVI/surety insurers | 50–100+ | yes (in filings) | extracted from every deal's signature pages; **auditor/agent concentration is itself a risk dimension** |
| **Key individuals** (execs, directors, founders) | thousands | partly | every filing's officers/directors; track **cross-entity overlaps and prior-failure history** |
| Index/ETF/passive holders | 50+ | yes | 13F, ETF holdings |

## §2 — The dimensions (the columns): every attribute, every entity

**A. Identity & structure** — legal name + all aliases, jurisdiction, registered agent, full parent/sub/SPV tree, CIK/ticker, ASN/IP. **B. Capital structure** — every instrument (notes/loans/DDTLs/converts/ABS/leases), coupon, maturity, seniority, collateral, covenant package, every amendment, **and who holds it** (reconstructed for privates from UCC-1s + lien releases). **C. Financials** — revenue/ARR, margins, EBITDA, net income, cash, burn, runway, capex, RPO/backlog (XBRL for public; triangulated for private). **D. Solvency** — interest coverage, DSCR, leverage, **covenant headroom + test schedule**. **E. Counterparty graph** — customers (+concentration %), suppliers, lenders, guarantors, anchor LPs; directed who-owes-whom edges. **F. Ownership & control** — holders, cap table, **board interlocks**, related-party deals, insider holdings. **G. Market signals** — equity, short interest, options skew, bond price (TRACE), secondary loan price, CDS, rating + outlook + watch. **H. Distress / leading indicators** — insider sales, late-filing notices (NT), covenant amendments/waivers, rating actions, **WARN layoffs**, non-payment suits + mechanic's liens, **UCC foreclosures/releases**, auditor changes, going-concern, dividend cuts, redemption gates, failed/pulled financings, down-rounds, **executive departures**. **I. Physical execution** — announced vs contracted vs operational MW, GPU counts, **interconnection-queue status + withdrawals**, permits, construction (satellite), PPAs, **metered power draw**. **J. Operational reality** — utilization, churn, **headcount trajectory (jobs)**, **chip-shipment flow (customs)**, **marketplace pricing + idle availability**, **BGP/peering footprint**.

**Added for comprehensiveness:** **K. Relationship/network** — shared auditors / counsel / lenders / agents / **registered agents + addresses** (the cleanest SPV-detection signal), co-investment, board interlocks → one graph. **L. People** — executive/director rosters, backgrounds, **prior bankruptcies/failures**, inter-entity movement, departures. **M. IP** — patents, IP pledged as collateral. **N. Tax/subsidy** — state/local incentives, IRA credits, **subsidy dependence**. **O. Real estate/land** — ownership, ground leases, property liens. **P. Supply-chain position** — chip allocation, **HBM/CoWoS dependence**, equipment lead times, order backlogs. **Q. Hedges/derivatives** — power, rate, FX. **R. Legal/regulatory** — investigations, AG/SEC actions, regulatory dockets (beyond civil litigation). **S. Historical trajectory** — the **full multi-year filing history**, not just the latest — the *trend* (deteriorating coverage, lengthening DSO, rising PIK) is often the real signal. **T. Workforce/sentiment** — Glassdoor, employee reviews/departures, web/app traffic, API-usage proxies.

## §3 — The sources (where each dimension lives)

EDGAR's **full** form taxonomy (10-K/Q, 8-K + their EX-10/EX-4 exhibits, **Form 4 insider sales, comment letters/CORRESP, 13D/G, 13F, Form D, NT late-filing, S-1/424B, XBRL, proxy DEF 14A**). Then the off-EDGAR surface where the long tail lives: **state UCC databases** (B/H/K), **state WARN portals** (H), **PACER + state courts** (H/E/R), **FERC + 7 ISO/RTO queues** (I/§1), **state PUC dockets, EPA/ICIS-Air, local building/zoning permits** (I), **customs/bills-of-lading** (J/C/P), **GPU marketplaces scraped** (J/G), **job boards/careers pages** (J/L/T), **BGP/peering/ASN/DNS** (J/A), **satellite (Sentinel/Planet)** (I), **DC trackers** (I/§1), **state corp registries + registered-agent reverse-lookup** (A/K/§1), **FINRA TRACE + loan-pricing** (G), **NAIC/BMA statutory** (E), **USPTO/patents** (M), **county property records** (O), **subsidy trackers (Good Jobs First) + lobbying (Senate LDA/OpenSecrets)** (N/R), **supply-chain trackers (TrendForce/DigiTimes)** (P), **turbine/equipment order trackers** (I/P), **short-seller/activist research archives** (all), **rating-agency full reports** (G), and **news/trade-press** (all).

- **Realtime X / social, via Grok** (operator-invoked — Ted can call Grok, an AI with live X access): the *earliest* layer, where GPU brokers, data-center insiders, credit desks, and short-sellers post before any filing. Point it at (a) **early-distress rumors on the obscure long tail**, (b) **triangulating the DARK items** (rumored occupancy/marks/contract terms — §7), (c) **sentiment/positioning**. Everything from it is `rumor`-tier: a lead to corroborate against a hard source, never standalone evidence — but often *first*.
- **Our own 54GB local corpus + the 18MB published report** — already-acquired EDGAR documents, the 252 debt docs, deal-level contagion paths, the materiality queue. **Mine what we already have before re-pulling.**

## §4 — The unified data model

One graph (Neo4j-authoritative), schema **entity × dimension × source × timestamp**, every cell tiered (`filing`/`agency`/`market`/`triangulated`/`estimate`/`rumor`) with provenance. Each cell holds the **full history the source exposes**, pulled once — the canary is usually a historical delta already in the record (a lien filed-then-released, a queue position withdrawn, an insider sale). The relationship edges (K) make it traversable: any flagged entity instantly shows its blast radius.

## §5 — Rigor methodology (how we keep an exhaustive pile of data honest)

Breadth without rigor is just a bigger pile. The non-negotiable methods:

1. **Entity resolution** — the load-bearing hard problem. Match every alias of every entity across SEC/UCC/court/registry/press into one canonical node ("CoreWeave, Inc." = "CCAC VII Holdco" parent-link = "CoreWeave" UCC debtor = the CIK). Without this the graph fragments and the SPV tail stays invisible. Use name + address + registered agent + officers + filing cross-references; record match confidence; keep unresolved candidates rather than dropping them.
2. **Conflict resolution** — explicit rules when sources disagree (e.g. stockanalysis $35B debt vs 10-K $21.6B): prefer the higher-tier source, **show both**, flag the delta and its likely cause (timing, definition). Never silently pick one.
3. **Triangulation requirement** — any load-bearing claim needs **≥2 independent sources**; single-source facts are labeled provisional.
4. **Coverage metrics** — measure completeness: for every entity, **% of dimensions filled** and at what tier; for every dimension, **% of entities covered**. "Exhaustive" must be a *measured number*, not an assertion — and the gaps become the next work, not a silent omission.
5. **Uncertainty quantification** — every estimate (especially the §7 DARK derivations) ships a **range and method**, never a bare point.
6. **Negative-space logging** — **absence is information.** A neocloud with *no* UCC liens, *no* queue position, *no* customs imports, or *no* filings is a finding (either truly tiny, or financed somewhere we can't see — itself a flag). Log the null explicitly; never leave "absence" indistinguishable from "not yet checked."
7. **Pre-registration of estimate methods** — for each DARK derivation, commit the proxy set, the method, and the error band **before** computing, so the estimate isn't reverse-fit to a desired answer.
8. **Adversarial red-team pass** — independent agents try to *refute* every load-bearing finding and every distress flag (the repo's existing discipline); a finding survives or it's downgraded.
9. **Reproducibility** — every cell re-derivable from its cited source with a one-command rerun; same input → same output.
10. **Bias awareness** — name what the method **systematically under-sees**: fully-private offshore SPVs with no US nexus, cash-financed players that file no liens, anything structured specifically to avoid public record. The streetlight effect is a known limitation, characterized rather than hidden.
11. **Time-alignment** — as-of date every datum; never compare a Q1 mark to a June price without flagging the gap.
12. **Base-rate anchoring** — every distress/timing estimate anchored to the historical base rates ([base_rates.md](base_rates.md)) so the inside view is checked against the outside view.

## §7 — The DARK residual, and deriving it

The only "physics" wall is data that doesn't publicly exist. From [information_edge_map.md](information_edge_map.md) the residual is four items — and **none is left blank; each is ESTIMATED from proxies** (tier `triangulated`/`estimate`, with a range and pre-registered method, §5.7):

| DARK item | derive/estimate from |
|---|---|
| **Covenant headroom level** (redacted threshold) | implied DSCR/leverage from disclosed cash/debt/interest/EBITDA vs rating-agency-cited norms (~1.26x base DSCR on comparable deals); the *behavior* is the estimate — 3 amendments in 8 weeks + DSCR test postponed to 2027 + *unlimited* equity cures = "could not pass it now." |
| **Contract cancellability** (survives funding failure?) | the **RPO-vs-headline gap is the firm-fraction estimate** (IREN $710M of ~$13B ⇒ ~95% soft); cross-read comparable contract descriptions (SpaceX "terminable after 3mo"; Moody's "non-terminable for convenience" on Meta — silence on OpenAI's is informative). |
| **Real occupancy %** | **metered power draw ÷ installed capacity**; marketplace idle-availability; revenue ÷ revenue-per-occupied-MW; contracted-vs-operational MW gap; BGP/traffic footprint — triangulated to a band. |
| **Private-debt marks** | **read-across from public BDC marks on comparable credits**; where CoreWeave's own **bonds/CDS** trade vs par; public DC-ABS spreads; secondary-loan quotes; redemption-gate behavior (gating ⇒ soft marks). |

## §8 — Architecture: one massive parallel pass

- **Acquisition:** one resilient, polite, rate-limited connector per source (§3); politeness rate-limits are the *only* throttle (etiquette/physics, not budget). No UA-spoofing; FOIA/robots respected.
- **Per-entity deep agents on EVERY enumerated entity** (floor 7,708 + the SPV/queue layers), thousands of subagents in parallel, each assembling its target's full profile across every source. Run time and subagent count are not constraints.
- **Entity-resolution + graph-build** continuously as profiles land (§5.1).
- **Anomaly + contagion pass** over the assembled matrix → ranked findings (where the first cracks already are), each red-teamed (§5.8) and base-rate-anchored (§5.12).
- **Provenance/coverage gate** — every cell tiered; coverage measured (§5.4); the DARK estimates labeled (§7).

## §9 — Sequencing (latency-to-first-signal, NOT triage — everything gets built)

1. **Mine the local corpus + full EDGAR taxonomy** (cheap, already-have / one connector) → seed the graph.
2. **Enumerate the full long-tail universe** (§1) — can't profile the unlisted.
3. **The earliest broad distress detectors across all entities** — UCC liens, WARN, queue withdrawals, non-payment litigation/mechanic's liens, customs stoppages, marketplace fire-sales, insider sales, executive departures.
4. **Per-entity deep agents across the whole population** (§8), continuously until coverage saturates.
5. **Physical layer** (satellite, permits, metered power) + **market layer** (TRACE, CDS, secondary marks) + **service/people/supply-chain/IP/tax/RE layers** (§2 K–T).
6. **Grok realtime-X rumor sweep** + the **§7 DARK estimates**.
7. **Entity resolution → graph → anomaly + contagion + red-team pass** → the ranked output.

## §10 — Scale

The full ecosystem (floor 7,708, true total an output of §1) × ~**60 dimensions (A–T)** × ~**25 sources** (incl. Grok + own corpus + the §7 estimates) × the **history each exposes** = the full matrix, in one exhaustive pass, governed by §5 and bounded only by §7. Large, finite, uncapped. This activates at full depth the WS5 "scale-out" that [ROADMAP.md](../ROADMAP.md) gated — now ungated, uncapped, rigor-governed, and pointed at the whole ecosystem rather than the dozen visible beams.
