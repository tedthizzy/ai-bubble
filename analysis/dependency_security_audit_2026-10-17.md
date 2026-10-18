# Dependency security review, October 17, 2026

## Installed environment verification, 2026-10-18T04:44:21.915754-07:00

The reviewed lock is installed in the active .venv. All 970 Python tests passed
in 50.80 seconds with PYTHONPATH=src and no validation overlays. Peak process-group
memory was 709,511,304 bytes under 1.5 GiB. CI 39123486171 passed full strict Mypy
and the runtime suite for the refreshed source report.

The actual sync changed 33 distribution records. This supersedes the isolated
candidate's 31-record count. jsonlines was unrequired by the lock; OpenCV moved
to its locked headless distribution. No jsonlines or cv2 imports were found in
src or scripts. The real HTML converter and security checks passed.

The successful receipt is
`data/refresh_2026-10-17/security-environment-application-v3/result.json`.
Its before, updated, undo and reapply manifests verify every file byte, symlink,
mode, filesystem flag and modification time. Directory metadata also matches.
The driver copied FROM snapshots into the active path during actual undo and
reapply. It retained both displaced environments and never ran a snapshot's
interpreter. The 512 MiB supervisor observed a 133,842,768-byte peak.

The first snapshot attempt stopped on macOS cp -p symlink flag errors before
installation. A host-Python attempt then stopped on an imported httpx dependency
before environment writes. Both logs and the partial snapshot remain retained.
The corrected standalone driver uses cp -cR, followed by copystat without
following symlinks. Its successful output is a new directory; no failed pass
was replayed over existing state.

