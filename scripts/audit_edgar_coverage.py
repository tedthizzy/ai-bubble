#!/usr/bin/env python3
"""Reconcile SEC filing/exhibit manifests against an EDGAR acquisition inventory.

The audit reads CSVs incrementally and keeps the URL join in a temporary SQLite
database. It makes no SEC requests and leaves all inputs unchanged.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DIMENSIONS = {
    "by_form": "form",
    "by_cik": "cik",
    "by_document_type": "document_type",
    "by_filing_date": "filing_date",
}
MANIFEST_FIELDS = ("filing_url", "cik", "form", "document_type", "filing_date")


def _read_csv(path: Path, required: tuple[str, ...]) -> tuple[list[str], Any]:
    stream = path.open(newline="", encoding="utf-8-sig")
    reader = csv.DictReader(stream)
    fields = reader.fieldnames or []
    missing = sorted(set(required) - set(fields))
    if missing:
        stream.close()
        raise ValueError(f"{path} missing required CSV columns: {', '.join(missing)}")
    return fields, (stream, reader)


def _record_key(row: dict[str, str]) -> str:
    """Match the acquisition summary's key without changing its current format."""
    return ":".join(
        (
            row.get("cik", "unknown"),
            row.get("accession_number", "unknown"),
            row.get("primary_document", "unknown"),
        )
    )


def _counts(db: sqlite3.Connection, column: str | None = None) -> dict[str, Any]:
    group = f"COALESCE(NULLIF(r.{column}, ''), '<missing>')" if column else None
    select_group = f"{group} AS group_key, " if group else ""
    group_by = "GROUP BY group_key ORDER BY group_key" if group else ""
    rows = db.execute(
        f"""SELECT {select_group}
                   COUNT(*) AS requested,
                   SUM(CASE WHEN a.url IS NOT NULL THEN 1 ELSE 0 END) AS acquired,
                   SUM(CASE WHEN a.url IS NULL THEN 1 ELSE 0 END) AS missing,
                   SUM(CASE WHEN a.url IS NULL AND e.record_key IS NOT NULL
                       THEN 1 ELSE 0 END) AS errors
            FROM requests r
            LEFT JOIN acquired a ON a.url = r.url
            LEFT JOIN attempt_errors e ON e.record_key = r.record_key
            {group_by}"""
    )
    if not group:
        requested, acquired, missing, errors = rows.fetchone()
        return {
            "requested": requested,
            "acquired": acquired or 0,
            "missing": missing or 0,
            "errors": errors or 0,
        }
    return {
        key: {"requested": requested, "acquired": acquired, "missing": missing, "errors": errors}
        for key, requested, acquired, missing, errors in rows
    }


def _populate_requests(
    db: sqlite3.Connection, manifests: list[Path]
) -> tuple[list[str], dict[str, int]]:
    stats = {
        "manifest": 0,
        "manifest_without_url": 0,
        "duplicate_manifest_urls": 0,
        "conflicting_duplicate_manifest_metadata": 0,
    }
    retry_fields: list[str] = []
    for path in manifests:
        fields, (stream, reader) = _read_csv(path, MANIFEST_FIELDS)
        retry_fields.extend(field for field in fields if field not in retry_fields)
        with stream, db:
            for raw_row in reader:
                stats["manifest"] += 1
                url = (raw_row.get("filing_url") or "").strip()
                if not url:
                    stats["manifest_without_url"] += 1
                    continue
                row = {key: value or "" for key, value in raw_row.items() if key is not None}
                metadata = (
                    row.get("cik", "").strip(),
                    row.get("form", "").strip(),
                    (row.get("document_type") or "primary").strip(),
                    row.get("filing_date", "").strip(),
                )
                inserted = db.execute(
                    """INSERT OR IGNORE INTO requests
                       (url,cik,form,document_type,filing_date,record_key,row_json)
                       VALUES (?,?,?,?,?,?,?)""",
                    (url, *metadata, _record_key(row), json.dumps(row, sort_keys=True)),
                ).rowcount
                if not inserted:
                    stats["duplicate_manifest_urls"] += 1
                    prior = db.execute(
                        """SELECT cik,form,document_type,filing_date
                           FROM requests WHERE url=?""",
                        (url,),
                    ).fetchone()
                    if tuple(prior) != metadata:
                        stats["conflicting_duplicate_manifest_metadata"] += 1
    return retry_fields, stats


def _populate_inventory(db: sqlite3.Connection, inventory: Path) -> dict[str, int]:
    stats = {"inventory": 0, "inventory_without_url": 0, "duplicate_inventory_urls": 0}
    _fields, (stream, reader) = _read_csv(inventory, ("filing_url",))
    with stream, db:
        for row in reader:
            stats["inventory"] += 1
            url = (row.get("filing_url") or "").strip()
            if not url:
                stats["inventory_without_url"] += 1
                continue
            inserted = db.execute("INSERT OR IGNORE INTO acquired(url) VALUES (?)", (url,)).rowcount
            if not inserted:
                stats["duplicate_inventory_urls"] += 1
    return stats


def _summary_errors(path: Path) -> dict[str, str]:
    errors = json.loads(path.read_text()).get("errors", {})
    if not isinstance(errors, dict):
        raise ValueError(f"{path} has a non-object errors field")
    return {str(key): str(detail) for key, detail in errors.items()}


