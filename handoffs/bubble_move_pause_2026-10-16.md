# Bubble move pause - 2026-10-16


## Full refresh resumed - October 17, 2026

Ted authorized the full data refresh, performance work, storage streamlining,
and GitHub reconciliation after the move checkpoint. That authorization
supersedes the earlier instruction to pause after moving.

The first bulk refresh caused system memory pressure, and Ted had to reboot the
Mac. The observed refresh child footprint reached 23.39 GiB on a 24 GiB host.
The incident and verified repair are documented in
[the memory incident record](../analysis/refresh_memory_incident_2026-10-17.md).
The repaired import completed 4,101,539 GLEIF records at a 45.4 MiB peak. All
heavy entry points now use the independent memory supervisor by default.

The broad SEC acquisition is interrupted. Its 2,258 completed document journal
entries remain in `data/refresh_2026-10-17/edgar_results.jsonl`. Completed finance,
GPU pricing, FDIC, and public-source outputs remain in the same dated run.
The repaired driver is `scripts/refresh_public_sources.py --as-of 2026-10-17
--resume`; verify that no other copy is active before launching it. It uses a
disk-backed document queue, batches filing discovery, and retains completed jobs.

The visualization and storage work remain unfinished. A cached layout has been
computed locally and pinned visualization libraries downloaded. The UI has not
been changed or browser-tested, and no refresh or optimization has been pushed.
The original 15 staged additions must remain separate from task commits.


## Move completed - 2026-10-17 10:21 PDT

The sole project location is `/Users/ted/Projects/bubble`. The original `/Users/ted/Documents/dev-archive/bubble` is absent. Apple reports the new folder as outside iCloud. The project was moved with an exclusive same-filesystem directory rename. No recursive deletion of the original project ran. iCloud quota reduction has not been measured.

This completes the requested move checkpoint. Pause here. The dated download and earlier pause records below describe previous states. Recheck live state before resuming.

### Preservation and relocation repairs

At 10:18:54 PDT, materialization finished with zero cloud-only files, zero read failures, and zero scan errors. Before the move, all 353,922 entries from the initial inventory remained present. The known script-version difference and interpreter repairs are documented below.

At 10:21:47 PDT, all 353,946 entries in the fresh pre-move inventory matched after the rename. Directory and file identities, file sizes, modification times, modes, and symlink targets matched. Six sample SHA-256 hashes matched. The root inode remained 70378520. The original path was absent.

The relocation then repaired 14 internal data symlinks as relative links and rewrote the old prefix in 100 generated virtual environment files. Three command examples now use `--repo-root .`. The Neo4j installer now finds `.env` relative to the repository. The installer was syntax checked and was not executed.

The environment uses the already-installed Python 3.12.5 through Homebrew's stable `opt` path. The original missing Python 3.12.11 target and configuration remain recorded in the local snapshots. No dependency installation or upgrade ran. All four active `.pth` files have UF_HIDDEN cleared outside iCloud. Imports now work without `PYTHONPATH`.

Saved provenance still contains the original absolute paths. `src/bubble/paths.py` maps that exact archived checkout prefix to the current checkout when reading cached files. Seven existing readers use it. Relative paths and unrelated absolute paths keep their previous meaning. The two scripts that previously used only the standard library still import under global Python. Source documents and their recorded hashes were not rewritten.

The full post-repair comparison found all original entries present. All 121,748 original regular files under `data/` retained their identity, mode, size, and modification time. All 21 active symlinks resolve. The only extra original-file metadata changes outside the intended repairs were in `.git/index`, after Git refreshed its cache. HEAD and the staged-diff digest stayed unchanged. The initial failing comparison and the reviewed result are both retained. Ruff added six cache files; they remain preserved.

### Verification

- The selected offline pytest suite ran through the relocated environment without `PYTHONPATH`: `200 passed in 3.52s`. The exact command and output are in `evidence/current-session/post-move-tests.json`.
- All 6,975 archived EDGAR inventory paths resolve under the new checkout. Three actual cached documents passed stored-byte SHA-256 checks and decompressed content-hash checks through `SourceCatalogClient`, using both saved paths and file URIs. Their inodes remained unchanged.
- Environment imports, `bubble --help`, shell activation, the standalone merge CLI, and the standalone registry module import passed from `/tmp`. The first activation check failed because the test command lost its quotes. The corrected test passed. Both results remain in the evidence.
- Ruff checks and format checks for the new helper and tests passed. Import and undefined-name checks for the seven changed readers passed. `git diff --check` and `bash -n scripts/install_gds_neo4j_desktop.sh` passed.
- The full GUI, financial data freshness, remote GitHub state, visualization behavior, and live Neo4j were not tested at this checkpoint.

