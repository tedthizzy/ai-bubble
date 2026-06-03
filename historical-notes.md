# Historical Notes — Implementation Reference

Consolidated implementation knowledge for the Burry forensic engine. Durable technical facts only.

## Current State (2026-06-02)
- Latest report: `data/reports/BURRY_REPORT_EvidenceGated_20260603-0026.json/.md`
- Gate: `high_confidence_final=false`, ecosystem `bubble_confidence=0.25` (BY DESIGN — see verdict below).
- Final metric: ~`$3.622T` across `1,326` final-metric groups from `2,705` approved rows (post
  economic-event collapse; was `$3.652T`/`1,338`).
- AI/data-center linkage in the metric: `$362.98B` established direct/watchlist, `$142.03B` direct.
  NOTE: the `90% not-established` is NOT a bubbliness measure — the `$3.622T` denominator is the whole
  EDGAR materiality corpus (casinos, student loans, utilities, telecom), so the AI share is not a clean
  ratio. Do not infer "only 10% AI-linked → not a bubble"; the honest ecosystem framing is "no defensible
  total-AI-leverage denominator yet."
- **TIERED VERDICT now in the report** (`ai_direct_core_verdict`, markdown "The Verdict (Tiered)"):
  AI-direct core `bubble_dynamics_present` @ **0.67** confidence (`0.85*(1-0.35*0.62)`); ecosystem-wide
  `not_established_as_ecosystem_wide_bubble`. Rests mainly on the ONE source-backed leg (cluster
  interest coverage); the realistic-util DSCR + GPU-depreciation legs are blocked/illustrative.
- **Source-backed cluster DSCR** (`bubble.analysis.cluster_dscr`, fixture
  `handoffs/fixtures/ai_direct_issuer_financials.csv`, 11 issuers, primary 10-Ks, adversarially verified):
  cluster EBITDA/interest coverage `1.35x` but leans on CoreWeave (~$2.4B EBITDA); ex-CoreWeave aggregate
  EBITDA NEGATIVE; 7/11 loss-making, 7/11 sub-1 interest coverage; CoreWeave DSCR incl. its $6.7B 2026
  principal wall ~`0.30x` (interest covered, principal only by refinancing); 67% Microsoft concentration.
- **Burry separation-test mismatch ratios** (`burry_separation_test`): debt-refi missing-rate 64.2% /
  $689.88B; physical deliverability is the honest tracker proxy (8.1% in-service, 23.6% under-construction,
  63.4% announced-only, 60.7% permit not_confirmed) — the 0.5% strong-queue-match is NOT a
  deliverability rate (`weak_lens_generation_queue_not_data_center_load`). **CORRECTION (verified):** the ISO
  queues ARE fully ingested — `queue_records.csv` has 16,253 records incl. all 9,263 PJM (+ NYISO 2,195,
  ERCOT 1,845, ISO-NE 1,751, SPP 960, CAISO 170, MISO 69). The gap is that these are GENERATION-side queues:
  only 26 of 16,253 records are data-center-load related (9 strong-matched). A firm-vs-queue rate needs
  utility large-load / load-interconnection data, not generation queues. (An earlier note + the workflow-2
  finding wrongly said "PJM un-ingested" — that was a subagent reading the 26-row matched subset; corrected.)
- Crack timing reconciled: structural AI-direct principal wall `2030-2033` vs near-term timing-engine
  refi pressure peak `~2026-Q2` (different universes; both real).
- Report consistency + strict invariants pass (0 errors / 0 violations); full gate green (ruff/mypy/pytest).
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
7. `_collapse_cross_filing_instrument_representatives` — same instrument across filings (strict: needs
   common coupon AND year).
