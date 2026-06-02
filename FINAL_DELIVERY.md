# Historical Delivery Status - bubble (Evidence-Gated Prototype)

**Date:** 2026-06-02  
**Status:** Not complete. The previous "final delivery" claim is superseded.

This file is a checkpoint note, not the live run log. Use
`docs/acquisition_status.md` as the current operational source of truth for
corpus counts, adjudication metrics, report paths, and next extraction gaps.

## What Is True Now

The repository has a useful prototype for the Burry-style AI/data center financing system:

- Domain models for entities, deals, risks, assumptions, cash flows, physical assets, and provenance.
- EDGAR-oriented extraction scaffolding.
- In-memory graph fallback plus Neo4j path.
- Red-flag and scenario-engine scaffolding.
- Physical deliverability risk models and deterministic scoring for grid queues, permits, long-lead equipment, and construction progress.
- CSV-based physical evidence ingestion via `scripts/ingest_physical_evidence.py` / `just physical-evidence`.
- SEC filing manifest generation via `scripts/build_edgar_manifest.py` / `just edgar-manifest`, producing a source-backed extraction backlog with relevance scores.
- EDGAR document acquisition via `scripts/acquire_edgar_documents.py` / `just edgar-acquire`, storing raw documents with accession/document ids, retrieval metadata, content hashes, and pending-review deal candidates.
- Generic source catalog acquisition via `scripts/acquire_source_catalog.py` / `just source-acquire`, storing raw filings, permits, PPAs, lease agreements, queue records, ownership records, tracker records, and extracted rows with source URI, retrieval timestamp, hashes, local paths, and record indexes.
- Source coverage reporting via `scripts/source_coverage_report.py` / `just source-coverage`, counting filings, entities, projects, queue records, permits, PPAs, lease agreements, ownership/tracker records, raw documents, and source-backed deals.
- Source-backed ownership/consolidation graph generation via `scripts/build_ownership_graph.py` / `just ownership-graph`, turning acquired GLEIF relationship records into LEI nodes, direct/ultimate consolidation edges, relationship statuses, validation fields, quantifiers, and provenance-bearing graph CSVs.
- Production source-data invariant that rejects inferred provenance in deal/source ingestion paths.
- Evidence-gated capital-structure metrics for debt-like exposure, SPV/off-balance-sheet exposure, quarterly refinancing walls, concentration, and downside bearers.
- CSV-based capital/deal evidence ingestion via `scripts/ingest_capital_evidence.py` / `just capital-evidence`.
- Streamlit UI scaffolding.
- Evidence-gated report generation.

The important change is that ecosystem-scale conclusions are now blocked from being presented as high-confidence when they are only inferred. The generated report labels current metrics as directional hypotheses and caps report confidence accordingly.

Latest verified evidence-gated report at this checkpoint:

- Markdown: `data/reports/BURRY_REPORT_EvidenceGated_20260602-0857.md`
- JSON: `data/reports/BURRY_REPORT_EvidenceGated_20260602-0857.json`
- `high_confidence_final`: `false`
- Evidence audit coverage now includes analyzer-level capital, compute, and
  debt-service audits plus explicit row/artifact-backed audits for high-impact
  Burry-answer rollups. The remaining consistency warnings are doc-pattern
  checks and do not open the gate.
- Source invariant audit: passed across 63 CSV files and 9,208,844 rows scanned
  with 0 violations and 0 warnings.
- Acquired source artifacts: 66,660 / 66,660 attempted.
- Covered filings: 197,243.
- Source-backed normalized entities: 789,787.
- Projects: 17,227.
- Source-backed deals: 62,952.
- Source-backed compute rows: 149.
- Source-backed timing signals: 3,263.
- Pending source-backed adjudication items: 6,773.
- Automated materiality adjudication decisions: 6,663 decisions, with 4,476
  supported blockers, 2,187 still requiring deeper extraction, 2,930 approved
  metric rows, and $4.378T deduped final metric support across 1,581
  source-instrument/economic-obligation metric groups. Semantic hard flags are now zero
  in approved metric rows; 157 approved rows remain indeterminate semantic
  review candidates.

Latest capital and timing outputs:

