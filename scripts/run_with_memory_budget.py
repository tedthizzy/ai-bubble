#!/usr/bin/env python3
"""Supervise one private process group using measured physical memory footprint."""

from __future__ import annotations

import argparse
import ctypes
import errno
import json
import os
import signal
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path
from typing import Any


class MacUsage(ctypes.Structure):
    """rusage_info_v0 from the installed macOS sys/resource.h."""

    _fields_ = [("uuid", ctypes.c_uint8 * 16)] + [
        (name, ctypes.c_uint64)
        for name in (
            "user_time",
            "system_time",
            "idle_wakeups",
            "interrupt_wakeups",
            "pageins",
            "wired_size",
            "resident_size",
            "phys_footprint",
            "start_abstime",
            "exit_abstime",
        )
    ]


def footprint(pid: int) -> int:
    if sys.platform == "darwin":
        library = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
        library.proc_pid_rusage.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
        library.proc_pid_rusage.restype = ctypes.c_int
        usage = MacUsage()
        if library.proc_pid_rusage(pid, 0, ctypes.byref(usage)) != 0:
            error = ctypes.get_errno()
            if error == errno.ESRCH:
                return 0
            raise OSError(error, "Cannot measure workload memory")
        return int(usage.phys_footprint)
    status = Path(f"/proc/{pid}/status")
    try:
        fields = {
            line.split(":", 1)[0]: line.split(":", 1)[1].strip()
            for line in status.read_text().splitlines()
            if ":" in line
        }
    except FileNotFoundError:
        return 0
    return sum(int(fields.get(key, "0 kB").split()[0]) * 1024 for key in ("VmRSS", "VmSwap"))


def group_pids(group: int) -> list[int]:
    result = subprocess.run(
        ["ps", "-axo", "pid=,pgid="], check=True, text=True, capture_output=True
    )
    return [
        int(parts[0])
        for line in result.stdout.splitlines()
        if len(parts := line.split()) == 2 and int(parts[1]) == group
    ]


def stop_group(group: int, *, immediate: bool = False) -> None:
    # start_new_session creates this group exclusively for the supervised job.
    try:
        os.killpg(group, signal.SIGKILL if immediate else signal.SIGTERM)
    except ProcessLookupError:
        return
    if immediate:
        return
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline and group_pids(group):
        time.sleep(0.05)
    if group_pids(group):
        with suppress(ProcessLookupError):
            os.killpg(group, signal.SIGKILL)


def ensure_memory_budget(mib: int = 2048) -> None:
    """Enter the supervisor automatically; descendants share its group budget."""
    guardian = os.environ.get("BUBBLE_MEMORY_GUARD_PARENT", "")
    group = os.environ.get("BUBBLE_MEMORY_GUARD_GROUP", "")
    if guardian.isdigit():
        try:
            os.kill(int(guardian), 0)
            if os.getppid() == int(guardian):
                os.environ["BUBBLE_MEMORY_GUARD_GROUP"] = str(os.getpgrp())
                return
            if group.isdigit() and os.getpgrp() == int(group):
                return
        except ProcessLookupError:
            pass
    command = [
        sys.executable,
        "-B",
        str(Path(__file__).resolve()),
        "--budget-mib",
        str(mib),
        "--",
        sys.executable,
        "-B",
        *sys.argv,
    ]
    os.execv(sys.executable, command)


def supervise(command: list[str], budget: int, report: Any) -> int:
    def event(name: str, **data: Any) -> None:
        record = json.dumps({"event": name, "time_unix": time.time(), **data})
        print(record, file=report, flush=True)

    if footprint(os.getpid()) <= 0:
        raise RuntimeError("Memory measurement failed; workload was not started")
    env = {
        key: value
        for key, value in os.environ.items()
        if not any(
            word in key.upper() for word in ("API_KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL")
        )
    }
    env["BUBBLE_MEMORY_GUARD_PARENT"] = str(os.getpid())
    env.pop("BUBBLE_MEMORY_GUARD_GROUP", None)
    process = subprocess.Popen(command, env=env, start_new_session=True)
    peak = 0
    next_report = 0.0
    event("memory_supervisor_started", workload_pid=process.pid, budget_bytes=budget)
    try:
        while process.poll() is None:
            pids = group_pids(process.pid)
            measured = [{"pid": pid, "bytes": footprint(pid)} for pid in pids]
            total = sum(item["bytes"] for item in measured)
            peak = max(peak, total)
            if total > budget:
                event(
                    "memory_budget_exceeded", budget_bytes=budget, footprint_bytes=total, pids=pids
                )
                stop_group(process.pid, immediate=True)
                process.wait()
                event(
                    "workload_stopped",
                    peak_bytes=peak,
                    reason="memory_budget",
                    outputs="partial; inspect before resuming",
                )
                return 75
            if time.monotonic() >= next_report:
                event("workload_memory", footprint_bytes=total, peak_bytes=peak, processes=measured)
                next_report = time.monotonic() + 10
            time.sleep(0.1)
        code = process.wait()
        if group_pids(process.pid):
            stop_group(process.pid)
            event("orphaned_workload_stopped", root_exit_code=code)
            return 75
        event("workload_exited", exit_code=code, peak_bytes=peak)
        return code
    except BaseException:
        stop_group(process.pid)
        process.wait()
        raise


def main() -> int:
    def interrupted(signum: int, _frame: Any) -> None:
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--budget-mib", type=int, default=2048)
    parser.add_argument("--report", type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if args.budget_mib < 32 or not command:
        parser.error("Provide a budget of at least 32 MiB and a command after --")
    report = args.report.open("x") if args.report else sys.stdout
    try:
        return supervise(command, args.budget_mib * 1024**2, report)
    finally:
        if args.report:
            report.close()


if __name__ == "__main__":
    raise SystemExit(main())
