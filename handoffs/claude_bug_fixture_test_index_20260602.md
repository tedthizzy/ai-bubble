# Bug-class → fixture → test → production-function index (task 186) — 2026-06-02

- **From:** Claude · **For:** Codex. A single map from each finding to its fixture, proposed test name, the production
  function likely responsible, and status — so you can jump straight from a bug class to where it's fixed and tested.
- Status: ✅ landed in main · ⏳ pending (candidate in `claude_production_candidates`) · 🔎 observation only.

| bug class | impact | fixture / finding source | proposed test name | likely production fn / file | status |
|-----------|--------|--------------------------|--------------------|-----------------------------|--------|
| same-instrument metric double-count | final-metric | `golden_corpus` entity_family; `claude_materiality_dedupe_design` | `test_same_instrument_one_metric_contribution_across_affiliates` | `materiality_adjudication_results` (final-metric grouping) | ✅ `19aab0a` |
| debt-prospectus approved as aggregate lease | final-metric | `golden_corpus` aggregate_shelf | `test_debt_securities_prospectus_not_approved_as_aggregate_lease` | `materiality_adjudication_results` | ✅ `abe7fa7` |
| TeraWulf committed-lease blocked by "aggregate" | final-metric | `claude_gap_sampling` aggregate_shelf (pkt `a7ef564972c7d6fa`) | `test_aggregate_word_alone_does_not_block_committed_transaction` | committed-lease detector | ✅ `c852f8e` |
| capital-exposure edge inherits extraction fanout | triage→final (graph) | `claude_code_audit` Finding 1 | `test_capital_edge_notional_dedupes_same_instrument` | `capital_exposure_graph` edge agg | ✅ `bc4da84` |
| contagion self-loop (entity→own tranche label) | triage / contagion-validity | `claude_contagion_path_qa` | `test_contagion_drops_entity_to_own_tranche_self_loop` | `contract_contagion_paths.py` | ⏳ #5 |
| contagion duplicate paths | triage | `claude_contagion_path_qa` | `test_contagion_dedupes_repeated_entity_counterparty_paths` | `contract_contagion_paths.py` | ⏳ #5 |
| counterparty role already in quote (false-pos) | triage / extraction | `golden_corpus` counterparty_role (69 FPs) | `test_role_keyword_in_quote_clears_counterparty_gap` | adjudicator counterparty path | ⏳ #3 |
| counterparty excerpt = wrong section (834) | triage / extraction | `counterparty_role_targets.csv` | `test_counterparty_excerpt_targets_agreement_preamble` | excerpt selection | ⏳ #3 |
| collateral secured/lien in quote (false-pos) | extraction | `golden_corpus` collateral; `claude_gap_sampling` | `test_secured_lien_language_clears_collateral_gap` | adjudicator collateral path | ⏳ #1 |
| collateral terms in held EX-10 (re-extract) | extraction / zero-acq | `acquisition_targets_collateral_recourse.csv` (101) | `test_collateral_reextracted_from_held_exhibit` | collateral extractor | ⏳ #1 |
| recourse first-mortgage / non-recourse (false-pos) | extraction | `golden_corpus` recourse; `claude_gap_sampling` | `test_first_mortgage_and_limited_guaranty_clear_recourse_gap` | adjudicator recourse path | ⏳ |
| depreciation useful-life mislabel/unsupported | compute-signal / confidence | `claude_compute_qa` | `test_depreciation_useful_life_requires_asset_class_in_quote` | `compute/edgar_extraction` | ⏳ #4 |
| physical project status 100% empty | acquisition / extraction | `claude_physical_qa` | `test_tracker_project_status_populated` | `tracker_projects` extraction | ⏳ #2 |
| physical generic-name MW double-count | triage / graph | `claude_physical_qa` (meta/amazon data center) | `test_projects_canonicalized_before_mw_rollup` | physical_capacity / tracker | 🔎 |
| ~80 high-impact report metrics unaudited | evidence-gate confidence | `claude_evidence_gate_remediation` | `test_every_high_impact_answer_metric_has_audit` (= my verifier returns 0) | `generate_final_burry_report.audit_report_evidence` | ⏳ #6 |
| node-level `exposure_usd` double-count | triage (not headline-consumed) | `claude_code_audit` | `test_node_exposure_from_incident_edges_not_both_endpoints` | `capital_exposure_graph` node agg | 🔎 |
| ecosystem_scope short-keyword substring | minor | `claude_code_audit` | `test_short_scope_keyword_word_boundary` | `ecosystem_scope` | 🔎 |

**Acceptance hooks already mergeable (in main / my branch):** `check_report_consistency` (stale paths/counts/confidence/
artifact-freshness/summary-CSV/metric-audit-coverage), `check_provenance_integrity` (divergent/invalid/conflicting hashes),
`simulate_metric_aggregation` (grouping-key deltas), `golden_corpus.json` (89 verified fixtures). The ⏳ rows map to the
ranked cards in `claude_production_candidates_20260602.md`.
