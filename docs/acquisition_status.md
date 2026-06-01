# Acquisition Status

Last updated: 2026-06-01 14:20 UTC.

This file is the operational snapshot for the current evidence corpus. Treat it
as a run log, not as a final investment conclusion.

## Current Corpus

- Latest evidence-gated report: `data/reports/BURRY_REPORT_EvidenceGated_20260601-1355.md`
- Evidence gate: not high-confidence final.
- Source invariant audit: passed, 49 CSV files and 3,266,269 rows scanned, 0 violations, 0 warnings.
- Source catalog artifacts: 586 / 586 attempted in the latest broad public-source run.
- Latest source-catalog extracted rows: 4,878,655.
- Covered filings: 41,688.
- Raw source documents: 25,852.
- Source-backed normalized entities: 789,787.
- Expanded SEC CIK candidates: 2,356.
- Projects: 17,226.
- Source-backed deals: 49,717.
- Source-backed compute rows: 166.
- Source-backed timing signals: 1,324.
- Pending source-backed review items: 1,437.
- Ownership graph: 425,765 LEI nodes, 425,679 named nodes, and 643,828 source-backed relationships.

## Latest EDGAR Manifest Run

Manifest:

- `data/manifests/edgar_filing_manifest_20260601-142009.csv`
- 166,653 document rows from 166,653 filings.
- 2,356 source-backed CIKs requested; 2,354 returned.
- Window: 2024-01-02 through 2026-06-01.
- Burry-relevant filings: 28,084.
- Exhibit indexes were not included in this broad pass.
- Errors: 0.

This is the next EDGAR acquisition backlog. The prior high-relevance acquired
tranche remains documented below for continuity.

## Prior EDGAR Acquisition Run

Manifest:

- `data/manifests/edgar_filing_manifest_20260601-131615.csv`
- 40,919 document rows from 35,613 filings.
- 5,306 exhibit rows.
- 144 CIKs.
- Window: 2023-01-03 through 2026-06-01.

Acquisition:

- `data/edgar_acquisition/edgar_document_inventory.csv`
- `data/edgar_acquisition/deals.csv`
- Newly acquired tranche: remaining EDGAR rows with relevance score >= 50.
- Documents attempted at that threshold: 13,658.
- Resumed from prior runs: 13,158.
- Newly downloaded in this tranche: 500.
- Errors: 0.
- Deal candidates after merge: 6,516 in the EDGAR acquisition summary; 49,717 source-backed deals across the full coverage report.

Remaining backlog in this manifest:

- Score >= 50: 0 rows.
- Score >= 40: 634 rows, mostly Forms 3/4/4-A and similar low-signal ownership/proxy rows.
- All remaining rows: 15,772.

The next EDGAR expansion should come from new CIKs, deeper date windows, or
targeted forms, rather than indiscriminately downloading the remaining low-score
ownership-form tail.

## Parallel Acquisition Posture

SEC-hosted acquisition is bounded by the fair-access lane:

- Global worker pool: up to 64 workers for local parsing/resume throughput.
- `sec.gov` request rate: 8 requests/second.
- `sec.gov` domain concurrency: 8.
- Retries: exponential backoff.
- Resume mode: enabled by default.

Non-SEC source acquisition is also bounded:

- Global worker pool: default 64 workers.
- Other-domain concurrency: default 16.
- Other-domain request rate: default 16 requests/second per domain key.
- Raw artifact, source URI, retrieval timestamp, local path, content hash, and extracted rows are retained.

## Current Analysis Outputs

Coverage counts acquired source rows and normalized extracted rows. Derived graph
node/edge CSVs are reported in graph summaries, not folded back into source
coverage counts.

Capital exposure graph:

- Nodes: 4,681.
- Source-backed edges: 7,444.
- Total edge notional: $2.954T.
- AI-infra-relevant notional: $280.45B.
- AI-infra-relevant edges: 205.

Ownership graph:

- Rows scanned: 650,379.
- Nodes: 425,765.
- Named nodes: 425,679.
- Active legal-entity nodes: 379,395.
- Source-backed relationships: 643,828.
- Active relationships: 469,194.
- Direct consolidation edges: 183,849.
- Ultimate consolidation edges: 191,834.
- Fully corroborated relationships: 415,829.
- Quantified relationships: 63,448.
- Outputs: `data/graph/ownership_nodes.csv`, `data/graph/ownership_edges.csv`, and `data/graph/ownership_graph_summary.json`.

Timing layer:

- Peak stress quarter: 2026-Q2.
- Candidate stress window: 2025-Q3 to 2026-Q4.
- Capital refinancing 2024-2030: $1.724T.
- AI-infra capital refinancing 2024-2030: $267.99B.
- Physical capacity 2024-2030: 177,293 MW.

Review queue:

- Critical items: 18.
- High items: 291.
- AI-infra-relevant items: 583.
- Pending AI-infra-relevant distinct capital notional: $793.04B.

Compute economics:

- GPU price observations: 45.
- Depreciation policies: 49.
- TAM claims: 10.
- Capex payback cases: 2.
- EPS depreciation impacts: 2.
- Chip supply observations: 9.

## Next Acquisition Priorities

1. Acquire documents from `data/manifests/edgar_filing_manifest_20260601-142009.csv`,
   prioritizing score >= 75 first, then score >= 50.
2. Add more source catalogs for state PUCs, local zoning/air permits, data-center
   leases, equipment financing, and project-level utility filings.
3. Improve named counterparty extraction on large unmatched EDGAR rows, especially
   aggregate lease obligations and prospectus supplements.
4. Increase compute-economics evidence by adding dated resale/rental-rate sources,
   hyperscaler depreciation/EPS bridges, and source-backed TAM comparators.
5. Keep every production metric evidence-gated until the review queue is cleared
   or corroborated enough to support high-confidence claims.
