# Direct-tier maturity/rate normalized fixture (Codex message #2 — feeds timing normalizer)

**Deliverable:** `handoffs/fixtures/direct_tier_maturity_rate_normalized_20260602.csv` (14 facilities). **Impact:
timing dimension + debt-service normalizer.** Normalized rows ranked by **timing-wall year** (2030-2032 first), with
exact coupon/spread/benchmark/undrawn-fee/maturity + accession + source quote per row.

## Largest timing-wall impact first (2030-2032 is the ~$33B peak)
- **2030:** CoreWeave DDTL 3.0 (SOFR+400bp, amortizes from 2026), TeraWulf WULF Compute (7.750%) + Flash Compute
  (7.250%), Nebius 2030 conv (1.00%).
- **2031:** IREN Hardware 3 DDTL (term SOFR+225bp, 0.40% undrawn, amortizing), Applied Digital ComputeCo 2 (6.750% @98%),
  CoreWeave 2031 notes (9.75% — press), MARA zero-coupon.
- **2032:** CoreWeave DDTL 4.0 ($8.5B, press), CleanSpark (0.00%), IREN Dec-2025 conv, Nebius 2032 conv (2.75%).
- **2033 / 2042:** IREN May-2026 conv (1.00%); Hut 8 DC (6.192% — the lone 2042 outlier).

## Rate spread tells the credit story
- **Secured floating:** CoreWeave SOFR+**400**bp vs IREN SOFR+**225**bp — IREN's Microsoft-contract-backed, hedged paper
  prices ~175bp tighter (better counterparty + collateral).
- **Secured fixed:** TeraWulf 7.750%/7.250%, Applied Digital 6.750%, Hut 8 6.192% — high-yield/speculative coupons on
  GPU-collateralized SPV paper.
- **Parent convertibles:** 0.00%-2.75% — low cash coupon, cost deferred to dilution/refi (CleanSpark/MARA zero-coupon).

## Source tiers
`primary_EDGAR` rows carry exact accession + quote. Two CoreWeave rows (DDTL 4.0, 2031 notes) are `press_NOT_verified`
— pull the 8-K/424B to confirm before normalizing as primary (flagged, not fabricated).

## Verified vs proposed
- VERIFIED: coupon/spread/maturity/benchmark/undrawn-fee per `accession` + `source_quote` (primary EDGAR).
- PROPOSED: timing-wall-year ordering; CoreWeave DDTL 4.0 / 2031-notes are press-only pending their filings.
