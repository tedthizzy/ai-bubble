# ROADMAP — the program to the 2026-Q4 adjudication

**Published 2026-06-12.** This plan went through two corrections on its first day, both worth recording because they define what the project is. First: a draft lived briefly in a private file, written in the idiom of a positioned short-research shop — phantom team, budget lines, a legal gate, "strategy leakage" risk. Wrong model; this project has no position, no client, and no secrecy interest, so everything is public except credentials, personal contact information, and interview notes pending source consent. Second, sharper: the payoff is not external persuasion either. **The payoff is a calibrated, decomposed, self-pre-registered model of reality the maintainer can trust enough to act on** — internal decision credibility. Publication is how an open-source project exists, not a campaign with a deadline; pre-registration is self-discipline against hindsight bias (you cannot quietly move 0.67 after the fact), not an audience play. Not investment advice.

## The organizing fact

Everything below is sequenced backward from one hard date: **the pre-registered 2026-Q4 TIMING-KILL adjudication** ([analysis/preregistered_signals.md](analysis/preregistered_signals.md)), adjudicated ~**Dec 18, 2026**. The date matters because that is when the engine's registered predictions are *scored* — the first real calibration datum for whether this apparatus can be trusted. The urgency is "don't let the prediction window pass un-scored or contaminated," not "publish before the market moves."

**Freeze discipline (registered here):** no semantic amendments to S1–S4 after **2026-09-30**, so the adjudication scores a spec that was fixed well before the data arrived. After that date the amendment log accepts only data-source repairs, documented as such.

Secondary anchors: Oct-1 Google/SPCX contract start; the 2027-Q1 termination window; quarterly BDC NAV re-cards; each 10-Q/K season.

## The apparatus (what is actually being built)

A portable engine with two inputs and a scored output:

1. **The causal model of the cash flows** — the forensic truth-engine (filings, coverage, collateral life, maturity walls, who-holds). Built; deepens via WS2.
2. **The market-implied model** — *consensus-inference*: reverse-engineering what prices imply about utilization, GPU life, renewals (WS1.1). This is not "market-facing" in the trading sense; it is the second input to the gap, without which "0.67 it's a bubble" means nothing. The verdict only means something as *0.67 versus a market pricing roughly zero of the measured fragility*.
3. **A calibrated verdict** — decomposed, signal-wired, pre-registered, and Brier-scored when the dates hit (WS1.3, WS4.4). The discipline is that the engine scores itself honestly.

