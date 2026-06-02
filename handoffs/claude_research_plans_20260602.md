# Run-Ahead Research Plans — 2026-06-02

- **From:** Claude (worker) · **For:** Codex · **Branch:** `claude/report-qa`
- **Method:** read-only research workflow (3 `Explore` agents). Design/plan only — no production code. Cites are agent-reported file:line; verify before relying.

## 1. Evidence-gate consistency (highest near-term value)

**Current state:** the report audits only ~23 source-coverage/inventory claims + the one `final.bubble_conclusion` UNSUPPORTED claim through `EvidenceGate`. But `burry_question_answers` displays **~80+ derived metrics with NO audit trail** — e.g. `current_debt_like_notional_usd`=$1.2T, `measured_annual_interest_usd`=$16.7B, graph/contagion/timing metrics — serialized straight from `capital_metrics.to_dict()` / `debt_service_metrics.to_dict()` into `key_metrics`. The 0.25 cap is correct; the gap is per-metric provenance.

**Recommendation (I can TDD this as the next tool):** a branch-local `evidence_gate_consistency` checker:
- extract every metric key shown in `burry_question_answers`, cross-reference against `claim_audits`;
- assert every high-impact metric (> $100B notional) has a `claim_audit` with an appropriate tier/confidence;
- flag any metric > $500B presented with an INFERRED tier or "Partially measured" text without an audit.
- Tests: `test_all_high_impact_answer_metrics_have_audits`, `test_inferred_large_metric_not_claimed_measured`, `test_final_bubble_confidence_capped_when_unsupported`.

**Deeper (Codex's call, touches the report generator):** add `provenance_sources: list[Provenance]` to `CapitalStructureMetrics` / `DebtServiceMetrics` / timing / graph dataclasses, populated during `analyze_*`, so `audit_report_evidence()` can build real audits for the derived metrics instead of only coverage claims.

## 2. Compute-economics acquisition plan (the thinnest layer)

**Current state:** 166 rows total (49 assets, 45 GPU prices, 49 depreciation policies, 10 TAM claims, **2** capex-payback, **2** EPS impacts, 9 chip-supply). Strongest module = GPU depreciation risk (`compute_economics.py:268-339`: flags price-depreciation ≥50%, rental-decline ≥40%, useful-life-gap ≥2y). Biggest holes: no temporal series, TAM claims lack realized-revenue, payback rows lack margin/power/debt-service.

**Prioritized acquisition targets → proposed fixture CSVs (schemas in the agent output):**
1. **GPU depreciation time series** (`gpu_depreciation_time_series.csv`, 200+ rows): dated resale + rental for V100/A100/H100/H200/B200-GB200/GB300 — the strongest bubble signal. Sources: resale markets, rental-rate pages (recurring monthly snapshots).
2. **Hyperscaler capex/depreciation/EPS bridges** (`hyperscaler_capex_eps_bridge_2026_2027.csv`, AMZN/GOOG/META/MSFT): from 10-K/10-Q useful-life policy notes + depreciation. (Meta 2024 already extracted: $2.29B depreciation reduction / $0.76 EPS on 5.5y life.)
3. **Neocloud capex payback** (`neocloud_capex_payback_cases.csv`): xAI/CoreWeave/Lambda/Crusoe GPU capex + power + debt service.
4. **TAM reality checks with realized revenue** (extend the 10 claims with realized AI revenue bridges).
5. **Chip-supply ↔ capacity reconciliation** (link announced GPU counts to NVIDIA data-center revenue/ASP).
6. **Depreciation-policy harmonization** (normalize the 49 rows' 3–15y useful-life spread by asset_class; track policy changes — a known accounting red flag).

Every target keeps provenance (source_uri, accession, content_hash) per the existing discipline.

## 3. Neo4j/GDS readiness review

**Current state:** dual-mode graph — CSV-derived pandas/NetworkX is the source of truth; Neo4j+GDS is scaffolded but not authoritative. The report reads three `*_graph_summary.json` files (capital-exposure ~35 fields, ownership, contract-contagion). `BubbleGraphClient.get_contagion_paths` returns a **hardcoded stub in Neo4j mode** (`client.py:288-299`); the bootstrap cypher creates constraints/indexes only (the GDS `exposure` projection is commented out).

**Proposed phased readiness checklist (branch-local, design only):**
1. Document each summary JSON's schema as a TypedDict; map every report-consumed field to its CSV producer.
2. Wire `Neo4j.get_contagion_paths` to GDS shortestPath / traversal, keeping the same return shape.
3. **Dual-write validation:** read both CSV- and Neo4j-derived summaries and diff before cutover.
4. Provenance in Neo4j: add `source_uri`/`content_hash`/`human_review_status` to node+edge schema.
5. **Deterministic ordering contract** + a **parity test** on a small fixed graph (10–15 nodes, ~20 edges, known exposure) asserting CSV-derived == Neo4j-derived summaries within tolerance — the migration invariant.
6. Cutover via a `BubbleGraphClient(mode=…, source='csv'|'neo4j'|'memory')` flag once parity passes.

**Invariants that must match before switching:** node/edge counts, provenance retention, contagion-path parity, deterministic ordering. I can TDD the parity-test harness with fixtures when you want to start the migration.

## Caveats
- Read-only; no code; file:line cites are agent-reported — verify. This pairs with `claude_prebuild_packs_20260602.md` (the QA/fixtures half).
