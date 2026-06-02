# Acquisition Status

Last updated: 2026-06-02 09:04 UTC.

This file is the operational snapshot for the current evidence corpus. Treat it
as a run log, not as a final investment conclusion.

## Current Corpus

- Latest evidence-gated report: `data/reports/BURRY_REPORT_EvidenceGated_20260602-0904.md`
- Evidence gate: not high-confidence final.
- Evidence audit coverage: report-level audits now include analyzer-level
  capital, compute, and debt-service audits plus explicit row/artifact-backed
  audits for high-impact Burry-answer rollups. Substantive high-impact metric
  audit warnings are cleared; the remaining consistency warnings are doc-pattern
  checks, not evidence gaps or a gate opening.
- Source invariant audit: passed at 2026-06-02 04:02 UTC, 63 CSV files
  and 9,208,844 rows scanned, 0 violations, 0 warnings.
- Generated report assets are internal evidence artifacts; the user-facing
  deliverable remains a high-level chat summary once the evidence supports it.
- Source catalog artifacts: 586 / 586 attempted in the latest broad public-source run.
- Latest source-catalog extracted rows: 4,878,655.
- Covered filings: 197,243.
- Raw source documents: 66,660.
- Source-backed normalized entities: 789,787 distinct entities from 1,397,581
  source-backed mentions.
- Expanded SEC CIK candidates: 2,356.
- Projects: 17,227.
- Source-backed deals: 62,952.
- Source-backed contract tranches: 10,051.
- Source-backed compute rows: 149.
- Source-backed timing signals: 3,263.
- Pending source-backed adjudication items: 6,773.
- Ownership graph: 425,765 LEI nodes, 425,679 named nodes, and 643,828 source-backed relationships.
- Contract-structure graph: 93,822 nodes and 189,129 source-backed edges.
- Contract/ownership contagion paths: 8,749 source-backed paths, including
  1,976 ownership-expanded paths, 6,773 contract-only paths, 453 AI-infra
  relevant paths, and 145 high-or-critical paths.
- Materiality-first LLM adjudication packets: 6,663 blocker groups packaged
  (full deduped queue), all 6,663 source-backed, 6,663 with local evidence
  snippets, 706 AI-infra relevant, and $56.029T of total exposure-basis across
  the packet set.
- Automated materiality adjudication decisions: 6,663 decisions, 6,463 with
  resolved text quotes plus 200 row-context-backed decisions for non-text
  sources, 4,470 supported as material blockers, 2,193 requiring deeper
  extraction, 0 requiring source retrieval, and 2,924 source-backed rows
  approved for metric use. Those approved rows total $8.301T as row-level
  supported amounts, but source-instrument and economic-obligation metric
  dedupe now collapses same-document/same-amount and exact repeated filing
  disclosures to $4.365T deduped final metric support across 1,579 metric groups;
  they are not treated as individual contracts unless contract terms are
  separately extracted.
- Report arithmetic invariants pass with 0 violations. The how-large answer now
  labels the $1.201T curated capital-structure deal-graph debt-like metric
  separately from the broader $4.365T materiality-adjudicated supported exposure
  metric so the two scopes are not read as inconsistent or directly additive.
- The broader materiality metric is now split by adjudicated thesis linkage:
  $0.360T has established direct/watchlist AI-data-center linkage ($0.074T
  direct and $0.286T watchlist), while $4.005T, or 91.8%, is source-backed
  but not yet established as AI/data-center-linked. The unlinked tail is a
  scope gap, not a final no-link conclusion.
- Semantic metric-validity gating now scans approved materiality rows as a
  separate source-text dimension: 2,773 approved rows classify as committed
  debt/obligation text, 157 remain indeterminate review candidates, and 0
  approved rows are hard-flagged as asset/capacity, equity/production, or
  boilerplate snippets.
- Decision coverage over packaged blocker groups: 100.0%; unresolved decision
  share remains 32.91% (still extraction-bound, not source-retrieval-bound).
- Top remaining decision gaps are now named counterparty role extraction
  (1,212), collateral scope (645), recourse/guarantee scope (517), split
  aggregate disclosure from committed obligations (165),
  asset/UPB/financing-capacity splitting (150), source-quote committed-obligation
  semantic confirmation (72), specific committed-obligation equity/share or
  mortgage-production splitting (58), queue/permit/interconnection linkage (43),
  mega-obligation confirmation (33), missing underlying term-level clauses
  (28), shelf-capacity-vs-committed-financing distinction (25), mixed-currency
  quote reselection or USD-equivalent extraction (10), and non-USD notional
  conversion before metric use (6).

## Phase Transition Readiness

The system is ready to move from catalog/entity/ownership structuring into the
next evidence-building phase, but acquisition should remain an always-on intake
workstream rather than be treated as complete.

The operating rule for the next phase is materiality-first, not
completeness-first. Broad acquisition should continue in parallel, but report
confidence should come from LLM-adjudicating the top material exposures:
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
- multi-tranche EDGAR enrichment where explicit source text names separate term
  loan, revolver, or note-series amounts inside a single debt/security document
- guarantee-scope EDGAR enrichment where source clauses identify guarantors or
  guarantee coverage prose outside simple `as Guarantor` role syntax
- source-backed contract-structure graph outputs for deal, tranche, collateral,
  guarantor, project/asset, non-recourse, and bankruptcy-remote/SPV terms
- source-backed contract/ownership contagion path outputs joining SEC contract
  edges to GLEIF legal-control paths where exact legal-name matches exist
- materiality-ranked LLM adjudication packet outputs for all deduped blocker
  groups (default full queue run), with bounded parallel workers, source
  snippets, and explicit decision fields
- automated materiality adjudication decision outputs that separate
  source-supported blockers from rows still blocked for final metric use
- bounded-parallel packet and decision builders (`--max-workers`) so full-queue
  adjudication remains practical at current corpus scale
- source-backed aggregate obligation snapshots can now be approved for aggregate
  metric use with latest-snapshot dedupe, while still blocking individual
  contract conclusions until counterparties, recourse, collateral, maturities,
  and payment schedules are extracted
- non-snapshot approved metric rows now collapse by source instrument and
  supported amount before final metric support is reported, preventing
  same-document/same-amount affiliate or repeated-extraction rows from inflating
  final supported notional
- capital exposure graph edge notionals now also dedupe repeated source
  instruments inside each entity-pair/deal-type edge, retaining source fanout
  evidence while preventing weak-link ranking and graph summaries from summing
  the same instrument across repeated filings/extractions
- compute depreciation extraction now binds useful-life values to the matching
  asset-class phrase, so building/land lives and percent-depreciation tables no
  longer produce false server/GPU useful-life red flags
- role-clause counterparty inference now auto-populates agent/trustee,
  commitment-party, lead-arranger/bookrunner, placement-agent, and initial
  purchaser representative counterparties from source quotes when `counterparty`
  fields are blank; quote selection now gives explicit named financing-role
  clauses enough weight to beat generic facility prose
- defined-party counterparty inference now recognizes named borrower labels
  like `("Borrower")` and `("Initial Borrower")`, plus `together, the
  "Commitment Parties"` commitment-letter clauses, while generic role-only
  phrases such as `certain Bridge Lenders` remain blocked for named-party
  extraction
- financing-role inference now also handles dotted `N.A.` bank-as-agent clauses,
  underwriter representative clauses, named joint book-running manager lists,
  and `Trustee U.S. Bank...` style trustee labels without broadening into
  generic `credit facility with...` prose
- scope-aware quote selection now prefers local source clauses containing
  explicit unsecured, non-recourse, guarantor, collateral, secured, or
  asset-backed terms over generic facility prose; this resolves collateral and
  recourse gaps only when the source snippet itself carries the scope evidence
- collateral-scope quote selection now recognizes source clauses naming security
  documents, collateral documents, loan-and-security agreements,
  asset-based/borrowing-base facilities, and centers long snippets around those
  terms so late-file scope evidence is not truncated away
- packet evidence selection now performs a second, strict pass for executable
  financing-scope clauses (`shall be secured`, `secured by`, `senior
  unsecured`, `non-recourse`, `guaranteed by`, and similar terms) so late-file
  collateral/recourse evidence can beat amount preambles, while definitions-only
  `Lien means...` or `Permitted Liens...` sections are not promoted as
  collateral proof by themselves
