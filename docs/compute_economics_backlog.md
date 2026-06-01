# Compute Economics Add-On Backlog

This is a queued extension to the Burry report system. It should be implemented
after the current source-backed acquisition and physical-risk pipeline is stable
enough to support repeatable report refreshes.

The goal is to add a compute economics lens that tests whether AI capex can
earn through realistic GPU depreciation, utilization, pricing, and TAM limits.
The ideas below are inspired by filing-based public forensic analysis, including
the 1CoastalJournal style of GPU depreciation and capex ROI work, but every
production metric must be re-sourced before it enters the system. Public posts
can identify questions to ask; they do not satisfy the evidence gate.

## Research Leads to Incorporate

Priority ideas to add once the core acquisition pipeline is repeatable:

- GPU useful-life mismatch: compare disclosed 5-6 year accounting lives with
  observed replacement cycles, resale prices, and rental-rate compression.
- Generation transition risk: model how H100/H200 values are pressured by
  Blackwell, GB300, and Rubin availability.
- Capex ROI and payback: test whether announced AI infrastructure capex can be
  recovered at realistic utilization, pricing, power cost, and depreciation.
- TAM reality checks: compare stated TAM claims against realistic serviceable
  revenue, constrained by compute supply, power, demand, and customer budgets.
- Depreciation-to-EPS impact: quantify how shorter economic lives would affect
  2026-2027 depreciation expense, net income, and diluted EPS.
- Chip supply versus announced capacity: compare disclosed or estimated GPU
  supply with announced MW, cluster, and data center capacity.
- Case-file presentation: add report sections that show the specific filing
  numbers, red flags, and math trail behind each conclusion.

## Research Lead: AI Compute Case Files Style

The @1CoastalJournal / "AI Compute Case Files" style is useful as a backlog
source for questions and report framing. Treat it as an external analytic
framework to replicate with primary evidence, not as a production data source.

High-priority additions from that framework:

- GPU depreciation risk: source accounting useful-life assumptions by company
  and compare them with source-backed replacement cycles, observed secondary
  market prices, and cloud GPU rental-rate compression.
- TAM sanity checks: collect company-stated AI or data center TAM claims, then
  compare them with realistic serviceable revenue constrained by power,
  deployed compute, utilization, customer budgets, and pricing.
- Capex ROI and payback: calculate whether GPU-heavy capex earns back before
  technical obsolescence, refinancing walls, contract roll-off, or rental-rate
  compression.
- Depreciation-to-EPS impact: quantify how shorter economic lives would affect
  2026-2027 depreciation expense, net income, and diluted EPS.
- Supply versus demand: reconcile announced clusters and data center capacity
  with chip supply, delivery windows, interconnection evidence, and permit
  readiness.

Specific lead examples to validate with primary sources:

- xAI filing work: inspect any available S-1, offering documents, and exhibits
  for GPU depreciation, AI D&A, R&D expense drivers, and H100-to-GB200/GB300
  transition timing. Extract only source-backed rows with filing/accession
  identifiers, quotes, timestamps, and hashes.
- Useful-life mismatch: test whether companies disclose 5-6 year lives for
  servers, network equipment, or compute hardware while actual frontier GPU
  economic lives behave closer to 2-3 years.
- H100 depreciation: build a dated resale/rental-rate series before making any
  claim that H100 value or rental rates fell by a specific percentage.
- NVIDIA data center revenue and purchase commitments: use 10-K/10-Q segment
  revenue and commitment disclosures as the production source for TAM and supply
  sanity checks.

Output format:

- Add a case-file subsection to the final report with source quote, extracted
  row, calculation, red flag, confidence, and unresolved evidence gap.
- Keep each calculation reproducible from stored raw artifact URI, retrieval
  timestamp, content hash, document id, and extracted rows.

## 2026-06-01 User-Added Compute Economics Leads

These are explicit backlog additions from the current product direction. They
are hypotheses to validate, not source-backed metrics yet.

Priority order:

1. GPU depreciation module. Compare disclosed accounting useful lives with
   observed economic lives for V100, A100, H100, H200, B200/GB200, GB300, and
   Rubin. Flag 5-6 year accounting assumptions when source-backed resale,
   rental-rate, or replacement-cycle evidence supports a materially shorter
   useful life.
2. TAM reality check. Compare company-stated AI/data-center TAM claims against
   realistic serviceable revenue constrained by deployed compute, power,
   utilization, pricing, customer budgets, and current realized revenue.
