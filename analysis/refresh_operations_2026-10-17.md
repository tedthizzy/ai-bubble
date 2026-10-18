# Bubble refresh operations, October 17, 2026

## Browser and publication checkpoint - 2026-10-17 18:50 PDT

The later dated checkpoints supersede the earlier pending states below.
Ted's latest confirmation authorizes using his existing Chrome and publishing
this work while retaining the existing published Git history. The exception
covers the 136 existing attribution matches. New commits must have zero matches.
No history rewrite is authorized or needed.

The explorer was rendered in the existing Chrome 155 session. Desktop and
390px mobile screenshots were viewed. Search, keyboard selection, core cards,
raw-point selection, all 459 connections on the largest raw-entity card, deal
cards and cascade controls were exercised. Reduced motion, ten rapid cascade
clicks, long mixed-script names, empty data and unavailable sources were checked.
At 150ms latency and 100,000 bytes/second with graph and overlay requests blocked,
the saved 28-entity core loaded with explicit unavailable-data messages.

Browser checks found and repaired synchronous render-resume recursion when
returning to a paused tab, an unclosed report definition list, and an empty
library tooltip. Grey lines now dim during selection. Header and legend
backgrounds preserve contrast over graph objects. Computed fonts are Arial at
14px and 18px; minimum checked text contrast is 6.0123:1.

After settling, Chrome rendered zero frames in five seconds. A post-cascade
sample taken during the remaining camera tween rendered 26 frames in five
seconds; a later settled sample rendered zero. The latter sample had 56 draw
calls in its last rendered frame, 7,687 points, zero textures and a 12,900,476-byte
JavaScript heap. These are observations on this browser, not a device-independent
speedup estimate. The full old renderer was not loaded for a comparative
benchmark, to avoid allocating its thousands of label textures in Ted's browser.

Exact observations, screenshot hashes and source hashes are recorded in
analysis/viz_browser_validation_2026-10-17.json. Local screenshots and test drivers
remain in data/refresh_2026-10-17/browser-validation/. The Node suite now has six
passing tests, including a regression for synchronous resume callbacks.

The existing finisher remains responsible for acquisition completion, retry,
full-byte merge, coverage audit, capital graph and dated engine v2. A separate
supervised scripts/publish_public_refresh.py process now waits for that exact
finisher PID. It requires its completion record and a drained queue. It verifies
the exact browser-checked UI hashes, preserves the original staged-diff digest,
and commits only freshness.json and the dated engine v2 JSON/Markdown outputs.
It accepts only a fast-forward of the known market-overlay files. Divergence,
unrelated incoming edits, source changes or stage failures stop publication.
It never restarts acquisition, retries a push, forces history or deletes files.

The publisher checks attribution, dry-runs and performs the authorized main push,
observes the Pages workflow, and compares the deployed freshness and explorer
file hashes. It publishes honest coverage gaps if sources remain unavailable;
publication does not mean every URL was acquired or the June core was recarded.
Its 14 focused tests passed, including preservation of an unrelated staged
addition in a real temporary Git repository. Mypy and Ruff passed. The first
Mypy run found one missing JSON-result annotation; that annotation was corrected.
The already-running process differs only by that inert type annotation; its
exact launch source is retained in .codex/refresh-2026-10-17/publisher-running-source.py.

Check the existing processes before starting anything:

    tail -n 6 data/refresh_2026-10-17/acquisition-resumed-document-fix.log
    tail -n 6 data/refresh_2026-10-17/finish-refresh.log
    tail -n 6 data/refresh_2026-10-17/publish-refresh.log

The publisher records publication-start.json and, after finishing, either
publication-result.json or publication-stopped.json in that run directory.
The exclusive start record prevents accidental duplicate launches. A partial
push is unknown until fresh remote state is checked; do not replay it blindly.
This checkpoint precedes the first push. Deployment is not yet verified here.

Bubble is at /Users/ted/Projects/bubble. The former Documents/dev-archive/bubble
location is absent. The move evidence remains in .codex/relocation-2026-10-17/.
Do not create a second checkout as a substitute for resuming this one.

The unbounded first refresh contributed to memory exhaustion and a remote reboot.
See [the incident and repair](refresh_memory_incident_2026-10-17.md). Heavy entry
points used for this refresh enter a process-group memory supervisor. It measures physical
footprint, stops its owned group above budget, and retains partial outputs.
This is a polling supervisor, not a kernel allocation limit. Inspect fresh state
after a stop. Never assume a partial operation failed or replay it blindly.

The resumed broad acquisition uses SQLite for pending documents and batches
filing discovery. Its SEC requests share an 8-request/second client. It retains
the full selected backlog and the new official-index CIK universe. Acquisition
is incomplete at this checkpoint. Recheck with:

    tail -n 8 data/refresh_2026-10-17/acquisition-resumed.log

