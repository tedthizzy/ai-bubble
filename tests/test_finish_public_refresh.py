import json
import sqlite3
from pathlib import Path

import pytest
from scripts import finish_public_refresh as finish


def completed(run: Path, *, pending: bool = False) -> None:
    (run / "run-result.json").write_text(json.dumps({"jobs": {"edgar": {"acquired": 1}}}))
    with sqlite3.connect(run / "document_queue.sqlite3") as database:
        database.execute("CREATE TABLE documents(status TEXT)")
        database.execute("INSERT INTO documents VALUES (?)", ("queued" if pending else "acquired",))


def test_continuation_waits_for_same_process_and_checks_completed_queue(
    tmp_path: Path, monkeypatch
):
    completed(tmp_path)
    states = iter(["same process", ""])
    sleeps = []
    monkeypatch.setattr(finish, "process_identity", lambda _: next(states))
    monkeypatch.setattr(finish.time, "sleep", sleeps.append)
    finish.wait_for_acquisition(tmp_path, 123, "same process")
    assert sleeps == [30]


@pytest.mark.parametrize("case", ["budget_stop", "reused_pid", "unfinished_queue"])
def test_continuation_refuses_uncertain_or_incomplete_acquisition(
    tmp_path: Path, monkeypatch, case
):
    if case == "unfinished_queue":
        completed(tmp_path, pending=True)
    monkeypatch.setattr(
        finish, "process_identity", lambda _: "different process" if case == "reused_pid" else ""
    )
    with pytest.raises((ValueError, RuntimeError)):
        finish.wait_for_acquisition(tmp_path, 123, "same process")


def test_failed_merge_keeps_results_and_prevents_later_graph_publication(
    tmp_path: Path, monkeypatch
):
    calls = []

    def command(_run, name, arguments):
        calls.append(name)
        return {"exit_code": 1 if name == "finish-merge" else 0, "command": arguments}

    monkeypatch.setattr(finish, "command", command)
    with pytest.raises(RuntimeError, match="merge"):
        finish.finish(tmp_path)
    assert calls == ["finish-retry-gaps", "finish-merge"]
    assert (tmp_path / "finish-merge-result.json").exists()
    assert not (tmp_path / "finish-result.json").exists()
