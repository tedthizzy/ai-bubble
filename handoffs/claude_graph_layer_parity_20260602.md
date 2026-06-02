# Graph-layer parity harness (backlog #8/#2) — capital-graph vs contract-graph AI-infra mismatch EXPLAINED

**Base:** current main `9f76eed`, report `BURRY_REPORT_EvidenceGated_20260602-1806.json`. READ-ONLY; no prod writes.
**Codex import note:** imported on `c092b91`; key graph-parity values were rechecked
against `BURRY_REPORT_EvidenceGated_20260602-1816.json` and still match within
rounding.
**Deliverable:** `handoffs/fixtures/graph_layer_parity_20260602.csv` (5 rows: metric, layer, value, basis, why it
differs, parity rule, test). Impact: **graph validity / evidence-gate confidence.** No EDGAR needed; all values from
the report JSON.

## The discrepancy (this is what Codex flagged)
| metric | capital_exposure_graph | contract_contagion_paths | factor |
|---|---|---|---|
| total notional | **$0.864T** (deduped edges) | **$44.591T** (8,749 paths) | 51x |
| AI-infra notional | **$4.75B** (debt-edge AI slice) | **$1.919T** (453 AI paths) | 404x |

## Why — it is STRUCTURAL, not a data error
1. **Path-multiplicity (the dominant cause).** `contract_contagion_paths` sums notional across **paths**, not
   distinct edges: 8,749 paths at avg **$5.10B/path** = $44.591T. A single high-notional node (e.g. a $44B obligor)
   sits on many paths and its notional is counted **once per path**. So $44.591T is path-enumeration, NOT exposure.
   The AI figure is the same: 453 AI-relevant paths × avg $4.24B = $1.919T (path-summed).
2. **Different scope.** Capital graph = deduped **debt/financing** edges only ($0.864T). Contract graph scans
   **195,896 contract edges** incl. PPA / ownership / guarantee / collateral / SPV edges — a far wider universe.
3. **Different AI-tagging granularity.** Capital tags AI-infra narrowly (a debt edge explicitly AI-tagged → $4.75B).
   Contract tags any **path touching an AI-relevant node** as AI-relevant → far more inclusive.

## Reconciliation — neither graph figure is the headline; the deduped distinct one is
```
$4.75B            <    $827.7B                  <    $1.919T
(capital debt-edge,    (materiality DISTINCT         (contract path-summed,
 too NARROW)            AI-relevant pending capital   multiplicity-INFLATED)
                        -- DEFENSIBLE headline)
```
`review_queue_pending_ai_infra_relevant_capital_distinct_notional_amount_usd = $827.7B` is the deduped distinct
AI-relevant notional and is the figure a skeptical reader should be pointed to. The two graph layers are
**diagnostic surfaces**, not headline exposure: the capital $4.75B understates (debt-edge only), the contract
$1.919T overstates (path-summed).

## Parity rules / proposed invariants (in fixture, with test names)
1. Path-summed totals ($44.591T, $1.919T) MUST be rendered with a **"path-summed (multiplicity-inflated), not
   exposure"** label and never compared 1:1 to deduped notional. (`test_contract_path_total_labeled_path_summed_not_exposure`)
2. `capital_edge_notional` ($0.864T) is the deduped lower bound and must be `<=` the contract path-summed total.
   (`test_capital_edge_notional_is_deduped_lower_bound`)
3. The **headline** AI-infra exposure must use the materiality DISTINCT basis ($827.7B), not either graph layer.
   (`test_ai_infra_headline_uses_distinct_materiality_basis`)
4. Each AI-infra figure must carry its basis tag (debt-edge / path-summed / distinct) so the 404x gap is never
   read as a contradiction. (`test_ai_infra_figures_carry_basis_label`)

## Verified vs proposed
- VERIFIED: all values + path counts (8,749 paths, 453 AI paths, 195,896 edges scanned) from the 1806 report.
- PROPOSED: the parity invariants/tests + the recommendation to headline the $827.7B distinct basis. This is a
  **graph-validity guardrail** (explains a real cross-layer discrepancy); no metric change.
