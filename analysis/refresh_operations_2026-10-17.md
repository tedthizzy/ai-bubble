# Bubble refresh operations, October 17, 2026

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
