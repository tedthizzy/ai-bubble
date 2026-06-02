# AI-direct refinancing wall: 88% of carded debt matures 2030-2033 (TIMING dimension)

**Base:** maturities from my primary-verified debt-service cards. READ-ONLY. **Deliverable:**
`handoffs/fixtures/ai_direct_maturity_wall_20260602.csv`. **Impact: timing dimension + refinancing risk + thesis.**
Fills the least-covered mission pillar (timing) using data already carded — no new extraction.

## The wall
Of **$41.7B carded AI-direct cluster debt** (22 facilities across CoreWeave/IREN/TeraWulf/Applied Digital/CleanSpark/
Hut 8/Nebius/MARA), **$36.6B (88%) matures in a concentrated 2030-2033 window**:
| year | total | convertible | secured | cumulative |
|---|---|---|---|---|
| 2029 | $1.85B | $1.00B | $0.85B | $1.9B |
| **2030** | **$10.47B** | $3.38B | $7.10B | $12.3B |
| **2031** | **$10.10B** | $1.35B | $8.75B | $22.4B |
| **2032** | **$12.03B** | $3.52B | $8.50B | $34.5B |
| 2033 | $4.00B | $4.00B | $0.00B | $38.5B |
| 2042 | $3.25B | — | $3.25B | $41.7B (Hut 8, the only facility outside the wall) |

(Carded only — CoreWeave's full debt is ~$25B+, so the true cluster wall is materially larger; this is a floor.)

## Why the timing is the danger (the wall lands at peak uncertainty)
The 2030-2032 peak coincides with three independently adverse clocks:
1. **GPU collateral is depreciated/obsolete by then.** The secured notes/DDTLs ($7-9B/yr in 2030-2032) are
   collateralized on GPUs bought in 2025-2026; by 2030-2032 those are **4-6 years old, at/past typical useful life**
   (see `claude_gpu_depreciation_reality`). The collateral backing the refinancing has eroded exactly when refinancing
   is due.
2. **Anchor contracts are expiring/renewing.** CoreWeave's OpenAI commitment runs **through Oct-2030** — the contract
   cash flow that services the 2030-2032 maturities is itself up for renewal in the same window (and subject to the
   nonperformance carve-out, `claude_contract_durability_backing_debt`).
3. **Convertibles need in-the-money conversion or cash.** ~$11.6B of the wall is convertibles (IREN/CleanSpark/Nebius/
   MARA); if the volatile miner/neocloud equities are below conversion price in 2030-2033, they must be **cash-refinanced
   or repaid** — a hard call for cash-negative issuers (see `claude_direct_tier_negative_carry`).

## Synthesis (ties the session's lanes into the timing axis)
The cluster's risk is not just negative carry today — it is a **synchronized 2030-2032 refinancing wall** where
depreciated GPU collateral, expiring anchor contracts, and out-of-the-money convertibles could compound. A sector-wide
AI-demand or rate shock in that window hits all the secured-SPV issuers' refinancing simultaneously (correlated, not
diversified) — the contagion path. **Highest timing-impact extraction:** the exact maturity + refi terms of CoreWeave's
uncarded ~$15B+ (DDTL 4.0 amortization, the $2.25B 1.75% notes S&P rated) — that determines the true 2030-2032 peak.

## Verified vs proposed
- VERIFIED: the per-facility maturity years (primary cards); the $36.6B/88% 2030-2033 concentration (arithmetic).
- PROPOSED: the three-adverse-clocks reading and the correlated-refinancing-wall conclusion; the carded $41.7B is a
  floor (CoreWeave's full stack uncarded). The GPU-age and contract-expiry overlaps are cross-lane inferences, flagged.
