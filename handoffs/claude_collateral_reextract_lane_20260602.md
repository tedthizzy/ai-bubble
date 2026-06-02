# Collateral RE_EXTRACT_DEPTH lane (Codex lane 1) — VERIFIED scaffold spec — 2026-06-02

- **From:** Claude · **For:** Codex. **Handoff only — NO code committed.** This lane targets
  `materiality_adjudication_results.py` / `materiality_adjudication.py`, which you have **uncommitted WIP on**
  (session-start `git status` shows both `M`). Writing tests against your in-flight signatures would collide,
  so this is a verified spec for you to land on your branch. Every claim below was checked against the real
  code + the targets CSV; the lane's own verifier additionally *ran* `build_materiality_adjudication_decisions`
  on each snippet.

## Cohort
`handoffs/fixtures/acquisition_targets_collateral_recourse.csv`: **101 `RE_EXTRACT_DEPTH` rows**
(zero-acquisition wins — the EX-10/EX-4 exhibit carrying the collateral/recourse terms is **already held**).
Gap split: `determine collateral scope` = 92, `determine recourse and guarantee scope` = 9. Spread:
Credit Agreement (86 across case variants), Indenture (13), Security Agreement (1), Guaranty (1);
EX-10_exhibit = 90, EX-4_exhibit = 11.

## VERIFIED decision logic (`materiality_adjudication_results.py`)
- `_category_gaps` (L262-365): for capital/contract it appends **`determine collateral scope`** (L349) unless a
  collateral/secured/unsecured/mortgage-bond marker or `_collateral_scope_terms()` hit is present, and —
  **independently** — appends **`determine recourse and guarantee scope`** (L334) unless a
  guarantee/recourse/guarantor/unsecured/issuer-note/secured-lender marker is present.
- `_decision` (L212-226): **any** remaining gap → `needs_deeper_extraction`; empty gaps + supporting terms →
  `supported_as_material_blocker`. `_metric_use_status` (L229-236): supported + no gaps + capital/contract/
  physical/compute + exposure>0 → `approved_for_metric_use`, `supported_amount_usd = exposure_basis_usd`.
- **KEY INVARIANT to lock:** a determinate **UNSECURED** finding clears the collateral gap exactly like a
  SECURED one (negative-but-determinate). Universal red→green per scaffold: after re-extract, the named gap is
  absent from `decision.remaining_gap`, `decision == supported_as_material_blocker`,
  `metric_use_status == approved_for_metric_use`, `supported_amount_usd == exposure_basis_usd`.

## 15 proposed scaffolds — 13 sound, 2 corrected
Each scaffold builds a tmp packet (`category='capital'`,
`subcategory='high_notional_debt_like_candidate'`, `exposure_basis_usd` from CSV, populated counterparty,
`evidence_snippets=json.dumps([{source_uri, content_hash, document_id, snippet:<held-exhibit clause>}])`) →
`build_materiality_adjudication_decisions([tmp], adjudicated_at='2026-06-01T00:00:00+00:00')`. All 15
packet_ids exist in the CSV with exact exposure matches (spot-verified SpaceX/VentureGlobal/Oracle/Caterpillar/
Vistra). RED today = each sits at `needs_deeper_extraction` until the held clause is re-extracted.

Sound (13): AT&T (17.5B, unsecured), Oracle (10B, unsecured), Abbott (7B, unsecured), Venture Global indenture
(6B, secured notes), Talen (1.2B, unsecured notes), Hut 8 (3.25B EX-4), GM (17B), Carnival (3B secured notes),
Caterpillar (1.7B EX-4 unsecured), United Rentals (1.5B unsecured+guarantee), Vistra (1.25B — sole
recourse/guarantee target, Security Agreement), American Airlines (1.1468B secured guaranty), Royal Caribbean
(1B secured vessel facility).

### ❗ Correction 1 — SpaceX (`d3e8fa103bb42e7c`, 20B) & Venture Global credit-agreement (`2ef4bf630fb5911a`, 16.461B)
**The finder's expected_outcome is WRONG as written** (verifier ran the code; I confirmed the structure).
These two snippets are **secured-ONLY** ("secured by a first priority security interest in substantially all
assets" / "first lien … borrowing base … collateral agent") with **no guarantee/recourse/guarantor word and no
unsecured language**. `_category_gaps` clears `determine collateral scope` via `_collateral_scope_terms()` but
**still appends `determine recourse and guarantee scope`** (L334) — so `_decision` returns
`needs_deeper_extraction`, `supported_amount_usd=0`, NOT supported. A secured-only quote does **not**
auto-clear the recourse gap.
**Fix:** the held exhibit *does* carry guarantee language — append it to the snippet, e.g.
`"… and are guaranteed by the Guarantors"`. Verifier confirms that flips both to
`supported_as_material_blocker` with empty gaps and `supported_amount_usd == exposure`. Assert **both** gaps
drop, not just collateral.

### ❗ Correction 2 — Oracle (`0261a1f1...`) & Caterpillar (`22ee0211...`) `target_fn` mislabel
Their `target_fn` claims the **decision-side** test "locks Codex `_contains_definition_only_scope` /
`_has_executable_scope_clause` guard." **False — verified:** `materiality_adjudication_results.py` never
imports or calls those (empty grep). The definition-only guard runs **only** inside
`build_materiality_adjudication_packets` (the artifact reader), which is bypassed when a decision is built from
a hand-supplied `evidence_snippets` JSON. The PASS assertions themselves still hold (both resolve UNSECURED →
`approved_for_metric_use`). **Fix:** either move the definition-only-guard assertion to a **packet-side** test
(like your existing `test_materiality_packet_snippet_does_not_prefer_definition_only_scope`), or restate
`target_fn` as the decision module's `_category_gaps` unsecured branch + `_best_scope_clause`/`_scope_quote_terms`.

## CAVEAT
Exact exhibit wording was **inferred from instrument type + issuer profile, not fetched** (read-only research).
The marker *families* (secured-by/first-priority/security-interest vs senior-unsecured/unsecured-obligations vs
guaranteed-by/non-recourse) are what the adjudicator keys on and are stable per instrument type — but when you
implement, **paste the verbatim clause from the actually-held exhibit** so substring assertions match real
text. Populate `counterparty` (e.g. `administrative agent` / `lenders party thereto` / `noteholders` /
`collateral agent`) or an `extract named counterparty and role` gap will also keep the packet blocked.

All line numbers verified against the worktree base of master `881b6c8` (your WIP may shift them).
