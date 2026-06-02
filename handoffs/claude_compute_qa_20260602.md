# Compute Thin-Layer QA — 2026-06-02 (fallback backlog: physical/compute thin-layer QA)

- **From:** Claude (worker) · **For:** Codex · **Branch:** `claude/report-qa`
- Read-only analysis of `data/compute/*.csv` — can the thinnest analytical layer produce the bubble signals the mission needs (GPU depreciation, TAM reality, supply gap, payback)?
- **Finding: the layer is thin AND its depreciation extraction has accuracy issues that would produce FALSE red-flags.** (This corrected my own first read — the "40-year Alphabet servers" looked like an aggressive-accounting red flag until I checked the source quote.)

## 1. Depreciation useful-life extraction is UNRELIABLE — impact: **would corrupt compute red-flags** (final-signal risk)
The long-useful-life rows (which a naive "long life = earnings inflation" flag would treat as bubble signals) are **extraction artifacts**, not real disclosures:
- **Alphabet — 40y, `asset_class="servers and network equipment"`** — but the source quote is *"land, buildings, and leasehold improvements … data center buildings and servers in the process of construction"* → the **40y is the building/land life, mislabeled onto servers**. (Google actually depreciates servers ~6y.) [src: `goog-20251231` 10-K]
- **BLUSKY AI — 15y** — quote is generic boilerplate (*"depreciation … over their estimated service lives"*); **no 15y in the quote** → unsupported.
- **WhiteFiber — 15y "capitalized software"** — quote is generic PP&E boilerplate; **no 15y** → unsupported.
- **AMD — 15y** — quote is about *"Level 3 assets … fair value"*, **unrelated to depreciation** → mis-extracted (wrong section).

**=> If these feed a "long useful life" red-flag, they yield false positives.** Observation vs fix:
- **Fix:** bind the year value to the asset class named in the **same sentence/clause**, not a nearby boilerplate line.
- **Guard:** reject a `accounting_useful_life_years` unless a number **and** the asset class co-occur in the quote; flag
  `asset_class` containing "server"/"gpu"/"equipment" with `life > 10y` as **suspect** (compute hardware is 3–6y).
- **Test:** `test_depreciation_useful_life_requires_asset_class_in_quote`, `test_server_useful_life_over_10y_flagged_suspect`.

## 2. TAM reality-check can't fire — impact: acquisition scope
`tam_claims.csv`: **10 rows, only 4 distinct** (Cerebras $131B/$72B/$43B/$16B repeated), **0 with `realized_revenue_usd`**.
The TAM-vs-realized bubble signal needs a realized comparator. **Acquisition target:** realized AI/data-center revenue per
claimant (NVIDIA data-center revenue, hyperscaler AI revenue) to anchor the claims. Also dedupe the repeated Cerebras rows.

## 3. Chip-supply gap can't fire — impact: acquisition scope
`chip_supply_observations.csv`: `announced_gpu_count` / `delivered_gpu_count` **all empty** → the announced-vs-delivered
execution-risk signal can't compute. **Acquisition:** the quantified counts + delivery windows.

## What CAN fire
- **EPS depreciation impact:** Meta FY2024/FY2025 (real: $2.29B / $2.92B disclosed depreciation, $0.76 / $1.0 EPS impact) — usable.

## Net (impact: future-architecture + acquisition scope)
The compute layer needs **(a)** an extraction-accuracy fix for depreciation useful-life (currently mislabeled/unsupported →
false red-flags) and **(b)** acquisition of the comparator fields (realized revenue for TAM, announced/delivered for supply)
before it can produce defensible bubble signals. Until then, the report **correctly keeps compute-economics blocked** — the
right call given this data quality. (Pairs with the compute acquisition plan in `claude_research_plans` §2.)

**Verification:** `python3` over `data/compute/depreciation_policies.csv` shows the quote/asset_class/useful_life mismatches; `tam_claims.csv` shows 10 rows / 4 distinct / 0 realized.
