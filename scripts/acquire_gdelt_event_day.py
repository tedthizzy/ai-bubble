#!/usr/bin/env python3
"""Acquire one complete UTC day of GDELT 2.0 Event files with source URLs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from pathlib import Path

BASE = "https://data.gdeltproject.org/gdeltv2/"
FIELDS = [
    "global_event_id",
    "event_date",
    "date_added_utc",
    "actor1_name",
    "actor2_name",
    "event_code",
    "goldstein_scale",
    "num_mentions",
    "num_sources",
    "avg_tone",
    "source_url",
    "raw_file_url",
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_slot(slot: datetime, raw_dir: Path) -> dict:
    stamp = slot.strftime("%Y%m%d%H%M%S")
    filename = f"{stamp}.export.CSV.zip"
    url = BASE + filename
    path = raw_dir / filename
    try:
        if path.exists():
            payload = path.read_bytes()
            resumed = True
        else:
            request = urllib.request.Request(
                url, headers={"User-Agent": "ai-bubble-public-data-research/1.0"}
            )
            with urllib.request.urlopen(request, timeout=40) as response:
                payload = response.read()
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                if len(archive.namelist()) != 1 or archive.testzip() is not None:
                    raise ValueError(f"invalid archive: {filename}")
            path.write_bytes(payload)
            resumed = False
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            member = archive.namelist()[0]
            with archive.open(member) as fh:
                rows = list(csv.reader(io.TextIOWrapper(fh, encoding="utf-8"), delimiter="\t"))
        if any(len(row) != 61 for row in rows):
            raise ValueError(f"unexpected column count: {filename}")
        return {
            "stamp": stamp,
            "status": "acquired",
            "url": url,
            "raw_path": str(path),
            "raw_sha256": sha256(payload),
            "raw_bytes": len(payload),
            "event_rows": len(rows),
            "resumed": resumed,
            "rows": rows,
        }
    except (urllib.error.URLError, TimeoutError, ValueError, zipfile.BadZipFile) as error:
        return {"stamp": stamp, "status": "failed", "url": url, "error": str(error), "rows": []}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="UTC day YYYY-MM-DD")
    parser.add_argument("--through-slot", help="Optional inclusive UTC YYYYMMDDHHMMSS slot cutoff")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    start = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=UTC)
    raw_dir = args.output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    slots = [start + timedelta(minutes=15 * index) for index in range(96)]
    if args.through_slot:
        slots = [slot for slot in slots if slot.strftime("%Y%m%d%H%M%S") <= args.through_slot]
    if not slots:
        raise ValueError("No slots fall within the requested day and cutoff")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(fetch_slot, slot, raw_dir): slot for slot in slots}
        results = [future.result() for future in as_completed(futures)]
    results.sort(key=lambda result: result["stamp"])
    output = args.output_dir / "event_rows.csv"
    with output.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for result in results:
            if result["status"] != "acquired":
                continue
            for row in result["rows"]:
                writer.writerow(
                    dict(
                        zip(
                            FIELDS,
                            [
                                row[0],
                                row[1],
                                row[59],
                                row[6],
                                row[16],
                                row[26],
                                row[30],
                                row[31],
                                row[32],
                                row[34],
                                row[60],
                                result["url"],
                            ],
                            strict=True,
                        )
                    )
                )
            del result["rows"]
    summary = {
        "utc_day": args.date,
        "expected_slots": len(slots),
        "last_requested_slot_utc": slots[-1].strftime("%Y-%m-%dT%H:%M:%SZ"),
        "acquired_slots": sum(r["status"] == "acquired" for r in results),
        "failed_slots": sum(r["status"] == "failed" for r in results),
        "event_rows": sum(r.get("event_rows", 0) for r in results),
        "source_url_rows": sum(
            1
            for row in csv.DictReader(output.open(newline="", encoding="utf-8"))
            if row["source_url"]
        ),
        "derived_path": str(output),
        "derived_sha256": sha256(output.read_bytes()),
        "raw_file_inventory": results,
        "caveat": "GDELT machine-coded events are media observations, not confirmed economic outcomes; event_date may predate file UTC date_added.",
    }
    summary_path = args.output_dir / "acquisition_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {key: value for key, value in summary.items() if key != "raw_file_inventory"}, indent=2
        )
    )


if __name__ == "__main__":
    main()
