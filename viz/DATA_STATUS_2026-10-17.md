# Explorer source status, October 17, 2026

The market overlay contains October 16 closing prices and October 15 credit
observations. The NAV denominators are the latest reported June 30 quarterly
values found in saved SEC periodic filings.

The adjudicated core, extracted contract field, cascade, and confidence
judgments still come from the June 3 report. The new cached layout changes
placement and browser work. It does not recompute that report's financial
conclusions. The confidence readings remain historical judgments.

The October source acquisition is incomplete. See freshness.json for its dated
snapshot and [the operations evidence](../analysis/refresh_operations_2026-10-17.md)
for verified results, source corrections, and remaining work. Download counts
are not unique obligations or a proof of full economic coverage.

The complete latest ownership graph is a separate source layer. It does not
imply a join to the adjudicated capital graph. Public-source retrieval dates
are separate from reporting periods.

At the earlier source checkpoint, browser verification and publication were
pending. Desktop and mobile Chrome checks subsequently completed at 18:50 PDT.
The evidence is recorded in
[viz_browser_validation_2026-10-17.json](../analysis/viz_browser_validation_2026-10-17.json).
GitHub deployment remains a separate stage with its own workflow and live-file
checks. A git commit alone does not establish the live site's runtime state.

The October dated engine snapshot is
[dated_engine_2026-10-17_v1.md](../analysis/dated_engine_2026-10-17_v1.md).
It includes current deterministic market components, the financial panel,
47,232 FERC source rows, 88 GPU quotes across four providers, and physical
rollups from the selected current sources. It explicitly marks SEC acquisition
incomplete. S1 is stale and S4 is unmeasured. It does not replace the June core.

The FERC API-page identity bug and Modal pricing-page changes were repaired.
The new normalized outputs retain their original source hashes and dates.
Retained batch totals overlap and must not be added together.