3. Depreciation-to-EPS impact. Quantify how shorter economic lives would flow
   through 2026-2027 depreciation expense, after-tax income drag, and diluted
   EPS for hyperscalers and neoclouds.
4. Capex ROI and payback. Test whether GPU-heavy capex pays back before
   technical obsolescence, refinancing pressure, contract roll-off, or
   rental-rate compression.
5. Chip supply versus announced capacity. Reconcile announced clusters, MW, and
   GPU counts with source-backed GPU delivery, purchase commitments,
   interconnection evidence, permit readiness, and construction progress.

Specific claims to validate from primary or auditable sources before use:

- Any xAI S-1, offering memorandum, credit document, or exhibit references to
  GPU depreciation, AI D&A, R&D expense drivers, H100 replacement timing, or
  GB200/GB300 transition risk. Store filing/accession/document identifiers when
  public, or document lawful provenance when the source is not EDGAR.
- H100 resale values and rental-rate compression. Build a dated observation
  series from raw resale/rental snapshots; do not use social-post ranges as
  report inputs.
- NVIDIA data center revenue history, product transition timing, purchase
  obligations, and supply commitments. Extract from 10-K, 10-Q, 8-K, investor
  deck, and exhibit artifacts with segment/table references.
- Hyperscaler EPS impact. Source capex, depreciation, useful lives, tax rates,
  diluted shares, and segment revenue from filings before calculating EPS drag.

User-supplied validation targets to add to the acquisition queue:

- GPU generation series: V100, A100, H100, H200, B200/GB200, GB300, and Rubin
  launch timing, original price ranges, secondary-market observations, rental
  rates, and replacement-cycle evidence.
- H100 stress case: verify whether source-backed resale prices and cloud rental
  observations support a 2-3 year economic-life case and materially faster value
  decline than accounting useful-life assumptions.
- NVIDIA data-center revenue series: extract fiscal-year data-center revenue,
  growth rates, purchase commitments, and product-transition commentary from
  NVIDIA 10-K/10-Q filings and investor materials before using the numbers in a
  TAM sanity check.
- Hyperscaler earnings bridge: collect 2026-2027 capex, depreciation, tax-rate,
  diluted-share, and segment-revenue evidence so the report can calculate EPS
  drag under shorter compute economic lives.

Case-file output should show:

- source quote or table reference
- extracted row id
- calculation and formula
- red flag reason
- confidence level and LLM adjudication status
- remaining evidence gap

## Source Policy

Treat all numbers in analyst threads, social posts, and newsletters as research
leads, not production evidence.

Production rows must carry the same provenance fields as the rest of the system:

- raw source URI
- retrieval timestamp
- content hash
- filing/accession/document id when available
- page, table, or section reference
- extracted rows
- confidence and LLM adjudication status

Preferred sources are 10-K, 10-Q, S-1, bond prospectuses, investor decks,
equipment purchase disclosures, lease or hosting agreements, GPU resale market
snapshots, cloud rental rate histories, and hyperscaler depreciation policy
notes.

Specific source-acquisition targets:

- SEC filings and exhibits with depreciation policy changes, capex guidance,
  lease commitments, debt facilities, asset-backed financings, and equipment
  purchase obligations.
- Public offering, debt, or financing documents for neoclouds and private AI
  infrastructure companies when lawfully obtainable.
- NVIDIA and competitor data center revenue disclosures, segment commentary,
  product transition timing, and supply constraints.
- GPU resale market snapshots by model and date, stored as raw artifacts with
  hashes and retrieval timestamps.
- Cloud GPU rental-rate snapshots by provider, GPU model, region, contract term,
  and observed date.
- Hyperscaler and neocloud investor materials containing TAM claims, utilization
  claims, revenue targets, or payback assumptions.

## Module 1: GPU Depreciation Risk

Purpose: compare accounting useful life assumptions against realistic economic
life by GPU generation.

Initial fields:

- gpu_generation: V100, A100, H100, H200, B200/GB200, GB300, Rubin
- launch_date
- original_price_usd
- observed_secondary_price_usd
- observed_cloud_rental_rate_usd_per_hour
- observed_date
- accounting_useful_life_years
- modeled_economic_life_years
- depreciation_method
- source_uri and provenance fields

Core outputs:

