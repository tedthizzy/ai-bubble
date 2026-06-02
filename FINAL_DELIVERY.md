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

- Markdown: `data/reports/BURRY_REPORT_EvidenceGated_20260602-2012.md`
- JSON: `data/reports/BURRY_REPORT_EvidenceGated_20260602-2012.json`
- `high_confidence_final`: `false`
- Evidence audit coverage now includes 473 claim audits: analyzer-level capital,
  compute, and debt-service audits, explicit row/artifact-backed audits for
  high-impact Burry-answer rollups, and aggregate hooks for pending review
  capital, pending AI-infra capital, pending compute, weak-link AI-infra,
  debt-service maturity-wall, capital-graph total/AI-infra notional, compute
  GPU-capex rollups, MW-based AI/data-center PPA offtaker concentration,
  legal-family PPA concentration, and AI/data-center-gated capital-graph
  risk-bearer/obligor rankings. The who-bears-downside answer also reports a
  downside-bearer taxonomy quality summary, and date/clause fragments are
  treated as unmapped rather than named risk bearers. Physical execution audits
  now cover the term-level rollup fields added in this checkpoint. Large
  numeric `key_metrics` values above $200B now have value-matched claim audits
  with gross, path-summed, out-of-scope, pre-dedupe, or distinct basis labels
  where applicable. Compute-economics coverage now separates missing-comparator
  blockage from true clean reads: 18 GPU generations lack comparable
  depreciation signals, 10 TAM claims lack realized-revenue comparators, 2 EPS
  impacts lack modeled economic depreciation, 9 chip-supply observations lack
  delivered-count comparators, and the payback layer has 2 cases where 1 is
  blocked by missing cash-flow inputs and 2 lack debt-service coverage. The
  report consistency checker now also gates current report ID, final metric,
  metric groups, AI-attribution split, audit count, and compute blocked counts;
  it currently reports 0 errors and 0 warnings.
- Source invariant audit: passed across 63 CSV files and 9,208,844 rows scanned
  with 0 violations and 0 warnings.
- Acquired source artifacts: 66,660 / 66,660 attempted.
- Covered filings: 197,243.
- Source-backed normalized entities: 789,787.
- Projects: 17,227.
- Source-backed deals: 62,952.
- Source-backed physical execution terms: 821 distinct extracted terms across
  662 projects.
- Compute economics rows: 272 total, including 180 source-backed rows after
  provenance dedupe.
- Source-backed timing signals: 3,263.
- Pending source-backed adjudication items: 6,773.
- Automated materiality adjudication decisions: 6,663 decisions, with 4,252
  supported blockers, 2,411 still requiring deeper extraction, 2,707 approved
  metric rows, and $3.742T deduped final metric support across 1,380
  source-instrument/same-accession/strict-cross-filing/economic-obligation
  metric groups. Semantic hard flags are now zero in approved metric rows;
  malformed comma-grouped SEC source amount tokens and residual
  availability/capacity/rollup amount mis-bindings, plus selected source quotes
  that only support mixed shelves, equity, no-leverage funds, acquisition
  purchase prices, deposits, loan portfolios, earnings releases, or marketing
  decks, now block metric use pending source-quote reselection or corrected
  extraction.

Latest capital and timing outputs:

- Capital exposure graph source-backed edges: 7,526.
- Capital exposure graph total edge notional: $864.18B.
- AI-infra-relevant graph notional: $4.75B across 139 stricter AI/data-center
  tagged edges after removing unrelated XAI Octagon fund and truncated `Ai`
  false positives.
- In-scope debt-like notional: $1.201T.
- Debt-service timing coverage remains materially incomplete: the crack-window
  maturity wall is now labeled as a floor because 165 of 439 distinct
  debt-service obligations and $541.811B of distinct debt-like notional still
  lack maturity-date evidence; distinct measured-rate notional coverage is
  44.2%. A follow-up fixture pack now identifies sibling-fill candidates where
  known coupons can be propagated to duplicate instrument rows, narrowing the
  true residual extraction queue to specific instruments rather than implying a
  broad mass-extraction pass.
- Contract-contagion notional is now explicitly labeled as path-summed and
  multiplicity-inflated: $44.591T across 8,749 paths, with $1.919T across
  453 AI-infra-relevant paths, is a diagnostic path surface rather than
  headline AI/data-center exposure.
