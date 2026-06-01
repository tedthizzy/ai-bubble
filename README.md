# bubble

**Michael Burry-Style Forensic Mapping of the AI / Data Center / Financing Ecosystem**

> Every node, edge, cash flow, risk, assumption, and hidden interconnection captured with full provenance, cross-referenced, and stress-tested. Maximum skepticism. Maximum rigor.

This system is deliberately engineered in the direction of a forensic analyst who assumes every optimistic projection is a potential liability until proven otherwise.

## VISION: The Complete "Burry Report" System

### Ultimate Goal

Build a **high-confidence forensic mapping and analysis system** capable of answering Michael Burry-style questions about the AI / Data Center / Financing ecosystem with real numbers, timelines, and evidence.

The system must be able to determine:

- Whether we are in a bubble
- How large the bubble is (in capital, leverage, and physical overbuild)
- When it is likely to crack (with specific timelines)
- Where the biggest risks and contagion paths lie
- Who ultimately bears the downside risk

### Core Philosophy

This is not a dashboard for enthusiasts. It is a **skeptical, forensic tool** designed to find the gap between the narrative and reality -- exactly the way Michael Burry would approach it. We prioritize truth over optimism, and we clearly distinguish between what is measured, what is estimated, and what is unknown.

### Target Scope (Go Big Mode)

- **750 - 900+ distinct entities** (hyperscalers, neoclouds, developers, financiers, power providers, SPVs, etc.)
- **16,000 - 20,000+ individual deals** >= $1M (leases, debt facilities, PPAs, land deals, equipment financing, SPV structures)
- Full coverage of the ecosystem's capital structure, physical execution, and risk transfer mechanisms

### Required Capabilities

#### 1. Data Ingestion Layer

- **SEC EDGAR** at scale (10-K, 10-Q, 8-K, bond filings, SPV disclosures)
- **Regulatory & Permit Data** (FERC, state PUCs, EPA, local zoning, air permits)
- **Project Trackers** (Cleanview, FracTracker, GlobalData, DCD)
- **Physical & Construction Data** (satellite imagery, interconnection queues, transformer backlogs)
- **Power & Energy Data** (ISO queues, PPA filings, on-site generation permits)
- **Ownership & Relationship Data** (corporate filings, state LLC records, guarantee disclosures)

#### 2. Knowledge Graph (Neo4j)

- Rich modeling of:
  - Entities (companies, projects, SPVs)
  - Deals (leases, debt, PPAs, land, financing)
  - Relationships (ownership, guarantees, collateral, debt waterfalls, SPV layering)
  - Physical assets (data centers, power infrastructure)
- Ability to trace off-balance-sheet risk and contagion paths

#### 3. LLM Extraction Pipeline

- High-quality, structured extraction from documents
- Entity resolution and relationship detection
- Confidence scoring + validation + retry logic
- Materiality-ranked LLM adjudication queue for low-confidence or high-impact items

#### 4. Analysis Engine (Burry Core)

- Red flag detection (aggressive assumptions, related-party risk, timeline slippage, incentive misalignment, circular financing)
- Multi-scenario stress testing (Base / Adverse / Severe / Tail)
- Physical constraint modeling (power availability vs announced capacity, permit status vs construction timeline)
- Utilization vs debt service mismatch analysis
- Concentration and contagion mapping

#### 5. Output & Reporting

- **Final Burry Report** that includes:
  - Clear yes/no on whether this is a bubble + confidence level
  - Timeline for cracks and peak stress (with specific quarters/years)
  - Quantified ecosystem metrics (total leverage, off-balance-sheet exposure, power risk %, refinancing walls, etc.)
  - Top risks with supporting evidence
  - Clear distinction between measured data, estimates, and unknowns
  - Actionable insights for a skeptical analyst

### Success Criteria

The system is successful when it can:

1. Produce a **Burry-grade report** that a professional investor would take seriously.
2. Show **real evidence** behind the key numbers.
3. Clearly state the **confidence level** on every major claim.
4. Highlight the **biggest gaps** and uncertainties that still remain.
5. Be **continuously updatable** as new filings, permits, and project data become available.

### Mindset & Tone

- Extreme skepticism toward optimistic narratives
- Focus on **cash flow reality**, **physical constraints**, and **who holds the risk**
- Clear separation between what the data actually shows and what is being assumed
- Willingness to call out overbuilding, leverage, and misaligned incentives

### Final Deliverable Vision

The end state is a system that can answer questions like:

- "How much real leverage exists when you include all the SPVs and insurance wrappers?"
- "What percentage of announced capacity is actually deliverable given power and permitting constraints?"
- "When do the major refinancing walls hit, and which players are most exposed?"
- "At realistic utilization levels, when does debt service exceed contracted revenue for the most leveraged players?"
- "Who ultimately bears the losses if this unwinds?"

## Core Principles (Non-Negotiable)

1. **Provenance on everything** — source, date, model, prompt hash, confidence, adjudication status.
2. **Graph as the living model** — Neo4j + GDS for debt waterfalls, contagion paths, concentration, off-balance-sheet exposure.
3. **LLM + deterministic hybrid** — edgartools + XBRL for numbers; LLM only for narrative, normalization, hidden entities. Multi-verifier on anything high-stakes.
4. **Adjudication gates first-class** — low-confidence or red-flag extractions go to a materiality-ranked LLM adjudication queue with full evidence context and override capability.
5. **Physical ↔ Financial reality check** — announced MW vs permits vs satellite vs equipment lead times.
6. **Materiality before completeness** — broad acquisition keeps running, but confidence comes first from adjudicating the top 50-100 exposures and claims that can move the conclusion.
7. **Replayable & auditable** — same input + same prompts + same models = reproducible conclusions (modulo documented non-determinism).
8. **Ethical by design** — polite scraping, rate limits, proper FOIA channels, no credential stuffing.

## Tech Stack (Production-Leaning from Day 1)

- **Python 3.12+** + `uv` (fast, reproducible)
- **Pydantic v2** — all domain models are the source of truth
- **edgartools** — best-in-class SEC EDGAR access (structured XBRL + filings)
- **Docling** — high-fidelity PDF/table/layout parsing (2026 standard)
- **instructor + Claude 4 / Grok / o3** — schema-enforced structured extraction + multi-verifier
- **LangGraph** — state machines for complex document reasoning + LLM adjudication checkpoints
- **Neo4j 5 + APOC + GDS** — graph + graph algorithms (centrality, shortest path for contagion, community)
- **Prefect 3** — long-running, scheduled, observable orchestration
- **Streamlit** — rapid forensic UI (adjudication queue, scenario simulator, graph explorer, Burry reports)
- **MinIO + Postgres** — raw artifacts + operational metadata/queues/audit

Full details in the approved implementation plan (`~/.grok/sessions/.../plan.md`).

## Quick Start (macOS)

```bash
# 1. Clone / enter the repo
cd /Users/ted/Documents/dev-archive/bubble

# 2. Install uv (if not present) + Python deps
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
just install          # or: uv sync --all-extras

# 3. Copy env and fill keys (at minimum ANTHROPIC_API_KEY for real extraction)
cp .env.example .env
# edit .env — add your LLM keys

# 4. Start the full stack (Neo4j + MinIO + Postgres)
just up
# Wait ~30-60s for healthchecks

# 5. Bootstrap schema only; production graph data comes from acquired sources
just bootstrap-neo4j

# 6. Build/acquire real source catalogs, then ingest a real public filing
just source-catalog --all-public --resolve-dynamic-public-sources
just ingest-msft

# 7. Generate first Burry-style report (red flags, assumptions, stress scenarios)
just burry-report MSFT

# 8. Launch the forensic dashboard + adjudication queue
just ui
# Open http://localhost:8501
```

One-command demo (after keys in .env):
```bash
just demo
```

## Directory Structure

See the detailed structure in the implementation plan. Key directories:

- `src/bubble/models/` — Pydantic heart (Entity, Deal, Risk, Assumption, Provenance, etc.)
- `src/bubble/ingestion/edgar/` — edgartools + LangGraph extraction pipeline
- `src/bubble/graph/` — Neo4j client with provenance-aware writes
- `src/bubble/analysis/` — red flags, physical deliverability risk, scenario runner, stress tester, contagion
- `src/bubble/ui/streamlit_app.py` — the Burry analyst cockpit
- `scripts/` — acquisition, extraction, report generation, and operational wrappers.
- `tests/` — real cached filings via vcrpy (never hits network in CI)

## The "Burry Test"

Can the system, with minimal operator guidance, surface the same class of concerns a forensic analyst would on a fresh 10-K or 8-K?

- Off-balance-sheet leverage via SPVs and guarantees
- Optimistic utilization / depreciation / power cost assumptions
- Concentration risk and single-tenant exposure
- Timeline slippage between announced capacity and visible permits/construction
- Incentive misalignment in the financing stack
- Physical constraint gaps (power, transformers, turbines)

If it cannot do this on real data, the system is not yet successful.

## Physical Deliverability Risk

The system now has explicit source-backed records for grid queues, permits, long-lead equipment, and observed construction progress. `PhysicalRiskEngine` turns those records into a component-level score:

- `interconnection` risk: firm power, queue status, and delay months
- `permits` risk: air/power/zoning status, contested or denied permits, missing generation permits
- `equipment` risk: transformers, turbines, switchgear, cooling, delivery status, and lead times
- `construction` risk: observed progress versus announced in-service dates

The resulting `PhysicalRiskAssessment` carries provenance, evidence tier, source counts, blocking issues, expected delay months, and a high-confidence eligibility flag. This is the foundation for replacing narrative physical-risk claims with auditable project-level evidence.

Physical capacity summaries also isolate active interconnection queue records explicitly tied to data-center, hyperscale, AI, or compute-campus load. The report separates direct data-center load requests from generation projects justified by data-center load growth, preserving queue ID, source URI, content hash, in-service date, customer, POI, and a short source excerpt for the top rows.

`match_data_center_queues.py` links those queue rows back to tracker-backed campus records when name, customer, county/state, and capacity evidence are strong enough. It writes a full pending-adjudication match audit to `data/physical/queue_project_matches.csv` and writes strong project-linked rows to `data/physical/queues.csv` for physical-risk scoring. Unmatched direct data-center load rows and explicitly data-center-driven supporting generation rows can also produce pending-adjudication `data/physical/queue_projects.csv` rows, with the official queue record as provenance, so real queue evidence is not discarded while waiting for tracker corroboration.

`match_physical_records.py` applies the same conservative source-linking pattern to EPA ICIS-Air permit rows and EPA/EIA generator records. It writes pending-adjudication audits to `data/physical/permit_project_matches.csv` and `data/physical/equipment_project_matches.csv`, then writes only strong project-linked rows to `data/physical/permits.csv` and `data/physical/equipment.csv`.

`physical_risk_summary.py` runs the project-level scoring path in parallel and writes `data/reports/physical_risk_summary.json`, including counts for assets with queue, permit, equipment, and observation evidence; source-backed queue capacity linked to projects; top blockers; and top risk projects.

Physical evidence can be loaded from a directory of CSVs:

```bash
just physical-evidence data/physical --as-of 2026-12-31
```

Expected files:

- `projects.csv` with one row per campus or physical asset
- `queue_projects.csv` for optional queue-derived direct-load and supporting-generation rows
- `queues.csv` for grid/interconnection records
- `permits.csv` for air, power, zoning, and construction permits
- `equipment.csv` for transformers, turbines, switchgear, cooling, and other long-lead equipment
- `observations.csv` for satellite or site-observed construction progress

Every row must include `source_uri`; optional `source_type`, `source_confidence`, `human_review_status` adjudication status, `page_or_section`, and `content_hash` fields feed the evidence gate.

