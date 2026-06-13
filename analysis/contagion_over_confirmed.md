# Contagion linkage over the confirmed-fragility set

> **⚓ Frame — read first (reanchor):** this repo is a **general forensic engine for financial fragility & mispricing across the _whole economy_** — hidden / mismatched / circular leverage and valuation-run-ahead-of-cash-flow, found with **no sector prior**. **AI / data-center is _case zero_, not the object** (the method is sector- and era-agnostic — cf. fiber 1999, shale 2014). **Operating mode: maximum exhaustiveness — broad AND deep, uncapped, ≥ $1M-substance floor, US-primary (international by connectedness-to-core × data-accessibility); acting resource-constrained is NEVER correct; the only stop is physics (data that doesn't publicly exist → estimate it from proxies).** Full scope & doctrine: [total_ecosystem_dive.md](total_ecosystem_dive.md) · [README](../README.md).

Cross-references the **174 confirmed-fragility entities** against the on-disk capital-exposure + contract graphs. **96 appear in the graph at all (match rate 0.552)** — most confirmed names come from the XBRL breadth layer and are NOT in the deal-corpus graph, so absence here is a coverage gap, not proof of no linkage. Machine-readable: [contagion_over_confirmed.json](contagion_over_confirmed.json).

- **Direct confirmed→confirmed edges:** 1
- **Shared-counterparty hubs (≥2 confirmed names depend on the same node):** 5

## Shared-counterparty contagion hubs (confirmed names exposed to the same node)

| counterparty | # confirmed | confirmed names |
|---|---:|---|
| morgan stanley | 2 | nebius group n v, terawulf inc |
| goldman sachs | 2 | hut 8 corp, nebius group n v |
| nvidia | 2 | hut 8 corp, nebius group n v |
| google alphabet | 2 | hut 8 corp, terawulf inc |
| fluidstack | 2 | hut 8 corp, terawulf inc |

**Reading:** LOW interconnection among confirmed-fragile names supports the broadly-distributed / idiosyncratic reading (no single contagion cascade); HIGH shared-counterparty clustering would indicate systemic contagion channels.

*Limit: this traverses only the deal-corpus capital + contract graphs (small, AI-seeded). The 425k-node LEI ownership graph and the full economy-wide contagion traversal are the next non-LLM extension. Match rate is the honest coverage number.*
