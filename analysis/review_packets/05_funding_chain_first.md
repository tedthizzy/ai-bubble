# Review packet 05_funding_chain_first

> **⚓ Frame — read first (reanchor):** this repo is a **general forensic engine for financial fragility & mispricing across the _whole economy_** — hidden / mismatched / circular leverage and valuation-run-ahead-of-cash-flow, found with **no sector prior**. **AI / data-center is _case zero_, not the object** (the method is sector- and era-agnostic — cf. fiber 1999, shale 2014). **Operating mode: maximum exhaustiveness — broad AND deep, uncapped, ≥ $1M-substance floor, US-primary (international by connectedness-to-core × data-accessibility); acting resource-constrained is NEVER correct; the only stop is physics (data that doesn't publicly exist → estimate it from proxies).** Full scope & doctrine: [../total_ecosystem_dive.md](../total_ecosystem_dive.md) · [README](../../README.md).


**Claim.** The first transmission channel is the semi-liquid-fund redemption gate, and it is already binding in 2026 (Apollo ~45% fill, Ares 43.1%, Blue Owl OTIC 40.7% requested, BCRED's first gate) — corroborating the funding-chain-first read.

**Evidence tier.** press_reported (named vehicle gate events, multi-source verified)

**Where the figure comes from.** analysis/marginal_buyer_constraints.{md,json} (4_semiliquid_gates.gates_actually_hit_2026)

**Reproduce it.**
```bash
python -c "import json;print(json.load(open('analysis/marginal_buyer_constraints.json'))['constraints']['4_semiliquid_gates']['gates_actually_hit_2026'])"
```

**Your job as reviewer.** Are these gates AI-credit-specific or broad private-credit risk-off? The fill-% inferences (BCRED Q2, Blue Owl per-fund) are arithmetic, not printed — verify against the primary filings. Does the manager-coupling claim (~12:1) hold?

**Verdict (reviewer fills in):** ☐ stands · ☐ stands with caveats · ☐ does not stand

Notes:
