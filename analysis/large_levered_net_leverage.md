# Large-levered layer — XBRL net-debt / coverage (real distress vs refi risk)

> **⚓ Frame — read first (reanchor):** this repo is a **general forensic engine for financial fragility & mispricing across the _whole economy_** — hidden / mismatched / circular leverage and valuation-run-ahead-of-cash-flow, found with **no sector prior**. **AI / data-center is _case zero_, not the object** (the method is sector- and era-agnostic — cf. fiber 1999, shale 2014). **Operating mode: maximum exhaustiveness — broad AND deep, uncapped, ≥ $1M-substance floor, US-primary (international by connectedness-to-core × data-accessibility); acting resource-constrained is NEVER correct; the only stop is physics (data that doesn't publicly exist → estimate it from proxies).** Full scope & doctrine: [total_ecosystem_dive.md](total_ecosystem_dive.md) · [README](../README.md).

Converts the scan's GROSS-notional flags into true leverage + coverage for the large-levered layer (scan gross debt ≥ $5B), so 'lots of debt' is separated from 'can't service it'. 92 names, XBRL from data.sec.gov. Distribution: {'distressed': 4, 'refi_risk': 15, 'manageable': 17, 'scan_oversized': 47, 'unknown': 8, 'no_xbrl': 1}. Machine-readable: [large_levered_net_leverage.json](large_levered_net_leverage.json).

| entity | sector | scan gross $B | XBRL net debt $B | ND/EBITDA | int cov | call |
|---|---|---:|---:|---:|---:|---|
| ARBOR REALTY TRUST INC |  | 7.9 | 11.0 | 60.3 | 0.2 | distressed |
| BLACKSTONE MORTGAGE TRUST, INC |  | 5.8 | 15.7 | 10.1 | 1.13 | distressed |
| Liberty Global Ltd. |  | 16.6 | 5.9 | 5.8 | 1.12 | distressed |
| MFA FINANCIAL, INC. |  | 54.1 | None | None | 1.42 | distressed |
| SIMON PROPERTY GROUP INC. |  | 20.0 | 27.7 | 12.0 | 2.38 | refi_risk |
| BAXTER INTERNATIONAL INC |  | 6.4 | 7.5 | 11.1 | 2.32 | refi_risk |
| FIRSTENERGY CORP. |  | 15.9 | 26.3 | 7.5 | 3.13 | refi_risk |
| Blackstone Real Estate Income  |  | 74.0 | 53.1 | 7.3 | 2.17 | refi_risk |
| WELLTOWER INC. |  | 31.5 | 13.2 | 7.2 | 3.04 | refi_risk |
| American Airlines Group Inc. |  | 11.8 | 26.1 | 7.1 | 1.71 | refi_risk |
| ESSEX PROPERTY TRUST, INC. |  | 6.7 | 6.8 | 6.6 | 4.83 | refi_risk |
| Bausch Health Companies Inc. |  | 32.3 | 19.5 | 6.4 | 1.88 | refi_risk |
| HEALTHPEAK PROPERTIES, INC. |  | 17.6 | 9.3 | 6.4 | 4.73 | refi_risk |
| LAS VEGAS SANDS CORP |  | 16.5 | 12.4 | 5.7 | 2.91 | refi_risk |
| CENTERPOINT ENERGY, INC. |  | 53.9 | 19.9 | 5.5 | 6.89 | refi_risk |
| KKR & Co. Inc. |  | 21.9 | 31.6 | 5.3 | 2.14 | refi_risk |
| Brixmor Property Group Inc. |  | 11.3 | 5.2 | 5.2 | 5.2 | refi_risk |
| NISOURCE INC. |  | 17.3 | 15.4 | 5.1 | 6.13 | refi_risk |
| Evergy, Inc. |  | 11.9 | 13.5 | 5.0 | 4.37 | refi_risk |
| LITHIA MOTORS INC |  | 6.0 | 9.5 | 5.0 | 6.96 | manageable |
| American Water Works Company,  |  | 21.3 | 12.6 | 4.6 | 9.31 | manageable |
| Energy Transfer LP |  | 47.2 | 68.1 | 4.6 | 4.23 | manageable |
| Cheniere Energy Partners, L.P. |  | 10.6 | 17.8 | 4.1 | 5.34 | manageable |
| Targa Resources Corp. |  | 28.0 | 18.3 | 3.8 | 36.14 | manageable |
| CORPAY, INC. |  | 20.7 | 7.8 | 3.3 | 183.41 | manageable |
| Salesforce, Inc. |  | 15.0 | 30.3 | 3.2 | 61.89 | manageable |
| Waste Connections, Inc. |  | 11.1 | 9.0 | 3.1 | 10.71 | manageable |
| AT&T INC. |  | 111.6 | 121.5 | 2.7 | 6.72 | manageable |
| PepsiCo, Inc. |  | 51.2 | 32.1 | 2.1 | 13.34 | manageable |
| FIFTH THIRD BANCORP |  | 22.0 | 14.7 | 1.9 | 1.96 | manageable |
| HONEYWELL INTERNATIONAL INC |  | 30.2 | 16.7 | 1.8 | 7.08 | manageable |
| Merck & Co., Inc. |  | 8.0 | 43.8 | 1.7 | 22.56 | manageable |
| Meta Platforms, Inc. |  | 29.0 | 35.3 | 0.3 | 228.46 | manageable |
| Ameris Bancorp |  | 126.1 | None | None | 2.26 | manageable |
| BYLINE BANCORP, INC. |  | 24.2 | None | None | 2.19 | manageable |
| ENTERPRISE FINANCIAL SERVICES  |  | 23.3 | None | None | 2.03 | manageable |
| Kennedy-Wilson Holdings, Inc. |  | 16.5 | 4.2 | 32.8 | 0.5 | scan_oversized |
| COPT DEFENSE PROPERTIES |  | 11.1 | 2.5 | 13.4 | 2.65 | scan_oversized |
| AMC ENTERTAINMENT HOLDINGS, IN |  | 14.0 | 3.7 | 12.4 | 0.67 | scan_oversized |
| Clear Channel Outdoor Holdings |  | 29.1 | 5.0 | 10.2 | 1.23 | scan_oversized |
| Urban Edge Properties |  | 10.1 | 1.6 | 10.0 | 2.24 | scan_oversized |
| STARWOOD PROPERTY TRUST, INC. |  | 11.3 | 2.0 | 9.1 | 0.16 | scan_oversized |
| Sunoco LP |  | 54.3 | 13.0 | 8.0 | 3.0 | scan_oversized |
| Fidelity National Information  |  | 55.2 | 16.0 | 6.6 | 3.38 | scan_oversized |
| BREAD FINANCIAL HOLDINGS, INC. |  | 77.1 | 2.1 | 6.1 | 0.39 | scan_oversized |
| NRG ENERGY, INC. |  | 86.5 | 19.6 | 6.0 | 4.87 | scan_oversized |
| Lumen Technologies, Inc. |  | 91.2 | 11.3 | 5.8 | 1.51 | scan_oversized |
| OMNICOM GROUP INC. |  | 27.5 | 4.0 | 5.5 | 2.74 | scan_oversized |
| Vistra Corp. |  | 59.2 | 16.6 | 4.3 | 5.26 | scan_oversized |
| McGraw Hill, Inc. |  | 14.1 | 2.3 | 3.6 | None | scan_oversized |
| ITT INC. |  | 22.7 | 2.8 | 3.4 | 206.93 | scan_oversized |
| ROYAL CARIBBEAN CRUISES LTD. |  | 69.0 | 20.6 | 3.1 | 4.73 | scan_oversized |
| ADAMAS TRUST, INC. |  | 6.2 | 0.5 | 2.9 | 0.84 | scan_oversized |
| CHS Inc. |  | 7.2 | 1.7 | 2.3 | 5.08 | scan_oversized |
| TXNM ENERGY INC |  | 9.3 | 2.0 | 2.1 | 4.86 | scan_oversized |
| MGM RESORTS INTERNATIONAL |  | 99.2 | 4.1 | 2.0 | 4.39 | scan_oversized |
| EURONET WORLDWIDE, INC. |  | 21.7 | 1.3 | 2.0 | 12.02 | scan_oversized |
| Victory Capital Holdings, Inc. |  | 6.3 | 0.9 | 1.6 | 8.62 | scan_oversized |
| ENTERPRISE PRODUCTS PARTNERS L |  | 86.5 | 13.8 | 1.5 | 7.36 | scan_oversized |
| UNITED RENTALS, INC. |  | 10.0 | 2.9 | 1.3 | None | scan_oversized |
| ConnectOne Bancorp, Inc. |  | 10.0 | 0.2 | 1.1 | 1.72 | scan_oversized |
| Keurig Dr Pepper Inc. |  | 43.7 | 2.4 | 0.6 | 7.41 | scan_oversized |
| JABIL INC |  | 6.9 | 0.7 | 0.4 | 12.29 | scan_oversized |
| Apollo Global Management, Inc. |  | 17.2 | 2.1 | 0.3 | 11.03 | scan_oversized |
| T-Mobile US, Inc. |  | 48.9 | 7.4 | 0.2 | 38.07 | scan_oversized |
| PennyMac Mortgage Investment T |  | 53.2 | 1.5 | None | None | scan_oversized |
| Hut 8 Corp. |  | 26.0 | 0.1 | None | -18.81 | scan_oversized |
| Goldman Sachs BDC, Inc. |  | 22.6 | 1.9 | None | None | scan_oversized |
| Bain Capital Specialty Finance |  | 11.3 | 1.4 | None | None | scan_oversized |
| Zscaler, Inc. |  | 8.3 | 0.2 | None | None | scan_oversized |
| BROWN & BROWN, INC. |  | 32.2 | 6.8 | None | None | scan_oversized |
| WOLFSPEED, INC. |  | 8.9 | 1.0 | None | -25.28 | scan_oversized |
| Pinnacle Financial Partners, I |  | 8.8 | -3.5 | None | None | scan_oversized |
| INTUIT INC. |  | 9.5 | 1.5 | None | None | scan_oversized |
| Morgan Stanley Direct Lending  |  | 6.2 | 2.0 | None | None | scan_oversized |
| Univest Financial Corporation |  | 6.8 | -0.0 | None | None | scan_oversized |
| Athene Holding Ltd. |  | 11.8 | -7.4 | None | None | scan_oversized |
| MERCER INTERNATIONAL INC. |  | 8.9 | 1.5 | None | -4.62 | scan_oversized |
| Alphabet Inc. |  | 54.5 | -27.2 | None | None | scan_oversized |
| Versant Media Group, Inc. |  | 8.0 | 1.8 | None | None | scan_oversized |
| NORTHRIM BANCORP INC |  | 9.7 | -0.0 | -0.1 | 4.05 | scan_oversized |
| CENTRAL PACIFIC FINANCIAL CORP |  | 16.0 | -0.0 | -0.1 | 2.45 | scan_oversized |
| Global Net Lease, Inc. |  | 38.6 | -0.1 | -0.4 | 1.68 | scan_oversized |
| Uniti Group Inc. |  | 17.0 | 9.7 | 10.4 | None | unknown |
| Venture Global, Inc. |  | 50.8 | 35.0 | 5.7 | None | unknown |
| ENBRIDGE INC |  | 54.7 | None | None | None | unknown |
| EQUITY RESIDENTIAL |  | 15.0 | 8.2 | None | None | unknown |
| Entergy Louisiana, LLC |  | 67.5 | None | None | None | unknown |
| GOLUB CAPITAL BDC, Inc. |  | 13.3 | 4.7 | None | None | unknown |
| Brookfield Renewable Partners  |  | 15.4 | None | None | None | unknown |
| Blackstone Secured Lending Fun |  | 15.4 | 7.7 | None | None | unknown |
| BLACKROCK FLOATING RATE INCOME | | | | | | no XBRL |

*EBITDA is built from XBRL (operating income + D&A, or bottom-up); most-recent FY. `scan_oversized` = XBRL net debt < ⅓ of the scan's gross flag (size/extraction artifact). `distressed` = interest coverage < 1.5×. `refi_risk` = serviced but ND/EBITDA ≥ 5×. Single-period ratios; financials/REIT/BDC leverage is not comparable to corporate (deposits/portfolio debt) — read those by sector, not on this axis.*
