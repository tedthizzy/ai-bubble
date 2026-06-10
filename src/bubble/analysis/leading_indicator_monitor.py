"""Forward leading-indicator monitor: the dials to watch for the crack, with current readings.

Burry's edge in 2008 was not just "it is a bubble" but a SPECIFIC set of
observable dials that would move first. This synthesizes the engine's
source-backed layers into a structured watchlist: each indicator names what it
measures, its current reading (where source-backed), the direction that signals
stress, a first-principles trigger where one is defensible, and the data feed to
refresh on update -- so the system can "continuously update as new data arrives"
and is monitorable, not just a one-shot verdict.

`currently_flashing` is reserved for a MEASURED reading that already sits past a
defensible FIRST-PRINCIPLES line (coverage < 1.0; the majority of sites un-built;
a single customer > 50% of revenue; a present filing-verified vendor round-trip;
GPU economic life below the booked schedule). Forward triggers that have not yet
breached are 'watch', never 'flashing' -- the monitor does not cry wolf. The
two-sided dials (equipment lead times) are tracked but never flashed, since both
directions carry information (loosening = demand cooling; tightening = revenue
conversion capped).
"""

from __future__ import annotations

from typing import Any

_EXISTENTIAL_CONCENTRATION_PCT = 50.0
_MAJORITY_PCT = 50.0
_COVERAGE_FLOOR = 1.0


