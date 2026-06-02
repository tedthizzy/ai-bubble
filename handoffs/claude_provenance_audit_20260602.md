# Provenance-Integrity Audit — 2026-06-02

- **From:** Claude (worker) · **For:** Codex · **Branch:** `claude/report-qa`
- **Files (branch-local, additive):** `src/bubble/quality/provenance_audit.py`, `scripts/check_provenance_integrity.py`, `tests/quality/test_provenance_audit.py` (3 checks, TDD, GREEN; ruff/mypy clean).
- Does **not** touch `source_invariant_audit.py` or your files; standalone for your review (not wired to `just`/CI).

## Checks (novel vs the existing source-invariant audit)
- `divergent_document_hash` (**ERROR**) — one document (`accession/primary_document`) carrying >1 `content_hash` → re-fetch drift / corruption.
- `invalid_content_hash` / `missing_content_hash` (**ERROR**) — non-sha256-hex, or blank hash on a row that has a `source_uri`.
- `hash_conflicting_document_ids` (**WARNING**) — one `content_hash` under multiple `document_id`s → duplicate content across filings.

## Real-data result (read-only, `data/edgar_acquisition/edgar_document_inventory.csv`)
- **66,072 rows scanned · 0 errors · 38 warnings.**
- The corpus is **integrity-clean** on the critical checks: no document has two fingerprints, no invalid/blank hashes.
- The **38 `hash_conflicting_document_ids`** are benign *duplicate-content cross-filings* (the same exhibit attached to two filings — e.g. `dp236467_ex9901.htm` under accessions `…013949` and `…013968`). **Relevant to the P0 metric-dedup work:** the same content under two accessions can be extracted twice, so an accession-keyed dedup would *not* catch it while a content_hash-keyed dedup would — a data point for choosing the instrument key.

## Run
```bash
PYTHONPATH=src uv run scripts/check_provenance_integrity.py --repo-root /Users/ted/Documents/dev-archive/bubble
```

## Notes
- The check functions are generic (`Iterable[Mapping]` + configurable key names), so they extend to `deals.csv`, `tranches.csv`, and `source_rows/*` by passing the right `doc_id_key`/`hash_key`/`uri_key`.
- Pairs with the report-consistency verifier (`scripts/check_report_consistency.py`) as the provenance/QA half of the same toolkit.

## Widened scan — inventory + deals + tranches (CLI now scans all three)

| corpus | rows | divergent_document_hash | invalid/missing hash | content_hash → multiple ids (fanout) |
|--------|-----:|------------------------:|---------------------:|-------------------------------------:|
| `edgar_document_inventory.csv` | 66,072 | **0** | **0** | 38 |
| `deals.csv` | 20,198 | **0** | **0** | **147** |
| `tranches.csv` | 10,051 | **0** | **0** | **1,605** |

**Integrity result: 0 errors across all three corpora (~96k rows)** — no document carries two fingerprints, no
invalid/blank hashes. The corpus is provenance-clean.

**Dedup-relevant finding (impact: future-architecture / supports your metric-dedup lane):** the `content_hash → multiple ids`
fanout shows the metric-layer duplication I flagged (P0) **originates at extraction**: one source document produces
multiple deal/tranche rows. deals.csv: **147 content_hashes each spawn 2–7 deals** (distribution: 90×2, 12×3, 1×4, 29×5,
14×6, 1×7); the worst are **Entergy Louisiana exhibits — one filing → 6 deals each** (e.g. `…exhibit4aq225/4bq225/4cq225/4dq225`),
the same affiliate clusters that drove the $2.5T metric double-count. tranches.csv fans out far more (**1,605** hashes →
multiple tranches), expected since tranches are per-facility-component. This is why an instrument key keyed on
`content_hash` alone over/under-collapses (see `claude_materiality_dedupe_design` + `claude_prebuild_packs` §instrument-key).

Run: `PYTHONPATH=src uv run scripts/check_provenance_integrity.py --repo-root /Users/ted/Documents/dev-archive/bubble`
