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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
Rows = dict[str, dict[tuple[str, ...], dict[str, str]]]


@dataclass
class _MergedInputs:
    headers: dict[str, list[str]]
    rows: Rows
    duplicate_counts: dict[str, int]
    inputs: list[dict[str, Any]]
    source_of: dict[str, dict[tuple[str, ...], Path]]
    inventory_paths: dict[str, set[str]]


def _sha256(path: Path, *, compressed: bool = False) -> str:
    digest = hashlib.sha256()
    opener = gzip.open if compressed else Path.open
    with opener(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _document_path(recorded: str, source_dir: Path) -> Path:
    path = Path(recorded)
    candidates = [path] if path.is_absolute() else [Path.cwd() / path, source_dir / path]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Inventory local_path is missing: {recorded} (source {source_dir})")


def _read_csv(path: Path, required: tuple[str, ...]) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        header = reader.fieldnames
        if header is None or len(header) != len(set(header)):
            raise ValueError(f"Missing or duplicate CSV columns: {path}")
        missing = set(required) - set(header)
        if missing:
            raise ValueError(f"{path}: missing required columns {sorted(missing)}")
        rows = list(reader)
    if any(None in row for row in rows):
        raise ValueError(f"{path}: row has more fields than its header")
    return header, rows


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


def _collect_sources(sources: list[Path]) -> _MergedInputs:
    headers: dict[str, list[str]] = {}
    merged: Rows = {name: {} for name in TABLES}
    duplicate_counts = dict.fromkeys(TABLES, 0)
    inputs: list[dict[str, Any]] = []
    source_of: dict[str, dict[tuple[str, ...], Path]] = {name: {} for name in TABLES}
    inventory_paths: dict[str, set[str]] = {}
    for source in sources:
        source_record: dict[str, Any] = {"directory": str(source), "tables": {}}
        for name, key_fields in TABLES.items():
            path = source / name
            if not path.is_file():
                raise FileNotFoundError(f"Missing acquisition table: {path}")
            header, rows = _read_csv(path, REQUIRED_COLUMNS[name])
            if name in headers and header != headers[name]:
                raise ValueError(f"Incompatible {name} header in {source}")
            headers.setdefault(name, header)
            source_record["tables"][name] = {
                "rows": len(rows),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for row in rows:
                key = tuple((row.get(field) or "").strip() for field in key_fields)
                if any(not part for part in key):
                    raise ValueError(f"Blank {name} key in {path}: {key}")
                if name == "edgar_document_inventory.csv":
                    inventory_paths.setdefault(key[0], set()).add(row["local_path"])
                if key in merged[name]:
                    if _comparison_row(name, merged[name][key]) != _comparison_row(name, row):
                        raise ValueError(
                            f"Conflicting duplicate {name} key {key}: "
                            f"{source_of[name][key]} versus {source}"
                        )
                    duplicate_counts[name] += 1
                else:
                    merged[name][key] = row
                    source_of[name][key] = source
        inputs.append(source_record)
    return _MergedInputs(headers, merged, duplicate_counts, inputs, source_of, inventory_paths)


def _validate_references(data: _MergedInputs, *, verify_bytes: bool) -> None:
    inventory = data.rows["edgar_document_inventory.csv"]
    inventory_by_url = {key[0]: row for key, row in inventory.items()}
    for key, row in inventory.items():
        source = data.source_of["edgar_document_inventory.csv"][key]
        local_path = _document_path(row.get("local_path", ""), source)
        if verify_bytes:
            actual = _sha256(local_path, compressed=local_path.suffix == ".gz")
            if actual != row.get("content_hash"):
                raise ValueError(f"Document SHA-256 mismatch for {key[0]}: {local_path}")
    for name in ("deals.csv", "tranches.csv"):
        for key, row in data.rows[name].items():
            url = row.get("source_uri", "")
            document = inventory_by_url.get(url)
            if document is None:
                raise ValueError(f"{name} has no inventory document: {url}")
            if row.get("content_hash") != document.get("content_hash"):
                raise ValueError(f"{name} content hash differs from inventory: {url}")
            if name == "deals.csv" and row.get("key_terms"):
                terms = json.loads(row["key_terms"])
                deal_path = terms.get("document_local_path")
                if deal_path not in data.inventory_paths[url]:
                    raise ValueError(f"Deal source local_path differs from inventory: {url}")
                _document_path(deal_path, data.source_of[name][key])
    deal_ids = {key[0] for key in data.rows["deals.csv"]}
    for row in data.rows["tranches.csv"].values():
        if row["deal_id"] not in deal_ids:
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
    data = _collect_sources(sources)
    _validate_references(data, verify_bytes=verify_bytes)
    report: dict[str, Any] = {
        "inputs": data.inputs,
        "verification": "raw_document_sha256" if verify_bytes else "local_path_exists",
        "counts": {
            name: {
                "unique_keys": len(rows),
                "identical_duplicate_keys": data.duplicate_counts[name],
                "conflicting_duplicate_keys": 0,
            }
            for name, rows in data.rows.items()
        },
        "source_local_paths_preserved": True,
    }
    target.mkdir(parents=True, exist_ok=False)
    for name, rows in data.rows.items():
        with (target / name).open("x", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=data.headers[name])
            writer.writeheader()
            writer.writerows(rows[key] for key in sorted(rows))
    with (target / "merge_manifest.json").open("x") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return report


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
    result = merge_acquisitions(
        args.input_dirs, args.output_dir, verify_bytes=args.verify_bytes
    )
    print(json.dumps({"output_dir": str(args.output_dir.resolve()), **result["counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
