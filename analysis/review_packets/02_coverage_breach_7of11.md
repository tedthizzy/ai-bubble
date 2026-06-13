# Review packet 02_coverage_breach_7of11

> **⚓ Frame — read first (reanchor):** this repo is a **general forensic engine for financial fragility & mispricing across the _whole economy_** — hidden / mismatched / circular leverage and valuation-run-ahead-of-cash-flow, found with **no sector prior**. **AI / data-center is _case zero_, not the object** (the method is sector- and era-agnostic — cf. fiber 1999, shale 2014). **Operating mode: maximum exhaustiveness — broad AND deep, uncapped, ≥ $1M-substance floor, US-primary (international by connectedness-to-core × data-accessibility); acting resource-constrained is NEVER correct; the only stop is physics (data that doesn't publicly exist → estimate it from proxies).** Full scope & doctrine: [../total_ecosystem_dive.md](../total_ecosystem_dive.md) · [README](../../README.md).


**Claim.** 7 of 11 cluster issuers breach debt-service coverage at the zero-shock base; the aggregate 1.35x is a CoreWeave masking artifact (negative ex-CoreWeave).

**Evidence tier.** source_backed (issuer filings; interest from measured rates on 44% of notional)

**Where the figure comes from.** data/published/BURRY_REPORT_...json debt_service_mismatch (top_entity_debt_service_risks, measured_annual_interest_usd) + cluster_dscr

**Reproduce it.**
```bash
python -c "import json;d=json.load(open('data/published/BURRY_REPORT_EvidenceGated_20260603-2312.json'))['debt_service_mismatch'];print('measured annual interest $', round(d['measured_annual_interest_usd']/1e9,2),'B on', d['measured_rate_notional_coverage_pct'],'% of notional')"
```

**Your job as reviewer.** The interest is measured on ~44% of notional (rates missing on the rest). Does extrapolating the missing-rate notional change the 7/11 count? Is the ex-CoreWeave negative aggregate robust to the missing-rate names?

**Verdict (reviewer fills in):** ☐ stands · ☐ stands with caveats · ☐ does not stand

Notes:
