#!/usr/bin/env python3
"""Combine completed, disjoint EDGAR acquisition batches without moving source files.

The merged inventory keeps each source batch's local_path. Use --verify-bytes to
hash every raw document (gzip is decompressed before hashing) before publishing.
The output directory must be new; no input or output file is overwritten.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bubble.paths import resolve_local_path

TABLES: dict[str, tuple[str, ...]] = {
    "edgar_document_inventory.csv": ("filing_url",),
    "deals.csv": ("deal_id",),
    "tranches.csv": ("deal_id", "tranche_id", "source_uri", "content_hash"),
}
REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "edgar_document_inventory.csv": ("filing_url", "local_path", "content_hash"),
    "deals.csv": ("deal_id", "source_uri", "content_hash", "key_terms"),
    "tranches.csv": ("deal_id", "tranche_id", "source_uri", "content_hash"),
}


@dataclass
class _MergedInputs:
    headers: dict[str, list[str]]
    database: sqlite3.Connection
    duplicate_counts: dict[str, int]
    inputs: list[dict[str, Any]]


def _key(values: tuple[str, ...]) -> str:
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"))


def _sha256(path: Path, *, compressed: bool = False) -> str:
    digest = hashlib.sha256()
    opener = gzip.open if compressed else Path.open
    with opener(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _document_path(recorded: str, source_dir: Path) -> Path:
    path = resolve_local_path(recorded)
    candidates = [path] if path.is_absolute() else [Path.cwd() / path, source_dir / path]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Inventory local_path is missing: {recorded} (source {source_dir})")


def _comparison_row(table: str, row: dict[str, str]) -> dict[str, str]:
    comparable = dict(row)
    if table == "edgar_document_inventory.csv":
        comparable.pop("local_path", None)
        comparable.pop("downloaded_at", None)
    elif table == "deals.csv" and row.get("key_terms"):
        try:
            terms = json.loads(row["key_terms"])
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed deal key_terms JSON for {row.get('deal_id')}") from exc
        if not isinstance(terms, dict):
            raise ValueError(f"Deal key_terms must be an object: {row.get('deal_id')}")
        terms.pop("document_local_path", None)
        comparable["key_terms"] = json.dumps(terms, sort_keys=True)
    return comparable


def _collect_sources(  # noqa: PLR0912 - preserve every input validation in the streaming pass
    sources: list[Path], database: sqlite3.Connection
) -> _MergedInputs:
    headers: dict[str, list[str]] = {}
    duplicate_counts = dict.fromkeys(TABLES, 0)
    inputs: list[dict[str, Any]] = []
    database.executescript("""
        PRAGMA cache_size=-4096;
        PRAGMA temp_store=FILE;
        CREATE TABLE records(table_name TEXT,record_key TEXT,row_json TEXT,
                             comparable TEXT,source_dir TEXT,
                             PRIMARY KEY(table_name,record_key));
        CREATE TABLE inventory_paths(url TEXT,path TEXT,PRIMARY KEY(url,path));
    """)
    for source in sources:
        source_record: dict[str, Any] = {"directory": str(source), "tables": {}}
        for name, key_fields in TABLES.items():
            path = source / name
            if not path.is_file():
                raise FileNotFoundError(f"Missing acquisition table: {path}")
            count = 0
            with path.open(newline="") as stream, database:
                reader = csv.DictReader(stream)
                header = reader.fieldnames
                if header is None or len(header) != len(set(header)):
                    raise ValueError(f"Missing or duplicate CSV columns: {path}")
                missing = set(REQUIRED_COLUMNS[name]) - set(header)
                if missing:
                    raise ValueError(f"{path}: missing required columns {sorted(missing)}")
                if name in headers and header != headers[name]:
                    raise ValueError(f"Incompatible {name} header in {source}")
                headers.setdefault(name, list(header))
                for row in reader:
                    if None in row:
                        raise ValueError(f"{path}: row has more fields than its header")
                    count += 1
                    key = tuple((row.get(field) or "").strip() for field in key_fields)
                    if any(not part for part in key):
                        raise ValueError(f"Blank {name} key in {path}: {key}")
                    if name == "edgar_document_inventory.csv":
                        database.execute(
                            "INSERT OR IGNORE INTO inventory_paths VALUES(?,?)",
                            (key[0], row["local_path"]),
                        )
                    comparable = json.dumps(_comparison_row(name, row), sort_keys=True)
                    previous = database.execute(
                        "SELECT comparable,source_dir FROM records WHERE table_name=? AND record_key=?",
                        (name, _key(key)),
                    ).fetchone()
                    if previous:
                        if previous[0] != comparable:
                            raise ValueError(
                                f"Conflicting duplicate {name} key {key}: {previous[1]} versus {source}"
                            )
                        duplicate_counts[name] += 1
                    else:
                        database.execute(
                            "INSERT INTO records VALUES(?,?,?,?,?)",
                            (
                                name,
                                _key(key),
                                json.dumps(row),
                                comparable,
                                str(source),
                            ),
                        )
            source_record["tables"][name] = {
                "rows": count,
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        inputs.append(source_record)
    return _MergedInputs(headers, database, duplicate_counts, inputs)


def _validate_references(data: _MergedInputs, *, verify_bytes: bool) -> None:
    database = data.database
    for serialized, source in database.execute(
        "SELECT row_json,source_dir FROM records WHERE table_name='edgar_document_inventory.csv'"
    ):
        row = json.loads(serialized)
        local_path = _document_path(row.get("local_path", ""), Path(source))
        if verify_bytes:
            actual = _sha256(local_path, compressed=local_path.suffix == ".gz")
            if actual != row.get("content_hash"):
                raise ValueError(f"Document SHA-256 mismatch for {row['filing_url']}: {local_path}")
    for name in ("deals.csv", "tranches.csv"):
        for serialized, source in database.execute(
            "SELECT row_json,source_dir FROM records WHERE table_name=?", (name,)
        ):
            row = json.loads(serialized)
            url = row.get("source_uri", "")
            stored = database.execute(
                "SELECT row_json FROM records WHERE table_name='edgar_document_inventory.csv' AND record_key=?",
                (_key((url,)),),
            ).fetchone()
            if stored is None:
                raise ValueError(f"{name} has no inventory document: {url}")
            document = json.loads(stored[0])
            if row.get("content_hash") != document.get("content_hash"):
                raise ValueError(f"{name} content hash differs from inventory: {url}")
            if name == "deals.csv" and row.get("key_terms"):
                terms = json.loads(row["key_terms"])
                deal_path = terms.get("document_local_path")
                if (
                    database.execute(
                        "SELECT 1 FROM inventory_paths WHERE url=? AND path=?", (url, deal_path)
                    ).fetchone()
                    is None
                ):
                    raise ValueError(f"Deal source local_path differs from inventory: {url}")
                _document_path(deal_path, Path(source))
            if (
                name == "tranches.csv"
                and database.execute(
                    "SELECT 1 FROM records WHERE table_name='deals.csv' AND record_key=?",
                    (_key((row["deal_id"],)),),
                ).fetchone()
                is None
            ):
                raise ValueError(f"Tranche has no merged deal: {row['deal_id']}")


def merge_acquisitions(
    input_dirs: list[Path], output_dir: Path, *, verify_bytes: bool = False
) -> dict[str, Any]:
    """Merge CSVs by their production keys and publish only to a new directory."""
    if not input_dirs:
        raise ValueError("At least one acquisition directory is required")
    sources = sorted({source.resolve() for source in input_dirs})
    target = output_dir.resolve()
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite output directory: {target}")
    if any(target == source or target.is_relative_to(source) for source in sources):
        raise ValueError("Output directory must be outside every source acquisition directory")
    for source in sources:
        if not source.is_dir():
            raise FileNotFoundError(f"Acquisition directory is missing: {source}")
    # An unnamed SQLite database spills to an OS temporary file and bounds the
    # join's working memory independently of the total acquisition size.
    database = sqlite3.connect("")
    try:
        data = _collect_sources(sources, database)
        _validate_references(data, verify_bytes=verify_bytes)
        report: dict[str, Any] = {
            "inputs": data.inputs,
            "verification": "raw_document_sha256" if verify_bytes else "local_path_exists",
            "counts": {
                name: {
                    "unique_keys": database.execute(
                        "SELECT COUNT(*) FROM records WHERE table_name=?", (name,)
                    ).fetchone()[0],
                    "identical_duplicate_keys": data.duplicate_counts[name],
                    "conflicting_duplicate_keys": 0,
                }
                for name in TABLES
            },
            "source_local_paths_preserved": True,
        }
        target.mkdir(parents=True, exist_ok=False)
        for name in TABLES:
            with (target / name).open("x", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=data.headers[name])
                writer.writeheader()
                for (serialized,) in database.execute(
                    "SELECT row_json FROM records WHERE table_name=? ORDER BY record_key", (name,)
                ):
                    writer.writerow(json.loads(serialized))
        with (target / "merge_manifest.json").open("x") as stream:
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write("\n")
        return report
    finally:
        database.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dirs", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--verify-bytes",
        action="store_true",
        help="Decompress gzip sources when needed and SHA-256-check every document",
    )
    args = parser.parse_args()
    result = merge_acquisitions(args.input_dirs, args.output_dir, verify_bytes=args.verify_bytes)
    print(
        json.dumps(
            {"output_dir": str(args.output_dir.resolve()), **result["counts"]}, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
