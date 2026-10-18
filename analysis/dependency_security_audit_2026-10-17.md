# Dependency security review, October 17, 2026

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
