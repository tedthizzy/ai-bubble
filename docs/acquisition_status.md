# Acquisition Status

Last updated: 2026-06-01 17:01 UTC.

This file is the operational snapshot for the current evidence corpus. Treat it
as a run log, not as a final investment conclusion.

## Current Corpus

- Latest evidence-gated report: `data/reports/BURRY_REPORT_EvidenceGated_20260601-1701.md`
- Evidence gate: not high-confidence final.
- Source invariant audit: passed, 53 CSV files and 8,537,486 rows scanned, 0 violations, 0 warnings.
- Source catalog artifacts: 586 / 586 attempted in the latest broad public-source run.
- Latest source-catalog extracted rows: 4,878,655.
- Covered filings: 197,243.
- Raw source documents: 53,682.
- Source-backed normalized entities: 7,690,577.
- Expanded SEC CIK candidates: 2,356.
- Projects: 17,226.
- Source-backed deals: 57,363.
- Source-backed contract tranches: 1,194.
- Source-backed compute rows: 166.
- Source-backed timing signals: 2,946.
- Pending source-backed review items: 2,415.
- Ownership graph: 425,765 LEI nodes, 425,679 named nodes, and 643,828 source-backed relationships.

## Phase Transition Readiness

The system is ready to move from catalog/entity/ownership structuring into the
next evidence-building phase, but acquisition should remain an always-on intake
workstream rather than be treated as complete.

Ready now:

- broad source-backed entity expansion from acquired filings, PPAs, tracker,
  permit, equipment, and GLEIF records
- bounded parallel acquisition with resume, retries, content hashes, retrieval
  timestamps, source URIs, local raw paths, and normalized extracted rows
- source-backed ownership graph from GLEIF relationship records plus LEI legal
  names
- review queue, capital exposure graph, weak-link, timing, and compute-economics
  scaffolding
- contract-level EDGAR enrichment for first-pass debt/bond tranches, collateral
  snippets, guarantors, SPV/non-recourse flags, rates, and maturities

Must move next:

- continued EDGAR/source acquisition as an always-on workstream for future
  filings, lower-priority backlog rows, and new source catalogs
- exhibit-enabled EDGAR manifests for EX-2, EX-4, EX-10, and EX-99 documents
- continued contract-level extraction for leases, debt, guarantees, collateral,
  tranches, PPAs, construction, and project-finance terms
- human review triage before any high-confidence bubble conclusion
- deeper contagion modeling that joins contract edges, ownership/SPV edges,
  guarantee/collateral terms, maturities, and physical execution risks
- source-backed GPU depreciation, TAM, payback, EPS, and chip-supply evidence

Not ready:

- a high-confidence final bubble call
- full exhibit coverage across the expanded manifest
- reviewed contract-level extraction at the scale needed for professional-grade
  leverage, SPV, collateral, and downside-risk conclusions

## Latest EDGAR Exhibit Run

Manifest:

- `data/manifests/edgar_exhibit_manifest_20260601-163528.csv`
- parent primary filings inspected: 1,740 with relevance score >= 120
- parent filings with candidate exhibits: 1,196
- exhibit document rows: 2,551
- exhibit mix: 1,353 EX-10 material contracts, 297 EX-4 debt/security
  instruments, 59 EX-2 transaction agreements, and 842 EX-99 supplemental
  disclosure exhibits
- errors: 0

Acquisition and contract enrichment:

- documents attempted/downloaded: 2,551 / 2,551
- documents resumed in latest enrichment pass: 2,551
- deal candidates extracted in the run: 2,198
- contract tranches materialized: 1,194
- tranche rows with interest rate: 570
- tranche rows with maturity: 683
- tranche rows with collateral description: 945
- tranche rows with guarantors: 42
- bytes downloaded/read: 1,009,835,015
- errors: 0
- worker pool: 64
- SEC request lane: 8 requests/second and 8-domain concurrency
- output directory: `data/edgar_acquisition`

This was built through the focused follow-on command
`scripts/build_edgar_exhibit_manifest.py`, which reads an existing primary
manifest and fetches only SEC archive directory indexes for selected high-signal
parent filings.

