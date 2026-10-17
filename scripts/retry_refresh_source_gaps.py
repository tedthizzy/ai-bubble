#!/usr/bin/env python3
"""Retry recorded SEC source gaps without changing an active refresh queue."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

from refresh_public_sources import DocumentQueue, PublicClient, emit, save


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    run = args.run.resolve()
    previous: set[str] = set()
    for inventory in (run / "source_gap_retries").glob("*/edgar/edgar_document_inventory.csv"):
        with inventory.open(newline="") as stream:
            previous.update(row["filing_url"] for row in csv.DictReader(stream))
    destination = run / "source_gap_retries" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    destination.mkdir(parents=True, exist_ok=False)
    # Eight requests/second in the main driver plus this one remain below ten.
    client = PublicClient(destination, 1)
    work = DocumentQueue(destination, client, previous)
    with sqlite3.connect(f"file:{run / 'document_queue.sqlite3'}?mode=ro", uri=True) as source:
        selected = work.enqueue(
            (json.loads(row[0]) for row in source.execute(
                "SELECT record FROM documents WHERE status='failed' ORDER BY sequence"
            )),
            current=True,
        )
    save(destination / "retry-start.json", {
        "selected": selected, "previously_recovered": len(previous),
        "source_run": str(run), "requests_per_second": 1,
        "billing": "No paid APIs or model calls",
    })
    emit("source_gap_retry_started", selected=selected, destination=str(destination))
    work.done.set()
    workers = [threading.Thread(target=work.worker) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    result = work.finish()
    save(destination / "retry-result.json", result)
    emit("source_gap_retry_finished", **result)


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget(512)
    main()