### Evidence, recovery, and Git

Original edited files, original symlink metadata, and the pre-checkpoint Git index are retained in `.codex/relocation-2026-10-17/`. This directory is gitignored. The `evidence/current-session/` and `evidence/previous-session/` directories retain drivers, manifests, logs, and results. Large text records are stored with lossless gzip compression. The archive manifest records hashes of the uncompressed originals. Temporary originals remain in place. No agent history, security snapshots, or logs were pruned.

To check the move, verify the new directory, confirm the old path is absent, inspect cloud-only flags, and run the installed CLI from outside the checkout. The archived verification drivers contain the complete inventory and path checks. Drivers with exclusive outputs must not be replayed blindly.

Recovery uses the preserved originals for individual file edits. The relative data symlinks remain portable. A reverse exclusive directory rename was tested on a scratch directory on this filesystem; it preserved identities and rejected an occupied destination. A full-project reverse move into iCloud was not performed. The original interpreter target is missing, so restoring that broken link would disable the environment.

Before the checkpoint commit, main was at `0585071`. The 15 pre-existing staged `analysis/` additions remained unchanged, with staged-diff SHA-256 `df66eae0573bd34899df7e4451677d9050f1db80625921296cb8651112e2bf7d`. The checkpoint commit uses an explicit relocation file list to exclude those additions. No fetch, pull, or push has run during the move work. Secret file contents were not printed.

### Work after this pause

Reconcile local and GitHub work on main while preserving the 15 staged additions. Then establish the actual data freshness from source manifests and record coverage dates. Download completion does not establish data freshness.

Inspect the GitHub visualization and measure real interactions. Use one font family and at most two font sizes. Reduce repeated labels and assess less costly rendering and interaction for grey background dots. Verify screenshots, contrast, and reduced motion behavior after changes.

Audit storage for supported reductions that preserve core functionality and recovery. Keep security snapshots, agent transcripts, and logs. No visualization or storage optimization has run at this checkpoint.

## Resumed download - 2026-10-17 07:39:16 PDT

Ted authorized continuing through the verified move, followed by a pause at that checkpoint. The October 16 notes below remain a dated record of the earlier pause.

The latest metadata check at 07:38:51 PDT on October 17 found 23,734 cloud-only files totaling 1,806,082,672 bytes. The source exists; the destination does not. Apple reports the source folder as an iCloud item and the Projects directory as outside iCloud. These are observations, not a guarantee of later state.

A new materialization helper is reading remaining files concurrently with 128 workers. Its script, requested-file manifest, logs, and prepared exclusive-rename driver are under `/var/folders/_w/b5k4dz1109q4nj1sx3y7dg7h0000gn/T/bubble-relocate-00glqmu8/`. Do not blindly rerun the drivers: output files are exclusive, and a partially completed move requires fresh source/destination checks.

The pre-existing `.venv/bin/python` symlink referenced a missing Homebrew Python 3.12.11 installation. It now points to the already-installed `/opt/homebrew/opt/python@3.12/bin/python3.12` (verified version 3.12.5). `.venv/pyvenv.cfg` now describes that interpreter. No dependency installation or upgrade was performed. Originals and metadata are preserved under `.codex/relocation-2026-10-17/` inside this repository.

Four active `.pth` setup files carried macOS UF_HIDDEN, which made Python skip them. Clearing the flags allowed core imports and `bubble --help` to pass. The flags returned while the source remained in iCloud, so the initial baseline pytest run failed collection with `ModuleNotFoundError: bubble`. A second offline run with `PYTHONPATH=src` passed all 31 selected tests. The flag change persisted for 30 seconds on a scratch copy outside iCloud. Apply the final flag repair after relocation and verify the installed package without a source-path override.

The prepared relocation repairs cover 14 data symlinks, 100 generated environment files, three command examples, and the Neo4j installation script's project-relative `.env` lookup. The actual data-link and file-path repairs have not run yet. The Neo4j installer has not been executed. Existing security snapshots and logs remain preserved.

A full metadata comparison found all 353,922 entries from the original inventory present. The original script-version difference documented below remains preserved in Git. The additional intentional changes are the interpreter link and its configuration. A scratch test on the same filesystem verified that the exclusive rename preserves directory and file inodes, rejects an existing destination with EEXIST, and can reverse a rename without changing those inodes.

Git was rechecked before this update: main at `0585071`, the same 15 staged additions, and this untracked handoff. No fetch, pull, push, or commit has run. GitHub reconciliation, data freshness, visualization changes, and storage optimization remain deferred until the move checkpoint.

