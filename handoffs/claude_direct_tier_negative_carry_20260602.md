# Direct-tier DSCR reality (Codex run-ahead #2: unit-economics) — REVENUE ADDED, tiering corrected

**Base:** primary-verified coupons (my debt cards) + issuer revenue releases. READ-ONLY. **Deliverable:**
`handoffs/fixtures/direct_tier_negative_carry_20260602.csv`. **Impact: compute economics + size/timing + thesis.**
Completes the unit-economics card with the revenue side and **corrects an earlier over-simplification**: the cluster is
NOT uniformly negative-carry — it splits into three DSCR tiers.

## Three DSCR tiers (corrected)
**1. Cash-service-stressed (interest burden the current revenue cannot cover):**
- **TeraWulf** — $342M/yr carded interest vs **~$130M/yr revenue = 2.6×.** DSCR ≪ 1 before opex. Worst in cluster.
- **CoreWeave** — revenue is large (~$8.3B annualized, $2.078B/q, 2026 guide $12-13B) **but it lost ~$740M in the
  quarter** and total debt is ~$25B+ (carded interest $216M is only the DDTL 3.0 — real interest is multiples higher).
  Loss-making at scale → full debt service not covered by current cash generation.

**2. Unprofitable but interest-manageable-on-revenue:**
- **Applied Digital** — $145M carded interest vs ~$508M revenue (TTM $338M) ≈ 29%. Covers interest on revenue, but the
  company is unprofitable and has more debt pending (ComputeCo $2.35B).

**3. Low-cash-carry (cost deferred to equity dilution / refi wall, NOT current cash):**
- **IREN** — cash interest only **~$80M vs ~$961M revenue (8%)**; the convertibles are low-coupon so cash carry is
  manageable — IREN's risk is **dilution + the $1.5B DDTL + execution**, not cash debt service. (This corrects my prior
  note that implied IREN was cash-negative.)
- **CleanSpark** ($0 cash coupon), **Nebius** (~1-3%, principal accretes to 120-125%) — deferred to 2030-2033 refi/dilution.

## The thesis read (sharper than "all negative carry")
The cash-service danger is concentrated in the **high-coupon SECURED-note names** (TeraWulf, CoreWeave, Hut 8, Applied
Digital), because they pay 6.2-9% cash on debt collateralized by depreciating GPUs while revenue is still ramping.
**TeraWulf is the acute case** (interest 2.6× revenue). The **convertible names (IREN, CleanSpark, Nebius) are not cash-
stressed** — their risk transmits through dilution and refinancing walls instead. So the "negative-carry bubble" claim
is precise only for the secured-SPV tranche; the convertible tranche is a deferred/dilutive claim, not a cash crisis.

## DSCR computability
- **Computable now:** TeraWulf (DSCR≪1), CoreWeave (loss-making → <1 on full service), Applied Digital (interest-covered,
  EBITDA-negative), IREN (interest well-covered).
- **NEEDS revenue:** Hut 8, CleanSpark, Nebius (marked in fixture).
- Reminder: **CoreWeave's DDTL DSCR ≥1.40x covenant does not begin until April 2027** — the lenders themselves defer the
  coverage test past the ramp (primary 8-K, `claude_debt_service_card_coreweave`).

## Verified vs proposed
- VERIFIED: coupons (primary cards); revenues (issuer releases — CoreWeave $2.078B/q & -$740M Q loss; IREN $240.3M/q;
  Applied Digital TTM $338M; TeraWulf guide $30-35M/q).
- PROPOSED: the three-tier classification and the per-name DSCR reads; CoreWeave's carded interest understates its true
  burden (only DDTL 3.0 carded) — flagged. Hut 8/CleanSpark/Nebius revenue NEEDS.
