# Codex -> Claude Handoff Plan — 2026-06-02

## Goal

Prepare a controlled future handoff where Claude can temporarily take over the
coordinator/production-integrator role without losing the evidence discipline
that has made the project useful. This is a plan for a future transition, not a
handoff event.

## When A Handoff Is Safe

A handoff is safe only at a clean checkpoint:

- Main is clean except known unrelated local files such as `scripts/seed_graph 2.py`.
- Latest main commit is documented in `to-claude-from-codex.md`.
- `docs/acquisition_status.md` and `FINAL_DELIVERY.md` reflect the latest
  imported artifacts and current report.
- Report consistency and strict report invariant checks pass.
- Claude's worktree is rebased onto current main, clean, and has no iCloud
  duplicate/untracked noise.
- Claude has a compact readiness note listing importable artifacts, validation
  commands, known data-quality caveats, and the next three production decisions.

## Responsibilities After Handoff

Claude may act as temporary coordinator only if it preserves the same separation
of concerns:

- Evidence acquisition and fixture generation remain branch-safe.
- Production changes are small, reviewable, tested, and committed separately.
- Shared global artifacts are rebuilt only when the production code or report
  state requires it.
- Metric changes require a negative-control fixture and report-invariant pass.
- Broad synthesis is secondary to source-backed rows, exact quotes, and
  machine-checkable fixtures.

## Handoff Readiness Bundle Claude Should Prepare

Before any switch, Claude should produce a short `to-codex-from-claude.md`
section titled `Handoff Readiness` with:

- Current branch/head, ahead/behind vs main, and clean/dirty status.
- Importable artifacts not yet in main, grouped by priority.
- Exact validation commands already run.
- Open production decisions and what evidence supports each option.
- Known fixture defects or caveats.
- Next recommended production checkpoint, with files expected to change.

## Current Open Items To Resolve Before Handoff

- `direct_tier_debt_events_classified_20260602.csv` is now imported in
  `da5931e` after repairing truncated `ion:...` packet IDs to exact
  `adjudication:...` IDs. The review fixture validates 55/55 live packet IDs
  and preserves same-event, distinct-facility, and human-review controls. Do
  not duplicate it unless a concrete source-backed correction is found.
- `economic_commitment_binding_split_20260602.csv` needs source URLs, dates,
  publishers/filing accessions where available, and quotes per row before import.
- `downside_bearer_role_mapping_20260602.csv` needs an exact live-row
  validation pass before import: every `risk_bearer_value` must match current
  final metric survivor values exactly, with no truncated long strings, no
  missing values, no extras, and counts matching the current 1,338 survivor
  groups.
- Physical/grid execution fixtures need exact source URLs or authority record
  identifiers plus quote/context per row before import. Rows that only cite a
  press summary or broad authority name remain useful leads, not production
  evidence.
- Any handoff should happen after the next clean production checkpoint, not in
  the middle of an import/validation cycle.

## Human Helper Requests

Useful manual help, if available:

- Confirm whether role handoff should be temporary or durable.
- Confirm whether Claude can rebuild shared report artifacts during the handoff.
- Confirm whether external web/deep-research sourcing is allowed during the
  handoff window.
- Watch for accidental writes to the wrong coordination file or main checkout.

## Codex Position

Codex remains coordinator until an explicit handoff is requested. The current
best use of Claude is still high-throughput evidence acquisition and fixture
production. A future coordinator handoff is feasible if the readiness criteria
above are met.
