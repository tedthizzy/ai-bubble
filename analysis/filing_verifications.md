# Filing verification log

Direct exhibit reads from SEC EDGAR (reachable from the local research environment; the CI runner IP is blocked — see [docs/edgar_access_remediation.md](../docs/edgar_access_remediation.md)). Each entry upgrades a claim from press tier to `filing_verified`, or records a correction where the filing overruled the press. Verbatim quotes; every entry carries CIK + accession so anyone can re-pull. No User-Agent spoofing; compliant UA, ≤ the SEC fair-access rate.

---

## 2026-06-13 · SpaceX 424B4 → SpaceX adjacency card

**Filing:** Space Exploration Technologies Corp, CIK 0001181412, **424B4** (definitive prospectus), filed 2026-06-12, accession 0001628280-26-042639. [Document](https://www.sec.gov/Archives/edgar/data/1181412/000162828026042639/spaceexplorationtechnologi.htm).

**Verified (verbatim):**
- Anthropic Cloud Services Agreements (May 2026), *"access to compute capacity across COLOSSUS and COLOSSUS II. Compute capacity provided includes approximately 325,000 NVIDIA GPUs… the customer has agreed to pay us $1.25 billion per month through May 2029, with capacity ramping in May and June 2026 at a reduced fee. **After the initial three-month period, the agreements may be terminated by either party upon 90 days' notice.**"*
- Cursor/Anysphere (April 2026) compute + option agreement; option to acquire at ~$60B implied; *"$1.5 billion termination fee… and an $8.5 billion deferred services"* obligation.
- COLOSSUS = Memphis; COLOSSUS II = Memphis + Southaven, MS; ~1.0 GW combined.

**Corrected (filing overruled press):**
- The press-reported **"Google $920M/month, ~110k GPU, ~$30B"** compute contract is **absent** from the definitive prospectus ("Google" → only Play Store / Grok-competitor / Google Fiber; "$920M" → a 2024 share buyback). EDGAR shows **no June-5 S-1 amendment** (5/20 S-1 → 6/01 → 6/03 → 6/12 424B4). The contract and the "Alphabet customer-as-shareholder" circularity built on it are **withdrawn**.
- Firm-minimum math revised: terminable after a 3-month initial period (not "after 2026-12-31") ⇒ firm ≈ ~$5–6B vs ~$45B gross (~87% haircut), vs the old press card's $18B/76%.

Card updated: [analysis/spacex_adjacency.md](spacex_adjacency.md) (correction log at top).

---

## 2026-06-13 · CoreWeave 10-K (FY2025) → core concentration + take-or-pay + debt stack

**Filing:** CoreWeave, Inc., CIK 0001769628, **10-K** for FY ending 2025-12-31, filed 2026-03-02, accession 0001769628-26-000104. [Document](https://www.sec.gov/Archives/edgar/data/1769628/000176962826000104/crwv-20251231.htm).

**Verified (verbatim):**
- **Customer concentration (the existential-concentration fragility condition):** *"We recognized an aggregate of approximately **67% of our revenue from our top customer, Microsoft**, for the year ended December 31, 2025. We recognized an aggregate of approximately 77% of our revenue from our top two customers…"* → confirms the engine's "CoreWeave ~67% Microsoft" at filing tier.
- **Take-or-pay structure:** *"We primarily finance our infrastructure development through **asset-level debt supported by take-or-pay customer contracts**…"*; *"customers… purchase a specified amount of capacity on a take-or-pay basis over the contract term."*
- **RPO / backlog:** *"As of December 31, 2025, we had **$60.7 billion of remaining performance obligations ('RPO')**, compared to $15.1 billion… as of December 31, 2024."* (The $99.4B used in the expectations inversion is the later Q1-2026 figure, from the 10-Q for the period ending 2026-03-31; both correct at their dates.)
- **Debt stack (filing tier):** 2030 Senior Notes (May 2025) **9.25%** $2,000M; 2031 Senior Notes (July 2025) **9.00%** $1,750M; 2031 Convertible Senior Notes (Dec 2025) 1.75% $2,588M; DDTL 2.1 (Sept 2025) SOFR+4.25% $3,000M; DDTL 3.0 (July 2025) SOFR+4.00% $2,600M.

**Flag raised:** the S1 signal's [issuance_cards.json](issuance_cards.json) carries a **"9.75% senior notes due 2031"** (April 2026). The FY2025 10-K shows a *9.00%* 2031 note (July 2025) and a *9.25%* 2030 note — so the 9.75% 2031 is a **separate, later April-2026 series**, not the same paper. To confirm against the Q1-2026 10-Q / an April-2026 8-K before the next S1 re-card, so the card doesn't conflate two 2031 series.

---

## Queue (next highest-value exhibit reads)

- CoreWeave Q1-2026 10-Q (acc 0001769628-26-000222) — confirm the $99.4B RPO and the 9.75% April-2026 issuance; OpenAI/Meta take-or-pay amounts.
- NBIS / IREN / APLD latest filings — upgrade the WS1.1 backlog/EV inputs from press to filing tier.
- BXSL / ARCC schedules of investments — size the AI/DC exposure behind the S3' set membership ([bdc_exposure_cards.md](bdc_exposure_cards.md)).
- The 11 cluster issuers' debt exhibits — the WS2.2/2.3 utilization + waterfall work, now unblocked locally.
