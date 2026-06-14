# EIA-860M generator buildout — national operating vs planned vs canceled (keyless)

> **⚓ Frame — read first (reanchor):** this repo is a **general forensic engine for financial fragility & mispricing across the _whole economy_** — hidden / mismatched / circular leverage and valuation-run-ahead-of-cash-flow, found with **no sector prior**. **AI / data-center is _case zero_, not the object** (the method is sector- and era-agnostic — cf. fiber 1999, shale 2014). **Operating mode: maximum exhaustiveness — broad AND deep, uncapped, ≥ $1M-substance floor, US-primary (international by connectedness-to-core × data-accessibility); acting resource-constrained is NEVER correct; the only stop is physics (data that doesn't publicly exist → estimate it from proxies).** Full scope & doctrine: [total_ecosystem_dive.md](total_ecosystem_dive.md) · [README](../README.md).

Ingests EIA-860M (every US generator + status), keyless. **Operating 1,392,666 MW** vs **planned 288,406 MW** (= 20.7% of the operating fleet in the pipeline) vs **canceled 181,264 MW** vs **retired 294,489 MW** — the national buildout-vs-attrition picture for the power layer feeding AI demand. Machine-readable: [eia_860m_buildout.json](eia_860m_buildout.json).

| sheet | generators | Σ MW | MW column |
|---|---:|---:|---|
| Operating | 27972 | 1,392,666 | Nameplate Capacity (MW) |
| Planned | 2257 | 288,406 | Nameplate Capacity (MW) |
| Retired | 7255 | 294,489 | Nameplate Capacity (MW) |
| Canceled or Postponed | 1714 | 181,264 | Nameplate Capacity (MW) |
| Operating_PR | 229 | 6,474 | Nameplate Capacity (MW) |
| Planned_PR | 6 | 177 | Nameplate Capacity (MW) |
| Retired_PR | 11 | 130 | Nameplate Capacity (MW) |

*Complements CAISO's ~11x withdrawn:completed queue ratio: EIA-860M is the *built/building* reality (operating + firmly-planned), the queue is the *aspirational* funnel. Together they bound the AI-power buildout's demand-ahead-of-delivery gap with hard MW.*
