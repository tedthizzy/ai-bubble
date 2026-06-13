# Fragility by sector — which clusters light up (AI is one of many)

> **⚓ Frame — read first (reanchor):** this repo is a **general forensic engine for financial fragility & mispricing across the _whole economy_** — hidden / mismatched / circular leverage and valuation-run-ahead-of-cash-flow, found with **no sector prior**. **AI / data-center is _case zero_, not the object** (the method is sector- and era-agnostic — cf. fiber 1999, shale 2014). **Operating mode: maximum exhaustiveness — broad AND deep, uncapped, ≥ $1M-substance floor, US-primary (international by connectedness-to-core × data-accessibility); acting resource-constrained is NEVER correct; the only stop is physics (data that doesn't publicly exist → estimate it from proxies).** Full scope & doctrine: [total_ecosystem_dive.md](total_ecosystem_dive.md) · [README](../README.md).

**As of 2026-06-13.** Phase 2 of the dive: the Phase-1 economy-wide fragility map, grouped by sector so the concentrations fall out as a result. Classification is **heuristic (name/ticker); CIK->SIC join queued**. Banks are shown on a separate axis (deposit/FHLB liabilities are not corporate leverage). Machine-readable: [fragility_by_sector.json](fragility_by_sector.json).

**Among genuine multi-name cohorts (n≥3), AI / data-center ranks #2 of 16 by mean composite fragility — in a top-tier dead heat with midstream/pipeline and mortgage REITs (~0.348).** A real, uniformly-stressed concentration — but not *the* epicenter; there isn't a single one.

| sector | n | Σ debt $B | Σ ≤2027 $B | mean comp | max comp | off-lev axis |
|---|---:|---:|---:|---:|---:|:--:|
| Aerospace / space / defense | 1 | 46 | 40 | 0.489 | 0.489 |  |
| Midstream / pipeline | 4 | 216 | 61 | 0.349 | 0.460 |  |
| Data center / AI infra | 7 | 255 | 120 | 0.348 | 0.456 |  |
| Mortgage REIT | 5 | 126 | 54 | 0.348 | 0.475 |  |
| Payments / fintech | 6 | 357 | 73 | 0.342 | 0.452 |  |
| Bank / depository | 8 | 261 | 197 | 0.338 | 0.435 | banks |
| Consumer / staples / retail | 4 | 195 | 78 | 0.338 | 0.354 |  |
| Gaming / leisure / lodging | 6 | 251 | 59 | 0.333 | 0.445 |  |
| Telecom | 4 | 280 | 108 | 0.331 | 0.390 |  |
| Specialty pharma / healthcare | 3 | 52 | 23 | 0.322 | 0.414 |  |
| REIT / CRE (equity) | 15 | 201 | 107 | 0.316 | 0.428 |  |
| LNG / gas export | 4 | 99 | 11 | 0.314 | 0.420 |  |
| Media / advertising | 3 | 47 | 20 | 0.295 | 0.373 |  |
| BDC / private credit | 5 | 118 | 16 | 0.293 | 0.338 |  |
| Industrial / materials / other infra | 6 | 117 | 53 | 0.289 | 0.341 |  |
| Other / unclassified | 97 | 1965 | 732 | 0.289 | 0.424 |  |
| Power / utility | 20 | 683 | 121 | 0.288 | 0.382 |  |
| Oil & gas E&P | 2 | 32 | 9 | 0.285 | 0.316 |  |

## Top names per sector

- **Aerospace / space / defense** (1): SPACE EXPLORATION TECHNOLOGIES CORP (0.489)
- **Midstream / pipeline** (4): ENBRIDGE INC (0.460), Energy Transfer LP (0.336), ENTERPRISE PRODUCTS PARTNERS L.P. (0.314), Targa Resources Corp. (0.288)
- **Data center / AI infra** (7): EQUINIX INC (0.456), Hut 8 Corp. (0.413), X.AI Corp, as holdings, X.AI LLC (0.410), Applied Digital Corp. (0.327), TERAWULF INC. (0.286), Hyperscale Data, Inc. (0.271)
- **Mortgage REIT** (5): PennyMac Mortgage Investment Trust (0.475), MFA FINANCIAL, INC. (0.376), ARBOR REALTY TRUST INC (0.312), BLACKSTONE MORTGAGE TRUST, INC. (0.303), Ready Capital Corp (0.272)
- **Payments / fintech** (6): BREAD FINANCIAL HOLDINGS, INC. (0.452), NAVIENT CORP (0.419), PayPal Holdings, Inc. (0.370), GLOBAL PAYMENTS INC (0.275), Shift4 Payments, LLC (0.274), Fidelity National Information Servic (0.259)
- **Bank / depository** (8): SIMMONS FIRST NATIONAL CORP (0.435), Ameris Bancorp (0.433), BYLINE BANCORP, INC. (0.408), FIFTH THIRD BANCORP (0.330), BANK OF HAWAII CORP (0.308), ConnectOne Bancorp, Inc. (0.279)
- **Consumer / staples / retail** (4): NIKE, INC. (0.354), Keurig Dr Pepper Inc. (0.348), AMCOR PLC (0.339), PepsiCo, Inc. (0.310)
- **Gaming / leisure / lodging** (6): LAS VEGAS SANDS CORP (0.445), Marina Bay Sands Pte. Ltd. (0.355), WYNN RESORTS LTD (0.349), MGM RESORTS INTERNATIONAL (0.305), ROYAL CARIBBEAN CRUISES LTD. (0.276), Carnival Corp Ltd. (0.267)
- **Telecom** (4): Lumen Technologies, Inc. (0.390), AT&T INC. (0.359), T-Mobile US, Inc. (0.307), COMCAST CORP (0.268)
- **Specialty pharma / healthcare** (3): Bausch Health Companies Inc. (0.414), Bausch & Lomb Corp (0.281), Sarepta Therapeutics, Inc. (0.273)
- **REIT / CRE (equity)** (15): EQUITY RESIDENTIAL (0.428), Kennedy-Wilson Holdings, Inc. (0.399), WELLTOWER INC. (0.381), HEALTHPEAK PROPERTIES, INC. (0.361), AGREE REALTY CORP (0.337), SIMON PROPERTY GROUP INC. (0.325)
- **LNG / gas export** (4): NextDecade Corp (0.420), Cheniere Energy Partners, L.P. (0.308), Venture Global, Inc. (0.282), RIO GRANDE LNG, LLC (0.247)
- **Media / advertising** (3): OMNICOM GROUP INC. (0.373), McGraw-Hill Global Education Interme (0.267), Versant Media Group, Inc. (0.247)
- **BDC / private credit** (5): ARES CAPITAL CORP (0.338), Goldman Sachs BDC, Inc. (0.331), GOLUB CAPITAL BDC, Inc. (0.299), Blackstone Secured Lending Fund (0.250), BLUE OWL CAPITAL INC. (0.249)
- **Industrial / materials / other infra** (6): Eaton Corp plc (0.341), BHP Group Ltd (0.295), Substitution of BHP Billiton Finance (0.295), RIO TINTO LTD (0.281), HONEYWELL INTERNATIONAL INC (0.272), JABIL INC (0.251)
- **Other / unclassified** (97): UNIVEST FINANCIAL Corp (0.424), X Holdings Corp., as holdings, X Cor (0.410), KDP (0.394), Alibaba Group Holding Ltd (0.375), Encore Inc. (0.373), CONOCOPHILLIPS (0.348)
- **Power / utility** (20): PUBLIC SERVICE ENTERPRISE GROUP INC (0.382), SM Energy Co (0.350), Entergy Louisiana, LLC (0.334), NRG ENERGY, INC. (0.331), CENTERPOINT ENERGY, INC. (0.300), NISOURCE INC. (0.295)
- **Oil & gas E&P** (2): ANTERO RESOURCES Corp (0.316), Permian Resources Corp (0.255)

## Reading & caveats

- **No single epicenter.** The top sectors sit in a narrow 0.34-0.35 mean-composite band (oil&gas E&P, midstream, AI-infra, mortgage REITs, payments) — fragility is **broadly distributed** across leveraged, rate-sensitive cohorts, not concentrated in one. This is the central Phase-2 finding.
- **AI-infra ranks high because it is *uniformly* stressed** (tight cohort, n=7), whereas big sectors like utilities (n=20) carry many healthy names that dilute the mean. AI validated as case zero precisely because the whole cohort lights up — but it is one of ~6 comparably-stressed cohorts, not a unique outlier.
- **Small-n instability:** several top sectors have n=3-4 (E&P, midstream), so their mean composite is noisy; treat the ordering inside the 0.34-0.35 band as a tie, not a strict ranking.
- **Coverage gap:** 97 of 200 names fell into *Other / unclassified* ($1965B if present) — the name heuristic is coarse and the single largest bucket. The CIK→SIC join is the fix and will redistribute most of these into real sectors before any conclusion is drawn.

*Heuristic classification; the precise CIK->SIC join (a small data.sec.gov pull) is queued for when storage clears. Seeds Phase 3 deep-agent profiling, which targets the highest-mean-composite non-bank concentrations.*