GitHub now reports one open alert: [Accelerate GHSA-4j2p-28q2-5m79](https://github.com/advisories/GHSA-4j2p-28q2-5m79).
Its primary advisory lists no patched release. A final live PyPI check still
reports 1.15.0 and omits the advisory. The explicit HTML-only boundary remains
in force. No alert was dismissed and no system package or global setting changed.

The driver and tested restoration sequence are retained at
`data/refresh_2026-10-17/verification_drivers/apply_locked_environment.py`.
The operations record names the archive and verification commands.

Earlier dated checkpoints are retained below. Their pending states are superseded by this completion entry.

## Current verification and local environment continuation

The lock remains the reviewed security candidate. Complete CI 39111714173 passed
for e61edda6b787fb4041fc40fdc9852f6461d13199, including strict source Mypy.
The latest local suite passed 969 tests in 15.00 seconds under 1.5 GiB; its
observed peak was 708,216,992 bytes. The active .venv remains unchanged while
source acquisition, final processing and publication continue.

The retained driver is
`data/refresh_2026-10-17/verification_drivers/apply_locked_environment.py`.
Its syntax check passed. Its supervised continuation is waiting for publisher
94613 and a successful publication-result.json. It requires complete document
coverage, unchanged uv.lock SHA256, retained staged work and ended source jobs
before any environment write. This is a project .venv change; it does not
install system packages or modify global environment settings.

The driver creates a new APFS snapshot under
`.codex/security-snapshots/2026-10-17/post-publication-<UTC timestamp>/`.
It compares every file byte and symlink, then runs the verified temporary uv
binary with `sync --locked --all-extras`. It retains an updated snapshot and
both displaced active environments. The undo check copies FROM venv-before
into the active .venv path and compares its bytes and package metadata. The
reapply check copies FROM venv-updated into the active path and repeats those
comparisons. It never executes an interpreter inside a snapshot or prunes one.
These install/undo/reapply steps remain unverified until the continuation runs.

Check `data/refresh_2026-10-17/security-environment-application/events.jsonl`,
its result.json and security-environment-apply-memory.jsonl. The process-group
budget is 512 MiB and has no automatic retry. If a step stops, inspect the last
journal phase and current active-path package metadata before any mutation.
The full runtime suite must then run against the active environment without
validation overlays; that is a separate 1.5 GiB supervised step.

## Earlier review and validation evidence, retained

The candidate lockfile has been checked against PyPI advisory records for all
301 locked registry versions. All requests succeeded. Accelerate 1.13.0 is the
remaining affected package in those records; its GHSA and PYSEC entries describe
the same issue. The [inventory](dependency_security_audit_2026-10-17.json) records
the exact lock hash, package changes, source records and verification limits.

GitHub initially reported 12 open alerts. The first candidate patched 11 of
those alerts. The complete PyPI pass also identified newer Docling, Docling Slim,
fsspec, langgraph-sdk and multidict advisories. The current candidate includes
those fixes and their required dependency updates. Minimum fixed versions are
encoded in pyproject.toml. No GitHub alert was dismissed.

The candidate changes 30 packages on this Mac. It was installed into the isolated
.codex/security-validation-complete-2026-10-17 overlay. The existing .venv is
unchanged while the active acquisitions run. Installation into .venv remains
required work after those processes finish, with a retained snapshot first.

The full runtime suite against the candidate returned `947 passed in 22.33s`.
The supervisor observed a 705,775,728-byte peak under its 1.5 GiB budget.
The real Docling HTML converter retained filing text and tables. The security
checks rejected PDF and checkpoint inputs and observed no embedded image or
model pipeline operations. The converter still explicitly disables remote
fetching, local fetching, images and browser rendering.

The [Accelerate advisory](https://github.com/advisories/GHSA-4j2p-28q2-5m79)
still lists no patched release. PyPI's latest release remains 1.15.0 and omits
that advisory. The September audit inspected that exact release and found the
unsafe checkpoint path. The current work preserves the HTML-only boundary and
the passing converter checks. Standalone untrusted model checkpoint loading
remains outside that boundary.

Ruff passes across src and tests. All 296 files pass formatting. Eight existing
format failures were repaired; AST comparison proved those edits changed no
Python behavior. The expectations and verdict modules pass focused strict Mypy.
A separate complete source check stopped at its 768 MiB supervision budget,
with 820,200,480 bytes observed. Its budget was retained. Remote complete source
CI remains pending publication of this checkpoint.

The first full test run against the earlier seven-package candidate found two
historical report failures and an expected-observation-field mismatch. Frozen
issuance snapshots now preserve the September and October reports. The September
snapshot matches the original report's SHA-256 exactly. The Pacific-date test
now also checks observed_as_of. The corrected suite and the complete candidate
both passed. Original failure logs remain retained.

The first metadata audit rejected cuda-toolkit 13.0.3.0 when PyPI returned its
equivalent canonical version 13.0.3. Package-name and PEP 440 version checks
corrected that error. The final complete audit includes that version. Known
advisory databases cannot establish the absence of vulnerabilities.

Commands and retained evidence:

- scripts/audit_locked_dependencies.py --lock uv.lock --output <new directory>
- data/refresh_2026-10-17/dependency-pypi-audit-v2/audit.json
- data/refresh_2026-10-17/dependency-complete-tests.log
- data/refresh_2026-10-17/dependency-complete-tests-memory.jsonl
- data/refresh_2026-10-17/dependency-install-plan.json
- data/refresh_2026-10-17/lock-check.log

The temporary uv binary came from its verified PyPI wheel and lives under
/tmp/bubble-uv-20261017. It was not installed globally. No GitHub authentication,
scope, app or workflow setting changed.

Verification update, 2026-10-17T23:46:07.652486-07:00: remote CI 39103139050 passed full strict source
Mypy. Its two Linux test portability failures are repaired locally. The latest
candidate suite passed 952 tests in 12.08s at 703,006,808 bytes. Ruff passed and
297 files passed formatting. Main .venv installation remains pending acquisition.
The initial local override accidentally collected retained '* 2.py' files;
the corrected command keeps the configured ignore glob. Both logs are retained.

Mako correction, 2026-10-17T23:51:08.162147-07:00: GitHub alert 71 reports
[GHSA-5639-2j2p-m4mx](https://github.com/advisories/GHSA-5639-2j2p-m4mx),
a Windows template path issue affecting Mako through 1.4.1. PyPI's current Mako
metadata omits this advisory. The lock now selects 1.4.3, above the verified
1.4.2 fixed release. The minimum is encoded in pyproject.toml. The Mac candidate
now changes 31 packages. The new 301-version PyPI audit again has zero errors;
that source alone cannot establish the complete advisory set. GitHub alerts
are checked separately. The candidate including Mako passes 952 tests in
13.70 seconds at a 704,497,800-byte observed peak. The new overlay is
.codex/security-validation-mako-2026-10-17, layered ahead of the complete overlay.

CI 39105258023 for 24ab270 succeeded, including full strict source Mypy and the
runtime suite. Five Linux platform checks were skipped. That run predates this
Mako patch. Pages 39105258021 succeeded; all four deployed explorer hashes match
the actual browser-verified financing checkpoint. Main .venv remains unchanged
while acquisition continues. Its installation is still required.
