#!/usr/bin/env python3
"""Derive current public evidence from immutable refreshed source batches."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from itertools import batched
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bubble.analysis.physical_capacity import build_physical_capacity_summary
from bubble.ingestion.capital.ppa_extraction import (
    PPA_DEAL_FIELDNAMES,
    _deal_row_if_extractable,
)
from bubble.ingestion.physical.tracker_extraction import extract_tracker_projects

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from combine_queue_sources import combine


def rows(path: Path) -> Iterator[dict[str, str]]:
    with path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            yield {key: (value or "").strip() for key, value in row.items()}


def file_record(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def save(path: Path, value: Any) -> None:
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def selected_csv(
    selections: list[tuple[Path, Callable[[dict[str, str]], bool]]], output: Path
) -> dict[str, int]:
    fields: list[str] = []
    for path, _ in selections:
        with path.open(newline="") as stream:
            fields.extend(
                key for key in csv.DictReader(stream).fieldnames or [] if key not in fields
            )
    counts: Counter[str] = Counter()
    with output.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for path, predicate in selections:
            for row in rows(path):
                if predicate(row):
                    writer.writerow(row)
                    counts[row["source_id"]] += 1
    if not counts:
        raise ValueError(f"No selected source rows for {output}")
    return dict(counts)


def derive(run: Path, output: Path, ferc_input: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    public = run / "public/source_rows"
    dynamic = run / "dynamic/source_rows"
    corrections = run / "queue_corrections/source_rows"
    latest = ferc_input.parent
    inputs = [
        public / "queue_records.csv",
        dynamic / "queue_records.csv",
        corrections / "queue_records.csv",
        public / "equipment_records.csv",
        dynamic / "equipment_records.csv",
        public / "tracker_records.csv",
        latest / "tracker_records.csv",
        latest / "queue_records.csv",
        ferc_input,
    ]
    selection: dict[str, Any] = {}
    selection["standard_queues"] = selected_csv(
        [
            (
                public / "queue_records.csv",
                lambda r: not r["source_id"].startswith(("ercot-", "iso-ne-", "pjm-")),
            ),
            (dynamic / "queue_records.csv", lambda r: r["source_id"].startswith("iso-ne-")),
            (corrections / "queue_records.csv", lambda r: r["source_id"].startswith("ercot-")),
        ],
        output / "queue_standard.csv",
    )
    selection["serial_queues"] = selected_csv(
        [
            (
                corrections / "queue_records.csv",
                lambda r: r["source_id"].startswith("pjm-serial-full-"),
            ),
        ],
        output / "queue_serial.csv",
    )
    selection["cycle_queues"] = selected_csv(
        [
            (latest / "queue_records.csv", lambda r: r["source_id"].startswith("pjm-cycle-")),
        ],
        output / "queue_cycle.csv",
    )
    # Only this directory is passed to the physical builder; raw staging CSVs
    # remain outside it, so no older/superseded queue snapshots are counted.
    physical = output / "physical"
    physical.mkdir()
    selection["queue_combination"] = combine(
        output / "queue_standard.csv",
        output / "queue_serial.csv",
        output / "queue_cycle.csv",
        physical / "queue_records.csv",
        output / "queue_combination.json",
    )
    selection["equipment"] = selected_csv(
        [
            (public / "equipment_records.csv", lambda r: r["source_id"].startswith("epa-egrid")),
            (dynamic / "equipment_records.csv", lambda r: r["source_id"].startswith("eia-860m")),
        ],
        physical / "equipment_records.csv",
    )
    selection["trackers"] = selected_csv(
        [
            (
                public / "tracker_records.csv",
                lambda r: not r["source_id"].startswith("fractracker-"),
            ),
            (latest / "tracker_records.csv", lambda r: r["source_id"].startswith("fractracker-")),
        ],
        output / "tracker_current.csv",
    )
    tracker = extract_tracker_projects(
        output / "tracker_current.csv", physical / "projects.csv", max_workers=8
    )
    save(output / "tracker_summary.json", tracker.to_dict())

    source_count = deal_count = 0
    with (output / "ppa_deals.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PPA_DEAL_FIELDNAMES)
        writer.writeheader()
        with ThreadPoolExecutor(max_workers=8) as executor:
            for batch in batched(rows(ferc_input), 256):
                source_count += len(batch)
                for deal in executor.map(_deal_row_if_extractable, batch):
                    if deal is not None:
                        writer.writerow(deal)
                        deal_count += 1
    selection["ppas"] = {
        "source_rows": source_count,
        "deals_written": deal_count,
        "skipped_rows": source_count - deal_count,
    }
    summary = build_physical_capacity_summary([physical])
    save(output / "physical_capacity_summary.json", summary.to_dict())
    result = {
        "as_of": run.name.removeprefix("refresh_"),
        "inputs": [file_record(path) for path in inputs],
        "source_selection": selection,
        "outputs": {
            str(path.relative_to(output)): file_record(path)
            for path in sorted(output.rglob("*"))
            if path.is_file()
        },
        "limits": [
            "Acquisition dates do not replace source observation dates.",
            "Generation requests, tracker MW and equipment capacity are separate measures.",
            "MISO input covers the selected ERAS requests, not the complete MISO universe.",
            "The eGRID generator reference remains the published 2023 source.",
            "PPA candidates remain pending review; edges are not additive debt.",
        ],
    }
    save(output / "input_manifest.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ferc-input", type=Path, required=True)
    args = parser.parse_args()
    result = derive(args.run, args.output, args.ferc_input)
    print(json.dumps({"as_of": result["as_of"], "source_selection": result["source_selection"]}))


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget(1024)
    main()
