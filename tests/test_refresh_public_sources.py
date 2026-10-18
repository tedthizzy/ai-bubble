from __future__ import annotations

import csv
import gzip
import hashlib
import json
import tracemalloc
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

from scripts import refresh_public_sources as refresh

if TYPE_CHECKING:
    import pytest


def close(work: refresh.DocumentQueue) -> None:
    work.journal.close()
    work.database.close()


def test_large_pending_queue_stays_on_disk(tmp_path: Path) -> None:
    work = refresh.DocumentQueue(tmp_path, SimpleNamespace(), {"https://example.test/known"})
    tracemalloc.start()
    try:
        added = work.enqueue(
            (
                {"filing_url": f"https://example.test/{index}", "relevance_score": "75"}
                for index in range(10_000)
            ),
            current=False,
        )
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert added == 10_000
    assert work.database.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 10_000
    assert peak < 4 * 1024**2
    assert (tmp_path / "document_queue.sqlite3").is_file()
    close(work)


def test_resume_retains_journal_and_prioritizes_current_filings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(refresh, "ROOT", tmp_path)
    original = {
        "document": {"filing_url": "https://example.test/already-saved"},
        "deal": None,
        "tranches": [],
        "error_url": None,
        "error": None,
    }
    journal = tmp_path / "edgar_results.jsonl"
    prefix = (json.dumps(original) + "\n").encode()
    journal.write_bytes(prefix)
    work = refresh.DocumentQueue(
        tmp_path, SimpleNamespace(get=lambda _url: b""), set(), resume=True
    )
    calls = []

    def acquire(_index, record, *_args, **_kwargs):
        calls.append(record["filing_url"])
        document = SimpleNamespace(to_csv_row=lambda: {"filing_url": record["filing_url"]})
        return SimpleNamespace(document=document, candidate=None, error_key=None, error=None)

    monkeypatch.setattr(refresh, "_acquire_edgar_manifest_row", acquire)
    work.enqueue(
        [
            {"filing_url": "https://example.test/already-saved", "relevance_score": "99"},
            {"filing_url": "https://example.test/backlog", "relevance_score": "99"},
        ],
        current=False,
    )
    work.enqueue(
        [{"filing_url": "https://example.test/current", "relevance_score": "1"}], current=True
    )
    work.done.set()
    work.worker()
    assert calls == ["https://example.test/current", "https://example.test/backlog"]
    assert journal.read_bytes().startswith(prefix)
    assert work.acquired == 3
    assert (
        work.database.execute("SELECT COUNT(*) FROM documents WHERE status='acquired'").fetchone()[
            0
        ]
        == 3
    )
    close(work)


def test_real_extraction_exports_original_byte_provenance(tmp_path: Path) -> None:
    payload = b"<html><body>Example Corp issued $300 million of senior unsecured notes due 2030.</body></html>"
    work = refresh.DocumentQueue(tmp_path, SimpleNamespace(get=lambda _url: payload), set())
    work.enqueue(
        [
            {
                "cik": "0000000001",
                "company_name": "Example Corp",
                "form": "8-K",
                "accession_number": "0000000001-26-000001",
                "primary_document": "filing.htm",
                "filing_url": "https://example.test/filing.htm",
                "relevance_score": "90",
                "filing_date": "2026-10-16",
            }
        ],
        current=True,
    )
    work.done.set()
    work.worker()
    result = work.finish()
    assert result["acquired"] == 1
    assert result["failed"] == 0
    with (tmp_path / "edgar/edgar_document_inventory.csv").open(newline="") as source:
        document = next(csv.DictReader(source))
    assert document["content_hash"] == hashlib.sha256(payload).hexdigest()
    assert gzip.decompress(Path(document["local_path"]).read_bytes()) == payload


def test_source_command_records_relative_log_after_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(refresh, "ROOT", tmp_path)
    Path("run").mkdir()
    result = refresh.command(Path("run"), "probe", ["-c", "print('completed')"])
    assert result["exit_code"] == 0
    assert result["log"] == "run/probe.log"
    assert Path(result["log"]).read_text().strip() == "completed"
