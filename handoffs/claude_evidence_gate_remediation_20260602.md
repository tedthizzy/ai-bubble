# EvidenceGate Audit-Remediation Design — 2026-06-02

- **From:** Claude (worker) · **For:** Codex · **Branch:** `claude/report-qa`
- **Purpose:** close the **36 warnings** from `scripts/check_report_consistency.py` (`unaudited_high_impact_metric`) — high-impact (>$100B) USD metrics shown in `burry_question_answers` with no `EvidenceGate` `claim_audit`. Maps each metric group → the source/audit object that should gate it → proposed tier → where to build it. **Design doc; code only if it stays standalone** (per your note).
- **Snapshot:** report `…0412`. 38 distinct metrics: how_large 12, when_cracks 14, hidden_risks 11, who_bears 1.
- **Root cause:** `audit_report_evidence()` (`generate_final_burry_report.py:53-207`) audits only coverage/physical claims + the one UNSUPPORTED `final.bubble_conclusion`. Capital/debt-service/graph/timing/contagion metrics serialize straight from `*.to_dict()` into `key_metrics`/answers with no audit. The 0.25 cap stays correct; the gap is per-metric provenance.

**Key framing:** almost none of these are *unsupported* — they're **source-backed (SEC EDGAR) but pending adjudication**, or **broad-corpus context**. So remediation = build a `claim_audit` per metric carrying the real contributing `Provenance` list + the existing `human_review_status`, and let `EvidenceGate` classify. It will *correctly* cap most at 0.45–0.6 (pending/inferred), consistent with the 0.25 final cap — an honest audit trail, not a confidence boost.

---

## Group A — Capital-structure & debt-service notionals (how_large + who_bears, ~13)
`current_debt_like_notional_usd` $1.2T, `current_total_notional_usd` $1.28T, `current_distinct_debt_like_notional_usd` $795B, `current_debt_service_missing_rate_notional_usd` $690B, `current_debt_service_measured_rate_notional_usd` $511B, `current_notional_review_required_usd` $564B, `current_duplicate_candidate_notional_usd` $406B, `current_guarantee_linked_usd` $187B, `current_aggregate_obligation_distinct_notional_usd` $177B, `current_unmapped_downside_bearer_usd` $450B, …

- **Source/audit object:** the scoped `Deal` records (+ `debt_tranches`) that `CapitalStructureMetrics` / `DebtServiceMetrics` roll up — each carries `Provenance` (SEC_EDGAR, content_hash, `human_review_status`).
- **Proposed audit:** one `claim_audit` per metric, `evidence=` the contributing Deal `Provenance` list. Special cases:
  - `*_pending_review_*`, `*_review_required_*`, `*_duplicate_candidate_*` → **explicitly pending/triage** → audit with pending status → gate caps ~0.6. Should read as *candidate*, not measured.
  - `*_missing_rate_notional_*` → notional is measured but **rate evidence absent** → tier `SINGLE_SOURCE_ESTIMATE` + blocking issue "interest rate not extracted".
  - `*_distinct_*` / `*_duplicate_candidate_*` → these are your dedup outputs; audit value = post-dedup; note the duplicate delta.
- **Where:** add `provenance_sources: list[Provenance]` to `CapitalStructureMetrics`/`DebtServiceMetrics`, populated in `analyze_capital_evidence`/`analyze_debt_service` from the input batches; extend `audit_report_evidence()` to emit these audits.

## Group B — Graph exposure component notionals (hidden_risks, ~5)
`current_capital_exposure_largest_component_notional_usd` **$10.1T**, `…ai_infra_relevant_notional_usd` $658B, `…top_ai_infra_component_notional_usd` $615B, `incident_notional_usd` $362B.

- **Source/audit object:** `capital_exposure_graph` edges (each has source_uri/content_hash); the summary already separates AI-infra-relevant from broad.
- ⚠ **Scope label is the critical part:** the **$10.1T largest component is the BROAD corpus, not AI-infra**. Its audit must carry `scope=balance_sheet_context` so it is **never read as AI-infra bubble exposure**. (Aligns with the existing `capital_scope` gate.) AI-infra-relevant component → audit with the AI-infra edge provenances, pending → capped.
- **Where:** `capital_exposure_graph_summary.json` already has the field separation; `audit_report_evidence()` builds audits from the source-backed-edge counts + a representative provenance + the scope tag.

## Group C — Contract-contagion notionals (hidden_risks, ~2)
`current_contract_contagion_ai_infra_relevant_notional_usd` $1.919T, `notional_usd`/`ai_infra_relevant_notional_usd`.

- **Source/audit object:** contagion paths. But these are **exact-legal-name joins, largely unverified** — my `contagion_path_qa` found ~25% have quality issues (13% self-referential false joins, 22.6% duplicates, only 6.4% FULLY_CORROBORATED). → audit tier **INFERRED**, capped 0.45, with a blocking issue "exact-name join, not adjudicated".

## Group D — Timing refinancing / compute amounts (when_cracks, ~8)
`current_timing_capital_refinancing_usd_2024_2030` **$5.756T (broad)**, `…ai_infra_capital_refinancing` $292B, `…compute_amount` $219B, `maturity_wall_notional_usd_2024_2030` $118B, `maturing_notional_usd` $106B.

- **Source/audit object:** `timing_signal_summary` (each signal has provenance). Candidate timing indicators, pending adjudication → `SINGLE_SOURCE_ESTIMATE`/pending → capped. The **$5.756T total is BROAD** → label `scope=balance_sheet_context`; only the AI-infra subset ($292B) is the headline.

---

## Cross-cutting recommendations
1. Add `provenance_sources: list[Provenance]` to `CapitalStructureMetrics`, `DebtServiceMetrics`, and carry representative provenances through the graph/timing/contagion summaries; populate during `analyze_*`.
2. Extend `audit_report_evidence()` to emit one `claim_audit` per high-impact metric using those provenances + existing `human_review_status`. **Let `EvidenceGate` classify** — it already caps pending/inferred. This closes all 36 warnings with *honest* tiers (mostly 0.45–0.6), not a confidence boost.
3. **Scope-label broad-corpus totals** ($10.1T graph, $5.756T refinancing) as `balance_sheet_context` so they're never mistaken for AI-infra bubble exposure.
4. **Acceptance test = my checker:** once every high-impact answer metric has a matching audit, `check_report_consistency.py` goes to **0 `unaudited_high_impact_metric` warnings** — so it doubles as the regression gate for this remediation.

## Proposed regression-test names
`test_every_high_impact_answer_metric_has_audit` (checker returns `[]`), `test_broad_corpus_totals_labeled_balance_sheet_scope`, `test_pending_metric_audit_caps_confidence_at_0_6`, `test_missing_rate_notional_flagged_blocking`, `test_contagion_notional_audited_inferred`.

## Impact label
Future-architecture / report-rigor. No metric value changes; this adds the provenance/audit trail behind numbers already shown, and prevents broad-corpus totals from masquerading as AI-infra exposure. Standalone except the `provenance_sources` dataclass fields, which touch your analysis modules — flagged for your call (handoff-first, per your note).
