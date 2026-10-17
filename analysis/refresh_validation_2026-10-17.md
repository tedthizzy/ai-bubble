# Refresh verification checkpoint, October 17, 2026

This checkpoint is partial. It does not establish that the full data refresh,
browser verification, or publication has finished. The operations and recovery
record is [refresh_operations_2026-10-17.md](refresh_operations_2026-10-17.md).

Verified:

- The selected ingestion, ownership, market-signal, journal-recovery, and dated
  engine tests reported 88 passed in 3.13s. The command used the relocated
  .venv, disabled coverage/cache writes, and ran under a 768 MiB supervisor.
  Its measured peak was 95,781,920 bytes.
- The additional real APFS compression tests reported 2 passed in 0.10s.
  They verified full byte identity, metadata preservation, restore/reapply,
  independent clone writes, and refusal to restore changed metadata.
- node --test tests/viz/explorer.test.cjs reported five passed tests.
  They exercised the full saved graph, all connection access, click-only raw
  point picking, search, long Unicode/HTML-shaped text, reduced motion, empty
  data, and failed market fetches. This harness is not a browser render.
- Mypy reported Success: no issues found in 8 source files.
  The saved command covers the compaction/NAV/status/market drivers and the
  ownership/streaming/PJM modules. It emitted only unused-config-section notes.
- Ruff passed on the changed Python implementations and tests.
  node --check viz/explorer.js and git diff --check passed.
- The complete saved graph, excluding the added layout, equals the original
  JSON. Its financial data and judgments have not been relabeled as October.
- The font tokens are Arial/sans-serif, 14px and 18px. The SVG also uses only
  those sizes. The minimum calculated contrast across declared text/background
  combinations was 6.01:1. The SVG was rendered with Quick Look and viewed.
- The latest ownership build scanned all 674,460 relationship rows and wrote
  667,429 valid relationships among 440,154 nodes. It peaked at 85,148,128
  bytes. The input manifest hashes both normalized inputs and all three final
  graph outputs. It remains a separate consolidation layer.
- Compression replaced 55,395 public SEC files after complete SHA-256 checks,
  with zero recorded errors. Its summary records 46,908,620,800 bytes less
  allocated storage and a 44,970,954,752-byte net increase in volume free space.
  Retained snapshots and restore evidence are named in the operations record.
- The first 27 SEC source gaps all succeeded on retry. Both the original
  failures and the recovered source inventory remain available.
- A sensitive-pattern audit of the checkpoint's public files found no matches.
  Secret files were not included in the audit or read into context.
- The former project path is absent. The current project root inode is 70378520.
  The filesystem device identifier changed across the reboot; it is not a
  durable relocation identity.
- git fetch origin main succeeded. Before this checkpoint, origin had no
  commits missing locally. No push or deployment has run for this work.
  The 15 pre-existing staged additions retain their original raw-diff digest.

The main test command is:

    .venv/bin/python -B scripts/run_with_memory_budget.py --budget-mib 768 --report data/refresh_2026-10-17/checkpoint-tests-memory.jsonl -- .venv/bin/python -B -m pytest -o 'addopts=-ra --strict-markers' --no-cov -p no:cacheprovider -q tests/ingestion/test_source_catalog_acquisition.py tests/ingestion/test_source_catalog_builder.py tests/ingestion/test_streaming_catalog.py tests/ingestion/test_xlsx_required_header.py tests/ingestion/test_pjm_public_export.py tests/test_memory_budget.py tests/test_refresh_public_sources.py tests/test_refresh_journal_failures.py tests/test_refresh_bdc_nav.py tests/test_market_signals.py tests/test_overlay_history.py tests/analysis/test_ownership_graph.py tests/analysis/test_ownership_sqlite.py tests/test_run_dated_engine_2026_09_16.py

Machine-readable outputs and traces remain in data/refresh_2026-10-17:

- checkpoint-tests.log and checkpoint-tests-memory.jsonl
- compression-tests-memory.jsonl and compression roundtrip JSON records
- checkpoint-ui-tests.log and text-contrast-verification.json
- checkpoint-types.log and checkpoint-types-memory.jsonl
- checkpoint-lint.log
- ownership-sqlite-memory.jsonl and ownership-sqlite-build.log
- storage-compression-v2.log
- source-gap-retry.log

The operations record names the retained originals and snapshot directories.
The local checkpoint file list is .codex/refresh-2026-10-17/checkpoint-files.json.
Git's checkpoint diff provides the authoritative changed-file list.

Not verified or unfinished:

- Full selected-manifest SEC URL coverage, final current capital graph, and the
  dated engine/report update.
- Real browser rendering, layout at different viewports, complete interaction
  behavior, network throttling, and measured frame performance.
- GitHub publication and deployed runtime state.

The broad acquisition is still active at this dated checkpoint. Recheck its
log and private process group before resuming or starting a replacement.
Browser control is awaiting Ted's answer under Projects/AGENTS.md. The older
June report remains historical until its evidence is recomputed.

The first unbounded catalog run exhausted memory. A subsequent object-based
ownership build stopped at its 1 GiB budget. The SQLite replacement completed
at an 81.2 MiB peak. Initial source/header errors and conservative compression
skips are recorded in the operations evidence. Earlier failed test invocations
remain in the session records; corrected runs produced the results above.
