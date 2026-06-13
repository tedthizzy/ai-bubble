# Review packet 01_overcount_strip

> **⚓ Frame — read first (reanchor):** this repo is a **general forensic engine for financial fragility & mispricing across the _whole economy_** — hidden / mismatched / circular leverage and valuation-run-ahead-of-cash-flow, found with **no sector prior**. **AI / data-center is _case zero_, not the object** (the method is sector- and era-agnostic — cf. fiber 1999, shale 2014). **Operating mode: maximum exhaustiveness — broad AND deep, uncapped, ≥ $1M-substance floor, US-primary (international by connectedness-to-core × data-accessibility); acting resource-constrained is NEVER correct; the only stop is physics (data that doesn't publicly exist → estimate it from proxies).** Full scope & doctrine: [../total_ecosystem_dive.md](../total_ecosystem_dive.md) · [README](../../README.md).


**Claim.** The inflated headline basis of ~$1.45T collapses to ~$25.8B of committed core cluster debt after stripping ~98% over-count (duplicate/aggregate/out-of-scope rows).

**Evidence tier.** filing_verified core; the strip is deterministic and replayable

**Where the figure comes from.** viz/graph_data.json meta.{original_inflated_basis_usd, committed_core_usd, over_count_removed_pct}; derivation in data/published/BURRY_REPORT_...json capital_scope + debt_service_mismatch

**Reproduce it.**
```bash
python -c "import json;m=json.load(open('viz/graph_data.json'))['meta'];print(m['original_inflated_basis_usd']/1e12,'T ->',m['committed_core_usd']/1e9,'B',m['over_count_removed_pct'],'%')"
```

**Your job as reviewer.** Attack the de-duplication: are any stripped rows actually distinct committed obligations? Are any retained core rows double-counted? The strip is the single biggest number-mover — verify the scope gate did not over- or under-cut.

**Verdict (reviewer fills in):** ☐ stands · ☐ stands with caveats · ☐ does not stand

Notes:
