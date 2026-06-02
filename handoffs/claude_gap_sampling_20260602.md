# Materiality Gap-Sampling Packs — 2026-06-02

- **From:** Claude (worker) · **For:** Codex · **Branch:** `claude/report-qa`
- **Method:** 4 parallel read-only `Explore` auditors over `needs_deeper_extraction` rows in `materiality_adjudication_decisions.csv`, one per gap bucket + **my verification** of a sample.
- **Verification:** 8/8 sampled false-positive packet_ids confirmed against the live CSV — each exists, has the claimed `remaining_gap`, and its `evidence_quote` contains the claimed language.
- **⚠ Data-quality caveat:** some auditors **fabricated the `content_hash` field** in their samples (non-hex like `5e6f7g8h`). **Ignore those hashes** — `packet_id` + `source_uri` + `quote` are the verified references. Counts are a snapshot (data moving as you rebuild).
- **Purpose:** fixtures + false-positive identification to feed your in-progress adjudicator heuristics. Read-only; no code edits; treat heuristics as candidates/validation set, likely overlapping your active work.

## Bucket summary (false-positive = the quote ALREADY answers the gap → safe to auto-resolve, reduces unresolved blockers)

| bucket | gap rows | est. auto-resolvable FP | dominant genuine-blocker pattern |
|--------|---------:|------------------------:|----------------------------------|
| counterparty_role | 919 | ~115 (~10–13%) | credit-agreement ref w/o syndicate roster → needs full doc |
| collateral_scope | 426 | ~2 (~0.5%) — **structural** | excerpt is non-collateral (8-K header / note terms) → wrong extraction target |
| recourse_guarantee | 88 | ~2–15 (~17%) | "senior secured … facility" w/o guarantee/recourse detail |
| aggregate_shelf | 198 | ~35 (~18%) | shelf-prospectus / balance-sheet snapshot / undrawn capacity |

---

## counterparty_role — ~115 rows where the party/role is already in the quote

**Safe heuristic:** if `evidence_quote` matches `\b(Borrower|Initial Borrower|Lender[s]?|Administrative Agent|Collateral Agent|Facility Agent|Guarantor[s]?|Bridge Lender[s]?|Arranger|Trustee)\b`, the role IS present → downgrade from `needs_deeper_extraction` (fully resolved if a *named* party precedes the role; "role-known, names-pending" if generic).

**Verified false-positive fixtures:**
- `adjudication:a15e730c03692dd6` (Global Payments) — *"Boost Newco Borrower, LLC (\"Borrower\"), and certain of Guarantor's existing subsidiaries…"* → Borrower named. `…/data/1123360/000112336025000082/ex993worldpayq32025financi.htm`
- `adjudication:1ce66d9fd03e5b27` (Venture Global) — *"Calcasieu Pass Funding, LLC (\"Borrower\"), an indirect subsidiary of Venture Global, Inc."* → Borrower + parent.
- `adjudication:3b917bbdef5ac8cc` (MiniMed) — *"The obligations of the Initial Borrower … are guaranteed by certain wholly-owned subsidiaries of Medtronic…"* → Borrower + Guarantor structure.
- `adjudication:e0f2aeea6d89b306` (Brown & Brown) — *"…certain Bridge Lenders to provide up to $9.4 billion…"* → **role confirmed, names not** (see caution).

**Caution:** ~28 "certain Bridge Lenders / syndicated lenders / consortium" rows confirm the **role** but not the individual **names** (which live in a syndicate schedule). Resolve these to *"role known, names pending schedule fetch"* — not fully cleared.

---

## collateral_scope — ~0.5% FP; this is a STRUCTURAL extraction-target problem

**Key insight:** 99.5% are genuine blockers because the **extracted excerpt is non-collateral** (8-K header, note-prospectus financial terms, credit-facility preamble) — the security-agreement text isn't in the quote. To clear these you must **fetch the security agreement / indenture collateral schedule**, not re-adjudicate the 8-K excerpt. (i.e. an acquisition/extraction-target gap, not an adjudication gap.)

**Safe heuristic:** quote contains `secured by | pledge | lien on | first-priority | second-priority | security interest | principal property` → `has_collateral`; plain `unsecured | no collateral` → `unsecured`. **Do NOT** auto-resolve guarantee-only quotes (a guarantee ≠ collateral scope).

**Verified FP fixture:** `adjudication:25fa4e2557e4f38b` (Micron) — *"…restrict our ability … to incur liens on Principal Property (as defined in the Indenture)…"* → collateral language present.

---

## recourse_guarantee — ~17% FP

**Safe heuristic (auto-resolve):** `first mortgage | mortgage bond` (collateral inherent); `non-recourse`; `guarant(y|ies) … limited by amount`; `full and unconditional guarantee`; named `Guarantors party hereto`.

