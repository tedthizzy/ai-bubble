# Utility → ratepayer downside pack (backlog #31) — the most underweighted AI-DC loss-bearer

**Base:** current main `2438027`, report `BURRY_REPORT_EvidenceGated_20260602-1806.json`. READ-ONLY; no prod writes.
**Codex import note:** imported on `c092b91` as a ratepayer-downside research
pack; production use still requires PUC/IRP/rate-base source extraction.
**Deliverable:** `handoffs/fixtures/utility_ratepayer_downside_20260602.csv` (4 utility families; per-node exposure,
consolidation status, AI/DC-load evidence, rate-base mechanism, stranded-asset risk, **actual downside bearer**,
acquisition target). Impact: **contagion / downside-bearer (a channel the report answer currently misses).**
Follows directly from the resolver-pack finding that 11 of the top-50 obligors are regulated utilities.

## Thesis
The AI/data-center buildout's power demand drives regulated utilities to add generation + transmission. Under
**rate-base recovery**, that capex (and the **stranded-asset risk** if hyperscaler DC demand doesn't materialize or
is cancelled) is borne by **RATEPAYERS + utility equity — not by the AI companies.** This is the report's most
underweighted downside bearer: the headline bearer/obligor ranking shows the utilities as borrowers, but does not
attribute the ultimate loss to ratepayers. It is the natural complement to the demand-side PPA offtaker
concentration you already landed (`18091af`/`2180c00`): the hyperscalers concentrate the *demand*; the *ratepayers*
in NEE/Entergy/Georgia-Power/Xcel territories concentrate the *downside*.

## 4 utility families (AI/DC-load evidenced)
- **Entergy** (TX/LA/AR/MS opcos + Corp): MISO ERAS gen-support for DC load (Entergy MS CC 820MW; Franklin
  Farms/Richland — real ERAS queue evidence from my physical lane). New CCGT built for DC → LA/MS/TX/AR ratepayers.
- **NextEra** (NEE/NEE Capital/FPL/NEER): the Amazon/Google/Microsoft Energy PPA hubs draw on NEER generators;
  FPL rate-base + merchant-PPA cancellation risk. → FL ratepayers + PPA counterparty exposure.
- **Southern / Georgia Power**: GA = top-5 DC state (25,124 MW tracker); new generation incl. the **$22.41B DOE
  Title XVII FFB loan** (my reselect lane) explicitly for load growth → Georgia ratepayers + DOE/FFB.
- **Xcel** (MN/CO): large-load DC interconnection requests → MN/CO ratepayers.

## CRITICAL caveat — entity-family fanout (do NOT sum)
The raw top-obligors list shows **$254.5B across 10 utility nodes**, but that is **inflated by family/parent-sub/
name-variant fanout** and must NOT be summed:
- Entergy = 5 nodes (Corp consolidates the 4 opcos) — summing = $142.3B double-count.
- NextEra = 3 nodes (NEE = NEE Capital = NextEra alias). Southern/Georgia Power = parent/sub (same $22.97B twice).
- Xcel = 2 nodes (name-variant dup of the same $19.5B).
The fixture lists per-node exposures with a `consolidation_status` flag; the family-true exposure needs a
consolidation pass (ties to backlog #20 entity-family/SPV). Also: the Entergy MS $28B node is partly a
historical-balance-sheet over-count (flagged in my reselect lane), and graph notional ≠ committed debt.

## Verified vs proposed
- VERIFIED: the per-node obligor exposures (from 1806 report `top_obligors`); the DC-load grid evidence (my
  physical lane ERAS rows); the $22.41B DOE loan (my reselect lane, verbatim).
- PROPOSED: the ratepayer-downside attribution + rate-base recovery mechanism + stranded-asset risk rating. The
  per-utility **rate-base $ tied specifically to AI/DC load** requires PUC-docket / IRP extraction (acquisition
  targets named per row) — that is the next production lane, not asserted here.