- non-specific capital candidate rows now route to an explicit
  `acquire underlying agreement or debt schedule clause for term-level extraction`
  gap when quote text lacks term-level contract evidence, reducing false
  precision on collateral/recourse/counterparty fields
- packet evidence snippets now use cross-artifact scoring and term-focused
  prioritization so clause-level contract text is preferred over low-signal
  boilerplate snippets when adjudicating materiality blockers
- packet evidence snippet extraction now skips binary/non-text artifacts (for
  example `.bin`, compressed archives, and byte-heavy files) so adjudication
  prompts carry source text rather than unreadable bytes
- packet evidence fallback now synthesizes bounded row-context snippets for
  physical/compute queue/permit/market observations when source artifacts are
  non-text, clearing the prior `needs_source_retrieval` bucket without inflating
  quote-backed confidence
- aggregate/shelf-capacity rows now block first on aggregate-to-committed split
  without stacking term-level counterparty/collateral/recourse gaps until a
  specific contract-level source row is extracted
- committed lease/service-contract value disclosures now clear the
  aggregate-split gap only when source text says the company entered into,
  executed, signed, or commenced a lease/service agreement and the selected
  quote ties the measured amount to aggregate contractual value; portfolio UPB,
  shelf capacity, total liabilities, debt-outstanding snapshots, and undrawn
  borrowing capacity remain blocked
- note-offering bond rows can now clear counterparty and collateral gaps when
  source quote context is prospectus/indenture note issuance without bilateral
  lender-agent language, reducing false bilateral assumptions
- debt-facility rows that are clearly primary note/indenture offerings in source
  text, including note offerings that mention related credit facilities in use
  of proceeds or guarantee context, now reuse the same non-bilateral handling
  and can clear synthetic counterparty gaps; plain `unsecured` clause language
  now also resolves collateral-scope gaps where secured-language evidence is
  absent
- lender-role recourse detection now accepts bank/trust/financial-institution
  counterparty names (not only explicit `lender`/`agent` labels) when rows are
  already source-backed transaction facilities/principal commitments
- weak-link support-term matching now includes physical execution language
  (`capacity`, `MW`, `construction`, `planned`, `queue`, `permit`,
  `interconnection`) so source-backed physical weak-link blockers are no longer
  falsely left in unresolved/no-gap status
- physical record matching now avoids counting a project/facility name match as
  both name overlap and owner overlap when owner/operator fields are absent,
  removing inflated permit/equipment project matches while preserving distinct
  owner-token matches
- physical project and observation ingestion now share one construction-status
  taxonomy, so delayed/suspended/on-hold projects are carried as `delayed`
  instead of being folded into `announced`; the refreshed physical summaries
  now surface 50 delayed projects and 8,680 MW of delayed tracker capacity as
  explicit deliverability evidence
- physical project tracker rollups now use a calibrated distinct-site key
  based on normalized project name plus city/state, with address/operator only
  as fallback keys for sparse rows; raw tracker capacity remains 552,455 MW,
  while duplicate-adjusted distinct tracker capacity is now 543,335 MW after
  collapsing 42 duplicate rows across 36 groups, without merging same-name
  multi-city operator portfolios
- capital boilerplate gating is now carried as an explicit extraction gap
  (`confirm final prospectus or underlying agreement terms`) instead of an
  implicit decision override, and plain `Registration Statement` references in
  otherwise term-specific 424B/FWP offerings are no longer treated as boilerplate
  by themselves
- issuer-level debt-outstanding snapshots now route to aggregate-to-committed
  split blocking even when upstream context labeled the amount as
  transaction-principal, reducing false contract-level counterparty requirements
- generic prospectus/equity-offering boilerplate rows now route to split or
  term-level evidence acquisition gaps instead of stacking synthetic-looking
  counterparty/recourse/collateral requirements
- ownership-expanded contagion rows with SEC contract evidence plus source-backed
  LEI ownership-path artifacts now clear legal-entity validation gaps when the
  ownership/control chain is explicitly encoded in adjudication context
- notional extraction now rejects portfolio rollup and rate-based estimate prose
  (for example, cumulative “debt and equity investments” rollups and “contract
  value based on prevailing market rates”), and treats “maximum aggregate amount
  of those offerings” language as shelf-capacity context
- aggregate lease-obligation rows now block metric use when the selected source
  quote is debt-securities prospectus or indenture boilerplate without direct
  lease-payment evidence
