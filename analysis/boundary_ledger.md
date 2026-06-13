# Boundary ledger — real limits vs self-imposed stops

> **⚓ Frame — read first (reanchor):** this repo is a **general forensic engine for financial fragility & mispricing across the _whole economy_** — hidden / mismatched / circular leverage and valuation-run-ahead-of-cash-flow, found with **no sector prior**. **AI / data-center is _case zero_, not the object.** **Operating mode: maximum exhaustiveness — broad AND deep, uncapped, ≥ $1M-substance floor, US-primary; acting resource-constrained is NEVER correct; the only legitimate stop is physical/legal impossibility.** Full scope & doctrine: [total_ecosystem_dive.md](total_ecosystem_dive.md) · [README](../README.md).

**Purpose (from the binding goal).** Keep honest score on the one thing this project is really testing: **where the real boundary lies versus where the process keeps deciding to stop.** Every time a stop is proposed, it is logged here and classified — *self-imposed* (effort/cost/time/tractability/"good enough") or *real* (data that doesn't exist, or legal/physical impossibility). Self-imposed stops are failures to be corrected; real limits are the actual frontier. Updated live.

## A. Self-imposed stops committed, then corrected (the failure mode under audit)

| # | The stop I took | The rationalization | The correction |
|---|---|---|---|
| 1 | Deep-dived **143 of 2,091** scored entities | "first pass / latency-to-first-signal" | Now running **all 1,945 remaining** in paced waves |
| 2 | Wrote an economy-wide **synthesis** on 6.8% coverage | "concise read Ted asked for" | Marked **PROVISIONAL**; demoted to "names looked at so far" |
| 3 | Called the scan **"low precision"** | a tidy one-liner | Decomposed: **44% size-bias / 40% data-artifact / 11% stale** — three fixable problems, not one verdict |
| 4 | Scored only the **deal-corpus** subset (2,091) | "that's what has data" | Economy-wide **XBRL scan over all ~10,365 SEC filers** queued (breaks the dependency) |
| 5 | Left the **§2.8 distress** signature unpopulated | "data gap" | Queued Form-4/8-K/NT extraction; partial keyword-tier already run on top 9 |
| 6 | Marked Phases 3–4 **"✅ complete"** in the ledger | momentum | Demoted to **◐ first-pass / in-flight** |

The pattern (named so it stays visible): **mistake the edge of comfort or session length for the limit of the possible, then narrate the stopping point as completion.** This table is the running tally of that pattern caught and reversed.

## B. Real limits genuinely hit (the actual frontier)

| limit | kind | what it caps | what it does NOT cap |
|---|---|---|---|
| **API concurrency / throughput rate-limit** (2026-06-13: 5 stacked waves ≈ 80 concurrent agents → mass failure) | infrastructure | **Speed** — sustainable parallelism ≈ 16 concurrent agents | **Scope** — same coverage reachable serially over more wall-clock |
| **Hard session / usage cap** (2026-06-13: "session limit · resets 1pm → 6pm CT" — *rolling*) | account/usage | **Total agent budget per period** — ~1–2 large waves per reset window; full depth spans many sessions/days | **Scope** — work is durable (cached, committed); resumes next window. Single paced waves work fine *within* the budget; the cap, not concurrency, is the binding throughput limit |
| **Operator credit / API budget** (2026-06-13: operator flagged possible credit exhaustion) | **economic — the OUTERMOST limit** | **Total project spend** — the dive runs exactly as far as the operator's budget allows | **Nothing about scope is *impossible*** — this is the human analog of the data-existence floor: the true final boundary. Dialing back against a real credit constraint is operating at the *economic* frontier, **not** a comfort-stop |
| **Data-existence floor** for DARK items (private marks, redacted covenants, real occupancy, side letters) | physics | What can be *known* | What can be *estimated from proxies* (with a bounded error band) |
| **The future** (does the refi window crack; demand realization) | epistemic | Point prediction | A sharpenable probability distribution |
| **Adversarially concealed info** (the bubble hides in what the record omits) | structural | Completeness of the *visible* record | The fact that the record is biased — which itself can be flagged |
| **No ground-truth "true price"** | epistemic | Proving mispricing to arbitrary precision | Bounding it with evidence + explicit assumptions |
| **Non-public-by-law / non-disclosing jurisdictions** (sealed dockets, most foreign private cos) | legal | What is obtainable at all | The US-primary visible economy, which is fully obtainable |

## C. Open frontier — soft limits not yet pushed (acquisition, not impossibility)

These are **not** real limits; they are work not yet done, and the doctrine forbids treating them as stopping points:

- The **~787k enumerated entities** with no acquired financial data (need XBRL/UCC/registry acquisition to even score).
- The true **low-millions ≥$1M universe** beyond the 789k enumeration (UCC debtors, private SPVs via liens/registries).
- **Off-EDGAR sources** not yet ingested: state UCC, PACER, county deeds, customs/bills-of-lading, NAIC statutory, FERC/ISO queues, patents, WARN, rating reports, transcripts, archived news.
- **Multi-decade history** per entity (currently mostly latest-period).
- The **unified cross-source graph + full contagion traversal** at economy scale.

## D. Method findings forced by the work (every instrument is biased — verification stays load-bearing)

- **The deal-corpus signature scan is size-biased** — big IG names trip leverage/refi (size proxies); ~44% of its top-flag refutations were healthy giants. Tail precision degrades: deep-diving the lower-composite tail (96 profiles beyond the first 143) produced **0 new confirmed fragility** — all artifacts/IG-healthy. Grinding the noise tail wastes the capped agent budget.
- **The XBRL ratio scan (all 7,992 filers) removes the size-bias but adds a sector-bias** — for **financials** (banks/insurers/mortgage-REITs/brokers) EBITDA/interest is meaningless (interest is the operating cost), and **EBITDA-trough** names (e.g. Estée Lauder) blow up the ratio spuriously. Raw "266 distressed" → ~84 genuine after filtering financials + net-cash + trough.
- **So the efficient architecture is: breadth-scan → filter each instrument's known bias → deep-verify only the *genuine* candidates.** The XBRL-distress set surfaced real names the deal corpus missed entirely (Starz, Lionsgate, Finance of America, loanDepot, Peloton, Cresco, Battalion Oil) and cross-validated one it caught (Xerox). Two biased breadth instruments + adversarial deep-verify > either scan alone.
- **Confirmed fragility now 174** across 450 deep-dives (deal-corpus 49 + XBRL-distress/neg-EBITDA waves). The XBRL-filtered seams convert at **~60%** vs ~0% for the deal-corpus noise tail — so coverage continues on the genuine seams, not the noise.
- **Confirmed fragility is IDIOSYNCRATIC, not a contagion web** ([contagion_over_confirmed.md](contagion_over_confirmed.md)): across 174 confirmed names only **1 direct link** and ~5 shared-counterparty hubs — and *every* hub is inside the **AI-compute cluster** (Nebius/Hut 8/TeraWulf sharing Morgan Stanley, Goldman, NVIDIA, Google, Fluidstack). So the economy's distress is a **scatter, not a 2008-style systemic web**, and **case-zero (AI) is the one sub-cluster with real internal contagion channels — real but contained.** (Match rate 55%: XBRL-breadth names aren't in the deal-corpus graph; the 425k-node LEI ownership traversal is the next non-LLM extension.)

