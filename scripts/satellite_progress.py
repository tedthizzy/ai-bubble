#!/usr/bin/env python
"""Sentinel-2 before/after construction detection over ALL georeferenced AI sites.

Selects every AI / data-center site in data/physical/projects.csv that has
coordinates, and computes a BEFORE and AFTER Sentinel-2 SR median composite per
site using SERVER-SIDE batched ``reduceRegions`` (one Earth Engine call per batch
of sites, not per site) -- so it scales to hundreds of sites cheaply (well within
the free EECU budget). Runs the construction change-detection
(bubble.ingestion.satellite) and writes data/physical/satellite_observations.json.

Requires GEE auth (gcloud application-default + a registered project). Project id
defaults to GEE_PROJECT env var or burry-498315.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import ee

from bubble.ingestion.satellite import aggregate_satellite_observations, classify_construction

_BANDS = ["B2", "B4", "B8", "B11"]
_BEFORE = ("2023-06-01", "2024-06-01")
_AFTER = ("2025-09-01", "2026-06-03")
_BUFFER_M = 500
_AI_KEYS = ("data center", "datacenter", "data centre", "campus", "hyperscale", "gigafactory")


def _is_ai_site(row: dict[str, str]) -> bool:
    text = f"{row.get('name', '')} {row.get('category', '')} {row.get('notes', '')}".lower()
    return any(k in text for k in _AI_KEYS)


def _coord(row: dict[str, str]) -> bool:
    return bool((row.get("location_lat") or "").strip() and (row.get("location_lon") or "").strip())


def _mw(row: dict[str, str]) -> float:
    for k in ("capacity_mw", "capacity_mw_high"):
        try:
            return float(row.get(k) or 0)
        except (TypeError, ValueError):
            continue
    return 0.0


def _batch_bands(sites: list[dict[str, str]], start: str, end: str) -> dict[int, dict[str, float]]:
    """One server-side reduceRegions over all site buffers in this batch."""

    feats = []
    for i, s in enumerate(sites):
        geom = ee.Geometry.Point([float(s["location_lon"]), float(s["location_lat"])]).buffer(
            _BUFFER_M
        )
        feats.append(ee.Feature(geom, {"idx": i}))
    fc = ee.FeatureCollection(feats)
    col = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(fc.geometry().bounds())
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40))
    )
    img = col.median().select(_BANDS).divide(10000)
    reduced = img.reduceRegions(
        collection=fc, reducer=ee.Reducer.mean(), scale=20, tileScale=4
    ).getInfo()
    out: dict[int, dict[str, float]] = {}
    for feat in reduced.get("features", []):
        props = feat.get("properties", {})
        idx = props.get("idx")
        bands = {b: float(props[b]) for b in _BANDS if props.get(b) is not None}
        if idx is not None:
            out[int(idx)] = bands
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default="burry-498315")
    parser.add_argument("--batch-size", type=int, default=120)
    parser.add_argument("--max-sites", type=int, default=10000)
    parser.add_argument("--min-mw", type=float, default=0.0)
    args = parser.parse_args()
    ee.Initialize(project=args.project)

    with open("data/physical/projects.csv", newline="") as fh:
        rows = list(csv.DictReader(fh))
    sites = [r for r in rows if _is_ai_site(r) and _coord(r) and _mw(r) >= args.min_mw]
    sites.sort(key=_mw, reverse=True)
    sites = sites[: args.max_sites]
    print(f"Analyzing {len(sites)} georeferenced AI/data-center sites (batch={args.batch_size})")

    observations: list[dict[str, Any]] = []
    for start in range(0, len(sites), args.batch_size):
        batch = sites[start : start + args.batch_size]
        try:
            before = _batch_bands(batch, *_BEFORE)
            after = _batch_bands(batch, *_AFTER)
        except Exception as e:  # batch-level resilience for live GEE
            print(f"  batch {start}: ERROR {type(e).__name__}: {str(e)[:90]} (skipping)")
            continue
        for i, r in enumerate(batch):
            b, a = before.get(i, {}), after.get(i, {})
            if len(b) < 4 or len(a) < 4:
                continue
            cls = classify_construction(b, a)
            observations.append(
                {
                    "site": r.get("name", "")[:60],
                    "state": r.get("state"),
                    "capacity_mw": _mw(r),
                    "lat": float(r["location_lat"]),
                    "lon": float(r["location_lon"]),
                    "before_window": _BEFORE,
                    "after_window": _AFTER,
                    "classification": cls,
                    "source": "Sentinel-2 SR Harmonized via Google Earth Engine",
                }
            )
        print(f"  batch {start}-{start + len(batch)}: {len(observations)} observations so far")

    out_path = Path("data/physical/satellite_observations.json")
    out_path.write_text(json.dumps(observations, indent=2))
    agg = aggregate_satellite_observations(observations)
    print(f"\nWrote {len(observations)} observations to {out_path}")
    print(
        "Aggregate:",
        json.dumps(
            {
                k: v
                for k, v in agg.items()
                if k not in ("top_active_sites", "high_capacity_no_change_sites")
            },
            indent=2,
        ),
    )


if __name__ == "__main__":
    main()
