"""
Generic source catalog acquisition.

A source catalog is a CSV of real source artifacts to acquire. Each row names a
corpus (filings, permits, ppas, leases, queue_records, ownership_records,
tracker_records, extracted_deals, projects, etc.), a source URI, and parser hints.
The acquisition output keeps raw artifacts and normalized extracted rows tied to
source URI, retrieval timestamp, content hash, and document/source ids.
"""

from __future__ import annotations

import csv
import importlib
import json
import os
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from io import BytesIO, TextIOWrapper
from itertools import chain
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import httpx

from bubble.ingestion.concurrency import (
    DomainFetchLimiter,
    FetchConcurrencyConfig,
    fetch_with_retries,
)
from bubble.models.base import Provenance, SourceType
from bubble.quality.source_invariants import assert_source_row

FetchBytes = Callable[[str], bytes]

REQUIRED_CATALOG_COLUMNS = {"source_id", "corpus", "source_uri"}
ALLOWED_CORPORA = {
    "filings",
    "source_documents",
    "projects",
    "queue_records",
    "permit_records",
    "equipment_records",
    "construction_observations",
    "ppas",
    "lease_agreements",
    "ownership_records",
    "tracker_records",
    "extracted_deals",
}
DEFAULT_USER_AGENT = "bubble-forensic-source-acquisition/0.1"
XLSX_HEADER_SCAN_ROWS = 100


@dataclass(frozen=True)
class SourceCatalogRow:
    """One requested real source artifact."""

    source_id: str
    corpus: str
    source_uri: str
    source_type: SourceType
    parser: str
    document_id: str | None
    entity_id: str | None
    project_id: str | None
    filing_accession: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class SourceArtifactRecord:
    """A retrieved raw source artifact."""

    source_id: str
    corpus: str
    source_uri: str
    source_type: str
    parser: str
    local_path: str
    retrieved_at: str
    content_hash: str
    byte_count: int
    extracted_rows: int
    document_id: str | None
    entity_id: str | None
    project_id: str | None
    filing_accession: str | None
    metadata: dict[str, Any]

    def to_csv_row(self) -> dict[str, Any]:
        row = asdict(self)
        row["metadata"] = json.dumps(self.metadata, sort_keys=True)
        return row


@dataclass(frozen=True)
class CatalogAcquisitionSummary:
    catalog_rows: int
    artifacts_attempted: int
    artifacts_acquired: int
    artifacts_resumed: int
    extracted_rows: int
    workers: int
    sec_requests_per_second: float
    sec_domain_concurrency: int
    other_requests_per_second: float
    other_domain_concurrency: int
    retry_attempts: int
    resume_enabled: bool
    corpora: dict[str, int]
    errors: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CatalogAcquisitionBatch:
    artifacts: list[SourceArtifactRecord]
    rows_by_corpus: dict[str, list[dict[str, Any]]]
    summary: CatalogAcquisitionSummary

    def write_inventory_csv(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "source_id",
            "corpus",
            "source_uri",
            "source_type",
            "parser",
            "local_path",
            "retrieved_at",
            "content_hash",
            "byte_count",
            "extracted_rows",
            "document_id",
            "entity_id",
            "project_id",
            "filing_accession",
            "metadata",
        ]
        with output.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(artifact.to_csv_row() for artifact in self.artifacts)
        return output

    def write_extracted_rows(self, output_dir: str | Path) -> list[Path]:
        base = Path(output_dir) / "source_rows"
        base.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for corpus, rows in sorted(self.rows_by_corpus.items()):
            if not rows:
                continue
            output = base / f"{corpus}.csv"
            fieldnames = list(dict.fromkeys(key for row in rows for key in row))
            with output.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            written.append(output)
        return written

    def write_summary_json(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(self.summary.to_dict(), indent=2, sort_keys=True))
        return output

    def write_outputs(self, output_dir: str | Path) -> dict[str, Any]:
        base = Path(output_dir)
        inventory = self.write_inventory_csv(base / "source_artifact_inventory.csv")
        row_paths = self.write_extracted_rows(base)
        summary = self.write_summary_json(base / "source_catalog_acquisition.summary.json")
        return {
            "inventory_csv": str(inventory),
            "extracted_row_csvs": [str(path) for path in row_paths],
            "summary_json": str(summary),
        }


