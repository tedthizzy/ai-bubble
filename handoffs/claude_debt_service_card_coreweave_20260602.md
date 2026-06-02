# CoreWeave debt-service card — PRIMARY-source-verified (fills confidence-unlock #2, the round-trip hub)

**Base:** SEC EDGAR primary filing. READ-ONLY; no prod writes. **Deliverable:**
`handoffs/fixtures/debt_service_card_coreweave_20260602.csv` (per-field value + **source_tier** + exact filing). Impact:
**evidence-gate confidence (AI-direct core) + bubble thesis evidence.** First executed row of the debt-service
worklist — CoreWeave is the round-trip hub (Microsoft→OpenAI→CoreWeave→NVIDIA) and the single most thesis-relevant name.

## PRIMARY-verified terms (EDGAR accession 0001769628-25-000033, filed 2025-07-28) — DDTL 3.0 Facility
- **$2.6B** delayed draw term loan; borrower **CCAC VII** (an SPV), **unconditionally guaranteed by Parent (CoreWeave)**
  via Parent Guarantee and Pledge Agreement (2025-07-28). **Recourse = full parent guarantee.**
- **Maturity 2030-08-21**; draws available until 2026-07.
- **Rate: daily compounded SOFR + 4.00%** (0% floor) [or base + 3.00%]; **undrawn fee 0.50%/yr**.
- **Collateral: substantially all assets of CCAC VII + 100% equity pledge** — i.e. **GPU-server-backed** (purpose is
  GPU capex for a customer contract).
- **Covenants:** **DSCR ≥ 1.40x — but only beginning April 2027** (no debt-service-coverage test during the ramp);
  **Contract Realization Ratio ≥ 0.85x monthly** (actual billed/received ÷ projected contracted cash flows, trailing 3mo).

## Why these specific terms are thesis evidence (not just data)
1. **The covenant is customer-payment-contingent.** The Contract Realization Ratio fires if the customer pays <85% of
   projected contracted cash flows — so the loan's covenant compliance is directly tied to **take-or-pay durability**,
   the exact risk the engine flags as unknown. This is a filing-level confirmation that the debt is only as good as the
   customer contract behind it.
2. **DSCR test deferred to April 2027** → no coverage discipline during buildout; the structure presumes the contract
   ramps before any service-coverage test bites. A negative-carry signal.
3. **Floating SOFR+4.00% on GPU collateral whose rental rates are reportedly falling** → rising cost of debt against
   depreciating collateral (the negative-carry core). The collateral-coverage erosion is the GPU-depreciation lane
   (`claude_gpu_depreciation_reality`) meeting the debt-service lane.

## Press-reported, NOT primary-verified (flagged; do not persist as fact)
- **DDTL 4.0: $8.5B senior secured, due ~2032-03** (StockTitan/press).
- **$2.75B 9.75% senior unsecured notes due 2031-10** (press) — a near-double-digit unsecured coupon is a strong
  speculative-grade credit signal, but **pull the notes 8-K / 424B to confirm before citing.**
- $3.1B leveraged loan backing OpenAI/Cohere contracts (PitchBook).

## Template for the rest of the worklist
Same extraction pattern (curl EDGAR 8-K with a declared User-Agent → parse the "Interest Rate / Maturity / Covenants /
Guarantees and Security" section) applies to the other negative-carry names (IREN, TeraWulf, Applied Digital,
CleanSpark, Hut 8, Nebius) in `claude_direct_tier_debt_service_worklist`. Recommend running them next in that order.

## Verified vs proposed
- VERIFIED (primary): every DDTL 3.0 field above is quoted from EDGAR accession 0001769628-25-000033 (CIK 1769628).
- NOT VERIFIED (press): DDTL 4.0 size/maturity, the 9.75% 2031 notes, the $3.1B loan — flagged `press_NOT_verified`
  in the fixture; pull the respective 8-K/424B to confirm.
- PROPOSED: the thesis reading (customer-contingent covenant, deferred DSCR, negative carry) — supported by the
  verified terms but is interpretation, not filing language.
