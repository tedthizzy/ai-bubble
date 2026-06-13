# Phase 3 — deep-agent forensic profiling of the flagged set (ready, gated)

> **⚓ Frame — read first (reanchor):** this repo is a **general forensic engine for financial fragility & mispricing across the _whole economy_** — hidden / mismatched / circular leverage and valuation-run-ahead-of-cash-flow, found with **no sector prior**. **AI / data-center is _case zero_, not the object** (the method is sector- and era-agnostic — cf. fiber 1999, shale 2014). **Operating mode: maximum exhaustiveness — broad AND deep, uncapped, ≥ $1M-substance floor, US-primary (international by connectedness-to-core × data-accessibility); acting resource-constrained is NEVER correct; the only stop is physics (data that doesn't publicly exist → estimate it from proxies).** Full scope & doctrine: [total_ecosystem_dive.md](total_ecosystem_dive.md) · [README](../README.md).

**As of 2026-06-13.** Phases 1–2 produced the economy-wide fragility map and its sector view from data already on disk. Phase 3 takes the flagged concentrations down to per-entity forensic depth. **The harness is built and ready; execution is GATED on (a) Ted's storage-capacity clearance and (b) an explicit go**, because the fan-out is large and its confirmation step writes filings to disk.

## What runs

- **Targets:** [phase3_targets.json](phase3_targets.json) — **143 entities** selected from the map: **49 canaries** (small/obscure, fail-first — the priority tier), **57 beams** (≥$20B, systemic-if-they-break), **37 mid**, plus **8 banks on a separate duration/deposit axis** (their "debt" is deposits/FHLB, not corporate leverage). The full canary universe is **1,078**; this first pass takes the top 50 by canary-score and the tail extends from there — no hard cap in principle.
- **Harness:** [`scripts/workflows/phase3_deep_dive.workflow.js`](../scripts/workflows/phase3_deep_dive.workflow.js) — a `pipeline(profile → adversarial-verify)` so each target's skeptic fires the moment its profile lands (canaries clear before beams finish). One agent assembles the forensic profile; a second independent agent tries to **refute** the fragility thesis (defaults to false-positive unless real fragility survives). Both emit validated structured output.

## Hard rules baked into the agents

- **No agent fetches `sec.gov`.** Agents research via web/public knowledge and list the exact filings/exhibits needed; the **orchestrator pulls EDGAR locally** with the declared UA (never spoofed). This is the disk-touching step that waits on storage.
- **No sector prior, confirm-don't-assume.** Each entity is judged on its own cash-flows-vs-obligations; being flagged is a hypothesis to verify or reject, not a conclusion.
- **Every load-bearing claim tiered** (`filing_verified` … `rumor`); gross facility size distinguished from net debt; known data artifacts (bank deposits as debt, penalty-rate coupons, double-counted notional) called out.

## Sequencing (on go)

1. Run the workflow over the 143 targets (canary-first).
2. Orchestrator pulls the `edgar_confirmation_needed` filings locally for every surviving thesis; upgrade tiers to `filing_verified`.
3. Red-team survivors a second time; base-rate-anchor timing against [base_rates.md](base_rates.md).
4. Extend down the canary tail (the remaining ~1,028) until the signal goes dry.
5. Feed confirmed concentrations + contagion paths into **Phase 4** — the concise current-state analysis + forward projection.

## Refinements queued (cheap, also gated on storage)

- **CIK→SIC join** — replaces heuristic sector labels; redistributes the 97/200 "Other / unclassified".
- **XBRL net-debt / EBITDA join** — converts gross notional into true leverage (notional ≠ leverage).
- **Distress §2.8 extraction** — Form-4 insider sales, 8-K covenant amendments, NT late filings, rating actions — the one fully-unpopulated signature today.

*Nothing here has been executed. This document + the harness + the target list are the setup; the run begins only on Ted's explicit go with storage cleared.*
