# Materiality Dedupe Design — 2026-06-02

- **From:** Claude (worker) · **For:** Codex · **Branch:** `claude/report-qa`
- **Method:** 5 parallel read-only `Explore` auditors (UltraCode workflow) over the materiality decision set + **independent verification by me** of the metric-impact claims.
- **Snapshot:** `data/reports/materiality_adjudication_decisions.csv` with **2,786** `approved_for_metric_use` rows at read time. NOTE: data is moving (you were regenerating the report), so treat counts as "as of this snapshot."
- **Constraints:** read-only; design + sample IDs + proposed keys/tests only. **No production rewrite, no artifact rebuild, no edits to your active files.**

---

## Priority summary

| # | Finding | Impact | Status |
|---|---------|--------|--------|
| **P0** | **Same-instrument double-counting in approved metric support** (~$2.5T, snapshot est.) | **final-metric** | mechanism VERIFIED; magnitude = my estimate, please reconcile |
| P1 | Affiliate cross-attribution (Entergy/Ameren/…) + lender-as-entity approved rows | final-metric | subset of P0; verified |
| P2 | Ranking/queue fanout (SpaceX exhibit ×20, physical ×176/×40, weak-link composite ×2.6) | triage-only | verified, rank inflation only |

---

## P0 — Metric double-counting (VERIFIED mechanism; magnitude is a snapshot estimate)

**Claim:** the same underlying instrument is `approved_for_metric_use` under **multiple distinct `metric_group_id`s**, so the `sum_distinct_metric_rows` aggregation counts it N times in `final_metric_supported_amount_usd`.

**Decisive evidence** (one facility, identical `content_hash` + identical `supported_amount`, but a distinct `metric_group_id` per row):

```
Entergy  content_hash 6fd721f7…  : 8 approved rows, 8 DISTINCT metric_group_ids, each $3.500B
   ENTERGY ARKANSAS, LLC / MISSISSIPPI / LOUISIANA / TEXAS  (each appears up to 2×)
Ameren   content_hash b2983ca2…  : 6 approved rows, 6 DISTINCT metric_group_ids, each $1.400B
   AMEREN CORP / Ameren Illinois Co / UNION ELECTRIC CO
Entergy  content_hash c74e515…   : 4 approved rows, 4 DISTINCT metric_group_ids, each $3.556B
```
→ one $3.5B facility contributes ~$28B; one $1.4B facility ~$8.4B; etc.

**Magnitude (snapshot estimate).** Collapsing approved rows by the conservative key `(content_hash, supported_amount)`:
- `approved` rows: 2,786 → distinct `metric_group_id`s: 2,785 (so the current metric-group dedupe collapses **~0**).
- raw approved sum ≈ **$11.79T**; collapsed by `(content_hash, amount)` ≈ **$9.22T**.
- **≈ $2.5T (≈22%)** of approved final-metric support is same-document/same-amount duplication; **777** `(content_hash, amount)` groups each span **>1** `metric_group_id` (truly double-counted), ≈ **$2.575T**.
- Top offenders are mostly **non-AI corporates** (so also out of AI scope, but they still inflate the headline corpus metric): PennyMac $230B ×2, Navient $30.2B ×2 (two docs), Pfizer $28B ×2, Fulton Financial $26.1B ×2 — plus the AI-relevant affiliate clusters above.

**Reproduction (read-only):**
```python
import csv
from collections import defaultdict
rows=[r for r in csv.DictReader(open("data/reports/materiality_adjudication_decisions.csv"))
      if r["metric_use_status"]=="approved_for_metric_use"]
f=lambda x:(float(x) if x else 0.0)
cur=sum(f(v[0]["supported_amount_usd"]) for v in
        _g(rows,lambda r:r["metric_group_id"]).values())                 # one per metric_group
ded=sum(f(k[1]) for k in _g(rows,lambda r:(r["content_hash"],r["supported_amount_usd"])))
print((cur-ded)/1e9, "B double-counted")     # ~2.5T
```
(group helper `_g` = `defaultdict(list)` keyed by the lambda.)

