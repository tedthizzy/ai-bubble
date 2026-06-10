"""Satellite construction-progress detection for AI data-center sites.

Implements the goal's "satellite imagery + construction progress" capability via
Sentinel-2 change detection: for a site's coordinates, compare a BEFORE and AFTER
median composite and read the spectral signature of a data-center buildout --
vegetation cleared (NDVI falls) and bare soil / built-up surface appears (BSI/NDBI
rise). A strong NDVI-down + BSI/NDBI-up signal is active construction or clearing;
this gives a primary, non-filing, physical-reality check on whether announced
capacity is actually being built on the ground.

The band math and the construction classification here are PURE and unit-tested
(no Earth Engine needed for the gate). The live Sentinel-2 pull is in
``scripts/satellite_progress.py``, which feeds these functions real reflectances.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def ndvi(bands: dict[str, float]) -> float:
    """Normalized Difference Vegetation Index = (NIR-Red)/(NIR+Red). Sentinel-2 B8/B4."""

    nir, red = bands.get("B8", 0.0), bands.get("B4", 0.0)
    return round(_safe_div(nir - red, nir + red), 4)


def ndbi(bands: dict[str, float]) -> float:
    """Normalized Difference Built-up Index = (SWIR-NIR)/(SWIR+NIR). Sentinel-2 B11/B8."""

    swir, nir = bands.get("B11", 0.0), bands.get("B8", 0.0)
    return round(_safe_div(swir - nir, swir + nir), 4)


def bsi(bands: dict[str, float]) -> float:
    """Bare Soil Index = ((SWIR+Red)-(NIR+Blue))/((SWIR+Red)+(NIR+Blue)). B11,B4,B8,B2."""

    swir, red = bands.get("B11", 0.0), bands.get("B4", 0.0)
    nir, blue = bands.get("B8", 0.0), bands.get("B2", 0.0)
    return round(_safe_div((swir + red) - (nir + blue), (swir + red) + (nir + blue)), 4)


def classify_construction(before: dict[str, float], after: dict[str, float]) -> dict[str, Any]:
    """Classify the construction signal from before/after band composites."""

    ndvi_before, ndvi_after = ndvi(before), ndvi(after)
    ndbi_before, ndbi_after = ndbi(before), ndbi(after)
    bsi_before, bsi_after = bsi(before), bsi(after)
    ndvi_delta = round(ndvi_after - ndvi_before, 4)
    ndbi_delta = round(ndbi_after - ndbi_before, 4)
    bsi_delta = round(bsi_after - bsi_before, 4)

    # Construction = vegetation cleared (NDVI down) + bare/built surface up (BSI or NDBI up).
    if ndvi_delta <= -0.10 and (bsi_delta >= 0.05 or ndbi_delta >= 0.05):
        signal = "active_construction_or_clearing"
    elif ndbi_delta >= 0.10:
        signal = "built_up_increase"
    elif abs(ndvi_delta) < 0.05 and abs(ndbi_delta) < 0.05 and abs(bsi_delta) < 0.05:
        signal = "no_significant_change"
    else:
        signal = "mixed_or_minor_change"

    return {
        "construction_signal": signal,
        "ndvi_delta": ndvi_delta,
        "ndbi_delta": ndbi_delta,
        "bsi_delta": bsi_delta,
        "ndvi_before": ndvi_before,
        "ndvi_after": ndvi_after,
        "ndbi_after": ndbi_after,
    }


def load_satellite_observations(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        loaded = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    return [r for r in loaded if isinstance(r, dict)] if isinstance(loaded, list) else []


def aggregate_satellite_observations(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize construction signals across observed AI data-center sites."""

    usable = [r for r in records if (r.get("classification") or {}).get("construction_signal")]
    if not usable:
        return {"status": "blocked_no_satellite_observations", "site_count": 0}

    by_signal: dict[str, int] = {}
    active: list[dict[str, Any]] = []
    no_change: list[dict[str, Any]] = []
    for r in usable:
        sig = str(r["classification"]["construction_signal"])
        by_signal[sig] = by_signal.get(sig, 0) + 1
        row = {
            "site": str(r.get("site") or "")[:60],
            "state": r.get("state"),
            "capacity_mw": r.get("capacity_mw"),
            "construction_signal": sig,
            "ndvi_delta": r["classification"].get("ndvi_delta"),
            "ndbi_delta": r["classification"].get("ndbi_delta"),
        }
        if sig in ("active_construction_or_clearing", "built_up_increase"):
            active.append(row)
        elif sig == "no_significant_change":
            no_change.append(row)

    active.sort(key=lambda x: x.get("capacity_mw") or 0, reverse=True)
    no_change.sort(key=lambda x: x.get("capacity_mw") or 0, reverse=True)
    total = len(usable)
    active_pct = round(100 * len(active) / total, 1) if total else None

    return {
        "status": "source_backed",
        "site_count": total,
        "signal_counts": by_signal,
        "active_construction_sites": len(active),
        "active_construction_pct": active_pct,
        "no_change_sites": len(no_change),
        "top_active_sites": active[:8],
        "high_capacity_no_change_sites": no_change[:8],
        "physical_read": _read(active, no_change, total),
        "note": (
            "Sentinel-2 before/after change detection over the announced AI data-center coordinates. "
            "'active_construction_or_clearing' = vegetation cleared (NDVI down) + bare/built surface up "
            "(BSI/NDBI up). A primary, non-filing physical check on whether announced capacity is being "
            "built; high-capacity sites with NO change are the stranded/timeline-slippage tells. "
            "Cloud/seasonal noise can blur the signal -- read with the construction-status proxy."
        ),
    }


def _read(active: list[dict[str, Any]], no_change: list[dict[str, Any]], total: int) -> str:
    if total and len(no_change) >= len(active):
        return (
            f"buildout_lagging_announcements: of {total} satellite-observed sites, only {len(active)} "
            f"show active construction/built-up change while {len(no_change)} show NO significant "
            "ground change -- consistent with announced-but-not-built capacity (the physical-mismatch "
            "thesis), with the high-capacity no-change sites the clearest stranding/slippage tells."
        )
    return (
        f"buildout_visibly_underway: {len(active)} of {total} observed sites show active construction "
        "or built-up change on satellite -- the announced capacity has a real ground footprint at "
        "most observed sites; the no-change sites remain the slippage watch-list."
    )
