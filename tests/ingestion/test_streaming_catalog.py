from __future__ import annotations

import csv
import hashlib
import tracemalloc
import zipfile
from typing import TYPE_CHECKING

import pytest

from bubble.ingestion.concurrency import FetchConcurrencyConfig
from bubble.ingestion.sources.catalog import SourceCatalogRow, parse_artifact_rows
from bubble.ingestion.sources.streaming import acquire_streamed_catalog, iter_records
from bubble.models.base import SourceType

if TYPE_CHECKING:
    from pathlib import Path


def catalog_row(path: Path, parser: str = "zip") -> SourceCatalogRow:
    return SourceCatalogRow(
        source_id="stream-test",
        corpus="lei_records",
        source_uri=path.as_uri(),
        source_type=SourceType.COMPANY_IR,
        parser=parser,
        document_id=None,
        entity_id=None,
        project_id=None,
        filing_accession=None,
        metadata={"zip_xml_record_tag": "LEIRecord", "zip_member_name_prefix": "records.xml"},
    )


def archive(path: Path, count: int) -> None:
    with (
        zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as output,
        output.open("records.xml", "w") as stream,
    ):
        stream.write(b'<Root xmlns="urn:test"><Records>')
        for index in range(count):
            extra = "<NewField>retained</NewField>" if index == count - 1 else ""
            stream.write(
                (
                    f"<LEIRecord><LEI>{index}</LEI><Entity><LegalName>Entity {index}</LegalName>"
                    f"{extra}</Entity></LEIRecord>"
                ).encode()
            )
        stream.write(b"</Records></Root>")


def test_streamed_zip_preserves_legacy_fields_and_late_columns(tmp_path: Path) -> None:
    source = tmp_path / "source.zip"
    archive(source, 3)
    row = catalog_row(source)
    catalog = tmp_path / "catalog.csv"
    with catalog.open("w", newline="") as stream:
        record = {
            "source_id": row.source_id,
            "corpus": row.corpus,
            "source_uri": row.source_uri,
            "source_type": row.source_type.value,
            "parser": "zip",
            "meta_zip_xml_record_tag": "LEIRecord",
            "meta_zip_member_name_prefix": "records.xml",
        }
        writer = csv.DictWriter(stream, fieldnames=list(record))
        writer.writeheader()
        writer.writerow(record)
    output = tmp_path / "output"
    result = acquire_streamed_catalog(catalog, output_dir=output, config=FetchConcurrencyConfig())
    assert result["summary"]["extracted_rows"] == 3
    assert result["summary"]["errors"] == {}
    with (output / "source_rows/lei_records.csv").open(newline="") as stream:
        actual = list(csv.DictReader(stream))
    expected = parse_artifact_rows(
        source.read_bytes(),
        row,
        retrieved_at=actual[0]["retrieved_at"],
        content_hash=hashlib.sha256(source.read_bytes()).hexdigest(),
        local_path=source,
    )
    for streamed, legacy in zip(actual, expected, strict=True):
        assert all(streamed[key] == str(value) for key, value in legacy.items())
    assert actual[-1]["Entity_NewField"] == "retained"
    assert actual[0]["Entity_NewField"] == ""


def test_xml_records_do_not_accumulate_in_memory(tmp_path: Path) -> None:
    source = tmp_path / "many-records.zip"
    archive(source, 60_000)
    tracemalloc.start()
    try:
        count = sum(1 for _ in iter_records(source, catalog_row(source)))
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert count == 60_000
    assert peak < 4 * 1024**2


def test_large_buffered_format_is_rejected_before_reading(tmp_path: Path) -> None:
    source = tmp_path / "large.json"
    with source.open("wb") as stream:
        stream.truncate(33 * 1024**2)
    with pytest.raises(ValueError, match="buffered-parser limit"):
        next(iter_records(source, catalog_row(source, parser="json")))
