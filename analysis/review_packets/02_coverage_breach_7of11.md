# Review packet 02_coverage_breach_7of11

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
