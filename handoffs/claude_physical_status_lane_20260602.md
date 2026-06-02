# Physical construction-status lane (Codex lane 2) — VERIFIED — 2026-06-02

- **From:** Claude · **For:** Codex. Shipped as committed test pack
  `tests/ingestion/test_physical_status_taxonomy.py` (+ this note). Verified independently against the
  live extractors and `data/physical/*.csv` (csv.DictReader counts) before writing.

## ⚠️ Framing correction (the work item is mis-scoped as "populate empty status")

`construction_status` is **NOT empty.** Verified counts:

| file | records | construction_status distribution |
|------|---------|----------------------------------|
| `projects.csv` | 2125 | announced=974, in_service=793, under_construction=298, cancelled=60 — **0/2125 empty** |
| `observations.csv` | 2125 | identical 4 values — **0/2125 empty** |
| `permits.csv` | **139** | issued=131, unknown=8 |
| `equipment.csv` | **14** | **all unknown, all generator (zero `installed`)** |
| `queues.csv` | 26 | study=14, unknown=11, agreement_executed=1; `delay_months` **empty on all 26** |

`permit_status` is the genuinely-sparse column (319/2125 = 15% empty). The real defect is **taxonomy
starvation**, not emptiness:

1. **`delayed` is unreachable from the projects writer.** `_construction_status`
   (`tracker_extraction.py:248-264`) has branches for in_service / cancel / under_construction / permitted
   only — `'delayed'`, `'Suspended'`, `'on hold'` all fall through to `announced`.
2. **`mechanical_completion` is unreachable** from ingestion entirely, yet `physical_risk._construction_risk`
   treats it as zero-risk — so the enum member exists but no row can ever carry it.
3. **`permitted` is starved by check-ordering.** The `under construction` substring is tested *before* the
   `approved/permitted` branch, so the live tracker string `"Approved/Permitted/Under construction"`
   (143 rows) → `under_construction`. A bare `"Approved"` → `permitted`, but that bare form doesn't occur on
   disk, so **0 projects carry `permitted`** despite 143 `approved_or_permitted` permit_status rows.
4. **The two writers disagree.** `_status_from_tracker` (`construction_observations.py:185-197`) *does* map
   `'delayed' → delayed`; `_construction_status` does not. Same raw input, two different statuses depending on
   which CSV you read.

**Recommended reframe:** "close taxonomy coverage gaps + unify the two status mappers + let
permit/equipment/observation evidence override the tracker-derived status" — not "fill empty status".

## ✅ Shipped this lane: `tests/ingestion/test_physical_status_taxonomy.py` (committed `676535e`)

Gate-green (`18 passed, 5 xfailed`, ruff + mypy clean). **No production change** — taxonomy unification is
your design call; I only pinned the contract and the gaps.

- **GREEN characterization** locks the verified-today contract of *both* mappers (so a refactor can't silently
  reclassify projects): `Operating→in_service`, `Cancelled→cancelled`, `expansion→under_construction`,
  bare `Approved→permitted`, `Approved/Permitted/Under construction→under_construction`, `Proposed→announced`,
  and the observations-writer `delayed→delayed`.
- **`xfail(strict=True)`** encodes the verified gaps — they keep the gate green today and **flip to a failure
  the moment you close the gap** (prompting marker removal): `delayed`, `Suspended`, `on hold`,
  `commissioning→mechanical_completion`, and a `test_status_mappers_agree_on_delayed` divergence pin.

Proposed target mappings are reasonable but **you own the final taxonomy** — adjust the xfail bodies if you
want different canonical values.

## Deliverability metric design (grounded; corroborations pruned)

A per-project `percent_deliverable` (capacity-weighted rollup by `capacity_mw_high`) belongs on
`PhysicalRiskAssessment` (it already has a `components` dict; **no `percent_deliverable` field yet**) and
should be populated in `PhysicalRiskEngine.assess` — **not** in the loader (keep ingestion deterministic).
Design = stage-weight × linkage-multiplier, EvidenceGate-tier-capped (single-source tracker claims stay under
the repo 0.25 ceiling):

- stage weight from the unified taxonomy: announced~0.15 / permitting~0.35 / under_construction~0.6 /
  mechanical_completion~0.85 / in_service~1.0 / delayed clamp≤0.4 / cancelled=0.0 (≈ `1 − blended_risk`, so it
  reuses the existing risk model rather than inventing a second source of truth).
- linkage multiplier from the match CSVs that actually exist on disk: `match_status ∈
  {strong_match, candidate_match, unmatched}` + `match_confidence`, plus permit `status='issued'`.

⚠️ **Do NOT build red tests on `installed` equipment (0 rows), `denied/withdrawn` permits (0 rows), or
`delay_months>=12` (0 rows)** — those corroborations don't exist in current data. Seed any such fixture
synthetically and label it forward-looking. **Unify the two status mappers FIRST**, else the metric reads a
different status from `projects.csv` than `observations.csv` for the same project_id.

## Provenance / discipline
The lane's finder fabricated two data counts (claimed `permits.csv issued=151/14` and
`equipment.csv installed=24`); recount with csv.DictReader gives 139 (issued=131/unknown=8) and 14 (all
unknown). I verified every number above myself; the four "evidence-row" fixtures the finder proposed
(operational/cancelled/cross-signal/installed) are **not buildable from current data** and were dropped from
the committed pack. Line numbers verified against the worktree base of master `881b6c8`.
