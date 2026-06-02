# Hidden-leverage taxonomy (#28) — the UNDER-count side (hidden-risks dimension)

**Base:** current main `6e4ca20`, survivor metric 1,380 / $3,742.4B. READ-ONLY; no prod writes.
**Deliverable:** `handoffs/fixtures/hidden_leverage_taxonomy_20260602.csv` (8 off-B/S structures: captured?, rows,
$, under-count risk, AI-relevance, where-to-look, metric-treatment rule). Impact: **hidden risks / final metric (under-count direction).**

## Why this lane (it inverts the whole session)
Every prior lane attacked **over-count** (the $3.742T is too high). This one asks the opposite: does the metric
**UNDER-count** by excluding off-balance-sheet structures? The answer is yes, structurally — the metric is a
**committed-DEBT** measure, and the dominant AI-data-center financial commitments are NOT debt:

## The key gap: take-or-pay = $0 captured
- **`take_or_pay` / minimum-revenue-commitment: 0 rows, $0 in the metric.** This is the **highest** under-count risk:
  hyperscaler DC-capacity take-or-pay, compute take-or-pay (the OpenAI/Oracle/CoreWeave-style multi-year compute
  commitments), and neocloud power take-or-pay are the **dominant AI-infra commitment form**, and **none** appear in
  SEC debt tables — they live in the 10-K "unconditional purchase obligations" / commitments footnote. A bull's
  strongest counter to "only $185B direct AI debt" is precisely these take-or-pay commitments, which dwarf the debt.
- **Operating leases / hosting / colocation: mostly excluded** (Alphabet's $80B+ leases are $0 in the metric by
  design). DC capacity is largely leased (Equinix/Digital Realty tenants), so the lease line is a large excluded obligation.

## The other structures (mostly partially captured)
| structure | in metric | $ captured | under-count risk |
|---|---|---|---|
| parent_guarantee | partial | $193.3B (63 rows) | MED (intra-group; double-count risk, not under-count) |
| prepay/capacity_payment | partial | $46.3B (17) | MED (off-B/S compute prepays missed) |
| vendor_financing | partial | $12.0B (6) | MED (**GPU vendor financing** — NVIDIA-style — partly off-B/S) |
| spv_securitization/ABS | partial | $5.2B (3) | MED (non-recourse SPV debt off parent B/S) |
| tax_equity | minimal | $1.0B (1) | LOW-MED (AI-power ITC tax-equity off-B/S) |
| sale_leaseback | minimal | $2.8B (1) | LOW-MED |

## The reconciling insight (balances the over-count work)
The metric corrections this session pushed the number DOWN (over-count removal) and re-scoped it (only $405.7B
AI-linked). This taxonomy shows the **opposite-direction caveat**: a true **economic-commitment** view of AI-infra —
debt **plus** take-or-pay + leases + hosting + GPU vendor financing — would be **materially larger** than the
$184.8B direct-tier debt. The two are not contradictory: the **committed-debt metric is correct as a debt metric**,
but it is **not** the total economic exposure. Both numbers should be reported: the debt figure ($184.8B direct /
$405.7B AI-linked) AND a separate **off-B/S fixed-obligation tier** (led by take-or-pay), clearly labeled.

## Proposed treatment (do NOT fold into the debt metric)
Add a separate **economic-commitment tier** (take-or-pay, operating-lease, hosting, GPU vendor-financing,
non-recourse SPV) with its own extraction from the commitments footnote — labeled distinctly so it never inflates
the committed-debt metric but is available for the "true AI-infra exposure" answer. Per-structure where-to-look +
metric-treatment rule in the fixture.

## Verified vs proposed
- VERIFIED: the in-metric capture counts/$ per structure (scanned across the 1,380 survivors' quotes/rationale);
  the take_or_pay = $0 result; the Alphabet-lease exclusion.
- PROPOSED: the economic-commitment tier + extraction targets. This is a **hidden-risks under-count guardrail** —
  no change to the committed-debt metric; it adds the missing exposure dimension.