- named financing-role inference now handles borrower-then-agent clauses,
  combined administrative/collateral agent roles, and underwriter representative
  lists without preserving lead-in prose as the counterparty name

Must move next:

- continued EDGAR/source acquisition as an always-on workstream for future
  filings, lower-priority backlog rows, and new source catalogs
- lower-score exhibit tails, new filings, and newly discovered CIKs when
  materiality gaps justify more SEC acquisition
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
- triage of the 2,498 pending contract-tranche adjudication items before relying on
  tranche-level downside-bearer or waterfall conclusions
- triage of the 1,276 pending contract-contagion adjudication items before relying on
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

Broad exhibit document acquisition/reparse refreshed 2026-06-01 23:40 UTC:

- documents attempted/downloaded: 16,981 / 16,981
- documents resumed in latest enrichment pass: 16,981
- deal candidates extracted in the run: 8,493
- contract tranches materialized in the run: 4,826
- deal mix: 4,170 debt facilities, 1,522 bonds, 710 PPAs, 433 leases,
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

The latest reparse keeps explicit multi-tranche extraction for debt/security
documents. When a single exhibit names separate term loan, revolver, or note
series amounts, `data/edgar_acquisition/tranches.csv` now carries separate
source-backed tranche rows instead of only one primary fallback tranche. The
fallback still applies when the source text does not clearly separate tranches.

The same reparse keeps guarantee-scope extraction from agreement prose enabled
for both deal-level and tranche-level rows, with source-backed
`guarantee_description` context preserved in `tranches.csv`.

The same reparse now rejects clearly non-contract notional prose upstream (such
as cumulative portfolio investment rollups and rate-based contract-value
estimates) and routes filing-fee “maximum aggregate offering” language into
shelf-capacity context so those rows do not masquerade as committed deal terms.

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
- contract tranches materialized: 3,341 in the primary-document run; 10,040
  total source-backed tranche rows after the broad exhibit multi-tranche reparse,
  focused exhibit, and primary passes
- bytes downloaded/read: 29,417,355,227
- errors: 0
- worker pool: 64
- SEC request lane: 8 requests/second and 8-domain concurrency
- output directory: `data/edgar_acquisition`
- latest inventory: `data/edgar_acquisition/edgar_document_inventory.csv`
- latest deal candidates: `data/edgar_acquisition/deals.csv`
- latest summary: `data/edgar_acquisition/edgar_document_acquisition.summary.json`

This run acquired primary documents only because the broad manifest did not
include exhibit indexes. The broad score >= 75 exhibit manifest has since been
built and acquired; further EDGAR expansion should now be driven by materiality
gaps, lower-score exhibit tails, new filings, or newly discovered CIKs.

The latest enrichment pass also corrected a material notional extraction edge
case where a malformed SEC paragraph combined a billion-scale aggregate phrase
with explicit series principal amounts. The parser now rejects the inconsistent
aggregate candidate and uses the source-backed series principal sum instead.
The affected Nebius row is now carried as a $3.1625B series-sum candidate, not
as a trillion-scale blocker.

The same tranche logic now also promotes a source-backed sum of explicit
component tranches to the deal notional when the prior amount picker latched
onto only one component of a multi-tranche facility.

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

- Nodes: 5,036.
- Source-backed edges: 7,526.
- Total edge notional: $864.18B.
- AI-infra-relevant notional: $5.16B.
- AI-infra-relevant edges: 156.
- Generic/artifact counterparty mentions skipped: 11,644.
- Contract-structure nodes: 93,822.
- Source-backed contract-structure edges: 189,129.
- Deal contract nodes: 62,952.
- Tranche contract nodes: 10,051.
- Collateral contract nodes: 10,065.
- Guarantee contract edges: 1,757.
- Collateral contract edges: 26,842.
- Non-recourse deal/tranche contract nodes: 2,586.
- Bankruptcy-remote/SPV deal/tranche contract nodes: 1,277.
- SPV-flagged deal/tranche contract nodes: 26,306.
- Tranche nodes with maturity: 6,037.
- Tranche nodes with interest rate: 5,081.
- Outputs: `data/graph/capital_exposure_nodes.csv`,
  `data/graph/capital_exposure_edges.csv`,
  `data/graph/capital_contract_nodes.csv`,
  `data/graph/capital_contract_edges.csv`, and
  `data/graph/capital_exposure_graph_summary.json`.

