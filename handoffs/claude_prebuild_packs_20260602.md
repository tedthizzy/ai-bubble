# Pre-Build Packs + Run-Ahead Research — 2026-06-02

- **From:** Claude (worker) · **For:** Codex · **Branch:** `claude/report-qa`
- **Method:** 2 UltraCode workflows — 10 prebuild lanes + 3 research lanes (13 read-only `Explore` agents) — **plus my own verification** of the high-stakes claims. Agent output is NOT taken at face value.
- **Golden corpus:** `handoffs/fixtures/golden_corpus.json` — 100 fixtures, **89/100 packet_ids auto-validated against the live decisions CSV** (the 11 "unverified" are contagion/physical rows keyed off *other* artifacts, not decisions packet_ids). content_hash/entity/source_uri in the JSON are taken from the **live row** (agents sometimes fabricated hashes).
- **Data is moving** (you're rebuilding). Treat counts as a snapshot; verify before adopting fixtures as test oracles.

## ⚠ Verification corrections (read first)

1. **`lender_as_entity_audit` "$5.7B leakage" is a FALSE ALARM — don't chase it.** I checked the bank-entity approved rows: M&T Bank ($3.5B), JPMorgan ($2.75B), Bank of Nova Scotia ($1.1B) are **issuing their own notes** (entity = issuer/obligor is correct; risk_bearer = noteholders); Goldman Sachs BDC is the **borrower**. Verified quotes are prospectus/pricing-supplement issuances. This is correct attribution, not leakage. The *real* role-as-entity problem is **agent/arranger-as-entity** (Goldman/Morgan Stanley as *Administrative Agent* pulled from the SpaceX shared exhibit) — already in `claude_materiality_dedupe_design_20260602.md` §B, and those are `triage_only`, not approved.
2. **Simulator baseline already moved:** your `19aab0a` fix is live — the CSV now shows S1 per-`metric_group_id` = **$9.227T (1929 groups)**, not $11.79T.

## DECISION-RELEVANT (you're on dedup/metrics now)

### Metric-aggregation simulator — strategy menu (reproduced on the live CSV)
| strategy | total | groups | note |
|----------|------:|-------:|------|
| S1 per `metric_group_id` (your current, post-fix) | **$9.227T** | 1929 | = your `19aab0a` |
| `content_hash` + amount | $9.216T | 1926 | ≈ your current grouping |
| `content_hash` alone | **$8.407T** | 1709 | −$0.8T more; risks merging different-amount instruments |
| `content_hash` + category (agent S4) | ~$10.59T | — | less aggressive |
| accession + amount (agent S3) | ~$7.21T | — | **breaks on 8 non-EDGAR sources (NYISO queue)** — don't use globally |

Takeaway: your current grouping ≈ `content_hash+amount`. The menu shows the safe envelope; `content_hash`-alone is the next step down but over-collapses different-amount tranches.

### Instrument-identity refinement (affects dedup precision — small, not urgent)
`content_hash` cannot be the sole key: **907 content_hashes map to multiple notionals** (one doc, many tranches). It both over- and under-collapses:
- **Over-collapse (verified):** Dropbox `content_hash ce6e7b24…` has **two distinct $1.0B tranches** (`contract_tranche_terms`) + one $1.74B → `(content_hash+amount)` merges the two $1.0B rows → possible **~$1B under-count**. Fix: add `seniority`/`tranche_id` to disambiguate same-amount tranches in one doc.
- **Under-collapse (verified):** Georgia Power **$18.4B across 102 records** with *different* content_hashes (prelim/final/reopening prospectuses) — these *should* collapse but content_hash-keying won't.
- **Proposed instrument key:** `(accession, borrower_cik, exhibit_filename, notional, rate, maturity, seniority, tranche_id)` — **excludes content_hash**. Fixtures: `golden_corpus.json → instrument_identity_resolver` (6 verified).

### Entity-family attribution (corroborates P0)
Utility families: Entergy (105 records / 12 entity variants: parent + 4 regional subs + 7 securitization tranches), Ameren (5), CMS/Consumers (34), Eversource/NSTAR (13). **Collapse rule:** same `content_hash` + same amount + parent-subsidiary relationship → **single metric entry at the PARENT level**, mark duplicates aggregate. (6 verified fixtures.)

## FIXTURE PACKS (in `golden_corpus.json`)

- **`golden_fp_fn_corpus`** — 30 fixtures, 7 packs: note_offerings, facilities, aggregate_shelf, recourse, lease_debt_conflict, source_provenance_edge (collateral = 0 matches). All 30 verified.
- **`counterparty_role_parser`** — 10 verified fixtures + regex design (admin-agent & trustee patterns highest precision; split on "and" for multi-party lists; party = uppercase legal name + `, as the <ROLE>`).
- **`collateral_recourse_classifier`** — 16 verified fixtures across 8 labels (secured/unsecured/first-lien/collateral-document/guarantee/non-recourse/bankruptcy-remote-SPV/asset-backed). CoreWeave = landmark non-recourse HPC financing; Blackstone/Encore = explicit first-lien.
- **`aggregate_shelf_classifier`** — 12 verified fixtures, 5 classes. **Metric-contamination signals:** PennyMac balance-sheet ($734–883B total liabilities) conflated with issued debt ($2.35B); servicing UPB ($733.6B) treated as debt outstanding. Alphabet shelf "may offer" still `needs_deeper_extraction`.

## QA AUDITS (triage / future-architecture)

- **`contagion_path_qa`** — 8,749 paths, **~25% have a quality issue:** 13.0% self-referential (entity name appears in counterparty = false join), **22.6% exact duplicates** (no dedup by deal/tranche), 19.1% `ENTITY_SUPPLIED_ONLY` provenance (only **6.4% FULLY_CORROBORATED**). Affects any contagion conclusion. (path-id fixtures in the workflow output; not decisions packet_ids.)
- **`physical_deliverability_qa`** — 17 unmatched high-MW MISO queue records (~3.9 GW false negatives), 11 weak permit matches (conf 0.54–0.66 false positives, e.g. H5 Denver), **77 projects flagged needing on-site generation permits with no permit evidence attached**, Equinix linked to 39 equipment matches (multi-source duplication).

## RUN-AHEAD RESEARCH (design docs)

- **`evidence_gate_consistency`** — **~80+ metrics displayed in `burry_question_answers` have NO EvidenceGate audit.** Only the 23 coverage/inventory claims + the final UNSUPPORTED bubble claim go through the gate. e.g. `current_debt_like_notional_usd`=$1.2T and `measured_annual_interest_usd`=$16.7B are serialized straight from `capital_metrics.to_dict()`/`debt_service_metrics.to_dict()` with no per-metric audit. The 0.25 cap is correct, but individual narrative numbers lack audit trails. **Recommendation (I can TDD this next):** a consistency checker that asserts every high-impact metric (> $100B) appearing in an answer has a corresponding `claim_audit` with an appropriate tier/confidence; flag any metric > $500B presented as INFERRED. Extends my report-consistency verifier.
- **`compute_economics_plan` / `neo4j_gds_readiness`** — design docs received; I'll fold the detail into a follow-up handoff (`claude_research_plans_20260602.md`).

## Caveats / what I did NOT do
- Read-only; no production edits; no artifact rebuilds. Lender-as-entity, simulator totals, Dropbox over-collapse, and the entity-family clusters were independently verified by me; the fixture packs are spot-verified (packet_ids auto-validated) but the *expected labels* are agent-proposed — confirm before using as oracles.
- Agent-reported `content_hash` values were unreliable; `golden_corpus.json` substitutes live values.
