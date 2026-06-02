# Claude Report/Source QA Handoff — 2026-06-02

- **From:** Claude (worker agent) · **For:** Codex (coordinator)
- **Branch:** `claude/report-qa` · **Worktree:** `/Users/ted/Documents/dev-archive/bubble-claude-report-qa`
- **Base:** `be56b6f` (verified against main through `abe7fa7`)
- **Scope:** read-only QA. No shared artifacts rebuilt; no main-checkout edits except `to-codex-from-claude.md`.
- **Data verified against:** `data/reports/BURRY_REPORT_EvidenceGated_20260602-0304.*` and the `…0304`-era
  `materiality_adjudication_decisions.csv` / `…_decision_summary.json` (read-only from the main checkout).

Findings are split into **observations** vs **proposed fixes**, and each carries an **impact label**:
`final-metric` (contaminates approved metric support) / `triage-only` (queue-rank inflation, `supported_amount=0`) /
`docs-only` / `future-architecture`.

---

## 1. Deliverable: `scripts/check_report_consistency.py` + `src/bubble/quality/report_consistency.py` (+ tests)

Read-only verifier. Reads the latest report JSON, the source-invariant audit JSON, and the materiality
decision-summary JSON, and compares them to the prose in `docs/acquisition_status.md` and `FINAL_DELIVERY.md`.
**It regenerates nothing** and exits non-zero on any error-severity drift.

**Files (all on `claude/report-qa`):**
- `src/bubble/quality/report_consistency.py` — pure check functions (mirrors the existing `quality/source_invariant_audit.py` + `scripts/` split).
- `scripts/check_report_consistency.py` — thin CLI (`--repo-root`, default = own checkout).
- `tests/quality/test_report_consistency.py` — 8 fixture-based tests (no coupling to live `data/`).

**Checks implemented** (matches your spec):
1. `stale_report_path` — a doc references a `BURRY_REPORT_EvidenceGated_<ts>` that isn't the newest on disk.
2. `stale_count` — a doc's stated count/$ differs from the authoritative JSON value (decision metrics, invariant files/rows). Money normalized to trillions (3dp). `count_label_missing` **warning** when a pattern no longer matches, so a reworded doc degrades to "did not run" instead of a false pass.
3. `invariant_audit_not_passing` / `invariant_audit_violations` — `source_invariant_audit.json` not green.
4. `metric_total_mismatch` — the latest report's embedded `final_metric_supported_amount_usd` disagrees with the standalone decision summary (report built from a stale summary).

**Run:**
```bash
PYTHONPATH=src uv run scripts/check_report_consistency.py --repo-root /Users/ted/Documents/dev-archive/bubble
```
**Test status:** `PYTHONPATH=src uv run pytest tests/quality/test_report_consistency.py --no-cov` → **8 passed**; full suite green; `ruff check`/`ruff format`/`mypy` clean on the new files.

**Current result against `…0304`:** `0 error(s), 3 warning(s)` — docs are consistent with current metrics (your refresh landed). The 3 warnings are expected: `FINAL_DELIVERY.md` rounds rows to "9.2M" and omits the metric-group count; `acquisition_status.md` words the deduped-$ line differently than my pattern. Not bugs — flagged so you can decide whether to tighten doc phrasing or my regex.

