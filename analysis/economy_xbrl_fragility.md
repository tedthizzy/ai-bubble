# Economy-wide XBRL fragility — all public filers, ratio-based (size-bias-free)

> **⚓ Frame — read first (reanchor):** this repo is a **general forensic engine for financial fragility & mispricing across the _whole economy_** — hidden / mismatched / circular leverage and valuation-run-ahead-of-cash-flow, found with **no sector prior**. **AI / data-center is _case zero_, not the object** (the method is sector- and era-agnostic — cf. fiber 1999, shale 2014). **Operating mode: maximum exhaustiveness — broad AND deep, uncapped, ≥ $1M-substance floor, US-primary (international by connectedness-to-core × data-accessibility); acting resource-constrained is NEVER correct; the only stop is physics (data that doesn't publicly exist → estimate it from proxies).** Full scope & doctrine: [total_ecosystem_dive.md](total_ecosystem_dive.md) · [README](../README.md).

Financials-based scan over **7992 SEC filers** (6914 with usable XBRL), independent of the deal corpus and immune to gross-notional size-bias (ratio-based: net-debt/EBITDA + EBITDA/interest). Distribution: {'manageable': 1660, 'insufficient_data': 2998, 'negative_ebitda': 1740, 'distressed': 266, 'refi_risk': 250}. **266 filers show interest coverage < 1.5×** (the real distress line). Machine-readable: [economy_xbrl_fragility.json](economy_xbrl_fragility.json).

## Most distressed by interest coverage (top 60)

| entity | ticker | net debt $B | ND/EBITDA | int cov | EBITDA $B |
|---|---|---:|---:|---:|---:|
| StoneX Group Inc. | SNEX | -0.4 | -142.0 | 0.0 | 0.0 |
| ASPEN INSURANCE HOLDINGS LTD | AHL-PD | -1.36 | -13588.0 | 0.01 | 0.0 |
| Applied Digital Corp. | APLD | -1.72 | -3881.2 | 0.02 | 0.0 |
| Emmaus Life Sciences, Inc. | EMMA | 0.03 | 94.4 | 0.04 | 0.0 |
| Freedom Holding Corp. | FRHC | -0.97 | -37.5 | 0.05 | 0.03 |
| SELECTIS HEALTH, INC. | GBCS | 0.02 | 126.3 | 0.08 | 0.0 |
| REGIONS FINANCIAL CORP | RF | -24.37 | -177.9 | 0.09 | 0.14 |
| CareView Communications Inc | CRVW | 0.02 | 69.0 | 0.09 | 0.0 |
| Dave Inc./DE | DAVE | -0.13 | -176.8 | 0.11 | 0.0 |
| RideNow Group, Inc. | RDNW | 0.19 | 21.7 | 0.11 | 0.01 |
| TuHURA Biosciences, Inc./NV | HURA | -0.01 | -89.6 | 0.11 | 0.0 |
| CPI AEROSTRUCTURES INC | CVU | -0.0 | -19.0 | 0.11 | 0.0 |
| BayFirst Financial Corp. | BAFN | None | None | 0.11 | 0.0 |
| ESTEE LAUDER COMPANIES INC | EL | 5.14 | 116.7 | 0.12 | 0.04 |
| SIMMONS FIRST NATIONAL CORP | SFNC | -0.74 | -10.1 | 0.13 | 0.07 |
| SPORTSMAN'S WAREHOUSE HOLDINGS, IN | SPWH | 0.04 | 24.3 | 0.13 | 0.0 |
| KEMPER Corp | KMPR | 0.87 | 160.5 | 0.14 | 0.01 |
| UWM Holdings Corp | UWMC | 2.56 | 52.6 | 0.15 | 0.05 |
| STARWOOD PROPERTY TRUST, INC. | STWD | 2.04 | 9.1 | 0.16 | 0.22 |
| AYTU BIOPHARMA, INC | AYTU | -0.02 | -38.6 | 0.17 | 0.0 |
| Qutoutiao Inc. | QTTOY | -0.01 | -1.6 | 0.17 | 0.0 |
| Airsculpt Technologies, Inc. | AIRS | 0.03 | 23.0 | 0.19 | 0.0 |
| ARBOR REALTY TRUST INC | ABR | 10.98 | 60.3 | 0.2 | 0.18 |
| BLUE DOLPHIN ENERGY CO | BDCO | 0.04 | 29.8 | 0.22 | 0.0 |
| iANTHUS CAPITAL HOLDINGS, INC. | ITHUF | 0.19 | 48.4 | 0.23 | 0.0 |
| OCONEE FINANCIAL CORP | OSBK | None | None | 0.26 | 0.0 |
| SHARING ECONOMY INTERNATIONAL INC. | SEII | 0.0 | 47.4 | 0.27 | 0.0 |
| MEDIFAST INC | MED | -0.07 | -2466.5 | 0.28 | 0.0 |
| Viatris Inc | VTRS | 9.73 | 72.0 | 0.29 | 0.14 |
| STARZ ENTERTAINMENT CORP /CN/ | STRZ | 0.5 | 6.5 | 0.29 | 0.08 |
| ONE Group Hospitality, Inc. | STKS | 0.34 | 31.4 | 0.29 | 0.01 |
| ORION ENERGY SYSTEMS, INC. | OESX | 0.0 | 19.1 | 0.29 | 0.0 |
| SoFi Technologies, Inc. | SOFI | -1.59 | -6.8 | 0.3 | 0.23 |
| Finance of America Companies Inc. | FOA | 0.25 | 6.9 | 0.3 | 0.04 |
| TORO CORP. | TORO | -0.09 | -306.9 | 0.3 | 0.0 |
| Trinseo PLC | TSEOQ | 2.7 | 72.3 | 0.3 | 0.04 |
| Tronox Holdings plc | TROX | 3.0 | 61.2 | 0.31 | 0.05 |
| SUNation Energy, Inc. | SUNE | 0.0 | 6.0 | 0.31 | 0.0 |
| Affirm Holdings, Inc. | AFRM | 7.15 | 51.9 | 0.32 | 0.14 |
| Lightstone Value Plus REIT IV, Inc | LTSV | 0.01 | 1.7 | 0.32 | 0.0 |
| LEE ENTERPRISES, Inc | LEE | 0.42 | 29.8 | 0.34 | 0.01 |
| Westrock Coffee Co | WEST | 0.49 | 47.4 | 0.36 | 0.01 |
| System1, Inc. | SST | 0.2 | 11.3 | 0.37 | 0.02 |
| SUIC Worldwide Holdings Ltd. | SUIC | 0.0 | 12.0 | 0.37 | 0.0 |
| CEMTREX INC | CETX | -0.0 | -2.5 | 0.38 | 0.0 |
| BREAD FINANCIAL HOLDINGS, INC. | BFH | 2.08 | 6.1 | 0.39 | 0.34 |
| Lument Finance Trust, Inc. | LFT | None | None | 0.39 | 0.0 |
| APPlife Digital Solutions Inc | ALDS | 0.0 | 3.1 | 0.39 | 0.0 |
| Ridgetech Inc. | RDGT | -0.01 | -118.2 | 0.39 | 0.0 |
| Vistance Networks, Inc. | VISN | 7.79 | 28.4 | 0.4 | 0.27 |
| GLEN BURNIE BANCORP | GLBZ | -0.0 | -10.3 | 0.4 | 0.0 |
| LIFECORE BIOMEDICAL, INC. \DE\ | LFCR | 0.13 | 17.5 | 0.41 | 0.01 |
| QUOTEMEDIA INC | QMCI | None | None | 0.41 | 0.0 |
| EAGLE BANCORP INC | EGBN | -0.56 | -4.0 | 0.42 | 0.14 |
| Strategic Storage Trust VI, Inc. | SGST | None | None | 0.42 | 0.01 |
| Lionsgate Studios Corp. | LION | 1.44 | 12.5 | 0.44 | 0.11 |
| READING INTERNATIONAL INC | RDI | 0.18 | 22.8 | 0.44 | 0.01 |
| Solowin Holdings, Ltd. | AXG | None | None | 0.45 | 0.0 |
| Ryerson Holding Corp | RYZ | 0.88 | 18.0 | 0.46 | 0.05 |
| Advantage Solutions Inc. | ADV | 1.45 | 19.1 | 0.46 | 0.08 |

*Single-period ratios from latest XBRL. Financials/REIT/BDC leverage is not comparable to corporate (deposits/portfolio debt) — read those by sector. `distressed` = EBITDA/interest < 1.5×; `negative_ebitda` is tracked separately. This is the breadth layer; the deal-corpus signature scan + deep agents are the depth layer.*
