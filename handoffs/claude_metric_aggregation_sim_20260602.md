# Metric-Aggregation Simulator — 2026-06-02 (lane 3)

- **From:** Claude (worker) · **For:** Codex · **Branch:** `claude/report-qa`
- **Tool (branch-local, additive):** `src/bubble/quality/metric_aggregation_sim.py` + `scripts/simulate_metric_aggregation.py` + `tests/quality/test_metric_aggregation_sim.py` (3 tests, GREEN; ruff/mypy clean). Read-only; **re-run after each rebuild** to monitor the dedup key.
- **Run:** `PYTHONPATH=src uv run scripts/simulate_metric_aggregation.py --repo-root /Users/ted/Documents/dev-archive/bubble`
- Each group contributes `max(supported_amount)` (matches your `max_amount_per_source_instrument` policy).

## Live result (2,817 approved rows; current baseline $9.305T / 1,949 groups)

| strategy | total | groups | Δ vs current |
|----------|------:|-------:|-------------:|
| `metric_group_id` (current) | **$9.305T** | 1,949 | 0 |
| `content_hash + amount` | $9.294T | 1,946 | **−$11B** ← your fix ≈ this |
| `source_uri + amount` | $9.355T | 1,964 | +$50B |
| `accession + amount` | $8.947T | 1,765 | −$357B |
| `instrument-key (hash+amount+category)` | $11.057T | 2,528 | **+$1,752B** |
| `content_hash` alone | $8.505T | 1,728 | −$800B |

## Insights (impact: future-architecture / dedup-monitoring)
- **Your current grouping ≈ `content_hash+amount`** (within $11B). It sits in the sensible middle of the envelope — good.
- ⚠ **Do NOT add category/subcategory to the dedup key:** `hash+amount+category` *increases* the total by **+$1.75T**
  (the same instrument approved under two categories then counts twice). A richer "instrument key" must **not** split on category.
- `accession+amount` removes another **−$357B** (collapses multiple exhibits of one filing) — but risks over-collapsing
  genuinely distinct instruments in a single filing; use only with `amount`+`seniority`/`tranche_id` guards (see
  `claude_prebuild_packs` instrument-key + the Dropbox over-collapse fixture).
- `content_hash` alone removes **−$800B** but over-collapses different-amount tranches (Dropbox: two distinct $1.0B
  tranches in one hash) — too aggressive.
- `source_uri+amount` ≈ `content_hash+amount` (+$50B) — source_uri and content_hash are near-equivalent keys here.

**Net:** the current key is sound; the actionable guard is "don't add category, be careful with accession-level collapse."
Re-run the tool after each rebuild; if a strategy's delta moves sharply, the dedup key or the approved set changed.
