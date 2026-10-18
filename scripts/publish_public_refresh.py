#!/usr/bin/env python3
"""Publish one authorized data checkpoint after its supervised finisher exits."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from finish_public_refresh import process_identity
from refresh_public_sources import ROOT, emit, save

OVERLAY_PATHS = {"viz/live.json", "viz/banner.svg", "viz/history.jsonl", "viz/calendar.json"}
ATTRIBUTION = re.compile(r"co-authored|anthropic", re.I)
SENSITIVE = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|"
    r"sk-[A-Za-z0-9_-]{30,}|AKIA[A-Z0-9]{16}|AIza[A-Za-z0-9_-]{30,})"
)


def git(*args: str, root: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=check, timeout=120
    )


def index_digest(root: Path = ROOT) -> str:
    result = subprocess.run(
        ["git", "diff", "--cached", "--raw", "-z"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    return hashlib.sha256(result.stdout).hexdigest()


def verify_browser_evidence(evidence: Path, root: Path = ROOT) -> None:
    record = json.loads(evidence.read_text())
    expected = {"viz/index.html", "viz/explorer.js", "viz/explorer.css"}
    hashes = record.get("source_sha256", {})
    if not record.get("local_interaction_verified") or set(hashes) != expected:
        raise ValueError("Missing browser interaction evidence for the exact explorer sources")
    for name, digest in hashes.items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Explorer changed after browser verification: {name}")


def advance_overlay_only(root: Path = ROOT) -> None:
    git("fetch", "origin", "main", root=root)
    ahead, behind = map(
        int,
        git("rev-list", "--left-right", "--count", "HEAD...origin/main", root=root).stdout.split(),
    )
    if ahead and behind:
        raise RuntimeError("Main diverged; no automatic merge or push")
    if behind:
        incoming = set(
            git("diff", "--name-only", "HEAD..origin/main", root=root).stdout.splitlines()
        )
        if not incoming <= OVERLAY_PATHS:
            raise RuntimeError("Incoming changes exceed the known market-overlay outputs")
        git("merge", "--ff-only", "origin/main", root=root)


def verify_public_files(paths: list[str], root: Path = ROOT) -> None:
    for name in paths:
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Expected a regular generated report: {name}")
        value = path.read_text()
        if SENSITIVE.search(value):
            raise ValueError(f"Sensitive-pattern match in publication candidate: {name}")
        if path.suffix == ".json":
            json.loads(value)


def commit_reports(paths: list[str], expected_index: str, root: Path = ROOT) -> str:
    if index_digest(root) != expected_index:
        raise RuntimeError("Staged work changed; publication stopped before Git writes")
    git("add", "--", *paths, root=root)
    # Commit only these generated outputs, preserving Ted's original staged files.
    git(
        "commit",
        "--only",
        "-m",
        "Refresh Bubble source coverage and dated engine report",
        "--",
        *paths,
        root=root,
    )
    if index_digest(root) != expected_index:
        raise RuntimeError("Staged digest changed after commit; inspect state before any push")
    return git("rev-parse", "HEAD", root=root).stdout.strip()


def verify_attribution(anchor: str, approved_lines: int, root: Path = ROOT) -> dict[str, int]:
    history = git("log", "--format=%B", root=root).stdout
    recent = git("log", f"{anchor}..HEAD", "--format=%B", root=root).stdout
    matches = sum(bool(ATTRIBUTION.search(line)) for line in history.splitlines())
    new_matches = sum(bool(ATTRIBUTION.search(line)) for line in recent.splitlines())
    if matches != approved_lines or new_matches:
        raise RuntimeError("Attribution exceeds Ted's exception for existing published history")
    return {"historical_matching_lines": matches, "new_matching_lines": new_matches}


def wait_for_finisher(pid: int, identity: str) -> None:
    next_update = 0.0
    while current := process_identity(pid):
        if current != identity:
            raise RuntimeError("Finisher PID was reused; inspect state")
        if time.monotonic() >= next_update:
            emit("publication_waiting_for_finisher", pid=pid)
            next_update = time.monotonic() + 1200
        time.sleep(30)


def wait_for_pages(sha: str, run: Path) -> dict[str, Any]:
    deadline = time.monotonic() + 1800
    while time.monotonic() < deadline:
        result = subprocess.run(
            [
                "gh",
                "run",
                "list",
                "--repo",
                "tedthizzy/ai-bubble",
                "--workflow",
                "refresh-and-deploy.yml",
                "--commit",
                sha,
                "--limit",
                "5",
                "--json",
                "databaseId,status,conclusion,url,headSha",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
            timeout=60,
        )
        jobs: list[dict[str, Any]] = json.loads(result.stdout)
        if jobs:
            job = jobs[0]
            save(run / f"publication-workflow-{time.time_ns()}.json", job)
            if job["status"] == "completed":
                if job["conclusion"] != "success":
                    raise RuntimeError(f"Pages workflow ended with {job['conclusion']}")
                return job
        time.sleep(20)
    raise TimeoutError("Pages workflow remains unverified after 30 minutes")


def verify_deployed_files(paths: list[str], run: Path) -> dict[str, str]:
    expected = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths}
    deadline = time.monotonic() + 900
    while time.monotonic() < deadline:
        observed = {}
        for name in paths:
            request = urllib.request.Request(
                "https://tedthizzy.github.io/ai-bubble/" + name.removeprefix("viz/"),
                headers={"Cache-Control": "no-cache"},
            )
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    observed[name] = hashlib.sha256(response.read()).hexdigest()
            except (urllib.error.URLError, TimeoutError):
                break
        save(run / f"publication-http-{time.time_ns()}.json", observed)
        if observed == expected:
            return observed
        time.sleep(20)
    raise TimeoutError("Deployed files did not match the verified checkpoint within 15 minutes")


def publish(
    run: Path, evidence: Path, expected_index: str, anchor: str, approved_lines: int
) -> dict[str, Any]:
    if git("branch", "--show-current").stdout.strip() != "main":
        raise RuntimeError("Publication requires the existing main branch")
    finished = json.loads((run / "finish-result.json").read_text())
    status = json.loads((ROOT / "viz/freshness.json").read_text())
    queue = status["sec_acquisition"]["new_run_queue"]
    if (
        status["refresh_as_of"] != run.name.removeprefix("refresh_")
        or not status["complete"]
        or not finished.get(
            "all_manifest_documents_acquired", finished["all_manifest_urls_acquired"]
        )
        or queue.get("queued")
        or queue.get("inflight")
    ):
        raise ValueError("Finisher output does not describe complete source coverage for this run")
    verify_browser_evidence(evidence)
    if index_digest() != expected_index:
        raise RuntimeError("Staged work changed while waiting")
    advance_overlay_only()
    as_of = run.name.removeprefix("refresh_")
    paths = [
        "viz/freshness.json",
        "viz/graph_data.json",
        f"analysis/dated_engine_{as_of}_v2.json",
        f"analysis/dated_engine_{as_of}_v2.md",
    ]
    verify_public_files(paths)
    archive = (
        ROOT / ".codex/publication-snapshots" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    )
    archive.mkdir(parents=True)
    index_path = Path(git("rev-parse", "--git-path", "index").stdout.strip())
    if not index_path.is_absolute():
        index_path = ROOT / index_path
    shutil.copy2(index_path, archive / "index.before")
    sha = commit_reports(paths, expected_index)
    attribution = verify_attribution(anchor, approved_lines)
    save(
        run / "publication-pre-push.json",
        {"commit": sha, "paths": paths, "attribution": attribution},
    )
    git("push", "--dry-run", "origin", "main")
    git("push", "origin", "main")
    # A timed-out push is unknown, never retried. Fresh remote state proves receipt.
    git("fetch", "origin", "main")
    if git("merge-base", "--is-ancestor", sha, "origin/main", check=False).returncode:
        raise RuntimeError("The remote does not contain the published commit")
    workflow = wait_for_pages(sha, run)
    deployed = verify_deployed_files(
        ["viz/freshness.json", "viz/graph_data.json", "viz/explorer.js", "viz/explorer.css"], run
    )
    return {
        "commit": sha,
        "paths": paths,
        "workflow": workflow,
        "deployed_sha256": deployed,
        "all_manifest_urls_acquired": finished["all_manifest_urls_acquired"],
        "all_manifest_documents_acquired": finished.get(
            "all_manifest_documents_acquired", finished["all_manifest_urls_acquired"]
        ),
        "source_document_replacements": finished.get("source_document_replacements", []),
        "coverage": finished["coverage"],
        "core_judgments": finished["core_judgments"],
        "original_staged_digest_preserved": index_digest() == expected_index,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--finisher-pid", required=True, type=int)
    parser.add_argument("--browser-evidence", required=True, type=Path)
    parser.add_argument("--expected-index", required=True)
    parser.add_argument("--attribution-anchor", required=True)
    parser.add_argument("--approved-historical-attribution-lines", required=True, type=int)
    parser.add_argument("--start-record", default="publication-start.json")
    args = parser.parse_args()
    run = args.run.resolve()
    identity = process_identity(args.finisher_pid)
    if args.finisher_pid <= 1 or not identity:
        parser.error("Expected the observed, active finisher PID")
    start = run / args.start_record
    with start.open("x") as stream:
        json.dump(
            {
                "pid": args.finisher_pid,
                "identity": identity,
                "publisher_pid": os.getpid(),
                "authorization": "Ted approved browser control and publication while preserving existing history.",
                "automatic_acquisition_restart": False,
            },
            stream,
            indent=2,
        )
    try:
        wait_for_finisher(args.finisher_pid, identity)
        result = publish(
            run,
            args.browser_evidence.resolve(),
            args.expected_index,
            args.attribution_anchor,
            args.approved_historical_attribution_lines,
        )
        save(run / "publication-result.json", result)
        emit("refresh_publication_finished", **result)
    except Exception as error:
        save(run / "publication-stopped.json", {"error": str(error), "automatic_retry": False})
        raise


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget(512)
    main()
