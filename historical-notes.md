# Historical Notes — Implementation Reference

Consolidated implementation knowledge for the Burry forensic engine. Durable technical facts only.

## Current State (2026-06-02)
- Latest report: `data/reports/BURRY_REPORT_EvidenceGated_20260602-2121.json/.md`
- Gate: `high_confidence_final=false`, `bubble_confidence=0.25`.
- Final metric: ~`$3.652T` across `1,338` final-metric groups from `2,705` approved rows.
- AI/data-center linkage in the metric: `$392.9B` established direct/watchlist; `89.2%` not-established.
- Report consistency + strict invariants pass (0 errors / 0 violations).
- Loose untracked file `scripts/seed_graph 2.py` is a pre-existing stray — do not stage; it is not part of the build.

## Scale (data-acquisition targets already met)
- Entities: 2,377 CIK-matched / 2,356 expanded CIKs / 10,365 SEC-reference (target 1,200-2,000).
- Deals: 62,952 scanned / 16,254 debt-like / 1,022 in-scope (target 25,000-40,000 scanned).
- Capital graph: 5,036 nodes / 7,526 edges; 93,822 contract nodes / 189,129 contract edges; 1,277 bankruptcy-remote
  SPV contracts; 2,586 non-recourse contracts; 6,037 tranche nodes with maturity; 5,081 with interest rate.
- Contagion: 8,749 source-backed paths / 145 high-or-critical / $1.92T AI-infra notional.
- Timing: 3,263 signals / $3.25T 2024-2030 refinancing / $227B AI-infra / forward peak $172B ($22.25B AI-infra).

## Production Workflow
- **Regenerate report:** `uv run python scripts/generate_final_burry_report.py` → timestamped
  `data/reports/BURRY_REPORT_EvidenceGated_*.json/.md` (gitignored).
- **Rebuild materiality decisions:** `uv run python scripts/build_materiality_adjudication_decisions.py` (reads
  `materiality_adjudication_packets.csv` → `materiality_adjudication_decisions.csv`). Upstream:
  `build_materiality_adjudication_packets.py`. Decisions are rebuild artifacts — not hand-edited; changes come via guard
  logic or packet re-ranking.
- **Validation suite (run before commit):** `just ci` (= ruff check + ruff format + mypy + pytest). Plus report checks:
  `scripts/check_report_consistency.py` (0 errors), `scripts/check_report_invariants.py --strict` (0 violations).
- **Survivor loader (analysis):** `load_decisions(Path("data/reports/materiality_adjudication_decisions.csv"))` from
  `scripts/check_direct_tier_debt_card_alignment.py`, then `_final_metric_representative_decisions(decisions)` from
  `src/bubble/analysis/materiality_adjudication_results.py`. Survivor fields: entity, supported_amount_usd,
  evidence_quote, metric_dedupe_quote, content_hash, packet_id (`adjudication:<hash>` — use FULL id, never truncate),
  source_uri, ai_data_center_linkage, subcategory, counterparty, risk_bearer.
- Report artifacts (`data/reports/*`, `data/graph/*`) are gitignored; only code + fixtures + docs are committed. Report
  freshness tracked in `docs/acquisition_status.md` + `FINAL_DELIVERY.md` prose.

## Evidence Gate (`src/bubble/analysis/evidence.py`)
- `EvidenceGate(min_high_confidence=0.75, min_corroborating_sources=2)`.
- Tiers: MEASURED > CORROBORATED_ESTIMATE > SINGLE_SOURCE_ESTIMATE > INFERRED > UNSUPPORTED.
- Semantic caps: COMMITTED_DEBT 1.0; INDETERMINATE 0.5; ASSET_OR_CAPACITY / EQUITY_OR_PRODUCTION 0.3; BOILERPLATE_ONLY 0.25.
- **`max_permitted_report_confidence` (lines 418-429):** any UNSUPPORTED claim → 0.25; any INFERRED → 0.45; any blocking
  issue → min(0.6, weakest); else min(0.95, weakest). **The current 0.25 = ≥1 UNSUPPORTED high-impact claim.**