## Latest Primary EDGAR Acquisition Run

Completed 2026-06-01 16:20 UTC:

- `data/manifests/edgar_filing_manifest_20260601-142009.csv`
- relevance threshold: score >= 75
- documents attempted/downloaded: 28,084 / 28,084
- documents resumed: 2,480
- deal candidates extracted: 6,882
- bytes downloaded/read: 29,417,355,227
- errors: 0
- worker pool: 64
- SEC request lane: 8 requests/second and 8-domain concurrency
- output directory: `data/edgar_acquisition`
- latest inventory: `data/edgar_acquisition/edgar_document_inventory.csv`
- latest deal candidates: `data/edgar_acquisition/deals.csv`
- latest summary: `data/edgar_acquisition/edgar_document_acquisition.summary.json`

This run acquired primary documents only because the broad manifest did not
include exhibit indexes. The next EDGAR pass should build an exhibit-enabled
manifest from the same expanded CIK set and prioritize contract exhibits.

## Latest EDGAR Manifest Run

Manifest:

- `data/manifests/edgar_filing_manifest_20260601-142009.csv`
- 166,653 document rows from 166,653 filings.
- 2,356 source-backed CIKs requested; 2,354 returned.
- Window: 2024-01-02 through 2026-06-01.
- Burry-relevant filings: 28,084.
- Exhibit indexes were not included in this broad pass.
- Errors: 0.

The score >= 75 tranche has now been acquired. The prior high-relevance acquired
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

- Nodes: 6,209.
- Source-backed edges: 9,358.
- Total edge notional: $6.511T.
- AI-infra-relevant notional: $280.75B.
- AI-infra-relevant edges: 206.

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
- Candidate stress window: 2025-Q3 to 2027-Q1.
- Capital refinancing 2024-2030: $6.618T.
- AI-infra capital refinancing 2024-2030: $269.02B.
- Physical capacity 2024-2030: 177,293 MW.
- Compute amount 2024-2030: $219.41B.
- Tranche-backed capital timing descriptions: 453.

Review queue:

- Critical items: 38.
- High items: 397.
- AI-infra-relevant items: 584.
- Pending capital distinct notional: $10.903T.
- Pending AI-infra-relevant distinct capital notional: $793.04B.
- Pending compute claim amount: $398.24B.

Weak links:

- Candidates: 514.
- High or critical candidates: 16.
- Capital candidates: 206.
- Physical candidates: 250.
- Combined capital/physical candidates: 39.
- Debt-service candidates: 19.
- AI-infra-relevant weak-link notional: $280.75B.

Compute economics:

- GPU price observations: 45.
- Depreciation policies: 49.
- TAM claims: 10.
- Capex payback cases: 2.
- EPS depreciation impacts: 2.
- Chip supply observations: 9.

## Next Acquisition Priorities

1. Build the next exhibit-enabled follow-on manifest from the expanded CIK set with
   `scripts/build_edgar_exhibit_manifest.py`, lowering the parent relevance
   threshold from 120 toward 75 after the current high-signal exhibit tranche and
   tranche rows are triaged.
2. Expand contract-level extraction beyond the first deterministic tranche pass:
   lease economics, debt waterfalls, guarantee scope, collateral packages, PPA
   contract terms, construction obligations, and project-finance covenants.
3. Rebuild the review queue after each material acquisition or extraction run;
   clear or corroborate critical/high items before upgrading any conclusion to
   high confidence.
4. Run the score >= 50 primary-document tail only if the score >= 75 review
   queue indicates incremental value after exhibit extraction.
5. Add more source catalogs for state PUCs, local zoning/air permits, data-center
   leases, equipment financing, and project-level utility filings.
6. Improve named counterparty extraction on large unmatched EDGAR rows, especially
   aggregate lease obligations and prospectus supplements.
7. Increase compute-economics evidence by adding dated resale/rental-rate sources,
   hyperscaler depreciation/EPS bridges, and source-backed TAM comparators.
8. Keep every production metric evidence-gated until the review queue is cleared
   or corroborated enough to support high-confidence claims.
