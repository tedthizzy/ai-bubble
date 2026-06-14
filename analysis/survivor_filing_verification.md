# Survivor filing verification (orchestrator-pulled EDGAR)

> **⚓ Frame — read first (reanchor):** this repo is a **general forensic engine for financial fragility & mispricing across the _whole economy_** — hidden / mismatched / circular leverage and valuation-run-ahead-of-cash-flow, found with **no sector prior**. **AI / data-center is _case zero_, not the object** (the method is sector- and era-agnostic — cf. fiber 1999, shale 2014). **Operating mode: maximum exhaustiveness — broad AND deep, uncapped, ≥ $1M-substance floor, US-primary (international by connectedness-to-core × data-accessibility); acting resource-constrained is NEVER correct; the only stop is physics (data that doesn't publicly exist → estimate it from proxies).** Full scope & doctrine: [total_ecosystem_dive.md](total_ecosystem_dive.md) · [README](../README.md).

Independent orchestrator-side EDGAR pull of the top confirmed survivors (already-distressed + high), to move them off agent-asserted tier. **166 spot-checked; 124 show a distress signal in the actual filings** (going-concern / delisting / default / late-filing / impairment); agent reliability on this sample = **0.747**. Machine-readable: [survivor_filing_verification.json](survivor_filing_verification.json).

| entity | CIK | agent sev | NT late | distress terms found (filing) | verdict |
|---|---|---|:--:|---|---|
| INNOVATE Corp. (NYSE: VATE; former | 0001006837 | already-distressed |  | 10-K 2026-03-26→going_concern,delisting,default,impairment | ✅ |
| Sotherly Hotels Inc. ((XBRL-distre | 0001301236 | already-distressed | Y | 10-K 2026-04-15→delisting,default,impairment; 8-K 2026-03-27→delisting | ✅ |
| System1, Inc. ((XBRL-distressed),  | 0001805833 | already-distressed |  | 10-K 2026-03-11→going_concern,delisting,default,impairment | ✅ |
| Mobile Infrastructure Corp ((XBRL- | 0001847874 | already-distressed |  | 10-K 2026-03-05→going_concern,delisting,default,impairment | ✅ |
| Xerox Holdings Corp ((XBRL-distres | 0001770450 | already-distressed | Y | 10-K 2026-03-17→going_concern,delisting,default,impairment | ✅ |
| MERCER INTERNATIONAL INC. ((XBRL-n | 0001333274 | already-distressed |  | 10-K 2026-02-12→impairment | ✅ |
| Beyond Meat, Inc. (BYND) — CIK 000 | 0001655210 | already-distressed | Y | 10-K 2026-04-09→delisting,default,impairment | ✅ |
| URBAN ONE, INC. (UONE / UONEK; CIK | 0001041657 | already-distressed |  | 10-K 2026-03-20→delisting,default,impairment | ✅ |
| Southland Holdings, Inc. ((XBRL-ne | 0001883814 | already-distressed |  | 10-K 2026-03-26→going_concern,delisting,default | ✅ |
| Local Bounti Corporation/DE (LOCL) | 0001840780 | already-distressed |  | 10-K 2026-03-27→going_concern,delisting,default,impairment | ✅ |
| HERTZ GLOBAL HOLDINGS, INC ((XBRL- | 0001657853 | already-distressed |  | 10-K 2026-02-26→default,impairment | ✅ |
| Maiden Holdings, Ltd. (former NASD | 0001412100 | already-distressed |  | 10-K 2025-03-10→going_concern,default,impairment; 8-K 2025-05-27→delisting | ✅ |
| Fat Brands, Inc ((XBRL-negEBITDA), | 0001705012 | already-distressed |  | 8-K 2026-06-04→bankruptcy | ✅ |
| BEASLEY BROADCAST GROUP INC ((XBRL | 0001099160 | already-distressed | Y | 10-K 2026-04-08→going_concern,delisting,default,impairment | ✅ |
| New Fortress Energy Inc. (NFE) [CI | 0001749723 | already-distressed | Y | 10-K 2026-04-13→going_concern,delisting,default,bankruptcy,impairment | ✅ |
| AEMETIS, INC ((XBRL-negEBITDA), ti | 0000738214 | already-distressed |  | 10-K 2026-03-16→going_concern,default,impairment | ✅ |
| Inotiv, Inc. (NASDAQ: NOTV) — CIK  | 0000720154 | already-distressed |  | 10-K 2025-12-05→going_concern,delisting,default,impairment; 8-K 2026-06-08→delis | ✅ |
| QVC Group, Inc. (QVCAQ) [CIK 00013 | 0001355096 | already-distressed | Y | 10-K 2026-04-15→going_concern,delisting,default,bankruptcy,impairment; 8-K 2026- | ✅ |
| Spirit Aviation Holdings, Inc. (FL | 0001498710 | already-distressed |  | 10-K 2026-03-16→going_concern,delisting,default,bankruptcy,impairment; 8-K 2026- | ✅ |
| SunPower Inc. (Nasdaq: SPWR), CIK  | 0001838987 | already-distressed | Y | 10-K 2026-04-14→going_concern,delisting,default,bankruptcy,impairment | ✅ |
| Ayr Wellness Inc. ((XBRL-negEBITDA | 0001847462 | already-distressed |  | — | ⚠️ none |
| Outlook Therapeutics, Inc. (OTLK)  | 0001649989 | already-distressed |  | — | ⚠️ none |
| Solo Brands, Inc. (SBDS; CIK 00018 | 0001870600 | already-distressed |  | 10-K 2026-03-23→going_concern,delisting,default,bankruptcy,impairment | ✅ |
| GoHealth, Inc. (GOCO) [CIK 0001808 | 0001808220 | already-distressed | Y | 10-K 2026-03-31→going_concern,delisting,default,impairment; 8-K 2026-06-11→going | ✅ |
| Foxx Development Holdings Inc. (Ot | 0002013807 | already-distressed | Y | 10-K 2025-10-15→going_concern,delisting,impairment | ✅ |
| Bausch Health Companies Inc. (Spec | 0000885590 | already-distressed |  | 10-K 2026-02-19→going_concern,default,bankruptcy,impairment | ✅ |
| Hyperscale Data, Inc. (Data center | 0000896493 | already-distressed | Y | — | ✅ |
| Humacyte, Inc. (NASDAQ: HUMA; CIK  | 0001818382 | already-distressed |  | 10-K 2026-03-27→going_concern,default,impairment | ✅ |
| Perfect Moment Ltd. (Other / uncla | 0001849221 | already-distressed |  | 8-K 2026-06-12→delisting | ✅ |
| Celularity Inc (Other / unclassifi | 0001752828 | already-distressed | Y | 10-K 2026-04-30→going_concern,delisting,default,impairment; 8-K 2026-06-12→delis | ✅ |
| NextNRG, Inc. (Nasdaq: NXXT; CIK 0 | 0001817004 | already-distressed | Y | 10-K 2026-04-16→going_concern,delisting,default,impairment | ✅ |
| Royale Energy, Inc. (Power / utili | 0001694617 | already-distressed | Y | 10-K 2025-04-09→going_concern,impairment | ✅ |
| Workhorse Group Inc. (Other / uncl | 0001425287 | already-distressed |  | 10-K 2026-03-31→going_concern,delisting,default,bankruptcy,impairment | ✅ |
| BRC Group Holdings, Inc. (Other /  | 0001464790 | already-distressed | Y | 10-K 2026-03-31→delisting,default,bankruptcy,impairment | ✅ |
| BATTALION OIL CORP ((XBRL-distress | 0001282648 | high |  | — | ⚠️ none |
| RCI Hospitality Holdings, Inc. (NA | 0000935419 | high | Y | 10-K 2026-03-19→delisting,default,impairment | ✅ |
| ProFrac Holding Corp. ((XBRL-distr | 0001881487 | high |  | 10-K 2026-03-13→delisting,default,bankruptcy,impairment | ✅ |
| Reading International Inc (RDI) —  | 0000716634 | high |  | 10-K 2026-03-31→going_concern,default,impairment | ✅ |
| Cogent Communications Holdings, In | 0001158324 | high |  | 10-K 2026-02-20→default | ✅ |
| Accuray Inc (NASDAQ: ARAY), CIK 00 | 0001138723 | high | Y | — | ✅ |
| Gray Media, Inc. (NYSE: GTN; forme | 0000043196 | high |  | 10-K 2026-02-26→bankruptcy,impairment | ✅ |
| LIFECORE BIOMEDICAL, INC. \\DE\\ ( | 0001005286 | high |  | 10-K 2025-08-07→going_concern,delisting,default,impairment | ✅ |
| AMC ENTERTAINMENT HOLDINGS, INC. ( | 0001411579 | high |  | 10-K 2026-02-23→delisting,default,bankruptcy,impairment | ✅ |
| Virgin Galactic Holdings, Inc ((XB | 0001706946 | high |  | 10-K 2026-03-30→going_concern,delisting,default | ✅ |
| GrafTech International Ltd (EAF),  | 0000931148 | high |  | 10-K 2026-02-13→delisting,default,impairment | ✅ |
| Wheels Up Experience Inc. ((XBRL-n | 0001819516 | high |  | 10-K 2026-03-10→delisting,default,impairment | ✅ |
| JELD-WEN Holding, Inc. ((XBRL-negE | 0001674335 | high |  | 10-K 2026-02-23→default,impairment | ✅ |
| FMC CORP ((XBRL-negEBITDA), tier n | 0000037785 | high |  | 8-K 2026-06-05→default | ✅ |
| ChargePoint Holdings, Inc. ((XBRL- | 0001777393 | high |  | 10-K 2026-04-02→delisting,default,impairment | ✅ |
| Lucid Group, Inc. (NASDAQ: LCID) — | 0001811210 | high |  | — | ⚠️ none |
| Babcock & Wilcox Enterprises, Inc. | 0001630805 | high |  | 10-K 2026-03-16→going_concern,default,bankruptcy,impairment | ✅ |
| Rapid Micro Biosystems, Inc. (NASD | 0001380106 | high |  | 10-K 2026-03-12→delisting,default,impairment | ✅ |
| W&T Offshore Inc (NYSE: WTI), CIK  | 0001288403 | moderate |  | 10-K 2026-03-16→default | ✅ |
| Altisource Portfolio Solutions S.A | 0001462418 | moderate |  | 10-K 2026-03-04→going_concern,default,impairment | ✅ |
| Townsquare Media, Inc. ((XBRL-dist | 0001499832 | moderate |  | 10-K 2026-03-16→going_concern,default,impairment | ✅ |
| RideNow Group, Inc. ((XBRL-distres | 0001596961 | moderate |  | 10-K 2026-03-13→going_concern,default,impairment | ✅ |
| Hyster-Yale, Inc. (NYSE: HY) — CIK | 0001173514 | moderate |  | — | ⚠️ none |
| Xponential Fitness, Inc. (XPOF) [C | 0001802156 | moderate |  | 10-K 2026-03-04→delisting,default,impairment | ✅ |
| TEAM, Inc. (NYSE: TISI) — CIK 0000 | 0000318833 | moderate |  | 10-K 2026-03-12→delisting,default,impairment | ✅ |
| Bridger Aerospace Group Holdings,  | 0001941536 | moderate |  | 10-K 2026-03-06→going_concern,delisting,default,impairment | ✅ |
| Compass Diversified Holdings (NYSE | 0001345126 | moderate |  | 10-K 2026-02-27→going_concern,delisting,default,bankruptcy,impairment | ✅ |
| NEWELL BRANDS INC. ((XBRL-distress | 0000814453 | moderate |  | — | ⚠️ none |
| Cresco Labs Inc. ((XBRL-distressed | 0001832928 | moderate |  | — | ⚠️ none |
| CENTURY CASINOS INC /CO/ ((XBRL-di | 0000911147 | moderate | Y | 10-K 2026-03-18→impairment | ✅ |
| Huntsman CORP ((XBRL-distressed),  | 0001307954 | moderate |  | 10-K 2026-02-18→impairment | ✅ |
| Spruce Power Holding Corp (NYSE: S | 0001772720 | moderate |  | 10-K 2026-03-31→going_concern,delisting,default,impairment | ✅ |
| Sinclair, Inc. ((XBRL-distressed), | 0001971213 | moderate |  | — | ⚠️ none |
| Clear Channel Outdoor Holdings, In | 0001334978 | moderate |  | 10-K 2026-02-26→delisting,impairment | ✅ |
| Green Plains Inc. (NASDAQ: GPRE) — | 0001309402 | moderate |  | 10-K 2026-02-10→default,impairment | ✅ |
| Bausch & Lomb Corp ((XBRL-distress | 0001860742 | moderate |  | — | ⚠️ none |
| KORE Group Holdings, Inc. (NYSE: K | 0001855457 | moderate |  | 10-K 2026-03-31→delisting,default,impairment | ✅ |
| Advantage Solutions Inc. (NASDAQ:  | 0001776661 | moderate |  | — | ⚠️ none |
| loanDepot, Inc. ((XBRL-distressed) | 0001831631 | moderate |  | 10-K 2026-03-12→default,impairment | ✅ |
| HARROW, INC. ((XBRL-distressed), t | 0001360214 | moderate |  | 10-K 2026-03-02→going_concern,delisting,impairment | ✅ |
| AIR T INC ((XBRL-distressed), tier | 0000353184 | moderate |  | — | ⚠️ none |
| Caesars Entertainment, Inc. ((XBRL | 0001590895 | moderate |  | 10-K 2026-02-17→impairment | ✅ |
| MarineMax, Inc. (NYSE: HZO) — CIK  | 0001057060 | moderate |  | 10-K 2025-11-17→impairment | ✅ |
| NN, Inc. (NASDAQ: NNBR) — CIK 0000 | 0000918541 | moderate |  | 10-K 2026-03-04→default,impairment | ✅ |
| WOLFSPEED, INC. ((XBRL-negEBITDA), | 0000895419 | moderate |  | — | ⚠️ none |
| Six Flags Entertainment Corporatio | 0001999001 | moderate |  | 10-K 2026-02-26→default,impairment | ✅ |
| Skillsoft Corp. (NYSE: SKIL) — CIK | 0001774675 | moderate |  | 10-K 2026-04-07→delisting,default,impairment | ✅ |
| EchoStar CORP ((XBRL-negEBITDA), t | 0001415404 | moderate |  | 10-K 2026-03-02→going_concern,delisting,default,bankruptcy,impairment; 8-K 2026- | ✅ |
| Trump Media & Technology Group Cor | 0001849635 | moderate |  | — | ⚠️ none |
| ContextLogic Holdings Inc. (LOGC)  | 0002064307 | moderate |  | 10-K 2026-03-05→going_concern,delisting,default,impairment | ✅ |
| Fortrea Holdings Inc. (FTRE) — CIK | 0001965040 | moderate |  | 10-K 2026-02-26→default,impairment | ✅ |
| Core Scientific, Inc./tx (CORZ) —  | 0001839341 | moderate |  | — | ⚠️ none |
| Vroom, Inc. ((XBRL-negEBITDA), tie | 0001580864 | moderate |  | 10-K 2026-03-26→going_concern,delisting,default,bankruptcy,impairment | ✅ |
| Alexandria Real Estate Equities, I | 0001035443 | moderate |  | — | ⚠️ none |
| OneWater Marine Inc. ((XBRL-negEBI | 0001772921 | moderate |  | 10-K 2025-12-15→impairment | ✅ |
| Keel Infrastructure Corp. ((XBRL-n | 0001812477 | moderate |  | 10-K 2026-03-31→delisting,bankruptcy,impairment; 8-K 2026-06-10→default | ✅ |
| PAR Technology Corp (NYSE: PAR; CI | 0000708821 | moderate |  | — | ⚠️ none |
| CLEVELAND-CLIFFS INC. ((XBRL-negEB | 0000764065 | moderate |  | 10-K 2026-02-09→going_concern,default,impairment | ✅ |
| Krispy Kreme, Inc. ((XBRL-negEBITD | 0001857154 | moderate |  | — | ⚠️ none |
| Kosmos Energy Ltd. (NYSE/LSE: KOS) | 0001509991 | moderate |  | 10-K 2026-03-02→default,impairment | ✅ |
| Cango Inc. (NYSE: CANG; CIK 000172 | 0001725123 | moderate |  | 20-F 2026-04-10→delisting,impairment | ✅ |
| PACIFIC BIOSCIENCES OF CALIFORNIA, | 0001299130 | moderate |  | 10-K 2026-02-25→default,impairment | ✅ |
| Alight, Inc. / Delaware ((XBRL-neg | 0001809104 | moderate |  | — | ⚠️ none |
| Repay Holdings Corp (RPAY) — CIK 0 | 0001720592 | moderate |  | — | ⚠️ none |
| PENN Entertainment, Inc. ((XBRL-ne | 0000921738 | moderate |  | 10-K 2026-02-26→default,impairment | ✅ |
| Under Armour, Inc. (UAA / UA; CIK  | 0001336917 | moderate |  | 10-K 2026-05-19→default,impairment | ✅ |
| Cipher Digital Inc. ((XBRL-negEBIT | 0001819989 | moderate |  | — | ⚠️ none |
| LIVEPERSON INC ((XBRL-negEBITDA),  | 0001102993 | moderate |  | 10-K 2026-03-16→delisting,default,impairment | ✅ |
| Traeger, Inc. ((XBRL-negEBITDA), t | 0001857853 | moderate |  | 10-K 2026-03-06→delisting,default,impairment | ✅ |
| TERAWULF INC. (WULF) [CIK 00010833 | 0001083301 | moderate |  | — | ⚠️ none |
| Rivian Automotive, Inc. / DE ((XBR | 0001874178 | moderate |  | — | ⚠️ none |
| Strategy Inc ((XBRL-negEBITDA), ti | 0001050446 | moderate |  | — | ⚠️ none |
| Bally's Corp ((XBRL-negEBITDA), ti | 0001747079 | moderate | Y | 10-K 2026-03-23→default,impairment | ✅ |
| Grocery Outlet Holding Corp. ((XBR | 0001771515 | moderate |  | — | ⚠️ none |
| Sarepta Therapeutics, Inc. (NASDAQ | 0000873303 | moderate |  | 10-K 2026-03-02→default,bankruptcy,impairment | ✅ |
| Celanese Corp ((XBRL-negEBITDA), t | 0001306830 | moderate |  | 10-K 2026-02-24→default,impairment | ✅ |
| Leslie's, Inc. (NASDAQ: LESL; CIK  | 0001821806 | moderate |  | — | ⚠️ none |
| XBP Global Holdings, Inc. ((XBRL-n | 0001839530 | moderate |  | 10-K 2026-03-31→delisting,default,bankruptcy,impairment | ✅ |
| MARA Holdings, Inc. (NASDAQ: MARA; | 0001507605 | moderate |  | 10-K 2026-03-02→going_concern,impairment | ✅ |
| Sabre GLBL Inc. (operating subsidi | 0001597033 | moderate |  | — | ⚠️ none |
| Commercial Vehicle Group, Inc. (Ot | 0001290900 | moderate |  | 10-K 2026-03-10→default,impairment | ✅ |
| Getty Images Holdings, Inc. (NYSE: | 0001898496 | moderate |  | — | ⚠️ none |
| Venture Global, Inc. (NYSE: VG) [C | 0002007855 | moderate |  | — | ⚠️ none |
| BTCS Inc. (Other / unclassified, t | 0001436229 | moderate |  | 10-K 2026-03-26→going_concern,default,impairment | ✅ |
| Applied Digital Corp. (NASDAQ: APL | 0001144879 | moderate |  | — | ⚠️ none |
| Arbor Realty Trust Inc (NYSE: ABR) | 0001253986 | moderate |  | — | ⚠️ none |
| Borr Drilling Ltd (Other / unclass | 0001715497 | moderate |  | 20-F 2026-03-26→going_concern,delisting,default,bankruptcy,impairment | ✅ |
| NEXPOINT DIVERSIFIED REAL ESTATE T | 0001356115 | moderate |  | — | ⚠️ none |
| ORACLE CORP (Other / unclassified, | 0001341439 | moderate |  | — | ⚠️ none |
| SEACOR Marine Holdings Inc. (Other | 0001690334 | moderate |  | 10-K 2026-02-25→default,impairment | ✅ |
| Goldman Sachs BDC, Inc. (GSBD) [CI | 0001572694 | moderate |  | 10-K 2026-02-26→default | ✅ |
| SelectQuote, Inc. ((XBRL-distresse | 0001794783 | low |  | 10-K 2025-08-21→default,impairment | ✅ |
| Baidu, Inc. ((XBRL-distressed), ti | 0001329099 | low |  | 20-F 2026-03-17→going_concern,delisting,default,impairment | ✅ |
| LEE ENTERPRISES, Inc ((XBRL-distre | 0000058361 | low |  | — | ⚠️ none |
| Consumer Portfolio Services, Inc.  | 0000889609 | low |  | 10-K 2026-03-16→default | ✅ |
| Finance of America Companies Inc.  | 0001828937 | low |  | 10-K 2026-03-13→delisting,default,bankruptcy,impairment | ✅ |
| NGL Energy Partners LP ((XBRL-dist | 0001504461 | low |  | 10-K 2026-05-28→delisting,default,impairment; 8-K 2026-03-12→default | ✅ |
| USA TODAY Co., Inc. ((XBRL-distres | 0001579684 | low |  | 10-K 2026-02-26→delisting,impairment | ✅ |
| AMC Global Media Inc. ((XBRL-distr | 0001514991 | low |  | 10-K 2026-02-11→default,impairment | ✅ |
| INTERGROUP CORP ((XBRL-distressed) | 0000069422 | low | Y | 10-K 2025-09-30→going_concern,delisting,default,impairment | ✅ |
| Cable One, Inc. ((XBRL-distressed) | 0001632127 | low |  | 10-K 2026-02-26→default,impairment | ✅ |
| Lionsgate Studios Corp. ((XBRL-dis | 0002052959 | low |  | 10-K 2026-05-27→default,impairment | ✅ |
| LIFETIME BRANDS, INC ((XBRL-distre | 0000874396 | low |  | 10-K 2026-03-12→default,bankruptcy,impairment | ✅ |
| Nebius Group N.V. ((XBRL-negEBITDA | 0001513845 | low |  | 20-F 2026-04-30→going_concern,delisting,impairment | ✅ |
| NEXTNAV INC. ((XBRL-negEBITDA), ti | 0001865631 | low |  | — | ⚠️ none |
| NeoGenomics Inc (NASDAQ: NEO), CIK | 0001077183 | low |  | 10-K 2026-02-17→default,impairment | ✅ |
| MAXLINEAR, INC ((XBRL-negEBITDA),  | 0001288469 | low |  | — | ⚠️ none |
| Polaris Inc. (NYSE: PII) [CIK 0000 | 0000931015 | low |  | 10-K 2026-02-13→default,impairment | ✅ |
| Alphatec Holdings, Inc. (ATEC) [CI | 0001350653 | low |  | 10-K 2026-02-24→default,impairment | ✅ |
| DNOW Inc. ((XBRL-negEBITDA), tier  | 0001599617 | low |  | 10-K 2026-02-26→impairment | ✅ |
| INTEGRA LIFESCIENCES HOLDINGS CORP | 0000917520 | low |  | 10-K 2026-02-26→default,impairment | ✅ |
| QuidelOrtho Corp ((XBRL-negEBITDA) | 0001906324 | low |  | — | ⚠️ none |
| Fox Factory Holding Corp (FOXF), C | 0001424929 | low |  | 10-K 2026-02-27→default,impairment | ✅ |
| HELEN OF TROY LTD ((XBRL-negEBITDA | 0000916789 | low |  | 10-K 2026-04-23→default,impairment | ✅ |
| Sunrun Inc. (RUN) — CIK 0001469367 | 0001469367 | low |  | — | ⚠️ none |
| Mativ Holdings, Inc. ((XBRL-negEBI | 0001000623 | low |  | 10-K 2026-02-26→default,impairment | ✅ |
| Belpointe PREP, LLC (NYSE American | 0001807046 | low |  | 10-K 2026-03-20→default,impairment | ✅ |
| WESTLAKE CORP ((XBRL-negEBITDA), t | 0001262823 | low |  | 10-K 2026-02-26→impairment | ✅ |
| Bumble Inc. ((XBRL-negEBITDA), tie | 0001830043 | low |  | — | ⚠️ none |
| DENTSPLY SIRONA Inc. (XRAY) — CIK  | 0000818479 | low |  | — | ⚠️ none |
| ZIPRECRUITER, INC. (NYSE: ZIP) | C | 0001617553 | low |  | — | ⚠️ none |
| PERRIGO Co plc ((XBRL-negEBITDA),  | 0001585364 | low |  | — | ⚠️ none |
| NextDecade Corp (NASDAQ: NEXT) — p | 0001612720 | low |  | 10-K 2026-03-02→going_concern,delisting,default | ✅ |
| Exodus Movement, Inc. (Other / unc | 0001821534 | low |  | 10-K 2026-03-11→impairment | ✅ |
| BLACKSTONE MORTGAGE TRUST, INC. (M | 0001061630 | low |  | 10-K 2026-02-11→default,impairment | ✅ |
| Energy Vault Holdings, Inc. (Power | 0001828536 | low | Y | 10-K 2026-03-18→going_concern,delisting,default,impairment | ✅ |
| HOVNANIAN ENTERPRISES INC (Other / | 0000357294 | low |  | 10-K 2025-12-22→default,impairment | ✅ |
| MGM Resorts International (NYSE: M | 0000789570 | low |  | 10-K 2026-02-11→default,impairment; 8-K 2026-05-14→default | ✅ |
| Gevo, Inc. (Other / unclassified,  | 0001392380 | low |  | — | ⚠️ none |
| Navient Corp (NAVI; CIK 0001593538 | 0001593538 | low |  | 10-K 2026-02-26→default,impairment | ✅ |
| Global Net Lease, Inc. (NYSE: GNL) | 0001526113 | low |  | 10-K 2026-02-25→delisting,default,impairment | ✅ |
| Hut 8 Corp. (NASDAQ/TSX: HUT) — CI | 0001964789 | low |  | 10-K 2026-02-25→delisting,default,impairment | ✅ |

*Keyword-tier verification (presence of distress language in the latest 10-K/20-F/8-K + NT late-filing flag), not a full re-audit. '⚠️ none' means the headline distress wasn't found in the most-recent primary doc — flag for a deeper read, not an automatic refutation.*