- Forward-monitoring and hidden-leverage research packs have been imported as
  handoff artifacts: a bubble leading-indicator catalog for future crack-window
  monitoring, and a hidden-leverage taxonomy that keeps the committed-debt
  metric distinct from excluded economic commitments such as take-or-pay,
  hosting, colocation, and supplier-financing obligations.
- A sourced economic-commitment handoff now gives the first candidate numbers
  for that excluded tier, separating binding buyer-side commitments/leases from
  seller-side backlog mirrors and non-binding lessor-revenue or framework
  claims. A deterministic `bubble.ingestion.compute.extract_economic_commitments`
  helper now classifies this source text into the corresponding economic-
  commitment tiers, and the EDGAR compute extraction pass now writes those rows
  to `economic_commitments.csv` with provenance and double-count caveats. This
  tier remains separate from the committed-debt metric.
- Utility/ratepayer downside is now ready for its first source-acquisition pass:
  `handoffs/codex_utility_ratepayer_acquisition_cards_20260602.md` and its
  fixture CSVs identify exact PUC/IRP/rate-case/large-load tariff targets for
  Georgia Power, Entergy Louisiana, FPL/NextEra, Xcel Colorado, Xcel Minnesota,
  and NextEra/Google data-center energy development. These are acquisition
  targets only; they do not yet quantify ratepayer exposure. A deterministic
  `bubble.ingestion.regulatory.extract_ratepayer_terms` helper now extracts the
  first comparable term evidence from acquired PUC/IRP text.
- Physical execution research now has a first source-target pack for
  behind-the-meter and utility-backed AI/data-center projects:
  `handoffs/claude_physical_execution_cards_20260602.md` and
  `handoffs/claude_onsite_gas_stranded_risk_20260602.md`. These are acquisition
  and architecture inputs for permit/PUC/power-contract diligence, not metric
  changes.
- Compute payback research now has a compact input bridge at
  `handoffs/claude_compute_payback_inputs_20260602.md`, identifying the
  per-name revenue, capex, clean-debt, and useful-life inputs needed before the
  engine can produce decision-useful payback or DSCR conclusions. The generated
  report now exposes blocked comparator counts across GPU depreciation, TAM,
  payback, EPS, and chip supply so the compute layer cannot mistake missing
  inputs for no stress.
- A deterministic physical-execution extractor now exists at
  `bubble.ingestion.physical.extract_physical_execution_terms`, turning acquired
  permit/PUC/source text into normalized evidence rows for on-site generation,
  air permits, behind-the-meter/off-grid status, queue-bypass language,
  litigation/enforcement risk, utility approvals, and ratepayer stranded-asset
  transfer terms.
- `scripts/extract_physical_execution_terms.py` materializes those rows to
  `data/physical/physical_execution_terms.csv`; the latest run wrote 821 terms
  from tracker, queue, and permit source rows.
- `scripts/summarize_physical_execution_terms.py` writes
  `data/reports/physical_execution_summary.json`; the latest report now carries
  a term-level physical execution rollup with 16,778.4 MW of on-site generation
  evidence, 443 behind-the-meter/off-grid flags, 30 permit litigation or
  enforcement-risk flags, 5 queue-bypass/no-queue flags, and 1 ratepayer
  stranded-asset transfer flag. These are source-term sums, not project-deduped
  capacity forecasts.
- Broader materiality-adjudicated supported exposure: $3.742T across 1,380
  metric groups; this is a different scope from the curated capital-structure
  deal-graph debt-like metric above, not an additive increment.
- Established direct/watchlist AI-data-center-linked support inside that broader
  materiality metric is $0.406T on the same 1,380-group final metric
  denominator; 89.2% remains source-backed but not yet thesis-linked.
- Clear AI/HPC/bitcoin data-center operators are normalized to direct linkage
  when source tags are blank, watchlist, or not established; Galaxy Digital is
  normalized only for packet text naming Galaxy Helios, CoreWeave, or
  data-center context. Indirect utility/telecom suppliers remain
  not-established until a fractional scope rule is sourced.
- Same-filing quote reselection now replaces semantically peripheral or
  exact-amount-weak approved snippets with stronger same-entity/same-content-hash
  committed-debt clauses where available. Reselection preserves stable metric
  dedupe quotes, so it improves evidence text without changing metric totals.
- Unconverted HKD face-value rows are blocked from metric use pending
  source-backed USD conversion; six rows now carry that extraction gap.
- Mixed-currency selected quotes without an explicit USD amount matching the
  recorded metric are blocked pending USD-equivalent extraction or source-quote
  reselection; USD-confirmed mixed-currency rows remain eligible.
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
