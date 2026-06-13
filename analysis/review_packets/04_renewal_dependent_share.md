# Review packet 04_renewal_dependent_share

> **⚓ Frame — read first (reanchor):** this repo is a **general forensic engine for financial fragility & mispricing across the _whole economy_** — hidden / mismatched / circular leverage and valuation-run-ahead-of-cash-flow, found with **no sector prior**. **AI / data-center is _case zero_, not the object** (the method is sector- and era-agnostic — cf. fiber 1999, shale 2014). **Operating mode: maximum exhaustiveness — broad AND deep, uncapped, ≥ $1M-substance floor, US-primary (international by connectedness-to-core × data-accessibility); acting resource-constrained is NEVER correct; the only stop is physics (data that doesn't publicly exist → estimate it from proxies).** Full scope & doctrine: [../total_ecosystem_dive.md](../total_ecosystem_dive.md) · [README](../../README.md).


**Claim.** Across the four inverted neoclouds, 78–96% of enterprise value (median) rests on RE-CONTRACTING assets after the signed backlog runs off — priced against ~2–3yr GPU economic life.

**Evidence tier.** market/press inputs + stylized inversion (assumptions carded)

**Where the figure comes from.** analysis/expectations_inversion.md; src/bubble/expectations/ (inversion.py math, names.py carded inputs)

**Reproduce it.**
```bash
python scripts/build_expectations_inversion.py && python -c "import json;[print(r['ticker'], r['renewal_dependent_share']) for r in json.load(open('viz/expectations.json'))['results']]"
```

**Your job as reviewer.** Attack the stylization: even revenue recognition over tenor, sunk capex in EV, double-count of current revenue and near-term backlog. Re-run with your own discount-rate / margin / tenor grid (inputs are in names.py) — does the renewal dependence stay high for the GPU clouds?

**Verdict (reviewer fills in):** ☐ stands · ☐ stands with caveats · ☐ does not stand

Notes:
