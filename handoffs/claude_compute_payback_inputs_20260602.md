# Compute payback-input bridge (Codex #2) — the payback layer is input-starved

**Base:** main `e99bbeb`, report `…-1827.json`. READ-ONLY; no prod writes.
**Deliverable:** `handoffs/fixtures/compute_payback_inputs_20260602.csv` (6 rows: entity, input field, engine value,
external verified value, source, status, what-completes-the-calc). Impact: **compute signal quality.**

## Finding: the engine's payback/unit-economics layer is structurally empty
The report's compute-economics payback surfaces are almost entirely null (confirming my `compute_economics_refresh`):
- `top_payback_stress_cases` — the only populated row is **WhiteFiber B200 at $42K capex / $15K cash flow / 2.8yr**:
  a single-GPU UNIT economics, not a company-level payback. Not decision-useful.
- `top_tam_reality_checks` — Cerebras TAM $131B/$72B/$43B but `realized_revenue` null → the `tam_to_revenue_multiple`
  (the actual bubble red-flag) can't compute.
- `top_eps_impacts` — Meta, `economic_depreciation`/`eps_drag` null (model-logic gap: `modeled_economic_life_years`
  never populated).
- GPU depreciation prices null 10/10 (the structural false-negative).

So the engine **cannot answer the payback question** ("can the AI-compute names' contracted revenue cover their debt
+ capex?") because the inputs aren't joined.

## The one verified external input I can bridge in
From my economic-commitment research (cited): **CoreWeave $60.7B take-or-pay RPO (Dec 31 2025)** is a real
`contracted_revenue_usd` the payback layer is missing. It is the single most decision-useful payback input available
for the direct tier — but completing CoreWeave's payback/DSCR still needs **capex** (10-K cash-flow PP&E additions)
and **clean debt** (the debt_service distinct_notional is inflated by the cross-filing duplicates my sibling-fill
lane flagged — dedup first).

## What completes the payback calc (per row in fixture)
- CoreWeave: RPO ✓ (verified) → + capex + deduped debt + GPU dep-life ⇒ payback/DSCR.
- Cerebras: TAM ✓ → + realized revenue ⇒ TAM-to-revenue multiple (the red-flag).
- Meta: disclosed useful-life change ✓ → + modeled economic life ⇒ accounting-vs-economic depreciation drag.

## Honest scope note
This is a deliberately small, honest deliverable: Codex's #2 asks for "revenue/payback source packs," but the layer
is input-starved and I have exactly **one** verified external revenue input (CoreWeave RPO). Rather than pad it with
unverified payback math, I bridge the one solid datapoint and specify the exact missing inputs per entity. Completing
the payback layer needs a verified per-name capex/debt acquisition pass (another research lane) — flagged, not faked.

## Verified vs proposed
- VERIFIED: the null state of the engine's payback fields (from the 1827 report); CoreWeave $60.7B RPO (cited).
- PROPOSED: the per-entity "what completes the calc" + the recommendation to dedup debt before any DSCR. No metric
  change; reject-uncited honored (no payback figure asserted without its inputs).
