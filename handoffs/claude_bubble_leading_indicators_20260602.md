# Bubble leading-indicator catalog (#26) — source-backed crack-window monitors

**Base:** current main `8bea1ea`. READ-ONLY; no prod writes.
**Deliverable:** `handoffs/fixtures/bubble_leading_indicators_20260602.csv` (9 indicators × 7 categories:
indicator, category, crack-signal threshold, data source, ties-to-finding, cadence, negative control).
Impact: **future architecture (forward monitoring).** The forward complement to the point-in-time diligence
checklist (#33): the checklist says where the evidence stands today; this catalog says **what to watch for the crack.**

## The 9 monitors (each tied to a session finding)
1. **Direct-tier credit spreads** (daily) — widening >300bp on IREN/TeraWulf/CoreWeave/Applied Digital. The $184.8B
   direct AI tier (top-3 = 56%) is where SEC-filable default risk concentrates. ← `ai_attribution_decomposition`.
2. **Refinancing failures** (per-filing) — a direct-tier issuer pulls/reprices a refi or fails to roll a maturity-wall
   row. ← `maturity_rate_coverage_expansion` (#18).
3. **Hyperscaler PPA/DC cancellations** (monthly) — Amazon/Google/Microsoft Energy defers capacity; tracker cancelled
   MW (now 18,514) rises. ← `downside_bearer_resolver` / `physical_grid_refresh`.
4. **GPU resale / rental decline** (weekly) — secondary H100/H200 or Lambda/RunPod rates fall >20% QoQ. Fills the
   `rental_rate_decline_pct` null-10/10 gap. ← `compute_economics_refresh`.
5. **Utilization miss** (quarterly) — neocloud utilization <70% or backlog flattens. The absent compute signal. ← compute lane.
6. **Power/interconnection delay** (quarterly) — a top-15 DC project's ISO queue slips >1yr / IA unexecuted. ← physical lane (0 MW firm).
7. **Utility rate-case denial / stranded-asset writedown** (per-docket) — a PUC denies DC-driven cost recovery. ← `utility_ratepayer_downside` (#31).
8. **Covenant breach / going-concern** (per-filing) — a direct-tier waiver / DSCR <1.0. ← diligence checklist (DSCR null).
9. **Dilution-to-survive equity raises** (per-filing) — back-to-back ATM/convert raises funding opex/refi, not capex. ← reselect/shelf taxonomy.

## Design principle (why each carries a negative control)
Every indicator pairs a crack-signal with a **negative control** to avoid false alarms: macro IG-spread moves ≠ AI
crack (watch the direct tier); a single project slip ≠ systemic delay (watch the named top-15); amend-and-extend ≠
covenant breach (require a waiver/going-concern); growth capex raises are bullish (flag only loss/refi funding). The
catalog is deliberately scoped to the **$184.8B direct tier + the demand/physical/ratepayer channels** this engine
identified — not the $3.742T headline, 89% of which is not AI-linked.

## Verified vs proposed
- VERIFIED: the data sources exist (TRACE, FERC EQR dataset 17, ISO queues, PUC dockets, the report's tracker
  cancelled_capacity_mw = 18,514) and each indicator traces to a delivered fixture.
- PROPOSED: the thresholds + cadences + the monitoring design. This is a future-architecture spec (a monitor would
  be built downstream); no metric change.
