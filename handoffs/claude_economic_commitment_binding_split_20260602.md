# Economic-commitment binding-vs-framework split (Codex backlog: split binding from frameworks/LOIs)

**Base:** issuer filings + press. READ-ONLY. **Deliverable:**
`handoffs/fixtures/economic_commitment_binding_split_20260602.csv`. **Impact: size + contagion + report language.**
Separates the headline trillion-dollar AI "commitments" into BINDING vs FRAMEWORK/LOI — the perceived bubble size is
heavily inflated by non-binding announcements.

## The finding: the mega AI commitments are mostly NOT binding
| commitment | headline | binding status |
|---|---|---|
| OpenAI total capex | $1.4T | **FRAMEWORK** — OpenAI itself reset to **~$600B by 2030**; the $1.4T bundles Azure/AWS/Oracle/CoreWeave spend, not OpenAI's own obligation; HSBC says OpenAI must find $207bn |
| OpenAI-Oracle cloud | $300B (4.5GW) | **FRAMEWORK** — "no binding SEC-grade disclosure published" |
| NVIDIA-OpenAI | $100B / 10GW | **NON-BINDING LOI + CIRCULAR** — explicit letter of intent; NVIDIA invests "as systems deployed" (funds OpenAI to buy NVIDIA) |
| OpenAI-Broadcom | 10GW | **FRAMEWORK** partnership |
| OpenAI-AMD | 6GW (tens of $B) | **ANNOUNCEMENT + warrants** (AMD gave OpenAI ~160M-share warrants) |
| Stargate (OpenAI/SoftBank/Oracle/MGX) | $500B / ~7GW | **MOSTLY LOI/performance obligations, not executed contracts** — delayed by partner control disputes; Abilene 1.2GW live |
| **OpenAI-CoreWeave** | **$22.4B** | **BINDING take-or-pay** (CoreWeave filings) — backs CoreWeave's secured debt |
| **Microsoft-OpenAI** | **$13B** | **BINDING equity** (10-K) |

## Why this matters (size + contagion + report wording)
- **Size:** the popularly-cited "trillions of AI commitments" are **announcement/LOI scale, not contractual.** The forensic
  engine correctly excludes them from the $3.65T committed-DEBT metric (they aren't debt instruments) — but the REPORT
  should explicitly note that the headline AI-commitment trillions are **framework-inflated**, distinct from the
  evidence-gated committed-debt figure. (Ties to the report-language lane.)
- **Contagion:** the binding edges are the dangerous ones — **OpenAI-CoreWeave $22.4B take-or-pay** is binding and backs
  CoreWeave's secured debt, so OpenAI's solvency transmits directly to CoreWeave's creditors. The NVIDIA $100B LOI is
  non-binding but **circular** (NVIDIA→OpenAI→buys NVIDIA), a round-trip flag (see `claude_circular_financing_map`).
- **The credibility gap:** OpenAI walking $1.4T → $600B is itself the tell — the commitments flex with narrative, which
  is the opposite of binding.

## Classification rule (for the engine)
- **BINDING** = executed take-or-pay / credit agreement / equity stake with filing evidence (CoreWeave $22.4B, MSFT $13B)
  → may anchor a contract/contagion edge.
- **FRAMEWORK/LOI/announcement** (Oracle $300B, NVIDIA $100B, Broadcom, AMD, Stargate, OpenAI $1.4T) → **must NOT** be
  counted as committed obligation; tag `aspirational/framework`, keep in a separate non-summing tier with a
  contamination guard. Negative control: do not let a press "partnership" headline create a committed-debt or
  contracted-revenue row.

## Verified vs proposed
- VERIFIED: the binding status as reported (OpenAI $1.4T→$600B reset; NVIDIA explicit LOI; Oracle no-binding-SEC; Stargate
  LOI/delayed; CoreWeave $22.4B + MSFT $13B binding per filings).
- PROPOSED: the binding/framework classification rule + the report-wording recommendation. The exact contractual terms of
  Oracle $300B / Stargate are not publicly disclosed (flagged) — classified framework precisely because no binding
  disclosure exists, not fabricated.
