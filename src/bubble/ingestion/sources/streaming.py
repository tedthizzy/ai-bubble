"""File-backed catalog acquisition with incremental normalization and output."""

from __future__ import annotations

import csv
import gzip
import hashlib
import importlib
import json
import os
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from io import TextIOWrapper
from itertools import islice
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote, urlparse

import httpx

from bubble.ingestion.concurrency import (
    DomainFetchLimiter,
    FetchConcurrencyConfig,
    fetch_with_retries,
)
from bubble.ingestion.sources import catalog as legacy
from bubble.paths import resolve_local_path

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def _iter_zip_records(path: Path, row: legacy.SourceCatalogRow) -> Iterator[dict[str, Any]]:
    metadata = row.metadata
    with zipfile.ZipFile(path) as archive:
        for name in legacy._zip_member_names(archive, metadata):
            with archive.open(name) as member:
                if name.lower().endswith(".xml"):
                    tag = str(metadata.get("zip_xml_record_tag", "")).strip()
                    if not tag:
                        raise ValueError("ZIP XML parsing requires meta_zip_xml_record_tag")
                    for number, element in enumerate(legacy._iter_xml_elements(member, tag), 1):
                        yield {
                            "zip_member": name,
                            "source_row_number": number,
                            **legacy._flatten_xml_element(element),
                        }
                else:
                    text = TextIOWrapper(member, encoding="utf-8-sig", errors="ignore", newline="")
                    for number, record in enumerate(csv.DictReader(text), 2):
                        yield {"zip_member": name, "source_row_number": number, **record}


def _iter_xlsx_records(path: Path, row: legacy.SourceCatalogRow) -> Iterator[dict[str, Any]]:
    metadata = row.metadata
    with path.open("rb") as raw:
        workbook = importlib.import_module("openpyxl").load_workbook(
            raw, read_only=True, data_only=True
        )
        try:
            for sheet in workbook.worksheets:
                if not legacy._xlsx_sheet_included(sheet.title, metadata):
                    continue
                number, header, data_rows = legacy._xlsx_header_and_rows(
                    sheet.iter_rows(values_only=True)
                )
                if header is None:
                    continue
                headers = legacy._xlsx_headers(header)
                required = legacy._xlsx_required_value_columns(metadata)
                for index, values in enumerate(data_rows, number + 1):
                    if not any(value not in {None, ""} for value in values):
                        continue
                    record = {"sheet_name": sheet.title, "source_row_number": index}
                    record.update(
                        {
                            headers[i]: value
                            for i, value in enumerate(values[: len(headers)])
                            if value not in {None, ""}
                        }
                    )
                    if not required or legacy._has_required_xlsx_value(record, required):
                        yield record
        finally:
            workbook.close()


def iter_records(path: Path, row: legacy.SourceCatalogRow) -> Iterator[dict[str, Any]]:
    parser = legacy._resolve_parser(row.parser, row.source_uri)
    metadata = row.metadata
    if parser == "zip":
        yield from _iter_zip_records(path, row)
    elif parser == "csv":
        with path.open(encoding="utf-8-sig", errors="replace", newline="") as stream:
            skip = legacy._int_metadata(metadata, "csv_skip_rows")
            yield from csv.DictReader(islice(stream, skip, None))
    elif parser == "xlsx":
        yield from _iter_xlsx_records(path, row)
    else:
        # These existing parsers load their input. Large inputs must gain a
        # streaming parser before being admitted to this path.
        if path.stat().st_size > 32 * 1024**2:
            raise ValueError(f"{parser} artifact exceeds the 32 MiB buffered-parser limit")
        payload = path.read_bytes()
        if parser == "json":
            yield from legacy._parse_json(payload, metadata=metadata)
        elif parser == "xml":
            yield from legacy._parse_xml(payload)
        else:
            yield legacy._text_record(payload)


