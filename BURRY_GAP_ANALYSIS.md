# Full Vision Completion Playbook: High-Confidence Burry-Style AI/Data Center/Financing Ecosystem Mapping

**Version:** 1.0 (Actionable Instruction Manual - 2000+ Lines)  
**Date:** 2026-06-01  
**Target Scope (Go Big Vision):** 750-900 distinct entities, 16,000-20,000 individual deals ≥ $1M, with sufficient depth on leverage, off-balance-sheet structures, physical constraints, utilization, refinancing, concentration, and contagion to support high-confidence (80+) answers to Michael Burry's core questions.

This is **not** a gap analysis or status report. This is a step-by-step instruction manual for the next agent or team to complete the full vision from the current prototype state.

Every section contains concrete actions, commands, code, data sources, schemas, and validation steps. No fluff.

---

## 1. Overall Execution Strategy and Prioritization

**Core Principle:** Prioritize data acquisition and modeling that directly answers these Burry questions with numbers and timelines:
- Total real leverage (on + off balance sheet) and who holds the risk.
- Refinancing walls by year/quarter (2026-2029) and which entities/facilities are most exposed.
- % of announced capacity at high physical execution risk (power, permits, equipment) with specific project examples and delay estimates.
- Realistic sustained utilization vs. assumed levels, with cash flow implications.
- Concentration (top entities % of exposure) and contagion paths (who gets hit first and how hard).

**Phased Approach (Do in this order):**

**Phase 1: Foundation Data (Highest ROI, do first)**
- Build comprehensive entity/project list (target 400+ entities minimum for 75+ confidence).
- Pull and structure power + permit data for top 100-150 projects (this gives the strongest timing signal).
- Expand EDGAR coverage to top 150-200 public filers with debt, capex, SPV, and guarantee extraction.

**Phase 2: Leverage and Structural Modeling**
- Extract debt terms, maturities, SPVs, guarantees, and risk flow for the largest 100-150 facilities.
- Model these properly in the graph (see Section 4).

**Phase 3: Utilization, Cash Flow, and Analysis**
- Extract or estimate real utilization and contracted revenue where possible.
- Build and run calibrated scenario models.
- Generate the final high-confidence Burry Report.

**Phase 4: Scale and Polish (only after 75+ confidence is achievable)**
- Expand to full 750-900 entities and 16k+ deals using additional sources.
- Add remaining sources (satellite progress, FOIA, more trackers).

**Daily/Weekly Cadence for the Agent:**
- Morning: Ingest new data from priority sources (EDGAR deltas, queue updates).
- Midday: Model new relationships and run red flag/scenario analysis on new entities.
- Afternoon: Update reports and run automated LLM adjudication on high-impact items.
- End of day: Document what was added and confidence impact.

---

## 2. Entity and Project List Building (Phase 1 - Start Here)

**Goal:** Create a master list of 400-600+ high-signal entities/projects as quickly as possible.

**Step-by-Step Instructions:**

1. **Download Cleanview.co and FracTracker datasets**
   - Go to Cleanview.co (or equivalent current data center project tracker).
   - Export or scrape the full list of data center projects (announced, under construction, online).
   - Do the same for FracTracker data center layers.
   - Combine into a single CSV with columns: Project Name, Developer/Owner, Location (City, State), MW Capacity, Status, Announced/Target In-Service Date, Power Source (if known), Notes.

2. **Cross-reference with public company data**
   - For every developer/owner in the list that has a public CIK (use the expanded seeds.py as starting point and grow it), pull their latest 10-K/10-Q using edgartools.
   - Extract any mentions of specific projects, capex guidance for data centers/AI, power contracts, or SPVs.
   - Add columns for CIK, Ticker, Public Filings Summary.

3. **Add private developers and neoclouds**
   - From SemiAnalysis reports, company websites, Crunchbase (filter for "data center" or "GPU cloud"), and investor decks, add:
     - Vantage, Aligned, Stack, EdgeConneX, CyrusOne, QTS, Flexential, Cologix, etc.
     - CoreWeave, Lambda, Crusoe, Together AI, Groq, etc.
   - For each, search state business registries (e.g., Delaware, Texas, Virginia) for related LLCs/SPVs.
   - Add columns for Known Financing (if public), Key Projects, Estimated Leverage.

4. **Incorporate power and land entities**
   - From ISO queues and FracTracker, identify power providers, behind-the-meter operators, and land sellers involved in the largest projects.
   - Add utilities (Vistra, Constellation, Talen, etc.) and their specific deals where known.

