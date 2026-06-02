# Read-Only Code Audit — high-leverage analysis modules — 2026-06-02 (lane 10)

- **From:** Claude (worker) · **For:** Codex · **Branch:** `claude/report-qa`
- Read-only review of modules Codex is **not** actively editing, focused on correctness of the numbers that reach the report. Observations separated from proposed fixes; impact labeled. File:line cites are against current `master`.

## Finding 1 — `weak_links._capital_candidates` inherits extraction fanout (REAL; impact: **triage-ranking only**)
**Observation:** `src/bubble/analysis/weak_links.py:173-224` builds one weak-link candidate per `capital_exposure_edges`
row with `exposure_usd = edge.notional_usd`. That edge notional is pre-aggregated in `capital_exposure_graph` by
`(source_name, target_name, deal_type)`, **summing across all deals sharing that triple** — including the extraction-fanout
deals (147 content_hashes → multiple deals; see `claude_provenance_audit` widened scan). So a weak-link capital candidate's
exposure can double-count one instrument that was extracted as several deals.
**Impact:** triage-ranking only — weak-links don't feed `final_metric_supported_amount_usd`; `exposure_usd` only orders the triage list.
**Proposed fix:** dedupe edge contributions by `content_hash`/instrument before summing the edge notional in
`capital_exposure_graph` (mirror the P0 instrument key). **Test:** `test_capital_edge_notional_dedupes_same_instrument`.

## Finding 2 — `debt_service` dedup is SOUND (positive)
`_obligation_economic_key` (`src/bubble/analysis/debt_service.py:1025`) keys on
`(entity, notional, tranche_name, deal_type, maturity)` — **not** accession/content_hash — so the same facility
re-reported across multiple filings collapses to one representative (`max` per group). This is the correct economic-identity
dedup; the capital-exposure-graph edge aggregation (Finding 1) should mirror it. **Residual risk only** if extraction yields
*different* notionals for one facility (extraction noise) → distinct keys; monitor, no action otherwise.

## Finding 3 — `ecosystem_scope` keyword gate is SOUND (positive; gates the headline)
`ecosystem_scope_reasons` (`src/bubble/analysis/ecosystem_scope.py:253-269`) scopes every headline AI-infra metric via
substring keyword match on `_deal_text`. `AI_DATA_CENTER_KEYWORDS` (`:124+`) is well-curated — specific multi-word/model
terms (`ai cluster`, `ai infrastructure`, `data center`, `gpu`, `h100`, `gb200`, `blackwell`, `hyperscaler`, `openai`,
`rubin`, …) with **no bare `"ai"`**, so the classic substring false-positive (`available`/`remain`/`certain`) is **absent**.
**Minor (not a bug):** `gpu`/`rubin` are short enough to theoretically substring-match a non-AI token (e.g. surname "Rubin").
If you want belt-and-suspenders, word-boundary matching (`\bgpu\b`) for the ≤5-char keywords removes that residual risk.

## Finding 4 — `EvidenceGate` correctly pins the report (positive; the core discipline)
`max_permitted_report_confidence` (`src/bubble/analysis/evidence.py:206-216`) returns 0.25 whenever any audited claim is
UNSUPPORTED. The report's `final.bubble_conclusion` claim is always audited with **empty evidence** (`generate_final_burry_report.py`
`audit_report_evidence`), so it is UNSUPPORTED → the report confidence is **robustly capped at 0.25** regardless of the
other metrics. The discipline holds. **Minor (cosmetic):** `_classify` labels a *single* primary source `MEASURED` but
*2+* sources `CORROBORATED_ESTIMATE` (an inversion-looking name); both are treated identically by the cap, so it is harmless
today — worth a rename only if the tiers ever get distinct downstream weights.

## Net
The headline-gating components (`ecosystem_scope`, `EvidenceGate`) and the debt-service dedup are **sound**. The one
actionable item is Finding 1 (weak-link capital exposure inherits extraction fanout) — **triage-ranking only**, fixable by
mirroring the debt-service economic-key dedup at the graph-edge level. No final-metric or evidence-gate-confidence risks found.