@dataclass(frozen=True)
class _CatalogArtifactResult:
    index: int
    artifact: SourceArtifactRecord | None
    rows: list[dict[str, Any]]
    resumed: bool
    error_key: str | None
    error: str | None


class SourceCatalogClient:
    """HTTP/file source fetcher."""

    def __init__(self, *, timeout_seconds: float = 45.0, identity: str | None = None) -> None:
        self.timeout_seconds = timeout_seconds
        self.identity = identity or os.getenv("EDGAR_IDENTITY")

    def fetch_bytes(self, source_uri: str) -> bytes:
        parsed = urlparse(source_uri)
        if parsed.scheme == "file":
            return Path(unquote(parsed.path)).read_bytes()
        if parsed.scheme in {"", "."}:
            return Path(source_uri).read_bytes()
        headers = self._headers_for_host(parsed.hostname or "")
        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
            response = client.get(source_uri, headers=headers)
            response.raise_for_status()
            return bytes(response.content)

    def fetch_catalog_row(self, catalog_row: SourceCatalogRow) -> bytes:
        """Fetch a catalog row, including row-specific HTTP method/header hints."""

        source_uri = catalog_row.source_uri
        parsed = urlparse(source_uri)
        if parsed.scheme == "file":
            return Path(unquote(parsed.path)).read_bytes()
        if parsed.scheme in {"", "."}:
            return Path(source_uri).read_bytes()

        headers = self._headers_for_host(parsed.hostname or "")
        headers.update(_http_headers_from_metadata(catalog_row.metadata))
        method = str(catalog_row.metadata.get("http_method", "GET")).strip().upper() or "GET"
        body = str(catalog_row.metadata.get("http_body", ""))
        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
            response = client.request(
                method,
                source_uri,
                headers=headers,
                content=body.encode("utf-8") if body else None,
            )
            response.raise_for_status()
            return bytes(response.content)

    def _headers_for_host(self, hostname: str) -> dict[str, str]:
        if hostname == "sec.gov" or hostname.endswith(".sec.gov"):
            if not self.identity:
                raise ValueError(
                    "SEC source acquisition requires EDGAR_IDENTITY, "
                    "for example 'Name email@example.com'."
                )
            return {"User-Agent": self.identity}
        return {"User-Agent": DEFAULT_USER_AGENT}


