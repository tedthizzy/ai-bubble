# IREN + TeraWulf debt-service cards — primary-verified (Codex Active Direction #5-6)

**Base:** SEC EDGAR + pricing releases. READ-ONLY. **Deliverables:**
`handoffs/fixtures/debt_service_card_iren_20260602.csv`, `…_terawulf_20260602.csv` — long-form
`entity,facility,field,value,source_tier,source,filing_accession` shape for `normalize_debt_service_card_rows`
(matches the CoreWeave card). **Impact: evidence-gate confidence (AI-direct core).** Continues the card series; same two
names are the over-count subjects, so these cards double as the real-instrument inventory behind that finding.

## IREN — ~$9.0B real debt across 5 facilities
- May 2026 conv notes due 2033: **$3.0B** ($2.6B + $400M greenshoe), **1.00%**, net $2.96B, 32.5% premium, senior unsecured.
- Dec 2025 conv notes: **$2.0B** (0.25% 2032 / 1.00% 2033), conv price ~$51.40. (EDGAR 000114036125044095)
- Oct 2025 conv notes: **$1.0B** (indenture 2025-10-14).
- June 2025 conv notes due 2029: **$0.5B**, **3.50%**, conv price ~$13.64.
- May 2026 DDTL (Hardware 3 Credit Agreement): **$1.5B** delayed draw term loan — coupon/collateral/covenants
  `needs_extraction` (pull the credit agreement).

## TeraWulf — ~$5.35B real debt
- WULF Compute LLC sr secured notes due 2030: **$3.2B**, **7.750%**, Lake Mariner expansion (EDGAR tm2528904).
- Flash Compute LLC (JV w/ Fluidstack) sr secured notes due 2030: **$1.3B**, **7.250%**, Abernathy TX; recourse partial
  (JV/project-financed) (EDGAR tm2534384).
- Private offering: **$0.85B**.
- **HPC Lease $12.8B = NOT debt** — seller-side contracted revenue (TeraWulf as lessor); `reclassify` out of the debt
  metric (see `claude_terawulf_overcount_verification`).

## Honesty notes
- `source_tier` per row: `primary_EDGAR` (filing-verified), `primary_press` (issuer pricing release, not yet tied to the
  filing), `needs_extraction` (field not yet pulled — NOT fabricated), `reclassify` (mis-categorized), `derived` (my sum).
- Press-only rows are **not** promoted to primary. The coupon/maturity I list from pricing releases are issuer-published
  but should be tied to the indenture before being treated as filing-verified.
- Highest-value remaining extraction: the **IREN $1.5B DDTL covenants** and the **TeraWulf notes collateral/recourse** —
  these drive the downside-bearer/DSCR picture. Flagged `needs_extraction`.

## Verified vs proposed
- VERIFIED: facility sizes/coupons/maturities as labeled by `source_tier`; the $12.8B TeraWulf row is self-labeled lease
  contractual value.
- PROPOSED: the ~$9.0B / ~$5.35B real-debt totals (sum of distinct facilities) and the HPC-lease reclassification.
