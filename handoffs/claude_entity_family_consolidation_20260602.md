# Entity-family / SPV consolidation map (backlog #20) — metric vs graph-display separation

**Base:** current main `9f76eed`, survivor metric 1,380 / $3,742.4B. READ-ONLY; no prod writes.
**Codex import note:** imported on `c092b91` as a graph-display guardrail pack;
its negative finding is not a production metric-dedupe change.
**Deliverable:** `handoffs/fixtures/entity_family_consolidation_20260602.csv` (4 families: member nodes, metric
rows, **metric-treatment verdict**, graph-surface treatment, over-count risk, rule). Impact: **final metric (negative
result) + graph validity.** Closes the entity-family loop my utility/ratepayer pack opened.

## Headline (a deliberately NEGATIVE result for the metric)
The utility entity-family fanout that inflates the **graph bearer/obligor display** ($254.5B across 10 utility
nodes) does **NOT** translate into a material **final-metric** over-count. Verified per family:
- **ENTERGY** — 13 survivor rows / $39.0B across 4 opcos (LA/AR/MS/TX). Each opco issues its **own first-mortgage
  bonds under distinct SEC accessions** (Entergy Louisiana alone has 4 separate filings). These are genuinely
  separate obligations — **correct in the metric; do NOT collapse.** The 5-node ($142.3B) "family exposure" only
  exists in the raw obligor ranking (parent + 4 opcos double-surfaced).
- **SOUTHERN** — 10 rows / $81.3B. GA Power's $22.41B DOE loan + Southern Co's notes are distinct. **One real
  over-count signal:** two identical **$18.40B Georgia Power** rows (accessions …0125000028 and …0125000002) =
  a likely **cross-filing duplicate of a total-long-term-debt figure** — but that's the rollup/cross-filing class
  already in my flags, not affiliate fanout.
- **NEXTERA / XCEL** — graph-only alias/name-variant duplicates (NEE=NEE Capital=NextEra; "Xcel … a Minnesota
  corporation" = Xcel). No metric impact.

## So the fix is on the GRAPH DISPLAY, not the metric
| family | metric | graph display fix |
|---|---|---|
| Entergy | keep 4 opcos distinct | collapse Corp+opcos to one family node (don't sum opco debt) |
| Southern | keep distinct (verify GA Power 2×$18.40B cross-filing dup) | collapse parent/sub same-figure |
| NextEra | n/a | alias-normalize NEE/NEE Capital → NextEra |
| Xcel | n/a | normalize ", a <State> corporation" name-suffix |

## Rules (in fixture, for a graph-side consolidation pass)
1. Utility opco first-mortgage bonds are separate obligations — **never collapse in the metric, never sum as
   "family exposure."**
2. Alias-normalize holdco aliases (NEE/NEE Capital→NextEra) and ", a <State> corporation" name-suffix variants
   before ranking bearers/obligors.
3. Collapse parent+subsidiary nodes that surface the **same** figure (Southern Co / Georgia Power $22.97B).
4. Flag identical-amount same-entity rows across **different accessions** for the existing cross-filing dedup
   (the GA Power 2×$18.40B case).

## Verified vs proposed
- VERIFIED: the survivor row counts / amounts / per-opco distinct accessions (from the loader + decisions CSV);
  the negative result (no material utility affiliate-fanout in the metric).
- PROPOSED: the graph-side consolidation rules + the GA Power cross-filing-dup check. No metric change recommended
  — this lane's value is the **guardrail** (proving the metric is already correct here) + the display cleanup.
