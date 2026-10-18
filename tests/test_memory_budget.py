from __future__ import annotations

import ctypes
import errno
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from scripts import run_with_memory_budget as memory

SUPERVISOR = Path(__file__).resolve().parents[1] / "scripts/run_with_memory_budget.py"


def fake_mac_usage(monkeypatch, errors, *, state="S", returncode=0):
    calls, sleeps = [], []
    outcomes = iter(errors)

    class ReadUsage:
        def __call__(self, pid, _version, usage):
            calls.append(pid)
            error = next(outcomes)
            if error:
                ctypes.set_errno(error)
                return -1
            usage._obj.phys_footprint = 123456
            return 0

    monkeypatch.setattr(
        memory.ctypes,
        "CDLL",
        lambda *_args, **_kwargs: SimpleNamespace(proc_pid_rusage=ReadUsage()),
    )
    monkeypatch.setattr(
        memory.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=returncode, stdout=state),
    )
    monkeypatch.setattr(memory.time, "sleep", sleeps.append)
    return calls, sleeps


def test_running_mac_process_is_remeasured_after_permission_error(monkeypatch):
    calls, sleeps = fake_mac_usage(monkeypatch, [errno.EPERM, 0])
    assert memory._mac_footprint(123) == 123456
    assert calls == [123, 123]
    assert sleeps == [0.01]


def test_persistent_mac_measurement_error_never_becomes_unmeasured_zero(monkeypatch):
    calls, sleeps = fake_mac_usage(monkeypatch, [errno.EPERM] * 3)
    with pytest.raises(OSError, match="PID 123") as error:
        memory._mac_footprint(123)
    assert error.value.errno == errno.EPERM
    assert calls == [123, 123, 123]
    assert sleeps == [0.01, 0.01]


@pytest.mark.parametrize("returncode,state", [(1, ""), (0, "Z+")])
def test_only_confirmed_exited_mac_process_uses_zero(monkeypatch, returncode, state):
    calls, sleeps = fake_mac_usage(monkeypatch, [errno.EPERM], state=state, returncode=returncode)
    assert memory._mac_footprint(123) == 0
    assert calls == [123]
    assert sleeps == []


def test_isolated_process_has_observable_memory() -> None:
    # The full suite can already have large ML libraries loaded on Linux.
    # Measure the same lightweight process on every host, retaining the cap.
    measured = subprocess.check_output(
        [
            sys.executable,
            "-B",
            "-c",
            "import os; from scripts.run_with_memory_budget import footprint; print(footprint(os.getpid()))",
        ],
        text=True,
    )
    assert 0 < int(measured) < 1024**3


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