- price depreciation from peak and from purchase date
- rental-rate compression by generation
- implied payback period at realistic utilization
- accelerated depreciation flag when economic life is shorter than accounting
  life by at least 24 months
- obsolescence pressure when a newer generation enters volume availability

## Module 2: TAM Sanity Check

Purpose: compare stated TAM narratives with revenue that could realistically be
captured under constrained demand, power, pricing, and utilization.

Initial fields:

- entity
- stated_tam_usd
- stated_tam_source_uri
- implied_revenue_capture_assumption
- realized_ai_or_data_center_revenue_usd
- utilization_assumption
- price_per_gpu_hour_or_mw_month
- addressable_customer_base
- modeled_revenue_low/base/high

Core outputs:

- stated TAM versus modeled realistic serviceable revenue
- required utilization to justify capex
- required price per GPU-hour or MW-month to justify capex
- red flag when required utilization or pricing is above observed market ranges

## Module 2B: Capex ROI / Payback

Purpose: test whether AI infrastructure capex can pay back before equipment
obsolescence, refinancing pressure, or contract roll-off.

Initial fields:

- entity
- project_or_cluster_id
- capex_usd
- gpu_capex_usd
- power_and_building_capex_usd
- contracted_revenue_usd
- spot_or_uncontracted_revenue_usd
- utilization_low/base/high
- gross_margin_low/base/high
- power_cost_usd_per_mwh
- depreciation_life_low/base/high
- debt_service_usd
- source_uri and provenance fields

Core outputs:

- simple payback period under low/base/high utilization
- debt-service coverage at realistic revenue and power-cost assumptions
- residual value sensitivity by GPU generation
- red flag when payback exceeds modeled economic life

## Module 3: Depreciation to EPS Impact

Purpose: quantify how accelerated depreciation flows through 2026-2027 earnings
for hyperscalers and neoclouds.

Initial fields:

- entity
- annual_ai_capex_usd
- data_center_capex_usd
- GPU capex estimate
- disclosed depreciation and amortization
- assumed accounting useful life
- modeled economic useful life
- incremental_depreciation_usd
- tax_rate
- diluted_shares
- EPS impact low/base/high

Core outputs:

- reported depreciation versus accelerated depreciation
- EPS drag by year and quarter
- free cash flow pressure after maintenance capex
- mismatch between capex growth and revenue growth

## Module 4: Chip Supply vs Announced Capacity

Purpose: compare announced compute/data center capacity with source-backed GPU
availability and delivery timing.

Initial fields:

- entity
- project_or_cluster_id
- announced_gpu_count
- announced_gpu_generation
- announced_mw
- disclosed_purchase_commitment
- supplier
- delivery_window
- observed_deployment_date
- source_uri and provenance fields

Core outputs:

- announced capacity versus sourced GPU delivery evidence
- implied GPUs per MW versus observed generation-specific ranges
- delivery slippage by quarter
- red flag when announced capacity lacks matching supply, power, or permit
  evidence

## Implementation Order

Current implementation status: the source-backed models, strict CSV loader,
deterministic analyzer, tests, and final-report section are implemented. The
remaining work is real source acquisition into `data/compute/` and broader
report calibration once those rows exist.

1. Add Pydantic models for `ComputeAsset`, `GpuPriceObservation`,
   `DepreciationPolicy`, `TamClaim`, `CapexPaybackCase`,
   `EpsDepreciationImpact`, and `ChipSupplyObservation`.
2. Add CSV loaders with strict provenance validation.
3. Add a deterministic `ComputeEconomicsEngine` for depreciation, payback,
   TAM, and EPS sensitivity.
4. Add claim audits for each output metric.
5. Add report sections:
   - GPU Depreciation Risk
   - TAM Reality Check
   - Capex ROI / Payback
   - Depreciation to EPS Impact
   - Chip Supply vs Announced Capacity
6. Add acquisition backlog entries for priority sources:
   - neocloud public financing or offering documents when available
   - hyperscaler 10-K/10-Q capex and depreciation notes
   - NVIDIA data center revenue disclosures
   - major GPU rental rate and resale market snapshots

## Open Validation Questions

- Which GPU price sources are reliable enough for production evidence?
- Can we separate GPU depreciation from broader data center D&A in filings?
- How much of each hyperscaler's capex is truly AI compute versus buildings,
  networking, power, and land?
- What utilization assumptions are source-backed rather than anecdotal?
- Which neocloud agreements disclose enough pricing, term, and utilization
  evidence to support payback math?