## Compute Economics Backlog

The GPU depreciation, TAM sanity-check, capex payback, depreciation-to-EPS, and chip-supply modules are documented in `docs/compute_economics_backlog.md`. Public analyst threads and social posts are research leads only; production metrics must be re-sourced from filings, market snapshots, rental-rate data, or other auditable artifacts.

The implemented source-backed loader reads optional CSVs from `data/compute/`:

- `compute_assets.csv`
- `gpu_price_observations.csv`
- `depreciation_policies.csv`
- `tam_claims.csv`
- `capex_payback_cases.csv`
- `eps_depreciation_impacts.csv`
- `chip_supply_observations.csv`

Every compute row must include `source_uri`, `retrieved_at`, and `content_hash`; optional `source_type`, `source_confidence`, `human_review_status` adjudication status, and `page_or_section` fields feed the evidence gate. If no compute evidence is loaded, the final report keeps the compute-economics conclusion blocked rather than filling the gap with assumptions.

Acquired EDGAR documents can be mined for conservative compute economics rows:

```bash
just compute-economics --inventory data/edgar_acquisition/edgar_document_inventory.csv --output-dir data/compute --workers 32
```

Public GPU rental pricing snapshots can be acquired as source-backed market observations:

```bash
just gpu-pricing --output-dir data/compute --workers 8 --other-domain-concurrency 4 --other-requests-per-second 8
```

This writes raw HTML artifacts under `data/compute/raw_gpu_pricing/`,
`gpu_price_source_artifacts.csv`, normalized `gpu_price_observations.csv`, and
`gpu_pricing_acquisition.summary.json`. It uses bounded workers, per-domain
throttling, retries, and resume mode so repeated runs parse existing raw
artifacts without refetching unless `--no-resume` is set.

The current deterministic extractor writes depreciation policy rows and chip/supply commitment observations only when the source filing explicitly states the fact. It does not infer GPU prices, utilization, payback, or EPS impact.
The worker count only controls local parsing of already acquired documents; it does not increase SEC request rates.

## EDGAR Filing Manifest

Before claiming source coverage, build an auditable backlog of SEC filings and exhibits to parse:

```bash
export EDGAR_IDENTITY="Your Name your.email@example.com"
just edgar-manifest --all-public --since 2024-01-01 --max-filings-per-cik 120 --include-exhibits --max-workers 32 --sec-domain-concurrency 8 --sec-requests-per-second 8
```

This writes a timestamped manifest under `data/manifests/` with one row per filing candidate, including:

- normalized CIK, accession number, filing/report dates, form, item numbers, and primary document URL
- optional EX-2, EX-4, EX-10, and EX-99 document URLs from SEC archive filing indexes when `--include-exhibits` is used
- SEC submissions source URI and content hash provenance
- Burry relevance score for 10-K, 10-Q, 8-K material agreements/debt items, S-1/S-3/424B financing filings, and keyword hits such as credit agreements, guarantees, leases, PPAs, project finance, data centers, AI infrastructure, and SPVs

The manifest is an acquisition backlog, not extracted evidence. It tells the system which filings should be parsed next and quantifies source coverage gaps before any ecosystem-scale claim can be upgraded.

Download the prioritized source documents and emit pending-adjudication deal candidates:

```bash
export EDGAR_IDENTITY="Your Name your.email@example.com"
just edgar-acquire data/manifests/edgar_filing_manifest_YYYYMMDD-HHMMSS.csv --output-dir data/edgar_acquisition --max-workers 32 --sec-domain-concurrency 8 --sec-requests-per-second 8
```

This stores raw EDGAR documents under `data/edgar_acquisition/documents/`, writes `edgar_document_inventory.csv` with source URI, retrieval timestamp, accession/document id, byte count, and content hash, and writes a capital-loader-compatible `deals.csv` with extracted pending-adjudication rows. The output directory can be passed directly to:

The EDGAR commands use a global worker pool for local parsing/resume throughput while the per-domain limiter keeps `sec.gov` requests bounded. Increase `--max-workers` for local CPU-heavy parsing, but keep `--sec-domain-concurrency` and `--sec-requests-per-second` at or below the SEC fair-access lane.
Delta EDGAR acquisitions merge into the existing inventory and deal CSVs by
default so a small daily manifest does not replace the larger acquired corpus.
Use `--overwrite` only for an intentional full rebuild.

```bash
just capital-evidence data/edgar_acquisition
```

EDGAR candidate extraction uses context-supported deal notional, not the largest dollar number in a filing. Corporate scale metrics such as AUM, remaining performance obligations, generic investment commitments, fundraising commitments, and outstanding balance-sheet totals are rejected as deal notional unless later adjudication overrides them.

Production source data is guarded by an invariant: source rows and deal nodes must be backed by an actual source URI and cannot use inferred provenance.

Coverage can be measured at any point:

```bash
just source-coverage --data-dir data
```

The coverage report counts filings, entities, raw source documents, projects, queue records, permits, ownership records, tracker records, PPAs, lease agreements, extracted deals, and source-backed deals.

The curated public CIK watchlist is only the first layer. Build a source-backed entity universe from acquired PPAs, EDGAR deal candidates, tracker projects, permits, and equipment rows, then map public-company names to SEC CIKs using the SEC company ticker reference:

```bash
export EDGAR_IDENTITY="Your Name your.email@example.com"
just entity-universe --data-dir data --output-dir data/entity_universe
```

This writes `entity_mentions.csv`, `entities.csv`, and `expanded_edgar_ciks.csv`. Rows preserve source URI, retrieval timestamp, content hash, document id, and record index so expanded CIKs remain traceable to real corpus evidence. Use the expanded CIK CSV as the next input for larger EDGAR manifest runs after adjudicating the highest-impact matches.

```bash
just edgar-manifest --all-public --cik-csv data/entity_universe/expanded_edgar_ciks.csv --since 2024-01-01 --include-exhibits --max-workers 32
```

When a broad primary-document manifest already exists, build a focused
exhibit-only follow-on without refetching SEC submissions JSON:

```bash
just edgar-exhibit-manifest data/manifests/edgar_filing_manifest_YYYYMMDD-HHMMSS.csv --min-parent-relevance-score 120 --exhibit-index-workers 64 --sec-domain-concurrency 8 --sec-requests-per-second 8
```

This reads the existing manifest, fetches SEC archive directory indexes only for
selected high-signal parent filings, and writes
`data/manifests/edgar_exhibit_manifest_YYYYMMDD-HHMMSS.csv`. Use the output with
`just edgar-acquire` to download EX-10, EX-4, EX-2, and EX-99 contract-level
documents into the same source-backed EDGAR acquisition corpus. The EDGAR
acquirer writes both `deals.csv` and `tranches.csv` when source text supports
tranche-level debt/bond terms, and enriches deal rows with collateral snippets,
guarantors, SPV/non-recourse flags, source URI, content hash, accession context,
and pending-adjudication status. A single debt/security document can emit
multiple `tranches.csv` rows when explicit source text names separate term
loan, revolver, or note-series amounts; otherwise the extractor falls back to
one primary tranche candidate.

For non-EDGAR sources, use a real source catalog:

```bash
just source-catalog --output data/source_catalogs/source_catalog.csv
just source-acquire data/source_catalogs/source_catalog.csv --output-dir data/source_acquisition
```

Minimum catalog columns are `source_id`, `corpus`, and `source_uri`. Supported `corpus` values include `filings`, `source_documents`, `projects`, `queue_records`, `permit_records`, `equipment_records`, `construction_observations`, `ppas`, `lease_agreements`, `ownership_records`, `tracker_records`, and `extracted_deals`. Optional columns include `source_type`, `parser` (`auto`, `csv`, `json`, `xml`, `zip`, `xlsx`, or `text`), `document_id`, `entity_id`, `project_id`, `filing_accession`, and `meta_*` columns. Acquisition writes raw artifacts, `source_artifact_inventory.csv`, and normalized `source_rows/<corpus>.csv` files with retrieval timestamp, source URI, content hash, local path, and record index.

