# Review packet 03_gpu_duration_mismatch

> **⚓ Frame — read first (reanchor):** this repo is a **general forensic engine for financial fragility & mispricing across the _whole economy_** — hidden / mismatched / circular leverage and valuation-run-ahead-of-cash-flow, found with **no sector prior**. **AI / data-center is _case zero_, not the object** (the method is sector- and era-agnostic — cf. fiber 1999, shale 2014). **Operating mode: maximum exhaustiveness — broad AND deep, uncapped, ≥ $1M-substance floor, US-primary (international by connectedness-to-core × data-accessibility); acting resource-constrained is NEVER correct; the only stop is physics (data that doesn't publicly exist → estimate it from proxies).** Full scope & doctrine: [../total_ecosystem_dive.md](../total_ecosystem_dive.md) · [README](../../README.md).


**Claim.** Peak debt horizon (~48 months) outlives GPU economic life (~24 months), so secured lenders cannot be made whole on the collateral — the defining structural mismatch (1 of 2 cleanly-met fragility conditions).

**Evidence tier.** source_backed (depreciation schedules vs debt maturities)

**Where the figure comes from.** data/published/BURRY_REPORT_...json (fragility dimension asset_liability_duration_mismatch); GPU economics in src/bubble/analysis/gpu_economics.py

**Reproduce it.**
```bash
PYTHONPATH=src python -c "import json;r=json.load(open('data/published/BURRY_REPORT_EvidenceGated_20260603-2312.json'));print([d for d in r['debt_service_mismatch']['debt_service_wall_by_quarter']][:4])"
```

**Your job as reviewer.** Is ~2-3yr GPU economic life defensible for the specific chips in these fleets (vs a longer book life)? If economic life is 4yr, does the mismatch survive? See base_rates.md: the analogy break is that GPUs lack fiber's 20yr option.

**Verdict (reviewer fills in):** ☐ stands · ☐ stands with caveats · ☐ does not stand

Notes:
