# Acquisition Status

Last updated: 2026-06-01 20:36 UTC.

This file is the operational snapshot for the current evidence corpus. Treat it
as a run log, not as a final investment conclusion.

## Current Corpus

- Latest evidence-gated report: `data/reports/BURRY_REPORT_EvidenceGated_20260601-2034.md`
- Evidence gate: not high-confidence final.
- Source invariant audit: passed at 2026-06-01 20:36 UTC, 59 CSV files
  and 8,879,511 rows scanned, 0 violations, 0 warnings.
- Generated report assets are internal evidence artifacts; the user-facing
  deliverable remains a high-level chat summary once the evidence supports it.
- Source catalog artifacts: 586 / 586 attempted in the latest broad public-source run.
- Latest source-catalog extracted rows: 4,878,655.
- Covered filings: 197,243.
- Raw source documents: 66,660.
- Source-backed normalized/extracted entity rows: 7,691,205.
- Expanded SEC CIK candidates: 2,356.
- Projects: 17,226.
- Source-backed deals: 62,950.
- Source-backed contract tranches: 6,839.
- Source-backed compute rows: 166.
- Source-backed timing signals: 3,812.
- Pending source-backed adjudication items: 6,189.
- Ownership graph: 425,765 LEI nodes, 425,679 named nodes, and 643,828 source-backed relationships.
- Contract-structure graph: 95,229 nodes and 190,804 source-backed edges.
- Contract/ownership contagion paths: 8,443 source-backed paths, including
  1,602 ownership-expanded paths, 6,841 contract-only paths, 349 AI-infra
  relevant paths, and 230 high-or-critical paths.
- Materiality-first LLM adjudication packets: 100 top blockers packaged, all
  100 source-backed with local evidence snippets, 76 AI-infra relevant, and
  $25.729T of total exposure-basis across the packet set.
- Automated materiality adjudication decisions: 100 decisions, 89 with resolved
  text quotes, 21 supported as material blockers, 68 requiring deeper extraction,
  11 requiring source retrieval/non-binary parsed evidence, and 3 source-backed
  aggregate obligation snapshot rows approved for metric use. Those 3 rows total
  $176.675B as historical snapshots, but dedupe to $75.6B of current supported
  aggregate metric exposure across 1 latest-snapshot metric group; they are not
  treated as individual contracts.

## Phase Transition Readiness

The system is ready to move from catalog/entity/ownership structuring into the
next evidence-building phase, but acquisition should remain an always-on intake
workstream rather than be treated as complete.

The operating rule for the next phase is materiality-first, not
completeness-first. Broad acquisition should continue in parallel, but report
confidence should come from LLM-adjudicating the top 50-100 material exposures:
largest AI/data-center lease obligations, largest debt facilities and bonds,
largest SPV or non-recourse structures, largest physical power constraints, and
largest compute depreciation, TAM, payback, EPS, and chip-supply claims.

All review/adjudication statuses are cleared by automated LLM adjudication.
Legacy fields named `human_review_status` are adjudication-status fields; there
is no required operator gate in the workflow.

Ready now:

- broad source-backed entity expansion from acquired filings, PPAs, tracker,
  permit, equipment, and GLEIF records
- bounded parallel acquisition with resume, retries, content hashes, retrieval
  timestamps, source URIs, local raw paths, and normalized extracted rows
- optional machine-readable progress events for long EDGAR exhibit-manifest and
  document-acquisition runs
- source-backed ownership graph from GLEIF relationship records plus LEI legal
  names
- adjudication queue, capital exposure graph, weak-link, timing, and compute-economics
  scaffolding
- contract-level EDGAR enrichment for first-pass debt/bond tranches, collateral
  snippets, guarantors, SPV/non-recourse flags, rates, and maturities
- source-backed contract-structure graph outputs for deal, tranche, collateral,
  guarantor, project/asset, non-recourse, and bankruptcy-remote/SPV terms
- source-backed contract/ownership contagion path outputs joining SEC contract
  edges to GLEIF legal-control paths where exact legal-name matches exist
- materiality-ranked LLM adjudication packet outputs for the top 100 blocker
  items, with source snippets and explicit decision fields
- automated materiality adjudication decision outputs that separate
  source-supported blockers from rows still blocked for final metric use
- source-backed aggregate obligation snapshots can now be approved for aggregate
  metric use with latest-snapshot dedupe, while still blocking individual
  contract conclusions until counterparties, recourse, collateral, maturities,
  and payment schedules are extracted

Must move next:

- continued EDGAR/source acquisition as an always-on workstream for future
  filings, lower-priority backlog rows, and new source catalogs
- expanded exhibit-enabled EDGAR manifests for EX-2, EX-4, EX-10, and EX-99
  documents beyond the first high-signal tranche
- continued actual document acquisition and contract-level extraction for
  leases, debt, guarantees, collateral, tranches, PPAs, construction, and
  project-finance terms
- deeper extraction for the materiality adjudication decision gaps: aggregate
  obligation splitting, named counterparty roles, collateral scope, recourse and
  guarantee scope, explicit rate/maturity evidence, and quote-resolved physical
  queue/permit linkage
- deeper contagion modeling that joins contract edges, ownership/SPV edges,
  guarantee/collateral terms, maturities, and physical execution risks beyond
  exact legal-name matches
- triage of the 1,809 pending contract-tranche adjudication items before relying on
  tranche-level downside-bearer or waterfall conclusions
- triage of the 1,441 pending contract-contagion adjudication items before relying on
  full contagion paths
- broadened source-backed GPU depreciation, TAM, payback, EPS, and chip-supply
  evidence beyond the first EDGAR-derived row set

Not ready:

- a high-confidence final bubble call
- lower-priority exhibit coverage outside the score >= 75 manifest
- LLM-adjudicated contract-level extraction at the scale needed for professional-grade
  leverage, SPV, collateral, and downside-risk conclusions
- LLM-adjudicated contract/ownership contagion paths at the scale needed for
  professional-grade contagion conclusions

## Latest EDGAR Exhibit Run

Broad exhibit manifest completed 2026-06-01 19:59 UTC:

- `data/manifests/edgar_exhibit_manifest_20260601-195938.csv`
- parent primary filings inspected: 28,084 with relevance score >= 75
- parent filings with candidate exhibits: 10,401
- exhibit document rows: 16,981
- exhibit mix: 6,841 EX-10 material contracts, 1,156 EX-4 debt/security
  instruments, 8,770 EX-99 supplemental disclosure exhibits, plus smaller EX-2
  and other exhibit rows captured by the manifest
- filing window: 2024-01-02 through 2026-06-01
- errors: 0
- worker pool: 64
- SEC request lane: 8 requests/second and 8-domain concurrency
- source primary manifest: `data/manifests/edgar_filing_manifest_20260601-142009.csv`

Broad exhibit document acquisition completed 2026-06-01 20:28 UTC:

- documents attempted/downloaded: 16,981 / 16,981
- documents resumed in latest enrichment pass: 4,003
- deal candidates extracted in the run: 8,493
- contract tranches materialized in the run: 3,498
- deal mix: 4,168 debt facilities, 1,522 bonds, 710 PPAs, 435 leases,
  144 land acquisitions, 25 guarantees, 23 construction contracts, and 1,466
  other candidates
- bytes downloaded/read: 4,929,859,833
- errors: 0
- worker pool: 64
- SEC request lane: 8 requests/second and 8-domain concurrency
- output directory: `data/edgar_acquisition`

Post-acquisition local extraction refreshed `data/capital/lease_agreements.csv`
to 768 source-backed lease agreements and refreshed compute-economics extraction
against 66,072 EDGAR inventory documents.

Prior focused exhibit run:

- `data/manifests/edgar_exhibit_manifest_20260601-163528.csv`
- parent primary filings inspected: 1,740 with relevance score >= 120
- parent filings with candidate exhibits: 1,196
- exhibit document rows: 2,551
- exhibit mix: 1,353 EX-10 material contracts, 297 EX-4 debt/security
  instruments, 59 EX-2 transaction agreements, and 842 EX-99 supplemental
  disclosure exhibits
- errors: 0

Prior focused acquisition and contract enrichment:

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

The prior focused pass was built through the follow-on command
`scripts/build_edgar_exhibit_manifest.py`, which reads an existing primary
manifest and fetches only SEC archive directory indexes for selected high-signal
parent filings.

## Latest Primary EDGAR Acquisition Run

Completed 2026-06-01 18:35 UTC:

- `data/manifests/edgar_filing_manifest_20260601-142009.csv`
- relevance threshold: score >= 75
- documents attempted/downloaded: 28,084 / 28,084
- documents resumed in latest enrichment pass: 28,084
- deal candidates extracted: 6,882
- contract tranches materialized: 3,341 in the primary-document run; 6,839
  total source-backed tranche rows after the broad exhibit, focused exhibit, and
  primary passes
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

The latest enrichment pass also corrected a material notional extraction edge
case where a malformed SEC paragraph combined a billion-scale aggregate phrase
with explicit series principal amounts. The parser now rejects the inconsistent
aggregate candidate and uses the source-backed series principal sum instead.
The affected Nebius row is now carried as a $3.1625B series-sum candidate, not
as a trillion-scale blocker.

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

- Nodes: 6,635.
- Source-backed edges: 10,084.
- Total edge notional: $7.849T.
- AI-infra-relevant notional: $642.03B.
- AI-infra-relevant edges: 217.
- Contract-structure nodes: 95,229.
- Source-backed contract-structure edges: 190,804.
- Deal contract nodes: 62,950.
- Tranche contract nodes: 6,839.
- Collateral contract nodes: 14,014.
- Guarantee contract edges: 882.
- Collateral contract edges: 31,312.
- Non-recourse deal/tranche contract nodes: 2,035.
- Bankruptcy-remote/SPV deal/tranche contract nodes: 975.
- SPV-flagged deal/tranche contract nodes: 23,092.
- Tranche nodes with maturity: 4,054.
- Tranche nodes with interest rate: 3,327.
- Outputs: `data/graph/capital_exposure_nodes.csv`,
  `data/graph/capital_exposure_edges.csv`,
  `data/graph/capital_contract_nodes.csv`,
  `data/graph/capital_contract_edges.csv`, and
  `data/graph/capital_exposure_graph_summary.json`.

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
- Candidate stress window: 2025-Q3 to 2027-Q3.
- Capital refinancing 2024-2030: $13.780T.
- AI-infra capital refinancing 2024-2030: $292.29B.
- Physical capacity 2024-2030: 177,293 MW.
- Compute amount 2024-2030: $219.41B.
- Source-backed timing signals: 3,812.
- Critical/high timing signals: 163.
- AI-infra-relevant timing signals: 313.

Adjudication queue:

- Critical items: 87.
- High items: 930.
- AI-infra-relevant items: 732.
- Contract-tranche adjudication items: 1,809.
- Pending capital distinct notional: $19.774T.
- Pending AI-infra-relevant distinct capital notional: $819.02B.
- Pending contract-tranche notional: $17.078T.
- Pending contract-contagion path exposure: $97.428T.
- Pending compute claim amount: $398.24B.
- Materiality decisions: 21 source-supported blockers, 68 requiring deeper
  extraction, 11 requiring source retrieval/non-binary parsed evidence, and 3
  approved aggregate obligation snapshots.
- Automated aggregate snapshot rows approved for metric use: $176.675B across 3
  source-backed lease-obligation snapshots.
- Deduped automated final metric support: $75.6B across 1 latest-snapshot metric
  group.
- Stricter quote-level contagion gating now blocks 30 contagion/legal-path rows until the
  evidence quote itself supports the legal-entity path and risk-transfer
  mechanism.

Weak links:

- Candidates: 528.
- High or critical candidates: 25.
- Capital candidates: 217.
- Physical candidates: 250.
- Combined capital/physical candidates: 42.
- Debt-service candidates: 19.
- AI-infra-relevant weak-link notional: $642.03B.

Compute economics:

- GPU price observations: 45.
- Depreciation policies: 49.
- TAM claims: 10.
- Capex payback cases: 2.
- EPS depreciation impacts: 2.
- Chip supply observations: 9.

## Next Acquisition Priorities

1. Extract deeper contract terms from the newly acquired score >= 75 exhibit set:
   lease economics, debt waterfalls, guarantee scope, collateral packages, PPA
   contract terms, construction obligations, and project-finance covenants.
2. Rebuild the adjudication queue and materiality packet set after each material
   acquisition or extraction run; clear or corroborate critical/high items and
   the contract-tranche queue before upgrading any conclusion to high confidence.
3. Run the score >= 50 primary-document or exhibit tail only if the score >= 75
   adjudication queue indicates incremental value after exhibit extraction.
4. Add more source catalogs for state PUCs, local zoning/air permits, data-center
   leases, equipment financing, and project-level utility filings.
5. Improve named counterparty extraction on large unmatched EDGAR rows, especially
   aggregate lease obligations and prospectus supplements.
6. Increase compute-economics evidence by adding dated resale/rental-rate sources,
   hyperscaler depreciation/EPS bridges, and source-backed TAM comparators.
7. Keep every production metric evidence-gated until the adjudication queue is
   cleared or corroborated enough to support high-confidence claims.
