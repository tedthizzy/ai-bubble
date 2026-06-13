# Survivor filing verification (orchestrator-pulled EDGAR)

> **⚓ Frame — read first (reanchor):** this repo is a **general forensic engine for financial fragility & mispricing across the _whole economy_** — hidden / mismatched / circular leverage and valuation-run-ahead-of-cash-flow, found with **no sector prior**. **AI / data-center is _case zero_, not the object** (the method is sector- and era-agnostic — cf. fiber 1999, shale 2014). **Operating mode: maximum exhaustiveness — broad AND deep, uncapped, ≥ $1M-substance floor, US-primary (international by connectedness-to-core × data-accessibility); acting resource-constrained is NEVER correct; the only stop is physics (data that doesn't publicly exist → estimate it from proxies).** Full scope & doctrine: [total_ecosystem_dive.md](total_ecosystem_dive.md) · [README](../README.md).

Independent orchestrator-side EDGAR pull of the top confirmed survivors (already-distressed + high), to move them off agent-asserted tier. **9 spot-checked; 9 show a distress signal in the actual filings** (going-concern / delisting / default / late-filing / impairment); agent reliability on this sample = **1.0**. Machine-readable: [survivor_filing_verification.json](survivor_filing_verification.json).

| entity | CIK | agent sev | NT late | distress terms found (filing) | verdict |
|---|---|---|:--:|---|---|
| Bausch Health Companies Inc. (Spec | 0000885590 | already-distressed |  | 10-K 2026-02-19→going_concern,default,bankruptcy,impairment | ✅ |
| Hyperscale Data, Inc. (Data center | 0000896493 | already-distressed | Y | — | ✅ |
| Humacyte, Inc. (NASDAQ: HUMA; CIK  | 0001818382 | already-distressed |  | 10-K 2026-03-27→going_concern,default,impairment | ✅ |
| Celularity Inc (Other / unclassifi | 0001752828 | already-distressed | Y | 10-K 2026-04-30→going_concern,delisting,default,impairment; 8-K 2026-06-12→delis | ✅ |
| NextNRG, Inc. (Nasdaq: NXXT; CIK 0 | 0001817004 | already-distressed | Y | 10-K 2026-04-16→going_concern,delisting,default,impairment | ✅ |
| Lexmark, as US holdings, Lexmark I | 0001770450 | already-distressed | Y | 10-K 2026-03-17→going_concern,delisting,default,impairment | ✅ |
| Babcock & Wilcox Enterprises, Inc. | 0001630805 | high |  | 10-K 2026-03-16→going_concern,default,bankruptcy,impairment | ✅ |
| Rapid Micro Biosystems, Inc. (NASD | 0001380106 | high |  | 10-K 2026-03-12→delisting,default,impairment | ✅ |
| AMC ENTERTAINMENT HOLDINGS, INC. ( | 0001411579 | high |  | 10-K 2026-02-23→delisting,default,bankruptcy,impairment | ✅ |

*Keyword-tier verification (presence of distress language in the latest 10-K/20-F/8-K + NT late-filing flag), not a full re-audit. '⚠️ none' means the headline distress wasn't found in the most-recent primary doc — flag for a deeper read, not an automatic refutation.*
