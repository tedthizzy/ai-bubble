from __future__ import annotations

import csv
import gzip
import hashlib
import json
from pathlib import Path

import pytest
from scripts.audit_edgar_coverage import audit_coverage
from scripts.build_refresh_status import retry_recoveries
from scripts.merge_edgar_acquisitions import merge_acquisitions

from bubble.ingestion.edgar.source_replacements import (
    MANIFEST_NAME,
    verified_source_replacements,
)


@pytest.fixture
def replacement(tmp_path: Path):
    source = tmp_path / "retries/batch/edgar"
    source.mkdir(parents=True)
    accession = "0000000001-26-000001"
    original = (
        "https://www.sec.gov/Archives/edgar/data/1/000000000126000001/xslF345X06/primary_doc.xml"
    )
    actual = f"https://www.sec.gov/Archives/edgar/data/1/{accession}.txt"
    raw = f"<SEC-DOCUMENT>{accession}.txt\n<TYPE>4\n<FILENAME>primary_doc.xml\n<ownershipDocument>issuer</ownershipDocument>".encode()
    path = source / "submission.txt.gz"
    path.write_bytes(gzip.compress(raw))
    record = {
        "filing_url": actual,
        "local_path": str(path),
        "content_hash": hashlib.sha256(raw).hexdigest(),
        "accession_number": accession,
    }
    row = {
        "original_url": original,
        "replacement_url": actual,
        "original_http_status": 404,
        "accession_number": accession,
        "content_hash": record["content_hash"],
        "representation": "sec_complete_submission",
        "identity_markers": [accession, "<ownershipDocument>"],
    }
    (source / MANIFEST_NAME).write_text(json.dumps({"version": 1, "replacements": [row]}))
    with (source / "edgar_document_inventory.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(record))
        writer.writeheader()
        writer.writerow(record)
    for name, fields in [
        ("deals.csv", ["deal_id", "source_uri", "content_hash", "key_terms"]),
        ("tranches.csv", ["deal_id", "tranche_id", "source_uri", "content_hash"]),
    ]:
        (source / name).write_text(",".join(fields) + "\n")
    manifest = tmp_path / "selection.csv"
    manifest.write_text(
        "filing_url,cik,form,document_type,filing_date\n" + original + ",1,4,primary,2026-10-16\n"
    )
    return source, record, row, manifest


def test_verified_copy_retains_actual_retrieval_url_through_merge_and_coverage(replacement):
    source, record, row, manifest = replacement
    output = source.parent.parent.parent / "merged"
    merge_acquisitions([source], output, verify_bytes=True)
    with (output / "edgar_document_inventory.csv").open() as stream:
        assert next(csv.DictReader(stream))["filing_url"] == record["filing_url"]
    report = audit_coverage([manifest], output / "edgar_document_inventory.csv")
    assert report["total"] == {"requested": 1, "acquired": 1, "missing": 0, "errors": 0}
    assert report["direct_url_total"]["missing"] == 1
    assert report["source_document_replacements"] == [row]
    assert "exact original-URL coverage" in report["coverage_definition"]


@pytest.mark.parametrize("failure", ["bytes", "missing", "accession", "markers", "origin"])
def test_replacement_cannot_hide_missing_or_mismatched_source(replacement, failure):
    source, record, row, _ = replacement
    if failure == "bytes":
        Path(record["local_path"]).write_bytes(gzip.compress(b"changed"))
    elif failure == "accession":
        row["accession_number"] = "0000000002-26-000001"
    elif failure == "markers":
        row["identity_markers"] = ["another filing"]
    elif failure == "origin":
        row["representation"] = "unverified third-party summary"
    (source / MANIFEST_NAME).write_text(json.dumps({"version": 1, "replacements": [row]}))
    with pytest.raises(ValueError):
        verified_source_replacements(source, lambda _: None if failure == "missing" else record)


def test_completed_retry_recovers_selected_document_without_claiming_original_http_success(
    replacement,
):
    source, record, row, _ = replacement
    (source.parent / "retry-result.json").write_text("{}")
    recovered, replacements = retry_recoveries(source.parent.parent)
    assert recovered == {record["filing_url"], row["original_url"]}
    assert replacements[0]["original_http_status"] == 404
