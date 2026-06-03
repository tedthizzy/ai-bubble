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

- Markdown: `data/reports/BURRY_REPORT_EvidenceGated_20260603-0551.md`
- JSON: `data/reports/BURRY_REPORT_EvidenceGated_20260603-0551.json`
- `high_confidence_final`: `false` (ecosystem-wide, BY DESIGN — see verdict below).
- Current `master` checkpoint: `e72d74e` (single-agent; the prior two-agent
  Claude/Codex handoff queue was consolidated into `master` at `7638aa9` and the
  role docs retired). Recent landed work: economic-event collapse, separation-test
  mismatch ratios, source-backed cluster DSCR, physical-deliverability honesty, and
  the tiered verdict + adversarial-audit corrections.
- **Tiered verdict (report `ai_direct_core_verdict`):** AI-direct core
  `bubble_dynamics_present` @ **0.67** confidence (fragility_facts 0.85 discounted by
  a credible bear case 0.62) for the financed AI-direct cluster; ecosystem-wide
  `not_established_as_ecosystem_wide_bubble` (no defensible total-AI-leverage
  denominator — the broad metric is mostly non-AI debt). The verdict now rests on
  TWO source-backed legs: cluster EBITDA/interest coverage (`1.35x`, 7/11 issuers
  loss-making, CoreWeave DSCR incl. principal ~0.30x) AND the GPU book-vs-economic-life
  gap (deployed-fleet rental yields −60-75% in ~2yr + Amazon's SEC 6→5yr server-life
  revision). Only the realistic-utilization DSCR leg remains illustrative. A
  forward cash-flow stress (Base/Adverse/Severe/Tail) now sits on the same
  source-backed financials: the cluster runs 1.35x at base but flips NEGATIVE by the
  adverse case (25% utilization miss + 200bp rate shock), with a majority of issuers
  breaching — a moderate, non-tail shock is enough to push the financed core into distress.
- Ultimate end-holder leg (who really eats it): SEC ownership filings (13F-HR, SC
  13G/13D, S-1/10-K beneficial ownership) across 12 cluster issuers + private-credit
  lenders yield 96 disclosed holders, **80 filing-verified** (exact DEF 14A / SC 13G
  share matches). Routing: household-routed (insurer/pension/passive index) ~15.6% by
  count / ~25.2% by disclosed value; read `mixed_holding` — disclosed equity is
  dominated by founders (super-voting) + intermediaries + risk-capital, with index
  funds the main household channel. Coverage is PARTIAL by construction: private-
  placement DDTL/SPV debt holders (likely insurance/annuity-funded private credit)
  are not 13-F-visible, so this is the disclosed-holder distribution, not a full cap table.
- Capital-exposure graph integration: the financed AI-direct cluster is now injected
  into the production graph as source-backed deals (issuer debt -> lead arranger, plus
  GPU-supplier / strategic-investor / anchor-customer topology edges) from the verified
  census + contagion fixtures. This lifts the graph's AI-infra-relevant notional from
  ~$5B (Equinix only) to **~$56.5B** and places the cluster's shared lenders (Goldman,
  Morgan Stanley) and NVIDIA/Microsoft as cross-cluster contagion hubs in the SAME
  5,102-node / 7,617-edge graph as the rest of the ecosystem. Per-lender syndicate
  allocations are undisclosed, so each issuer's debt is attributed once to its lead
  arranger (no double-count); names are canonicalized so variants don't fragment hubs.
- Supply-side equipment-bottleneck layer (the goal's "equipment bottlenecks" physical-
  constraint capability): 8 AI data-center supply chokepoints mapped from supplier
  filings (TSMC CoWoS advanced packaging, HBM, NVIDIA GPU allocation, gas turbines,
  large power transformers/switchgear, backup gensets, liquid cooling, skilled electrical
  labor). All 8 gate the buildout; 6 are single-source/duopoly; lead times up to ~42
  months (median ~24); 12 of 30 kept suppliers filing-verified (TSMC Q1-FY2026 / Q4-FY2025
  earnings calls, SK Hynix IR, etc.). Burry read: TSMC CoWoS is the near-single-source gate
  whose shock propagates to every downstream issuer at once (supply-side analogue of the
  NVIDIA hub); unsourceable lead times left null, analyst-only figures flagged.
- Debt-side end-holder routing (the goal's "insurance and pension exposure" leg,
  resolving the equity-only gap the end_holders layer flagged): traced how the 8 cluster
  private-credit lenders are FUNDED, from their own 10-Ks/earnings. All 8 draw material
  insurance/annuity + pension capital (Apollo/Athene 51.1% via $331.5B Athene + $52.4B
  Athora, Blackstone 53%, KKR/Global Atlantic 44%, Carlyle 41%, Brookfield 37%, Blue Owl
  20%, Ares 14%); median ~41% insurance-funded, 18 of 47 kept sources filing-verified.
  Burry read: the cluster's private-placement DEBT loss routes to policyholders and
  retirees (households) — the quiet 2008-style channel, invisible in 13-F equity data.
  Coverage is partial and explicit: aggregate lender funding mix, NOT a per-DDTL-facility
  attribution (undisclosed); analyst/residual figures flagged, nulls not fabricated.
