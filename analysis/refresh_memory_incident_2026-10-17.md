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

## Bounded resumption

The broad acquisition resumed after the repair. At 12:18 PDT the supervised
process group used 152,994,704 bytes, with a peak of 345,884,160 bytes under its
2 GiB budget. The journal recorded 5,096 acquired documents and four failures.
Filing discovery had checked 5,312 of 29,815 CIKs. These are progress observations,
not final coverage. Recheck `data/refresh_2026-10-17/acquisition-resumed.log` and
the SQLite queue for current state. The earlier stopped-state paragraphs describe
the incident checkpoints, not a continuing prohibition on this bounded run.

## Document acquisition repair - 2026-10-17 17:04 PDT

Ted reported that Scout's ranking process also contributed to the outage.
Scout's RUNBOOK.md, line 29 when opened on October 17, attributes PID 10186's
42.267 GiB footprint to Scout and reports a completed 5.896 GiB replacement run.
That attribution is from Scout's runbook. Bubble's separate 23.39 GiB footprint
remains supported by its previously identified child PID in the OS report.
The evidence does not establish a unique initiator of the system failure.

The first bounded SEC resumption stopped at 14:11:25 PDT above its unchanged
2 GiB budget. The footprint was 2,166,557,216 bytes. Both owned processes were
absent afterward, and the Mac reported normal memory pressure. The queue retained
32,910 acquired documents, 44 failed documents, seven in-flight records and
194,432 queued records. All 32,954 journal lines parsed. No non-URL queue keys
were present. Discovery completed all 29,815 CIKs with zero failed CIKs.

Two interrupted fund filings were already saved and passed gzip validation.
The largest expanded to 130,544,556 bytes despite a 10,478,305-byte manifest
size. Downloaded XSL-rendered fund filings can greatly exceed that size.
Text normalization retained large regex fragment lists and full intermediate
strings. StringIO also uses a wide writable buffer, so an unbounded StringIO
replacement was insufficient. Initial conservative 768 MiB stress probes stopped
safely; their logs remain under the dated refresh directory.

PublicClient now streams decoded HTTP bytes into gzip files, retaining failed
parts and refusing to replace a saved source. Text parsing waits on a shared
byte-weighted reservation before reading saved sources. Normalization coalesces
regex fragments in 64 KiB buffers, including HTML entities. Small documents keep
the native regex fast path. The exact legacy normalization output is preserved
in tests, including Unicode, malformed markup and buffer boundaries.
Source hashes are calculated incrementally from original decompressed bytes.

The final real-source check processed both interrupted saved filings with no
network fetches, retained their complete text counts and hashes, and exited 0.
It peaked at 1,095,075,160 bytes under the existing 2 GiB production threshold.
The largest document retained all 71,658,264 normalized characters.
This is measured stress-test evidence, not a promise that every future document
fits below budget. The process-group supervisor remains active.

A focused test invocation exposed a macOS rusage exit-transition race: the OS
can return EPERM for a zombie. The supervisor now ignores only a PID confirmed
absent or zombie by ps; a live unmeasurable PID still fails closed. The corrected
45-test run passed in 3.61 seconds at a 358,859,688-byte peak. Mypy passed for
document_acquisition.py. Ruff passed on the changed code and tests.

The audited queue resumed once at 17:01 PDT. Its current log is
data/refresh_2026-10-17/acquisition-resumed-document-fix.log. Its observed peak
passed 1.5 GiB while making progress beyond the old stop. Inspect this log,
the owned process group and the queue before any later resume. Never start
a second main refresh or raise the 2 GiB budget to bypass a stop.
