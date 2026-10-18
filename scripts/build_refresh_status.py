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


def dated_market(root: Path, as_of: str) -> tuple[Path, dict[str, Any]]:
    """Keep an overnight completion from using market observations after its cutoff."""
    path = root / "analysis" / f"market_snapshot_{as_of}.json"
    snapshot = read(path)
    if snapshot["as_of_pacific"] != as_of:
        raise ValueError("Market snapshot cutoff differs from the report")
    live = snapshot["live"]
    for group in ("quotes", "credit", "bdc", "adjacent"):
        for row in live.get(group, {}).values():
            if isinstance(row, dict) and row.get("date", "") > as_of:
                raise ValueError(f"Market observation postdates the cutoff: {group}")
    return path, live


def build(run: Path) -> dict[str, Any]:  # noqa: PLR0915 - assemble independent source status records
    graph = read(ROOT / "viz/graph_data.json")
    market_path, live = dated_market(ROOT, run.name.removeprefix("refresh_"))
    panel = read(
        ROOT / "analysis" / f"case_zero_financials_{run.name.removeprefix('refresh_')}_v4.json"
    )
    sources = []
    for name in (
        "public",
        "gleif",
        "dynamic",
        "queue_corrections",
        "dynamic_catalog_repair/acquired",
    ):
        directory = run / name
        summary = directory / "source_catalog_acquisition.summary.json"
        if not summary.exists():
            continue
        result = read(summary)
        sources.append(
            {
                "batch": name,
                "artifacts": result["artifacts_acquired"],
                "rows": result["extracted_rows"],
                "errors": sorted(result["errors"]),
            }
        )
    current: list[dict[str, Any]] = []
    with (run / "dynamic_acquisition_catalog.csv").open(newline="") as stream:
        current.extend(
            {
                "source": row["source_id"],
                "source_uri": row["source_uri"],
                "observation_date": row.get("meta_content_date")
                or row.get("meta_as_of")
                or row.get("meta_title")
                or None,
                "published": row.get("meta_publish_date") or row.get("meta_release_date") or None,
                "next_release": row.get("meta_next_release_date") or None,
            }
            for row in csv.DictReader(stream)
        )
    repair_catalog = run / "dynamic_catalog_repair/catalog.csv"
    if repair_catalog.exists():
        with repair_catalog.open(newline="") as stream:
            first_ferc = next(
                (row for row in csv.DictReader(stream) if row["corpus"] == "ppas"), None
            )
        if first_ferc:
            current.append(
                {
                    "source": "FERC Entities to PPAs",
                    "source_uri": first_ferc["source_uri"],
                    "observation_date": first_ferc.get("meta_data_last_updated"),
                    "discovered_records": int(first_ferc["meta_total_count"]),
                }
            )
    with sqlite3.connect(f"file:{run / 'document_queue.sqlite3'}?mode=ro", uri=True) as database:
        counts = dict(database.execute("SELECT status,COUNT(*) FROM documents GROUP BY status"))
        failed_urls = {
            row[0] for row in database.execute("SELECT url FROM documents WHERE status='failed'")
        }
    recovered: set[str] = set()
    for result in (run / "source_gap_retries").glob("*/retry-result.json"):
        with (result.parent / "edgar/edgar_document_inventory.csv").open(newline="") as stream:
            recovered.update(row["filing_url"] for row in csv.DictReader(stream))
    unresolved = len(failed_urls - recovered)
    exhibits: dict[str, Any] = {"status": "not_started", "complete": False}
    exhibit_root = run / "exhibit_completion"
    if (exhibit_root / "parents.sqlite3").is_file():
        with sqlite3.connect(f"file:{exhibit_root / 'parents.sqlite3'}?mode=ro", uri=True) as db:
            parents = dict(db.execute("SELECT status,COUNT(*) FROM parents GROUP BY status"))
            columns = {row[1] for row in db.execute("PRAGMA table_info(parents)")}
            index_parsers = (
                dict(db.execute("SELECT index_parser,COUNT(*) FROM parents GROUP BY index_parser"))
                if "index_parser" in columns
                else {"filename_inference": sum(parents.values())}
            )
        with sqlite3.connect(
            f"file:{exhibit_root / 'document_queue.sqlite3'}?mode=ro", uri=True
        ) as db:
            attachments = dict(db.execute("SELECT status,COUNT(*) FROM documents GROUP BY status"))
            failed_attachments = {
                row[0] for row in db.execute("SELECT url FROM documents WHERE status='failed'")
            }
        recovered_attachments: set[str] = set()
        for inventory in (exhibit_root / "source_gap_retries").glob(
            "*/edgar/edgar_document_inventory.csv"
        ):
            with inventory.open(newline="") as stream:
                recovered_attachments.update(row["filing_url"] for row in csv.DictReader(stream))
        unresolved_attachments = len(failed_attachments - recovered_attachments)
        exhibits = {
            "status": "acquiring",
            "parents": parents,
            "index_parsers": index_parsers,
            "documents": attachments,
            "complete": (exhibit_root / "run-result.json").is_file()
            and not parents.get("queued")
            and not parents.get("failed")
            and set(index_parsers) == {"sec_document_types_v1"}
            and not attachments.get("queued")
            and not attachments.get("inflight")
            and not unresolved_attachments,
            "recovered_source_errors": len(failed_attachments & recovered_attachments),
            "unresolved_source_errors": unresolved_attachments,
            "selection": "Every selected exhibit-eligible filing; all relevant text exhibits, no per-filing cap.",
        }
        if exhibits["complete"]:
            exhibits["status"] = "complete"
    discovery_path = run / "filing_discovery_result.json"
    discovery = read(discovery_path) if discovery_path.exists() else {}
    latest = [
        e["latest_periodic_filing"] for e in panel["entities"] if e.get("latest_periodic_filing")
    ]
    nav = read(ROOT / "analysis" / f"bdc_nav_{panel['as_of']}.json")
    fdic = read(ROOT / "analysis" / f"fdic_bank_distress_{panel['as_of']}.json")
    with (ROOT / "data/edgar_acquisition_2026-09-16/edgar_document_inventory.csv").open(
        newline=""
    ) as stream:
        baseline_count = sum(1 for _ in csv.DictReader(stream))
    status = {
        "snapshot_at_pacific": datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
        "refresh_as_of": panel["as_of"],
        "complete": (run / "run-result.json").exists()
        and not counts.get("queued")
        and not counts.get("inflight")
        and not unresolved
        and exhibits["complete"]
        and discovery.get("failed_ciks") == 0,
        "report": {
            "generated_from": graph.get("meta", {}).get("generated_from"),
            "financial_review_as_of": graph.get("meta", {}).get("as_of"),
            "current_verdict_recomputed": bool(graph.get("meta", {}).get("current_review")),
            "reason": "Current statement measurements retain their original period ends. Historical confidence judgments remain dated and are not probabilities.",
        },
        "market": {
            "dated_snapshot": str(market_path.relative_to(ROOT)),
            "generated_utc": live["generated_utc"],
            "price_dates": sorted({v["date"] for v in live.get("quotes", {}).values()}),
            "credit_dates": sorted(
                {
                    v["date"]
                    for v in live.get("credit", {}).values()
                    if isinstance(v, dict) and v.get("date")
                }
            ),
            "nav_periods": sorted({v["nav_asof"] for v in nav["bdc"].values()}),
            "source_status": live.get("source_status", {}),
        },
        "financial_panel": {
            "targets": panel["target_count"],
            "complete": panel["complete_count"],
            "filing_dates": sorted({v["filing_date"] for v in latest}),
            "periods": sorted({v["report_date"] for v in latest if v.get("report_date")}),
        },
        "sec_acquisition": {
            "exhibits": exhibits,
            "new_run_queue": counts,
            "baseline_inventory": baseline_count,
            "recovered_failures": len(failed_urls & recovered),
            "unresolved_source_errors": unresolved,
            "filing_discovery": {
                "ciks": discovery.get("ciks"),
                "failed_ciks": discovery.get("failed_ciks"),
            },
            "note": "Queue counts exclude the retained baseline. Downloads are not unique obligations.",
            "status": "incomplete"
            if counts.get("queued") or counts.get("inflight") or unresolved
            else "queue_drained",
        },
        "public_batches": sources,
        "current_public_releases": current,
        "fdic": {"period": fdic["quarter"], "institutions": fdic["institutions_returned"]},
        "public_batch_note": "Batch counts include retained prior attempts and replacements; their rows must not be added together.",
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
        folder = (
            ROOT
            / ".codex/refresh-status-snapshots"
            / datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
        )
        folder.mkdir(parents=True)
        shutil.copy2(args.output, folder / args.output.name)
    args.output.write_text(json.dumps(status, indent=2) + "\n")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "complete": status["complete"],
                "sec_queue": status["sec_acquisition"]["new_run_queue"],
            }
        )
    )


if __name__ == "__main__":
    main()
