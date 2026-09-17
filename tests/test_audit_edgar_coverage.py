from __future__ import annotations

import csv
import json
from typing import TYPE_CHECKING

import pytest
from scripts.audit_edgar_coverage import audit_coverage

if TYPE_CHECKING:
    from pathlib import Path


FIELDS = [
    "cik",
    "company_name",
    "form",
    "accession_number",
    "filing_date",
    "primary_document",
    "document_type",
    "filing_url",
    "relevance_score",
]


def _write_csv(path: Path, rows: list[dict[str, str]], fields: list[str] = FIELDS) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def _row(
    name: str,
    *,
    cik: str = "0001",
    kind: str = "primary",
    form: str = "8-K",
    day: str = "2026-09-01",
) -> dict[str, str]:
    return {
        "cik": cik,
        "company_name": "Example",
        "form": form,
        "accession_number": f"0001-26-{name}",
        "filing_date": day,
        "primary_document": f"{name}.htm",
        "document_type": kind,
        "filing_url": f"https://www.sec.gov/Archives/edgar/data/1/{name}.htm",
        "relevance_score": "100",
    }


def test_reconciles_primary_exhibit_duplicates_errors_and_retry(tmp_path: Path) -> None:
    primary = tmp_path / "primary.csv"
    exhibit = tmp_path / "exhibit.csv"
    inventory = tmp_path / "inventory.csv"
    summary = tmp_path / "manifest.summary.json"
    acquisition = tmp_path / "acquisition.summary.json"
    retry = tmp_path / "retry.csv"
    a = _row("a")
    b = _row("b", kind="exhibit")
    c = _row("c", cik="0002", form="10-Q", day="2026-09-02")
    _write_csv(primary, [a, c])
    _write_csv(exhibit, [a, b])
    _write_csv(inventory, [a, a, _row("outside")], ["filing_url"])
    summary.write_text(json.dumps({"errors": {"0003": "SEC submissions unavailable"}}))
    acquisition.write_text(
        json.dumps({"errors": {"0001:0001-26-b:b.htm": "HTTP 503", "unmatched:key": "HTTP 403"}})
    )
    before = [path.read_bytes() for path in (primary, exhibit, inventory)]

    result = audit_coverage(
        [primary, exhibit],
        inventory,
        manifest_summaries=[summary],
        acquisition_summaries=[acquisition],
        retry_manifest=retry,
    )

    assert result["total"] == {"requested": 3, "acquired": 1, "missing": 2, "errors": 1}
    assert result["by_form"]["8-K"] == {
        "requested": 2,
        "acquired": 1,
        "missing": 1,
        "errors": 1,
    }
    assert result["by_cik"]["0002"]["missing"] == 1
    assert result["by_document_type"]["exhibit"]["errors"] == 1
    assert result["by_filing_date"]["2026-09-02"]["missing"] == 1
    assert result["input_rows"]["duplicate_manifest_urls"] == 1
    assert result["input_rows"]["duplicate_inventory_urls"] == 1
    assert result["input_rows"]["inventory_urls_outside_manifests"] == 1
    assert result["input_rows"]["acquisition_error_keys_without_request"] == 1
    assert len(result["acquisition_errors"]) == 2
    assert result["acquisition_summaries"] == [str(acquisition)]
    assert result["manifest_discovery_errors"] == [
        {"summary": str(summary), "key": "0003", "error": "SEC submissions unavailable"}
    ]
    with retry.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert {row["filing_url"] for row in rows} == {b["filing_url"], c["filing_url"]}
    assert rows[0]["relevance_score"] == "100"
    assert [path.read_bytes() for path in (primary, exhibit, inventory)] == before


def test_invalid_urls_conflicting_metadata_and_existing_output(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    inventory = tmp_path / "inventory.csv"
    retry = tmp_path / "retry.csv"
    row = _row("a")
    conflict = dict(row, form="10-K")
    invalid = dict(row, filing_url="")
    _write_csv(manifest, [row, conflict, invalid])
    _write_csv(inventory, [], ["filing_url"])
    report = audit_coverage([manifest], inventory, retry_manifest=retry)
    assert report["total"]["requested"] == 1
    assert report["input_rows"]["manifest_without_url"] == 1
    assert report["input_rows"]["conflicting_duplicate_manifest_metadata"] == 1
    with pytest.raises(FileExistsError):
        audit_coverage([manifest], inventory, retry_manifest=retry)


def test_requires_url_column(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    inventory = tmp_path / "inventory.csv"
    _write_csv(manifest, [_row("a")])
    _write_csv(inventory, [{"id": "a"}], ["id"])
    with pytest.raises(ValueError, match="filing_url"):
        audit_coverage([manifest], inventory)