def _num(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _cluster_coverage(m: dict[str, Any]) -> dict[str, Any]:
    layer = m.get("cluster_interest_coverage", {}) or {}
    reading = _num(layer.get("cluster_ebitda_interest_coverage"))
    backed = layer.get("status") == "source_backed" and reading is not None
    return {
        "key": "cluster_interest_coverage",
        "indicator": "Cluster EBITDA / interest coverage",
        "measures": "Whether the financed cluster's operations cover interest before any principal.",
        "current_reading": reading,
        "stress_direction": "falling",
        "trigger": "coverage < 1.0 (operations do not cover interest)",
        "data_feed": "per-issuer 10-K/10-Q EBITDA + interest expense (re-aggregate cluster census)",
        "current_status": "source_backed" if backed else "watch",
        "currently_flashing": bool(backed and reading is not None and reading < _COVERAGE_FLOOR),
    }


def _gpu_life_gap(m: dict[str, Any]) -> dict[str, Any]:
    gap = (m.get("gpu_economics_mismatch", {}) or {}).get("source_backed_gap", {}) or {}
    backed = gap.get("status") == "source_backed"
    return {
        "key": "gpu_economic_life_gap",
        "indicator": "GPU economic life vs booked depreciation schedule",
        "measures": "Whether the collateral decays faster than it is depreciated (earnings/collateral quality).",
        "current_reading": "economic life < booked schedule (confirmed)" if backed else None,
        "stress_direction": "widening gap / accelerating rental-rate compression",
        "trigger": "secondary GPU rental/resale price falling faster than the booked useful life implies",
        "data_feed": "secondary GPU rental-rate and resale-price prints; issuer useful-life disclosures",
        "current_status": "source_backed" if backed else "watch",
        "currently_flashing": bool(backed),
    }


def _refi_wall(m: dict[str, Any]) -> dict[str, Any]:
    rw = m.get("refi_wall", {}) or {}
    backed = rw.get("status") == "source_backed"
    return {
        "key": "near_term_refi_wall",
        "indicator": "Near-term (2025-2027) refinancing roll on negative carry",
        "measures": "Debt that must be rolled while the issuer is cash-flow negative, exposed to rate at roll.",
        "current_reading": _num(rw.get("near_term_2025_2027_usd")),
        "stress_direction": "rising refi rate / shrinking covenant headroom into the roll",
        "trigger": "refi rate at roll exceeds the asset cash yield (deepening negative carry)",
        "data_feed": "issuer maturity schedules + credit-spread / new-issue coupon prints",
        "current_status": "source_backed" if backed else "watch",
        # Forward trigger: present but not yet breached -> watch, not flashing.
        "currently_flashing": False,
    }


def _vendor_round_trip(m: dict[str, Any]) -> dict[str, Any]:
    cf = m.get("circular_financing", {}) or {}
    hub = cf.get("reciprocal_hub") or {}
    backed = cf.get("status") == "source_backed"
    rt = _num(hub.get("filing_verified_round_trip_count"))
    return {
        "key": "vendor_round_trip_dependence",
        "indicator": "Vendor round-trip dependence (supplier-as-investor)",
        "measures": "Filing-verified loops where the dominant GPU supplier also funds the buyer (NVIDIA).",
        "current_reading": rt,
        "stress_direction": (
            "either way is a tell: MORE injections = demand less arm's-length; the supplier HALTING "
            "injections removes a prop the buyers may not stand without"
        ),
        "trigger": "a filing-verified reciprocal loop exists (present), or NVIDIA pauses customer funding",
        "data_feed": "NVIDIA equity-injection announcements + investee 10-K subsequent-events / PIPE filings",
        "current_status": "source_backed" if backed else "watch",
        "currently_flashing": bool(backed and rt is not None and rt > 0),
    }


def _satellite_stall(m: dict[str, Any]) -> dict[str, Any]:
    sat = m.get("satellite_construction", {}) or {}
    site_n = _num(sat.get("site_count"))
    no_change = _num(sat.get("no_change_sites"))
    backed = sat.get("status") == "source_backed" and bool(site_n)
    pct = (
        round(100 * no_change / site_n, 1) if backed and no_change is not None and site_n else None
    )
    return {
        "key": "satellite_construction_stall",
        "indicator": "Satellite construction-stall rate",
        "measures": "Share of georeferenced announced sites with no visible ground construction (Sentinel-2).",
        "current_reading": pct,
        "stress_direction": "rising stall rate (announced != real; debt service can precede energized capacity)",
        "trigger": "majority of observed sites show no construction (> 50%)",
        "data_feed": "Sentinel-2 change detection over the site list (re-run satellite_progress.py)",
        "current_status": "source_backed" if backed else "watch",
        "currently_flashing": bool(pct is not None and pct > _MAJORITY_PCT),
    }


def _equipment_lead(m: dict[str, Any]) -> dict[str, Any]:
    eq = m.get("equipment_bottlenecks", {}) or {}
    backed = eq.get("status") == "source_backed"
    return {
        "key": "equipment_lead_times",
        "indicator": "Supply-side equipment lead times (CoWoS/HBM, transformers, turbines)",
        "measures": "Whether the physical buildout is gated by single-source/duopoly chokepoints.",
        "current_reading": _num(eq.get("max_lead_time_months")),
        "stress_direction": "two-sided: loosening = demand cooling tell; tightening = revenue conversion capped",
        "trigger": "no single line -- a regime change in either direction is the signal",
        "data_feed": "supplier lead-time disclosures (TSMC/SK hynix/GE Vernova etc.); order-book commentary",
        "current_status": "source_backed" if backed else "watch",
        # Two-sided dial: informative in both directions, so never 'flashing'.
        "currently_flashing": False,
    }


def _customer_concentration(m: dict[str, Any]) -> dict[str, Any]:
    maxc = _num(m.get("_max_single_customer_pct"))
    return {
        "key": "customer_concentration",
        "indicator": "Single-customer revenue concentration (max issuer)",
        "measures": "Whether any issuer depends on one customer for an existential share of revenue.",
        "current_reading": maxc,
        "stress_direction": "any large-customer renegotiation, pullback, or non-performance",
        "trigger": "single customer > 50% of an issuer's revenue (existential)",
        "data_feed": "issuer 10-K customer-concentration disclosure; RPO / commitment renegotiation news",
        "current_status": "source_backed" if maxc is not None else "watch",
        "currently_flashing": bool(maxc is not None and maxc > _EXISTENTIAL_CONCENTRATION_PCT),
    }


def build_leading_indicator_monitor(m: dict[str, Any]) -> dict[str, Any]:
    """Synthesize the source-backed layers into a monitorable forward watchlist."""

    m = m or {}
    indicators = [
        _cluster_coverage(m),
        _gpu_life_gap(m),
        _refi_wall(m),
        _vendor_round_trip(m),
        _satellite_stall(m),
        _equipment_lead(m),
        _customer_concentration(m),
    ]
    if not any(i["current_status"] == "source_backed" for i in indicators):
        return {"status": "blocked_no_indicators", "indicators": []}

    backed = [i for i in indicators if i["current_status"] == "source_backed"]
    flashing = [i for i in indicators if i["currently_flashing"]]
    return {
        "status": "source_backed",
        "indicator_count": len(indicators),
        "source_backed_reading_count": len(backed),
        "currently_flashing_count": len(flashing),
        "currently_flashing": [i["key"] for i in flashing],
        "indicators": indicators,
        "composite_read": (
            f"{len(flashing)} of {len(indicators)} leading indicators are ALREADY flashing on a measured, "
            "first-principles line (not a forecast): "
            f"{', '.join(i['indicator'] for i in flashing)}. The remaining dials are forward triggers or "
            "two-sided monitors to watch into the 2025-Q3..2027-Q3 refinancing window. The financed core "
            "is not waiting on a future catalyst to be fragile -- several stress conditions are present "
            "now; the open question is the timing of the financing/demand shock that converts present "
            "fragility into distress."
            if flashing
            else "No indicator currently sits past a first-principles stress line; all are forward watches."
        ),
        "note": (
            "Forward leading-indicator monitor synthesized from the source-backed layers. Each indicator "
            "names its data feed so updates are mechanical. 'currently_flashing' requires a MEASURED "
            "reading past a defensible first-principles line; forward and two-sided dials are 'watch', "
            "never flashed. This is the 'continuously update / leading indicators' capability, grounded "
            "in the same primary sources as the verdict."
        ),
    }
