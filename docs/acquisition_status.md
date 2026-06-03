# Acquisition Status

Last updated: 2026-06-03 00:26 UTC.

This file is the operational snapshot for the current evidence corpus. The report
now carries a scoped, tiered verdict (below), but the ECOSYSTEM-WIDE binary is
still gated; treat the ecosystem call as a run log and the AI-direct-core call as
the scoped conclusion.

## Current Corpus

- Latest evidence-gated report: `data/reports/BURRY_REPORT_EvidenceGated_20260603-2028.md`
- Evidence gate: ecosystem `high_confidence_final=false` / `bubble_confidence 0.25` (by design).
- **Tiered verdict (`ai_direct_core_verdict`):** AI-direct core `bubble_dynamics_present` @ 0.67;
  ecosystem-wide `not_established_as_ecosystem_wide_bubble` (broad metric is mostly non-AI debt, so
  no defensible total-AI-leverage denominator). Source-backed cluster EBITDA/interest coverage 1.35x
  (7/11 issuers loss-making; CoreWeave DSCR incl. principal ~0.30x) PLUS the source-backed GPU
  depreciation gap (rental yields −60-75% + Amazon SEC 6→5yr); cluster total debt $54.8B (census).
  Only the realistic-utilization DSCR leg remains illustrative.
- Capital-exposure graph now INJECTS the source-backed AI-direct cluster (issuer debt
  -> lead arranger + GPU-supplier / strategic-investor / anchor-customer topology edges
  from the verified census + contagion fixtures), lifting graph AI-infra-relevant
  notional from ~$5B (Equinix only) to ~$56.5B and surfacing Goldman/Morgan Stanley/
  NVIDIA/Microsoft as cross-cluster hubs in the same 5,102-node production graph.
- Supply-side equipment-bottleneck layer (can they physically build it): 8 chokepoints
  from supplier filings (TSMC CoWoS, HBM, NVIDIA GPUs, gas turbines, transformers,
  gensets, cooling, electrical labor); all 8 gate the buildout, 6 are single-source/
  duopoly, lead times up to ~42 months (median ~24), 12 suppliers filing-verified.
- Debt-side end-holder routing (resolves the equity-only gap): the 8 cluster
  private-credit lenders (Apollo/Athene 51%, Blackstone 53%, KKR/Global Atlantic 44%,
  Carlyle, Brookfield, Blue Owl, Ares, Sixth Street) all draw material insurance/annuity
  + pension funding (median ~41% insurance-funded, 18 sources filing-verified), so the
  cluster's private-placement DEBT loss routes to policyholders/retirees — the channel
  13-F equity data cannot show. Aggregate funding mix, not per-facility attribution.
- Forensic red-flag scorecard (per-issuer Burry checklist from SEC filings, adversarially
  verified): all 8 cluster issuers carry a filing-tied SERIOUS accounting flag; 38 of 42
  present flags filing-verified. Most common: material_weakness_icfr (8/8),
  customer_concentration >35% (8/8), related-party/circular financing (7/8), auditor change
  (5/8), insider net selling (5/8). Highest-risk: Core Scientific, Hut 8, IREN. A SYSTEMIC
  (not idiosyncratic) forensic signal across the financed cluster.