**Verified FP fixtures:**
- `adjudication:1df873b018c36ef0` (Union Electric) — *"UNION ELECTRIC COMPANY 4.80% FIRST MORTGAGE BOND DUE 2036 … ANY TRANSFER, PLEDGE…"* → secured by definition.
- `adjudication:0038992c96d28f12` (Trinseo) — *"…provided guaranties with respect to the obligations under the Super HoldCo 1L Credit Agreement, which guaranties were limited by amount"* → guarantee scope stated.

**Dominant blocker (≈58%):** `senior secured … (term loan|credit facility)` with **no** guarantee/recourse specifics → needs full credit/guarantee agreement (e.g. `adjudication:56b42d78a830d9c0` Columbus McKinnon, `adjudication:c1e88a8ecef6c4fe` Construction Partners).

---

## aggregate_shelf — ~18% FP

**Core distinction:** SPECIFIC-COMMITMENT markers (`issued|redeemed|entered into` + dates/counterparty) → **false positive** (it *is* a committed obligation, even if the word "aggregate" appears) vs AGGREGATE/SHELF markers (`prospectus supplement`, balance-sheet metrics, `ability to borrow up to`, `total consolidated … in aggregate principal amount`) → correctly blocked.

**Verified FP fixtures (should clear):**
- `adjudication:03c20e6eeadb4dd4` (PennyMac) — *"Issued $2.35 billion of unsecured senior notes with maturities ranging from 2032 to 2034 · … · Redeemed $650 million…"* → specific issuance.
- `adjudication:a7ef564972c7d6fa` (**TeraWulf — AI-infra relevant**) — *"Entered into long-term HPC lease agreements representing aggregate contractual value in excess of $12.8 billion, including a lease with Fluidstack supported by Google's credit."* → a committed AI/data-center lease being blocked merely because "aggregate" appears. **Don't let the word "aggregate" alone block a committed `entered into` transaction.**

**Correctly-blocked aggregate (keep blocked):**
- `adjudication:cacdcaac9f59c6bb` (Oracle) — *"…ability to borrow up to an additional $9.9 billion under our revolving credit facility…"* → undrawn capacity.
- `adjudication:e4452759a1db84cf` (Enbridge) — *"total consolidated long-term debt … in aggregate principal amount, approximately $103,994 million"* → balance-sheet inventory.
- `adjudication:b4b5a60c2ec7c917` (Truist) — *"This prospectus may not be used to sell securities unless accompanied by a prospectus supplement…"* → shelf boilerplate.

---

## Candidate heuristics (deterministic; verify against your in-progress adjudicator)

1. **counterparty role-keyword present** → not a full counterparty gap (resolve, or mark "names-pending" if only generic "Lenders/Bridge Lenders").
2. **collateral**: `secured by|pledge|lien|first/second-priority|security interest|principal property` → collateral known; `unsecured` → unsecured; guarantee-only → still blocked.
3. **recourse/guarantee**: `first mortgage|mortgage bond|non-recourse|guaranty… limited by amount|full and unconditional guarantee|Guarantors party hereto` → resolved.
4. **aggregate/shelf**: `issued|redeemed|entered into` + (date|maturity|named counterparty) → committed (clear); `prospectus supplement|may not be used unless accompanied|ability to borrow up to|available to draw|total consolidated…in aggregate principal amount|strong balance sheet|tangible net worth|D/E ratio` → aggregate/shelf (keep blocked).
5. **collateral structural fix (acquisition, not adjudication):** when the collateral excerpt is an 8-K header / note-terms / facility preamble, route to *fetch security agreement / indenture collateral schedule* rather than re-adjudicating the excerpt.

## Proposed regression-test names (fixtures = the verified packet_ids above)
`test_role_keyword_in_quote_clears_counterparty_gap`,
`test_generic_syndicate_marks_names_pending_not_resolved`,
`test_secured_lien_language_clears_collateral_gap`,
`test_guarantee_only_quote_does_not_clear_collateral`,
`test_first_mortgage_and_limited_guaranty_clear_recourse_gap`,
`test_senior_secured_without_guarantee_detail_stays_blocked`,
`test_issued_redeemed_entered_clears_aggregate_split`,
`test_aggregate_word_alone_does_not_block_committed_transaction`,
`test_shelf_and_balance_sheet_language_stays_aggregate_blocked`.

## What I did NOT do
- No edits to production code or your active files; no artifact rebuilds. Read-only sampling only.
- Ignored auditor-fabricated `content_hash` values; relied on verified `packet_id`/`source_uri`/`quote`.
- These buckets are your active heuristic lane — use this as a fixture/validation set, not as new code. Counts are a single snapshot.
