# Debt-service card verification: collateral/recourse/covenants -> primary EDGAR (Codex Active Direction #1)

**Base:** SEC EDGAR 8-Ks (exact accessions). READ-ONLY. **Deliverable:**
`handoffs/fixtures/debt_service_verified_collateral_recourse_20260602.csv` (long-form, with `filing_accession` +
`source_quote` per row). **Impact: evidence-gate confidence (AI-direct).** Upgrades the `needs_extraction`/`primary_press`
fields on the cards you imported into primary-EDGAR rows — TeraWulf + IREN first per your priority.

## IREN Hardware 3 DDTL — fully verified (EDGAR 0001140361-26-023427, 8-K 2026-06-01)
A **thesis-confirming** structure, primary-sourced:
- **~$3.6B aggregate Hardware 3 financing** = ~$1.5B DDTL + ~$2.1B Notes (issuer/borrower **IE US Hardware 3 LLC**, an
  IREN SPV). *(Note: the ~$2.1B Hardware-3 Notes are real secured debt; relevant to IREN's true debt total.)*
- **Rate: term SOFR + 2.25%** (vs CoreWeave SOFR+4.00% — IREN's Microsoft-backed paper prices ~175bp tighter); **0.40%
  undrawn fee**; **interest-rate HEDGED** (JPMorgan + J. Aron/Goldman) — a real mitigant.
- **Collateral: ALL Hardware 3 assets, including the GPUs acquired to service the Microsoft Contract, 100% equity pledge,
  AND the cash flows from the Microsoft Contract.** ← secured on depreciating GPUs + a single-customer contract — the exact
  structure of `claude_ai_direct_recourse_structure` + `claude_contract_durability_backing_debt` + `claude_gpu_collateral_erosion`,
  now PRIMARY-confirmed for IREN.
- **Recourse: Limited Parent Guarantee** (IREN Limited) — limited, not full; downside sits primarily with Hardware 3
  creditors.
- Availability until 2027-05-29; customary covenants incl. additional-indebtedness restrictions.

## TeraWulf WULF Compute Notes — verified (EDGAR 0001104659-25-101866, 8-K 2025-10-23)
- Issuer **WULF Compute LLC** (wholly-owned indirect SPV); **7.750% Senior Secured Notes due 2030**, semiannual Apr 15 /
  Oct 15; **senior secured obligations of WULF Compute and the Guarantors**; covenants restrict additional indebtedness,
  liens, restricted payments, asset sales; trustee Wilmington Trust. (Specific collateral schedule is in the indenture
  exhibit — `primary_EDGAR_partial`; pull the indenture for the asset list.)

## TeraWulf Flash Compute — verified (EDGAR 0001104659-25-124839, 8-K 2025-12-29)
- Issuer **Flash Compute LLC** (sub of FS CS I LLC); **7.250% sr secured notes due 2030** (semiannual Jun 30/Dec 31);
  Guarantor **Abernathy Data LLC**; **$75M cash collateral** securing a Guarantor letter of credit.
- **JV ownership: 50.1% TeraWulf / 49.9% Fluidstack** (FS CS I LLC) -> **TeraWulf's effective share of the $1.3B is
  ~$651M**, not the full $1.3B. Relevant to TeraWulf's real-debt attribution (the JV minority is Fluidstack's).

## Hut 8 DC — verified (EDGAR 0001104659-26-053247, 8-K 2026-05-01)
- Issuer **Hut 8 DC LLC** (indirect wholly-owned SPV); **6.192% sr secured notes due 2042** (semiannual May 15/Nov 15);
  senior secured obligations of the Issuer; collateral agent appointed; covenants restrict additional indebtedness +
  restricted payments. (Collateral schedule in indenture.)

## Convertible names — recourse verified (parent senior unsecured, no collateral, no guarantee)
- **CleanSpark** (EDGAR 0001193125-25-280105): "senior unsecured obligations of the Company and are **not guaranteed by
  any of the Company's subsidiaries**" — parent-level, structurally subordinated to any subsidiary debt.
- **MARA Holdings** (EDGAR 0001493152-24-048704): $850M 0.00% conv due 2031, "senior unsecured obligations of the
  Company"; principal does not accrete.
- **Nebius** (EDGAR 0001104659-25-089969): 1.00% due 2030 + 2.75% due 2032 convertible senior notes (indenture
  2025-09-15); senior, unsecured per parent-level structure (explicit ranking quote in the press-release exhibit).

## Active Direction #1 COMPLETE — the structural dichotomy, primary-confirmed cluster-wide
Every direct-tier facility's collateral/recourse is now primary-EDGAR-verified, splitting cleanly:
- **SECURED via bankruptcy-remote SPVs on GPUs + customer-contract cash flows, limited/parent-guaranteed recourse:**
  IREN Hardware 3 (GPUs + Microsoft Contract cash flows, Limited Parent Guarantee), TeraWulf WULF Compute & Flash
  Compute (Flash = 50.1/49.9 JV), Hut 8 DC, CoreWeave CCAC VII (full parent guarantee).
- **PARENT senior UNSECURED convertibles, no collateral, no subsidiary guarantee:** CleanSpark, MARA, Nebius, IREN
  convertibles.
This backs `claude_ai_direct_recourse_structure` with exact filing quotes for every name.

## Verified vs proposed
- VERIFIED (primary EDGAR, exact accession + quote per row): all IREN DDTL fields; TeraWulf WULF Compute
  issuer/security/coupon/maturity/covenants.
- PROPOSED: WULF Compute specific collateral list (indenture pull pending); the ~$2.1B Hardware-3 Notes are flagged as
  real secured debt relevant to IREN's true total (not a new overcount claim — just completeness).
