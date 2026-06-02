# Ingestion-layer read-only audit — VERIFIED synthesis (3 modules) — 2026-06-02

- **From:** Claude · **For:** Codex. Three parallel read-only UltraCode audits of the *ingestion gate* (what gets
  extracted at all, and at what notional): `edgar/document_acquisition.py`, `edgar/filing_manifest.py`,
  `ingestion/physical/{queue,record}_matching.py`.
- **Discipline note:** the raw auditors over-labeled. I re-checked every HIGH/CRITICAL claim against the actual code
  before relaying. **Net: 1 genuinely-real HIGH, 2 medium/narrow, and 4 refuted false alarms.** The refutations matter
  as much as the findings — they stop us from "fixing" correct code. Evidence (file:line) is inline for each.

---

## ✅ VERIFIED-REAL (worth a fixture + fix)

### R1 — `record_matching` double-scores the facility name as both name AND party  *(HIGH, real)*
`record_matching.py:518-524` computes `party_score` from `_overlap_ratio(row_name_tokens, project.party_tokens)` —
i.e. it probes the **facility name tokens** against the project's **owner/party tokens**, while `name_score` already
probes `row_name_tokens` vs `project.name_tokens`. The same `row_name_tokens` feeds both. A shared token (e.g.
`google` in "Google Data Center" vs project party "Google Cloud") contributes to *both* scores.
The queue path does **not** have this bug — `queue_matching.py:497-503` uses a *separate* `queue_party_tokens` and
guards `if queue_party_tokens and not queue_party_tokens.issubset(queue_name_tokens)` so name tokens can't masquerade
as party evidence. The record path has neither the separate token source nor the `issubset` guard.
- **Impact:** up to **+0.28** (party `strong_score`) of phantom confidence from name/party token overlap; can tip a
  borderline permit/equipment row over the 0.52 accept floor → false physical match → inflated physical capacity/risk.
- **Fix:** thread a real owner/operator field from the permit/equipment row as `row_party_tokens` and apply the queue
  path's `issubset` guard; or, until that field exists, drop `party_score` in the record path.
- **Fixture/test:** `test_record_match_does_not_count_name_tokens_as_party_overlap` — a permit whose only overlap with
  the project is the shared facility/owner token scores name OR party, not both.
- **Likely fn/file:** `_score_record_match` · `src/bubble/ingestion/physical/record_matching.py`

## 🟡 VERIFIED-REAL but NARROW / gated (lower than auditor's label)

### R2 — `document_acquisition` notional-scope gap: no `undrawn` / `available commitment` rejection  *(medium, narrow)*
The auditor flagged that `notional_commitment_scope` lacks terms like `undrawn`, `available commitment`,
`remaining availability`. Plausible: a facility's *total* (incl. undrawn) size could be classed as committed notional.
This is a **scope-label** gap (which bucket a number lands in), **not** an amount-fabrication. Worth one fixture if it
survives a quick check of `_notional_commitment_scope` against an "undrawn"/"availability" excerpt.
- **Fixture/test:** `test_undrawn_availability_excerpt_marks_non_committed_scope`
- **Likely fn/file:** `_notional_commitment_scope` · `edgar/document_acquisition.py`

### R3 — `document_acquisition` tranche-sum override is GATED, not unbounded  *(downgrade: low-med → regression fixture)*
Auditor framed `document_acquisition.py:856-858` ("explicit tranche total can replace deal notional at 5× tolerance")
as a medium **final-metric** risk. **Corrected:** two *different* code paths were conflated.
- The **override** at `:856-858` uses `_explicit_tranche_total`, which requires **≥2** tranches *each* extracted via
  `extraction_method == "explicit_debt_tranche_context_v1"` (`:1902-1911`). A single mis-extracted tranche **cannot**
  trigger it.
- The **5× tolerance** lives elsewhere — `_explicit_tranches_are_plausible` (`:1889-1899`, `tranche_total <=
  deal_notional * 5`) is applied inside `extract_debt_tranche_candidates` at `:1788`; if the explicit tranches sum to
  >5× the deal notional they are discarded and a single primary tranche is used instead.
- **Verdict:** this is a deliberate, gated mechanism (≥2 explicit debt-context tranches AND ≤5× plausibility cap), not
  an open door. Keep it; **lock the invariants with a regression fixture** so a refactor can't loosen them.
