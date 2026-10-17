# Refresh memory incident, October 17, 2026

The refresh workload contributed to system memory exhaustion. Ted reported the
out-of-system-memory dialog and had to send a remote reboot command. All refresh
jobs were absent when checked after the reboot. Heavy work remains stopped while
the resource handling is repaired.

The Mac reports 24 GiB of physical memory. The macOS Jetsam report at 11:13:25 PDT
records PID 9972, a previously observed child of the refresh driver, with a
23.39 GiB reported footprint. A second Python process had a 42.27 GiB footprint;
its activity has not been confirmed. The separate panic report records a watchdog
timeout. The full reports remain in `/Library/Logs/DiagnosticReports/`; selected
fields are preserved in `data/refresh_2026-10-17/memory-incident.json`.

The GLEIF input archives expand to 8,430,570,250 and 1,108,795,321 bytes of XML.
The catalog parser appends every flattened record to a list, then constructs a
second list with provenance. The refresh ran both GLEIF artifacts concurrently
with document acquisition and filing discovery. I launched that workload without
a bound on combined memory. That was the error. Streaming XML events alone did
not make the retained output lists bounded.

The first process-limit probe was rejected by macOS. `RLIMIT_AS` aliases
`RLIMIT_RSS` here and cannot be treated as an enforced address-space limit.
An attempted unified-log query also failed because `--max-bytes` is unsupported;
the structured diagnostic reports provide the evidence above.

The interrupted run retained 2,258 completed document journal entries. All 30
financial targets completed, four GPU pricing sources produced 77 observations,
and the FDIC snapshot completed. The public-source batch saved 480 of 482
artifacts and recorded two source errors. GLEIF archives were saved, but their
normalized outputs did not complete. These are partial refresh results, not a
completed update.

The original project path remains absent. The 15 pre-existing staged additions
retain staged-diff SHA-256
`df66eae0573bd34899df7e4451677d9050f1db80625921296cb8651112e2bf7d`.
Pre-fix code copies are in `.codex/refresh-2026-10-17/before-memory-fix/`.

Before heavy work resumes, use file-backed parsing and incremental output, and
verify an independent supervisor that accounts for the whole child process group
and terminates it when its memory budget is exceeded. Preserve interrupted
outputs and re-read their state before resuming. No heavy job has been restarted
at this incident checkpoint.

## Verified repair

The source catalog CLI now streams downloads and normalized rows through files.
XML records are removed from their parent after use. Pending SEC documents live
in SQLite, and filing discovery uses batches of 64 CIKs. These changes preserve
the scope and provenance while bounding retained data.

The independent supervisor measures physical footprint for the entire private
process group. The default budget is 2 GiB. It terminates the owned group when
the budget is exceeded and preserves partial outputs for inspection. This is an
external supervisor, not a kernel address-space limit. The heavy entry points
enter it automatically. No automatic retry follows a budget termination.

The guarded test run reported `23 passed in 3.16s`. It covered a real allocation
over budget, a parent-and-child budget violation, streaming XML retention,
legacy-field parity, disk-backed pending work, journal recovery, and original-byte
provenance in exported SEC inventories. Its observed peak was 74,843,120 bytes
under a 512 MiB test budget. Exact commands and results are in
`data/refresh_2026-10-17/bounded-refresh-tests.json`.

The actual saved GLEIF archives then completed normalization under a 1 GiB
budget: 4,101,539 records, zero source errors, and a peak footprint of 47,596,024
bytes (45.4 MiB). Both artifact counts match their XML header counts. The
supervisor trace is `data/refresh_2026-10-17/gleif-streaming-memory.jsonl`; header
checks are in `gleif-header-verification.json` in the same directory.

The broad acquisition run remains interrupted at this repair checkpoint. Recheck
processes and saved state before using the repaired driver with `--resume`.
