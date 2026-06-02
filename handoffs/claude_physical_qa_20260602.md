# Physical Thin-Layer QA — 2026-06-02 (fallback backlog: physical/compute thin-layer QA)

- **From:** Claude (worker) · **For:** Codex · **Branch:** `claude/report-qa`
- Read-only analysis of `data/physical/*` + `physical_risk_summary.json`. The physical layer answers the core
  **"% of announced capacity deliverable / when does power & permitting gate the buildout"** questions.
- **Finding: broad project coverage (2,125) but thin evidence linkage + missing status → it can't yet produce defensible physical-risk conclusions.** (Consistent with the original brief's "physical constraints: early 15–25%.")

## 1. `status` field is 100% empty — impact: **blocks the "% deliverable" question**
`data/physical/projects.csv`: **2,125 projects, ALL `status=""`.** Can't distinguish announced / under-construction /
operating / cancelled → **can't compute "% of announced capacity at execution risk."** The tracker source almost
certainly carries status; the extraction dropped it. **Fix:** populate `status` in `tracker_projects` extraction.
**Test:** `test_tracker_project_status_populated`.

## 2. Evidence linkage is ultra-thin — impact: physical-risk scores are mostly "no-evidence" defaults
`physical_risk_summary`: **2,140 assets assessed**, but only **24** with queue evidence, **98** with permit evidence,
**2** with equipment evidence (~1–5%). The **85 "critical/high"** assessments are dominated by blockers like
*"No source-backed grid interconnection record attached"* / *"No source-backed permit record attached"* — i.e. **absence
of evidence, not measured deliverability risk.** So the layer can't currently distinguish "high risk" from "unlinked."
**Fix:** deepen queue/permit/equipment matching (the match audits link <5% of projects). Pairs with the
acquisition-target pattern in `claude_acquisition_targets`.

## 3. Generic duplicate project names — impact: **MW double-count risk** (triage / future-architecture)
Many projects share generic tracker labels: `"h5 data center"` 10×, `"cielo digital infrastructure"` 11×,
`"meta data center"` 9×, `"amazon data center"` 7×, `"tract data center"` 7×. Summing MW by name would either
double-count one campus or conflate distinct campuses. **Fix:** canonical project IDs keyed on `(owner, county/location, POI)`
— not the generic name — before MW aggregation. **Test:** `test_projects_canonicalized_before_mw_rollup`.

## 4. Match confidence — minor false-positive risk
queue matches 26 (conf 0.74–0.99, none weak); permit 266 (**11 weak <0.7**); equipment 245 (**8 weak <0.7**). 19 weak
matches worth a spot-review, but match quality is mostly fine.

## Net (impact: acquisition scope + future-architecture)
Breadth (2,125 projects) without (a) **status** (100% empty → blocks the deliverability %), (b) **evidence linkage**
(<5% of projects), or (c) **name canonicalization** (MW double-count). This is why the report correctly can't yet answer
"% of announced capacity deliverable." **Cheapest high-value win: populate `status` (it's in the tracker data already),**
then deepen evidence matching. **Verification:** `python3` over `data/physical/projects.csv` shows all-blank status and the
duplicate-name counts; `physical_risk_summary.json` shows the 24/98/2 evidence linkage.
