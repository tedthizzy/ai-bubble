# Compute-payback computability cards (Codex message #4 — DSCR computable yes/no per name)

**Deliverable:** `handoffs/fixtures/compute_payback_computability_20260602.csv` (8 companies). **Impact: compute
economics + evidence-gate.** Per Codex: the fixture states **whether DSCR/payback is computable** and which inputs are
present vs `NEEDS` — NOT the final conclusion.

## Computability verdicts
- **YES (enough to compute DSCR now):** **TeraWulf** ($342M interest > ~$130M revenue → DSCR<1) and **Hut 8** ($201M
  interest < ~$284M revenue but −$253M/q net → DSCR<1 on EBITDA). Both EBITDA-negative.
- **PARTIAL (have debt+interest+revenue; missing cash &/or exact capex):** CoreWeave, IREN, Applied Digital, Nebius,
  CleanSpark — DSCR computable on an interest-coverage basis but **cash + full capex commitments are `NEEDS`** for a true
  payback model.
- **NO (revenue/cash not yet extractable):** **MARA Holdings** — zero-coupon defers cash interest, but current
  revenue/cash/full-debt are `NEEDS`.

## Inputs present (verified this session) vs NEEDS
- PRESENT: total debt (debt cards), cash interest (coupons), annual revenue (issuer releases), customer concentration,
  maturity wall (`claude_ai_direct_maturity_wall`).
- NEEDS (the gating extractions): **cash balance** (every name), **full interest** for CoreWeave (only DDTL 3.0 carded;
  true burden ≫), **exact capex commitments**, going-concern/refi language per 10-K/10-Q.

## The cross-cutting computable fact (not the conclusion, but it IS computable)
For every name where revenue is known, the company is **EBITDA-negative / net-loss-making**, so **DSCR < 1 on a
debt-service-coverage basis today** — coverage depends on the FUTURE contracted-revenue ramp. The "NEEDS cash" gap is
what blocks a full *payback-period* model (vs the *coverage* ratio, which is already computable as <1).

## Verified vs proposed
- VERIFIED: debt/interest/revenue/concentration/maturity per the cited session handoffs + primary filings.
- PROPOSED: the can_compute verdicts; cash/capex/going-concern are `NEEDS` (flagged, not fabricated). Highest-value next
  pull: cash balances (one 10-Q line each) flips most PARTIAL → YES.
