#!/usr/bin/env python3
"""Publish dated source coverage without relabeling historical report judgments."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def read(path: Path) -> Any:
    return json.loads(path.read_text())


def build(run: Path) -> dict[str, Any]:
    graph = read(ROOT / "viz/graph_data.json")
    live = read(ROOT / "viz/live.json")
    panel = read(ROOT / "analysis" / f"case_zero_financials_{run.name.removeprefix('refresh_')}_v4.json")
    sources = []
    for name in ("public", "gleif", "dynamic", "queue_corrections"):
        directory = run / name
        summary = directory / "source_catalog_acquisition.summary.json"
        if not summary.exists():
            continue
        result = read(summary)
        sources.append({"batch": name, "artifacts": result["artifacts_acquired"],
                        "rows": result["extracted_rows"], "errors": sorted(result["errors"])})
    current: list[dict[str, Any]] = []
    with (run / "dynamic_acquisition_catalog.csv").open(newline="") as stream:
        current.extend({
                "source": row["source_id"],
                "source_uri": row["source_uri"],
                "observation_date": row.get("meta_content_date") or row.get("meta_as_of") or
                    row.get("meta_title") or None,
                "published": row.get("meta_publish_date") or row.get("meta_release_date") or None,
                "next_release": row.get("meta_next_release_date") or None,
            } for row in csv.DictReader(stream))
    with sqlite3.connect(f"file:{run / 'document_queue.sqlite3'}?mode=ro", uri=True) as database:
        counts = dict(database.execute("SELECT status,COUNT(*) FROM documents GROUP BY status"))
        failed_urls = {row[0] for row in database.execute("SELECT url FROM documents WHERE status='failed'")}
    recovered: set[str] = set()
    for result in (run / "source_gap_retries").glob("*/retry-result.json"):
        with (result.parent / "edgar/edgar_document_inventory.csv").open(newline="") as stream:
            recovered.update(row["filing_url"] for row in csv.DictReader(stream))
    unresolved = len(failed_urls - recovered)
    latest = [e["latest_periodic_filing"] for e in panel["entities"] if e.get("latest_periodic_filing")]
    nav = read(ROOT / "analysis" / f"bdc_nav_{panel['as_of']}.json")
    fdic = read(ROOT / "analysis" / f"fdic_bank_distress_{panel['as_of']}.json")
    with (ROOT / "data/edgar_acquisition_2026-09-16/edgar_document_inventory.csv").open(newline="") as stream:
        baseline_count = sum(1 for _ in csv.DictReader(stream))
    status = {
        "snapshot_at_pacific": datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
        "refresh_as_of": panel["as_of"],
        "complete": (run / "run-result.json").exists() and not counts.get("queued") and not counts.get("inflight") and not unresolved,
        "report": {
            "generated_from": graph.get("meta", {}).get("generated_from"),
            "current_verdict_recomputed": False,
            "reason": "The adjudicated core and its judgments retain their original evidence date.",
        },
        "market": {
            "generated_utc": live["generated_utc"],
            "price_dates": sorted({v["date"] for v in live.get("quotes", {}).values()}),
            "credit_dates": sorted({v["date"] for v in live.get("credit", {}).values() if isinstance(v, dict) and v.get("date")}),
            "nav_periods": sorted({v["nav_asof"] for v in nav["bdc"].values()}),
            "source_status": live.get("source_status", {}),
        },
        "financial_panel": {
            "targets": panel["target_count"], "complete": panel["complete_count"],
            "filing_dates": sorted({v["filing_date"] for v in latest}),
            "periods": sorted({v["report_date"] for v in latest if v.get("report_date")}),
        },
        "sec_acquisition": {
            "new_run_queue": counts,
            "baseline_inventory": baseline_count,
            "recovered_failures": len(failed_urls & recovered),
            "unresolved_source_errors": unresolved,
            "note": "Queue counts exclude the retained baseline. Downloads are not unique obligations.",
            "status": "incomplete" if counts.get("queued") or counts.get("inflight") or unresolved else "queue_drained",
        },
        "public_batches": sources,
        "current_public_releases": current,
        "fdic": {"period": fdic["quarter"], "institutions": fdic["institutions_returned"]},
        "source_corrections": [
            "The July EIA URL failed; the latest August workbook was acquired.",
            "The first PJM serial export lacked the anonymous public header; a corrected full export was acquired.",
            "ERCOT header selection was repaired; the corrected output retains both generator sheets.",
        ],
        "limits": [
            "Retrieval date and observation date are separate.",
            "Source rows and graph edges are not additive debt.",
            "The June core confidence readings are historical judgments, not calibrated probabilities.",
        ],
    }
    return status


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("viz/freshness.json"))
    args = parser.parse_args()
    status = build(args.run)
    if args.output.exists():
        folder = ROOT / ".codex/refresh-status-snapshots" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
        folder.mkdir(parents=True)
        shutil.copy2(args.output, folder / args.output.name)
    args.output.write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps({"output": str(args.output), "complete": status["complete"],
                      "sec_queue": status["sec_acquisition"]["new_run_queue"]}))


if __name__ == "__main__":
    main()