## Earlier pause record

Paused before the move, at Ted's request for an interim stopping point. iCloud's remaining file downloads made the move unsuitable as the immediate pause point. No automatic move process remains running.

The project remains at `/Users/ted/Documents/dev-archive/bubble`. `/Users/ted/Projects/bubble` does not exist. The temporary project snapshot and the initial clone probe were removed after verification. No second project copy created by this task remains. macOS has accepted download requests and can continue downloading while agent work is stopped.

At 18:12 PDT on 2026-10-16, 28,110 original files totaling 79,116,802,395 bytes were local. Another 207,942 original files remained cloud-only. The initial inventory contained 236,052 regular files totaling 91,646,874,806 bytes, 117,846 directories, and 24 symlinks. Download status can change after this observation. Download time is not evidence of data freshness.

The full source entry set matched the initial inventory before this handoff was added. Every original regular file and symlink retained its inode, mode, size, and modification time, except `scripts/refresh_live_overlay.py`. Its initial version matched Git blob `11c42afd30bf02e643112018b8f36d2757315a0b` in commit `829bb7e`. Its current version matched blob `f2f5889d28cf709c0d822efdf8a31b248b221550` in commit `0585071`. Both commits were verified as ancestors of the current HEAD. The cause of this version change during download was not established. Both versions remain preserved in Git. Directory identities and modes also matched the initial inventory.

The cleanup removed 138,587 entries from the exact temporary snapshot at `/private/tmp/bubble-move-odwzsr8_/bubble.snapshot`. It checked recorded entry identity and used individual unlink operations and empty-directory removals without following symlinks. The original project was never recursively deleted. SHA-256 checks matched the source and temporary copies of `README.md`, `pyproject.toml`, and `.gitignore` before cleanup.

Git remained on `main`. The last observed HEAD was `058507182b198e80a2e662db126cc79c2ba8c264`. The 15 staged additions under `analysis/`, with filenames ending in ` 2.json` or ` 2.md`, were already present and remain staged. This task has not fetched, pulled, pushed, or committed. The remote has not been checked. The handoff is a new unstaged file.

Resume with the move:

1. Recheck both locations, Git status, current processes, and cloud-only file flags. Finish materializing every original file. All 215,462 remaining per-file download requests in the bulk pass were accepted by macOS, but acceptance does not prove completion.
2. Capture a fresh inventory and safety snapshot. The earlier inventory includes an outdated version of one script and does not include this handoff. Do not rerun the old helpers unchanged: they use exclusive output files, a deleted snapshot, and process IDs from the previous run.
3. Verify source and destination parent devices before using an exclusive atomic directory rename. Preserve existing staged work. Verify the complete destination inventory and absence of the original path after moving.
4. Repair the 14 internal absolute symlinks under `data/economy_input_2026-09-16_manifest_pre_deals_v1/source_acquisition/source_rows/` and `data/economy_input_2026-09-16_nonsec_v1/source_acquisition/source_rows/`. Each set covers queue_records, permit_records, tracker_records, ppas, equipment_records, ownership_records, and lei_records CSVs. They still point at the original location and remain unchanged at this pause. Convert them to relative links after the move and verify every target.
5. Check relocation-sensitive configuration, including generated virtual environment shebangs and activation files. Application runtime has not been tested. Remove only the verified temporary snapshot after the move, leaving one project location at `/Users/ted/Projects/bubble`.

Then complete Ted's remaining request:

- Reconcile the latest local and GitHub work safely, then pull or push as needed on main. Preserve the existing staged additions. Verify the remote state before reporting sync complete.
- Establish how up to date the actual Bubble data is from source manifests and record coverage dates. No data freshness conclusion has been made.
- Inspect and measure the GitHub visualization. Reduce repetitive labels and visual noise. Use one font family and at most two font sizes. Assess whether grey background dots can show less information or require less interaction while preserving access to core information.
- Implement supported performance improvements and verify real rendered interactions, screenshots, text contrast, and reduced motion behavior.
- Audit storage and streamline it without losing core functionality or preventing easy restoration. Preserve existing security snapshots, agent transcripts, and logs. No storage optimization has been performed.

Local evidence is retained in `/private/tmp/bubble-move-odwzsr8_/`: `paused.json`, `before.json`, `changed-file-preservation.json`, `download-queue-result.json`, and the move and cleanup logs. `paused.json` corrects a path-label error in the raw cleanup log; the separate Git blob check names the correct file. Temporary diagnostic paths may not persist indefinitely, so reverify live state when resuming. Secret file contents were not printed.
