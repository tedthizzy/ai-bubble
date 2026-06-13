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
| **Hard session / usage cap** (2026-06-13: "You've hit your session limit · resets 1pm CT") | account/usage | **Total agent budget per period** — full coverage of ~1,800 deep-dives + verification spans multiple sessions/days | **Scope** — work is durable (cached, committed); resumes next window. Single paced waves work fine *within* the budget; it was the daily cap, not concurrency, that stopped the run |
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
- **Confirmed-fragility set is stable at ~49** across 239 deep-dives; the marginal yield of more *deal-corpus* tail is ≈0, but the *XBRL-distress* tail is still yielding new genuine names — coverage continues there, not in the noise.

**Standing rule:** anything in Section C may only move to Section B if a specific, documented attempt establishes the data genuinely does not exist or cannot be lawfully obtained. Until then it is open work, not a limit.
