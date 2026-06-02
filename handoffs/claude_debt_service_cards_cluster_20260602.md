# CleanSpark + Hut 8 + Applied Digital debt-service cards (Codex Active Direction #6)

**Base:** SEC EDGAR + pricing releases. READ-ONLY. **Deliverables:** `handoffs/fixtures/debt_service_card_cleanspark_…`,
`…_hut8_…`, `…_applied_digital_…` (long-form normalizer shape). **Impact: evidence-gate confidence (AI-direct core).**
Completes the negative-carry-cluster card set (CoreWeave/IREN/TeraWulf already delivered). These are the same names in
the over-count finding, so the cards are the real-instrument inventory behind it.

## Cards
- **CleanSpark — $1.15B** 0.00% (zero-coupon) conv notes due 2032 (net $1.13B), senior unsecured (EDGAR 000119312525280105).
  All 7 metric packets trace to this ONE offering → real captured debt $1.15B.
- **Hut 8 — $3.25B** 6.192% sr secured notes due 2042, issuer Hut 8 DC LLC, indenture 2026-04-27 (EDGAR tm2612880). All 3
  metric packets = this one offering (counted 3×) → real $3.25B.
- **Applied Digital — ~$8.8B** (est): APLD ComputeCo 2 LLC $2.15B 6.750% notes due 2031 at 98% (Polaris Forge 2, EDGAR
  000149315226008772) + APLD ComputeCo proposed $2.35B + ~$2.61B existing debt. The **$4.30B packet** is
  `needs_refs_check` (your `evidence_quote_refs` call) and the $2.35B-vs-$2.15B may be one downsized deal — flagged.

## Honesty notes
- `source_tier`: `primary_EDGAR` / `primary_press` / `needs_extraction` / `derived`. Collateral/recourse/covenants for
  the secured notes are `needs_extraction` (SPV issuers — pull indentures for recourse). Press-only not promoted.
- Nebius and MARA cards still pending (need research) — next in the queue.

## Verified vs proposed
- VERIFIED: sizes/coupons/maturities per `source_tier`; CleanSpark and Hut 8 each resolve to a single offering.
- PROPOSED: Applied Digital ~$8.8B total (pending the $4.3B refs-check and the $2.35B/$2.15B distinct-vs-downsized call).