- Utilization vs debt-service mismatch (deal/entity-level, the goal's named capability):
  per-issuer from filings. Honest, thin result by construction — per-deal utilization +
  full debt service are rarely cleanly disclosed (only 1 issuer disclosed a utilization
  figure, 1 disclosed full debt service). Where disclosed, Cipher Mining's REVENUE is below
  its full debt service (coverage < 1x). The verify pass nulled CoreWeave's "debt service"
  (it was principal-only, not P+I) — opacity is itself a transparency red flag.
- Per-entity weakest-links ranking (the goal's "clear identification of the weakest links"
  + "top high-risk entities with exact concerns"): composite = filing-verified red-flag
  score + financial fragility (negative EBITDA / net loss / leverage). Ranked: #1 Core
  Scientific (19.0: restatement + material weakness + concentration + negative EBITDA),
  #2 Hut 8, #3 TeraWulf, #4 IREN (partial going-concern), #5 CoreWeave ($21.4B debt). Each
  concern traces to its source layer; fragility is broad (8/8 serious flag, most EBITDA-negative).
- Contract-level recourse structure (who bears the loss, from the ACTUAL credit-agreement
  & guaranty exhibits Grok's locator surfaced): 22 facilities, 18 filing-verified — 16
  full-recourse-to-parent, 2 non-recourse, 1 limited; 8 parent-guaranteed, 1 bankruptcy-
  remote, 1 GPU-collateralized. Read `loss_concentrates_on_parent_equity` — confirms the
  census recourse finding with document language (e.g. CoreWeave's DDTL 5.0 parent guaranty
  has NO commercial cap, only a fraudulent-conveyance savings clause; DSCR ≥1.35x covenant;
  $35M cross-default). Non-recourse/bankruptcy-remote claims rejected unless the document states them.
- Cluster-boundary test: a 6-name adjacent breadth sweep (crypto-miners/HPC pivots) with an
  adversarial in-scope gate qualifies only 1 (Bit Digital) as genuine financed AI-infra; 5
  are crypto-only-marginal-AI (the verify pass corrected Bitdeer down + nulled a fabricated
  EBITDA). `cluster_is_bounded` — reinforces the scoped (not ecosystem-wide) verdict.
- BROAD boundary sweep (36 candidates spanning public/private neoclouds, crypto converts, DC
  developers, chips): 13 VERIFIED as financed_ai_infra_leveraged beyond the deep-8 — Crusoe,
  Lambda, Nscale, Vultr (private neoclouds), Vantage/QTS/Sabey/Switch/Iron Mountain (SPV/ABS-
  financed developers), Bitfarms/Bit Digital. So the financed cluster is ~20+, NOT 8-9; the
  deep-8 are the publicly-primary-source-verifiable core. (Riot/CleanSpark/MARA confirmed
  crypto-primary by their own 10-Ks.) Fixture: handoffs/ai_cluster_boundary_sweep_20260603.json.
- UNSUPERVISED CLUSTER DISCOVERY (`cluster_discovery.py`, the data-driven boundary, not asserted):
  StandardScaler -> PCA -> KMeans with k chosen empirically (silhouette + GMM BIC) + bootstrap
  stability, over scale-free financials of the 11 census issuers. PCA: first 2 PCs explain 82% of
  variance. Discovered split: a profitable-but-levered group (CoreWeave, IREN, CleanSpark, Bitdeer
  — EBITDA-positive) vs a cash-flow-NEGATIVE-fragile group (Applied Digital, Hut 8, MARA, Core
  Scientific, Cipher), with TeraWulf (30x leverage) and Nebius as outliers. The fragile cluster is
  DISCOVERED then labelled, bootstrap-stability 0.93. HONEST: n=11 -> silhouette 0.375 (modest),
  k=2/3/4 statistically close, so the *number* is uncertain; what's solid is the 2-axis structure
  + the robust fragile sub-cluster. Next rigor step: expand n with the boundary-sweep additions.
- EXHAUSTIVE ENTITY-UNIVERSE MAP (`entity_universe_map.py`): all 649 data-derived AI-infra entities
  (422 project owners + 216 capital-graph AI nodes + 36 sweep) classified into structural buckets
  via a 50-agent batched workflow, the financed-leveraged subset adversarially verified. Empirical
  composition: 137 private developers, 133 utility/power, 46 IG-REIT, 33 hyperscaler-demand, 30
  crypto, 21 financing-SPV, 15 chip/equipment supplier, 6 EPC, 200 unidentifiable — and only 28
  financed_ai_infra_leveraged (9 strictly confirmed). So the bubble-distress cluster is ~4% of the
  AI-infra universe — EMPIRICALLY bounded, not ecosystem-wide. Surfaced genuinely new material names:
  Crusoe (~$10-17B debt, private), EdgeConneX (~$10B ABS), Edged (~$2B). 153 public filers. This is
  the deep-modeled entity universe (each entity carries a sourced bucket + filer + AI-debt flag).
  Fixture: handoffs/ai_entity_universe_classified_20260603.json.
- CORE HARDENING (#4, GPU depreciation earnings-quality, `gpu_earnings_quality.py`): restating the
  cluster's GPU depreciation at a ~3yr economic life (vs the disclosed 4-6yr) adds ~$2.95B/yr of
  D&A across 6 issuers — CoreWeave's net loss roughly TRIPLES (-$1.17B -> -$3.62B), and Nebius (the
  only "profitable" name) flips NEGATIVE (its profit was an artifact of slow depreciation + non-core
  gains). Several issuers EXTENDED useful lives (CoreWeave 5->6yr, Nebius 4->5yr) — earnings-flattering,
  opposite the economic reality. Inputs (D&A, useful life) primary-sourced; economic life a labeled
  assumption; method = D&A x life-ratio (net compute-PP&E rarely disclosed). Fixture:
  handoffs/ai_gpu_earnings_quality_20260603.json.
- VERIFIED CLUSTER EXTENSION (`cluster_extension.py`): deep-modeled the new material members surfaced
  by the universe map — Crusoe, EdgeConneX, Bitfarms, Bit Digital confirmed in-cluster. Adds ~$7.4B
  RECOURSE debt (EdgeConneX ~$5.5B EMEA corporate facilities; Crusoe ~$1.15B). CRITICAL disentanglement:
  Crusoe's ~$10.75B associated debt is mostly NON-RECOURSE — the ~$9.6B Abilene JPMorgan loans sit at a
  Blue Owl / Oracle-lease JV/SPV that does NOT reach Crusoe's equity (and Abilene's expansion was
  scrapped Mar 2026). Edged excluded ($2B was a cumulative-financing headline, not debt). Fixture:
  handoffs/ai_new_cluster_members_20260603.json.
- Continuous-update harness (`bubble.ingestion.update_detector` + `scripts/check_for_updates.py`):
  diffs a fresh EDGAR submissions snapshot vs ingested accessions (189,737 found), prioritizes
  by form relevance, flags rerun. The report now also carries a Methodology/Assumptions/Limitations
  appendix.
- Named refinancing wall (specific maturities, $/% , most-exposed): $68.7B dated debt; peak 2030
  ($26.2B); near-term 2025-2027 $2.4B (3.5%) — named facilities (Core Scientific $1B Morgan Stanley
  term loan due 2027, Hut 8 Coinbase/FalconX, CoreWeave convertible notes, MARA line of credit).
- Graph Data Science: notional-weighted PageRank systemic centrality (`graph_centrality.py`) over the
  full 5,102-node / 7,617-edge capital-exposure graph. Ecosystem-wide systemic centers are the major
  utility/energy counterparties (PG&E, SoCal Edison, NRG, Shell Energy) + Morgan Stanley — the broad
  corpus is mostly non-AI — while the AI-cluster-specific systemic nodes (NVIDIA/Microsoft/shared
  lenders) remain in the contagion-hub layer.
- PRODUCTION NEO4J (done): the capital-exposure graph (5,102 nodes / 7,617 edges) is now loaded into a
  live Neo4j 2026.05.0 instance (`bubble.graph.neo4j_loader` + `scripts/load_graph_to_neo4j.py`) under
  uniqueness constraints + indexes, and native-Cypher analytics run IN the database. The AI-infra mass
  computed in Neo4j ($56.5B / 232 edges) cross-validates the in-code figure. The report surfaces
  `neo4j_production_graph`. (GDS plugin not installed on the local instance; the in-code weighted
  PageRank covers the GDS-algorithm side.)
- SATELLITE (done): Sentinel-2 before/after change detection (`bubble.ingestion.satellite` +
  `scripts/satellite_progress.py`, via Google Earth Engine) over ALL 762 georeferenced AI/data-center
  sites, server-side batched (14 reduceRegions calls; trivial EECU). Result: only 110/762 (14.4%) show
  ACTIVE construction/built-up change; 407/762 (53%) show NO significant ground change — a primary,
  non-filing physical confirmation of the announced-but-not-built thesis (Microsoft Fairwater validated
  the method with a strong NDVI −0.216 clearing signal; high-capacity no-change sites are the stranding
  tells). Surfaced as `satellite_construction` + 2 claim audits. Read with the construction-status proxy
  (cloud/seasonal noise applies).
- Core verdict evidence basis now enumerates the 2 PRIMARY source-backed legs PLUS 11 corroborating
  source-backed layers (honest depth; confidence unchanged at 0.67).
- Report now opens with a "Scoped Burry Conclusion": binary call (core
  `bubble_dynamics_present` @ 0.67; ecosystem not-established), crack timeline, and the
  top-3 register risks — the Final Report's "clear binary conclusion + confidence" up front.
- Top actionable-risk register (the Final Report's "Top 10-15 risks" requirement):
  10 ranked, severity-weighted (1-5) risks synthesized DETERMINISTICALLY across the
  source-backed layers, each anchored to a computed/sourced number + backing layer +
  source-status tag. Top 2 are severity-5 (cash-flow fragility flipping negative by the
  adverse case; refinancing treadmill on negative carry); all 10 currently source_backed.
- Evidence audit coverage: 555 claim audits now include analyzer-level capital,
  compute, and debt-service audits, explicit row/artifact-backed audits for
  high-impact Burry-answer rollups, and aggregate hooks for pending review
  capital, pending AI-infra capital, pending compute, weak-link AI-infra,
  debt-service maturity-wall, capital-graph total/AI-infra notional, and compute
  GPU-capex rollups. Capital-graph audits now also cover MW-based PPA capacity
  concentration, legal-family PPA concentration, and AI/data-center-gated
  risk-bearer and obligor rankings, so demand-side power offtakers and
  downside-bearer nodes are visible without reading the raw non-thesis graph
  ranking as the AI-specific answer. Physical execution audits now also cover
  distinct extracted terms, projects, on-site generation MW term-sum,
  behind-the-meter/off-grid flags, permit litigation/enforcement-risk flags,
  and queue-bypass/no-queue flags.
  Large numeric `key_metrics` values over $200B now have value-matched claim
  audits, including gross pending, path-summed, out-of-scope, pre-dedupe, and
  distinct basis labels so diagnostic totals are not read as clean exposure.
  Compute-economics coverage now also separates zero red flags from missing
  comparators: the report has 18 GPU generations without comparable
  depreciation signals, 10 TAM claims missing realized-revenue comparators, 2
  EPS impacts missing modeled economic depreciation, 9 chip-supply observations
  missing delivered-count comparators, plus 2 payback cases where 1 is blocked
  by missing cash-flow inputs and 2 are missing debt-service coverage inputs.
  The report consistency checker now also gates current report ID, final metric,
  metric groups, AI-attribution split, audit count, and compute blocked counts;
  it currently reports 0 errors and 0 warnings.
- Source invariant audit: passed at 2026-06-02 04:02 UTC, 63 CSV files
  and 9,208,844 rows scanned, 0 violations, 0 warnings.
- Generated report assets are internal evidence artifacts; the user-facing
  deliverable remains a high-level chat summary once the evidence supports it.
- Checkpoint: single-agent on `master` at `e72d74e`; the prior two-agent handoff
  queue was consolidated into `master` (`7638aa9`) and the role docs retired. The
  only untracked strays are `scripts/seed_graph 2.py` and the two Grok comm files.
  Recent landed work: economic-event collapse, separation-test mismatch ratios,
  source-backed cluster DSCR, physical-deliverability honesty, tiered verdict +
  adversarial-audit corrections.
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
- Source-backed physical execution terms: 821 distinct extracted terms across
  662 projects. The term-level rollup includes 16,778.4 MW of on-site
  generation evidence, 443 behind-the-meter/off-grid flags, 30 permit
  litigation/enforcement-risk flags, 5 queue-bypass/no-queue flags, and 1
  ratepayer stranded-asset transfer flag. These MW values are source-term sums,
  not project-deduped capacity forecasts.
- Compute economics rows: 272 total, including 180 source-backed rows after
  provenance dedupe.
- Source-backed timing signals: 3,263.
- Pending source-backed adjudication items: 6,773.
- Ownership graph: 425,765 LEI nodes, 425,679 named nodes, and 643,828 source-backed relationships.
- Contract-structure graph: 93,822 nodes and 189,129 source-backed edges.
- Contract/ownership contagion paths: 8,749 source-backed paths, including
  1,976 ownership-expanded paths, 6,773 contract-only paths, 453 AI-infra
  relevant paths, and 145 high-or-critical paths.
- Capital-graph PPA concentration now surfaces capacity-weighted AI/data-center
  offtake hubs separately from dollar exposure: Ohio Valley Electric Corporation
  is 31,296 MW across 3 source-backed PPA edges; Amazon/AWS is 16,276 MW across
  43 family-consolidated PPA edges; Alphabet/Google is 9,518 MW across 34
  suppliers; Microsoft is now family-consolidated across Microsoft Energy LLC
  and Microsoft Corporation to 5,767 MW after excluding intra-family transfer
  rows.
- Capital-graph AI/data-center exposure tagging now uses stricter entity and
  keyword matching to avoid unrelated `XAI Octagon` fund rows and truncated
  title-case `Ai` snippets. The AI-gated capital graph now has 139 relevant
  edges and $4.75B of AI-infra-relevant notional; the current AI-gated downside
  bearer surface is Equinix as guarantor against three Equinix financing issuer
  nodes totaling $4.75B.
- The displayed capital-structure downside-bearer list now includes a taxonomy
  quality summary. Its current top 15 named bearers are classified as
  risk-principal exposure, with $0 artifact/intermediary exposure in that
  displayed slice; a date/clause fragment formerly shown as `On May 29, 2026,
  the Parent` is now treated as unmapped rather than a named bearer. Unmapped
  downside-bearer exposure remains the binding gap at $460.362B across 432 deals
  and 454 unresolved bearer mentions.
- Materiality-first LLM adjudication packets: 6,663 blocker groups packaged
  (full deduped queue), all 6,663 source-backed, 6,663 with local evidence
  snippets, 706 AI-infra relevant, and $56.029T of total exposure-basis across
  the packet set.
- Automated materiality adjudication decisions: 6,663 decisions, 6,463 with
  resolved text quotes plus 200 row-context-backed decisions for non-text
  sources, 4,250 supported as material blockers, 2,413 requiring deeper
  extraction, 0 requiring source retrieval, and 2,705 source-backed rows
  approved for metric use. Those approved rows total $7.395T as row-level
  supported amounts, but source-instrument, same-accession/same-amount,
  strict cross-filing instrument-fingerprint, exact cross-filing quote,
  economic-obligation, and same-content/same-quote collision metric dedupe now
  collapses same-document/same-amount, exact repeated filing, exact selected
  quote repeats across filings, and identical source-quote amount collisions to
  $3.622T deduped final metric support across 1,326 metric
  groups;
  they are not treated as individual contracts unless contract terms are
  separately extracted.
- Report arithmetic invariants pass with 0 violations, including the AI-linkage
  relevance partition: direct plus watchlist equals established AI-linked
  support, and established plus not-established equals the final metric. The
  how-large answer now labels the $1.201T curated capital-structure deal-graph
  debt-like metric separately from the broader $3.622T materiality-adjudicated
  supported exposure metric so the two scopes are not read as inconsistent or
  directly additive.
- A read-only mixed-evidence collision checker now reviews same-entity,
  same-document, same-metric-quote groups that survived final metric dedupe
  because their evidence quotes differ. On the current decisions CSV it finds
  26 candidate groups: all 26 are distinct-facility candidates to keep
  separate, with 0 aggregate/component candidates. The 2 AI-linked candidates
  are both distinct-facility cases, so this review surface does not currently
  reduce the $362.976B established direct/watchlist AI-linked support.
- The when-cracks answer now carries its own debt-service timing coverage
  caveat: the maturity wall is a floor because 165 of 439 distinct debt-service
  obligations and $541.811B of distinct debt-like notional still lack
  maturity-date evidence; distinct measured-rate notional coverage is 44.2%.
- The hidden-risks/contagion answer now labels graph notional bases explicitly:
  capital-graph notional is deduped edge-level financing exposure, while
  contract-contagion notional is path-summed and multiplicity-inflated. The
  $44.591T total contract path notional and $1.919T AI-infra-relevant path
  notional are diagnostic graph-path surfaces, not headline exposure figures.
- Five Claude branch-safe research packs were imported for the next graph and
  downside-bearer passes: graph-layer parity, maturity/rate extraction targets,
  downside-bearer resolver taxonomy, utility/ratepayer downside, and
  entity-family graph-display guardrails. They are fixture/design inputs, not
  production metric changes.
- Three additional Claude branch-safe research packs were imported for
  forward-monitoring and scope calibration: bubble leading indicators,
  rate-coverage sibling-fill candidates, and hidden-leverage/economic-commitment
  taxonomy. These are also fixture/design inputs, not production metric changes:
  the leading-indicator catalog defines what to monitor for future crack-window
  movement, the rate-coverage sibling-fill pack narrows true coupon-extraction
  work to residual instruments rather than duplicate rows, and the
  hidden-leverage taxonomy separates committed-debt metrics from excluded
  off-balance-sheet economic commitments such as take-or-pay, hosting,
  colocation, and supplier-financing obligations.
- A utility/ratepayer acquisition-card pack now gives exact source targets for
  the first ratepayer-downside extraction pass:
  `handoffs/codex_utility_ratepayer_acquisition_cards_20260602.md`,
  `handoffs/fixtures/utility_ratepayer_acquisition_targets_20260602.csv`, and
  `handoffs/fixtures/source_catalog_utility_ratepayer_20260602.csv`. The
  catalog fixture validates through `load_source_catalog()` and targets Georgia
  Power PSC Docket 56002, Entergy Louisiana LPSC U-37425, FPL FPSC
  20250011-EI, Xcel Colorado PUC 26AL-0137E, Xcel Minnesota MPUC
  E022/M-25-289, and NextEra/Google multi-GW data-center campus development.
  These source targets are acquisition scope only; they do not quantify
  ratepayer exposure until docket/tariff/order extraction is run.
- A first deterministic extraction schema now exists for acquired
  utility/ratepayer regulatory text:
  `bubble.ingestion.regulatory.extract_ratepayer_terms`. It extracts MW
  thresholds and load-growth amounts, minimum contract terms, take-or-pay
  percentages, exit-fee percentages, load-factor percentages, incremental
  generation charges, dedicated-infrastructure cost-recovery language,
  ratepayer-subsidy risk/protection language, separate-customer-class terms,
  bring-your-own-generation directives, and data-center load-driver flags. This
  makes the PUC/IRP target pack machine-checkable once acquired, but still does
  not decide final ratepayer exposure.
- A Claude economic-commitment tier pack was imported for the hidden-leverage
  under-count side: `handoffs/claude_economic_commitment_tier_20260602.md` and
  `handoffs/fixtures/economic_commitment_tier_20260602.csv`. It separates
  binding buyer-side commitments and leases from seller-side backlog mirrors and
  non-binding/lessor-revenue claims. This is not folded into the committed-debt
  metric; it is a separate candidate exposure tier for take-or-pay, lease, and
  compute-capacity obligations.
- A deterministic economic-commitment extractor now exists at
  `bubble.ingestion.compute.extract_economic_commitments`. It classifies
  acquired compute/SEC text into datacenter purchase commitments,
  not-yet-commenced datacenter leases, seller-side remaining-performance-
  obligation mirrors, take-or-pay compute commitments, non-binding lessor
  revenue projections, and capacity-only/no-dollar disclosures. This prepares
  the hidden-leverage tier for source-backed extraction while preserving the
  double-count caveat between buyer obligations and seller backlog.
- The EDGAR compute-economics extraction pass now materializes those terms to
  `economic_commitments.csv` with source URI, content hash, document id,
  accession, quote, binding tier, and double-count caveat. Source-coverage
  accounting includes the new file as a compute-economics corpus member, so the
  off-balance-sheet commitment tier can be counted and audited alongside chip
  supply, depreciation, TAM, payback, and EPS-impact rows.
- Two physical-execution research packs were imported for the remaining
  physical/grid gate:
  `handoffs/claude_physical_execution_cards_20260602.md` and
  `handoffs/claude_onsite_gas_stranded_risk_20260602.md`, with fixture CSVs.
  They reframe top AI/data-center project diligence around permit and PUC
  handles where flagship projects are behind-the-meter rather than ISO-queue
  based, and define a separate on-site gas/stranded-asset risk surface. These
  are acquisition and architecture inputs only; they do not change the
  committed-debt metric or open the evidence gate.
- A compute payback-input bridge was also imported:
  `handoffs/claude_compute_payback_inputs_20260602.md` and
  `handoffs/fixtures/compute_payback_inputs_20260602.csv`. It documents that
  the current payback/unit-economics layer is input-starved and identifies the
  per-name revenue, capex, debt, and useful-life inputs needed before DSCR or
  payback conclusions can be made. The report now carries explicit blocked
  compute-economics counts so missing comparators are not silently reported as
  clean.
- A deterministic debt-service card normalizer now exists at
  `bubble.ingestion.compute.normalize_debt_service_card_rows`, with CLI
  `scripts/normalize_debt_service_cards.py`. It converts long-form
  source-backed cards for direct-tier AI/data-center borrowers into one row per
  facility with parsed maturity, floating spread/fixed coupon, undrawn fee,
  collateral, recourse, covenants, source tier, and verification status. This
  supports DSCR/timing coverage work without changing committed-debt metric
  totals; press-only facilities remain explicitly unverified. A direct-tier
  card pack is now imported for CoreWeave, IREN, TeraWulf, Applied Digital,
  CleanSpark, Hut 8, Nebius, and MARA, plus contract-durability and negative-
  carry summaries. Normalizing those cards yields 19 actionable facilities: 3
  primary-verified facilities totaling $5.75B, and 16 unverified or
  needs-extraction facilities totaling $34.95B. The residual extraction target
  is now explicit: 2 primary-verified facility rows still lack collateral, 2
  lack maturity, 1 lacks rate evidence, and 2 lack recourse evidence.
- A supplemental primary-EDGAR debt-service evidence pack now covers the
  collateral/recourse/covenant fields that were still thin in the card
  inventory:
  `handoffs/claude_debt_service_verified_collateral_recourse_20260602.md` and
  `handoffs/fixtures/debt_service_verified_collateral_recourse_20260602.csv`.
  It contributes 30 long-form rows across 8 direct-tier facilities: 27
  primary-EDGAR rows, 2 primary-EDGAR-partial rows, and 1 derived TeraWulf
  JV-share row. It primary-verifies IREN Hardware 3's DDTL rate, undrawn fee,
  GPU/Microsoft-contract collateral, limited parent guarantee, hedge, and
  covenants; TeraWulf WULF/Flash Compute issuer, coupon, security, guarantor,
  covenants, and JV share; Hut 8 DC notes' issuer, coupon, security, and
  covenants; and parent-unsecured/no-subsidiary-guarantee recourse for
  CleanSpark, MARA, and Nebius convertibles. This is field-level evidence for
  DSCR/timing/downside analysis and does not change committed-debt metric
  totals.
- A read-only coverage checker now summarizes that verified field pack:
  `scripts/check_direct_tier_debt_service_field_coverage.py`, writing
  `handoffs/fixtures/debt_service_verified_field_coverage_20260602.csv`. The
  current coverage surface has 8 rows: 3
  `core_structural_fields_verified` facilities, 1
  `collateral_recourse_rate_verified` facility, 3
  `parent_unsecured_recourse_verified` convertible facilities, and 1
  `aggregate_context_only` IREN Hardware 3 row. It preserves 27 primary-EDGAR
  rows, 2 partial-primary rows, and 1 derived JV-share row, and flags the
  remaining field gaps explicitly rather than implying full DSCR/payback
  readiness.
- A read-only direct-tier debt-card alignment checker now compares current
  final-metric survivors with the normalized direct-tier card inventory:
  `scripts/check_direct_tier_debt_card_alignment.py`. On the 21:21 decisions it
  finds 8 direct-tier entities with $140.901B of current metric survivors versus
  $40.70B of carded facilities, of which only $5.75B is primary verified. All 8
  entities are flagged for review because the current metric exceeds carded
  facilities by more than 10%; this is an audit queue for economic-event dedupe
  and primary debt-service extraction, not an automatic metric change.
- A second read-only direct-tier duplicate checker now isolates same-issuer,
  same-amount survivor clusters that may represent repeated economic events:
  `scripts/check_direct_tier_economic_event_duplicates.py`, with fixture
  `handoffs/fixtures/direct_tier_economic_event_duplicates_20260602.csv`. On
  the 21:21 decisions it finds 9 clusters with $32.925B of possible repeated
  same-amount excess. Eight clusters ($29.925B) are classified as probable
  same-instrument review candidates, led by TeraWulf's $3.2B 2030 note/facility
  cluster; one IREN $1.0B cluster ($3.0B excess) is intentionally labeled a
  distinct-facility negative control because the rows carry conflicting 2031,
  2032, and 2033 maturity evidence. This is a reviewer fixture, not a final
  metric reduction.
- A Claude direct-tier debt-event classification fixture has been imported and
  repaired for exact live packet IDs:
  `handoffs/claude_direct_tier_debt_events_classified_20260602.md` and
  `handoffs/fixtures/direct_tier_debt_events_classified_20260602.csv`.
  `scripts/check_direct_tier_debt_event_classifications.py` validates it
  against the current materiality decisions. The current fixture has 55 rows and
  0 validation errors: 26 `same_event` rows ($54.030B) expected to collapse to a
  representative after production review, 24 `distinct_facility` rows
  ($96.409B) expected to stay as keep/negative controls, and 5
  `needs_human_review` rows ($25.587B) expected to be excluded or rebound only
  after manual evidence review. This is an adjudication input for future metric
  logic, not a metric change.
- A deterministic physical-execution extractor now exists at
  `bubble.ingestion.physical.extract_physical_execution_terms`. It normalizes
  acquired permit/PUC/source text into machine-checkable physical execution
  evidence such as on-site generation MW, air permit identifiers,
  behind-the-meter/off-grid flags, queue-bypass/no-queue language,
  permit-litigation risk, PUC/utility approvals, and ratepayer stranded-asset
  transfer language. This is the first production bridge from the physical
  handoff cards to source-backed extraction rows.
- `scripts/extract_physical_execution_terms.py` now materializes those rows to
  `data/physical/physical_execution_terms.csv`; the latest run scanned 754,191
  tracker/queue/permit source rows and wrote 821 terms after explicit false-
  positive guards for PJM unit-number abbreviations and negated no-litigation
  language.
- `scripts/summarize_physical_execution_terms.py` now writes
  `data/reports/physical_execution_summary.json` and the evidence-gated report
  now includes `physical_execution_summary` plus key metrics for distinct terms,
  projects, term-level MW sums, and physical execution risk-term counts.
- The broader materiality metric is now split by adjudicated thesis linkage:
  $0.363T has established direct/watchlist AI-data-center linkage, while
  90.0% is source-backed but not yet established as AI/data-center-linked.
  This split now uses the same 1,326-group final metric denominator as the
  materiality metric after same-accession, strict cross-filing instrument, and
  same-content/same-quote collision dedupe.
  The unlinked tail is a scope gap, not a final no-link conclusion.
  Clear AI/HPC/bitcoin data-center operators including IREN, CleanSpark,
  American Bitcoin, MARA/Marathon, Hut 8, Applied Digital, CoreWeave,
  TeraWulf, Nebius, and Cerebras are normalized to direct linkage when entity
  tags are otherwise blank, watchlist, or not established. Galaxy Digital rows
  are normalized to direct only when the packet text itself names Galaxy Helios,
  CoreWeave, or data-center context; generic Galaxy corporate notes remain
  not-established. Indirect utility/telecom suppliers remain not-established
  until a source-backed fractional scope rule is defined.
- Semantic metric-validity gating now scans approved materiality rows as a
  separate source-text dimension; hard-flagged asset/capacity,
  equity/production, and boilerplate rows are blocked rather than approved for
  metric use, while indeterminate rows remain review candidates rather than
  high-confidence debt semantics.
  A same-filing quote-quality pass now reselects stronger committed-debt clauses
  for rows whose original selected snippet was semantically peripheral or lacked
  exact amount committed-instrument text when a same-entity/same-content-hash
  sibling clause is available. Quote reselection preserves stable approved-row
  metric grouping, but re-evaluates metric eligibility when the stronger quote
  itself proves undrawn capacity, terminated backstop capacity, or another
  non-committed financing-capacity disclosure.
- Decision coverage over packaged blocker groups: 100.0%; unresolved decision
  share is 36.18% (still extraction-bound, not source-retrieval-bound).
- Top remaining decision gaps are now named counterparty role extraction
  (1,203), collateral scope (670), recourse/guarantee scope (523),
  asset/UPB/financing-capacity splitting (287), split aggregate disclosure from
  committed obligations (228), source-quote committed-obligation
  semantic confirmation (188), specific committed-obligation equity/share or
  mortgage-production splitting (47), queue/permit/interconnection linkage (43),
  mega-obligation confirmation (33), missing underlying term-level clauses
  (29), shelf-capacity-vs-committed-financing distinction (26),
  resale-registration-vs-committed-financing distinction (12), mixed-currency
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
- AI-infra-relevant notional: $4.75B.
- AI-infra-relevant edges: 139.
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
- Materiality decisions: 4,250 source-supported blockers, 2,413 requiring
  deeper extraction, 0 requiring source retrieval, and 2,705 rows approved
  for metric use (6,463 quote-backed decisions plus 200 row-context-backed
  decisions on non-text sources).
- Automated row-level supported amount approved for metric use: $7.395T.
- Deduped automated final metric support: $3.622T across 1,326 metric groups
  after source-instrument, same-accession/same-amount, strict cross-filing
  instrument-fingerprint, exact cross-filing selected-quote, latest-snapshot,
  exact economic-obligation, and same-content/same-quote collision grouping. The
  same-accession collapse removed
  $220.077B of same-issuer, same-filing duplicate survivors that had different
  snippets, content hashes, subcategories, or counterparties but represented the
  same filed amount. The conservative cross-filing pass removed another $5.550B
  where same-issuer/same-amount representatives from different SEC accessions
  all shared both a coupon token and a maturity-year token.
- Same-content/same-quote collision dedupe now collapses only groups where all
  final-metric representatives share the same entity, content hash, metric
  dedupe quote, and evidence quote. This removes repeated extractions of the
  same selected source sentence with inconsistent parsed amounts while leaving
  mixed-evidence credit agreements, bridge/term/revolver stacks, and
  multi-tranche documents untouched for a separate acquisition-event treatment.
  This pass removed 39 metric groups and about $60.81B of deduped final metric
  support relative to report `2012`; 26 mixed-evidence collision groups remain
  unresolved and are not collapsed by this guard.
- Exact cross-filing selected-quote dedupe now also collapses source-instrument
  rows from different SEC accessions when the entity, supported amount, and
  selected evidence quote match exactly. This catches no-coupon/no-maturity
  credit-facility repeats that the stricter coupon/year instrument fingerprint
  cannot see. On the current corpus it removed one Fidelity National
  Information Services duplicate group and $8.00B of deduped final metric
  support relative to report `2033`.
- Seller-side AI/data-center lease revenue is now excluded from committed-debt
  metric eligibility. The TeraWulf row describing HPC lease agreements with
  aggregate contractual value in excess of $12.8B is retained as a source-backed
  blocker, but now carries the `separate seller-side contracted revenue from
  issuer debt obligation` extraction gap instead of being counted as TeraWulf
  debt. This pass removed one approved row, one metric group, and $12.80B of
  deduped final metric support relative to report `2043`.
- Title-bound credit-agreement aggregate rows are now re-evaluated after
  same-filing quote reselection. When a transaction-tranche-sum row is supported
  only by a title/party block, but same-filing component rows bind the actual
  term-loan/revolver amounts, the aggregate row is blocked pending component
  splitting. This resolved the Hilton $8.85B aggregate candidate while keeping
  the source-bound $7.60B initial term loan and $1.00B revolver rows eligible,
  removing one approved row, one metric group, and $8.85B of deduped final
  metric support relative to report `2108`.
- A resale-registration guard now blocks explicit selling-securityholder or
  no-proceeds registration snippets in capital and contract-tranche packets
  unless the selected source text also carries primary note-offering or
  lender-facility evidence. Quote selection now avoids blending a concrete
  primary note/facility snippet with a separate resale wrapper, so real note
  issuance evidence is not overblocked. Twelve rows now carry the `distinguish
  resale registration from committed financing` gap; the live final metric has
  dropped by four groups and about $17.50B across the capital and contract
  passes.
- Amount-bound undrawn or terminated capacity is now re-evaluated after same-
  filing quote reselection, so concrete non-committed capacity clauses such as
  undrawn revolvers and terminated bridge backstops no longer survive merely
  because the first selected quote was weaker. Real issued notes, existing
  senior note guarantees, and underwriter purchase-commitment boilerplate remain
  eligible when their amount is bound to committed financing. This pass removed
  another 94 approved rows, $291.37B of row-level support, six metric groups,
  and about $46.37B of deduped final metric support relative to the 15:12
  report.
- Residual capacity and amount-binding guards now also block consolidated-
  indebtedness roll-ups, available borrowing-capacity clauses, covenant-basket
  thresholds, weak rate-grid quotes whose selected evidence does not contain the
  bound amount, and zero-draw replacement revolvers. Committed bridge loans and
  `total committed amount` revolver controls remain protected. This pass removed
  another 31 approved rows, about $75.0B of row-level support, 14 metric groups,
  and $34.50B of deduped final metric support relative to the 15:47 report.
- Residual rollup and amount-binding guards now also block pro-forma combined
  financing totals, loan/receivable portfolio asset totals, total-capacity
  bundles, total long-term debt rollups, debt-maturity charts, total
  indebtedness schedules, and `totaled X comprised of...` multi-instrument debt
  baskets unless the source quote binds the supported amount to a specific
  committed obligation. This pass removed another 28 approved rows, about
  $159.91B of row-level support, 18 metric groups, and $113.75B of deduped
  final metric support relative to the 16:07 report.
- Malformed comma-grouped amount tokens in local SEC source documents now block
  metric eligibility pending source-quote reselection or corrected extraction.
  This pass removed the KADANT $40.75B parser artifact from final metric support
  while retaining the rows as source-backed blockers requiring deeper extraction.
  EDGAR acquisition and compute-economics money parsers now also reject
  malformed grouped tokens and concatenated redline amount runs before future
  deal, tranche, or compute rows are emitted.
- Semantic non-committed disclosure guards now block explicit mixed-shelf,
  preferred-equity, no-leverage fund, acquisition purchase-price, deposit/loan
  portfolio, earnings-release, and marketing-deck snippets from metric use when
  the selected source quote does not contain a specific committed obligation.
  Genuine committed snippets using `total committed amount`, `facility size`,
  `borrowing base`, `senior secured debt`, or facility-agreement language remain
  eligible. This pass removed another 73 approved rows, about $306.50B of
  row-level support, 38 metric groups, and $165.14B of deduped final metric
  support relative to the 16:29 report.
- Relevance split of that deduped final metric: $0.363T established
  direct/watchlist AI-data-center linkage; 90.0% remains not-established for
  thesis linkage. The split now ties exactly to the $3.622T / 1,326-group final
  materiality denominator.
- Clear AI/HPC/bitcoin data-center operators including IREN, CleanSpark,
  American Bitcoin, MARA/Marathon, Hut 8, Applied Digital, CoreWeave,
  TeraWulf, Nebius, and Cerebras are normalized to direct linkage when entity
  tags are otherwise blank, watchlist, or not established. Galaxy Digital rows
  are normalized to direct only when the packet text itself names Galaxy Helios,
  CoreWeave, or data-center context; generic Galaxy corporate notes remain
  not-established. Indirect utility/telecom suppliers remain not-established
  until a source-backed fractional scope rule is defined.
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
  asset/capacity, equity/production, or boilerplate rows; indeterminate rows
  remain queued for review rather than treated as high-confidence debt
  semantics.
- Same-filing quote reselection now replaces semantically peripheral or
  exact-amount-weak approved snippets with stronger same-entity/same-content-hash
  committed-debt clauses while preserving stable metric dedupe; this reduced
  indeterminate approved rows without changing approved metric counts or totals.
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
- GPU generations missing comparable depreciation inputs: 18.
- Depreciation policies: 32.
- TAM claims: 10.
- TAM claims missing realized-revenue comparators: 10.
- Capex payback cases: 2.
- Payback cases blocked by missing cash-flow inputs: 1.
- Payback cases missing debt-service coverage inputs: 2.
- EPS depreciation impacts: 2.
- EPS impacts missing modeled economic depreciation: 2.
- Chip supply observations: 9.
- Chip supply observations missing delivered-count comparators: 9.

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