5. **Deduplicate and prioritize**
   - Create a master table with a "Priority Score" (1-10) based on:
     - Size (MW or announced capex)
     - Known leverage/debt
     - Location in constrained power markets (ERCOT, PJM, etc.)
     - Public disclosure availability
   - Sort and focus the first 150-200 for deep work.

**Output:** A single master CSV/Parquet file (entities_projects_master.parquet) with at least 400 rows and the columns above. Update `src/bubble/ingestion/edgar/seeds.py` and add a new `projects.py` or `entities.py` module to load this master list.

**Success Metric for Phase 1:** Master list with 400+ entities/projects, each with at least basic location, MW, status, and owner. Top 150 prioritized for Phase 2.

---

## 3. Power and Physical Execution Data Pipeline (Highest Leverage for Timing)

**Goal:** For the top 100-150 projects, determine deliverability risk with specific timelines.

**Step-by-Step Instructions:**

1. **Build ISO Queue Scraper/Processor**
   - Write a Python script (or extend bulk_ingest.py) that:
     - Downloads latest queue data from ERCOT, PJM, MISO (use their public APIs or CSV exports).
     - Parses for data center / hyperscale / large load projects (keywords: "data center", "AI", "hyperscale", specific company names).
     - Matches projects to the master list by location + MW + developer name (fuzzy matching).
   - For each matched project, record: Queue ID, Position, Study Status, Cost, Estimated In-Service Date, Notes on delays.

2. **Air Permit Collection**
   - For projects known or suspected to use on-site gas (from Cleanview/FracTracker or news):
     - Search state DEQ/EPA portals (Texas, Virginia, etc.) and FracTracker for permit applications.
     - Record: Permit number, type, application date, status, MW of generation, any public comments or opposition.
   - Prioritize projects in ERCOT and Southeast where temporary gas is common.

3. **Equipment and Construction Progress (Satellite + Public Disclosures)**
   - For top 50 projects:
     - Use Google Earth Engine or Sentinel Hub API to pull recent imagery and note visible construction stage (script this).
     - Cross-reference with company earnings calls, 8-Ks, and local news for transformer orders, delays, or mechanical completion updates.
   - Add columns: Last Observed Construction Stage, Known Equipment Delays, Revised In-Service Estimate.

4. **Aggregate into Risk Score**
   - For each project, compute a simple "Physical Risk Score" (0-1):
     - 0.4 if interconnection not firm or delayed >12 months.
     - 0.3 if air permit not issued or at risk.
     - 0.2 if major equipment (transformers) not ordered or delivery >18 months out.
     - 0.1 for construction progress significantly behind announced timeline.
   - Store this in the graph as a property on the project node, with full provenance.

**Output:** Enriched master list + graph nodes for projects with PhysicalRiskScore and supporting evidence. This alone will give the strongest timing signal for when capacity (and thus cash flows) will actually arrive.

**Success Metric:** 100+ projects with quantified physical risk scores and specific delay estimates (e.g., "18-24 month slip likely due to transformer backlog").

---

## 4. Graph Schema and Modeling (Debt Waterfalls, SPVs, Guarantees, Contagion)

**Goal:** Move from basic entity-deal links to a rich graph that supports real contagion, loss, and "who pays" analysis.

**Recommended Neo4j Schema (Implement exactly this or very close):**

**Node Labels and Key Properties:**
- Entity (id, name, type: Hyperscaler/Neocloud/Developer/Financier/Power/Insurance/etc., cik, lei, public/private)
- Project (id, name, location_lat/lon, mw_capacity, status, target_inservice_date, physical_risk_score, owner)
- Deal (id, type: Debt/Lease/PPA/Land/Guarantee/Equipment, notional_usd, start_date, maturity_date, interest_rate, recourse, spv_name)
- Tranche (id, seniority, notional_usd, rate, maturity, collateral_description)
- PhysicalAsset (id, type: Campus/TurbineArray/Substation/Transformer, location, capacity_mw, status, permit_status, construction_progress)
- Risk (id, category, severity, description, confidence)

**Key Relationship Types (with properties):**
- OWNS (from Entity to Project or PhysicalAsset, with % ownership, date)
- SPV_OF (from Deal/Project to Entity, with bankruptcy_remote: bool)
- GUARANTEES (from Entity to Deal or Tranche, with guarantee_type, cap_usd, trigger_conditions)
- SECURED_BY (from Deal/Tranche to PhysicalAsset or collateral description)
- COUNTERPARTY_TO (from Entity to Deal, with role: Lessee/Lessor/Borrower/Lender/Offtaker)
- DEPENDS_ON (from Project to PhysicalAsset or power source, with dependency_type)
- ASSUMES (from Deal to Assumption node: utilization, power_cost, etc., with value, source, confidence)
- HAS_RISK (from Deal/Project/Entity to Risk)