- Forensic red-flag scorecard (the goal's "Advanced red flag detection" capability):
  per-issuer Burry checklist run on all 8 financed-cluster issuers from their SEC filings
  (adversarially verified). Striking systemic result: ALL 8 carry a filing-tied SERIOUS
  accounting flag; 38 of 42 present flags filing-verified. material_weakness_icfr is present
  in 8/8 (e.g. CoreWeave's three control weaknesses verbatim-confirmed "continued to exist
  as of December 31, 2025"); customer concentration >35% 8/8; related-party/circular 7/8;
  auditor change 5/8; insider net selling 5/8. Highest red-flag scores: Core Scientific,
  Hut 8, IREN. This is a pervasive, correlated forensic signal — not idiosyncratic.
  Severity-weighted; only PRESENT, source-tied flags score; unsourced serious flags rejected
  by the verifier; absence is not a clean bill, only non-disclosure in the window read.
  Complements the inferred-heuristic RedFlagEngine. Fixture:
  handoffs/ai_cluster_red_flags_20260603.json.
- Utilization vs debt-service mismatch (the goal's "Utilization vs. debt service mismatch
  analysis at the deal and entity level" capability): per-issuer from filings. Result is
  honest and thin BY CONSTRUCTION — per-deal utilization and full debt service are rarely
  cleanly disclosed (1/8 disclosed a utilization figure; 1/8 disclosed full debt service).
  Where it IS disclosed: Cipher Mining's REVENUE is below its full debt service (coverage
  < 1x). The adversarial verify pass nulled CoreWeave's "debt service" because the figure
  was 2026 principal maturity, not P+I service — refusing to let a principal-only number
  masquerade as DSCR. The leg quantifies the disclosure opacity itself as a transparency
  red flag rather than fabricating a coverage number. Fixture:
  handoffs/ai_utilization_debt_service_20260603.json.
- Report now leads with a "Scoped Burry Conclusion" block: the binary call (core
  `bubble_dynamics_present` @ 0.67 confidence; ecosystem `not_established`), the crack
  timeline (near-term 2025-Q3..2027-Q3, majority breach by the adverse scenario), and the
  top-3 register risks — fulfilling the Final Report's "clear binary conclusion with
  confidence score" + "specific timeline for cracks" up front.
- Top actionable-risk register (fulfills the Final Burry Report's "Top 10-15 actionable
  risks with supporting data" requirement): 10 ranked, severity-weighted (1-5) risks
  synthesized deterministically across the seven verified layers + red-flag scorecard,
  each anchored to a computed/sourced number, its backing layer, and a source-status tag.
  Ranked output (all 10 source_backed): (1, S5) cluster cash-flow fragility — positive
  coverage leans on CoreWeave and flips NEGATIVE by the adverse case; (2, S5) refinancing
  treadmill on negative carry ($54.8B, 6-10% refi); (3, S4) anchor-customer concentration
  (8/8 issuers >35%); (4, S4) pervasive internal-control/accounting red flags (8/8 serious);
  (5, S4) single-counterparty contagion (NVIDIA supplier+investor circular); (6, S4) GPU
  economic life < depreciation schedule; (7, S3) TSMC CoWoS single-source supply gate;
  (8, S3) demand-side off-BS leverage; (9, S3) downside socialized to insurance/pension
  (households); (10, S2) ratepayer exposure (largely protected). A risk enters only if its
  backing layer is source-backed; nothing asserted above its evidence tier.
- Evidence audit coverage now includes 542 claim audits: analyzer-level capital,
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
  the report invariant checker also verifies that the direct/watchlist/
  not-established AI-linkage partition sums to the final metric. Current QA
  reports 0 errors, 0 warnings, and 0 invariant violations.
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
- Automated materiality adjudication decisions: 6,663 decisions, with 4,250
  supported blockers, 2,413 still requiring deeper extraction, 2,705 approved
  metric rows, and $3.622T deduped final metric support across 1,326
  source-instrument/same-accession/strict-cross-filing/economic-obligation/
  same-content-quote-collision/exact-cross-filing-quote/economic-event metric
  groups. The economic-event layer collapses one offering counted across
  proposed/priced/closed/indenture filings for curated direct-tier AI issuers,
  removing ~$29.9B of same-instrument over-count from the direct-linkage bucket
  while preserving distinct facilities (conflicting coupon/maturity-year).
  Semantic
  hard flags are now zero in approved metric rows;
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
- Debt-service term cards now have a deterministic normalizer:
  `bubble.ingestion.compute.normalize_debt_service_card_rows` and
  `scripts/normalize_debt_service_cards.py`. It turns long-form source cards
  into facility-level rows with maturity, rate/spread/coupon, undrawn fee,
  collateral, recourse, covenants, and verification status, while keeping
  press-only facilities out of primary-verified DSCR/timing coverage. The
  direct-tier card pack now covers CoreWeave, IREN, TeraWulf, Applied Digital,
  CleanSpark, Hut 8, Nebius, and MARA. Current normalization yields 19
  actionable facilities: 3 primary-verified facilities totaling $5.75B and 16
  unverified or needs-extraction facilities totaling $34.95B, with the remaining
  primary-card gaps concentrated in collateral, recourse, maturity, and rate
  fields. A read-only alignment checker now compares these cards with current
  final-metric survivors; the 21:21 decisions show $140.901B of current metric
  survivors across the 8 direct-tier entities versus $40.70B of carded
  facilities, making this the next explicit audit queue for economic-event
  dedupe and primary debt-service extraction.
- The direct-tier debt-service evidence layer now includes a supplemental
  primary-EDGAR collateral/recourse/covenant pack:
  `handoffs/claude_debt_service_verified_collateral_recourse_20260602.md` and
  `handoffs/fixtures/debt_service_verified_collateral_recourse_20260602.csv`.
  It adds 30 field-level rows across 8 facilities (27 primary-EDGAR, 2 partial,
  1 derived) covering IREN Hardware 3 DDTL collateral/limited guarantee/rate,
  TeraWulf WULF and Flash Compute secured-SPV terms, Hut 8 DC secured notes,
  and parent-unsecured convertible recourse for CleanSpark, MARA, and Nebius.
  This improves DSCR, timing, collateral-recovery, and downside-bearer
  evidence without changing the committed-debt metric.
- `scripts/check_direct_tier_debt_service_field_coverage.py` now converts that
  long-form evidence into a facility-level coverage fixture:
  `handoffs/fixtures/debt_service_verified_field_coverage_20260602.csv`. It
  reports 3 core-structural verified facilities, 1 collateral/recourse/rate
  verified facility, 3 parent-unsecured recourse verified convertibles, and 1
  aggregate-context row, while keeping remaining missing covenants/rate fields
  visible for DSCR/payback work.
- A companion direct-tier economic-event duplicate checker now turns that queue
  into row-level review clusters:
  `scripts/check_direct_tier_economic_event_duplicates.py` writes
  `handoffs/fixtures/direct_tier_economic_event_duplicates_20260602.csv`. The
  current run finds 9 same-issuer/same-amount clusters with $32.925B of possible
  repeated excess; $29.925B is probable same-instrument review and $3.0B is an
  explicit IREN negative control with conflicting maturity years. This is still
  read-only QA, not a metric adjustment.
- A validated direct-tier debt-event classification fixture now provides the
  next production-review input:
  `handoffs/fixtures/direct_tier_debt_events_classified_20260602.csv`, checked
  by `scripts/check_direct_tier_debt_event_classifications.py`. It validates
  55 live packet IDs with 0 errors: 26 same-event collapse candidates
  ($54.030B), 24 keep/negative-control distinct facilities ($96.409B), and 5
  exclude-or-rebind human-review rows ($25.587B). This is a review fixture, not
  an automatic metric reduction.
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
- Broader materiality-adjudicated supported exposure: $3.622T across 1,326
  metric groups; this is a different scope from the curated capital-structure
  deal-graph debt-like metric above, not an additive increment.
- Established direct/watchlist AI-data-center-linked support inside that broader
  materiality metric is $0.363T on the same 1,326-group final metric
  representative base. A read-only mixed-evidence collision checker now reviews
  same-document/same-metric-quote groups with different evidence quotes; current
  output finds 26 review groups, all distinct-facility candidates, with 0
  aggregate/component candidates. Both AI-linked candidates are
  distinct-facility cases, so the checker does not currently reduce the $0.363T
  established AI-linked support. The prior Hilton aggregate/component candidate
  is now resolved by blocking the unsupported $8.85B transaction-tranche-sum row
  while preserving the $7.60B term-loan and $1.00B revolver component rows.
  A seller-side revenue guard now blocks the TeraWulf $12.8B HPC lease aggregate
  contractual-value row from being counted as TeraWulf debt; it remains a
  source-backed blocker pending buyer/seller economic-commitment classification.
  90.0% remains source-backed but not yet thesis-linked.
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
- It has not built complete project-level power/permitting deliverability. The ISO interconnection
  queues ARE fully ingested (16,253 records incl. all 9,263 PJM), but they are generation-side and a
  weak lens for data-center LOAD; a real firm-vs-queue rate needs utility large-load / load-interconnection
  studies. Deliverability is read from the tracker construction-status proxy.
- It has not proven an ECOSYSTEM-WIDE bubble conclusion (there is no defensible total-AI-leverage
  denominator yet). It DOES now state a scoped, source-backed AI-direct-core verdict
  (`bubble_dynamics_present` @ 0.67) — see the tiered verdict above.
- It has not yet produced the airtight version: 1 of 3 separation-test mismatch legs
  (realistic-util DSCR) is still illustrative. Who-bears-downside is quantified (by facility
  recourse) and contagion is mapped via SHARED-COUNTERPARTY hubs (NVIDIA = supplier AND investor
  across the cluster — the filing-verified circular loop; shared customers Microsoft/Google;
  shared lenders); only full multi-hop propagation through the capital-exposure graph remains.

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