`just source-catalog` writes SEC submissions targets from a vetted EDGAR watchlist, includes public CAISO, NYISO, MISO, PJM, and SPP interconnection queue targets, includes EPA eGRID plant/unit/generator data, includes EPA ICIS-Air facility/program permit records, includes the Server Country data-center project tracker, and can append validated curated catalogs for ISO queues, permits, PPAs, leases, ownership records, tracker rows, and extracted deal feeds:

```bash
just source-catalog --curated-catalog data/curated/iso_queues.csv --curated-catalog data/curated/permits.csv
```

Live public source listings can be resolved into concrete artifact URLs at catalog-build time. For example, ERCOT's GIS report listing is resolved to the latest primary GIS workbook, ISO-NE's public queue page is resolved to the current Excel export, EIA's 860M page is resolved to the latest downloadable generator inventory workbook, FERC's Market-Based Rate `Entities to PPAs` data set is resolved into paged API acquisition rows, FracTracker's ArcGIS data-center tracker is resolved into paged feature-layer queries, and GLEIF's Level 2 relationship API is resolved to the latest `who owns whom` relationship-record CDF archive. The source-list URL, document id or release date, data-set timestamp, API page boundaries, and workbook/archive filename are retained in metadata:

```bash
just source-catalog --resolve-dynamic-public-sources --output data/source_catalogs/source_catalog.csv
```

Coverage reporting separates queued catalog targets from acquired artifacts, so the report can say how many filings, entities, projects, source-backed deals, and source-backed contract tranches are actually covered while also showing how much acquisition work is waiting. Derived graph node/edge outputs are reported through graph summaries and are not folded back into raw source coverage counts.

Acquisition is parallel by default. `source-acquire` uses a bounded worker pool (`--max-workers`, default 64), per-domain concurrency gates, retries with exponential backoff, and resume mode so existing raw artifacts are parsed without redownloading. SEC-hosted URLs require `EDGAR_IDENTITY` and are capped below the SEC's published 10 requests/second fair-access limit by default (`--sec-requests-per-second 8`; see SEC Developer Resources: https://www.sec.gov/about/developer-resources).
Acquisition summary JSONs persist the actual worker count, SEC/non-SEC request-rate settings, per-domain concurrency settings, retry count, and resume status used for each run.
Long EDGAR exhibit-manifest and document-acquisition runs accept `--progress-interval N` to emit machine-readable progress events every N completed parent indexes or documents.

The current operational corpus snapshot is tracked in `docs/acquisition_status.md`.
Update that file after material acquisition, extraction, adjudication-queue, timing, or
report refreshes so the docs stay tied to measured source coverage instead of
stale ambition.

`source-invariants` audits production CSV outputs for blocked seed/demo/mock/placeholder source URIs and missing direct-acquisition provenance. It writes `data/reports/source_invariant_audit.json`; use `--fail-on-violation` in CI or before publishing a report.

Local extraction is parallel by default where rows can be normalized independently. `ppa-deals` and `tracker-projects` both accept `--max-workers` (default 32), preserve source-row order in their outputs, and report the worker count used in their summaries.

## Capital Structure Analysis

Entity-level Burry reports now include `capital_structure` metrics computed from extracted `Deal` records:

- debt-like notional exposure
- off-balance-sheet, SPV-linked, non-recourse, or guarantee-linked exposure
- separate guarantee-linked and SPV/non-recourse exposure subtotals
- separate LLM-adjudicated exposure from pending-adjudication candidate exposure
- a high-notional adjudication queue for unapproved deterministic extraction candidates
- distinct candidate exposure after economic deduplication, plus duplicate candidate groups
- aggregate-obligation exposure separated from individual deal records
- quarterly refinancing walls
- near-term refinancing exposure
- top counterparty concentration
- downside bearers by role, including lenders, lessors, insurers, guarantors, noteholders, and bondholders