- **Fixture/test:** `test_tranche_override_requires_two_explicit_tranches_and_5x_cap` (1 tranche → no override;
  sum >5× → fall back to primary; 2 valid tranches ≤5× → override).
- **Likely fn/file:** `_explicit_tranche_total` / `_explicit_tranches_are_plausible` · `edgar/document_acquisition.py`

## 🔎 WORTH A LOOK (auditor medium; genuine tuning question)

- **MW phased upsert replace-vs-sum** (`queue_matching.py:~712`): upsert keeps `capacity > existing_capacity`
  (replace) rather than summing. For genuinely *phased* entries sharing a project_id this under-counts total MW
  (100MW + 50MW → 100MW). Opposite sign to the usual double-count worry, but worth confirming intent. Note: same-name
  generic dedup (R-false-3 below) is what *prevents* over-count here, so the two interact — decide intent explicitly.

---

## ❌ REFUTED — false alarms (do NOT change this code)

### F1 — filing_manifest "systematic false-negative crisis" (auditor: 3× HIGH) — REFUTED
The auditor's HIGH findings (30-40% 'securities' false-positives; 15-25% AI-keyword misses; asymmetric weighting) all
assume keyword scoring runs over the **filing body**. It does not. `score_filing_relevance` builds `searchable_text`
from **form + primary_document filename + description + item codes only** (`filing_manifest.py:605-614`). So:
- 'securities' boilerplate in a risk-factors body **never** scores; `securit` (`:82`) only fires on a filename/short
  description — cosmetic, and usually relevant when it does.
- 'compute cluster' / 'training cluster' in a body **never** mattered — body text isn't scored. The recall claim is an
  artifact of the body-text misread.
- The **75 threshold** is not a drop-gate for primaries. It gates (a) the `is_burry_relevant` label (`:151-153`) and
  (b) **exhibit follow-on fetch** (`min_parent_relevance_score`, `:374/:399`), and prospectus forms
  (S-1/S-3/424B…) **bypass it entirely** (`:796`). A sub-75 primary still lands in the manifest.
- **Genuine small kernel (not a bug):** keyword scoring is metadata-only and coarse, so a material-agreement 8-K whose
  *filename/description/items* lack a keyword leans on form+item base score to clear 75 for exhibit-follow. If we ever
  want richer recall, score against a fuller text field — but first confirm typical `8-K + item 1.01` already clears
  75 (it does: 65 + 25 = 90). **No action needed now.**

### F2 — physical "inverted filter accepts 0.08 matches" (auditor: HIGH) — REFUTED
`queue_matching.py:457` / `record_matching.py:487`: `if not reasons or confidence < 0.48: continue` is a **skip-guard**
— it skips a row that has *no reasons* **or** is *below threshold*. That is correct. The auditor read it as an
*acceptance* condition; their proposed `and` "fix" would **introduce** the very bug (keep low-confidence rows that have
any reason). Their example ("county-only 0.22 PASSES") is wrong: 0.22 < 0.48 → guard true → `continue` → skipped.

### F3 — physical "unconditional cross-state +0.06 bonus" (auditor: HIGH) — REFUTED
`record_matching.py:533` (`if project.state: confidence += 0.06; "state_match"`) looks unconditional, but candidates
are **pre-filtered by state**: projects are bucketed `projects_by_state[project.state]` (`:348`) and a row only ever
scores `projects_by_state.get(row_state, [])` (`:478`). So every scored project is already same-state; the inline
check is redundant-but-correct. A "CA permit → TX project +0.06" cannot occur — CA rows never see TX projects.

### F4 — (de-scoped) physical confidence rounding-before-cap (auditor: LOW) — cosmetic
`min(round(c,3), 0.99)` vs `round(min(c,0.99),3)` differs only in the 0.9949–0.9954 boundary; no behavioral impact on
the 0.48/0.52/0.72 decision floors. Not worth a change.

---

## Suggested order for Codex
1. **R1** (record_matching double-scoring) — only verified HIGH; smallest, most contained fix + fixture.
2. **R3** regression fixture (lock the tranche-override invariants — cheap insurance, no prod change).
3. **R2** undrawn-scope fixture (after a 2-line check of `_notional_commitment_scope`).
4. Decide intent on the **MW phased upsert** (replace vs sum) — design call, not a clear bug.
5. filing_manifest: **no action** (F1). Park "richer recall text field" as a future-recall idea only.

All line numbers verified against master `881b6c8`.
