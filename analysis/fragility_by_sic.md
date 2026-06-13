# Fragility by real SIC division (ground-truthed sectors)

> **⚓ Frame — read first (reanchor):** this repo is a **general forensic engine for financial fragility & mispricing across the _whole economy_** — hidden / mismatched / circular leverage and valuation-run-ahead-of-cash-flow, found with **no sector prior**. **AI / data-center is _case zero_, not the object** (the method is sector- and era-agnostic — cf. fiber 1999, shale 2014). **Operating mode: maximum exhaustiveness — broad AND deep, uncapped, ≥ $1M-substance floor, US-primary (international by connectedness-to-core × data-accessibility); acting resource-constrained is NEVER correct; the only stop is physics (data that doesn't publicly exist → estimate it from proxies).** Full scope & doctrine: [total_ecosystem_dive.md](total_ecosystem_dive.md) · [README](../README.md).

**As of 2026-06-13.** The Phase-2 sector view, re-grounded in **real SEC SIC codes** pulled from data.sec.gov (131/140 CIK'd entities resolved), replacing the name heuristic. Machine-readable: [fragility_by_sic.json](fragility_by_sic.json).

| SIC division | n | mean comp | max comp | Σ debt $B |
|---|---:|---:|---:|---:|
| 46 Pipelines (non-gas) | 1 | 0.460 | 0.460 | 55 |
| 70 Hotels/lodging | 3 | 0.335 | 0.445 | 118 |
| 20 Food | 2 | 0.329 | 0.348 | 95 |
| 65 Real estate | 2 | 0.327 | 0.399 | 27 |
| 78 Motion pictures | 1 | 0.315 | 0.315 | 14 |
| 48 Communications | 6 | 0.315 | 0.390 | 293 |
| 67 Holding/investment (incl REITs/BDCs) | 20 | 0.301 | 0.475 | 373 |
| 64 Insurance agents | 1 | 0.300 | 0.300 | 32 |
| 29 Petroleum refining | 1 | 0.298 | 0.298 | 54 |
| 49 Utilities (electric/gas/sanitary) | 16 | 0.296 | 0.337 | 592 |
| 61 Nondepository credit | 6 | 0.282 | 0.452 | 110 |
| 73 Business services/software | 14 | 0.268 | 0.373 | 267 |
| 63 Insurance carriers | 1 | 0.267 | 0.267 | 12 |
| 60 Depository banks | 15 | 0.264 | 0.433 | 273 |
| 38 Instruments | 2 | 0.264 | 0.277 | 8 |
| 26 Paper | 1 | 0.259 | 0.259 | 9 |
| 51 Wholesale nondurable | 1 | 0.252 | 0.252 | 7 |
| 55 Auto dealers | 1 | 0.251 | 0.251 | 6 |
| 27 Printing/publishing | 1 | 0.248 | 0.248 | 14 |
| 62 Securities/brokers | 4 | 0.244 | 0.269 | 46 |
| (no SIC) | 9 | 0.242 | 0.331 | 171 |
| 37 Transportation equipment | 3 | 0.234 | 0.272 | 32 |
| 35 Machinery/computers | 4 | 0.234 | 0.271 | 24 |
| 28 Chemicals/pharma | 7 | 0.227 | 0.414 | 44 |
| 34 Fabricated metals | 1 | 0.225 | 0.225 | 1 |
| 36 Electronics | 4 | 0.222 | 0.296 | 17 |
| 13 Oil & gas extraction | 1 | 0.220 | 0.220 | 3 |
| 22 Textiles | 1 | 0.220 | 0.220 | 2 |
| 44 Water transport | 4 | 0.209 | 0.276 | 72 |
| 15 Construction | 1 | 0.200 | 0.200 | 1 |
| 50 Wholesale durable | 1 | 0.197 | 0.197 | 1 |
| 45 Air transport | 2 | 0.191 | 0.272 | 12 |
| 72 Personal services | 1 | 0.160 | 0.160 | 2 |
| 01 Agriculture | 2 | 0.112 | 0.115 | 0 |

## Top names per SIC division

- **46 Pipelines (non-gas)** (1): ENBRIDGE INC (0.460)
- **70 Hotels/lodging** (3): LAS VEGAS SANDS CORP (0.445), MGM RESORTS INTERNATIONAL (0.305), Hilton Grand Vacations Inc. (0.255)
- **20 Food** (2): Keurig Dr Pepper Inc. (0.348), PepsiCo, Inc. (0.310)
- **65 Real estate** (2): Kennedy-Wilson Holdings, Inc. (0.399), Urban Edge Properties (0.254)
- **78 Motion pictures** (1): AMC ENTERTAINMENT HOLDINGS, INC. (0.315)
- **48 Communications** (6): Lumen Technologies, Inc. (0.390), AT&T INC. (0.359), T-Mobile US, Inc. (0.307), Liberty Global Ltd. (0.302), Uniti Group Inc. (0.286), Versant Media Group, Inc. (0.247)
- **67 Holding/investment (incl REITs/BDCs)** (20): PennyMac Mortgage Investment Trust (0.475), EQUITY RESIDENTIAL (0.428), WELLTOWER INC. (0.381), MFA FINANCIAL, INC. (0.376), HEALTHPEAK PROPERTIES, INC. (0.361), ADAMAS TRUST, INC. (0.339)
- **64 Insurance agents** (1): BROWN & BROWN, INC. (0.300)
- **29 Petroleum refining** (1): Sunoco LP (0.298)
- **49 Utilities (electric/gas/sanitary)** (16): American Water Works Company, Inc. (0.337), Energy Transfer LP (0.336), Entergy Louisiana, LLC (0.334), NRG ENERGY, INC. (0.331), ENTERPRISE PRODUCTS PARTNERS L.P. (0.314), Cheniere Energy Partners, L.P. (0.308)
- **61 Nondepository credit** (6): BREAD FINANCIAL HOLDINGS, INC. (0.452), Hut 8 Corp. (0.413), Bit Digital, Inc (0.286), Exodus Movement, Inc. (0.188), VerifyMe, Inc. (0.181), WhiteFiber, Inc. (0.174)
- **73 Business services/software** (14): OMNICOM GROUP INC. (0.373), Meta Platforms, Inc. (0.325), Zscaler, Inc. (0.311), UNITED RENTALS, INC. (0.288), Clear Channel Outdoor Holdings, In (0.281), INTUIT INC. (0.280)
- **63 Insurance carriers** (1): Athene Holding Ltd. (0.267)
- **60 Depository banks** (15): Ameris Bancorp (0.433), BYLINE BANCORP, INC. (0.408), ENTERPRISE FINANCIAL SERVICES CORP (0.342), FIFTH THIRD BANCORP (0.330), Pinnacle Financial Partners, Inc. (0.295), ConnectOne Bancorp, Inc. (0.279)
- **38 Instruments** (2): EASTMAN KODAK COMPANY (0.277), BAXTER INTERNATIONAL INC (0.250)
- **26 Paper** (1): MERCER INTERNATIONAL INC. (0.259)
- **51 Wholesale nondurable** (1): CHS Inc. (0.252)
- **55 Auto dealers** (1): LITHIA MOTORS INC (0.251)
- **27 Printing/publishing** (1): McGraw Hill, Inc. (0.248)
- **62 Securities/brokers** (4): KKR & Co. Inc. (0.269), Victory Capital Holdings, Inc. (0.259), Apollo Global Management, Inc. (0.258), HOULIHAN LOKEY, INC. (0.189)
- **(no SIC)** (9): Goldman Sachs BDC, Inc. (0.331), Bain Capital Specialty Finance, In (0.319), GOLUB CAPITAL BDC, Inc. (0.299), Morgan Stanley Direct Lending Fund (0.278), BLACKROCK FLOATING RATE INCOME STR (0.255), Blackstone Secured Lending Fund (0.250)
- **37 Transportation equipment** (3): HONEYWELL INTERNATIONAL INC (0.272), Polaris Inc. (0.249), Commercial Vehicle Group, Inc. (0.181)
- **35 Machinery/computers** (4): Hyperscale Data, Inc. (0.271), LENNOX INTERNATIONAL INC (0.249), ITT INC. (0.246), TPI COMPOSITES, INC (0.168)
- **28 Chemicals/pharma** (7): Bausch Health Companies Inc. (0.414), Merck & Co., Inc. (0.247), Alvotech (0.240), AMNEAL PHARMACEUTICALS LLC (0.193), Celularity Inc (0.173), Humacyte, Inc. (0.163)
- **34 Fabricated metals** (1): Babcock & Wilcox Enterprises, Inc. (0.225)
- **36 Electronics** (4): WOLFSPEED, INC. (0.296), JABIL INC (0.251), Sanmina Corporation (0.189), ChargePoint Holdings, Inc. (0.152)
- **13 Oil & gas extraction** (1): W&T OFFSHORE INC (0.220)
- **22 Textiles** (1): MOHAWK INDUSTRIES INC (0.220)
- **44 Water transport** (4): ROYAL CARIBBEAN CRUISES LTD. (0.276), DHT Holdings, Inc. (0.203), Castor Maritime Inc. (0.180), SEACOR Marine Holdings Inc. (0.177)
- **15 Construction** (1): HOVNANIAN ENTERPRISES INC (0.200)
- **50 Wholesale durable** (1): Gold.com, Inc. (0.197)
- **45 Air transport** (2): American Airlines Group Inc. (0.272), AIR T INC (0.111)
- **72 Personal services** (1): WW INTERNATIONAL, INC. (0.160)
- **01 Agriculture** (2): iANTHUS CAPITAL HOLDINGS, INC. (0.115), Grown Rogue International Inc. (0.110)

*SIC is the issuer's primary classification; conglomerates and holding companies (SIC 67) may understate sub-sector detail. Pairs with the name-heuristic view in [fragility_by_sector.md](fragility_by_sector.md).*