These metrics are evidence-gated from deal and tranche provenance. If extracted deals are sparse or unsupported, the report will say so instead of converting the gap into a false high-confidence conclusion.

The final report applies a deterministic AI/data-center ecosystem scope gate
before headline capital and debt-service metrics are calculated. It keeps the
raw acquired corpus intact, but excludes debt and lease rows from headline math
unless the row is tied to a core AI/data-center operator or contains explicit
AI/data-center deal evidence. Broader hyperscaler, utility, supplier, and
financier rows remain visible as balance-sheet context, but do not drive the
headline wall without direct evidence. The report writes `capital_scope` so
excluded rows, context rows, excluded debt-like notional, and inclusion reasons
remain auditable.

Debt-service output also separates raw extracted obligations from distinct
candidate economic obligations. Distinct rollups collapse repeated SEC rows
from the same accession/entity/notional group, preserve the duplicate candidate
groups, and keep raw obligations visible for audit before any refinancing-wall
or crack-timing conclusion is treated as high confidence.

Capital evidence can be loaded from a directory of CSVs:

```bash
just capital-evidence data/capital --as-of 2026-12-31 --near-term-end 2029-12-31
```

The extracted deal rows can also be compiled into a source-backed capital
exposure graph. This writes entity nodes, counterparty edges, and a summary of
top obligors, risk bearers, exposure edges, connected components, unmapped
high-notional deals, skipped generic counterparties, source URIs, and
adjudication status. The summary also separates direct AI/data-center keyword edges and
watchlist-entity edges from the broader acquired capital network, so unrelated
corporate financing does not silently become an AI-infrastructure conclusion.
It also writes `capital_contract_nodes.csv` and `capital_contract_edges.csv`,
which preserve source-backed deal, tranche, collateral, guarantor, project,
asset, non-recourse, and bankruptcy-remote/SPV structure for deeper contagion
mapping:

```bash
just capital-exposure-graph --data-dir data --output-dir data/graph
```

The contract-structure graph can then be joined to the source-backed ownership
graph to create a conservative contract/ownership contagion path artifact. The
join is currently exact legal-name matching only; unmatched high-impact
guarantee and collateral paths are still retained as contract-only adjudication items.
Outputs are written to `data/reports/contract_contagion_paths.csv` and
`data/reports/contract_contagion_summary.json`, with SEC/GLEIF source URIs,
content hashes, adjudication statuses, notional exposure, ownership path depth, and
risk flags preserved on each row:

```bash
just contract-contagion-paths --data-dir data --output-dir data/reports --max-paths 50000
```

The default path cap is 50,000 so broad contract graphs are not silently clipped
at the first 10,000 source-backed paths.

Acquired ownership records can also be compiled into a source-backed legal
entity ownership and consolidation graph. The graph currently targets GLEIF
relationship records and preserves source URI, retrieval timestamp, content
hash, local raw artifact path, source record index, document id, relationship
status, relationship type, validation source, and quantifier fields. It writes
nodes, edges, and a rollup summary used by the final evidence-gated report:

```bash
just ownership-graph --data-dir data --output-dir data/graph
```

Weak-link scoring combines the capital exposure graph with source-backed
physical execution risk to create a ranked triage list for the report:

```bash
just weak-links --data-dir data --output-dir data/reports
```

The report-level adjudication queue combines the highest-impact pending items across
capital extraction, contract-tranche extraction, weak-link scoring, physical
match audits, contract/ownership contagion paths, and compute economics rows.
It writes `data/reports/review_queue.csv` and
`data/reports/review_queue_summary.json`; every item keeps source URI, content
hash, page or section, source confidence, adjudication status, ecosystem
relevance tags, and a legacy review-group id for duplicate-aware triage. The summary
separates raw pending capital notional from adjudication-grouped notional, separately
tracks pending contract-tranche adjudication notional, separately tracks pending
contagion-path exposure, and breaks out the
AI-infrastructure-relevant subset so broad corporate financing does not silently
dominate the Burry worklist:

All review/adjudication statuses are cleared by automated LLM adjudication.
Legacy columns named `human_review_status` are treated as adjudication-status
fields; there is no required operator gate in this workflow.

```bash
just review-queue --data-dir data --output-dir data/reports
```

The broad queue can then be collapsed into a materiality-first LLM adjudication
packet set. This deduplicates repeated review groups, ranks the top blockers by
priority, exposure, AI/data-center relevance, and risk score, attaches local
source snippets where the acquired artifact is available, and emits explicit
decision questions/fields for automated adjudication. It writes
`data/reports/materiality_adjudication_packets.csv` and
`data/reports/materiality_adjudication_summary.json`:

```bash
just materiality-adjudication --data-dir data --output-dir data/reports --limit 250 --snippets-per-packet 3
```

The packet set can then be adjudicated into conservative decision rows. This
does not convert unresolved rows into final metrics; it separates
source-supported blockers from rows that still need deeper extraction, quote
retrieval, duplicate/aggregate splitting, counterparty-role extraction,
collateral/guarantee scoping, or explicit rate/maturity evidence. It writes
`data/reports/materiality_adjudication_decisions.csv` and
`data/reports/materiality_adjudication_decision_summary.json`:

```bash
just materiality-adjudication-decisions --data-dir data --output-dir data/reports
```

The crack-window timing layer then combines source-backed capital and tranche
maturities, physical COD/queue dates, EPS depreciation timing, and chip delivery
windows into a quarter stress calendar. It writes
`data/reports/timing_signals.csv`, `data/reports/timing_signal_quarters.csv`,
and `data/reports/timing_signal_summary.json`; every signal requires source URI
and content hash provenance and is treated as a candidate timing indicator until
LLM-adjudicated:

```bash
just timing-signals --data-dir data --output-dir data/reports
```

Expected files:

- `deals.csv` with one row per lease, debt facility, bond, PPA, guarantee, or other contract
- `tranches.csv` with optional tranche-level debt/bond terms linked by `deal_id`;
  a source document may contribute multiple tranche rows when separate
  facility/series terms are explicit

Every row must include `source_uri`; optional `source_type`, `source_confidence`, `human_review_status` adjudication status, `page_or_section`, and `content_hash` fields feed the evidence gate. Use `counterparty_roles` and `key_terms` as JSON objects so roles, guarantees, SPVs, and lease classification flags remain structured.

Acquired FERC PPA rows can be normalized into `data/capital/deals.csv` without inferring dollar exposure:

```bash
just ppa-deals --input data/source_acquisition/source_rows/ppas.csv --output data/capital/deals.csv
```

Acquired project tracker rows can be normalized into source-backed physical project evidence:

```bash
just tracker-projects --input data/source_acquisition/source_rows/tracker_records.csv --output data/physical/projects.csv
```

This preserves the tracker source URI, raw artifact hash, local raw artifact path, and record index while carrying reported capacity ranges, investment, status, location, owner/operator/tenant fields, and source confidence into `projects.csv`.

## Current Status

This is an evidence-gated prototype, not a completed Burry-grade system. Current ecosystem-scale reports are treated as directional hypotheses until the evidence gate can prove the key claims with measured, corroborated, and LLM-adjudicated sources.

The report generator now caps confidence when a major claim is inferred or unsupported. This is intentional: the system should be skeptical of its own outputs before it is skeptical of the market narrative.

This is designed to become a live, continuously evolving forensic instrument (daily delta EDGAR, weekly deep re-validation, event-driven scenario re-runs).

See `justfile` for the full command surface and the implementation plan for the complete roadmap (Phases 0–6).

## License & Ethics

Internal forensic use. All scraping respects robots.txt and published rate limits. FOIA and regulatory requests must go through proper legal channels. No unauthorized access to private data rooms or systems.

Built with extreme prejudice toward hidden risk and optimistic narrative.