def acquire_source_catalog(
    catalog_csv: str | Path,
    *,
    output_dir: str | Path,
    fetch_bytes: FetchBytes | None = None,
    limit: int | None = None,
    max_workers: int = 64,
    sec_requests_per_second: float = 8.0,
    sec_domain_concurrency: int = 8,
    other_requests_per_second: float = 16.0,
    other_domain_concurrency: int = 16,
    retry_attempts: int = 3,
    retry_backoff_seconds: float = 0.5,
    resume: bool = True,
    write_outputs: bool = True,
) -> CatalogAcquisitionBatch:
    """Acquire every artifact in a source catalog and normalize extracted rows."""

    catalog_rows = load_source_catalog(catalog_csv)
    selected_rows = catalog_rows[:limit] if limit is not None else catalog_rows
    source_client = SourceCatalogClient()
    fetcher = fetch_bytes
    output_base = Path(output_dir)
    rows_by_corpus: dict[str, list[dict[str, Any]]] = {corpus: [] for corpus in ALLOWED_CORPORA}
    limiter = DomainFetchLimiter(
        FetchConcurrencyConfig(
            max_workers=max_workers,
            sec_domain_concurrency=sec_domain_concurrency,
            other_domain_concurrency=other_domain_concurrency,
            sec_requests_per_second=sec_requests_per_second,
            other_requests_per_second=other_requests_per_second,
            retry_attempts=retry_attempts,
            retry_backoff_seconds=retry_backoff_seconds,
        )
    )
    worker_count = min(max(1, max_workers), max(1, len(selected_rows)))
    results: list[_CatalogArtifactResult] = []
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(
                _acquire_catalog_row,
                index,
                catalog_row,
                output_base,
                fetcher,
                source_client,
                limiter,
                retry_attempts,
                retry_backoff_seconds,
                resume,
            )
            for index, catalog_row in enumerate(selected_rows)
        ]
        results = [future.result() for future in as_completed(futures)]

    results.sort(key=lambda result: result.index)
    artifacts = [result.artifact for result in results if result.artifact is not None]
    errors = {
        str(result.error_key): str(result.error)
        for result in results
        if result.error_key and result.error
    }
    for result in results:
        if result.artifact is not None:
            rows_by_corpus[result.artifact.corpus].extend(result.rows)

    summary = CatalogAcquisitionSummary(
        catalog_rows=len(catalog_rows),
        artifacts_attempted=len(selected_rows),
        artifacts_acquired=len(artifacts),
        artifacts_resumed=sum(result.resumed for result in results),
        extracted_rows=sum(artifact.extracted_rows for artifact in artifacts),
        workers=worker_count,
        sec_requests_per_second=sec_requests_per_second,
        sec_domain_concurrency=sec_domain_concurrency,
        other_requests_per_second=other_requests_per_second,
        other_domain_concurrency=other_domain_concurrency,
        retry_attempts=retry_attempts,
        resume_enabled=resume,
        corpora=dict(sorted(Counter(artifact.corpus for artifact in artifacts).items())),
        errors=errors,
    )
    batch = CatalogAcquisitionBatch(
        artifacts=artifacts,
        rows_by_corpus=rows_by_corpus,
        summary=summary,
    )
    if write_outputs:
        batch.write_outputs(output_base)
    return batch


def _acquire_catalog_row(
    index: int,
    catalog_row: SourceCatalogRow,
    output_base: Path,
    fetcher: FetchBytes | None,
    source_client: SourceCatalogClient,
    limiter: DomainFetchLimiter,
    retry_attempts: int,
    retry_backoff_seconds: float,
    resume: bool,
) -> _CatalogArtifactResult:
    try:
        local_path = _artifact_path(output_base, catalog_row)
        resumed = resume and local_path.exists()
        if resumed:
            raw = local_path.read_bytes()
            retrieved_at = datetime.fromtimestamp(local_path.stat().st_mtime, UTC).isoformat()
        else:
            raw = fetch_with_retries(
                lambda: limiter.run(
                    catalog_row.source_uri,
                    lambda: (
                        fetcher(catalog_row.source_uri)
                        if fetcher is not None
                        else source_client.fetch_catalog_row(catalog_row)
                    ),
                ),
                attempts=retry_attempts,
                backoff_seconds=retry_backoff_seconds,
            )
            retrieved_at = datetime.now(UTC).isoformat()
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(raw)

        content_hash = Provenance.compute_content_hash(raw)
        extracted = parse_artifact_rows(
            raw,
            catalog_row,
            retrieved_at=retrieved_at,
            content_hash=content_hash,
            local_path=local_path,
        )
        return _CatalogArtifactResult(
            index=index,
            artifact=SourceArtifactRecord(
                source_id=catalog_row.source_id,
                corpus=catalog_row.corpus,
                source_uri=catalog_row.source_uri,
                source_type=catalog_row.source_type.value,
                parser=catalog_row.parser,
                local_path=str(local_path),
                retrieved_at=retrieved_at,
                content_hash=content_hash,
                byte_count=len(raw),
                extracted_rows=len(extracted),
                document_id=catalog_row.document_id,
                entity_id=catalog_row.entity_id,
                project_id=catalog_row.project_id,
                filing_accession=catalog_row.filing_accession,
                metadata=catalog_row.metadata,
            ),
            rows=extracted,
            resumed=resumed,
            error_key=None,
            error=None,
        )
    except Exception as exc:  # pragma: no cover - exact network/filesystem failures vary
        return _CatalogArtifactResult(
            index=index,
            artifact=None,
            rows=[],
            resumed=False,
            error_key=catalog_row.source_id,
            error=str(exc),
        )


