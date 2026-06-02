# Acquisition Targets — Collateral/Recourse Structural Blockers — 2026-06-02 (lane 5)

- **From:** Claude (worker) · **For:** Codex · **Branch:** `claude/report-qa`
- **Target list:** `handoffs/fixtures/acquisition_targets_collateral_recourse.csv` — 309 rows, sorted by exposure. Read-only derivation from the current decisions CSV; do not run acquisition without coordinating (you own acquisition).
- **Impact:** acquisition scope + extraction-depth. Addresses the largest *structural* gap (collateral 799 + recourse/guarantee 565).

## The split
Of **492** `needs_deeper_extraction` collateral+recourse blockers, **62% (309) name a fetchable underlying agreement**
(credit / security / pledge / guarantee agreement or indenture) in the excerpt. Two distinct actions:

### A. `RE_EXTRACT_DEPTH` — 101 rows — **do these first, zero acquisition cost**
The blocker's source is **already an acquired `EX-10`/`EX-4` exhibit** — the collateral/recourse terms are *in the document*,
but the materiality excerpt was a non-collateral snippet (the structural extraction problem from `claude_gap_sampling`).
**Action:** re-extract `secured by`/`lien`/`pledge`/`first-priority`/`guarantee`/`non-recourse` clauses from the **full
exhibit text**, not the 8-K excerpt. No re-fetch. Top: SpaceX $20B (already holds the EX-10 bridge agreement).

### B. `FETCH_EXHIBIT_FROM_ACCESSION` — 208 rows — targeted acquisition
The blocker's source is an **8-K body / prospectus that names** the agreement; the agreement is (typically) an `EX-10`/`EX-4`
exhibit on the **same accession**. **Action:** fetch that exhibit — `scripts/build_edgar_exhibit_manifest.py` does exactly
this (reads a primary manifest, fetches archive indexes for selected accessions). Top targets by exposure:
- Broadcom — credit agreement — accession `000119312525158202` — $30.4B
- Georgia Power — credit agreement — `000110465925024497` — $18.4B
- MiniMed Group — `000162828026003281` — $18.0B
- Lincoln National, Comcast, Duke Energy, Eaton — credit agreements (accessions in the CSV)

## CSV columns
`packet_id, entity, exposure_basis_usd, remaining_gap, source_form, named_agreement, accession, action, source_uri`

## Recommendation
1. **RE_EXTRACT_DEPTH (101)** is the cheapest win — clause-level re-extraction of exhibits you already hold could clear ~101
   collateral/recourse blockers with no acquisition. (Pairs with the collateral/recourse heuristics in `claude_gap_sampling`.)
2. **FETCH_EXHIBIT_FROM_ACCESSION (208)**: build a targeted exhibit manifest for these accessions' EX-10/EX-4 docs,
   prioritized by exposure; bounded fetch under the SEC fair-access lane.

## Verification
`python3` filter on `data/reports/materiality_adjudication_decisions.csv` for `decision==needs_deeper_extraction` and the
two collateral/recourse gaps reproduces the 492 / 309 split. After re-extraction or fetch, those gap counts should drop.