The journal, queue, and raw sources remain under data/refresh_2026-10-17.
The driver accepts --resume after the previous owned process has ended.
Completed source batches remain immutable. The recovery tests include successful
journal replay and legacy failure keys. Failed URLs need reconciliation and
retry before claiming complete selected-manifest coverage.

The completed market refresh contains October 16 closes and October 15 credit
observations. All 19 graph quotes, 12 filing counts, eight BDC marks, four credit
series, and two adjacent quotes were present. BDC NAV is the latest reported
quarterly value found in saved SEC periodic filings, dated June 30. The NAV
builder excludes proxy estimates, future periods, and period-change facts.
It does not change the registered basket memberships or thresholds.

The latest GLEIF artifacts carry October 17 source timestamps. They contain
3,466,099 LEI records and 674,460 relationship records. The complete ownership
graph scans those relationships and retains 667,429 valid relationships among
440,154 entities. Self-links and incomplete endpoints follow the existing
production parser. The SQLite builder preserves the original fields, ordering,
reference replacement, and summary semantics in parity tests. Its full-input
run peaked at 85,148,128 bytes under a 512 MiB budget. The older object-based
attempt stopped safely at its 1 GiB budget; it produced no output directory.
Do not increase the budget to work around retained-record growth.

The August EIA workbook is the latest published release resolved from its page.
It was released September 24, with the next release listed as October 23.
The earlier July URL failed. The corrected ERCOT normalization retains 1,789
large/small generator records; its large-generator header occurs after the old
30-row scan window. The corrected PJM serial export contains 9,263 records.
PJM's anonymous export header is resolved from its public application and is
not stored in repository catalog metadata. These corrections retain the
unsuccessful first attempts.

The historical SEC storage pass compressed 55,395 files with zero recorded
errors. Every replacement passed complete before/after SHA-256 checks.
Allocated storage for replaced files fell by 46,908,620,800 bytes (43.7 GiB).
The volume's free space increased by 44,970,954,752 bytes (41.9 GiB) while
acquisition continued adding data. APFS sharing and concurrent writes mean the
volume change is not an isolated measurement of compression savings.

Compression preserves filenames and readable bytes. The snapshots retain the
same verified content in compressed APFS clones. Future writes to either copy
are independent. Original modes, ownership, timestamps, unrelated flags, and
extended-attribute hashes are checked. The pass skipped ineligible files.
It did not prune transcripts, logs, prior snapshots, or source artifacts.
The pass used a 512 MiB process budget and peaked at 106,562,424 bytes.

The retained action records and snapshots are under:

    .codex/storage-compaction/2026-10-17/historical-sec-text-v2/

Each action directory contains original.json, result.json, and snapshot.
To restore one file as an uncompressed file:

    .venv/bin/python -B scripts/compact_public_data.py --restore-action ACTION_DIRECTORY

The restore checks that the target still has the recorded content hash, retains
a snapshot of the target, and refuses to overwrite changed content. Compression,
restore, reapplication, and independent clone writes passed real filesystem
checks. Evidence is in data/refresh_2026-10-17/compression-tracked-roundtrip.json
and compression-roundtrip-verification.json. Never prune those snapshots.

To run a later compression pass, use a new archive directory:

    .venv/bin/python -m py_compile scripts/compact_public_data.py && .venv/bin/python -u -B scripts/compact_public_data.py --roots HISTORICAL_PUBLIC_DATA_DIRECTORY --archive .codex/storage-compaction/NEW_PASS

The first conservative pass skipped all tracked files and changed nothing.
The completed second pass explicitly preserves UF_TRACKED and the compression
flag. Both summaries remain available.

The explorer implementation uses one Arial family and two CSS sizes: 14px and
18px. The extracted field uses static Points and LineSegments buffers. Core
entities retain interaction; raw entities remain searchable and selectable.
Every connection remains accessible through the selected entity's card.
Rendering pauses while idle and wakes for interaction. Reduced motion removes
camera tweening and cascade animation. Libraries are pinned locally with their
licenses. The report date and market dates remain separate.

The UI has passed logic and data-parity tests. The minimum checked text contrast
across its declared text/background colors is 6.01:1. The generated SVG banner
was rendered and viewed. Browser rendering, interaction, throttled-network
checks, and measured frame performance remain unverified. Browser control is
pending Ted's confirmation under the Mac instructions. Do not describe the
explorer as visually verified or deployed.

Source freshness is generated from saved outputs:

    .venv/bin/python -B scripts/build_refresh_status.py --run data/refresh_2026-10-17