**Root cause.** `metric_group_id` is assigned per review-group / per-entity, so it is finer-grained than the *instrument*. `sum_distinct_metric_rows` dedupes by `metric_group_id` and therefore never collapses (a) the same instrument attributed to multiple affiliated entities, (b) the same instrument extracted twice for one entity, or (c) multi-rank packets of one source.

**Proposed fix (metric path — your `materiality_adjudication_results.py`; I propose, I do not edit).**
Change the final-metric dedupe key from `metric_group_id` to an **instrument key**, e.g. `(content_hash, round(notional), deal_type)` (or `(accession, notional, deal_type)` where content_hash spans a multi-instrument filing). Collapse approved rows sharing it into **one** metric contribution; retain all entities/counterparties/source_uris/content_hashes on the representative for provenance. Keep aggregate-snapshot handling you already have — this is orthogonal (it fixes counting the *same* snapshot N times, not whether snapshots are approvable).

**Caveats (please reconcile before acting):**
1. The magnitude is *my* grouping, not your official aggregator — reconcile `(content_hash, amount)` collapse against `final_metric_supported_amount_usd` in your code; the official number may differ.
2. `(content_hash, amount)` can in principle over-collapse two genuinely distinct same-amount obligations in one filing (rare) — the production key should add `deal_type`/notional-context.
3. Data was moving as you regenerated; numbers above are a single snapshot.

**Regression test names:**
`test_same_instrument_one_metric_contribution_across_affiliates`,
`test_metric_dedupe_collapses_same_content_hash_same_notional`,
`test_duplicate_entity_extraction_not_double_counted`,
`test_final_metric_excludes_repeated_aggregate_snapshot`.

---

## Lane findings (from the 5 auditors)

### A — capital_contract_fanout (final-metric; = P0/P1)
Single instruments cross-attributed to parent + subsidiaries, all approved. Clusters (content_hash → entities, all identical amount):
- Entergy `c74e515…` $3.556B → 5 Entergy subs · pkts `caa96eca…`,`95b5937d…`,`c962e580…`,`f741c0ac…` · `…/data/66901/000119312525174487/d99077ds3asr.htm`
- Entergy `6fd721f7…` $3.5B → 4 subs (8 rows) · pkts `db31dd56…`,`7cd93084…`,`ca70ea4f…`,`582eb8e2…` · `…/data/7323/000006598424000062/etr-20240611.htm`
- Ameren `b2983ca2…` $1.4B → 3 entities · pkts `1b089e51…`,`1756b20f…`,`a410f083…`,`af3905ca…` · `…/data/100826/000110465925119977/tm2533090d1_8k.htm`
- Eversource `cc6ec692…` $2.0B → 3 entities · pkts `e9d73ed3…`,`23d8a188…`,`3e41f5b7…`
- Empire State Realty `f9a53c79…` $1.5B → OP + Trust · pkts `b72318a0…`,`4b4ddd55…`,`4c154e4b…`
- CMS Energy `d6e6eff6…` $1.1B → CMS + Consumers · pkts `ce1f706d…`,`5056fb14…`,`7331e6a0…`

**Dedupe key:** `(content_hash, counterparty/parent_entity, notional)`; collapse subsidiary rows to one canonical (parent or named guarantor), keep affiliates as provenance.

### B — cross_entity_attribution (final-metric subset + triage)
SpaceX S-1 `exhibit109-sx1.htm` (`836d3d6b…`) → **20 rows, 1 real borrower**. Misattributions across the whole CSV (snapshot):
- **447** rows with `' - SEC exhibit '` in the entity name (document/exhibit label leaking into entity) — triage.
- **6** rows `', as holdings,'` = definition-derived (X.AI/X "Existing Subsidiary Indebtedness" defined terms, **not** parties) — triage. pkts `8f27cb92…`,`fc9c81d5…`,`2cf9314d…`,`b9ce4951…`,`957aadef…`,`53677c91…`.
- **33** rows where a **bank is the entity** (Goldman/Morgan Stanley/BofA as Arranger/Agent) — **6 of these are `approved_for_metric_use` → metric leakage.** pkts incl. `ca90d6e6…`,`44b9a32d…`,`701fc2f3…`.

