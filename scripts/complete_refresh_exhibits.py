#!/usr/bin/env python3
"""Acquire relevant text exhibits for every selected filing, with a durable queue."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import sqlite3
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from _thread import LockType
    from collections.abc import Iterator

    import httpx

from bubble.ingestion.concurrency import DomainFetchLimiter, FetchConcurrencyConfig
from bubble.ingestion.edgar.filing_manifest import (
    FilingRecord,
    _fetch_exhibit_records_for_filing,
    _should_fetch_exhibit_index,
    filing_document_table_url,
    parse_filing_document_table,
)
from bubble.models.base import Provenance, SourceType

sys.path.insert(0, str(Path(__file__).resolve().parent))
from finish_public_refresh import process_identity
from refresh_public_sources import (
    OLD_INVENTORY,
    OLD_MANIFESTS,
    ROOT,
    DocumentQueue,
    PublicClient,
    emit,
    save,
)


def filing_record(row: dict[str, Any]) -> FilingRecord:
    def dates(key: str) -> date | None:
        return date.fromisoformat(row[key]) if row.get(key) else None

    return FilingRecord(
        cik=row["cik"],
        company_name=row.get("company_name") or row["cik"],
        ticker=row.get("ticker") or None,
        form=row["form"],
        accession_number=row["accession_number"],
        filing_date=dates("filing_date"),
        report_date=dates("report_date"),
        acceptance_datetime=row.get("acceptance_datetime"),
        items=(row.get("items") or "").split("|"),
        primary_document=row["primary_document"],
        primary_document_description=row.get("primary_document_description"),
        size_bytes=int(row["size_bytes"]) if row.get("size_bytes") else None,
        is_xbrl=str(row.get("is_xbrl")).lower() == "true",
        is_inline_xbrl=str(row.get("is_inline_xbrl")).lower() == "true",
        source_uri=row.get("source_uri") or row["filing_url"],
        filing_url=row["filing_url"],
        relevance_score=int(row.get("relevance_score") or 0),
        relevance_reasons=(row.get("relevance_reasons") or "").split("|"),
        provenance=Provenance(
            source_uri=row.get("source_uri") or row["filing_url"],
            source_type=SourceType.SEC_EDGAR,
            content_hash=row.get("provenance_content_hash")
            or Provenance.compute_content_hash(json.dumps(row, sort_keys=True)),
        ),
        filing_detail_url=row.get("filing_detail_url")
        or (
            f"https://www.sec.gov/Archives/edgar/data/{int(row['cik'])}/"
            f"{row['accession_number'].replace('-', '')}/index.json"
        ),
    )


class SharedClient(PublicClient):
    """Use one SEC request/second beside the original eight-request producer."""

    def __init__(self, run: Path, main_pid: int, identity: str) -> None:
        super().__init__(run, 1)
        self.main_pid = main_pid
        self.main_identity = identity
        self.next_probe = 0.0
        self.main_active = True
        self.index_sources: dict[str, tuple[str, str]] = {}
        self.index_locks: dict[str, LockType] = {}
        self.index_state_lock = threading.Lock()
        self.index_cache_hits = 0
        for receipt in (run / "sec_json").glob("*.html.source.json"):
            record = json.loads(receipt.read_text())
            accession = urlsplit(record["url"]).path.split("/")[-2]
            self.index_sources.setdefault(accession, (record["url"], record["sha256"]))

    def json(self, url: str) -> Any:
        """An accession identifies one submission even when several CIKs co-file."""
        index_url = filing_document_table_url(url)
        if index_url is None:
            return super().json(url)
        accession = urlsplit(index_url).path.split("/")[-2]
        with self.index_state_lock:
            lock = self.index_locks.setdefault(accession, threading.Lock())
        with lock:
            if accession in self.index_sources:
                source_uri, expected_hash = self.index_sources[accession]
                path = (
                    self.run
                    / "sec_json"
                    / (hashlib.sha256(source_uri.encode()).hexdigest() + ".html.gz")
                )
                with gzip.open(path, "rb") as stream:
                    raw = stream.read()
                if hashlib.sha256(raw).hexdigest() != expected_hash:
                    raise ValueError("Changed cached SEC document index")
                payload = parse_filing_document_table(raw, source_uri)
                with self.index_state_lock:
                    self.index_cache_hits += 1
                return payload
            payload = super().json(url)
            self.index_sources[accession] = (payload["source_uri"], payload["source_sha256"])
            return payload

    @contextmanager
    def response(self, url: str) -> Iterator[httpx.Response]:
        if time.monotonic() >= self.next_probe:
            observed = process_identity(self.main_pid)
            if observed and observed != self.main_identity:
                raise RuntimeError("Original acquisition PID reused; inspect rate allocation")
            active = bool(observed)
            if self.main_active and not active:
                self.interval = 1 / 8
                emit(
                    "exhibit_sec_rate_changed",
                    requests_per_second=8,
                    reason="original acquisition exited",
                )
            self.main_active = active
            self.next_probe = time.monotonic() + 10
        with super().response(url) as response:
            yield response


def seed_parents(run: Path, db: sqlite3.Connection) -> None:
    core = json.loads((ROOT / "analysis/case_zero_financials_2026-10-17_v4.json").read_text())
    ciks = {entity["cik"] for entity in core["entities"]}
    db.execute(
        "CREATE TABLE parents(url TEXT PRIMARY KEY,core INTEGER,day TEXT,record TEXT,status TEXT DEFAULT 'queued',error TEXT)"
    )
    paths = [OLD_MANIFESTS[0], run / "current_filing_manifest.csv"]
    for path in paths:
        with path.open(newline="") as stream, db:
            for row in csv.DictReader(stream):
                if row.get("document_type", "primary") != "primary":
                    continue
                record = filing_record(row)
                if _should_fetch_exhibit_index(record):
                    db.execute(
                        "INSERT OR IGNORE INTO parents(url,core,day,record) VALUES(?,?,?,?)",
                        (
                            row["filing_url"],
                            row["cik"] in ciks,
                            row.get("filing_date"),
                            json.dumps(row),
                        ),
                    )


def upgrade_parent_indexes(db: sqlite3.Connection, destination: Path) -> None:
    """Recheck filename-only indexes, retaining their complete previous state."""
    columns = {row[1] for row in db.execute("PRAGMA table_info(parents)")}
    if "index_parser" in columns:
        return
    snapshot = destination / f"parents-before-document-types-{time.time_ns()}.sqlite3"
    with sqlite3.connect(snapshot) as backup:
        db.backup(backup)
    checked = db.execute("SELECT COUNT(*) FROM parents WHERE status!='queued'").fetchone()[0]
    with db:
        db.execute(
            "ALTER TABLE parents ADD COLUMN index_parser TEXT DEFAULT 'sec_document_types_v1'"
        )
        db.execute(
            "CREATE TABLE previous_index_pass AS SELECT url,status,error,index_parser FROM parents WHERE status!='queued'"
        )
        db.execute("UPDATE previous_index_pass SET index_parser='filename_inference'")
        db.execute("UPDATE parents SET status='queued' WHERE status IN ('checked','failed')")
    emit("exhibit_indexes_requeued_for_document_types", rechecked=checked, snapshot=str(snapshot))


def upgrade_cofiler_indexes(db: sqlite3.Connection, destination: Path) -> None:
    """Retain the rejected pass, then retry same-accession co-registrant links."""
    pending = db.execute(
        "SELECT COUNT(*) FROM parents WHERE status='queued' AND index_parser!='sec_document_types_v2'"
    ).fetchone()[0]
    failed = db.execute(
        "SELECT COUNT(*) FROM parents WHERE status='failed' AND error=?",
        ("SEC document table references a file outside its accession",),
    ).fetchone()[0]
    if not pending and not failed:
        return
    stamp = time.time_ns()
    snapshot = destination / f"parents-before-cofilers-{stamp}.sqlite3"
    with sqlite3.connect(snapshot) as backup:
        db.backup(backup)
    with db:
        db.execute(
            f"CREATE TABLE cofiler_rejections_{stamp} AS SELECT url,status,error,index_parser FROM parents WHERE status='failed'"
        )
        db.execute(
            "UPDATE parents SET status='queued',error=NULL WHERE status='failed' AND error=?",
            ("SEC document table references a file outside its accession",),
        )
        db.execute("UPDATE parents SET index_parser='sec_document_types_v2' WHERE status='queued'")
    emit("cofiler_indexes_requeued", rejected=failed, pending=pending, snapshot=str(snapshot))


def main() -> None:  # noqa: PLR0912, PLR0915 - bounded one-off source coordinator
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--main-pid", required=True, type=int)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    run = args.run.resolve()
    destination = run / "exhibit_completion"
    destination.mkdir(exist_ok=args.resume)
    identity = process_identity(args.main_pid)
    if not identity:
        raise ValueError("Observe the original acquisition before starting")
    start = {
        "pid": os.getpid(),
        "identity": process_identity(os.getpid()),
        "original_pid": args.main_pid,
        "original_identity": identity,
        "selection": "Every exhibit-eligible selected primary filing, with no per-filing exhibit cap.",
        "budget_mib": 2048,
        "sec_rate_while_original_active": 1,
        "index_parser": "sec_document_types_v2",
        "index_workers": 4,
        "source_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in (
                "scripts/complete_refresh_exhibits.py",
                "scripts/refresh_public_sources.py",
                "src/bubble/ingestion/edgar/filing_manifest.py",
            )
        },
    }
    marker = run / "exhibit-completion-start.json"
    if marker.exists():
        if not args.resume:
            raise FileExistsError(marker)
        prior = json.loads(marker.read_text())
        if process_identity(prior["pid"]):
            raise RuntimeError("Previous exhibit process is still present")
        retained = run / f"exhibit-completion-start-{prior['pid']}.json"
        with retained.open("x") as stream:
            json.dump(prior, stream, indent=2)
        marker.write_text(json.dumps(start, indent=2) + "\n")
    else:
        save(marker, start)
    client = SharedClient(destination, args.main_pid, identity)
    known: set[str] = set()
    with OLD_INVENTORY.open(newline="") as stream:
        known.update(row["filing_url"] for row in csv.DictReader(stream))
    with sqlite3.connect(f"file:{run / 'document_queue.sqlite3'}?mode=ro", uri=True) as original:
        known.update(row[0] for row in original.execute("SELECT url FROM documents"))
    work = DocumentQueue(destination, client, known, resume=args.resume)
    # Discovery and document downloads have separate semaphores. A continuous
    # discovery feeder must not monopolize the download workers' semaphore.
    index_limiter = DomainFetchLimiter(
        FetchConcurrencyConfig(
            sec_domain_concurrency=4,
            sec_requests_per_second=0,
        )
    )
    with sqlite3.connect(destination / "parents.sqlite3") as db:
        db.execute("PRAGMA cache_size=-4096")
        if not args.resume:
            seed_parents(run, db)
        upgrade_parent_indexes(db, destination)
        upgrade_cofiler_indexes(db, destination)
        count = db.execute("SELECT COUNT(*) FROM parents").fetchone()[0]
        emit("exhibit_parent_census", parents=count)
        rows = iter(
            db.execute(
                "SELECT url,record FROM parents WHERE status='queued' ORDER BY core DESC,day DESC,url"
            )
        )
        workers = [threading.Thread(target=work.worker) for _ in range(8)]
        for worker in workers:
            worker.start()
        completed = db.execute("SELECT COUNT(*) FROM parents WHERE status!='queued'").fetchone()[0]
        manifest = destination / "exhibits.csv"
        fields = None
        if args.resume and manifest.exists():
            with manifest.open(newline="") as existing:
                fields = csv.DictReader(existing).fieldnames
        with (
            manifest.open("a" if args.resume else "x", newline="") as stream,
            ThreadPoolExecutor(max_workers=4) as executor,
        ):
            header = csv.DictWriter(stream, fieldnames=fields) if fields else None
            active = {}

            def submit() -> bool:
                item = next(rows, None)
                if item is None:
                    return False
                url, row = item
                future = executor.submit(
                    _fetch_exhibit_records_for_filing,
                    completed,
                    filing_record(json.loads(row)),
                    client.json,
                    index_limiter,
                    None,
                    3,
                    2,
                )
                active[future] = url
                return True

            for _ in range(32):
                if not submit():
                    break
            while active:
                ready, _ = wait(active, return_when=FIRST_COMPLETED)
                for future in ready:
                    url = active.pop(future)
                    _, exhibits, error = future.result()
                    if error:
                        db.execute(
                            "UPDATE parents SET status='failed',error=? WHERE url=?", (error, url)
                        )
                    else:
                        records = [record.to_csv_row() for record in exhibits]
                        if records:
                            if header is None:
                                header = csv.DictWriter(stream, fieldnames=list(records[0]))
                                header.writeheader()
                            header.writerows(records)
                            stream.flush()
                            work.enqueue(records, current=True)
                        db.execute("UPDATE parents SET status='checked' WHERE url=?", (url,))
                    db.commit()
                    completed += 1
                    if completed % 100 == 0:
                        emit("exhibit_discovery_progress", checked=completed, total=count)
                    submit()
        work.done.set()
        for worker in workers:
            worker.join()
        result = work.finish()
        result["parents"] = dict(db.execute("SELECT status,COUNT(*) FROM parents GROUP BY status"))
        result["index_cache"] = {
            "unique_accessions": len(client.index_sources),
            "reused": client.index_cache_hits,
        }
    save(destination / "run-result.json", result)
    emit("exhibit_completion_finished", **result)


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget()
    main()
