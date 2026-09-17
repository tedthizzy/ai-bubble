"""Verify CT and Hillsborough bulk files and emit source-invariant audit rows.

The ledger contains only batch metadata. It contains no debtor, party, case,
business, or address data from the raw public records.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("data/off_edgar_expansion_2026-09-16")
OUT = ROOT / "provenance_ledger"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def add_record(
    rows: list[dict[str, str]],
    *,
    source_system: str,
    file_path: Path,
    source_uri: str,
    expected_hash: str,
    expected_bytes: int,
    record_count: int,
    retrieved_at: str | None = None,
) -> None:
    if file_path.stat().st_size != expected_bytes:
        raise RuntimeError(f"byte-count mismatch: {file_path}")
    digest = sha256(file_path)
    if digest != expected_hash:
        raise RuntimeError(f"SHA-256 mismatch: {file_path}")
    rows.append(
        {
            "source_system": source_system,
            "source_uri": source_uri,
            "content_hash": digest,
            "retrieved_at": retrieved_at or datetime.fromtimestamp(
                file_path.stat().st_mtime, timezone.utc
            ).isoformat(),
            "local_file": str(file_path),
            "bytes": str(expected_bytes),
            "record_count": str(record_count),
            "grain": "public source file/batch",
        }
    )


def main() -> None:
    rows: list[dict[str, str]] = []
    ct = json.loads((ROOT / "connecticut/acquisition_manifest.json").read_text())
    for record in ct["records"]:
        add_record(
            rows,
            source_system=f"connecticut_{record['dataset']}",
            file_path=Path(record["raw_file"]),
            source_uri=record["export_url"],
            expected_hash=record["sha256"],
            expected_bytes=record["bytes"],
            record_count=record["parsed_rows"],
            retrieved_at=record["acquired_at_utc"],
        )
        if not record["count_matches_source"] or not record["source_stable_during_acquisition"]:
            raise RuntimeError(f"Connecticut API count or snapshot mismatch: {record['dataset']}")

    for dirname, prefix in (
        ("hillsborough_civil", "hillsborough_civil"),
        ("hillsborough_official_records", "hillsborough_official_records"),
    ):
        manifest = json.loads((ROOT / dirname / "acquisition_manifest.json").read_text())
        for record in manifest["files"]:
            add_record(
                rows,
                source_system=f"{prefix}_{record.get('kind', record['file'].split(' File_')[0])}",
                file_path=ROOT / dirname / record["file"],
                source_uri=record["source_url"],
                expected_hash=record["sha256"],
                expected_bytes=record["bytes"],
                record_count=record.get("parsed_records", record.get("parsed_rows")),
            )
            if "eof_declared_records" in record and (
                record["eof_declared_records"] != record["parsed_records"]
            ):
                raise RuntimeError(f"Hillsborough EOF count mismatch: {record['file']}")

    if len(rows) != 141:
        raise RuntimeError(f"expected three CT + 24 civil + 114 official files; got {len(rows)}")
    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / "public_registry_source_batches_2026-09-16.csv"
    if output.exists():
        raise FileExistsError(f"refusing to overwrite source ledger: {output}")
    with output.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"verified {len(rows)} raw source files; ledger: {output}")
    print(f"aggregate source rows: {sum(int(row['record_count']) for row in rows):,}")


if __name__ == "__main__":
    main()
