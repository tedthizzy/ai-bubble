#!/usr/bin/env python3
"""Re-extract deal candidates from a saved EDGAR inventory without network I/O.

The source inventory and raw documents remain untouched. A new output directory
contains only corrected deals, tranches, and an input/coverage summary.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

from bubble.ingestion.edgar.document_acquisition import (
    EdgarAcquisitionBatch,
    EdgarAcquisitionSummary,
    extract_deal_candidate,
    normalize_document_text,
)

csv.field_size_limit(10**9)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inventory_rows(inventory_csv: Path) -> list[dict[str, str]]:
    with inventory_csv.open(newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"filing_url", "local_path", "content_hash", "cik", "accession_number"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Inventory missing fields: {required - set(reader.fieldnames or [])}")
        return list(reader)


def _manifest_metadata(
    manifest_csvs: list[Path], inventory_rows: list[dict[str, str]]
) -> tuple[dict[str, dict[str, str]], int]:
    manifest_by_url: dict[str, dict[str, str]] = {}
    duplicate_manifest_urls = 0
    for manifest in manifest_csvs:
        with manifest.open(newline="") as stream:
            reader = csv.DictReader(stream)
            if "filing_url" not in (reader.fieldnames or []):
                raise ValueError(f"Manifest missing filing_url: {manifest}")
            for row in reader:
                url = row["filing_url"]
                prior = manifest_by_url.get(url)
                if prior is not None:
                    if row != prior:
                        raise ValueError(f"Conflicting manifest metadata for {url}")
                    duplicate_manifest_urls += 1
                else:
                    manifest_by_url[url] = row
    if manifest_csvs:
        missing_metadata = [
            row["filing_url"] for row in inventory_rows if row["filing_url"] not in manifest_by_url
        ]
        if missing_metadata:
            raise ValueError(
                f"Inventory has {len(missing_metadata)} documents absent from supplied manifests; "
                f"first: {missing_metadata[0]}"
            )
    return manifest_by_url, duplicate_manifest_urls


def _extract_candidates(
    rows: list[dict[str, str]], manifest_by_url: dict[str, dict[str, str]], progress_interval: int
) -> tuple[list, Counter[str], int]:

    candidates = []
    seen_urls = set()
    forms: Counter[str] = Counter()
    total_bytes = 0
    for index, row in enumerate(rows, start=1):
        url = row["filing_url"]
        if not url or url in seen_urls:
            raise ValueError(f"Missing or duplicate inventory filing URL: {url}")
        seen_urls.add(url)
        path = Path(row["local_path"])
        if not path.is_absolute():
            path = Path.cwd() / path
        stored = path.read_bytes()
        raw = gzip.decompress(stored) if path.suffix == ".gz" else stored
        actual_hash = hashlib.sha256(raw).hexdigest()
        if actual_hash != row["content_hash"]:
            raise ValueError(f"Raw source hash mismatch: {url} at {path}")
        if row.get("byte_count") and len(raw) != int(row["byte_count"]):
            raise ValueError(f"Raw source byte count mismatch: {url} at {path}")
        manifest_row = manifest_by_url.get(url, row)
        candidate = extract_deal_candidate(manifest_row, normalize_document_text(raw), actual_hash, path)
        if candidate is not None:
            candidates.append(candidate)
        total_bytes += len(raw)
        forms[row.get("form", "")] += 1
        if progress_interval and index % progress_interval == 0:
            print(json.dumps({"event": "offline_reextract_progress", "completed": index, "total": len(rows)}), flush=True)
    return candidates, forms, total_bytes


def reextract(
    inventory_csv: Path,
    output_dir: Path,
    *,
    manifest_csvs: list[Path] | None = None,
    progress_interval: int = 1000,
) -> dict:
    if output_dir.exists():
        raise FileExistsError(f"Refusing to replace dated re-extraction: {output_dir}")
    rows = _inventory_rows(inventory_csv)
    manifest_csvs = manifest_csvs or []
    manifest_by_url, duplicate_manifest_urls = _manifest_metadata(manifest_csvs, rows)
    candidates, forms, total_bytes = _extract_candidates(rows, manifest_by_url, progress_interval)

    summary = EdgarAcquisitionSummary(
        manifest_rows=len(rows),
        documents_attempted=len(rows),
        documents_downloaded=len(rows),
        documents_resumed=len(rows),
        deal_candidates=len(candidates),
        tranche_candidates=sum(len(candidate.to_tranche_csv_rows()) for candidate in candidates),
        total_bytes=total_bytes,
        workers=1,
        sec_requests_per_second=0,
        sec_domain_concurrency=0,
        retry_attempts=0,
        resume_enabled=True,
        forms=dict(sorted(forms.items())),
        deal_types=dict(sorted(Counter(candidate.deal_type.value for candidate in candidates).items())),
        errors={},
    )
    output_dir.mkdir(parents=True)
    batch = EdgarAcquisitionBatch(documents=[], deal_candidates=candidates, summary=summary)
    batch.write_deals_csv(output_dir / "deals.csv")
    batch.write_tranches_csv(output_dir / "tranches.csv")
    report = {
        "method": "offline_reextract_current_document_acquisition_parser",
        "source_inventory": {
            "path": str(inventory_csv.resolve()),
            "sha256": _sha256(inventory_csv),
            "rows": len(rows),
        },
        "source_manifests": [
            {"path": str(path.resolve()), "sha256": _sha256(path)} for path in manifest_csvs
        ],
        "manifest_metadata_matched_rows": len(rows) if manifest_csvs else 0,
        "duplicate_manifest_urls": duplicate_manifest_urls,
        "source_documents_verified": len(rows),
        "all_content_hashes_verified": True,
        "no_network_calls": True,
        "summary": summary.to_dict(),
        "outputs": {
            name: {"path": str(path.resolve()), "sha256": _sha256(path)}
            for name, path in (
                ("deals", output_dir / "deals.csv"),
                ("tranches", output_dir / "tranches.csv"),
            )
        },
    }
    (output_dir / "offline_reextraction.summary.json").write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory_csv", type=Path)
    parser.add_argument("--manifest", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--progress-interval", type=int, default=1000)
    args = parser.parse_args()
    print(
        json.dumps(
            reextract(
                args.inventory_csv,
                args.output_dir,
                manifest_csvs=args.manifest,
                progress_interval=args.progress_interval,
            )["summary"],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
