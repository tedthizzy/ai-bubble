# Nebius + MARA debt-service cards (closes Codex Active Direction #6 card series)

**Base:** SEC + pricing releases. READ-ONLY. **Deliverable:** `handoffs/fixtures/debt_service_card_nebius_mara_20260602.csv`.
**Impact: evidence-gate confidence (AI-direct).** Final two names of the requested card series
(CoreWeave/IREN/TeraWulf/Applied Digital/CleanSpark/Hut 8 already delivered).

## Cards
- **Nebius — ~$3.75B real convertibles:** $2.75B (1.00% due 2030 / 2.75% due 2032, two $1.375B series) + $1.0B (2.00%
  due 2029 / 3.00% due 2031, accreting to 120%/125%). **Metric shows $5.89B / 3 pkts** — the $3.16B packet (exceeds the
  largest $2.75B series) and a $1.15B packet (bound to a Class A SHARE-offering quote, likely not debt) are
  **questionable → refs-check** (modest ~$2.1B potential over-count, smaller than the miner cluster).
- **MARA Holdings — ~$3.52B captured:** $850M 0.00% conv due 2031 (completed 2024-12-04, upsized from $700M) + a
  separate zero-coupon series due 2030 (`needs_extraction`). 3 MARA Holdings packets.

## ⚠️ Disambiguation (prevents a real error)
The metric also contains **Marathon Petroleum Corporation ($5.00B, "April 7, 2026, Marathon Petroleum Corporation")** —
an **oil refiner (MPC), a DIFFERENT company** from MARA Holdings (the bitcoin/AI miner). They share the "MARA" string
but are unrelated; the $5.0B is Marathon Petroleum's own (legitimate, non-AI) debt. Do not merge them.

## Verified vs proposed
- VERIFIED: Nebius and MARA Holdings offering sizes/coupons/maturities (issuer releases); the Marathon-Petroleum-≠-MARA
  distinction (live decisions CSV).
- PROPOSED: Nebius ~$3.75B real / ~$2.1B questionable (pending refs-check on the $3.16B and $1.15B packets); MARA's
  2030 series size pending extraction. Lower priority than the confirmed miner-cluster over-count.
