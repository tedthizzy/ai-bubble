from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from scripts.run_with_memory_budget import footprint

SUPERVISOR = Path(__file__).resolve().parents[1] / "scripts/run_with_memory_budget.py"


def test_current_process_has_observable_memory() -> None:
    assert 0 < footprint(os.getpid()) < 1024**3


def test_small_workload_finishes_and_reports_peak(tmp_path: Path) -> None:
    report = tmp_path / "small.jsonl"
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(SUPERVISOR),
            "--budget-mib",
            "128",
            "--report",
            str(report),
            "--",
            sys.executable,
            "-B",
            "-c",
            "import time; time.sleep(.25); print('finished')",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "finished"
    events = [json.loads(line) for line in report.read_text().splitlines()]
    assert events[-1]["event"] == "workload_exited"
    assert 0 < events[-1]["peak_bytes"] < 128 * 1024**2


def test_real_allocation_is_stopped_before_completion(tmp_path: Path) -> None:
    # Even without the supervisor this fixture allocates at most 128 MiB.
    report = tmp_path / "limited.jsonl"
    program = (
        "import os,time\nchunks=[]\n"
        "for _ in range(32):\n chunks.append(os.urandom(4*1024**2)); time.sleep(.03)\n"
        "print('unexpected completion')\n"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(SUPERVISOR),
            "--budget-mib",
            "48",
            "--report",
            str(report),
            "--",
            sys.executable,
            "-B",
            "-c",
            program,
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 75, result.stderr
    assert "unexpected completion" not in result.stdout
    events = [json.loads(line) for line in report.read_text().splitlines()]
    exceeded = next(item for item in events if item["event"] == "memory_budget_exceeded")
    assert 48 * 1024**2 < exceeded["footprint_bytes"] < 80 * 1024**2
    assert events[-1]["reason"] == "memory_budget"


def test_budget_includes_a_spawned_child(tmp_path: Path) -> None:
    report = tmp_path / "descendant.jsonl"
    program = (
        "import os,subprocess,sys,time\n"
        "child=subprocess.Popen([sys.executable,'-B','-c',"
        '"import os,time; data=os.urandom(72*1024**2); time.sleep(2)"])\n'
        "own=os.urandom(8*1024**2)\nchild.wait()\nprint('unexpected completion')\n"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(SUPERVISOR),
            "--budget-mib",
            "64",
            "--report",
            str(report),
            "--",
            sys.executable,
            "-B",
            "-c",
            program,
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 75, result.stderr
    assert "unexpected completion" not in result.stdout
    events = [json.loads(line) for line in report.read_text().splitlines()]
    exceeded = next(item for item in events if item["event"] == "memory_budget_exceeded")
    assert len(exceeded["pids"]) == 2
    assert events[-1]["reason"] == "memory_budget"
