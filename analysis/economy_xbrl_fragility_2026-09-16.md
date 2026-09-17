# XBRL ratio screen: SEC exchange-ticker reference universe

This scan covers **8022 CIKs in the SEC exchange-ticker reference**, including 7021 nonempty companyfacts responses. The SEC returned 994 HTTP 404 responses and 7 empty HTTP 200 JSON objects. The reference omits filers without exchange tickers. Ratios use XBRL financial facts, separate from deal-notional totals. These are raw financial screen labels, not observed distress or an estimate of distress prevalence. Distribution: {'manageable': 836, 'insufficient_data': 4415, 'distressed': 155, 'refi_risk': 145, 'negative_ebitda': 1470}. **155** meet the uncalibrated interest-coverage cutoff below 1.5. The JSON includes all 8022 per-filer results and field definitions. Machine-readable: [economy_xbrl_fragility_2026-09-16.json](economy_xbrl_fragility_2026-09-16.json).

## Lowest positive-EBITDA interest coverage (top 60 screen hits)

| entity | ticker | net debt $B | ND/EBITDA | int cov | EBITDA $B |
|---|---|---:|---:|---:|---:|
| SkinHealth Systems Inc. | SKIN | None | None | 0.0 | 0.0 |
| CareView Communications Inc | CRVW | None | None | 0.03 | 0.0 |
| Emmaus Life Sciences, Inc. | EMMA | 0.02 | 82.1 | 0.04 | 0.0 |
| AIR T INC | AIRT | 0.23 | 200.9 | 0.09 | 0.0 |
| Forafric Global PLC | AFRI | None | None | 0.12 | 0.0 |
| SPORTSMAN'S WAREHOUSE HOLDINGS, IN | SPWH | 0.04 | 24.1 | 0.13 | 0.0 |
| Mirum Pharmaceuticals, Inc. | MIRM | None | None | 0.15 | 0.0 |
| Biglari Holdings Inc. | BH-A | None | None | 0.16 | 0.0 |
| CPI AEROSTRUCTURES INC | CVU | None | None | 0.16 | 0.0 |
| Cardiff Lexington Corp | CDIX | 0.02 | 20.3 | 0.16 | 0.0 |
| Sleep Number Corp | SNBRQ | None | None | 0.18 | 0.01 |
| Westrock Coffee Co | WEST | 0.47 | 45.6 | 0.19 | 0.01 |
| Terra Property Trust, Inc. | TPTS | 0.1 | 40.3 | 0.19 | 0.0 |
| Airsculpt Technologies, Inc. | AIRS | 0.02 | 20.3 | 0.2 | 0.0 |
| AXON ENTERPRISE, INC. | AXON | 1.13 | 53.8 | 0.22 | 0.02 |
| iANTHUS CAPITAL HOLDINGS, INC. | ITHUF | 0.2 | 50.4 | 0.23 | 0.0 |
| BLUE DOLPHIN ENERGY CO | BDCO | None | None | 0.25 | 0.0 |
| Tronox Holdings plc | TROX | 2.93 | 59.8 | 0.26 | 0.05 |
| 111, Inc. | YI | None | None | 0.27 | 0.0 |
| People Inc | PPLI | 0.3 | 9.1 | 0.28 | 0.03 |
| Viatris Inc | VTRS | 12.46 | 92.2 | 0.29 | 0.14 |
| Gevo, Inc. | GEVO | 0.11 | 21.3 | 0.29 | 0.01 |
| BrightSpire Capital, Inc. | BRSP | 2.68 | 362.1 | 0.31 | 0.01 |
| TheRealReal, Inc. | REAL | None | None | 0.33 | 0.01 |
| NextBoat Inc. | NXB | -0.0 | -3.2 | 0.34 | 0.0 |
| LEE ENTERPRISES, Inc | LEE | None | None | 0.35 | 0.01 |
| OPTICAL CABLE CORP | OCC | None | None | 0.35 | 0.0 |
| FGI Industries Ltd. | FGI | None | None | 0.38 | 0.0 |
| Green Plains Inc. | GPRE | 0.27 | 8.7 | 0.41 | 0.03 |
| Strategic Storage Trust VI, Inc. | SGST | None | None | 0.42 | 0.01 |
| Mobile Infrastructure Corp | BEEP | 0.18 | 22.5 | 0.43 | 0.01 |
| Datadog, Inc. | DDOG | None | None | 0.44 | 0.0 |
| Lionsgate Studios Corp. | LION | 1.31 | 11.5 | 0.44 | 0.11 |
| READING INTERNATIONAL INC | RDI | 0.14 | 18.1 | 0.44 | 0.01 |
| EASTMAN KODAK CO | KODK | -0.18 | -6.2 | 0.47 | 0.03 |
| System1, Inc. | SST | 0.25 | 19.2 | 0.47 | 0.01 |
| AES CORP | AES | None | None | 0.48 | 0.68 |
| APPIAN CORP | APPN | 0.11 | 11.1 | 0.49 | 0.01 |
| Cresco Labs Inc. | CRLBF | None | None | 0.5 | 0.02 |
| ALTISOURCE PORTFOLIO SOLUTIONS S.A | ASPS | 0.16 | 26.7 | 0.5 | 0.01 |
| Backblaze, Inc. | BLZE | None | None | 0.51 | 0.0 |
| OFFICE PROPERTIES INCOME TRUST | OPI | 1.63 | 15.4 | 0.52 | 0.11 |
| Xerox Holdings Corp | XRX | 3.66 | 20.7 | 0.53 | 0.18 |
| JETBLUE AIRWAYS CORP | JBLU | 6.34 | 19.8 | 0.54 | 0.32 |
| Advantage Solutions Inc. | ADV | 1.48 | 19.6 | 0.55 | 0.08 |
| INNEOVA Holdings Ltd | INEO | None | None | 0.57 | 0.0 |
| NEXPOINT DIVERSIFIED REAL ESTATE T | NXDT | None | None | 0.61 | 0.02 |
| LIFETIME BRANDS, INC | LCUT | None | None | 0.62 | 0.01 |
| Talen Energy Corp | TLN | 9.34 | 49.4 | 0.63 | 0.19 |
| AMC ENTERTAINMENT HOLDINGS, INC. | AMC | 3.07 | 10.4 | 0.64 | 0.3 |
| SONIDA SENIOR LIVING, INC. | SNDA | 1.52 | 61.0 | 0.65 | 0.02 |
| Xponential Fitness, Inc. | XPOF | 0.5 | 15.6 | 0.65 | 0.03 |
| TAKE TWO INTERACTIVE SOFTWARE INC | TTWO | 1.17 | 12.4 | 0.66 | 0.09 |
| INNOVATE Corp. | VATE | 0.54 | 9.1 | 0.66 | 0.06 |
| Granite Point Mortgage Trust Inc. | GPMT | None | None | 0.66 | 0.06 |
| Baidu, Inc. | BIDU | None | None | 0.67 | 0.27 |
| Eton Pharmaceuticals, Inc. | ETON | None | None | 0.67 | 0.0 |
| Nine Energy Service, Inc. | NINE | 0.08 | 2.2 | 0.67 | 0.04 |
| Clipper Realty Inc. | CLPR | None | None | 0.67 | 0.04 |
| CRYO CELL INTERNATIONAL INC | CCEL | 0.01 | 5.3 | 0.71 | 0.0 |

*Among 7021 companyfacts responses, the dated scan has 3833 filers with a matched debt/cash period (2239 within 186 days) and 3206 with matched EBITDA/interest years (2495 within 456 days). 1593 have positive-EBITDA interest coverage and 1343 have usable net-debt/EBITDA. Missing, stale or mismatched components are withheld from the affected ratio. Annual earnings can still predate the latest quarterly balance sheet. Banks, insurers, REITs, BDCs and utilities need sector-specific metrics. Negative EBITDA can reflect startup or accounting effects and is not evidence that debt service failed. Every screen hit requires company-level review.*
