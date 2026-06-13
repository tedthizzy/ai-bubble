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

## 2026-06-13 · Cluster-wide sweep (12 issuers + 2 BDCs)

Ran `scripts/edgar_verify_cluster.py` — the latest 10-K/10-Q (or 20-F for the foreign filer) for every cluster issuer + the two listed BDCs, extracting concentration / RPO / take-or-pay / going-concern / debt / profitability at filing tier. Full extracted snippets: [cluster_filing_facts.json](cluster_filing_facts.json). Key findings:

**1. Going-concern: ZERO current auditor qualifications (a false alarm avoided).** The keyword sweep flagged six issuers (WULF, IREN, APLD, MARA, CORZ, BTBT), but reading each snippet, **five are hypothetical risk-factor boilerplate** ("*could* … impact our ability to continue as a going concern" — WULF re: SHA-256, IREN/APLD/BTBT generic, MARA re: a possible restatement) and the sixth (**CORZ**) is **historical** — its actual 2022 Chapter 11 (since emerged; now being acquired by CoreWeave). No affirmative going-concern *qualification* surfaced. (Airtight confirmation = reading each auditor's report paragraph; the risk-factor language alone does not establish distress, and treating it as such would be exactly the over-count error the engine rejects.)

**2. CoreWeave is the cluster's internal customer-hub — a filing-verified concentration cascade.** Multiple issuers' AI/data-center revenue concentrates *into CoreWeave* as the customer:
- **CORZ:** *"One customer, CoreWeave, currently accounts for 100% of our Colocation segment revenue"* (and CoreWeave is acquiring CORZ).
- **GLXY:** *"our AI/HPC data center business will initially be highly dependent on a single customer, CoreWeave."*
- **APLD:** *"material customer concentration"*; ~$11B of its ~$16B lease backlog is CoreWeave (per its disclosures).

And CoreWeave itself is **67% Microsoft** with **56% of its backlog OpenAI** (the capital-markets-funded demand leg). So the cluster's revenue funnels up into CoreWeave, and CoreWeave funnels into Microsoft + OpenAI. A CoreWeave stumble is therefore not only its own lenders' problem — it removes GLXY's, CORZ's, and much of APLD's revenue simultaneously. This is the contagion-hub finding, now at filing tier and on the *revenue* side, not just the debt side.

**3. Profitability: the cluster is overwhelmingly loss-making (filing-verified).** Net result, latest fiscal year: CRWV −$1,167M, APLD −$231M, HUT −$248M, CORZ −$347M (Q1-26), CIFR −$822M, BTBT −$85M, MARA loss, WULF loss, GLXY loss. The **only exceptions: CLSK net income +$364M** and **IREN FY net income +$86.9M** (both confirmed; both volatile — IREN swung to a −$248M quarter on impairments). Confirms the engine's "loss-making cluster" characterization directly.

**4. A structural debt-split the engine should weight.** Two financing styles:
- **Bitcoin-miner pivots** fund via *cheap convertibles* (equity optionality): MARA $1.0B **0%** conv '32; CLSK $1.15B **0%** conv '32; IREN 3.25–3.5% conv '29; GLXY 3.0% exch '26; CORZ 3.0% conv '29/'31.
- **Pure neoclouds / AI-DC** fund via *expensive secured / SPV* debt: CRWV 9.00–9.75% senior + DDTLs at SOFR+4.0–4.25% (total indebtedness **$21.6B at YE2025**, +$3.7B undrawn); **CIFR's "Black Pearl Compute LLC" SPV raised $2.0B of 6.125% senior secured notes due 2031** (the CoreWeave/Elk-Grove SPV pattern repeating); APLD's ComputeCo 6.75% '31.

The coverage stress (7/11 breaching) is concentrated in the *secured-debt* names; the 0%-convertible miners carry near-zero cash interest, so their fragility is dilution/refi-at-maturity, not current debt service. This sharpens the two-clock read: the secured neoclouds bleed on carry *now*; the convert-financed miners face a *2029–2032 maturity/conversion* event, not a near-term coverage breach.

**5. IREN backlog — a material press-vs-filing gap.** IREN's filing **RPO is $710.3M as of 2026-03-31** (10-Q), against the ~$3.1B "contracted ARR" and ~$13.1B "total contract value" press/company headlines used in the expectations inversion. GAAP RPO excludes not-yet-commenced and cancellable/optional portions — so IREN's *firm* contracted backlog is a fraction of the headline, which means its renewal-dependent share of EV is **understated** in the inversion. Flagged in `src/bubble/expectations/names.py`.

**6. BDC self-disclosure.** **BXSL's 10-K** explicitly names the risk: *"growing concern about the sustainability of the private credit industry, particularly due to its significant exposure to the expanding technology sector, which includes artificial intelligence infra[structure]."* **ARCC's 10-K** confirms the *"Retained Vantage Data Centers"* position — the one named DC exposure behind its weak S3′ "exposed" membership.

## Queue (remaining filing-tier deepening)

- Read each auditor's report paragraph to make the "zero going-concern qualifications" claim airtight.
- Per-facility debt waterfalls (caps/triggers/seniority) on the secured names (CRWV, CIFR/Black Pearl, APLD/ComputeCo) — the WS2.3 waterfall work.
- Confirm the 9.75% April-2026 CoreWeave note vs the 9.00% July-2025 note (de-conflate the S1 issuance card).
