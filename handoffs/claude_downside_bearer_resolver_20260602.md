# Downside-bearer resolver pack (Codex Active #1) — bearer/obligor → legal entity + role + actual loss-bearer

**Base:** current main `2438027`, report `BURRY_REPORT_EvidenceGated_20260602-1806.json`. READ-ONLY; no prod writes.
**Codex import note:** imported on `c092b91` as a branch-safe resolver pack; use
as fixture evidence/design input before production resolver changes.
**Deliverable:** `handoffs/fixtures/downside_bearer_resolver_20260602.csv` (50 rows = top 25 `top_risk_bearers` +
top 25 `top_obligors`; each: surface, name, exposure, graph roles, resolved_role, resolution_action,
resolution_basis, **actual_downside_bearer**). Impact: **graph validity / contagion (downside-bearer correctness).**
Extends the landed AI-gated bearer surface (`56f5293`) + role-conflation cleanup; does not duplicate them.

## 11-role resolver taxonomy (all 50 classified; 0 unresolved)
| resolved_role | n | resolution_action | who actually bears the loss |
|---|---|---|---|
| offthesis_obligor | 15 | flag_non_ai | obligor equity/creditors — exclude from AI bearer ranking |
| regulated_utility | 11 | map downside to RATEPAYER | **ratepayer (rate-base recovery) + utility equity + stranded-asset risk** |
| lender_financier | 10 | keep_as_lender | the bank, on borrower default (syndicated share only) |
| project_finance_borrower | 3 | keep | project lenders + equity sponsors (non-recourse LNG SPVs) |
| reit_obligor | 3 | flag_non_ai_unless_DC | REIT equity + creditors (off-thesis unless a data-center REIT) |
| spv_sponsor_borrower | 2 | resolve to parent | sponsor parent + SPV lenders |
| placeholder_garble | 2 | drop/merge | none (parsing artifact) |
| intragroup_guarantor | 1 | relabel + collapse | parent (WML→Wynn Resorts, intra-group) |
| utility_holdco_alias | 1 | merge | NEE→NextEra (collapse alias) |
| loan_series_label | 1 | drop | none (FEC = Finnish Export Credit loan label, re-attribute to named lenders) |
| ai_infra_supplier_obligor | 1 | keep (AI-relevant) | supplier equity/creditors (Vertiv = DC power/cooling) |

## Key findings
1. **Only 1 of the top-50 bearers/obligors is genuinely AI-infra-relevant** (Vertiv, a data-center power/cooling
   supplier). The raw bearer/obligor ranking is otherwise dominated by non-AI names — confirming the headline
   ranking needs AI-gating (which you landed in `56f5293`) and that the genuine AI downside flows through OTHER
   channels (below), not these top-$ nodes.
2. **The real AI-data-center downside channel is the REGULATED UTILITY → RATEPAYER (11 of 50).** NextEra/NEE,
   Entergy (TX/LA/AR/MS/Corp), Georgia Power, Southern Co, Xcel carry AI/DC load growth; under rate-base recovery
   the cost (and stranded-asset risk if the DC demand doesn't materialize) is borne by **ratepayers + utility
   equity**, not by the AI companies. This is the most underweighted downside bearer in the report and is the
   natural follow-on to the demand-side PPA concentration you just landed (`18091af`/`2180c00`).
3. **Banks (10) are the credit-supply side**, not principal bearers — they bear loss only on borrower default,
   and only their syndicated share. KEEP as lenders; do not rank as the people "holding the bag."
4. **Graph artifacts to drop/relabel** (some already handled in my lane-#3 cleanup): FEC (loan-series label),
   the JPMorgan "acting in different capacities" placeholder, WML (intra-group, relabel to Wynn Macau Limited).

## Negative controls (do NOT over-correct)
- Real lender bearers (Citizens $42.25B, JPMorgan $21.42B, BofA, PNC, Goldman, Sumitomo, TD, UMB, BNP) are valid
  `lender_financier` — KEEP, do not drop.
- The `reit_obligor` rule must NOT sweep in **data-center REITs** (Equinix, Digital Realty) — those are AI-relevant;
  the rule is scoped to net-lease/retail REITs (Kimco, W.P. Carey, Realty Income).
- `trustee_or_agent` (Wilmington Trust / U.S. Bank as Trustee, etc.) must be EXCLUDED from bearer ranking (pass-through
  role) — none currently leak into the top-50 (your earlier intermediary-exclusion holds), so this is a guardrail not a fix.

## Verified vs proposed
- VERIFIED: every name + exposure_usd + graph roles is from the 1806 report `capital_exposure_graph`. The role
  classification is rule-based (rules in the fixture build) and auditable per row.
- PROPOSED: the resolution actions + the ratepayer-downside re-attribution + an AI-supplier flag. A downstream
  utility→ratepayer downside surface (rate-base $ tied to AI/DC load) is the recommended next production lane.
