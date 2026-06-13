# Economy-wide fragility map — where the mispricing actually concentrates

> **⚓ Frame — read first (reanchor):** this repo is a **general forensic engine for financial fragility & mispricing across the _whole economy_** — hidden / mismatched / circular leverage and valuation-run-ahead-of-cash-flow, found with **no sector prior**. **AI / data-center is _case zero_, not the object** (the method is sector- and era-agnostic — cf. fiber 1999, shale 2014). **Operating mode: maximum exhaustiveness — broad AND deep, uncapped, ≥ $1M-substance floor, US-primary (international by connectedness-to-core × data-accessibility); acting resource-constrained is NEVER correct; the only stop is physics (data that doesn't publicly exist → estimate it from proxies).** Full scope & doctrine: [total_ecosystem_dive.md](total_ecosystem_dive.md) · [README](../README.md).

**As of 2026-06-13.** Output of the **sector-agnostic** forensic signature scan (`scripts/economy_wide_signature_scan.py`) over the enumerated substrate: **62,952 deal rows** + **10,051 tranche rows**, **2,091 entities scored** on the eight §2 signatures with **no AI filter**. The epicenter is an *output*, not an assumption. Machine-readable: [economy_wide_fragility_map.json](economy_wide_fragility_map.json).

## Headline

- The **AI / data-center cluster is mid-pack**: its highest-ranked entity is **#14** of 2,091; only **2 AI-tagged names appear in the top 50**. Case zero is real but is *not* the economy's primary fragility concentration.
- The top of the map is dominated by **leveraged, credit-sensitive, rate-exposed balance sheets**: mortgage REITs, midstream/LNG, distressed telecom, levered specialty pharma, payments/fintech, CRE/REITs and BDC private credit — sectors with no AI dependence.

## Method (pre-registered)

Each entity is scored 0-1 on each signature; the composite is a fixed-weight blend committed **before** inspecting the ranking (rigor §5.7): `leverage 0.22`, `refi 0.18`, `carry 0.14`, `hidden 0.14`, `concentration 0.12`, `circular 0.1`, `distress 0.1`. Obligor attribution is **role-based** (debt loads the borrower/issuer, not the arranging bank). Per-deal notional above **$100B is excluded** as a program/shelf/units artifact and logged (14 rows). Counterparty-HHI is suppressed below 3 distinct counterparties (sparsity is not concentration).

## Top 50 by composite fragility

| # | entity | | debt $B | ≤2027 $B | max cpn | SPV | #cp | HHI | composite |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | SPACE EXPLORATION TECHNOLOGIES CORP |  | 45.5 | 40.0 | 6.8% | 4 | 5 | 0.23 | 0.489 |
| 2 | PennyMac Mortgage Investment Trust |  | 53.2 | 33.9 | 11.3% | 0 | 11 | 0.12 | 0.475 |
| 3 | ENBRIDGE INC |  | 54.7 | 26.6 | 7.4% | 0 | 6 | 0.51 | 0.460 |
| 4 | EQUINIX INC |  | 76.3 | 51.0 | 4.8% | 0 | 9 | 0.81 | 0.456 |
| 5 | BREAD FINANCIAL HOLDINGS, INC. |  | 77.1 | 38.7 | 12.0% | 0 | 3 | 0.42 | 0.452 |
| 6 | LAS VEGAS SANDS CORP |  | 16.5 | 13.1 | 20.0% | 0 | 1 | 1.00 | 0.445 |
| 7 | SIMMONS FIRST NATIONAL CORP |  | 52.9 | 35.4 | 13.9% | 0 | 0 | 0.00 | 0.435 |
| 8 | Ameris Bancorp |  | 126.1 | 103.7 | 8.2% | 0 | 3 | 0.33 | 0.433 |
| 9 | EQUITY RESIDENTIAL |  | 15.0 | 11.0 | 16.1% | 0 | 5 | 0.22 | 0.428 |
| 10 | UNIVEST FINANCIAL Corp |  | 8.0 | 8.0 | 7.0% | 0 | 3 | 1.00 | 0.424 |
| 11 | NextDecade Corp |  | 28.9 | 4.8 | 13.0% | 8 | 21 | 0.25 | 0.420 |
| 12 | NAVIENT CORP |  | 157.3 | 16.0 | 9.4% | 0 | 3 | 1.00 | 0.419 |
| 13 | Bausch Health Companies Inc. |  | 32.3 | 17.5 | 11.0% | 1 | 6 | 0.29 | 0.414 |
| 14 | Hut 8 Corp. | **AI** | 26.0 | 20.6 | 9.0% | 1 | 11 | 0.28 | 0.413 |
| 15 | X Holdings Corp., as holdings, X Corp. |  | 20.0 | 20.0 | 2.0% | 1 | 4 | 0.25 | 0.410 |
| 16 | X.AI Corp, as holdings, X.AI LLC | **AI** | 20.0 | 20.0 | 2.0% | 1 | 4 | 0.25 | 0.410 |
| 17 | BYLINE BANCORP, INC. |  | 24.2 | 16.0 | 6.9% | 0 | 8 | 0.90 | 0.408 |
| 18 | Kennedy-Wilson Holdings, Inc. |  | 16.5 | 12.4 | 7.3% | 3 | 3 | 0.35 | 0.399 |
| 19 | KDP |  | 18.4 | 18.4 | 5.5% | 0 | 5 | 0.50 | 0.394 |
| 20 | Lumen Technologies, Inc. |  | 91.2 | 26.8 | 10.8% | 4 | 38 | 0.10 | 0.390 |
| 21 | PUBLIC SERVICE ENTERPRISE GROUP INC |  | 11.4 | 11.4 | 5.8% | 0 | 3 | 0.50 | 0.382 |
| 22 | WELLTOWER INC. |  | 31.5 | 18.2 | 5.1% | 0 | 6 | 0.60 | 0.381 |
| 23 | MFA FINANCIAL, INC. |  | 54.1 | 15.7 | 10.2% | 2 | 3 | 0.38 | 0.376 |
| 24 | Alibaba Group Holding Ltd |  | 48.9 | 12.0 | 5.2% | 0 | 3 | 0.34 | 0.375 |
| 25 | Encore Inc. |  | 42.6 | 40.0 | 2.0% | 0 | 2 | 0.50 | 0.373 |
| 26 | OMNICOM GROUP INC. |  | 27.5 | 18.8 | 5.3% | 0 | 11 | 0.20 | 0.373 |
| 27 | PayPal Holdings, Inc. |  | 9.2 | 1.0 | 20.0% | 0 | 3 | 0.57 | 0.370 |
| 28 | HEALTHPEAK PROPERTIES, INC. |  | 17.6 | 9.0 | 9.0% | 2 | 12 | 0.16 | 0.361 |
| 29 | AT&T INC. |  | 111.6 | 58.1 | 5.2% | 0 | 9 | 0.20 | 0.359 |
| 30 | Marina Bay Sands Pte. Ltd. |  | 5.8 | 2.9 | 20.0% | 0 | 0 | 0.00 | 0.355 |
| 31 | NIKE, INC. |  | 6.5 | 5.0 | 0.6% | 0 | 3 | 1.00 | 0.354 |
| 32 | SM Energy Co |  | 23.2 | 15.2 | 8.4% | 0 | 11 | 0.39 | 0.350 |
| 33 | WYNN RESORTS LTD |  | 43.7 | 0.0 | 6.8% | 0 | 6 | 0.94 | 0.349 |
| 34 | CONOCOPHILLIPS |  | 18.5 | 8.0 | — | 0 | 6 | 0.85 | 0.348 |
| 35 | Keurig Dr Pepper Inc. |  | 43.7 | 21.4 | 5.5% | 0 | 12 | 0.31 | 0.348 |
| 36 | ENTERPRISE FINANCIAL SERVICES CORP |  | 23.3 | 23.3 | 5.7% | 0 | 0 | 0.00 | 0.342 |
| 37 | Eaton Corp plc |  | 52.5 | 28.5 | 5.5% | 1 | 12 | 0.23 | 0.341 |
| 38 | ADAMAS TRUST, INC. |  | 6.2 | 0.3 | 9.9% | 0 | 4 | 1.00 | 0.339 |
| 39 | AMCOR PLC |  | 93.7 | 32.6 | 5.5% | 0 | 26 | 0.37 | 0.339 |
| 40 | ARES CAPITAL CORP |  | 54.8 | 2.1 | 5.5% | 12 | 14 | 0.21 | 0.338 |
| 41 | American Water Works Company, Inc. |  | 21.3 | 18.5 | 5.2% | 0 | 2 | 1.00 | 0.337 |
| 42 | AGREE REALTY CORP |  | 22.9 | 15.4 | 5.8% | 0 | 4 | 0.44 | 0.337 |
| 43 | General Motors Co |  | 78.3 | 33.5 | — | 0 | 26 | 0.34 | 0.336 |
| 44 | Energy Transfer LP |  | 47.2 | 17.4 | 8.0% | 0 | 4 | 0.29 | 0.336 |
| 45 | Entergy Louisiana, LLC |  | 67.5 | 11.1 | 8.8% | 0 | 17 | 0.34 | 0.334 |
| 46 | EQT Corp |  | 10.9 | 10.8 | 7.5% | 0 | 0 | 0.00 | 0.333 |
| 47 | NRG ENERGY, INC. |  | 86.5 | 14.8 | 7.4% | 3 | 17 | 0.14 | 0.331 |
| 48 | Goldman Sachs BDC, Inc. |  | 22.6 | 10.1 | 6.4% | 6 | 6 | 0.31 | 0.331 |
| 49 | FIFTH THIRD BANCORP |  | 22.0 | 22.0 | 4.0% | 0 | 1 | 1.00 | 0.330 |
| 50 | Sabre Corp |  | 15.9 | 8.1 | 11.2% | 2 | 22 | 0.12 | 0.329 |

## Per-signature leaders (top 8 each)

- **leverage** — Ameris Bancorp (1.00), NAVIENT CORP (1.00), AT&T INC. (1.00), MGM RESORTS INTERNATIONAL (1.00), ORACLE CORP (1.00), BLACKROCK FLOATING RATE INCO (1.00), AMCOR PLC (0.99), Broadcom Inc. (0.98)
- **refi** — X Holdings Corp., as holding (1.00), X.AI Corp, as holdings, X.AI (1.00), KDP (1.00), PUBLIC SERVICE ENTERPRISE GR (1.00), ENTERPRISE FINANCIAL SERVICE (1.00), FIFTH THIRD BANCORP (1.00), BANK OF HAWAII CORP (1.00), EQT Corp (1.00)
- **carry** — LAS VEGAS SANDS CORP (1.00), EQUITY RESIDENTIAL (1.00), PayPal Holdings, Inc. (1.00), Marina Bay Sands Pte. Ltd. (1.00), Perfect Moment Ltd. (1.00), Hyperscale Data, Inc. (1.00), NEXTNRG, INC. (1.00), Workhorse Group Inc. (1.00)
- **hidden** — HEALTHPEAK OP, LLC (1.00), BHP Group Ltd (1.00), Substitution of BHP Billiton (1.00), LOMB CORPORATION (1.00), Shift4 Payments, LLC (1.00), McGraw-Hill Global Education (1.00), Calpine Corporation (1.00), DOC DR, LLC (as successor to (1.00)
- **concentration** — UNIVEST FINANCIAL Corp (1.00), NAVIENT CORP (1.00), NIKE, INC. (1.00), ADAMAS TRUST, INC. (1.00), ARBOR REALTY TRUST INC (1.00), ConnectOne Bancorp, Inc. (1.00), BAXTER INTERNATIONAL INC (1.00), LENNOX INTERNATIONAL INC (1.00)
- **circular** — Rio Bravo Solar II, LLC (1.00), TransAlta Energy Marketing ( (1.00), Shell Energy North America ( (1.00), Constellation Energy Generat (1.00), Greg LeMond (1.00), Northwest Ohio Solar, LLC (0.80), Washington Wind LLC (0.80), Elora Solar, LLC (0.80)
- **distress** — 

## Data-quality caveats & known bias (§5.10)

- **Coverage bias:** only entities with a deal/tranche footprint in our corpus are scored; fully-private cash-financed players and entities whose debt we have not yet extracted are under-represented. Absence here is *not* a clean bill.
- **`max_coupon` is outlier-sensitive:** a few >15% values (e.g. PayPal, Las Vegas Sands) are likely penalty/step-up/extraction artifacts, not the running coupon. Carry weight is modest (0.14); a median-coupon refinement is queued.
- **Double-count residual:** the same obligation across filings is de-duped on (obligor, type, notional, maturity); near-miss variants may still double-count.
- **Notional ≠ leverage:** notional sums gross facility/issuance size, not net debt; the next pass joins XBRL net-debt/EBITDA to convert size into true leverage.
- **Bank balance sheets distort the leverage signal:** for depository institutions (e.g. Ameris, Simmons First, Univest) deposit / FHLB / repo liabilities are summed as `debt_facility`. Bank fragility is duration & deposit-flight, not corporate leverage — banks are reclassified and scored separately in Phase 2, not on this corporate-leverage axis.
- **Distress signature (§2.8) is a DATA GAP, not a null reading:** `concentration_risk_flag` is essentially unpopulated in the deal corpus, so the distress sub-score is ~0 everywhere. The real §2.8 layer — insider selling, covenant amendments/waivers, late filings, rating actions, non-payment liens — requires Form-4 / 8-K / NT extraction queued for Phase 3; its absence here must not be read as 'no distress'.

*Reproducible from the cited source rows; rerun `uv run python scripts/economy_wide_signature_scan.py`. This map seeds Phase 2 (sector classification) and Phase 3 (deep-agent profiling of the flagged concentrations).*