**Rule:** attribute borrower-side exposure only to the named **Borrower** (`"<X> as the Borrower"`); drop entities appearing only in definitions/recitals or in Arranger/Agent roles; strip `' - SEC exhibit '` / `', as holdings,'` markers in entity normalization. **Tests:** `test_no_sec_exhibit_marker_in_entity`, `test_only_borrower_or_guarantor_attributed`, `test_no_lender_entity_approved_for_metric`.

### C — ranking_pipeline_integration (final-metric + triage; the structural root)
**1,803** content hashes appear at multiple ranks (2–176 packets each); **10,336** packets across multi-rank hashes. *Auditor-reported* code mechanism (please verify line numbers — auditor read the files, I did not):
- `materiality_adjudication.py` collapses by `review_group_id` (~L155–162), but `packet_id` derivation (~L237–242) **includes `source_uris`+`content_hashes`**, so same-source different-extraction rows get distinct `packet_id`s and survive the collapse.
- `_materiality_sort_key` (~L535–541) ranks each surviving duplicate on exposure/risk → multi-rank fanout.
- `review_queue.py` dedupe key (~L843–851) `(category, subcategory, deal_id, source_row_id, source_uri, content_hash)` is too granular for content_hash fanout.
- Offender hashes all/most `approved_for_metric_use`: `4be34d0b…` ×10, `5259284325…` ×9, `6fd721f7…` ×8 (Entergy), `26441da89a…` ×8 (NYISO), `efce6f70…` ×10.

**Proposed (auditor):** add `_collapse_packets_by_content(packets)` after ranking, before limit (~L162): group by `(content_hash, category, subcategory)`, keep highest-materiality representative, accumulate all `source_uris`/`content_hashes`/`counterparties` as tuples. **Tests:** `test_collapse_same_content_hash_reduces_packet_count`, `test_collapse_preserves_highest_materiality_rank`, `test_collapse_accumulates_source_uris_in_tuples`.

### D — physical_fanout (triage-only)
- `349ff011…` (EPA ICIS-AIR permit zip) → **176** rows / 169 unique permit-facility pairs (≈1.04×).
- `895cd81d…` (EPA eGRID2023 xlsx) → **40** rows / 10 unique pairs (**4.0×**; Equinix fuel cell ×7, Apple PV ×3).
- All `triage_only`/`blocked` (no metric leakage). **Key:** `(category='physical', subcategory, content_hash, entity, counterparty)`; physical category 242 → ~160 rows. **Test:** `test_physical_match_collapses_per_unique_pair`.

### E — weak_link_composite (triage-only)
`capital_exposure` weak-link rows sum duplicate same-(entity, notional, content_hash) packets → composite exposure_basis ~2.6× inflated (SpaceX/X.AI/X $40B ×2–3; CoreWeave $8.92B/$6.2B ×2). All `triage_only`. `debt_service_stress` already dedupes via `_distinct_obligations` (debt_service.py ~L839–868) — *auditor recommends mirroring that for capital_exposure in `weak_links.py` (~L101) before `_capital_candidates`.* **Test:** `test_weak_link_composite_dedupes_duplicate_obligations`.

---

## Unified design — two collapse points

1. **METRIC PATH (P0 — do first, highest value).** Instrument-key dedupe `(content_hash, notional, deal_type)` in the **final-metric aggregation** so one instrument contributes once to `final_metric_supported_amount_usd`. This is the ~$2.5T item.
2. **RANKING PATH (P2).** `_collapse_packets_by_content` on `(content_hash, category, subcategory)` after sort / before limit (lane C) — removes queue/rank fanout (SpaceX ×20, physical, multi-rank).

**Invariant for both:** collapsing must **preserve provenance** — keep every `source_uri`, `content_hash`, `counterparty`, and `entity` of the collapsed rows on the representative; never drop source evidence, only stop *counting/ranking* it N times. Neither change weakens the evidence gate.

---

## What I did NOT do
- No edits to production code or your active files; no artifact rebuilds.
- Code line numbers in lane C are auditor-reported from reading the files — verify before relying.
- Magnitudes are single-snapshot estimates from my own grouping; reconcile against your official aggregator before treating $2.5T as exact.