8. `_collapse_economic_event_representatives` — economic-event repeats: one offering counted across
   proposed→priced→closed→indenture filings. Scoped to the 8 curated direct-tier AI issuers
   (`DIRECT_TIER_ENTITY_ALIASES`); collapses only the `probable_same_instrument_review` class (same
   amount + consistent single coupon/year + multi-accession, ignoring counterparty which varies across an
   instrument's filings); preserves `distinct_facility` (conflicting year/coupon, e.g. IREN $1B ×4) and
   descriptor-free `amount_only`. **The dict-row mirror in `quality/relevance_linkage.py` re-implements
   the full pipeline INCLUDING this layer — both must stay in sync; they share the alias map + descriptor
   core via import (`canonical_direct_tier_entity`, `economic_event_year_coupon_tokens`).** Oracle:
   `scripts/check_direct_tier_economic_event_duplicates.py` should show `probable_same_instrument_review`
   → 0 clusters after collapse (negative control `distinct_facility` preserved).

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
- **AI-direct over-count — economic-event repeats (collapse LANDED for the conservative same-amount class):**
  one offering counted across proposed→priced→closed→indenture docs. The **same-amount/same-instrument** subset
  (`probable_same_instrument_review`: identical amount + consistent coupon/year across multiple accessions) is now
  collapsed in-pipeline (layer 8 above): **−$29.925B across 8 clusters**, moving established AI direct/watchlist
  `$392.9B → $362.98B` (all from the `direct` bucket); total metric `$3.652T → $3.622T`, survivors `1,338 → 1,326`.
  Collapsed clusters (primary-EDGAR-verified): TeraWulf $3.2B/7.750%/2030 ×5, Applied Digital $2.35B ×3 + $2.15B ×2,
  Hut 8 $3.25B/6.192%/2042 ×2, IREN $2.6B ×2 + $2.0B ×2, TeraWulf $1.275B ×2, CleanSpark $1.15B/0.00%/2032 ×2.
  Negative control preserved: IREN $1.0B ×4 (`distinct_facility`, years 2031;2032;2033, coupons 0.25;1.00).
  **The larger ~$84.6B figure additionally included staged-amount repeats (proposed $X vs priced $Y, different
  amount-keys → not caught by the same-amount checker); those remain flagged for human review, NOT auto-collapsed**
  (skepticism-first: only the unambiguous same-amount class is automated). Fixtures: `miner_cluster_overcount_confirmed`,
  `direct_tier_debt_events_classified` (same_event/distinct_facility/needs_human_review + negative controls
  Eaton/Simon/Venture Global). Tests: `tests/analysis/test_economic_event_collapse.py`,
  `tests/quality/test_relevance_linkage.py`.
- **Bubble thesis (AI-direct core):** loss-making issuers → secured debt via bankruptcy-remote SPVs on *depreciating GPU*
  collateral + single-customer contract cash flows (IREN Hardware 3: GPUs + Microsoft Contract cash flows, Limited
  Parent Guarantee; TeraWulf WULF/Flash Compute; Hut 8 DC; CoreWeave CCAC VII full parent guarantee) → serviceable only
  from *holed* take-or-pay contracts (CoreWeave 96% take-or-pay but "except nonperformance" carve-out + OpenAI/MSFT 71%
  concentration) → bunched into a **2030-2033 refinancing wall (88% of carded AI-direct debt)** that coincides with GPU
  obsolescence (H100 secondary $40K→$6-15K in ~2-3yr vs 6-12yr book life) and contract expiry. Physical buildout is real
  + power-advantaged (brownfield/ERCOT, firm interconnection) → risk has moved from concrete to demand+refinancing.
- **Debt-service rates (primary EDGAR):** CoreWeave SOFR+400bp; IREN Hardware 3 SOFR+225bp (Microsoft-backed, hedged);
  secured fixed TeraWulf 7.750%/7.250%, Applied Digital 6.750%, Hut 8 6.192%; parent convertibles 0.00-2.75% (deferred
  to dilution). **Source-backed (commit 075ca7d, 11-issuer primary-10-K fixture):** cluster aggregate
  EBITDA/interest coverage `1.35x` — interest IS covered cluster-wide but propped by CoreWeave; ex-CoreWeave
  aggregate EBITDA is NEGATIVE; 7 of 11 issuers loss-making and 7 of 11 cannot cover interest from EBITDA
  (IREN/CleanSpark/Bitdeer do). DSCR INCLUDING principal is <1x where disclosed (CoreWeave ~0.30x with its
  $6.7B 2026 wall) — principal only serviceable by refinancing. (Earlier "DSCR<1 all loss-making" was an
  over-generalization the source-backed pull corrected.)
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
- The ecosystem-wide `high_confidence_final` stays `false` / `bubble_confidence 0.25` BY DESIGN — an
  ecosystem-wide bubble is genuinely not established (the metric denominator is mostly non-AI debt). The
  defensible high-confidence answer is the SCOPED AI-direct core verdict, which the report now states
  outside that gate. Do not try to force the ecosystem gate open; that would be overclaiming.

## Open Critical Path
**DONE (this session, master):** economic-event collapse (`7542037`); separation-test mismatch ratios +
honesty hardening (`10e3f5e`); source-backed cluster DSCR + physical-deliverability honesty (`075ca7d`);
tiered verdict synthesis (`e72d74e`) + adversarial-audit corrections (data-driven weakest links, data-gap
separation, honest ecosystem framing, reconciled crack timing, no truncation). The report now answers all
five Burry questions with a scoped, tiered, evidence-tiered verdict.

**Remaining (rigor, not blockers — task #11):** (1) **Physical deliverability lens** — the ISO generation
queues are fully ingested (16,253 records) but are the wrong lens for data-center LOAD; a real firm-vs-queue
rate needs utility large-load / load-interconnection studies (NOT a parsing task — the earlier "un-ingested
PJM" framing was a subagent error, now corrected). (2) **capital-exposure graph drops AI-direct GPU-SPV debt**
(shows ~$4.75B Equinix of $408B; CoreWeave's $21B+ DDTL/SPV debt absent) → who-bears-downside is qualitative.
(3) **refi wall is a curated ~$41B floor**, not an exhaustive census → `ai-direct-debt-census` workflow run
2026-06-03 to replace it. Mismatch legs: GPU-depreciation now has source-backed evidence
(`handoffs/gpu_price_evidence_20260603.json`: H100 rental −64-83%, Amazon's SEC 6→5yr server-life revision);
realistic-utilization DSCR still needs per-deal utilization inputs.
