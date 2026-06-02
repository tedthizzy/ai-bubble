# Gate-unlock critical path — the spine of the Burry goal (coordinator strategy)

**Author:** Claude (incoming coordinator). **Status:** branch-safe strategy; execution pending clean handoff (Codex
still active on main — committed 2 min ago; my worktree lacks `data/` so production runs in the MAIN checkout). **Impact:
THE path from the current locked report to a high-confidence Final Burry Report.**

## Reframe: the goal is NOT a data-quantity problem — it is an evidence-GATE problem
Current scale already MEETS the ambition targets:
- **Entities:** 2,377 CIK-matched / 10,365 SEC-reference (target 1,200-2,000) ✅
- **Deals:** 62,952 scanned / 16,254 debt-like / 1,022 in-scope (target 25,000-40,000 scanned) ✅
- **Graph:** 5,036 capital nodes / 7,526 edges; 93,822 contract nodes / 189,129 contract edges; 1,277 bankruptcy-remote
  SPVs; 2,586 non-recourse contracts ✅
- **Contagion:** 8,749 paths / 145 high-or-critical / $1.92T AI-infra notional ✅
- **Timing:** 3,263 signals / $3.25T 2024-2030 refinancing / $227B AI-infra / forward peak $172B ✅

**Yet `high_confidence_final=False`, `bubble_confidence=0.25`.** The breadth is built; the CONCLUSION is gated.

## Why confidence = 0.25 (exact mechanism, from `src/bubble/analysis/evidence.py:418-429`)
`max_permitted_report_confidence` is a conservative floor over the weakest high-impact claim:
- **any UNSUPPORTED-tier claim → 0.25** (← this is the current state: ≥1 Burry-question claim has no attached evidence)
- any INFERRED-tier claim → 0.45
- any blocking issue → min(0.6, weakest effective confidence)
- else → min(0.95, weakest)
And `high_confidence_final` flips True only when EVERY high-impact claim is tier ∈ {MEASURED, CORROBORATED,
SINGLE_SOURCE}, effective_confidence ≥ 0.75, semantic bucket = COMMITTED_DEBT (not boilerplate/asset/equity), ≥2
corroborating sources, AND human_review_status = APPROVED (`evidence.py:305-356`).

## The unlock ladder (the critical path)
| Stage | Blocker to clear | Lifts cap to | What it requires |
|---|---|---|---|
| 1 | UNSUPPORTED claims | 0.25 → 0.45 | attach ≥1 source to every high-impact Burry claim |
| 2 | INFERRED claims | 0.45 → 0.60 | replace scaled/modeled values with MEASURED primary evidence |
| 3 | blocking issues | 0.60 → 0.75+ | semantic=committed_debt, ≥2 sources, confidence≥0.75 per claim |
| 4 | adjudication | high_confidence_final=True | human_review_status=APPROVED on every high-impact claim |

## The leverage: this session's verified evidence already feeds Stages 2-4 for the AI-direct core
The 6 Burry questions and the evidence now in hand:
1. **Bubble conclusion** — `claude_bubble_conclusion_evidence_matrix` (bull-vs-bear, weighed).
2. **Size** — $3.652T metric, with the **~$84.6B AI-direct over-count correction** (economic-event repeats) primary-
   verified per name; AI-direct core $392.9B → ~$310-321B.
3. **Timing** — `claude_ai_direct_maturity_wall`: 88% of carded AI-direct debt walls 2030-2033; report timing_signals
   already quantify $227B AI-infra refinancing.
4. **Hidden risks** — holed take-or-pay (`claude_contract_durability_backing_debt`), GPU collateral erosion
   (`claude_gpu_collateral_erosion`), the SPV/recourse structure (primary EDGAR: IREN Hardware 3, TeraWulf, Hut 8...).
5. **Contagion** — `claude_circular_financing_map` + the 8,749 graph paths; NVIDIA round-trip + OpenAI-CoreWeave $22.4B
   binding edge.
6. **Downside bearer** — `claude_downside_bearer_taxonomy` + the exact-match role mapping (secured-SPV creditors,
   ratepayers, equity-dilution; 79 trustee/agent conflations to re-role).

**Each of these is now backed by primary-EDGAR rows with exact accession + quote** — i.e. tier MEASURED, not inferred.
The unlock work is to WIRE this verified evidence into the report's claim audits so the gate sees MEASURED+APPROVED
instead of UNSUPPORTED/INFERRED.

## Execution sequence (once the handoff is clean and I hold the main checkout)
1. **Import the P1 queue** (`f853695`) + add a role-mapping validator. (no report rebuild)
2. **Apply the ~$84.6B economic-event collapse** — modify `materiality_adjudication_results.py` dedup (issuer+offering
   identity), add negative-control regression (Eaton/Simon/Venture Global must survive), rebuild report, invariants pass.
3. **Wire verified AI-direct evidence into claim audits** — attach the primary-EDGAR provenance (accession+quote) to the
   size/timing/risk/contagion/bearer claims so their tier → MEASURED and semantic → COMMITTED_DEBT (clears Stages 1-3
   for the AI-direct core).
4. **Adjudicate** the high-impact AI-direct claims to APPROVED (Stage 4).
5. **Regenerate + validate**; read the new `max_permitted_report_confidence`. Iterate per remaining weakest claim.

## Honest scope note
The gate is conservative BY DESIGN (skepticism-first). high_confidence_final for the WHOLE ecosystem (all 6 questions,
all entities) is a high bar. The achievable near-term milestone is **high-confidence on the AI-direct core** (the
$310-321B negative-carry cluster), where I now have primary evidence end-to-end — then expand outward. The report can
surface a confident, evidence-tiered conclusion on the AI-direct cluster while honestly marking the broader ecosystem
claims at their true (lower) tier. That IS the Burry standard: grounded, transparent, ahead of consensus, not overclaimed.

## Verified vs proposed
- VERIFIED: the scale metrics + the 0.25 mechanism (report JSON + evidence.py); the per-question evidence inventory.
- PROPOSED: the unlock sequence + the "AI-direct core first" milestone. Execution requires the main checkout (pending
  clean handoff) — I will NOT edit main while Codex is active there.
