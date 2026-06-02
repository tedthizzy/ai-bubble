# Maturity/rate coverage expansion map (backlog #18) — timing dimension

**Base:** current main `2180c00`, report `BURRY_REPORT_EvidenceGated_20260602-1759.json`. READ-ONLY; no prod writes.
**Codex import note:** imported on `c092b91`; the high-level timing coverage
caveat is now surfaced in the `1816` report, while the row-level issuer/source
targets in this pack remain acquisition/extraction candidates.
**Deliverable:** `handoffs/fixtures/maturity_rate_coverage_expansion_20260602.csv` (44 rows: entity, deal_ref,
notional, what's missing, maturity/rate if present, ai_relevant, source_uri, extraction method, negative-control flag).
Impact: **evidence-gate confidence (timing dimension)** — closes the debt-service rate/maturity gap that helps
justify or lift the 0.25 cap. All deal_refs/source_uris/values are pulled verbatim from the report (no fabrication).

## Report basis (authoritative, not my heuristic)
`debt_service_mismatch`: **439 distinct obligations; 339 missing rate; $599.5B distinct missing-rate notional;
rate coverage only 44.2%.** (I deliberately use the report's debt-service-scoped distinct counts, NOT a raw
survivor-quote scan — a raw scan flags 884/$2.66T but conflates the maturity gap with the over-count rows already
mined in the size lane.)

## Ranked extraction targets — the AI pure-plays ARE the gap (thesis-aligned)
Top AI-relevant, non-lease entity-level rate gaps (these are where extraction most moves the timing dimension):
- **IREN Ltd** — rate missing on **$45.5B across 40 obligations** (of $77.0B distinct).
- **TeraWulf Inc.** — rate missing on **$62.9B across 33 obligations** (of $73.3B); also several maturity+rate gaps.
- **Applied Digital Corp.** — rate missing on **$25.5B across 39 obligations** (of $35.6B).
- **CoreWeave, Inc.** — rate missing on $6.6B (4 obligations); + an $8.5B coverage-gap row.
These four bitcoin-miner-to-AI-datacenter / neocloud names carry the bulk of the AI-attributable rate gap — their
convertible/secured notes have coupons+maturities recoverable from their 424B/indenture exhibits.

## Extraction method (per row in fixture)
- 424B/FWP prospectus → the notes table gives coupon% + maturity per tranche.
- Credit-agreement exhibit (ex10) → Schedule/Section gives maturity date + applicable margin (rate as base+margin).
- Each row carries its `source_uri` (real EDGAR filing) + `deal_ref` + the per-issuer obligation count to prioritize.

## Negative controls (do NOT extract / exclude — 9 rows flagged)
- **Alphabet lease coverage-gaps ($75.6B ×N, deal_type=lease)**: these are the Alphabet operating-lease class already
  handled as **$0 committed-debt metric contribution** (your $80B equity-raise fixture). They dominate Alphabet's
  $564B entity-risk number — so **Alphabet's headline rate-gap is lease-inflated, not committed debt**; exclude the
  lease rows before treating Alphabet as a real extraction target. (Flagged `LEASE/over-count -- exclude` in the CSV.)
- Rows with `maturity_date` already populated (e.g. the top_debt_service_obligations) are NOT gaps — don't re-extract.

## Verified vs proposed
- VERIFIED: the 439/339/$599.5B/44.2% basis, every entity's missing-rate notional + obligation count, every
  deal_ref/source_uri (all from the 1759 report JSON).
- PROPOSED: the extraction-method assignment per row + the prioritization (AI pure-plays first). Per-row candidate
  coupon/maturity SNIPPETS require an EDGAR read pass (workflow) — flagged as the follow-up, not done inline here.
