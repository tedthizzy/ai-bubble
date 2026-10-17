import json
from pathlib import Path
from types import SimpleNamespace

from scripts import refresh_public_sources as refresh


def test_resume_resolves_legacy_failure_key_and_retains_later_success(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(refresh, "ROOT", tmp_path)
    work = refresh.DocumentQueue(tmp_path, SimpleNamespace(get=lambda _: b""), set())
    record = {"cik": "0000000001", "accession_number": "0000000001-26-000001",
              "primary_document": "filing.htm", "filing_url": "https://example.test/filing.htm"}
    work.enqueue([record], current=True)
    work.journal.write(json.dumps({"document": None, "error_url": "0000000001:0000000001-26-000001:filing.htm", "error": "Temporary failure"}) + "\n")
    work.journal.write(json.dumps({"document": {"filing_url": record["filing_url"]}, "error_url": None, "error": None}) + "\n")
    work.journal.close()
    work.database.close()
    resumed = refresh.DocumentQueue(tmp_path, SimpleNamespace(), set(), resume=True)
    assert resumed.acquired == 1
    assert resumed.failed == 0
    assert resumed.database.execute("SELECT url FROM documents").fetchall() == [(record["filing_url"],)]
    resumed.journal.close()
    resumed.database.close()


def test_new_failure_journal_retains_the_requested_url(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(refresh, "ROOT", tmp_path)
    monkeypatch.setattr(refresh, "_acquire_edgar_manifest_row", lambda *_: SimpleNamespace(
        document=None, candidate=None, error_key="cik:accession:document", error="Temporary failure"))
    work = refresh.DocumentQueue(tmp_path, SimpleNamespace(get=lambda _: b""), set())
    work.enqueue([{"filing_url": "https://example.test/filing.htm"}], current=True)
    work.done.set()
    work.worker()
    work.journal.close()
    work.database.close()
    entry = json.loads((tmp_path / "edgar_results.jsonl").read_text())
    assert entry["filing_url"] == entry["error_url"] == "https://example.test/filing.htm"