def _write_retry(db: sqlite3.Connection, retry_manifest: Path, fields: list[str]) -> None:
    retry_manifest.parent.mkdir(parents=True, exist_ok=True)
    with retry_manifest.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for (row_json,) in db.execute(
            """SELECT r.row_json FROM requests r
               LEFT JOIN acquired a ON a.url=r.url
               WHERE a.url IS NULL ORDER BY r.filing_date,r.url"""
        ):
            row = json.loads(row_json)
            writer.writerow({field: row.get(field, "") for field in fields})


def audit_coverage(
    manifests: list[Path],
    inventory: Path,
    *,
    manifest_summaries: list[Path] | None = None,
    acquisition_summaries: list[Path] | None = None,
    retry_manifest: Path | None = None,
) -> dict[str, Any]:
    """Return exact URL coverage; optionally write only unacquired manifest rows."""
    if not manifests:
        raise ValueError("At least one manifest CSV is required")
    if retry_manifest and retry_manifest.exists():
        raise FileExistsError(retry_manifest)
    with tempfile.TemporaryDirectory(prefix="bubble-edgar-coverage-") as temporary:
        db = sqlite3.connect(Path(temporary) / "coverage.sqlite3")
        db.executescript(
            """PRAGMA synchronous=OFF;
            CREATE TABLE requests (
                url TEXT PRIMARY KEY, cik TEXT, form TEXT, document_type TEXT,
                filing_date TEXT, record_key TEXT, row_json TEXT
            );
            CREATE TABLE acquired (url TEXT PRIMARY KEY);
            CREATE TABLE attempt_errors (record_key TEXT PRIMARY KEY, detail TEXT);
            CREATE INDEX requests_record_key ON requests(record_key);"""
        )

        retry_fields, manifest_stats = _populate_requests(db, manifests)
        inventory_stats = _populate_inventory(db, inventory)

        acquisition_errors: list[dict[str, str]] = []
        for path in acquisition_summaries or []:
            errors = _summary_errors(path)
            with db:
                for key, detail in errors.items():
                    acquisition_errors.append({"summary": str(path), "key": key, "error": detail})
                    db.execute(
                        "INSERT OR REPLACE INTO attempt_errors VALUES (?,?)",
                        (str(key), str(detail)),
                    )

        discovery_errors: list[dict[str, str]] = []
        for path in manifest_summaries or []:
            errors = _summary_errors(path)
            discovery_errors.extend(
                {"summary": str(path), "key": str(key), "error": str(detail)}
                for key, detail in errors.items()
            )

        if retry_manifest:
            _write_retry(db, retry_manifest, retry_fields)

        report: dict[str, Any] = {
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "manifests": [str(path) for path in manifests],
            "manifest_summaries": [str(path) for path in manifest_summaries or []],
            "acquisition_summaries": [str(path) for path in acquisition_summaries or []],
            "inventory": str(inventory),
            "coverage_definition": (
                "Acquired means filing_url appears in inventory; local file bytes are not checked. "
                "Missing includes rows with known acquisition errors; errors are a subset of missing. "
                "Manifest discovery errors precede document requests and are reported separately."
            ),
            "total": _counts(db),
            "input_rows": {
                **manifest_stats,
                **inventory_stats,
                "inventory_urls_outside_manifests": db.execute(
                    """SELECT COUNT(*) FROM acquired a LEFT JOIN requests r ON r.url=a.url
                       WHERE r.url IS NULL"""
                ).fetchone()[0],
                "acquisition_error_entries": len(acquisition_errors),
                "acquisition_error_keys_without_request": db.execute(
                    """SELECT COUNT(*) FROM attempt_errors e
                       WHERE NOT EXISTS (
                           SELECT 1 FROM requests r WHERE r.record_key=e.record_key
                       )"""
                ).fetchone()[0],
            },
            "acquisition_errors": acquisition_errors,
            "manifest_discovery_errors": discovery_errors,
            "retry_manifest": str(retry_manifest) if retry_manifest else None,
        }
        report.update({name: _counts(db, column) for name, column in DIMENSIONS.items()})
        db.close()
        return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifests", nargs="+", type=Path)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--manifest-summary", action="append", type=Path, default=[])
    parser.add_argument("--acquisition-summary", action="append", type=Path, default=[])
    parser.add_argument("--retry-manifest", type=Path)
    parser.add_argument("--report-json", type=Path)
    args = parser.parse_args()
    if args.report_json and args.report_json.exists():
        parser.error(f"Report exists: {args.report_json}")
    report = audit_coverage(
        args.manifests,
        args.inventory,
        manifest_summaries=args.manifest_summary,
        acquisition_summaries=args.acquisition_summary,
        retry_manifest=args.retry_manifest,
    )
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        with args.report_json.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write("\n")
    print(
        json.dumps(
            {
                "total": report["total"],
                "input_rows": report["input_rows"],
                "manifest_discovery_error_count": len(report["manifest_discovery_errors"]),
                "report_json": str(args.report_json) if args.report_json else None,
                "retry_manifest": report["retry_manifest"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
