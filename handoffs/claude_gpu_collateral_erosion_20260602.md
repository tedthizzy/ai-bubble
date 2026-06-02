# GPU collateral erosion: the secured-debt collateral depreciates faster than the debt (compute economics)

**Base:** GPU market + accounting data. READ-ONLY. **Deliverable:**
`handoffs/fixtures/gpu_collateral_erosion_20260602.csv`. **Impact: compute economics + downside-bearer (secured-note
recovery) + timing.** Connects the secured debt-service cards to the depreciating GPU collateral that backs them.

## The collateral-coverage gap (the forensic core)
The secured notes/DDTLs (TeraWulf $3.2B + $1.3B, CoreWeave DDTL, Hut 8 $3.25B, Applied Digital $2.15B) are
collateralized on GPUs + data-center assets. Two depreciation clocks diverge:
- **Accounting (slow):** hyperscalers stretched server useful life **3-4yr → 6yr** early-2020s; CoreWeave books **6yr**
  (Seeking Alpha alleges up to a **12-yr server** assumption). Straight-line over 6-12yr keeps **book carrying value
  high.**
- **Secondary market (fast):** **H100 SXM fell from ~$40K (late-2023) to $6-15K (2026)** — **60-85% in ~2-3 years**,
  accelerating after year 2; $25-30K → $15-20K for standard units.
**For SECURED DEBT, recovery = liquidation (market) value, not book carrying value.** So the collateral backing the
notes erodes far faster than the book shows — and the **2030-2033 maturity wall** (`claude_ai_direct_maturity_wall`)
lands when the 2025-26-vintage collateral is **4-6 years old and worth a fraction** of its financed value on the
secondary market. Noteholders' real coverage deteriorates across the loan life.

## Corroborating signal: the accounting optimism is already partially unwinding
**Amazon reverted server useful life 6yr → 5yr (eff. Jan-2025), cutting net income $298M/quarter ($677M/9mo)** — a
direct admission that the 6-year assumption was too optimistic. Under **ASC 360**, if useful lives prove over-stated,
issuers must book **impairments** — exactly the write-down the slow schedules have deferred. CoreWeave's 6-12yr
assumption is the most exposed to this.

## The bull counterpoint (kept, for balance)
Depreciation is a LIQUIDATION-value story; while **demand holds, utilization keeps the GPUs earning** regardless of
secondary price: CoreWeave's **A100s (2020) are fully booked**, and **expired-contract H100s were re-booked at 95% of
original price.** So collateral erosion only bites if (a) **demand softens** (utilization falls) OR (b) a **default
forces liquidation** into the depreciated secondary market. It is a conditional, demand-dependent risk — not a
certainty. This is the hinge between the bull and bear cases.

## Synthesis (ties to the cluster thesis)
The secured-SPV debt is a bet that **demand (and thus utilization) outlasts the GPUs' rapid secondary-market decay and
the 2030-2033 refinancing wall.** If demand holds, book values and coverage are fine; if demand softens, the gap between
book and liquidation value becomes a wave of ASC-360 impairments and impaired collateral recovery — concentrated exactly
when the wall hits. This is the compute-economics expression of the same demand-durability hinge as the contract lane.

## Verified vs proposed
- VERIFIED: the 6yr hyperscaler useful life + Amazon's 6→5yr reversion (−$677M/9mo); H100 secondary $40K→$6-15K;
  CoreWeave 6yr booking; A100 fully-booked / H100 re-booked-95% counterpoints (press/filings/market data).
- PROPOSED: the book-vs-liquidation collateral-coverage-gap framing and the impairment-wave-at-the-wall synthesis; the
  "12-yr CoreWeave server assumption" is an analyst allegation (flagged), and per-issuer collateral carrying values
  NEED the 10-K PP&E footnotes (flagged, not fabricated).
