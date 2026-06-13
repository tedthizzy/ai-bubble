# Bank-distress scan — all FDIC institutions (off-EDGAR, proper bank model)

> **⚓ Frame — read first (reanchor):** this repo is a **general forensic engine for financial fragility & mispricing across the _whole economy_** — hidden / mismatched / circular leverage and valuation-run-ahead-of-cash-flow, found with **no sector prior**. **AI / data-center is _case zero_, not the object** (the method is sector- and era-agnostic — cf. fiber 1999, shale 2014). **Operating mode: maximum exhaustiveness — broad AND deep, uncapped, ≥ $1M-substance floor, US-primary (international by connectedness-to-core × data-accessibility); acting resource-constrained is NEVER correct; the only stop is physics (data that doesn't publicly exist → estimate it from proxies).** Full scope & doctrine: [total_ecosystem_dive.md](total_ecosystem_dive.md) · [README](../README.md).

Closes the financials gap the corporate-leverage scan couldn't read. **All 4,352 FDIC banks** (2026-Q1) scored on the *bank-specific* distress model — risk-based capital, ROA, nonperforming, equity/assets. **286 flagged** ({'other_distress': 280, 'undercapitalized': 2, 'not_well_capitalized': 4}). Real new public-record ingestion via the free FDIC API. Machine-readable: [fdic_bank_distress.json](fdic_bank_distress.json).

## Most distressed banks (by risk-based capital ratio)

| bank | state | assets $B | RBC % | ROA % | NPA % | flags |
|---|---|---:|---:|---:|---:|---|
| BENEFICIAL STATE BANK | CALIFORNIA | 1.97 | 0 | -0.3442506925316247 | 2.128631884742297 | losing money (ROA -0.34%) |
| EREBOR BANK N A | OHIO | 1.7 | 0 | -1.4110345532046793 | 0 | losing money (ROA -1.41%) |
| MUTUALONE BANK | MASSACHUSE | 1.26 | 0 | 0.26458684405673794 | 4.760855190654618 | high nonperforming (4.8%) |
| BANK OF WASHINGTON | MISSOURI | 1.18 | 0 | 0.2155545456173276 | 4.305603658448376 | high nonperforming (4.3%) |
| FINWISE BANK | UTAH | 0.89 | 0 | 1.5407701589390352 | 5.594409523948667 | high nonperforming (5.6%) |
| MRV BANKS | MISSOURI | 0.79 | 0 | 1.6694537499186974 | 6.084016830807696 | high nonperforming (6.1%) |
| AXIOM BANK NATIONAL ASSN | FLORIDA | 0.77 | 0 | -0.0672502724021053 | 0.9561251809766864 | losing money (ROA -0.07%) |
| FIRST SOUTHERN BANK | ALABAMA | 0.69 | 0 | -4.341435775637918 | 5.095866815557648 | losing money (ROA -4.34%); high nonperforming (5.1%) |
| BANK OF HOUSTON | TEXAS | 0.69 | 0 | -2.920138818476591 | 0.11260456398550142 | losing money (ROA -2.92%) |
| CROWN BANK | NEW JERSEY | 0.64 | 0 | 2.166380540934845 | 7.082712751899056 | high nonperforming (7.1%) |
| ONEUNITED BANK | MASSACHUSE | 0.61 | 0 | -1.0365121017602759 | 0.12872992494585625 | losing money (ROA -1.04%) |
| FIRST CHOICE BANK | MISSISSIPP | 0.56 | 0 | -0.23676326744477152 | 0.5433644568771577 | losing money (ROA -0.24%) |
| HUNTINGTON FSB | WEST VIRGI | 0.54 | 0 | -0.4550750763954537 | 0.15874636786453644 | losing money (ROA -0.46%) |
| CITIZENS COMMUNITY BANK | ILLINOIS | 0.54 | 0 | 0.6164675289739738 | 4.195408168002005 | high nonperforming (4.2%) |
| BANK OF LAFAYETTE GEORGIA | GEORGIA | 0.45 | 0 | 0.923211915564762 | 0.459926243670207 | thin equity (3.8% of assets) |
| BANK OF FRANKEWING | TENNESSEE | 0.43 | 0 | 0.4997932673303315 | 4.602299306152453 | high nonperforming (4.6%) |
| EXCHANGE BANK | GEORGIA | 0.41 | 0 | -3.2842483587695743 | 0.07362028347429807 | losing money (ROA -3.28%) |
| BALBOA THRIFT&LOAN ASSN | CALIFORNIA | 0.41 | 0 | -0.6028060818827904 | 0.8801254871204138 | losing money (ROA -0.60%) |
| COMMUNITY SAVINGS BANK | ILLINOIS | 0.41 | 0 | -0.3248444880397054 | 0.12201306862867602 | losing money (ROA -0.32%) |
| VARO BANK NATIONAL ASSN | UTAH | 0.37 | 0 | -24.675163734001373 | 0.14294493280252224 | losing money (ROA -24.68%) |
| EASTERN SAVINGS BANK FSB | MARYLAND | 0.35 | 0 | 2.360438779588755 | 5.662626439525115 | high nonperforming (5.7%) |
| PHENIX-GIRARD BANK | ALABAMA | 0.34 | 0 | 0.8009890473454179 | 0.09367000232720503 | thin equity (2.0% of assets) |
| LAONA STATE BANK | WISCONSIN | 0.29 | 0 | -0.4458396817768143 | 0.777671541639772 | losing money (ROA -0.45%) |
| GATEWAY BANK FSB | CALIFORNIA | 0.29 | 0 | -0.48994873819918244 | 2.5250410079223817 | losing money (ROA -0.49%) |
| ONE WORLD BANK | TEXAS | 0.29 | 0 | -1.6191743623996218 | 1.1248381339026354 | losing money (ROA -1.62%) |
| NEW HORIZON BANK NA | VIRGINIA | 0.28 | 0 | -0.48020748587597284 | 0.6862073049495214 | losing money (ROA -0.48%) |
| PEOPLES TRUST&SAVINGS BANK | INDIANA | 0.25 | 0 | -0.10549764456220506 | 1.7084484244264235 | losing money (ROA -0.11%) |
| FIRST SECURITY BANK&TRUST CO | OKLAHOMA | 0.25 | 0 | 0.9304063967427824 | 7.699258554059396 | high nonperforming (7.7%) |
| FIRST BANK OF CENTRAL OHIO | OHIO | 0.25 | 0 | -0.19702224108794722 | 0.6448152707858457 | losing money (ROA -0.20%) |
| FIRST STATE BANK OF WYOMING | MINNESOTA | 0.24 | 0 | -0.20252492135558894 | 0.10321303001569174 | losing money (ROA -0.20%) |
| HIBERNIA BANK | LOUISIANA | 0.24 | 0 | -0.019567158155632283 | 1.2065871812374058 | losing money (ROA -0.02%) |
| TRIAD BANK NATIONAL ASSN | OKLAHOMA | 0.21 | 0 | 2.218752727378517 | 5.383082538736591 | high nonperforming (5.4%) |
| VIDALIA FEDERAL SAVINGS BANK | GEORGIA | 0.21 | 0 | -0.7289529857701532 | 0.24576925777684153 | losing money (ROA -0.73%) |
| FIRST&PEOPLES BANK&TRUST CO | KENTUCKY | 0.21 | 0 | -0.5623698496575467 | 7.328214365918571 | losing money (ROA -0.56%); high nonperforming (7.3%) |
| FIRST ENTERPRISE BANK | OKLAHOMA | 0.2 | 0 | -1.2684347878861444 | 5.737858426340698 | losing money (ROA -1.27%); high nonperforming (5.7%) |
| CITIZENS BANK&TRUST CO | LOUISIANA | 0.19 | 0 | 0.7686184084108814 | 5.177428428885327 | high nonperforming (5.2%) |
| CENTRAL FS&LA | ILLINOIS | 0.19 | 0 | -0.053771224122598396 | 0.47816401595606906 | losing money (ROA -0.05%) |
| UNITED REPUBLIC BANK | NEBRASKA | 0.19 | 0 | 0.04522735741176168 | 5.868012689284431 | high nonperforming (5.9%) |
| INTEGRO BANK | ARIZONA | 0.19 | 0 | -1.0005980648914061 | 2.39751447415859 | losing money (ROA -1.00%) |
| SOUTH LAFOURCHE B&T CO | LOUISIANA | 0.18 | 0 | 0.9120364814592583 | 4.0306214485433385 | high nonperforming (4.0%) |
| WALDEN MUTUAL BANK | NEW HAMPSH | 0.18 | 0 | 0.006787522271557453 | 5.913665108605994 | high nonperforming (5.9%) |
| BEACH CITIES COMMERCIAL BANK | CALIFORNIA | 0.18 | 0 | -0.33852064252108793 | 0 | losing money (ROA -0.34%) |
| FIDELITY BANK OF TEXAS | TEXAS | 0.17 | 0 | -0.37961845863740545 | 0.4317303680592088 | losing money (ROA -0.38%) |
| FLINT HILLS BANK | KANSAS | 0.17 | 0 | -12.415564938936317 | 0 | losing money (ROA -12.42%) |
| HERITAGE BANK OF ST TAMMANY | LOUISIANA | 0.17 | 0 | -6.90648808769119 | 0.8550214648494484 | losing money (ROA -6.91%) |
| WESTMORELAND FS&LA | PENNSYLVAN | 0.17 | 0 | -0.33130044362082783 | 0.5598499151022929 | losing money (ROA -0.33%) |
| FIRST BANK | KANSAS | 0.16 | 0 | 1.0141093474426808 | 4.00917624655731 | high nonperforming (4.0%) |
| BANK OF ESTES PARK | COLORADO | 0.16 | 0 | -0.19819402051181062 | 0 | losing money (ROA -0.20%) |
| ICON BUSINESS BANK | CALIFORNIA | 0.16 | 0 | -0.8799286045952559 | 0.21831273618629354 | losing money (ROA -0.88%) |
| FIRST NATIONAL BANK OF HUGO | COLORADO | 0.15 | 0 | -6.077905525610047 | 0 | losing money (ROA -6.08%) |

*Bank distress ≠ corporate leverage: a bank is fragile via capital adequacy (risk-based capital < 10% = not well-capitalized; < 8% = PCA), losses (ROA < 0), and asset quality (nonperforming > 4%) — not EBITDA/interest. This is the breadth layer for the ~4,000-bank universe the corporate scan excluded.*
