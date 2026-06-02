# Economic-commitment tier (off-B/S take-or-pay) — SOURCED via deep-research (quantifies the #28 gap)

**Base:** main `f0eff65`. Built from a deep-research pass (109 agents, 3-vote adversarial verification, primary-source
citations). READ-ONLY; no prod writes.
**Deliverable:** `handoffs/fixtures/economic_commitment_tier_20260602.csv` (8 commitments: parties, amount, structure,
binding tier, term, disclosure location, **source URL**, double-count caveat). Impact: **hidden risks / size
(under-count tier)**. This puts CITED numbers on the take-or-pay gap my hidden-leverage taxonomy (#28) flagged as $0
in the metric. Distinct from Codex's utility-ratepayer acquisition pack (`f0eff65`) — that's PUC dockets; this is
off-B/S compute commitments.

## The forensic split (this is the whole point)
The "AI is committing $hundreds-of-billions" headlines are mostly **non-binding frameworks or seller-side revenue
projections**. The only **binding** figures sourceable from primary filings are far smaller and live in MD&A
obligations / RPO footnotes, NOT debt tables:

**BINDING (footnoted), buyer-side:**
- **Microsoft $109.95B purchase commitments** — FY2025 10-K MD&A obligations table, "primarily relate to datacenters
  and include open purchase orders and take-or-pay contracts." ⚠ BLENDED (cancellable POs + take-or-pay; the
  strict take-or-pay subset is not separately quantified — do not attribute the full $109.95B to take-or-pay).
  [sec.gov msft-20250630]
- **Microsoft $92.7B datacenter leases not-yet-commenced** — ASC 842, off-B/S until commencement (FY2026-31). A
  distinct LEASE tier; keep separate from the purchase line. [same 10-K]

**BINDING take-or-pay, seller-side (the mirror — DO NOT sum with buyer-side):**
- **CoreWeave $60.7B RPO** (Dec 31 2025, +302% YoY) — explicitly "take-or-pay, payment regardless of utilization,"
  >98% of 2025 revenue, ~5-yr WAD. The cleanest large binding datapoint, but it is the SELLER's backlog (the mirror
  of its customers' purchase obligations, incl Microsoft + the ~$18.4B OpenAI commitment inside it). [crwv-20251231]
- **OpenAI→CoreWeave ~$18.4B** (~$11.9B thru Oct 2030 + ~$6.5B thru May 2031) — binding, but ALREADY inside CoreWeave's $60.7B RPO.

**EXCLUDED from any binding tally (flagged):**
- Nebius→Microsoft ~$17.4-19.4B (seller-side; buyer side likely folded into MSFT's $109.95B).
- Applied Digital ~$11B / Core Scientific ~$3.5B — **lessor "anticipated rental revenue," NOT take-or-pay**.
- Anthropic/Google/Broadcom ~3.5 GW TPU — **gigawatt-only, NO dollar figure** (press release).
- The splashiest "$300B"-type headlines did NOT surface as sourceable binding obligations in primary filings.

## What this means for the bubble-size answer
- The debt metric's $0 take-or-pay capture understates true AI-infra economic exposure — but the **honestly
  sourceable binding buyer-side number is ~$110-200B** (Microsoft datacenter purchase + leases), the same order of
  magnitude as the $184.8B direct-tier DEBT, **not** the trillions the headlines imply.
- **Structural mechanism (BIS, March 2026, cited):** hyperscalers route build-out through SPV/JV vehicles that raise
  the debt while the hyperscaler commits via long-term leases / capacity-offtake — which is exactly why an SEC-debt
  metric structurally misses this tier. [bis.org r_qt2603u]
- The bull case rests heavily on NON-binding/lessor-revenue framing; a rigorous engine reports the **binding tier
  (~$110-200B, cited) separately from the debt metric, and excludes the framework/LOI numbers.**

## Verified vs proposed
- VERIFIED (cited, 3-0 adversarial): every binding figure + its disclosure location + source URL (Microsoft 10-K,
  CoreWeave 10-K/10-Q/S-1, BIS). Reject-uncited honored: the "$300B" headlines are NOT in the tally.
- PROPOSED: fold this into the report as a separate **economic_commitment_tier** (never into the committed-debt
  metric), with the binding/non-binding flag per row. Extraction path: 10-K MD&A "purchase commitments" + ASC 606 RPO
  footnotes (a checker spec, parallel to Codex's ratepayer extraction schema).