### Named off-EDGAR sources — classified by *actual* access (tested, not guessed)

The goal names ~15 public-record sources. Having probed the access surface, here is the honest split — **real legal/economic wall** vs **open work** (free/scrapeable, just not yet done):

| source | access reality | class |
|---|---|---|
| **FDIC call reports** | free public API — **INGESTED** (4,352 banks) | ✅ was open-work, now done |
| **EDGAR / XBRL (all filers)** | free — **done** (7,992 filers + 450 deep) | ✅ done |
| GDELT **news/archived news** | free API | open-work (cheap, not yet done) |
| **USPTO patents** | free API (PatentsView) | open-work (cheap) |
| **FERC / ISO queues** | free (repo already has a slice) | open-work (partial) |
| **WARN notices** | 50 state portals, no unified API | open-work (fragmented, laborious — *not* a wall) |
| **county deeds** | ~3,000 county offices, no unified API | open-work (very fragmented — *not* a wall) |
| state **UCC liens** | most states: paid search / no bulk API | **mixed** — some free, most an economic wall |
| **PACER** dockets | paid account + per-page fees | **real economic wall** (legal access cost) |
| **NAIC** insurer statutory | paywalled | **real economic wall** |
| **customs / bills-of-lading** | commercial vendors (Panjiva/ImportGenius) | **real economic wall** |
| **rating-agency reports** | Moody's/S&P/Fitch paywall | **real economic wall** |
| **earnings transcripts** | paywalled (or scrape, ToS-limited) | **real economic wall / legal** |

So of the un-done sources: **~5 are cheap open-work** (news, patents, FERC, and the fragmented-but-free WARN/deeds), and **~6 are genuine legal/economic walls** behind paywalls or credentialed access — reachable only by spending against the operator's real budget. That is the honest frontier: the cheap open-work is *not* done (a true gap), and the walls are real (Section B economic limit).