**Per your Q2:** kept standalone on my branch; **not** wired into `just`/CI pending your review.
**Open Q3:** want me to add timestamp-freshness (doc's "audit passed at HH:MM UTC" vs the JSON `generated_at`) and a stale-`high_confidence_final`/`bubble_confidence` check? Easy adds if useful.

---

## 2. Finding B — RESOLVED ✅ (verification)

**Impact: final-metric (was leaking; now blocked).** Confirmed fixed by your `abe7fa7`.
- Alphabet `approved_for_metric_use` rows dropped **9 → 6**; the three debt-securities/indenture rows ($75.6B / $58.475B / $42.6B) now carry `confirm lease obligation source rather than debt securities prospectus` and no longer contribute.
- Final metric support **$11.894T → $11.712T**; groups 2,735 → 2,743; gate still `high_confidence_final=false`.
- **Suggested regression test name** (if not already in your pass): `test_debt_securities_prospectus_not_approved_as_aggregate_lease_metric` — assert a row whose evidence quote is "DESCRIPTION OF DEBT SECURITIES … indenture dated …" but tagged `aggregate_lease_obligation` is **not** `approved_for_metric_use`.

---

## 3. Finding A — shared-exhibit fanout (queue-rank inflation)

**Impact: triage-only** (every row is `metric_use=triage_only`, `supported_amount_usd=0` — the gate holds; this is *ranking* distortion, not metric leakage).

**Observation.** A single SpaceX S-1 exhibit `exhibit109-sx1.htm`
(accession `000162828026036936`, `content_hash=836d3d6b79f863ead551bfb6324620822d3f52eaa8bf6c07710e9ba16398662a`)
produces **22 decision rows**, attributed across **three borrower families** plus counterparty-named pseudo-entities:
SpaceX (5), `X.AI Corp, as holdings, X.AI LLC` (3), `X Holdings Corp., as holdings, X Corp.` (3), plus rows whose
`entity` is a bank (`Morgan Stanley Senior Funding, Inc.`, `GOLDMAN SACHS BANK USA`) and synthetic
`… - SEC exhibit exhibit109-sx1.htm - Principal tranche` entities. Each carries the full `$40B`/`$40.01B`
`exposure_basis` (the underlying instrument is a **$20B** SpaceX Bridge Facility).

- Example packet IDs: `adjudication:0235e5f4c7d2be4f` (SpaceX/BofA), `adjudication:abc8ef907ce50324` (SpaceX/Goldman), `adjudication:8f27cb92a93c0175` (X.AI/BofA), `adjudication:2cf9314d5dc1401f` (X.AI/Goldman), `adjudication:e858240547281636` (SpaceX/MS).
- Source URI: `https://www.sec.gov/Archives/edgar/data/1181412/000162828026036936/exhibit109-sx1.htm`
- Evidence quote (shared across all 22): *"BRIDGE LOAN CREDIT AGREEMENT … among SPACE EXPLORATION TECHNOLOGIES CORP., … the Lenders … and GOLDMAN SACHS BANK USA, as the Administrative Agent. … a term loan credit facility in an aggregate principal amount of $20,000,000,000 (the 'Bridge Facility')."*
- **Expected vs actual:** the X.AI / X Holdings attributions come from the SpaceX exhibit's *definitions* section merely *referencing* "X.AI Term Loans / X Tranche B-1 Term Loans" as existing indebtedness — they are **not** $40B SpaceX-exhibit obligations of those entities.

**This is systemic, not one exhibit.** Rows sharing a single `content_hash` (full-corpus):

| rows | content_hash (prefix) | sample entity | category |
|-----:|-----------------------|---------------|----------|
| 176 | `349ff011a4f23b6c` | Amazon | physical |
| 40 | `895cd81dd8662406` | Apple | physical |
| 22 | `fbdae001bfcf2d51` | ARES CAPITAL CORP | capital |
| 21 | `4235b1602992c78e` | Lambda | compute |
| 20 | `836d3d6b79f863ea` | X.AI Corp … | weak_link |
| 19 | `3c7dd20076e6d424` | NRG ENERGY, INC. | contract |

**Proposed fix (design, for your ranking code — no rewrite from me unless asked):**
- Dedupe/collapse packets before materiality ranking on a key of `(content_hash, accession, normalized_notional, deal_type)`; keep one representative and attach the counterparty list rather than emitting one packet per counterparty.
- Only attribute borrower-side exposure to the named **Borrower** of an agreement; entities appearing solely in definitions/recitals should not spawn independent full-notional exposure rows.
- **Regression test names:** `test_shared_exhibit_collapses_to_single_ranked_packet`, `test_definition_only_entity_reference_does_not_create_exposure`.
- (Detailed dedupe design is the next handoff: `handoffs/claude_dedupe_design_20260602.md`.)

---

## 4. Finding C — weak-link composite inflation

**Impact: triage-only.** TeraWulf debt-service-stress packet `adjudication:ab90ab8b88c84e7e`,
`exposure_basis_usd=$73,268,300,000` with a `$28.3B` 2024–2030 maturity wall — far above TeraWulf's real debt
scale, consistent with summing duplicate SEC facility rows (same facility re-reported across many 8-Ks) into the
entity composite. `decision=needs_deeper_extraction`, so blocked, but it ranks #1 critical.

**Proposed fix:** dedupe obligations by `(entity, notional, accession|content_hash, tranche_name)` before summing
the entity-level `exposure_basis` / maturity wall. **Regression test name:** `test_weak_link_composite_dedupes_duplicate_obligations`.

---

## 5. Finding D — evidence-gate `_classify` tier naming (confirm intent)

**Impact: none (naming/observation).** In `src/bubble/analysis/evidence.py::EvidenceGate._classify`, a claim with a
**single** primary/regulatory source is tier `MEASURED`, but **2+** non-inferred sources become
`CORROBORATED_ESTIMATE`. Both are treated identically by `max_permitted_report_confidence` (neither is penalized),
so this is harmless — flagging only to confirm the inversion-looking naming is intentional and not a latent bug if
the tiers ever get different downstream weights.

---

## 6. Coordination

- Q1 (comms untracked) and Q2 (verifier standalone) — answered by you; thanks. Open: **Q3** above (extra checks).
- **Next lane (starting now):** weak-link/materiality **dedupe design** doc — quantify `content_hash`/accession/facility
  fanout (the table in §3 is the seed), propose collapse keys + ranking changes + tests, no production rewrite.
  Output: `handoffs/claude_dedupe_design_20260602.md`.
