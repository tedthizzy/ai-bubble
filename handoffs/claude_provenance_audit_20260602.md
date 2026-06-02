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
- The check functions are generic (`Iterable[Mapping]` + configurable key names), so they extend to `deals.csv`, `tranches.csv`, and `source_rows/*` by passing the right `doc_id_key`/`hash_key`/`uri_key`. The CLI currently wires only the EDGAR inventory; say the word and I'll widen it.
- Pairs with the report-consistency verifier (`scripts/check_report_consistency.py`) as the provenance/QA half of the same toolkit.