def load_source_catalog(catalog_csv: str | Path) -> list[SourceCatalogRow]:
    with Path(catalog_csv).open(newline="") as f:
        rows = [
            {key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(f)
        ]
    missing = REQUIRED_CATALOG_COLUMNS - set(rows[0]) if rows else set()
    if missing:
        raise ValueError(f"Source catalog missing required columns: {sorted(missing)}")
    return [_catalog_row_from_csv(row) for row in rows]


def parse_artifact_rows(
    raw: bytes,
    catalog_row: SourceCatalogRow,
    *,
    retrieved_at: str,
    content_hash: str,
    local_path: Path,
) -> list[dict[str, Any]]:
    parser = _resolve_parser(catalog_row.parser, catalog_row.source_uri)
    if parser == "csv":
        records = _parse_csv(raw, metadata=catalog_row.metadata)
    elif parser == "json":
        records = _parse_json(raw, metadata=catalog_row.metadata)
    elif parser == "xml":
        records = _parse_xml(raw)
    elif parser == "zip":
        records = _parse_zip(raw, metadata=catalog_row.metadata)
    elif parser == "xlsx":
        records = _parse_xlsx(raw, metadata=catalog_row.metadata)
    else:
        records = [_text_record(raw)]
    return [
        _with_provenance(
            record,
            catalog_row,
            retrieved_at=retrieved_at,
            content_hash=content_hash,
            local_path=local_path,
            record_index=index,
        )
        for index, record in enumerate(records)
    ]


def _catalog_row_from_csv(row: dict[str, str]) -> SourceCatalogRow:
    assert_source_row(row, context=f"source_catalog:{row.get('source_id', 'unknown')}")
    source_type = _source_type(row.get("source_type"))
    corpus = row["corpus"].strip().lower()
    if corpus not in ALLOWED_CORPORA:
        raise ValueError(f"Unsupported source corpus '{corpus}' for {row['source_id']}")
    metadata = {
        key.removeprefix("meta_"): value
        for key, value in row.items()
        if key.startswith("meta_") and value
    }
    return SourceCatalogRow(
        source_id=row["source_id"],
        corpus=corpus,
        source_uri=row["source_uri"],
        source_type=source_type,
        parser=(row.get("parser") or "auto").lower(),
        document_id=row.get("document_id") or None,
        entity_id=row.get("entity_id") or None,
        project_id=row.get("project_id") or None,
        filing_accession=row.get("filing_accession") or None,
        metadata=metadata,
    )


def _source_type(value: str | None) -> SourceType:
    if not value:
        return SourceType.MANUAL_CURATED
    try:
        return SourceType(value.strip().lower())
    except ValueError as exc:
        raise ValueError(f"Unsupported source_type: {value}") from exc


def _resolve_parser(parser: str, source_uri: str) -> str:
    if parser != "auto":
        return parser
    suffix = Path(urlparse(source_uri).path).suffix.lower()
    return {
        ".csv": "csv",
        ".json": "json",
        ".xml": "xml",
        ".zip": "zip",
        ".xlsx": "xlsx",
    }.get(suffix, "text")


def _parse_csv(raw: bytes, *, metadata: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    text = _decode(raw)
    lines = text.splitlines()
    skip_rows = _int_metadata(metadata or {}, "csv_skip_rows")
    return [dict(row) for row in csv.DictReader(lines[skip_rows:])]


def _parse_json(
    raw: bytes,
    *,
    metadata: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    parsed = json.loads(_decode(raw))
    flatten_records = _bool_metadata(metadata or {}, "json_flatten_records")
    records_path = str((metadata or {}).get("json_records_path", "")).strip()
    if records_path:
        parsed = _json_path(parsed, records_path)
    if isinstance(parsed, list):
        return [_json_record(item, flatten=flatten_records) for item in parsed]
    if isinstance(parsed, dict):
        for value in parsed.values():
            if isinstance(value, list) and all(isinstance(item, dict) for item in value):
                return [_json_record(item, flatten=flatten_records) for item in value]
        return [_json_record(parsed, flatten=flatten_records)]
    return [{"value": parsed}]


def _json_path(value: Any, path: str) -> Any:
    selected = value
    for part in path.split("."):
        key = part.strip()
        if not key:
            continue
        if isinstance(selected, Mapping):
            selected = selected[key]
        elif isinstance(selected, list):
            selected = selected[int(key)]
        else:
            raise ValueError(f"Cannot resolve JSON records path '{path}'")
    return selected


def _json_record(value: Any, *, flatten: bool = False) -> dict[str, Any]:
    if isinstance(value, Mapping):
        if flatten:
            flattened: dict[str, Any] = {}
            _flatten_json_mapping(value, flattened)
            return {str(key): _cell(cell) for key, cell in flattened.items()}
        return {str(key): _cell(cell) for key, cell in value.items()}
    return {"value": _cell(value)}


def _flatten_json_mapping(
    value: Mapping[str, Any],
    flattened: dict[str, Any],
    *,
    prefix: str = "",
) -> None:
    for key, cell in value.items():
        normalized_key = str(key)
        if normalized_key == "attributes" and isinstance(cell, Mapping):
            _flatten_json_mapping(cell, flattened)
        elif isinstance(cell, Mapping):
            child_prefix = f"{prefix}{normalized_key}_" if prefix else f"{normalized_key}_"
            _flatten_json_mapping(cell, flattened, prefix=child_prefix)
        else:
            flattened[f"{prefix}{normalized_key}"] = cell


def _parse_xml(raw: bytes) -> list[dict[str, Any]]:
    root = ET.fromstring(raw)
    children = [child for child in list(root) if isinstance(child.tag, str)]
    if children:
        return [_xml_record(child) for child in children]
    return [_xml_record(root)]


def _xml_record(element: ET.Element) -> dict[str, Any]:
    record: dict[str, Any] = {}
    child_counts: Counter[str] = Counter(_xml_tag(child) for child in list(element))
    for child in list(element):
        if not isinstance(child.tag, str):
            continue
        key = _xml_tag(child)
        value = _xml_value(child)
        if child_counts[key] > 1:
            existing = record.get(key)
            if existing:
                record[key] = f"{existing}|{value}"
            else:
                record[key] = value
        else:
            record[key] = value
    if record:
        return record
    return {_xml_tag(element): _xml_value(element)}


def _xml_value(element: ET.Element) -> str:
    if list(element):
        return json.dumps(_xml_record(element), sort_keys=True)
    return (element.text or "").strip()


def _xml_tag(element: ET.Element) -> str:
    return str(element.tag).rsplit("}", 1)[-1]


def _parse_zip(raw: bytes, *, metadata: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with zipfile.ZipFile(BytesIO(raw)) as archive:
        for member_name in _zip_member_names(archive, metadata or {}):
            with archive.open(member_name) as member_file:
                if member_name.lower().endswith(".xml"):
                    records.extend(
                        _parse_zip_xml_member(
                            member_file,
                            member_name=member_name,
                            metadata=metadata or {},
                        )
                    )
                else:
                    text = TextIOWrapper(
                        member_file,
                        encoding="utf-8-sig",
                        errors="ignore",
                        newline="",
                    )
                    reader = csv.DictReader(text)
                    for source_row_number, row in enumerate(reader, start=2):
                        record = {
                            "zip_member": member_name,
                            "source_row_number": source_row_number,
                        }
                        record.update(dict(row))
                        records.append(record)
    return records


def _parse_zip_xml_member(
    member_file: Any,
    *,
    member_name: str,
    metadata: Mapping[str, Any],
) -> list[dict[str, Any]]:
    record_tag = str(metadata.get("zip_xml_record_tag", "")).strip()
    if not record_tag:
        raise ValueError("ZIP XML parsing requires meta_zip_xml_record_tag")

    records: list[dict[str, Any]] = []
    for source_row_number, element in enumerate(
        _iter_xml_elements(member_file, record_tag),
        start=1,
    ):
        record = {
            "zip_member": member_name,
            "source_row_number": source_row_number,
        }
        record.update(_flatten_xml_element(element))
        records.append(record)
        element.clear()
    return records


def _iter_xml_elements(source: Any, record_tag: str) -> Any:
    for _event, element in ET.iterparse(source, events=("end",)):
        if _xml_tag(element) == record_tag:
            yield element


def _flatten_xml_element(element: ET.Element) -> dict[str, str]:
    fields: dict[str, str] = {}
    _flatten_xml_children(element, parent="", fields=fields)
    return fields


def _flatten_xml_children(element: ET.Element, *, parent: str, fields: dict[str, str]) -> None:
    children = [child for child in list(element) if isinstance(child.tag, str)]
    if not children:
        _merge_flat_xml_field(fields, parent or _xml_tag(element), (element.text or "").strip())
        return
    for child in children:
        tag = _xml_tag(child)
        path = f"{parent}_{tag}" if parent else tag
        _flatten_xml_children(child, parent=path, fields=fields)


def _merge_flat_xml_field(fields: dict[str, str], key: str, value: str) -> None:
    if not value:
        return
    existing = fields.get(key)
    if existing:
        fields[key] = f"{existing}|{value}"
    else:
        fields[key] = value


def _zip_member_names(
    archive: zipfile.ZipFile,
    metadata: Mapping[str, Any],
) -> list[str]:
    selected_names = _split_metadata(metadata, "zip_member_names")
    archive_names = [name for name in archive.namelist() if not name.endswith("/")]
    if selected_names:
        available = set(archive_names)
        missing = [name for name in selected_names if name not in available]
        if missing:
            raise ValueError(f"ZIP artifact missing requested members: {missing}")
        return selected_names

    prefix = str(metadata.get("zip_member_name_prefix", "")).strip()
    if prefix:
        return [name for name in archive_names if name.startswith(prefix)]
    return [name for name in archive_names if name.lower().endswith(".csv")]


def _int_metadata(metadata: Mapping[str, Any], key: str) -> int:
    value = metadata.get(key)
    if value in {None, ""}:
        return 0
    try:
        return max(0, int(str(value)))
    except ValueError:
        return 0


def _bool_metadata(metadata: Mapping[str, Any], key: str) -> bool:
    return str(metadata.get(key, "")).strip().lower() in {"1", "true", "yes", "y"}


def _split_metadata(metadata: Mapping[str, Any], key: str) -> list[str]:
    value = str(metadata.get(key, "")).strip()
    if not value:
        return []
    return [name.strip() for name in value.replace(";", "|").split("|") if name.strip()]


def _parse_xlsx(raw: bytes, *, metadata: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    load_workbook = importlib.import_module("openpyxl").load_workbook
    workbook = load_workbook(BytesIO(raw), read_only=True, data_only=True)
    records: list[dict[str, Any]] = []
    try:
        for sheet in workbook.worksheets:
            if not _xlsx_sheet_included(sheet.title, metadata or {}):
                continue
            row_iter = sheet.iter_rows(values_only=True)
            header_row_number, header, data_rows = _xlsx_header_and_rows(row_iter)
            if header is None:
                continue
            headers = _xlsx_headers(header)
            required_value_columns = _xlsx_required_value_columns(metadata or {})
            for row_number, row in enumerate(data_rows, start=header_row_number + 1):
                if not any(cell not in {None, ""} for cell in row):
                    continue
                record = {
                    "sheet_name": sheet.title,
                    "source_row_number": row_number,
                }
                record.update(
                    {
                        headers[index]: value
                        for index, value in enumerate(row[: len(headers)])
                        if value not in {None, ""}
                    }
                )
                if required_value_columns and not _has_required_xlsx_value(
                    record, required_value_columns
                ):
                    continue
                records.append(record)
    finally:
        workbook.close()
    return records


def _xlsx_header_and_rows(row_iter: Any) -> tuple[int, tuple[Any, ...] | None, Any]:
    preview: list[tuple[Any, ...]] = []
    for _ in range(XLSX_HEADER_SCAN_ROWS):
        try:
            preview.append(tuple(next(row_iter)))
        except StopIteration:
            break
    if not preview:
        return 0, None, []

    header_index = max(range(len(preview)), key=lambda index: _non_empty_count(preview[index]))
    if _non_empty_count(preview[header_index]) == 0:
        return 0, None, []
    return (
        header_index + 1,
        preview[header_index],
        chain(preview[header_index + 1 :], row_iter),
    )


def _xlsx_sheet_included(sheet_name: str, metadata: Mapping[str, Any]) -> bool:
    names_value = str(metadata.get("xlsx_sheet_names", "")).strip()
    if names_value:
        names = {name.strip() for name in names_value.replace(";", "|").split("|") if name.strip()}
        return sheet_name in names

    prefix = str(metadata.get("xlsx_sheet_name_prefix", "")).strip()
    return not prefix or sheet_name.startswith(prefix)


def _xlsx_required_value_columns(metadata: Mapping[str, Any]) -> list[str]:
    return _split_metadata(metadata, "xlsx_required_value_columns")


def _has_required_xlsx_value(record: Mapping[str, Any], required_columns: list[str]) -> bool:
    return any(str(record.get(column, "")).strip() for column in required_columns)


def _non_empty_count(row: tuple[Any, ...]) -> int:
    return sum(cell not in {None, ""} for cell in row)


def _xlsx_headers(row: tuple[Any, ...]) -> list[str]:
    seen: Counter[str] = Counter()
    headers: list[str] = []
    for index, value in enumerate(row, start=1):
        base = str(value).strip() if value not in {None, ""} else f"column_{index}"
        base = " ".join(base.split())
        seen[base] += 1
        headers.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
    return headers


def _text_record(raw: bytes) -> dict[str, Any]:
    text = _decode(raw)
    return {"text": text[:250_000], "text_char_count": len(text)}


def _with_provenance(
    record: dict[str, Any],
    catalog_row: SourceCatalogRow,
    *,
    retrieved_at: str,
    content_hash: str,
    local_path: Path,
    record_index: int,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        key: _cell(value)
        for key, value in record.items()
        if key
        not in {
            "source_id",
            "source_uri",
            "source_type",
            "retrieved_at",
            "content_hash",
            "local_path",
            "record_index",
            "metadata",
        }
    }
    row.update(
        {
            "source_id": catalog_row.source_id,
            "source_uri": catalog_row.source_uri,
            "source_type": catalog_row.source_type.value,
            "retrieved_at": retrieved_at,
            "content_hash": content_hash,
            "local_path": str(local_path),
            "record_index": record_index,
            "metadata": json.dumps(catalog_row.metadata, sort_keys=True),
        }
    )
    for key, value in {
        "document_id": catalog_row.document_id or "",
        "entity_id": catalog_row.entity_id or "",
        "project_id": catalog_row.project_id or "",
        "filing_accession": catalog_row.filing_accession or "",
    }.items():
        _add_catalog_identifier(row, key, value)
    return row


def _add_catalog_identifier(row: dict[str, Any], key: str, value: str) -> None:
    if key not in row:
        row[key] = value
    elif value:
        row[f"catalog_{key}"] = value


def _artifact_path(output_dir: Path, row: SourceCatalogRow) -> Path:
    suffix = _artifact_suffix(row)
    safe_source_id = "".join(
        ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in row.source_id
    )
    return output_dir / "raw" / row.corpus / f"{safe_source_id}{suffix}"


def _artifact_suffix(row: SourceCatalogRow) -> str:
    explicit = str(row.metadata.get("file_extension", "")).strip().lstrip(".")
    if explicit:
        return f".{explicit}"
    return Path(urlparse(row.source_uri).path).suffix or ".bin"


def _http_headers_from_metadata(metadata: Mapping[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in metadata.items():
        if not key.startswith("http_header_"):
            continue
        header_name = key.removeprefix("http_header_").replace("_", "-")
        if header_name and str(value).strip():
            headers[header_name] = str(value).strip()
    return headers


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", errors="ignore")


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, int | float | bool):
        return str(value)
    return json.dumps(value, sort_keys=True)