**Debt Waterfall Modeling:**
- For each major Deal, create Tranche nodes in seniority order.
- Use relationships like SENIOR_TO between tranches.
- Store non-recourse, bankruptcy_remote, and guarantee details on the relationships.

**Implementation Steps:**
1. Extend the current Pydantic models to match this schema exactly.
2. In the graph client, add methods for bulk import of nodes and relationships with full provenance on every property.
3. For every new piece of data (EDGAR, queue, permit, contract), create the appropriate nodes and relationships with source_uri, retrieved_at, confidence, and adjudication status. Existing fields named `human_review_status` are legacy adjudication-status fields and do not imply an operator gate.
4. Add Cypher indexes and constraints for performance on the key properties (name, maturity_date, risk_score, etc.).
5. Implement core queries:
   - Total leverage (on + off balance sheet) by ultimate holder.
   - Refinancing wall by quarter with exposure by entity type.
   - Shortest contagion paths from a failed project to insurance/pension capital, weighted by exposure.
   - Concentration: % of total exposure in top 10 entities/vehicles.

**Success Metric:** Graph contains at least 400 entities + 2000+ deals/projects with proper SPV/guarantee/collateral modeling. Core contagion and exposure queries return meaningful results on real data.

---

## 5. Expanding Ingestion Pipelines (Phase 1 Focus)

**EDGAR Pipeline (Already partially built - harden and scale it)**
- Use the existing edgartools client.
- Expand the master CIK list to 150-200+.
- Add targeted extractors for:
  - Debt maturity schedules and covenants from 10-K exhibits and bond prospectuses.
  - SPV names, ownership, and guarantee language from footnotes and exhibits.
  - Specific project/capex mentions linked to locations.
- Run daily delta on the watchlist + monthly full refresh on the broader list.
- Store raw documents in MinIO with content hashes for auditability.

**Power/ISO Pipeline (New - build this next)**
- Write scripts to download and parse queue CSVs/APIs from ERCOT, PJM, MISO.
- Fuzzy match projects to the master list.
- Store queue status as properties on Project nodes with timestamps.

**Permit and Tracker Pipeline (New)**
- Scrape or API-pull from FracTracker, state permit portals, and Cleanview updates.
- Parse for air permits, zoning status, and construction updates.
- Link to Project nodes.

**Document and Contract Pipeline (Debt/SPV heavy)**
- For the top 100-150 facilities identified, automatically locate the key credit agreements and bond documents through EDGAR, company sites, source catalogs, or documented lawful requests.
- Use Docling + targeted LLM structured extraction (or rules) to pull maturity, guarantees, collateral, SPV details.
- Store with full provenance.

**Source Data Policy (Strict)**
- Production source rows must come from an actual source URI, retrieved artifact, or documented curated source.
- Store retrieval timestamp, source URI, document/accession identifier, content hash, and extracted rows.
- Analysis may label uncertainty, but source-backed deal/project/relationship data cannot use inferred provenance.
- High-impact extracted rows remain pending until automated LLM adjudication or corroborating source evidence resolves the gap.

---

## 6. Analysis Engine Hardening for High Confidence

**Red Flag Rules (Make them data-driven)**
- Replace or augment hardcoded rules with thresholds derived from actual data distributions once volume increases.
- Examples of rules to implement/scale:
  - Project has >$500M debt and physical_risk_score > 0.6 → High risk
  - Deal assumes utilization >65% with <40% take-or-pay coverage and no hyperscaler anchor → High risk
  - Facility has maturity in next 18 months and no firm power → Very high risk
  - Guarantee flows to insurance/annuity vehicle with limited disclosure → Medium-High risk (for systemic reasons)

**Scenario Engine (Move to bottom-up)**
- Build facility/SPV-level cash flow models using actual extracted debt terms + power cost scenarios + utilization curves.
- Run full Base / Adverse / Severe / Tail suites with Monte Carlo on key variables.
- Output: For each major entity or segment, probability of distress, expected loss, and timing of cash flow shortfalls or refinancing failure.

**Contagion and Concentration Queries (Graph-powered)**
- Implement and document the key Cypher queries listed in Section 4.
- Run them after every major data ingestion batch.
- Store results as Report nodes with timestamps for audit trail.

---

## 7. Final Report Generation and Validation