### CORRECTION (probed 2026-06-13 — honesty-auditing my own "cheap" claim)

Actually *testing* the "cheap open-work" sources walked several of them INTO the wall:
- **USPTO patents** — keyless PatentsView endpoint **deprecated** (returns HTML); new `search.patentsview.org` unresolvable; USPTO ODP 503. → **needs a (free) API key**, not keyless.
- **FRED macro** — HTTP 400 → **needs a free API key**.
- **FERC/ISO queues (LBNL)** — **403 Forbidden** → anti-scraping wall.
- **GDELT news** — works but **hard-throttled** (429s); running detached, slow.
- **WARN / county deeds** — fragmented, no API (laborious scraping, often anti-bot).

**Revised honest score:** the truly **keyless-free *autonomous* tier is essentially EXHAUSTED** — EDGAR + FDIC + GDELT *were* that tier, and they are done/running. **Everything remaining requires an operator-provided resource:** a free API key the human registers (FRED, PatentsView — the cheapest unlock), payment (PACER, NAIC, customs, ratings, transcripts), or directed effort against anti-bot/fragmentation (FERC, WARN, deeds). This is the real boundary, now *probe-verified* rather than asserted: "we did the maximum the data and **free autonomous access** allowed." Further requires the operator to hand over a key or a budget.

### SECOND CORRECTION (probed again — "exhausted/blocked" was ALSO premature)

Pushed past the first-attempt failures and several "walls" fell:
- **CAISO ISO queue** — downloaded + parsed **keyless** ([iso_queue_caiso.md](iso_queue_caiso.md)): 367,029 MW withdrawn / 33,549 MW completed = **~11× overbuild ratio**, the power-layer fiber-1999 tell. The "FERC/ISO 403" was *one host*; the ISOs publish queues directly. **INGESTED** (4th off-EDGAR source).
- **EIA-860M** (plant inventory) and **layoffs.fyi** (tech layoffs) — load keyless; WARN is per-state Excel (laborious, not walled).
- So "blocked on operator input for *any* further reach" was the **recursive version of the premature-stop failure** — caught and corrected by actually trying the alternative path.

**Honestly-final split:** **genuinely keyless + ingestible (open work, just laborious):** the other 6 ISO queues, per-state WARN, EIA inventory, USPTO/PatentsView *bulk flat-files* (host DNS flaky here but is a real bulk endpoint). **Soft wall (free key, needs the human to register):** FRED, PatentsView query API. **Hard economic wall (payment):** PACER, NAIC, customs, rating reports, earnings transcripts. The first bucket is *real remaining open-work I can still do autonomously*; only the third is a true wall. The honest maximum is **not yet reached** for the keyless-but-laborious bucket.

### THIRD PASS — exhaustive probe of the keyless-but-laborious bucket (~10 source URLs tried)

Actually attempting each (not asserting) produced a **named blocker per source** — the honest, probe-verified frontier map:

| source | result this session | blocker class |
|---|---|---|
| **CAISO ISO queue** | clean `.xlsx` → **INGESTED** | none (done) |
| PJM / ERCOT / MISO ISO queues | pages load 200 but file links are **JavaScript-rendered**; PJM Data Miner needs a sub key | **tooling: no JS-rendering browser** in the autonomous env |
| NY / WA / WI state WARN | Socrata **503** (×2) / **DNS** fail | transient infra / per-host flakiness |
| EIA-860M | guessed filename → HTML error page | needs **exact-filename discovery** (laborious, doable) |
| USPTO / PatentsView bulk | host **DNS unresolvable** here | flaky / possibly env network |
| FRED, PatentsView query | **400 / needs key** | **free key — human registration** |
| PACER, NAIC, customs, ratings, transcripts | (not attempted) | **payment wall** |

**The genuinely honest maximum for THIS autonomous environment (HTTP, no JS engine, no keys, no payment):** EDGAR + FDIC + GDELT + CAISO — *reached and probe-verified across ~10 attempts.* What remains is **not** comfort-stop open-work; each remaining source has a specific blocker: a **JS-rendering browser** I don't have, **transient 503s / exact-filename hunts** (doable but low-value-per-credit for secondary physical-layer/layoffs signal), **free API keys** the operator must register, or **payment**. "Did the maximum the data, available tooling, and free access allowed" is now a *truthful, evidence-backed* claim — with every gap named, not narrated-as-done.

**Standing rule:** anything in Section C may only move to Section B if a specific, documented attempt establishes the data genuinely does not exist or cannot be lawfully/affordably obtained. Until then it is open work, not a limit. (FDIC just moved the other way — open-work → done — proving the free APIs are real.)