def download(
    row: legacy.SourceCatalogRow,
    base: Path,
    limiter: DomainFetchLimiter,
    config: FetchConcurrencyConfig,
    resume: bool,
) -> tuple[Path, str, bool]:
    parsed = urlparse(row.source_uri)
    if parsed.scheme in {"", "file", "."}:
        path = resolve_local_path(
            unquote(parsed.path) if parsed.scheme == "file" else row.source_uri
        )
        return path, datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(), True
    path = legacy._artifact_path(base, row)
    if resume and path.exists():
        return path, datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(), True
    if path.exists():
        raise FileExistsError(f"Refusing to replace saved artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    client = legacy.SourceCatalogClient()
    headers = client._headers_for_host(parsed.hostname or "")
    headers.update(legacy._http_headers_from_metadata(row.metadata))
    method = str(row.metadata.get("http_method", "GET")).strip().upper() or "GET"
    body = str(row.metadata.get("http_body", ""))

    def fetch() -> Path:
        with (
            httpx.Client(timeout=60, follow_redirects=True) as http,
            http.stream(
                method, row.source_uri, headers=headers, content=body.encode() if body else None
            ) as response,
        ):
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(
                dir=path.parent, prefix=path.name + ".", suffix=".part", delete=False
            ) as staged:
                for block in response.iter_bytes(1024 * 1024):
                    staged.write(block)
                staged.flush()
                os.fsync(staged.fileno())
            # Exclusive commit: an existing saved source is never replaced.
            os.link(staged.name, path)
            os.unlink(staged.name)
        return path

    fetch_with_retries(
        lambda: limiter.run(row.source_uri, fetch),
        attempts=config.retry_attempts,
        backoff_seconds=config.retry_backoff_seconds,
    )
    return path, datetime.now(UTC).isoformat(), False


def normalize(
    row: legacy.SourceCatalogRow,
    base: Path,
    limiter: DomainFetchLimiter,
    config: FetchConcurrencyConfig,
    resume: bool,
) -> dict[str, Any]:
    path, retrieved, resumed = download(row, base, limiter, config, resume)
    content_hash = digest(path)
    spools = base / "normalized_spools"
    spools.mkdir(exist_ok=True)
    descriptor, spool_name = tempfile.mkstemp(
        dir=spools, prefix=row.source_id + ".", suffix=".jsonl.gz"
    )
    os.close(descriptor)
    fields: set[str] = set()
    count = 0
    with gzip.open(spool_name, "wt") as stream:
        for index, record in enumerate(iter_records(path, row)):
            item = legacy._with_provenance(
                record,
                row,
                retrieved_at=retrieved,
                content_hash=content_hash,
                local_path=path,
                record_index=index,
            )
            fields.update(item)
            stream.write(json.dumps(item, default=str) + "\n")
            count += 1
    artifact = legacy.SourceArtifactRecord(
        source_id=row.source_id,
        corpus=row.corpus,
        source_uri=row.source_uri,
        source_type=row.source_type.value,
        parser=row.parser,
        local_path=str(path),
        retrieved_at=retrieved,
        content_hash=content_hash,
        byte_count=path.stat().st_size,
        extracted_rows=count,
        document_id=row.document_id,
        entity_id=row.entity_id,
        project_id=row.project_id,
        filing_accession=row.filing_accession,
        metadata=row.metadata,
    )
    return {"artifact": artifact, "spool": spool_name, "fields": sorted(fields), "resumed": resumed}


def acquire_streamed_catalog(
    catalog_csv: Path,
    *,
    output_dir: Path,
    config: FetchConcurrencyConfig,
    resume: bool = True,
    limit: int | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "source_catalog_acquisition.summary.json"
    if summary_path.exists() or (output_dir / "source_rows").exists():
        raise FileExistsError(
            "Normalized outputs exist; inspect them or choose a new output directory"
        )
    catalog = legacy.load_source_catalog(catalog_csv)
    selected = catalog[:limit] if limit is not None else catalog
    limiter = DomainFetchLimiter(config)
    results = {}
    errors = {}
    with ThreadPoolExecutor(max_workers=min(4, max(1, config.max_workers))) as executor:
        futures = {
            executor.submit(normalize, row, output_dir, limiter, config, resume): index
            for index, row in enumerate(selected)
        }
        for future in as_completed(futures):
            index = futures[future]
            try:
                results[index] = future.result()
            except Exception as exc:
                errors[selected[index].source_id] = f"{type(exc).__name__}: {exc}"
    ordered = [results[index] for index in sorted(results)]
    inventories = [item["artifact"].to_csv_row() for item in ordered]
    inventory = output_dir / "source_artifact_inventory.csv"
    with inventory.open("x", newline="") as stream:
        fields = sorted({key for item in inventories for key in item})
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(inventories)
    outputs = []
    for corpus in sorted({item["artifact"].corpus for item in ordered}):
        items = [item for item in ordered if item["artifact"].corpus == corpus]
        fields = sorted({key for item in items for key in item["fields"]})
        destination = output_dir / "source_rows" / (corpus + ".csv")
        destination.parent.mkdir(exist_ok=True)
        with destination.open("x", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for item in items:
                with gzip.open(item["spool"], "rt") as source:
                    for line in source:
                        writer.writerow(json.loads(line))
        outputs.append(str(destination))
    summary = {
        "catalog_rows": len(catalog),
        "artifacts_attempted": len(selected),
        "artifacts_acquired": len(ordered),
        "artifacts_resumed": sum(item["resumed"] for item in ordered),
        "extracted_rows": sum(item["artifact"].extracted_rows for item in ordered),
        "workers": min(4, max(1, config.max_workers)),
        "errors": errors,
        "normalization": "file-backed streaming",
    }
    with summary_path.open("x") as stream:
        json.dump(summary, stream, indent=2)
    return {
        "summary": summary,
        "outputs": {
            "inventory_csv": str(inventory),
            "extracted_row_csvs": outputs,
            "summary_json": str(summary_path),
        },
    }