- Capital exposure graph source-backed edges: 7,526.
- Capital exposure graph total edge notional: $864.18B.
- AI-infra-relevant graph notional: $5.16B.
- In-scope debt-like notional: $1.201T.
- Broader materiality-adjudicated supported exposure: $4.378T across 1,581
  metric groups; this is a different scope from the curated capital-structure
  deal-graph debt-like metric above, not an additive increment.
- Established direct/watchlist AI-data-center-linked support inside that broader
  materiality metric is $0.370T ($0.074T direct and $0.296T watchlist);
  $4.008T, or 91.6%, remains source-backed but not yet thesis-linked.
- Unconverted HKD face-value rows are blocked from metric use pending
  source-backed USD conversion; six rows now carry that extraction gap.
- Ownership graph LEI nodes: 425,765.
- Ownership graph source-backed relationships: 643,828.
- Ownership graph active relationships: 469,194.
- Ownership graph direct consolidation edges: 183,849.
- Ownership graph ultimate consolidation edges: 191,834.
- Peak stress quarter: 2026-Q2.
- Candidate stress window: 2025-Q3 to 2027-Q3.
- Whole-corpus capital refinancing 2024-2030: $3.2533T.
- AI-infra capital refinancing 2024-2030: $227.22B. The forward signal from
  the 2026-Q2 report as-of quarter is $99.31B, with $127.91B already matured
  before that quarter and a forward AI-infra peak of $22.25B in 2027-Q3.
- Project tracker physical capacity: raw tracker capacity is 552,455 MW; the
  calibrated distinct-site rollup now reports 543,335 MW after collapsing 42
  duplicate tracker rows across 36 groups.

See `docs/acquisition_status.md` for the current run log and acquisition backlog.

## What Is Not Yet True

The system does not yet satisfy the full vision:

- It has not completed review-grade coverage of 1,200-2,000+ meaningful entities,
  even though the raw normalized entity universe is now much larger.
- It has crossed the numeric target for extracted source-backed deal rows, but
  those rows are not yet review-cleared or fully deduplicated into final
  economic exposures.
- It has measured multi-trillion-dollar graph exposure, but it has not yet
  proven full visible plus hidden ecosystem leverage with enough corroboration
  to support a final bubble conclusion.
- It has not built complete project-level power, permitting, construction, and asset coverage.
- It has not proven bubble/no-bubble conclusions with measured and corroborated evidence.
- It has not produced a professional-investor-grade final report backed by real source coverage.

## Current Command

```bash
uv run python scripts/generate_final_burry_report.py
```

This produces an evidence-gated report under `data/reports/`. It is useful as a thesis scaffold and quality-control artifact, not as a final answer.

Physical evidence can be loaded with:

```bash
just physical-evidence data/physical --as-of 2026-12-31
```

Capital evidence can be loaded with:

```bash
just capital-evidence data/capital --as-of 2026-12-31 --near-term-end 2029-12-31
```

## Next Critical Work

1. Replace seed-scale estimates with measured EDGAR, debt, lease, PPA, permit, grid queue, and project tracker records.
2. Expand EDGAR document acquisition to exhibit indexes and attachment-level downloads, not just primary documents.
3. Populate real source catalogs for FERC, ISO queues, state PUC/EPA/local permits, ownership registries, and project trackers, then promote repeated catalogs into dedicated adapters where needed.
4. Build the master entity/project list with real identifiers, source URIs, and priority scores.
5. Feed real queue, permit, equipment, and construction observations into `PhysicalRiskEngine` for the top 100-150 projects.
6. Feed real credit agreements, bond filings, leases, PPAs, and guarantee disclosures into `CapitalStructureAnalyzer` at ecosystem scale.
7. Expand graph schema coverage for SPVs, guarantees, tranches, collateral, and risk-transfer paths.
8. Add source-backed evidence audits to entity-level reports, not only the Go Big report.
9. Require automated LLM adjudication or corroborating source evidence for
   high-impact claims before any report can be labeled final. Legacy fields
   named `human_review_status` are adjudication-status fields, not an operator
   approval gate.

The system should remain skeptical of its own outputs until the evidence gate can prove the claims.