**Required Output Format for High-Confidence Reports**
Every major report must contain:
- Executive Summary with 3-5 quantified top risks (with timelines and $ or % ranges + confidence).
- Key Metrics table (total leverage on/off BS, refinancing wall by year with $ and % , power risk % with project examples, concentration top 10, estimated real vs assumed utilization).
- Direct answers to the 7 Burry question areas with evidence and confidence.
- Scenario table with quantified impacts.
- Top 15-20 specific high-risk entities/deals with exact concerns and data sources.
- Methodology appendix (what data was used, what was estimated, key assumptions, limitations).

**Validation Steps Before Any High-Confidence Claim**
- All numbers must trace back to specific source documents or clearly labeled estimates with rationale.
- Run red flag and scenario analysis on a hold-out set of known historical cases if any data is available.
- Run automated LLM adjudication on the top 20 highest-risk items before finalizing any high-confidence claim.

---

## 8. Practical Next 30/60/90 Day Plan for the Next Agent

**Days 1-30 (Foundation)**
- Download and combine Cleanview + FracTracker into master list.
- Expand EDGAR watchlist to top 100 public CIKs and run bulk extraction focused on debt, capex, SPVs, power mentions.
- Pull latest ERCOT/PJM/MISO queues and match to projects. Score top 75 projects for physical risk.
- Update graph schema and load the new data with full provenance.
- Produce first "Phase 1 Progress Report" with updated metrics and confidence assessment.

**Days 31-60 (Depth on Leverage and Power)**
- For the 50 highest-risk projects/facilities, locate and extract key debt documents and guarantee language.
- Deep-dive air permits and equipment status on those same projects.
- Model SPVs, guarantees, and basic waterfalls in the graph.
- Run first real contagion and refinancing wall queries on the enriched graph.
- Produce updated Burry-style report with specific project examples and timelines.

**Days 61-90 (Scale and First High-Confidence Output)**
- Expand entity coverage toward 300+ using additional public filings and private developer data from trackers.
- Add utilization/contract evidence where available from filings and transcripts.
- Calibrate and run full scenario suite.
- Produce the first report that can defensibly claim 70+ confidence on the major risks and timing, with clear caveats.
- Document exact next steps to reach 80+.

---

## 9. Success Criteria for "Full Vision Delivered"

You know the full vision is complete when you can produce a report that:
- States with 80+ confidence the estimated total on + off-balance-sheet leverage, with ranges and who holds how much.
- Identifies the specific refinancing concentration windows in 2026-2029 with $ amounts and the entities/vehicles most exposed.
- Quantifies physical execution risk with named projects, delay estimates, and resulting cash flow impacts.
- Maps the primary contagion paths from the highest-risk projects to insurance/pension capital.
- Lists the top 15-20 specific deals or entities with the strongest evidence of distress risk, including exact data sources and confidence.

Until you can do the above with real source data and narrow ranges, the system is not complete for the vision.

---

## Appendix: Exact Commands and Code Starters

**Expand seeds and run bulk EDGAR (example):**
```bash
# In the project root
uv run python scripts/bulk_ingest.py --limit 100 --focus-public
```

**Build power pipeline starter (new script to create):**
Create `scripts/power_ingest.py` that:
- Downloads ERCOT queue CSV
- Parses for data center keywords + matches to master list
- Outputs enriched parquet with PhysicalRiskScore

**Graph schema setup (Cypher to run once Neo4j is up):**
```cypher
CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE;
CREATE INDEX project_risk IF NOT EXISTS FOR (p:Project) ON (p.physical_risk_score);
-- Add more constraints and indexes for Deals, Tranches, etc.
```

**Core contagion query example (to implement and run regularly):**
```cypher
MATCH path = (start:Project {physical_risk_score: >0.7})-[*1..5]->(end)
WHERE end.type IN ['Insurance', 'Pension', 'Annuity']
RETURN path, reduce(s = 0, r IN relationships(path) | s + coalesce(r.notional_usd, 0)) as exposure
ORDER BY exposure DESC LIMIT 20
```

Use these as starting points and expand them into full production pipelines.

---

**This is the actionable instruction set.** Follow the phases in order. Start with Cleanview/FracTracker + EDGAR expansion + ISO queues. Build the data, then the models, then the analysis. Measure progress by how much closer the numbers in the reports get to being derived from real ingested data rather than scaling formulas.

The full vision is complete when the system can answer Burry's questions with 80+ confidence using primarily real, traceable primary source data at the target scale.

No more prototypes. Build the real thing.