- `high_confidence_final=True` requires EVERY high-impact claim: tier ∈ {MEASURED, CORROBORATED, SINGLE_SOURCE},
  effective_confidence ≥ 0.75, semantic = COMMITTED_DEBT, ≥2 corroborating sources, human_review_status = APPROVED.
- **Unlock ladder:** clear UNSUPPORTED (0.25→0.45) → clear INFERRED (0.45→0.60) → clear blocking issues (→0.75) →
  APPROVED adjudication (→high_confidence_final). See `claude_gate_unlock_critical_path_20260602.md`.

## Metric Dedup Pipeline (`materiality_adjudication_results.py`, `_final_metric_representative_decisions` ~line 2138)
Filter to `metric_use_status == approved_for_metric_use`; group by `metric_aggregation_policy`; then sequential collapse
layers (order matters; any change needs a before/after-total regression):
1. `_source_hash_metric_dedupe_key` — same content hash.
2. `_economic_quote_metric_dedupe_key` — same entity + quote.
3. `_economic_obligation_metric_dedupe_key` — same obligation semantics.
4. `_accession_amount_metric_dedupe_key` — same filing + amount.
5. `_collapse_content_hash_quote_collision_representatives` — exact quote repeats in one doc.
6. `_collapse_cross_filing_exact_quote_representatives` — same quote across filings.
7. `_collapse_cross_filing_instrument_representatives` — same instrument across filings.

## Landed Guards & Checkers (production logic)
- Dedup: same-accession, strict cross-filing, resale-wrapper, amount-binding, malformed comma-grouping, semantic
  non-committed, identical source-quote collision, exact cross-filing selected-quote.
- `Block seller-side lease revenue from debt metrics` — removed the TeraWulf $12.8B HPC-lease (provider revenue, not
  debt). Keep incidental "lease" in credit-agreement/indenture text (FP control: 15 rows / $37.5B must survive).
- `Block title-bound facility aggregate metric rows` — removed Hilton $8.85B aggregate (kept $7.60B term + $1.00B revolver).
- Checkers (read-only, output to `handoffs/fixtures/`): report consistency, report invariants (+ relevance partition),
  metric integrity, provenance integrity, graph artifacts, timing dedup, mixed-evidence collisions, direct-tier
  economic-event duplicates, direct-tier debt-card alignment, debt-service field coverage, debt-event classifications.
- Debt-service card normalizer: `bubble.ingestion.compute.normalize_debt_service_card_rows`; long-form shape
  `entity,facility,field,value,source_tier,source` (+ optional source_uri, filing_accession, source_quote).

## Key Forensic Findings
- **AI-direct over-count ~$84.6B (economic-event repeats):** one offering counted across proposed→priced→closed→indenture
  docs. Primary-EDGAR-verified per name vs largest-ever-offering ceiling: IREN $43.88B→~$9B (largest offering $3.0B),
  TeraWulf $36→~$5.35B ($3.2B notes ×5, Flash Compute ×4), CleanSpark $13.64B→~$1.15B, Hut 8 $9.75B→~$3.25B (one
  offering ×3). Would move AI-direct core $392.9B → ~$310-321B. Fixtures: `miner_cluster_overcount_confirmed`,
  `direct_tier_debt_events_classified` (same_event/distinct_facility/needs_human_review + negative controls
  Eaton/Simon/Venture Global). The economic-event duplicate checker exists; the collapse logic does not yet.
- **Bubble thesis (AI-direct core):** loss-making issuers → secured debt via bankruptcy-remote SPVs on *depreciating GPU*
  collateral + single-customer contract cash flows (IREN Hardware 3: GPUs + Microsoft Contract cash flows, Limited
  Parent Guarantee; TeraWulf WULF/Flash Compute; Hut 8 DC; CoreWeave CCAC VII full parent guarantee) → serviceable only
  from *holed* take-or-pay contracts (CoreWeave 96% take-or-pay but "except nonperformance" carve-out + OpenAI/MSFT 71%
  concentration) → bunched into a **2030-2033 refinancing wall (88% of carded AI-direct debt)** that coincides with GPU
  obsolescence (H100 secondary $40K→$6-15K in ~2-3yr vs 6-12yr book life) and contract expiry. Physical buildout is real
  + power-advantaged (brownfield/ERCOT, firm interconnection) → risk has moved from concrete to demand+refinancing.
