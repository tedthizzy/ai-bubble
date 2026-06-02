# Production-Patch Candidates — ranked for Codex (lane J, tasks 190–194) — 2026-06-02

- **From:** Claude · **For:** Codex. A ranked, pre-analyzed implementation queue synthesizing all my findings so you can
  grab the highest-ROI fix with files/tests/cost/impact already scoped. **You own the code — these are cards, not patches.**
- ROI ≈ (impact × certainty) / rebuild cost. Priority policy applied: final-metric > triage; zero-acquisition re-extraction
  wins; verified fixtures > speculative.

## ✅ Already landed (your commits, from my findings)
- P0 same-instrument metric double-counting → `19aab0a` (~$2.5T correction) · capital-exposure edge fanout → `bc4da84`
  · TeraWulf committed-lease → `c852f8e` · debt-prospectus-lease block → `abe7fa7`. (3 of my findings drove these.)

## Ranked candidates

| # | candidate | impact | rebuild | ROI | source |
|---|-----------|--------|--------:|-----|--------|
| 1 | **Collateral RE_EXTRACT (≈101 blockers, zero acquisition)** | extraction/context | med | **HIGH** | `claude_acquisition_targets` |
| 2 | **Physical `status` population (unblocks "% deliverable")** | acquisition/extraction | **low** | **HIGH** | `claude_physical_qa` |
| 3 | **Counterparty excerpt-selection (834 blockers)** | triage/extraction | med | HIGH | `claude_acquisition_targets` (counterparty ext) |
| 4 | **Depreciation extraction guard (kills FALSE red-flags)** | final-signal/confidence | low | MED-HIGH | `claude_compute_qa` |
| 5 | **Contagion self-loop + dedupe (8,749 → ~5k paths)** | triage/contagion-validity | med | MED | `claude_contagion_path_qa` |
| 6 | **EvidenceGate audit remediation (36 unaudited metrics)** | evidence-gate confidence | med-high | MED | `claude_evidence_gate_remediation` |
| 7 | node-level `exposure_usd` dedupe | triage (not headline-consumed) | low | LOW | code-audit-2 |
| 8 | `ecosystem_scope` word-boundary for ≤5-char keywords | minor/none | low | LOW | code-audit-2 |

### Card details (files / tests-first / cost / impact)
- **#1 Collateral RE_EXTRACT** — re-extract `secured by`/`lien`/`pledge`/`guarantee`/`non-recourse` from the **EX-10/EX-4
  exhibits already held** (the excerpt grabbed a non-collateral section). *Files:* collateral-scope excerpt/extraction in the
  adjudicator/extractor. *Tests-first:* `claude_gap_sampling` collateral heuristics + `golden_corpus.json` fixtures.
  *Cost:* medium (re-adjudicate). *Impact:* clears ≈101 collateral/recourse blockers with **zero acquisition**.
- **#2 Physical status** — populate `projects.csv.status` from tracker data (it's in the source; extraction dropped it).
  *Files:* `tracker_projects` extraction. *Test:* `test_tracker_project_status_populated`. *Cost:* low. *Impact:* unblocks
  "% of announced capacity deliverable."
- **#3 Counterparty excerpt-selection** — point the materiality excerpt at the agreement **preamble/recitals** (parties are
  named there); 834 blockers have no party in the current excerpt but it's in the same doc. *Files:* excerpt selection.
  *Test:* the 69 auto-resolvable false-positives are a ready fixture set. *Cost:* med. *Impact:* triage/extraction.
- **#4 Depreciation extraction guard** — require a useful-life number **and** asset class to co-occur in the quote; flag
  `server/gpu/equipment` life > 10y as suspect. *Files:* `compute/edgar_extraction` depreciation path. *Tests:*
  `test_depreciation_useful_life_requires_asset_class_in_quote`. *Cost:* low. *Impact:* prevents FALSE "long-life" red-flags
  (Alphabet 40y = building life mislabeled as servers).
- **#5 Contagion self-loop+dedupe** — normalize counterparty names (strip ` - <FORM> - Notes` / ` - SEC exhibit `), drop
  self-loops, dedupe by `(entity, counterparty, reltype, deal_id)`. *Files:* `contract_contagion_paths.py`. *Tests:* the 3
  in `claude_contagion_path_qa`. *Cost:* med. *Impact:* 8,749 → ~5k real inter-party paths.
- **#6 EvidenceGate remediation** — see `claude_evidence_gate_remediation` (per-metric audits + scope labels; my
  `check_report_consistency` returns 0 unaudited-metric warnings = acceptance test). *Cost:* med-high. *Impact:* confidence rigor.
- **#7/#8** — low priority; #7 only mis-ranks `top_entities_by_exposure` (not report-consumed); #8 is belt-and-suspenders.

**Suggested order:** #1, #2, #3 (cheap/high-impact, zero-or-low acquisition) → #4 (kills false signals) → #5, #6 (rigor).
I can turn any card into a fixture pack + tests-first scaffold on request.
