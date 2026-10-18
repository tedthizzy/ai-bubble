#!/usr/bin/env python3
"""Finish one supervised refresh after its owned acquisition process exits."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refresh_public_sources import (
    OLD_INVENTORY,
    OLD_MANIFESTS,
    ROOT,
    command,
    emit,
    save,
)


def process_identity(pid: int) -> str:
    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "lstart=,comm="],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 1:
        return ""
    result.check_returncode()
    return result.stdout.strip()


def wait_for_acquisition(run: Path, pid: int, identity: str) -> None:
    next_update = 0.0
    while current := process_identity(pid):
        if current != identity:
            raise RuntimeError("Acquisition PID was reused; inspect saved state")
        if time.monotonic() >= next_update:
            emit("waiting_for_acquisition", pid=pid, run=str(run))
            next_update = time.monotonic() + 1200
        time.sleep(30)
    if not (run / "run-result.json").is_file():
        raise RuntimeError(
            "Acquisition ended without run-result.json. Inspect its supervisor and queue; "
            "this continuation does not restart a stopped acquisition."
        )
    result = json.loads((run / "run-result.json").read_text())
    if "edgar" not in result.get("jobs", {}):
        raise ValueError("Acquisition completion record has no EDGAR result")
    with sqlite3.connect(f"file:{run / 'document_queue.sqlite3'}?mode=ro", uri=True) as database:
        unfinished = database.execute(
            "SELECT COUNT(*) FROM documents WHERE status IN ('queued','inflight')"
        ).fetchone()[0]
    if unfinished:
        raise ValueError(
            f"Acquisition completion record disagrees with {unfinished} unfinished URLs"
        )


def finish(run: Path) -> None:
    def stage(name: str, arguments: list[str]) -> None:
        result = command(run, "finish-" + name, arguments)
        save(run / ("finish-" + name + "-result.json"), result)
        if result["exit_code"] != 0:
            raise RuntimeError(f"Refresh stage {name} stopped with code {result['exit_code']}")
        emit("refresh_stage_finished", stage=name)

    stage("retry-gaps", ["scripts/retry_refresh_source_gaps.py", "--run", str(run)])
    batches = [OLD_INVENTORY.parent, run / "edgar"]
    batches.extend(
        result.parent / "edgar"
        for result in sorted((run / "source_gap_retries").glob("*/retry-result.json"))
    )
    merged = run / "edgar_merged_current"
    stage(
        "merge",
        [
            "scripts/merge_edgar_acquisitions.py",
            *(str(path) for path in batches),
            "--output-dir",
            str(merged),
            "--verify-bytes",
        ],
    )
    manifests = [*OLD_MANIFESTS, *sorted((run / "filing_batches").glob("*.csv"))]
    coverage = run / "coverage-current.json"
    stage(
        "coverage",
        [
            "scripts/audit_edgar_coverage.py",
            *(str(path) for path in manifests),
            "--inventory",
            str(merged / "edgar_document_inventory.csv"),
            "--retry-manifest",
            str(run / "missing-current.csv"),
            "--report-json",
            str(coverage),
        ],
    )
    as_of = run.name.removeprefix("refresh_")
    stage(
        "capital",
        [
            "scripts/refresh_capital_graph_2026_09_16.py",
            "--layer",
            "capital",
            "--mode",
            "complete",
            "--as-of",
            as_of,
            "--ferc-deals",
            str(run / "derived_public_current/ppa_deals.csv"),
            "--edgar-deals",
            str(merged / "deals.csv"),
            "--output-root",
            str(ROOT / "data" / f"capital_graph_refresh_{as_of}"),
        ],
    )
    stage("freshness", ["scripts/build_refresh_status.py", "--run", str(run)])
    stage(
        "report",
        [
            "scripts/build_public_refresh_report.py",
            "--run",
            str(run),
            "--output-prefix",
            str(ROOT / "analysis" / f"dated_engine_{as_of}_v2"),
        ],
    )
    audit = json.loads(coverage.read_text())
    save(
        run / "finish-result.json",
        {
            "coverage": audit["total"],
            "all_manifest_urls_acquired": audit["total"]["missing"] == 0,
            "merged_inventory": str(merged),
            "publication": "pending required browser confirmation, render and interaction checks",
            "core_judgments": "historical until recarded; no new bubble probability",
        },
    )
    emit("refresh_postprocessing_finished", coverage=audit["total"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--acquisition-pid", type=int, required=True)
    args = parser.parse_args()
    run = args.run.resolve()
    if args.acquisition_pid <= 1 or args.acquisition_pid == os.getpid():
        parser.error("Expected the observed acquisition workload PID")
    identity = process_identity(args.acquisition_pid)
    if not identity:
        parser.error("Acquisition process is absent; inspect saved state before continuing")
    save(
        run / "finish-start.json",
        {
            "acquisition_pid": args.acquisition_pid,
            "process_identity": identity,
            "continuation_pid": os.getpid(),
            "budget_mib": 2048,
            "method": "wait, one source-gap retry, full-byte merge, URL audit, capital graph, dated report",
            "automatic_acquisition_restart": False,
            "automatic_publication": False,
        },
    )
    wait_for_acquisition(run, args.acquisition_pid, identity)
    finish(run)


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget()
    main()