The status snapshots and original files are retained under .codex. The June
adjudicated core and confidence judgments have not been recomputed. A market
refresh does not update those conclusions. SEC coverage reconciliation, the
current complete capital graph, and the dated engine report remain outstanding.
The UI changes and new source outputs have not been pushed at this checkpoint.

Git fetched origin/main on this date. The remote had no newer commits than the
local base; local main was ahead. Preserve the 15 pre-existing staged analysis
additions. The staged raw-diff check is:

    git diff --cached --raw -z | shasum -a 256

Before adding this pass's files, and after committing only this pass's files,
its expected hash is df66eae0573bd34899df7e4451677d9050f1db80625921296cb8651112e2bf7d.

## Current acquisition log - 2026-10-17 17:04 PDT

The earlier resumed log records a safe budget stop at 14:11:25 PDT.
The document-memory repair and complete queue audit are in the incident record.
The subsequent main refresh uses:
    data/refresh_2026-10-17/acquisition-resumed-document-fix.log

This supersedes acquisition-resumed.log as the current progress log.
Check the private workload PID in its supervisor event before any resume.
The 2 GiB threshold is unchanged. Large documents run under a byte-weighted
text-processing reservation; downloads stream to disk. Completed raw sources,
failed response parts, prior results and every checkpoint remain retained.
The stopped queue and original edited files are backed up in
.codex/refresh-2026-10-17/before-document-memory-fix-1792281345903613000/.

## Public-source and continuation checkpoint - 2026-10-17 17:18 PDT

Dynamic source identity now includes request and revision metadata. The previous
URI-only check dropped FERC pages at the same API endpoint. Latest discovery
contained 47,232 FERC records; the older catalog acquired 46,669. A repair batch
acquired 476 artifacts with zero source errors: all 473 current FERC pages,
the current PJM cycle export and two current FracTracker pages. All 476 saved
artifacts passed full SHA-256 checks. The normalized FERC IDs are unique and
exactly match the discovered total. The earlier artifacts remain unchanged.

The repair wrapper failed only while relativizing its log path after acquisition.
Fresh inspection verified the completed outputs; the acquisition was not replayed.
The child exit code was not captured by the failed wrapper. The retained
repair-reconciliation.json records that distinction. A regression now verifies
the relative-log-path case.

The public derivation completed under 1 GiB at a 277,529,344-byte peak.
It retains 18,322 queue records after replacing 908 PJM serial rows represented
in the current cycle; all 105,405 equipment reference rows; and current tracker
records. It produces 47,046 pending PPA candidates from 47,232 source rows.
Its immutable input/output hashes and selection counts are in:
    data/refresh_2026-10-17/derived_public_current/input_manifest.json

The current FERC-only capital graph completed under 2 GiB at a
753,173,464-byte peak. Its 47,046 deals remain pending review. The current
ownership graph remains separate. These are not additive debt totals.

Modal's new page includes accessible static prices plus animated duplicate
digits and a changed CPU heading. The old parser silently returned no rows.
The parser now reads the static prices, supports T4 and records empty parses
as errors. Reprocessing all four saved snapshots produced 88 quotes, zero errors,
and a 57,606,648-byte peak. The new raw directory uses relative symlinks to the
saved originals; source acquisition dates and hashes remain unchanged.
    data/refresh_2026-10-17/gpu_prices_reparsed/

The dated engine v1 ran the existing deterministic market, financial,
physical-capacity and compute functions. It explicitly records incomplete SEC
acquisition, stale S1 and unmeasured S4. It adds no new bubble probability.
The June adjudicated core remains historical.

The supervised continuation is running:
    data/refresh_2026-10-17/finish-refresh.log
It waits for the exact observed acquisition PID to exit, rejects PID reuse,
requires a valid completion record and a drained queue, then runs one gap retry,
the production merge with full raw-byte hashing, the exact URL coverage audit,
the complete capital graph and the v2 dated engine report. Stage errors stop
later stages and retain their results. A stopped acquisition is never restarted
automatically. The continuation does not publish or rewrite Git history.

Source freshness uses Pacific dates for saved SEC panels even after UTC
midnight. Its regression covers 00:30 UTC while the Pacific date is still
October 17.

Git fetched successfully. Before this checkpoint, origin/main had no incoming
commits and local main was ahead by three. The required whole-history attribution
check returned 136 matching lines across 130 older commits, all with existing
Co-Authored-By trailers. None belongs to this work's new commits. History remains
unchanged. This conflicts with Projects/AGENTS.md:244, which requires zero matches
before pushing; an explicit exception or a separate authorized history decision
is needed before publication. Browser control also remains pending the required
confirmation under Projects/AGENTS.md:303. No push or deployment ran.
