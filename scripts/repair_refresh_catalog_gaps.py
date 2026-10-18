#!/usr/bin/env python3
"""Acquire omitted current catalog revisions without replacing earlier batches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from refresh_public_sources import command, missing_dynamic_sources, save, write_csv


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    run = args.run.resolve()
    destination = run / "dynamic_catalog_repair"
    destination.mkdir(exist_ok=False)
    selected = missing_dynamic_sources(
        run, ("public", "gleif", "dynamic", "queue_corrections")
    )
    write_csv(destination / "catalog.csv", selected)
    save(
        destination / "repair-start.json",
        {
            "selected": len(selected),
            "method": "URI, parser, corpus, complete request and source-revision metadata",
            "original_batches": "retained",
            "billing": "No paid APIs or model calls",
        },
    )
    if not selected:
        save(destination / "repair-result.json", {"selected": 0, "exit_code": 0})
        return 0
    result = command(
        destination,
        "acquisition",
        [
            "scripts/acquire_source_catalog.py",
            str(destination / "catalog.csv"),
            "--output-dir",
            str(destination / "acquired"),
            "--max-workers",
            "4",
            "--other-domain-concurrency",
            "4",
            "--other-requests-per-second",
            "8",
        ],
    )
    save(destination / "repair-result.json", result)
    print(json.dumps(result), flush=True)
    return int(result["exit_code"])


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget(512)
    raise SystemExit(main())
