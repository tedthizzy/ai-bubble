# Fragility Atlas — index (bounded free-public-tier deliverable)

> **⚓ Frame:** a general, evidence-gated forensic engine for **financial fragility & mispricing across the whole (US-primary) economy** — no sector prior; **AI / data-center is case zero, not the object.** This index is the navigable entry point to the **bounded free-public-tier atlas**: the US public-filer + FDIC-bank universe, scored on every free/autonomously-reachable dimension, with the genuine flagged candidates adversarially verified. Scope, doctrine, and what's *out of scope as a real wall*: [total_ecosystem_dive.md](total_ecosystem_dive.md) · [boundary_ledger.md](boundary_ledger.md) · [README](../README.md).

## The verdict (one screen)

**No single epicenter; no systemic-cascade wiring.** Pointed economy-wide with no sector prior, fragility is **broadly distributed, idiosyncratic, and ~62% worsening** — concentrated in leveraged media / energy / healthcare / consumer / REIT names, **not AI**. Three integrated layers:

1. **Corporate/issuer** — 450 deep-verified → **174 confirmed fragile** (124/166 orchestrator-filing-verified); distributed, idiosyncratic (1 direct contagion link), trajectory-worsening.
2. **Banking** — all 4,352 FDIC banks: **healthy on capital** (~6 below well-capitalized); *not* a systemic node.
3. **Physical power (case zero's base)** — **overbuilt & attriting**: CAISO ~**11× withdrawn:completed** queue, EIA **181 GW canceled vs 288 GW planned**.

AI is one stressed-and-wired cohort (the sole shared-financier contagion cluster) sitting on an over-promised power base — not the economy's fragility epicenter. Full reasoning + forward projection: **[SYNTHESIS_2026-06-13.md](SYNTHESIS_2026-06-13.md)**.

## Artifacts by layer

**Breadth scans (the universe):**
- [economy_wide_fragility_map.md](economy_wide_fragility_map.md) — sector-agnostic signature scan, 2,007 deal-corpus entities (AI #14).
- [economy_xbrl_fragility.md](economy_xbrl_fragility.md) — ratio-based scan over **all 7,992 SEC filers** (size-bias-free).
- [fragility_by_sector.md](fragility_by_sector.md) · [fragility_by_sic.md](fragility_by_sic.md) — sector views (heuristic + real SIC).

**Depth (the flagged set):**
- [phase3_findings.md](phase3_findings.md) — 450 deep-agent profiles + adversarial verdicts → 174 confirmed.
- [survivor_filing_verification.md](survivor_filing_verification.md) — orchestrator EDGAR re-pull: **124/166 filing-verified, 75% agent reliability.**
- [large_levered_net_leverage.md](large_levered_net_leverage.md) — XBRL net-debt/coverage (real distress vs refi-risk).
- [multidecade_trends.md](multidecade_trends.md) — multi-year trajectories (~62% deteriorating).

**Contagion (unified graph):**
- [contagion_over_confirmed.md](contagion_over_confirmed.md) — capital + contract graphs (1 direct link; AI-only shared counterparties).
- [ownership_contagion.md](ownership_contagion.md) — 425k-node LEI ownership (0 shared ultimate owners).

**Off-EDGAR layers (5 sources ingested):**
- [fdic_bank_distress.md](fdic_bank_distress.md) — banking layer (FDIC call reports).
- [iso_queue_caiso.md](iso_queue_caiso.md) · [eia_860m_buildout.md](eia_860m_buildout.md) — physical-power layer.
- [gdelt_news_distress.md](gdelt_news_distress.md) — news corroboration (independent source).

**Meta / scorekeeping:**
- [boundary_ledger.md](boundary_ledger.md) — **the honest score**: real limits (account-registration, payment) vs open-work, every gap named and probe-verified; 6 self-corrections logged.
- [base_rates.md](base_rates.md) — outside-view priors (fiber 1999, shale 2014).

## Reproduce

Every artifact regenerates from its `scripts/*.py` (all under the CI gate where in `src/`; analysis scripts are standalone). Breadth → `economy_wide_signature_scan.py`, `xbrl_economy_scan.py`; depth → `build_phase3_targets.py` + `workflows/phase3_deep_dive.workflow.js` + `extract_phase3_findings.py`; verify → `verify_survivors_edgar.py`; contagion → `contagion_over_confirmed.py`, `ownership_contagion.py`; off-EDGAR → `fdic_bank_distress.py`, `iso_queue_caiso.py`, `eia_860m_buildout.py`, `gdelt_news_distress.py`.

*Bounded-tier completeness: all free/autonomous dimensions over the ~12k universe are computed; out-of-scope items are paywalled/credentialed/private and tagged as real walls in the boundary ledger. "We did the maximum the free, autonomous data, tooling, and access allowed."*
