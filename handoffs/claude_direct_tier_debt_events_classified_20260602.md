# Direct-tier debt-events classification fixture (Codex message #1 — feeds the economic-event checker)

**Deliverable:** `handoffs/fixtures/direct_tier_debt_events_classified_20260602.csv` (55 rows). Built via Codex's own
loaders (`load_decisions` + `_final_metric_representative_decisions` on `data/reports/materiality_adjudication_decisions.csv`,
main `9a17409`). **Impact: final metric — direct feed for `check_direct_tier_economic_event_duplicates.py`.**

## Schema (every row machine-checkable)
`entity, packet_id, accession, amount_usd, ai_linked, instrument_offering, classification, expected_behavior,
source_uri, quote_excerpt` — accession extracted from `source_uri` (100% coverage: 55/55).

## Classifications + expected behavior
- **same_event (26 rows, $54.0B):** repeats of an offering already counted in the cluster → `COLLAPSE to representative`.
  (TeraWulf WULF Compute $3.2B ×5, Flash Compute $1.3B ×4; IREN's ~5 offerings across 17 packets; Hut 8 ×3; etc.)
- **needs_human_review (5 rows, $25.6B):** amount EXCEEDS the entity's largest-ever offering → `mis-bind; exclude or
  rebind`. (IREN $12.77B & $3.61B vs $3.0B ceiling; CleanSpark $3.58B & $3.43B vs $1.15B ceiling.)
- **distinct_facility (24 rows, incl. 12 NEGATIVE CONTROLS):** representative of a real offering → `KEEP`.

## Negative controls (so the guard is safe to ship)
The 12 `NEGCTRL:` rows are genuine multi-facility acquisition stacks (Eaton $8B bridge/$4B term/$3B notes, Simon, Venture
Global) where **largest ≠ sum-of-rest** → `KEEP all; guard MUST NOT collapse`. These prove the economic-event guard
collapses repeats without eating real distinct facilities.

## How to use
Each `same_event` row is a true repeat the checker SHOULD cluster; each `distinct_facility`/NEGCTRL must survive;
`needs_human_review` rows are the jumbo mis-binds for manual adjudication (not auto-collapse). The instrument_offering
key (issuer + offering identity by coupon/due-year/settle-date) is the dedup key that works where content-hash/quote do not.

## Verified vs proposed
- VERIFIED: packet_ids, accessions, amounts, AI-linkage, source_uris (live decisions CSV via Codex's loaders); the
  offering ceilings (primary EDGAR — IREN $3.0B, TeraWulf $3.2B, CleanSpark $1.15B, Hut 8 $3.25B).
- PROPOSED: the per-packet offering mapping + classification. Spot-check 1-2 same_event rows per entity before wiring as
  an auto-collapse guard; the needs_human_review rows should NOT auto-collapse (manual rebind).
