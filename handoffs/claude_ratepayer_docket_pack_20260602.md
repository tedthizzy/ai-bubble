# Ratepayer downside-bearer / large-load tariff docket pack (Codex run-ahead #5 + acquisition targets)

**Base:** utility regulatory filings + press. READ-ONLY. **Deliverable:**
`handoffs/fixtures/ratepayer_docket_pack_20260602.csv`. **Impact: downside-bearer (ratepayer) + acquisition scope.**
First substantive pass on the ratepayer dimension — who bears the AI-datacenter grid-buildout cost, and how the 2025
tariff response reallocates it. Source URLs + extraction expectations for the named utilities.

## The 2025 regulatory shift (verified terms)
The dominant 2025 response has been to **shift data-center grid cost off ratepayers via minimum-take + exit-fee
tariffs** — a regulatory take-or-pay that mirrors the compute-contract take-or-pay:
- **AEP Ohio (PUCO, approved 2025-07-09):** DCs >25MW new load must pay **min 85% of subscribed energy even if
  unused**; monthly minimum demand to 85% of contracted capacity; **min 8-yr contract after a 4-yr ramp**; **exit fee =
  3 years of minimum charges** (available only after year 5 post-ramp); increased collateral. Strongest ratepayer
  protection of the three.
- **Georgia Power (GA PSC Docket #44280, Docs #222325/#221165):** large-load **>100MW billed on project risk**; DC
  **pays T&D costs as construction progresses**; contracts extended **5→15 yr**; minimum billing — to stop DCs leaving
  before paying for the infrastructure built for them.
- **Entergy Louisiana / Meta (LPSC, 20-yr agreement):** **Meta fully covers** the cost of new dedicated assets (7×
  750MW gas + 2,500MW solar + storage); utility claims **$2B customer savings**; framed under the White House Ratepayer
  Protection Plans.

## Forensic durability questions (where ratepayers still bear residual risk)
The tariffs reduce ratepayer exposure ON PAPER, but the same durability failure modes as the compute contracts apply:
1. **Exit-fee adequacy vs stranded-asset life:** AEP's 3-years-of-minimum-charges exit fee may **under-cover an 8-15 yr
   asset** if the DC leaves — the residual stranded cost falls on ratepayers. The exit-fee/asset-life gap is the key
   extraction.
2. **Counterparty credit:** minimum-take and special contracts are **only as good as the data center's credit** — the
   same OpenAI/neocloud counterparty-concentration risk surfaces in the rate base (Entergy's 7 gas plants ride on Meta).
3. **Contested & uneven:** Ohio Manufacturers' Association is **challenging** the AEP tariff; SELC says Georgia approved
   **"without sufficient customer protections."** The protections are litigated and vary by state — so ratepayer
   exposure is jurisdiction-dependent, not uniformly closed.
4. **Stranded dedicated generation:** Entergy building **7 gas plants for ONE 7GW customer** — if AI demand falters, the
   stranded-asset question is whether Meta's special-contract obligation (and credit) actually covers decommissioning.

## Extraction expectations (acquisition targets — what to pull per docket)
For each proceeding: minimum-take %, ramp/contract length, **exit-fee formula vs asset depreciation life** (the gap =
ratepayer residual), collateral/security, special-contract counterparty + credit support, and the
contested/appeal status. Next utilities to add: **Xcel, FPL/NextEra, Dominion (PJM/Virginia data-center alley),
ERCOT large-load** — and PJM/MISO capacity-auction cost allocation (where DC load has spiked capacity prices borne by
all ratepayers).

## Verified vs proposed
- VERIFIED (primary regulatory/press): the AEP Ohio 85%/exit-fee/8-yr terms (PUCO 2025-07-09); Georgia Docket #44280
  >100MW/T&D/15-yr terms; Entergy/Meta 20-yr full-cost-coverage + 7 gas plants; the OMA and SELC challenges.
- PROPOSED: the exit-fee-vs-asset-life gap, the counterparty-credit and stranded-generation residual-risk reads, and the
  next-utility target list. Exact docket sub-numbers beyond Georgia #44280 and precise exit-fee/asset-life math NEED the
  primary tariff sheets (flagged, not fabricated).
