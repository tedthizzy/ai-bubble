# Rate-coverage gap is over-stated — sibling-fill, don't mass-extract (corrects my #18 framing)

**Base:** current main `8bea1ea`, report `…-1816.json` (debt_service rate coverage 44.2%). READ-ONLY; no prod writes.
**Deliverable:** `handoffs/fixtures/rate_coverage_sibling_fill_20260602.csv` (6 direct-tier issuers: known coupons,
known/null row counts, disposition, residual extraction, notes). Impact: **timing dimension + avoided wasted work.**

## The finding (a self-correction of my #18 maturity/rate lane)
My #18 lane implied the AI pure-plays' rate gap ($45-63B per issuer) needs mass EDGAR extraction. **That over-states
the gap.** For most direct-tier issuers the coupon **is already extracted in a sibling filing** — the NULL-rate rows
are **cross-filing duplicates of the same instrument** counted across multiple 8-K / press-release / prospectus
filings:
| issuer | known coupon(s) | known rows | NULL rows | disposition |
|---|---|---|---|---|
| TeraWulf | **7.75%, 6.4%** | 4 | 9 | SIBLING-FILL (9 dups of the 7.75% notes due 2030 + 6.4%) |
| Hut 8 | **6.192%** | 3 | 4 | SIBLING-FILL (dups of the 6.192% notes due 2042) |
| CoreWeave | **2.25%, 9.0%** | 2 | 1 | SIBLING-FILL |
| Applied Digital | **9.25%** | 1 | 1 | SIBLING-FILL |
| IREN | none in debt_service (**1.00% convertibles known from my reselect lane**) | 0 | 1 | GENUINE EXTRACTION ($6B 424b5) |
| MARA | none | 0 | 1 | GENUINE EXTRACTION (convertible) |

## So the fix is dedup-then-measure, NOT a mass-extraction workflow
- **4 of 6 issuers need ZERO new EDGAR fetches** — propagate the known coupon to the same-instrument duplicate rows
  (the cross-filing dedup machinery already exists in production). TeraWulf alone has 9 NULL rows that are dups of
  its 2 known coupons.
- **Only 2 genuine extractions remain**: IREN's $6B 424b5 (`ny20064909x1_424b5`) and MARA's convertible (`ex99-1`).
  IREN's other big piece — the $3.0B 1.00% convertibles due 2033 — is already coupon-known from my reselect lane.
- **Therefore the 44.2% rate-coverage figure is pessimistic**: a large share of the "missing-rate notional" is
  duplicate rows whose coupon is recoverable by sibling-fill, not by acquisition. The true post-dedup coverage is
  materially higher.

## Why this matters (decision I made)
I scoped an EDGAR-extraction workflow to "close the timing gate," but the data showed it would mostly chase
cross-filing duplicates of already-coupon'd instruments — so I did NOT spend the EDGAR fetches. The cheap, correct
move is sibling-fill + the 2 residual extractions.

## Verified vs proposed
- VERIFIED: the known coupons per issuer (TeraWulf 7.75%/6.4%, Hut 8 6.192%, CoreWeave 2.25%/9.0%, Applied Digital
  9.25%) and the NULL/known row counts (from the 1816 report debt_service lists); IREN 1.00% (my reselect lane).
- PROPOSED: the sibling-fill disposition + the claim that post-dedup rate coverage >> 44.2%. The exact recomputed
  coverage needs the dedup applied (production); the 2 residual extractions (IREN $6B, MARA) are the only genuine gap.
