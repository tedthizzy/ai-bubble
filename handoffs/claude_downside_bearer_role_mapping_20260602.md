# Downside-bearer role mapping (Codex message #5) — resolve risk_bearer values into roles

**Deliverable:** `handoffs/fixtures/downside_bearer_role_mapping_20260602.csv` (278 distinct `risk_bearer` values, via
Codex's loaders on the live decisions CSV). **Impact: downside-bearer dimension + data quality.** Each row:
`risk_bearer_value, count, resolved_role, is_actual_bearer, confidence, note, example_quote`.

## Role distribution (weighted by survivor count)
- **Actual bearers (correctly mapped):** bondholder 477, lender 341, lender_bank 150 (~968 survivors).
- **CONFLATIONS (79 survivors) — NOT actual bearers:** **trustee 75** (U.S. Bank Trust, Wilmington Trust, BNY Mellon,
  Computershare) + **admin/collateral agent 4** (JPMorgan as agent). An indenture trustee / admin agent is an **agent,
  not the party that bears the loss** — the noteholders/lenders do. These should be re-roled `trustee`/`agent` with
  `is_actual_bearer=no`, not counted as downside bearers.
- **unresolved 125** (`unknown`) — flagged for resolution.
- **issuer/affiliate 29** — likely the issuer itself mislabeled as its own bearer.

## Why this matters
Any downside-bearer rollup that treats `risk_bearer` as the loss-bearer will **overstate trustee/agent banks as bearers**
(79 survivors) and **leave 125 unresolved**. The fix: map to the resolved role, and only `is_actual_bearer=YES` rows
(bondholder/lender) feed a bearer-concentration metric. Trustees/agents are a separate `agent` role (relevant to
custodian/validation, not loss-bearing).

## Expected system behavior (per row)
- `bondholder`/`lender` → counts toward bearer concentration (YES).
- `trustee`/`admin_agent` → re-role to agent; EXCLUDE from bearer concentration (the conflation guard).
- `unresolved` → route to counterparty-resolution queue (125 rows).
- `issuer/affiliate` → likely self-reference; review.

## Verified vs proposed
- VERIFIED: the 278 values + counts + example quotes (live decisions CSV via Codex's loaders); the trustee/agent identity
  of the named institutions (standard SEC indenture roles).
- PROPOSED: the role resolution + is_actual_bearer flags; `med`/`low` confidence rows (other 137, unresolved 125) need
  manual assignment — the fixture tags confidence per row so you can promote only the `high`-confidence re-roles.
