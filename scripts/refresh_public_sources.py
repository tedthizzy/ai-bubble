#!/usr/bin/env python3
"""Acquire a dated public-source refresh without replacing historical evidence.

All SEC work shares one paced connection pool. Download workers keep consuming
the backlog while filing discovery and independent public-source jobs run.
Documents are stored as gzip; inventories retain hashes of original bytes.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import UTC, date, datetime
from email.message import Message
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from collections.abc import Iterator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bubble.ingestion.concurrency import DomainFetchLimiter, FetchConcurrencyConfig  # noqa: E402
from bubble.ingestion.edgar.document_acquisition import _acquire_edgar_manifest_row  # noqa: E402
from bubble.ingestion.edgar.filing_manifest import (  # noqa: E402
    build_edgar_filing_manifest,
    filing_document_table_url,
    parse_filing_document_table,
)

IDENTITY = "ai-bubble research ted1508@gmail.com"
OLD_MANIFESTS = (
    ROOT / "data/manifests/edgar_filing_manifest_20260917-020227.csv",
    ROOT / "data/manifests/edgar_exhibit_manifest_20260601-195938.csv",
)
OLD_INVENTORY = ROOT / "data/edgar_acquisition_2026-09-16/edgar_document_inventory.csv"
OLD_CATALOG = (
    ROOT / "data/source_catalogs/source_catalog_2026-09-16_with_pjm_cycle_and_serial_full.csv"
)


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, default=str)
        stream.write("\n")


def emit(event: str, **details: Any) -> None:
    print(
        json.dumps({"at_utc": datetime.now(UTC).isoformat(), "event": event, **details}), flush=True
    )


def iter_rows(path: Path) -> Any:
    with path.open(newline="") as stream:
        yield from csv.DictReader(stream)


def rows(path: Path) -> list[dict[str, str]]:
    return list(iter_rows(path))


def csv_fields(path: Path) -> list[str]:
    with path.open(newline="") as source:
        fields = csv.DictReader(source).fieldnames
    if fields is None:
        raise ValueError(f"Missing CSV header: {path}")
    return list(fields)


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        return
    fields = list(dict.fromkeys(key for record in records for key in record))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


class PublicClient:
    def __init__(self, run: Path, requests_per_second: float) -> None:
        self.run = run
        self.lock = threading.Lock()
        self.next_sec = 0.0
        self.interval = 1.0 / requests_per_second
        self.client = httpx.Client(
            headers={"User-Agent": IDENTITY},
            follow_redirects=True,
            timeout=httpx.Timeout(60, connect=20),
            limits=httpx.Limits(max_connections=96, max_keepalive_connections=48),
        )
        self.calls = 0

    @contextmanager
    def response(self, url: str) -> Iterator[httpx.Response]:
        host = httpx.URL(url).host
        sec = host == "sec.gov" or host.endswith(".sec.gov")
        if sec:
            with self.lock:
                now = time.monotonic()
                delay = max(0.0, self.next_sec - now)
                self.next_sec = max(now, self.next_sec) + self.interval
            if delay:
                time.sleep(delay)
        with self.client.stream("GET", url) as response:
            if sec and response.status_code == 429:
                wait = response.headers.get("Retry-After", "60")
                seconds = float(wait) if wait.replace(".", "", 1).isdigit() else 60.0
                with self.lock:
                    self.next_sec = max(self.next_sec, time.monotonic() + seconds)
                emit("sec_rate_limit", retry_after_seconds=seconds)
            response.raise_for_status()
            yield response
        with self.lock:
            self.calls += 1
            count = self.calls
        if count % 250 == 0:
            emit("public_requests", successful=count)

    def get(self, url: str) -> bytes:
        with self.response(url) as response:
            return response.read()

    def download(self, url: str, destination: Path) -> None:
        """Stream decoded HTTP bytes into a saved document, retaining failed parts."""
        if destination.exists():
            raise FileExistsError(f"Refusing to replace saved source: {destination}")
        with tempfile.NamedTemporaryFile(
            dir=destination.parent, prefix=destination.name + ".", suffix=".part", delete=False
        ) as staged:
            with self.response(url) as response:
                if destination.suffix == ".gz":
                    with gzip.GzipFile(
                        fileobj=staged, mode="wb", compresslevel=3, mtime=0
                    ) as compressed:
                        for block in response.iter_bytes(chunk_size=1024 * 1024):
                            compressed.write(block)
                else:
                    for block in response.iter_bytes(chunk_size=1024 * 1024):
                        staged.write(block)
            staged.flush()
            os.fsync(staged.fileno())
        # An interrupted response never becomes a completed cache entry.
        os.link(staged.name, destination)
        # Only retire this successful staging name. The exact same inode remains
        # at destination; failed response parts and prior sources are retained.
        os.unlink(staged.name)

    def json(self, url: str) -> Any:
        document_table_url = filing_document_table_url(url)
        if document_table_url:
            return self.filing_document_table(document_table_url, parse_filing_document_table)
        digest = hashlib.sha256(url.encode()).hexdigest()
        path = self.run / "sec_json" / (digest + ".json.gz")
        path.parent.mkdir(exist_ok=True)
        if path.exists():
            try:
                with gzip.open(path, "rt") as stream:
                    return json.load(stream)
            except (OSError, EOFError, ValueError):
                emit("sec_cache_incomplete", url=url, preserved=str(path))
                path = path.with_name(digest + f".retry-{time.time_ns()}.json.gz")
        payload = self.get(url)
        # Parallel financial and manifest readers can request the same response.
        with self.lock:
            if not path.exists():
                with path.open("xb") as stream:
                    stream.write(gzip.compress(payload, mtime=0))
                save(
                    path.with_suffix(".source.json"),
                    {
                        "url": url,
                        "retrieved_at": datetime.now(UTC).isoformat(),
                        "sha256": hashlib.sha256(payload).hexdigest(),
                    },
                )
        return json.loads(payload)

    def filing_document_table(self, url: str, parser: Any) -> Any:
        digest = hashlib.sha256(url.encode()).hexdigest()
        path = self.run / "sec_json" / (digest + ".html.gz")
        path.parent.mkdir(exist_ok=True)
        if path.exists():
            with gzip.open(path, "rb") as stream:
                return parser(stream.read(), url)
        payload = self.get(url)
        result = parser(payload, url)
        with self.lock:
            if not path.exists():
                with path.open("xb") as stream:
                    stream.write(gzip.compress(payload, mtime=0))
                save(
                    path.with_suffix(".source.json"),
                    {
                        "url": url,
                        "retrieved_at": datetime.now(UTC).isoformat(),
                        "sha256": hashlib.sha256(payload).hexdigest(),
                        "index_parser": result["index_parser"],
                    },
                )
        return result


class DocumentQueue:
    """A durable queue whose pending document records stay on disk."""

    def __init__(
        self, run: Path, client: PublicClient, known: set[str], *, resume: bool = False
    ) -> None:
        self.run = run
        self.client = client
        self.known = known
        self.lock = threading.Lock()
        self.done = threading.Event()
        self.stop = threading.Event()
        self.limiter = DomainFetchLimiter(FetchConcurrencyConfig(sec_requests_per_second=0))
        database = run / "document_queue.sqlite3"
        journal = run / "edgar_results.jsonl"
        if not resume and (database.exists() or journal.exists()):
            raise FileExistsError("Acquisition state exists; inspect it before --resume")
        self.database = sqlite3.connect(database, check_same_thread=False)
        self.database.execute("PRAGMA journal_mode=WAL")
        self.database.execute("PRAGMA synchronous=NORMAL")
        self.database.execute("PRAGMA cache_size=-4096")
        self.database.execute("PRAGMA temp_store=FILE")
        self.database.execute("""CREATE TABLE IF NOT EXISTS documents (
            sequence INTEGER PRIMARY KEY, url TEXT UNIQUE NOT NULL,
            priority INTEGER NOT NULL DEFAULT 1, score INTEGER NOT NULL DEFAULT 0,
            record TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL DEFAULT 'queued', result TEXT)""")
        self.database.execute(
            "CREATE INDEX IF NOT EXISTS next_document ON documents(status,priority,score DESC,sequence)"
        )
        if journal.exists():
            archived = ROOT / ".codex/refresh-2026-10-17/journal-checkpoints"
            archived.mkdir(parents=True, exist_ok=True)
            snapshot = archived / (str(time.time_ns()) + ".jsonl.gz")
            with journal.open("rb") as source, gzip.open(snapshot, "xb") as target:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    target.write(block)
            with journal.open() as source:
                for number, line in enumerate(source, 1):
                    try:
                        entry = json.loads(line)
                    except ValueError as exc:
                        raise ValueError(
                            f"Partial journal line {number}; preserved, not replayed"
                        ) from exc
                    document = entry.get("document")
                    url = (
                        document["filing_url"]
                        if document
                        else entry.get("filing_url") or entry.get("error_url")
                    )
                    if url and not url.startswith(("https://", "http://")):
                        # Older failure entries stored the record key under
                        # error_url. Recover its URL from the durable queue.
                        parts = url.split(":", 2)
                        matches = []
                        if len(parts) == 3:
                            matches = self.database.execute(
                                """SELECT url FROM documents WHERE
                                json_extract(record,'$.cik')=? AND
                                json_extract(record,'$.accession_number')=? AND
                                json_extract(record,'$.primary_document')=?""",
                                parts,
                            ).fetchall()
                        if len(matches) != 1:
                            raise ValueError(
                                f"Cannot resolve legacy failed record; journal preserved: {url}"
                            )
                        url = matches[0][0]
                    if url:
                        self.database.execute(
                            """INSERT INTO documents(url,status,result) VALUES (?,?,?)
                            ON CONFLICT(url) DO UPDATE SET status=excluded.status,result=excluded.result""",
                            (url, "acquired" if document else "failed", line),
                        )
        # A worker may have saved raw bytes before the reboot. Production resume
        # checks those bytes before fetching; the source file is never replaced.
        self.database.execute("UPDATE documents SET status='queued' WHERE status='inflight'")
        self.database.commit()
        self.enqueued = self.database.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        self.acquired = self.database.execute(
            "SELECT COUNT(*) FROM documents WHERE status='acquired'"
        ).fetchone()[0]
        self.failed = self.database.execute(
            "SELECT COUNT(*) FROM documents WHERE status='failed'"
        ).fetchone()[0]
        self.completed = self.acquired + self.failed
        self.journal = journal.open("a" if resume else "x")

    def enqueue(self, records: Any, *, current: bool) -> int:
        added = 0
        for record in records:
            url = record.get("filing_url", "")
            if not url or url in self.known:
                continue
            with self.lock:
                cursor = self.database.execute(
                    """INSERT OR IGNORE INTO documents
                    (url,priority,score,record) VALUES (?,?,?,?)""",
                    (
                        url,
                        0 if current else 1,
                        int(record.get("relevance_score") or 0),
                        json.dumps(record),
                    ),
                )
                added += cursor.rowcount
                if current:
                    self.database.execute("UPDATE documents SET priority=0 WHERE url=?", (url,))
                if added and added % 500 == 0:
                    self.database.commit()
        with self.lock:
            self.database.commit()
            self.enqueued += added
        emit("documents_enqueued", current=current, added=added, total=self.enqueued)
        return added

    def worker(self) -> None:
        while not self.stop.is_set():
            with self.lock:
                row = self.database.execute("""SELECT sequence,record FROM documents
                    WHERE status='queued' ORDER BY priority,score DESC,sequence LIMIT 1""").fetchone()
                if row:
                    self.database.execute(
                        "UPDATE documents SET status='inflight' WHERE sequence=?", (row[0],)
                    )
                    self.database.commit()
            if row is None:
                if self.done.wait(0.25):
                    return
                continue
            index, serialized = row
            manifest_record = json.loads(serialized)
            result = _acquire_edgar_manifest_row(
                index,
                manifest_record,
                self.run / "edgar",
                self.client.get,
                self.limiter,
                3,
                2.0,
                True,
                True,
                fetch_to_file=getattr(self.client, "download", None),
            )
            document = result.document.to_csv_row() if result.document else None
            candidate = result.candidate
            entry = {
                "document": document,
                "deal": candidate.to_capital_csv_row() if candidate else None,
                "tranches": candidate.to_tranche_csv_rows() if candidate else [],
                "filing_url": manifest_record["filing_url"],
                "error_url": manifest_record["filing_url"] if result.error else None,
                "error_key": result.error_key,
                "error": result.error,
            }
            serialized = json.dumps(entry, default=str)
            with self.lock:
                self.journal.write(serialized + "\n")
                self.journal.flush()
                self.database.execute(
                    "UPDATE documents SET status=?,result=? WHERE sequence=?",
                    ("acquired" if document else "failed", serialized, index),
                )
                self.database.commit()
                self.completed += 1
                self.acquired += document is not None
                self.failed += document is None
                if self.completed % 100 == 0:
                    count = self.database.execute(
                        "SELECT COUNT(*) FROM documents WHERE status='queued'"
                    ).fetchone()[0]
                    emit(
                        "edgar_progress",
                        completed=self.completed,
                        acquired=self.acquired,
                        failed=self.failed,
                        queued=count,
                    )

    def finish(self) -> dict[str, Any]:
        self.journal.close()
        exports = {
            "edgar_document_inventory.csv": "document",
            "deals.csv": "deal",
            "tranches.csv": "tranches",
        }
        output = self.run / "edgar"
        output.mkdir(exist_ok=True)
        for filename, key in exports.items():
            destination = output / filename
            if destination.exists():
                raise FileExistsError(f"Inspect existing export before replacing it: {destination}")
            baseline = OLD_INVENTORY if key == "document" else OLD_INVENTORY.parent / filename
            fields = csv_fields(baseline)
            with destination.open("x", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                for (serialized,) in self.database.execute(
                    "SELECT result FROM documents WHERE status='acquired' ORDER BY sequence"
                ):
                    record = json.loads(serialized)
                    values = (
                        record[key] if key == "tranches" else [record[key]] if record[key] else []
                    )
                    writer.writerows(values)
        error_path = self.run / "edgar_errors.jsonl"
        with error_path.open("x") as errors:
            for (serialized,) in self.database.execute(
                "SELECT result FROM documents WHERE status='failed' ORDER BY sequence"
            ):
                record = json.loads(serialized)
                errors.write(
                    json.dumps({"url": record["error_url"], "error": record["error"]}) + "\n"
                )
        summary = {
            "attempted": self.completed,
            "acquired": self.acquired,
            "failed": self.failed,
            "enqueued": self.enqueued,
            "errors_file": str(error_path),
            "queue": "disk-backed SQLite",
        }
        save(self.run / "edgar_acquisition.json", summary)
        self.database.close()
        return summary


def load_script(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def discover(
    run: Path, as_of: date, client: PublicClient, documents: DocumentQueue
) -> dict[str, Any]:
    universe = run / "discovery_universe.json"
    if universe.exists():
        state = json.loads(universe.read_text())
        ciks = state["ciks"]
        census_count = state["official_recent_rows"]
    else:
        ciks = {
            r["cik"].zfill(10) for path in OLD_MANIFESTS for r in iter_rows(path) if r.get("cik")
        }
        census = []
        for quarter in range(3, (as_of.month - 1) // 3 + 2):
            url = f"https://www.sec.gov/Archives/edgar/full-index/{as_of.year}/QTR{quarter}/master.idx"
            raw = client.get(url)
            with (run / f"{as_of.year}-QTR{quarter}-master.idx.gz").open("xb") as stream:
                stream.write(gzip.compress(raw, mtime=0))
            for line in raw.decode(errors="replace").splitlines():
                fields = line.split("|", 4)
                if (
                    len(fields) == 5
                    and re.fullmatch(r"\d+", fields[0])
                    and "2026-09-16" <= fields[3] <= as_of.isoformat()
                ):
                    census.append(
                        dict(
                            zip(
                                ("cik", "company_name", "form", "filing_date", "filename"),
                                fields,
                                strict=True,
                            )
                        )
                    )
                    ciks.add(fields[0].zfill(10))
        write_csv(run / "new_official_filing_census.csv", census)
        ciks = sorted(ciks)
        census_count = len(census)
        save(
            universe,
            {
                "as_of": as_of,
                "ciks": ciks,
                "official_recent_rows": census_count,
                "latest_filing_date": max((r["filing_date"] for r in census), default=None),
                "selection": "Every existing selected CIK plus every CIK in the new official quarterly index window; no entity cap.",
            },
        )
    emit("filing_discovery_started", ciks=len(ciks), official_rows=census_count)
    batches = run / "filing_batches"
    batches.mkdir(exist_ok=True)
    summaries: list[dict[str, Any]] = []
    added = total_records = 0
    for offset in range(0, len(ciks), 64):
        stem = batches / f"{offset:06d}"
        csv_path = stem.with_suffix(".csv")
        summary_path = stem.with_suffix(".summary.json")
        if not csv_path.exists() or not summary_path.exists():
            if csv_path.exists() or summary_path.exists():
                raise FileExistsError(f"Partial filing batch: {stem}; inspect before replaying")
            manifest = build_edgar_filing_manifest(
                ciks[offset : offset + 64],
                fetch_json=client.json,
                since=date(2026, 9, 16),
                until=as_of,
                max_filings_per_cik=None,
                include_exhibits=True,
                max_exhibits_per_filing=None,
                max_workers=8,
                sec_requests_per_second=0,
                retry_attempts=3,
                retry_backoff_seconds=2,
            )
            manifest.write_csv(csv_path)
            manifest.write_summary_json(summary_path)
        summary = json.loads(summary_path.read_text())
        summaries.append({"path": str(summary_path), "errors": len(summary.get("errors", {}))})
        total_records += sum(1 for _ in iter_rows(csv_path))
        added += documents.enqueue(iter_rows(csv_path), current=True)
        emit(
            "filing_batch_finished",
            ciks_completed=min(offset + 64, len(ciks)),
            total_ciks=len(ciks),
            total_records=total_records,
        )
    combined = run / "current_filing_manifest.csv"
    if not combined.exists():
        paths = sorted(batches.glob("*.csv"))
        headers = csv_fields(paths[0])
        with combined.open("x", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=headers)
            writer.writeheader()
            for path in paths:
                writer.writerows(iter_rows(path))
    result = {
        "ciks": len(ciks),
        "manifest_rows": total_records,
        "new_documents": added,
        "batches": summaries,
        "failed_ciks": sum(item["errors"] for item in summaries),
    }
    save(run / "current_filing_manifest.summary.json", result)
    return result


def finance(run: Path, as_of: date, client: PublicClient) -> dict[str, Any]:
    module = load_script("refresh_case_zero_financials")

    class Sec:
        def get(self, url: str) -> bytes:
            try:
                return client.get(url)
            except httpx.HTTPStatusError as exc:
                headers = Message()
                for name, value in exc.response.headers.items():
                    headers[name] = value
                raise urllib.error.HTTPError(
                    url, exc.response.status_code, str(exc), headers, None
                ) from exc
            except httpx.HTTPError as exc:
                raise urllib.error.URLError(str(exc)) from exc

    targets = list(module.TARGETS)
    table = client.json("https://www.sec.gov/files/company_tickers.json")
    bdc = {"ARCC", "BXSL", "FSK", "GBDC", "MAIN", "OBDC", "PSEC", "TSLX"}
    targets += [
        (r["ticker"], str(r["cik_str"]).zfill(10), "bdc")
        for r in table.values()
        if r["ticker"] in bdc
    ]
    entities = []
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = [
            executor.submit(
                module.refresh_one, Sec(), ticker, cik, role, as_of, run / "financial_raw"
            )
            for ticker, cik, role in targets
        ]
        for future in as_completed(futures):
            record = future.result()
            entities.append(record)
            emit("financial_entity", ticker=record["ticker"], status=record["status"])
    panel = {
        "as_of": as_of.isoformat(),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "baseline_date": module.BASELINE_DATE.isoformat(),
        "target_count": len(targets),
        "complete_count": sum(e["status"] == "complete" for e in entities),
        "partial_count": sum(e["status"] == "partial" for e in entities),
        "unavailable_count": sum(e["status"] == "unavailable" for e in entities),
        "source_method": "SEC submissions and companyfacts; one shared request budget; no paid APIs",
        "raw_dir": str((run / "financial_raw").relative_to(ROOT)),
        "output_json_name": f"case_zero_financials_{as_of}_v4.json",
        "entities": sorted(entities, key=lambda e: e["ticker"]),
    }
    save(ROOT / "analysis" / panel["output_json_name"], panel)
    with (ROOT / "analysis" / f"case_zero_financials_{as_of}_v4.md").open("x") as stream:
        stream.write(module.render_markdown(panel))
    return {
        k: panel[k]
        for k in ("target_count", "complete_count", "partial_count", "unavailable_count")
    }


def command(run: Path, label: str, args: list[str]) -> dict[str, Any]:
    env = {
        k: v
        for k, v in os.environ.items()
        if not any(s in k.upper() for s in ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL"))
    }
    env.update(PYTHONDONTWRITEBYTECODE="1", EDGAR_IDENTITY=IDENTITY)
    path = run / (label + ".log")
    if path.exists():
        path = run / (label + "." + str(time.time_ns()) + ".log")
    with path.open("x") as stream:
        process = subprocess.Popen(
            [sys.executable, "-B", *args],
            cwd=ROOT,
            env=env,
            stdout=stream,
            stderr=subprocess.STDOUT,
        )
        emit("source_job_started", name=label, pid=process.pid)
        code = process.wait()
    return {"command": args, "exit_code": code, "log": str(path.resolve().relative_to(ROOT))}


def catalog_jobs(run: Path) -> dict[str, Any]:
    results = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        jobs = {}
        for name in ("public", "gleif"):
            directory = run / name
            summary = directory / "source_catalog_acquisition.summary.json"
            if summary.exists():
                results[name] = {
                    "retained_completed_batch": True,
                    "summary": json.loads(summary.read_text()),
                }
                continue
            path = run / (name + "_source_catalog.csv")
            if not path.exists():
                source = [
                    row
                    for row in rows(OLD_CATALOG)
                    if row["source_uri"].startswith(("http://", "https://"))
                    and "sec.gov/" not in row["source_uri"]
                    and ("gleif" in row["source_uri"].lower()) == (name == "gleif")
                ]
                write_csv(path, source)
            jobs[
                executor.submit(
                    command,
                    run,
                    "catalog_" + name,
                    [
                        "scripts/acquire_source_catalog.py",
                        str(path),
                        "--output-dir",
                        str(directory),
                        "--max-workers",
                        "4",
                        "--other-requests-per-second",
                        "8",
                        "--other-domain-concurrency",
                        "4",
                        "--retry-backoff-seconds",
                        "2",
                    ],
                )
            ] = name
        for future in as_completed(jobs):
            results[jobs[future]] = future.result()
            emit("catalog_group_finished", group=jobs[future])
    return results


def dynamic_catalog(run: Path) -> dict[str, Any]:
    path = run / "dynamic_source_catalog.csv"
    if not path.exists():
        discovery = command(
            run,
            "dynamic_catalog",
            [
                "scripts/build_source_catalog.py",
                "--limit",
                "1",
                "--resolve-dynamic-public-sources",
                "--output",
                str(path),
            ],
        )
        if discovery["exit_code"] != 0:
            return discovery
    catalog = run / "dynamic_acquisition_catalog.csv"
    if not catalog.exists():
        selected = missing_dynamic_sources(run, ("public", "gleif"))
        if not selected:
            return {"artifacts_added": 0}
        write_csv(catalog, selected)
    summary = run / "dynamic" / "source_catalog_acquisition.summary.json"
    if summary.exists():
        return {"retained_completed_batch": True, "summary": json.loads(summary.read_text())}
    return command(
        run,
        "dynamic_acquisition",
        [
            "scripts/acquire_source_catalog.py",
            str(catalog),
            "--output-dir",
            str(run / "dynamic"),
            "--max-workers",
            "2",
        ],
    )


def catalog_identity(row: dict[str, str], *, inventory: bool = False) -> tuple[str, ...]:
    metadata = (
        json.loads(row.get("metadata") or "{}")
        if inventory
        else {
            key.removeprefix("meta_"): value
            for key, value in row.items()
            if key.startswith("meta_") and value
        }
    )
    metadata = {key: value for key, value in metadata.items() if value not in (None, "")}
    return (
        row["source_uri"],
        row["corpus"],
        row["parser"],
        json.dumps(metadata, sort_keys=True, separators=(",", ":")),
    )


def missing_dynamic_sources(run: Path, completed: tuple[str, ...]) -> list[dict[str, str]]:
    # POST pages and source revisions share URLs. Their request and revision
    # metadata are part of artifact identity; URI alone loses current pages.
    successful: set[tuple[str, ...]] = set()
    for name in completed:
        inventory = run / name / "source_artifact_inventory.csv"
        if inventory.exists():
            successful.update(catalog_identity(row, inventory=True) for row in iter_rows(inventory))
    return [
        row
        for row in iter_rows(run / "dynamic_source_catalog.csv")
        if row["source_uri"].startswith(("http://", "https://"))
        and "sec.gov/" not in row["source_uri"]
        and catalog_identity(row) not in successful
    ]


def resume_jobs(run: Path, jobs: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Retain completed source jobs while recovering interrupted work."""
    results = {}
    pending = {}
    for name, operation in jobs.items():
        previous = run / (name + "_result.json")
        if previous.exists():
            result = json.loads(previous.read_text())
            if "error" not in result and result.get("exit_code", 0) == 0:
                results[name] = result
                continue
        pending[name] = operation
    return results, pending


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--sec-requests-per-second", type=float, default=8)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Retain completed jobs and recover the saved document journal",
    )
    args = parser.parse_args()
    if not 0 < args.sec_requests_per_second <= 8:
        parser.error("SEC rate must be positive and at most 8 across the whole refresh")
    run = ROOT / "data" / f"refresh_{args.as_of}"
    run.mkdir(parents=True, exist_ok=True)
    if (run / "run-start.json").exists() and not args.resume:
        parser.error("Run exists. Inspect its state, then use --resume.")
    save(
        run / (f"resume-{time.time_ns()}.json" if args.resume else "run-start.json"),
        {
            "as_of": args.as_of,
            "started_at_utc": datetime.now(UTC),
            "pid": os.getpid(),
            "sec_rate": args.sec_requests_per_second,
            "billing": "No paid APIs or model calls",
            "pending_documents": "disk-backed SQLite",
            "filing_batch_ciks": 64,
            "document_workers": 8,
        },
    )
    csv.field_size_limit(10**9)
    client = PublicClient(run, args.sec_requests_per_second)
    known = {record["filing_url"] for record in iter_rows(OLD_INVENTORY)}
    documents = DocumentQueue(run, client, known, resume=args.resume)
    for manifest in OLD_MANIFESTS:
        documents.enqueue(iter_rows(manifest), current=False)
    workers = [threading.Thread(target=documents.worker, name=f"edgar-{i}") for i in range(8)]
    for worker in workers:
        worker.start()
    jobs = {
        "financials": lambda: finance(run, args.as_of, client),
        "filing_discovery": lambda: discover(run, args.as_of, client, documents),
        "source_catalog": lambda: catalog_jobs(run),
        "dynamic_acquisition": lambda: dynamic_catalog(run),
        "gpu_prices": lambda: command(
            run,
            "gpu_prices",
            [
                "scripts/acquire_gpu_pricing.py",
                "--output-dir",
                str(run / "gpu_prices"),
                "--workers",
                "8",
            ],
        ),
        "fdic": lambda: command(
            run, "fdic", ["scripts/refresh_fdic_banks.py", "--as-of", str(args.as_of)]
        ),
    }
    results, pending = resume_jobs(run, jobs)
    if "filing_discovery" not in pending:
        documents.done.set()
    with ThreadPoolExecutor(max_workers=max(1, len(pending))) as executor:
        futures = {executor.submit(operation): name for name, operation in pending.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as exc:
                results[name] = {"error_type": type(exc).__name__, "error": str(exc)}
            destination = run / (name + "_result.json")
            if destination.exists():
                destination = run / (name + f"_result.{time.time_ns()}.json")
            save(destination, results[name])
            emit("source_job_finished", name=name)
            if name == "filing_discovery":
                documents.done.set()
    documents.done.set()
    for worker in workers:
        worker.join()
    results["edgar"] = documents.finish()
    save(run / "run-result.json", {"completed_at_utc": datetime.now(UTC), "jobs": results})
    emit("refresh_acquisition_finished", **results["edgar"])


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget()
    main()
