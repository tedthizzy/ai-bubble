# Downside-bearer taxonomy (Codex backlog: full 9-role taxonomy) — who actually eats the loss

**Base:** synthesis of this session's primary-verified findings. READ-ONLY. **Deliverable:**
`handoffs/fixtures/downside_bearer_taxonomy_20260602.csv` (9 roles: bearer, who-bears, transmission, evidence example,
negative control). **Impact: downside-bearer dimension (core mission pillar).** Maps every channel through which an
AI-buildout loss reaches a bearer, grounded in the cards/structures verified this session.

## The 9 bearers and their transmission mechanisms
1. **Lender (secured)** — SPV noteholders / DDTL lenders; loss via **impaired collateral** (depreciating GPUs + customer-
   contract cash flows). Evidence: IREN Hardware 3 DDTL (secured on GPUs + Microsoft Contract cash flows), TeraWulf WULF
   Compute 7.750%, Hut 8 DC 6.192%. (`claude_debt_service_verified_collateral_recourse`)
2. **Shareholder** — equity dilution (convertible conversion) or restructuring wipeout. Evidence: CleanSpark/IREN/Nebius/
   MARA parent convertibles; all loss-making (CleanSpark −$378M/q). (`claude_direct_tier_negative_carry`)
3. **Sponsor/parent** — parent guarantee called. Evidence: CoreWeave **FULL** parent guarantee vs IREN **LIMITED** Parent
   Guarantee — the recourse strength determines whether SPV loss reaches the parent.
4. **Customer/offtaker** — take-or-pay obligation. Evidence: OpenAI $22.4B to CoreWeave (binding); Microsoft 71% of
   CoreWeave revenue. NEG: NVIDIA $100B / Oracle $300B are framework/LOI, NOT binding offtake.
   (`claude_economic_commitment_binding_split`)
5. **Ratepayer** — grid cost socialized via rate base / minimum bills. Evidence: Entergy 7 gas plants for Meta; residual
   after the exit-fee/asset-life gap. NEG: AEP Ohio 85% min-take + exit fee shifts cost to the DC. (`claude_ratepayer_docket_pack`)
6. **Utility opco** — stranded dedicated generation if DC load fails (Entergy 7×750MW for one Meta load).
7. **Vendor/supplier** — vendor financing / circular investment at risk. Evidence: NVIDIA $100B LOI (funds OpenAI to buy
   NVIDIA); AMD warrants. (`claude_circular_financing_map`)
8. **Landlord/REIT** — vacancy / tenant default. Evidence: Applied Digital (lessor, $5B IG-hyperscaler lease), Digital
   Realty, Equinix.
9. **Subsidy/taxpayer** — tax credits, public power upgrades, guarantees at risk.

## The synthesis (where the loss actually concentrates)
For the negative-carry AI-direct cluster, the **primary bearer is the secured lender** (SPV noteholders on depreciating-
GPU + single-customer-contract collateral), with the **sponsor/parent** as backstop only where guaranteed (CoreWeave
full; IREN limited), and the **customer/offtaker** as the upstream trigger (a counterparty failure — e.g. OpenAI —
breaks the contract cash flow that the secured debt depends on). For the **physical/grid** layer, the bearer splits
between **ratepayers** (rate-base socialization, where tariffs don't fully shift cost) and **utility opcos** (stranded
dedicated generation). The **vendor** channel (NVIDIA circular) is non-binding but recursive. Each negative control
prevents over-assigning a bearer where the structure insulates it (non-recourse SPV, IG offtaker, protected ratepayer).

## Verified vs proposed
- VERIFIED: each evidence example traces to a primary-sourced session handoff (recourse structures, ratepayer dockets,
  commitment binding split, contract durability).
- PROPOSED: the taxonomy organization and the "loss concentrates in secured lender + sponsor + offtaker-trigger"
  synthesis; the negative controls are the guardrails against over-assignment.
