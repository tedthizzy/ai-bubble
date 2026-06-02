# AI-direct downside-bearer structure: SPV-secured-on-GPUs vs parent-unsecured-convertibles

**Base:** synthesis of my primary-verified debt-service cards (CoreWeave/IREN/TeraWulf/Applied Digital/CleanSpark/Hut 8/
Nebius/MARA). READ-ONLY. **Deliverable:** `handoffs/fixtures/ai_direct_recourse_structure_20260602.csv`. **Impact:
downside-bearer dimension + contagion.** Turns the card series into a who-bears-the-loss map for the AI-direct core.

## The structural split (a clean, evidence-backed dichotomy)
The negative-carry AI-direct cluster finances itself two ways, with very different downside bearers:

**1. SECURED notes/loans issued through bankruptcy-remote SPVs, collateralized on GPUs + data-center assets + the
customer contract** — CoreWeave (CCAC VII), TeraWulf (WULF Compute LLC; Flash Compute LLC JV), Hut 8 (Hut 8 DC LLC),
Applied Digital (APLD ComputeCo / ComputeCo 2 LLC), IREN ($1.5B DDTL via "Hardware 3"). 
- **Downside bearer = the SPV noteholders**, whose collateral is **depreciating GPUs** (rental rates reportedly down
  50-70%, see `claude_gpu_depreciation_reality`) and **a single customer's contract cash flows** (whose durability is
  the take-or-pay question). Recourse to the parent is typically **limited** — EXCEPT CoreWeave, where the DDTL carries a
  **full parent guarantee** (so CoreWeave the parent IS on the hook).
- This is the structurally riskiest debt in the bubble: bankruptcy-remote, single-asset-class collateral that
  depreciates, single-counterparty cash flow.

**2. UNSECURED convertibles issued at the PARENT** — IREN, CleanSpark, Nebius, MARA Holdings (mostly low/zero-coupon).
- **Downside bearer = convertible holders, but the loss path is equity dilution** (the notes convert to shares), so it
  partially lands on **existing equity holders** rather than triggering default. Lower coupons (0.00%-3.50%) reflect the
  embedded equity option, not credit strength.

## Why this matters for the thesis
- The "AI debt" is not uniform: the **secured-SPV tranche is where a GPU-value or contract-cancellation shock converts
  directly into creditor losses** (and, for CoreWeave, parent insolvency). The **parent-convertible tranche transmits a
  shock into equity dilution / refinancing risk** instead.
- The SPV structure also means headline entity-level debt **understates the per-project concentration**: each SPV is
  exposed to ONE campus / ONE customer, so the contagion path is project-specific, not diversified across the parent.
- Recourse fields marked `needs_extraction` are the **highest-value remaining pulls** (the indentures' parent-guarantee
  / non-recourse language) — they determine whether a project failure stays in the SPV or reaches the parent.

## Note: buyer/seller mirror is NOT systemic
A scan for seller-side contracted-revenue rows misclassified as debt in the metric returned essentially only the
already-flagged TeraWulf $12.8B HPC lease (and likely IREN $12.77B). The debt metric is otherwise clean of provider-
revenue-as-debt — the mirror risk is contained to those ~2 high-value cases, not a broad population.

## Verified vs proposed
- VERIFIED: the issuer/SPV names and secured/unsecured status from my primary-source cards; CoreWeave's full parent
  guarantee (primary 8-K); the mirror-scan negative result (live decisions CSV).
- PROPOSED: the two-bucket downside-bearer reading and the per-project-concentration implication; the `needs_extraction`
  recourse fields are flagged, not asserted.