Collateral scope quality hardening (2026-06-01 refresh):

- Collateral extraction now rejects non-actionable risk-factor/prospectus
  boilerplate and only carries actionable collateral descriptions into contract
  graph edges and risk flags.
- This removed a large set of false collateral edges without reducing
  source-backed provenance coverage.

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
- Capital refinancing 2024-2030: $3.2533T.
- AI-infra capital refinancing 2024-2030: $227.22B, of which $127.91B
  matured before the 2026-Q2 report as-of quarter and $99.31B remains forward
  from 2026-Q2.
- Forward AI-infra refinancing peak: 2027-Q3, with $22.25B of source-backed
  AI-infra refinancing maturities in that quarter.
- Whole-corpus forward capital refinancing from 2026-Q2: $1.4411T.
- Physical capacity 2024-2030: 177,293 MW.
- Compute amount 2024-2030: $124.21B.
- Source-backed timing signals: 3,263.
- Critical/high timing signals: 143.
- AI-infra-relevant timing signals: 277.

Adjudication queue:

- Critical items: 86.
- High items: 761.
- AI-infra-relevant items: 706.
- Contract-tranche adjudication items: 2,498.
- Pending capital distinct notional: $11.923T.
- Pending AI-infra-relevant distinct capital notional: $827.72B.
- Pending contract-tranche notional: $10.672T.
- Pending contract-contagion path exposure: $30.028T.
- Pending compute claim amount: $398.24B.
- Materiality packets: 6,663 source-backed packets, 706 AI-infra relevant, and
  6,663 with local evidence snippets.
- Materiality decisions: 4,470 source-supported blockers, 2,193 requiring
  deeper extraction, 0 requiring source retrieval, and 2,924 rows approved
  for metric use (6,463 quote-backed decisions plus 200 row-context-backed
  decisions on non-text sources).
- Automated row-level supported amount approved for metric use: $8.301T.
- Deduped automated final metric support: $4.365T across 1,579 metric groups
  after source-instrument, latest-snapshot, and exact economic-obligation
  grouping.
- Relevance split of that deduped final metric: $0.360T established
  direct/watchlist AI-data-center linkage, including $0.074T direct and
  $0.286T watchlist; $4.005T remains not-established for thesis linkage.
- Six HKD-denominated rows whose source text carries `HK$` face values now
  block on `convert non-USD notional to USD before metric use`; they are not
  carried as USD-supported metric amounts until the currency token and
  conversion basis are extracted.
- Ten selected quotes with non-USD/mixed-currency tokens now block on
  `extract USD-equivalent or reselect source quote for non-USD/mixed-currency
  obligation` unless the selected quote itself contains an explicit USD amount
  matching the recorded metric. USD-confirmed mixed-currency offerings remain
  eligible.
- Semantic hard flags remaining in approved metric rows: 0
  asset/capacity, equity/production, or boilerplate rows; 157 indeterminate
  rows remain queued for review rather than treated as high-confidence debt
  semantics.
- Top unresolved gaps are named counterparty roles, collateral scope,
  recourse/guarantee scope, aggregate-to-committed splitting, and underlying
  term-level clause acquisition.

Contract/ownership contagion:

- Source-backed paths: 8,749.
- Ownership-expanded paths: 1,976.
- Contract-only paths: 6,773.
- AI-infra-relevant paths: 453.
- Guarantee paths: 448.
- Collateral paths: 6,355.
- Non-recourse paths: 2,290.
- SPV paths: 8,489.
- High/critical paths: 145.
- Total path notional: $44.591T.
- AI-infra-relevant path notional: $1.919T.
- Default path cap raised to 50,000 so this layer is not clipped at the prior
  10,000-path script default.

Weak links:

- Candidates: 540.
- High or critical candidates: 20.
- Capital candidates: 232.
- Physical candidates: 250.
- Combined capital/physical candidates: 39.
- Debt-service candidates: 19.
- AI-infra-relevant weak-link notional: $333.00B.

Compute economics:

- Compute assets: 49.
- GPU price observations: 45.
- Depreciation policies: 32.
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
