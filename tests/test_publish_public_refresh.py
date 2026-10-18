from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/publish_public_refresh.py"
spec = importlib.util.spec_from_file_location("publish_public_refresh", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def command(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    command(tmp_path, "init", "--initial-branch=main")
    command(tmp_path, "config", "user.name", "Fixture")
    command(tmp_path, "config", "user.email", "fixture@example.invalid")
    command(tmp_path, "config", "core.hooksPath", "/dev/null")
    (tmp_path / "report.json").write_text('{"version":1}\n')
    command(tmp_path, "add", "report.json")
    command(tmp_path, "commit", "-m", "Initial fixture")
    return tmp_path


def test_report_commit_preserves_unrelated_staged_addition(repository: Path) -> None:
    (repository / "ted.json").write_text('{"preserve":true}\n')
    command(repository, "add", "ted.json")
    before = module.index_digest(repository)
    (repository / "report.json").write_text('{"version":2}\n')
    (repository / "new.md").write_text("Dated report\n")
    sha = module.commit_reports(["report.json", "new.md"], before, repository)
    assert sha == command(repository, "rev-parse", "HEAD")
    assert set(
        command(repository, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()
    ) == {"report.json", "new.md"}
    assert module.index_digest(repository) == before
    assert command(repository, "diff", "--cached", "--name-only") == "ted.json"


def test_index_change_stops_before_staging_reports(repository: Path) -> None:
    before = command(repository, "rev-parse", "HEAD")
    (repository / "report.json").write_text('{"version":2}\n')
    with pytest.raises(RuntimeError, match="before Git writes"):
        module.commit_reports(["report.json"], "wrong digest", repository)
    assert command(repository, "rev-parse", "HEAD") == before
    assert not command(repository, "diff", "--cached", "--name-only")


def test_browser_evidence_requires_exact_rendered_sources(tmp_path: Path) -> None:
    hashes = {}
    for name in ["viz/index.html", "viz/explorer.js", "viz/explorer.css"]:
        path = tmp_path / name
        path.parent.mkdir(exist_ok=True)
        path.write_text("fixture")
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({"local_interaction_verified": True, "source_sha256": hashes}))
    module.verify_browser_evidence(evidence, tmp_path)
    (tmp_path / "viz/explorer.js").write_text("changed")
    with pytest.raises(ValueError, match="changed after browser"):
        module.verify_browser_evidence(evidence, tmp_path)


def test_attribution_exception_covers_only_approved_history(repository: Path) -> None:
    anchor = command(repository, "rev-parse", "HEAD")
    assert module.verify_attribution(anchor, 0, repository)["new_matching_lines"] == 0
    command(repository, "commit", "--allow-empty", "-m", "Co-authored historical fixture")
    with pytest.raises(RuntimeError, match="exception"):
        module.verify_attribution(anchor, 1, repository)
    accepted_anchor = command(repository, "rev-parse", "HEAD")
    assert (
        module.verify_attribution(accepted_anchor, 1, repository)["historical_matching_lines"] == 1
    )


def test_publication_candidates_reject_sensitive_patterns(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    path.write_text(json.dumps({"private": "-----BEGIN PRIVATE KEY-----"}))
    with pytest.raises(ValueError, match="Sensitive-pattern"):
        module.verify_public_files([path.name], tmp_path)


def test_reused_finisher_pid_stops_without_waiting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "process_identity", lambda _: "reused")
    with pytest.raises(RuntimeError, match="reused"):
        module.wait_for_finisher(1234, "original")


def test_missing_completion_stops_before_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        module, "git", lambda *args, **kwargs: type("Result", (), {"stdout": "main"})()
    )
    with pytest.raises(FileNotFoundError):
        module.publish(tmp_path, tmp_path / "evidence.json", "digest", "anchor", 0)


@pytest.mark.parametrize("counts,changed", [("1 1", ""), ("0 1", "src/changed.py")])
def test_remote_divergence_and_unrelated_updates_stop_before_merge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, counts: str, changed: str
) -> None:
    calls = []

    def fake_git(*args, **kwargs):
        calls.append(args)
        return type("Result", (), {"stdout": counts if args[0] == "rev-list" else changed})()

    monkeypatch.setattr(module, "git", fake_git)
    with pytest.raises(RuntimeError):
        module.advance_overlay_only(tmp_path)
    assert not any(args[0] == "merge" for args in calls)