- **Debt-service rates (primary EDGAR):** CoreWeave SOFR+400bp; IREN Hardware 3 SOFR+225bp (Microsoft-backed, hedged);
  secured fixed TeraWulf 7.750%/7.250%, Applied Digital 6.750%, Hut 8 6.192%; parent convertibles 0.00-2.75% (deferred
  to dilution). DSCR<1 cluster-wide on EBITDA (all names loss-making).
- **Downside bearer:** secured-SPV creditors (collateral = depreciating GPUs + one contract); ratepayers (rate-base
  socialization where tariffs don't fully shift cost — AEP Ohio 85% min-take shifts it, Entergy 7 gas plants for Meta is
  stranded-risk); equity holders (convertible dilution). Role-field caveat: 79 survivors mislabel trustees/agents (U.S.
  Bank Trust, Wilmington Trust, BNY Mellon, JPMorgan-as-agent) as risk bearers — re-role to agent (not bearer); 125
  unresolved.
- **Economic-commitment headline inflation:** OpenAI's ~$1.4T "commitments" are mostly framework/LOI (OpenAI reset to
  ~$600B; NVIDIA $100B/10GW is a non-binding LOI + circular; Oracle $300B has no binding SEC disclosure; Stargate $500B
  mostly LOIs). Only OpenAI-CoreWeave $22.4B take-or-pay + Microsoft-OpenAI $13B equity are binding. Keep frameworks in a
  non-summing tier; do not count as committed obligations.
- **Exact-match dedup surface is exhausted** (cross-filing/truncation/cross-hash all $0 after the landed collapses).
  Residual size correction is the economic-event (per-deal) class, not blind predicate mining. The corpus-wide
  amount-in-quote predicate is ~66% FP — do not re-run as a blind scan; entity-anchored primary-EDGAR verification
  still surfaces real over-counts.

## Conventions
- Every fixture row: source_uri + (accession where applicable) + exact quote + classification + expected_behavior.
- Separate VERIFIED (primary filing) from PROPOSED (interpretation). Mark unextracted fields `needs_extraction`/`NEEDS`,
  never fabricate IDs/accessions/quotes. Keep negative controls in every dedup/guard fixture.
- Packet IDs are `adjudication:<hash>` — use the FULL id (a `[-N:]` truncation produced `ion:...` defects).
- Source tiers: `primary_EDGAR` / `primary_press` / `press_NOT_verified` / `needs_extraction` / `derived` / `reclassify`.

## Known Caveats
- Graph summaries (`capital_exposure_graph_summary.json`, `ownership_graph_summary.json`) are CSV-derived, not Neo4j/GDS
  backed (Neo4j is optional infra; in-memory CSV layer is authoritative for reports).
- iCloud sync creates duplicate strays (`* N.ext`, multi-digit too). A worktree-local `core.excludesFile` pattern
  suppresses them; clean with a `grep -E ' [0-9]+\.'` purge before commits.
- The Burry-question answers are gated `blocked_until_source_coverage_sufficient` until the high-impact claims pass the
  evidence gate.

## Open Critical Path
See `handoffs/claude_gate_unlock_critical_path_20260602.md`: the breadth is built; the goal's bottleneck is lifting the
high-impact Burry-question claims through the evidence tiers (UNSUPPORTED/INFERRED → MEASURED + corroborated + APPROVED)
so `high_confidence_final` can flip. Near-term milestone: high-confidence on the AI-direct core ($310-321B post-collapse
cluster), where primary evidence is end-to-end, then expand outward. Next production steps: (1) apply the economic-event
collapse with negative-control regression + report regen; (2) wire the verified AI-direct evidence into the report claim
audits so tier→MEASURED; (3) adjudicate those claims to APPROVED; (4) regenerate and read the new confidence cap.
