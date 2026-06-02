# EvidenceGate metric-audit-coverage lane (Codex lane 3) — VERIFIED — 2026-06-02

- **From:** Claude · **For:** Codex. **Handoff only — no code.** This lane touches the report assembler
  (`scripts/generate_final_burry_report.py`, your domain) and most fixes require rebuilding shared `data/`
  artifacts (`data/graph/*`, `data/reports/*`) — which I never do. Verified spec below.
- Report basename mapped: `BURRY_REPORT_EvidenceGated_20260602-0513`.

## ⚙️ Core diagnosis — VERIFIED (this is a wiring gap, not an evidence gap)
The "unaudited high-impact metric" warnings are **mostly not missing evidence.** Confirmed against real code:

- **The checker matches by exact scalar float membership.** `check_metric_audit_coverage`
  (`report_consistency.py:342-359`) builds `audited_values: set[float]` from
  `evidence_quality.claim_audits[].value` — **scalar int/float only** (dict-valued audits contribute nothing,
  L344-346) — then flags any walked report key with `float(value) > 100e9` whose exact float is **not in the
  set** (L353-359). Two failure modes fall out: (a) **dict-valued audits never match**; (b) **any rounding
  breaks the match** — the audit float must equal the report float to the cent.
- **The analysis modules already build the audits, but the assembler never merges them.**
  `capital_structure.py` builds `claim_audits` with exactly the claim_ids the report needs
  (`capital.total_notional` L406, `capital.debt_like_notional` L415, `capital.guarantee_linked` L460,
  `capital.pending_review_debt_like_notional` L487, `capital.notional_review_required` L496 [dict],
  `capital.downside_bearers` L528 [dict], …) and exposes them via `to_dict()["claim_audits"]` (L208).
- **But `evidence_quality.claim_audits` = `evidence_audits`** (`generate_final_burry_report.py:1576`), and
  `evidence_audits` comes solely from `audit_report_evidence(metrics)` (L1061), which runs `EvidenceGate` over a
  **hand-enumerated `coverage.*` / `physical.*` claim list** (L60+). The capital_structure / debt_service /
  capital_exposure_graph / contract_contagion / timing / review_queue `claim_audits` are **never appended** to
  that list. That single omission is the bulk of the warnings.

## Three fix classes (35 mapped metrics; verifier confirmed 21 sound, corrected 18)

### Class 1 — MERGE-ONLY (audit already exists, exact value) — safe, contained, no artifact rebuild
Thread the analyzers' existing `claim_audits` into `evidence_audits` before L1576. `capital_structure` audits
already carry the precise report floats:

| metric (report key) | exact audit value | existing claim_id |
|---|---|---|
| `current_debt_like_notional_usd` | 1200595124370.18 | `capital.debt_like_notional` |
| `current_distinct_debt_like_notional_usd` | 795293874370.18 | `capital.distinct_debt_like_notional` |
| `current_duplicate_candidate_notional_usd` | 406050050000.0 | `capital.duplicate_candidate_notional` |
| `current_aggregate_obligation_distinct_notional_usd` | 176685000000.0 | `capital.aggregate_obligation_distinct` |
| `current_total_notional_usd` | 1278878535956.18 | `capital.total_notional` |
| `current_pending_review_debt_like_notional_usd` (+ `when_cracks` re-emit) | 1200595124370.18 | `capital.pending_review_debt_like_notional` |
| `current_guarantee_linked_usd` | 186838201225.0 | `capital.guarantee_linked` |

⚠️ `debt_service` builds some audits too (`debt_service.missing_rate_notional` = **689881283165.74**) but
`DebtServiceMetrics.to_dict()` **drops `claim_audits`** — so the merge needs `to_dict()` to expose them first,
then the assembler to append. Not a pure one-liner.

### Class 2 — SPLIT dict-valued audit into scalars — small change inside `capital_structure.py`
These audits exist but are dict-valued, so the scalar checker never matches. Emit scalar siblings (use the
**exact** values — finder rounded several):

| metric | CORRECTED exact value | proposed scalar claim_id |
|---|---|---|
| `current_notional_review_required_usd` | **564275000000.0** (finder said 564.3B) | `capital.notional_review_required.notional` |
| `current_notional_review_required_distinct_usd` | **176675000000.0** (finder said 176685000000 — that **collides** with aggregate_obligation_distinct) | `capital.notional_review_required.distinct_notional` |
| `current_unmapped_downside_bearer_usd` | **449901144204.04** (finder rounded) | `capital.unmapped_downside_bearer` |

### Class 3 — NEW audits in artifact builders — **Codex-only (needs shared-artifact rebuild)**
No audit exists; the source artifact carries none. These require editing the builder *and* regenerating the
shared artifact, so they're out of my lane. Verifier-corrected values/sources noted:

- `debt_service.py`: `current_debt_service_measured_rate_notional_usd` = **510713841204.44** (method is
  `_evidence_summary`, **not** `_build_audit_payload`); `current_distinct_debt_service_missing_rate_notional_usd`
  = **599461137298.53**; `maturity_wall_notional_usd_2024_2030` = **118250000000.0** (per-entity row; top-level
  alt is 278383365879.58); the bare `measured_rate_notional_usd` first-seen is a **DebtServiceEntityRisk row =
  140350000000.0** (not a quarter row); bare `distinct_notional_usd` is **DebtServiceEntityRisk idx0 =
  141550001225.0** (not the 8.5B duplicate-group).
- `capital_exposure_graph.py` (`data/graph/…_summary.json`, 10142 source-backed edges, **0 audits**):
  `…largest_component_ai_infra_relevant_notional` = **332403514666.67**; `…top_ai_infra_component_notional` =
  **310761466666.67**; bare `ai_infra_relevant_notional_usd` per-component = **332403514666.67** (not top-level
  333003514666.67); `incident_notional_usd` hub = **463741928619.85**.
- `contract_contagion_paths.py` (8749 source-backed paths, 0 audits); `timing_signals.py` (3854 source-backed
  signals, 0 audits): `current_timing_ai_infra_capital_refinancing_2024_2030` = **292289419740.72**; quarter
  `capital_refinancing_usd` = **220471841010.0**.
- `review_queue.py`: `notional_amount_usd` = 734000000000 (path is `top_distinct_capital_review_queue_items`
  idx5, not `top_review_queue_items`); the >100B `exposure_usd` is actually a **`weak_links.py`
  WeakLinkCandidate row = 141550001225.0**, not a review-queue item (most of those are 0.0).

## Recommended order
1. **Class 1 merge** (biggest warning drop for the least change; additive — appends already-gated
   `corroborated_estimate` audits, fabricates nothing). I can ship the `to_dict()`-expose + assembler-merge as
   a tested fix on request — say the word and I'll TDD it without rebuilding any artifact.
2. **Class 2 scalar splits** in `capital_structure.py` (also Claude-safe — pure analyzer change + unit test).
3. **Class 3** builder audits — your call, since each needs the shared artifact regenerated.

## Discipline note
Finder mapped 35 metrics; the lane's verifier **ran `check_metric_audit_coverage`** and corrected 18 (rounded
values that wouldn't exact-match, 3 misattributed source rows, 1 value collision, wrong method name). I
re-verified the three load-bearing structural claims (checker = exact-scalar; capital audits exist; assembler
omits the merge) against the worktree base of master `881b6c8`. **Use the corrected exact floats above** — a
rounded value silently fails to match and the warning persists.