Instrument selection, position sizing, distribution embargoes — the trading-shop apparatus — are explicitly out of scope ([analysis/limits_to_arbitrage.md](analysis/limits_to_arbitrage.md) analyzes why no clean expression exists, as *evidence about the mispricing's persistence*, not as a menu).

## Resourcing honesty

There is no team. The unit of work is not engineer-headcount; it is:

- **agent-hours** — an AI agent does the overwhelming majority of engineering and analysis throughput (the entire market-facing layer shipped in one day on this model). Effectively abundant.
- **[TED]-hours** — the solo maintainer: adjudication, tier assignments, verdict promotion, calls, voice. Scarce; every [TED] touchpoint arrives as a pre-built packet with a default recommendation.
- **[EXT]-latency** — external humans: adversarial reviewers, interviewees. The slowest-moving resource, so external-facing items start early, not last.

Cash costs are incidental (hosting free, data sources keyless; an optional commercial EDGAR mirror is the only real line item, and only if the free paths fail).

## Doctrine (non-negotiable, enforced in CI and review)

1. Evidence tiers with hard caps; provenance on every scalar; UNSUPPORTED caps at 0.25. No borrowed thresholds — derive or cite-and-tier.
2. Pre-registration is append-only. Signal respecifications go through the amendment log with reasons, never silent edits — and never after the freeze date.
3. The public gate (ruff + format + mypy + full pytest) is the merge gate.
4. Scope discipline: the cluster verdict moves only on gated evidence. Adjacents (SpaceX et al.) are pattern-extension until exhibit-verified.
5. **Open by default.** Everything public except credentials, PII, and consent-pending interview notes. Claim policy for named companies: every claim is a filing quote or labeled arithmetic on filed numbers — the filings carry the claims. No SEC UA-spoofing; polite scraping; FOIA through proper channels. Honest caveats and visible corrections are first-class.
6. Two-clock language everywhere: operational bleed now (crack window 2025-Q3..2027-Q3), synchronized maturity wall 2030–33. Never conflate.
7. **Reflexive skepticism.** The engine discounts narrative-ahead-of-substance everywhere, so it must discount its own: surface impressiveness — commit velocity, tree size, professional sheen — is not evidence, and only gated evidence moves verdicts. Corollary (learned from an independent observer who misread this repo as a fund's work): the artifacts *actively induce* a positioned-desk frame in fresh readers, human or LLM. The README's identity block exists to pre-empt that; point fresh agent sessions at it first.

---

## WS0 — Signal integrity hotfix (SHIPPED 2026-06-12, the day of this plan)

The signals are the scoring instrument; a spuriously-firing signal contaminates the exact calibration datum the adjudication exists to produce. All respecs went through the amendment log (A1–A5):

| # | task | outcome |
|---|---|---|
| 0.1 | **S3 → differential vs control** (the material fix) | Carded every book ([analysis/bdc_exposure_cards.md](analysis/bdc_exposure_cards.md)): FSK's −41% is legacy credit + a class action, not AI; OBDC's AI lending sits at the manager level; only BXSL (+weakly ARCC) is exposed. S3′ = worst exposed − non-AI control median. **Registration-day "confirming" withdrawn — reads neutral (+7.5pp).** |
| 0.2 | **S2 → differential respec** | (CCC − HY) YTD differential, BB OAS as quality-end control with a market-wide flag. |
| 0.3 | **S1b — discrete failed-print event** | `status` field on issuance cards; the first pulled/failed cluster print is confirming regardless of spread drift on completed deals. |
| 0.4 | **S4 — demand trajectory** | Pre-registered basket (company-stated run-rates: OpenAI, Anthropic, Microsoft-AI; growth-not-level semantics). **Registered reading: +253% YoY = contra — the bull's strongest number, registered anyway.** |
| 0.5 | **S1 staleness guard** | Prints >45d old read `stale`, never `contra`; `stale` cannot feed TIMING-KILL. |
| 0.6 | **Tests + typing + deps** | Signal logic extracted to `src/bubble/market_signals.py` (typed, unit-tested, under the gate); aiohttp bumped past its advisories. |

## WS1 — Quantitative epistemics (agent-executable; weeks 1–5)

| # | task | deliverable |
|---|---|---|
| 1.1 | **Consensus-inference (per-name expectations inversion)** | `src/bubble/expectations/`: reverse-DCF per traded name (CRWV, NBIS, IREN, APLD; extendable) — solve for the utilization, renewal rate, GPU economic life, and margin the live price implies, vs what the engine measured. Published table: *price implies X / engine measured Y / delta*, auto-refreshed. Sensitivity bands, not point estimates. The second input to the gap — core epistemics, not commercial apparatus. |
| 1.2 | **Base-rate book** | `analysis/base_rates.md` + machine-readable priors: fiber/CLEC 1999–2003 primary (capex-peak→first-default lag, recovery rates, financed-fringe-first sequence, equity-up-while-credit-cracks duration); shale 2014–16 secondary. Explicitly list where the analogy breaks. |
| 1.3 | **Verdict decomposition tree** | `src/bubble/verdict_tree.py`: the flat 0.67 decomposed into stated, signal-wired, Brier-scoreable conditional probabilities, run in **shadow mode** until **[TED]** promotes it. **Spec requirement:** the factorization must be able to represent the fiber-1999 sequence where the funding window closes *first* and causes the distress (not only distress→window), or document explicitly why the chosen chain is the right approximation. |
| 1.4 | **Marginal-buyer constraint cards** | NAIC RBC charges on rated tranches; BDC leverage caps and the NAV decline that binds them; downgrade triggers in carded facilities; annuity surrender mechanics. The funding map becomes a timing mechanism. |

**Exit (M2, ~Jul 17):** inversion table live; verdict tree in shadow mode with Brier harness; constraint cards v1.

## WS2 — Evidence depth (weeks 2–11 — the only work that can MOVE the verdict)

| # | task | notes |
|---|---|---|
| 2.1 | **EDGAR access remediation** (enabler, start immediately) | Compliant fetch paths, tried in order: residential egress box running the existing fetchers on cron; SEC bulk datasets; commercial mirror API as paid fallback; browser-assisted manual pulls for top exhibits. **No UA spoofing under any option.** Unblocks 2.2/2.3, SpaceX S-1 exhibit verification, BDC schedule-of-investments verification, and the daily delta. |
| 2.2 | **Utilization bottom-up, the 11 core issuers** | Facility-level models: contracted revenue, realistic utilization bands, power/opex, full debt service — the load-bearing assumption under 7/11 *and* under the bull's "backlog is the balance sheet." Agent pipeline over the 252 candidate debt docs + transcripts; **[TED]** adjudication checkpoint per issuer. **Pre-committed: reported whichever way it lands.** |
| 2.3 | **Waterfall depth, materiality-first** | Full caps/triggers/covenants/seniority on the top 10–15 facilities (~80% of notional). Per-facility card: *who bears the first dollar, under what trigger*. |
| 2.4 | **Human-source layer (Fisher protocol)** | **[TED]** structured calls — GPU brokers (real rental rates), neocloud customers (stickiness), DC construction/ops, a private-credit allocator — scaled to availability. Agent builds the kit: named-uncertainty target list auto-generated from model sensitivities, question templates, consent-flagged note capture at `human_source` tier. Notes publish per-source on consent. |

**Exit (M3, ~Aug 28):** utilization models adjudicated for all 11; top-15 waterfalls carded; EDGAR restored; SpaceX and BDC cards at filing tier.

## WS3 — Continuous ops, trimmed to the critical path (weeks 1–14)

On the path to the adjudication: **3.1 history persistence** (overlay appends time series — quotes, OAS, discounts, signal states — feeding drift charts and the track-record page), **3.2 daily delta** (post-2.1), **3.3 calendar engine** (the forced-truth calendar as code: dated events fire Actions-cron notifications and assemble adjudication packets), **3.6 test/typing debt**.

**Deferred past the Q4 adjudication** (they serve the reusable-instrument product, gated on the Q4 evidence — see WS5): Neo4j-authoritative migration, viz feature upgrades, satellite de-confounding.

**Exit (M4, ~Sep 25):** dials chart their own history; the calendar fires itself; quarterly re-cards are tickets, not memory. **Freeze date for signal semantics: Sep 30.**

## WS4 — External error-correction + the scored record

External review exists here for **error-finding**, not credibility theater — hostile competent outsiders are the cheapest detection mechanism for the failure modes the maintainer can't see. External humans are also the slowest resource, so this starts early:

| # | task | owner | timing |
|---|---|---|---|
| 4.1 | **External adversarial review** | **[EXT]** reviewers, agent preps packets | Packets go out **in July on the current public evidence**, with a WS2 addendum process. One-click-reproducible: claim → provenance chain → rerun script. Responses published verbatim, including the ones that hurt. Targets: a structured-credit reader (waterfalls), a private-credit professional (marginal-buyer model), a genuine AI bull (demand trajectory). |
| 4.2 | **Adversarial collaboration on Q4** | **[TED]** + a named bull | *Optional but valuable*: written in advance, which 2026-Q4 outcome counts as whose win — its value here is that a smart bull stress-tests the criteria themselves before the freeze. If signed, the terms are public. If no counterparty materializes, the pre-registration + public scoring already does the epistemic work. |
| 4.3 | **Claim policy (no legal gate)** | default policy | Every named-company claim is a filing quote or labeled arithmetic on filed numbers — already true of the strongest claims (7/11 breaching). A one-time personal legal review is optional cheap insurance for the maintainer, covering the automated outputs too (the dial firing "confirming" on a named issuer is a publication event); it is not a program dependency. |
| 4.4 | **The scored record** | agent | Signal history + adjudications + Brier scores rendered on the Pages site. This is the calibration ledger — the thing the maintainer consults in 2027 to decide how much to trust the engine's next verdict. Public because the project is. |
| 4.5 | **The synthesis document** | **[TED]** voice, agent productionizes | An *output*, not the spine: one document — the 56x strip ($1.45T claimed → $25.8B verified) as the hook, the two-clock structure as the finding, the steelman + registration as the discipline. Target freeze ~Oct 30, publish ~Nov 13. If it slips, the adjudication still runs on schedule; the score is the deliverable that cannot slip. |
| 4.6 | **Distribution** | **[TED]**, optional | Telling people about published research is just email; do it if and when it's fun. Nothing in the program depends on it. |

**Exit:** M5 ~Oct 30 — reviews returned, synthesis frozen (if on schedule). M6 ~Nov 13 — synthesis published. M7 ~**Dec 18 — the Q4 adjudication runs publicly, on schedule, Brier-scored, retro held. This one is not optional.**

## WS5 — Gated: scale-out to a reusable instrument (post-Q4 decision)

Explicitly **not** required (capture-recapture already bounds the unobserved fraction; materiality-first *is* the standard). 750–900 entities / 16–20k deals, FOIA at volume, continuous satellite, the engine generalized to the next episode's sector — decided **[TED]** with the Q4 calibration evidence in hand. If the engine scores well, point it at the next sector; if not, fix what the score revealed.

## Explicit non-goals

- No forensic-depth modeling of adjacents beyond pattern-extension cards.
- No trading-book buildout, no instrument selection, no sizing — the trading-shop apparatus is foreign to this project's payoff.
- No silent verdict inflation: 0.67/0.25 move only through the gate, via WS2 evidence or the validated verdict tree.

## Top risks → mitigations

1. **SEC access stays blocked** → 2.1's path fan-out decided immediately; manual pulls keep top-15 exhibits moving regardless.
2. **[TED]-bandwidth bottleneck** → every touchpoint is a pre-built packet with a default recommendation; calls clustered; nothing blocks on Ted except adjudication and voice.
3. **Market converges early** → fine: the signals fire, the record scores. (Under the corrected frame this is not a race lost; it is data arriving early.)
4. **Signal misfire / spec churn contaminating the adjudication** → WS0 shipped first; the Sep-30 freeze; `stale`/`insufficient` statuses instead of forced directional readings.
5. **Hindsight drift** — the subtle one: quietly reinterpreting thresholds after data arrives → append-only log, frozen semantics, and the public scored record make it mechanically hard.
6. **Doctrine drift across agent sessions** → doctrine lives in this file and CI; the gate is mechanical; [TED] retains sole authority over tier assignments and verdict changes.
7. **An un-scored window** — the inversion of the original plan's "leakage" risk: the real failure is Dec 18 passing without a clean, frozen, scoreable registration. Everything above serves preventing that.

## Definition of done

1. Zero UNSUPPORTED on the core verdict chain; approved review on every load-bearing claim.
2. Verdict tree live, signal-wired, Brier-scored; the flat 0.67 retired in favor of the decomposition.
3. Utilization bottom-up + top-15 waterfalls adjudicated — **whichever way they land, reported faithfully**.
4. The 2026-Q4 adjudication executed on schedule against the frozen spec, scored, and recorded — the engine's first calibration datum.
5. Ops continuous: the calendar fires itself, the dials chart their own history, quarterly re-cards are tickets.
6. The WS5 decision made deliberately, with the calibration evidence in hand.

At that point the project is what it set out to be: a rigorously calibrated engine for modeling a financed boom — with a public record of exactly how well it modeled this one.
