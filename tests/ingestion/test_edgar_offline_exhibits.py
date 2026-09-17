from __future__ import annotations

import gzip
from datetime import date
from typing import TYPE_CHECKING

from bubble.ingestion.edgar.filing_manifest import build_edgar_filing_manifest
from bubble.ingestion.edgar.offline_exhibits import (
    discover_exhibit_links,
    discover_offline_exhibits,
)

if TYPE_CHECKING:
    from pathlib import Path


FILING_URL = "https://www.sec.gov/Archives/edgar/data/123/000000012326000002/report.htm"


def test_offline_links_only_accept_same_accession_text_exhibits():
    html = b"""<html><body><h1>Exhibit Index</h1>
    <a href="ex10-credit.htm">10.1</a>
    <a href="ex10-credit.htm">Credit agreement</a>
    <a href="financial.htm">Exhibit 99.1</a>
    <a href="ex4-indent.htm">Indenture</a>
    <a href="ex21-subsidiaries.htm">21.1</a>
    <a href="guarantor-list.htm">Exhibit 22.1</a>
    <a href="d123dex211.htm">Subsidiary schedule</a>
    <a href="d123dex221.htm">Guarantor schedule</a>
    <a href="ex101.xml">XBRL</a>
    <a href="ex10-pdf.pdf">10.2</a>
    <a href="https://www.sec.gov/Archives/edgar/data/123/old/ex10-old.htm">10.3</a>
    <a href="https://example.com/ex10-fake.htm">10.4</a>
    <a href="#incorporated">10.5</a>
    <a href="xbrl_calc.htm">99.2</a>
    </body></html>"""
    assert discover_exhibit_links(html, FILING_URL) == [
        ("d123dex211.htm", "21"),
        ("d123dex221.htm", "22"),
        ("ex10-credit.htm", "10"),
        ("ex21-subsidiaries.htm", "21"),
        ("ex4-indent.htm", "4"),
        ("financial.htm", "99"),
        ("guarantor-list.htm", "22"),
    ]


def test_offline_manifest_preserves_parent_and_explicit_coverage_limits(tmp_path: Path):
    def submission(_url: str) -> dict[str, object]:
        return {
            "name": "Example AI Infra",
            "tickers": ["AIDC"],
            "filings": {
                "recent": {
                    "accessionNumber": ["0000000123-26-000002", "0000000123-26-000003"],
                    "filingDate": ["2026-09-15", "2026-09-16"],
                    "reportDate": ["2026-09-15", "2026-09-16"],
                    "acceptanceDateTime": ["2026-09-15T20:00:00Z", "2026-09-16T20:00:00Z"],
                    "form": ["8-K", "8-K"],
                    "items": ["1.01 9.01", "1.01 9.01"],
                    "size": [100, 100],
                    "isXBRL": [0, 0],
                    "isInlineXBRL": [0, 0],
                    "primaryDocument": ["report.htm", "missing.htm"],
                    "primaryDocDescription": ["Credit agreement", "Other report"],
                }
            },
        }

    source = build_edgar_filing_manifest(["123"], fetch_json=submission, since=date(2026, 9, 1))
    manifest_csv = source.write_csv(tmp_path / "primary.csv")
    documents = tmp_path / "documents"
    local = documents / "0000000123" / "000000012326000002" / "report.htm"
    local.parent.mkdir(parents=True)
    local.write_text('<a href="agreement.htm">Exhibit 10.1</a>')

    result = discover_offline_exhibits(manifest_csv, documents)
    assert result.coverage["selected_parent_filings"] == 2
    assert result.coverage["parsed_parent_filings"] == 1
    assert result.coverage["missing_local_parent_filings"] == 1
    assert result.coverage["discovered_exhibit_rows"] == 1
    exhibit = result.manifest.records[0]
    assert exhibit.primary_document == "agreement.htm"
    assert exhibit.parent_primary_document == "report.htm"
    assert exhibit.source_uri == FILING_URL
    assert exhibit.filing_url == FILING_URL.replace("report.htm", "agreement.htm")
    assert exhibit.size_bytes is None
    assert exhibit.provenance.confidence == 0.85
    assert "exhibit:10:material contract exhibit" in exhibit.relevance_reasons
    assert result.manifest.summary.sec_requests_per_second == 0


def test_offline_manifest_reads_gzip_parent_and_scores_21_22(tmp_path: Path):
    def submission(_url: str) -> dict[str, object]:
        return {
            "name": "Example AI Infra",
            "filings": {
                "recent": {
                    "accessionNumber": ["0000000123-26-000002"],
                    "filingDate": ["2026-09-15"],
                    "reportDate": ["2026-09-15"],
                    "acceptanceDateTime": ["2026-09-15T20:00:00Z"],
                    "form": ["10-Q"],
                    "items": [""],
                    "size": [100],
                    "isXBRL": [0],
                    "isInlineXBRL": [0],
                    "primaryDocument": ["report.htm"],
                    "primaryDocDescription": ["Quarterly report"],
                }
            },
        }

    source = build_edgar_filing_manifest(["123"], fetch_json=submission)
    manifest_csv = source.write_csv(tmp_path / "primary.csv")
    documents = tmp_path / "documents"
    local = documents / "0000000123" / "000000012326000002" / "report.htm.gz"
    local.parent.mkdir(parents=True)
    local.write_bytes(
        gzip.compress(
            b'<a href="ex21-subsidiaries.htm">Subsidiaries</a>'
            b'<a href="guarantors.htm">Exhibit 22.1</a>'
        )
    )

    result = discover_offline_exhibits(manifest_csv, documents)
    assert result.coverage["parsed_parent_filings"] == 1
    assert result.coverage["parsed_compressed_parent_filings"] == 1
    assert result.coverage["parsed_plain_parent_filings"] == 0
    assert result.coverage["missing_local_parent_filings"] == 0
    assert [record.primary_document for record in result.manifest.records] == [
        "ex21-subsidiaries.htm",
        "guarantors.htm",
    ]
    assert "exhibit:21:subsidiary roster exhibit" in result.manifest.records[0].relevance_reasons
    assert "exhibit:22:guarantor subsidiary exhibit" in result.manifest.records[1].relevance_reasons


def test_offline_manifest_marks_corrupt_gzip_as_parse_error(tmp_path: Path):
    def submission(_url: str) -> dict[str, object]:
        return {
            "name": "Example",
            "filings": {
                "recent": {
                    "accessionNumber": ["0000000123-26-000002"],
                    "filingDate": ["2026-09-15"],
                    "reportDate": ["2026-09-15"],
                    "acceptanceDateTime": ["2026-09-15T20:00:00Z"],
                    "form": ["10-Q"],
                    "items": [""],
                    "size": [100],
                    "isXBRL": [0],
                    "isInlineXBRL": [0],
                    "primaryDocument": ["report.htm"],
                    "primaryDocDescription": ["Quarterly report"],
                }
            },
        }

    source = build_edgar_filing_manifest(["123"], fetch_json=submission)
    manifest_csv = source.write_csv(tmp_path / "primary.csv")
    documents = tmp_path / "documents"
    local = documents / "0000000123" / "000000012326000002" / "report.htm.gz"
    local.parent.mkdir(parents=True)
    local.write_bytes(b"not a gzip member")

    result = discover_offline_exhibits(manifest_csv, documents)
    assert result.coverage["parsed_parent_filings"] == 0
    assert result.coverage["missing_local_parent_filings"] == 0
    assert result.coverage["parse_error_parent_filings"] == 1


def test_offline_manifest_reports_unlinked_parent_for_index_followup(tmp_path: Path):
    def submission(_url: str) -> dict[str, object]:
        return {
            "name": "Example",
            "filings": {
                "recent": {
                    "accessionNumber": ["0000000123-26-000002"],
                    "filingDate": ["2026-09-15"],
                    "reportDate": ["2026-09-15"],
                    "acceptanceDateTime": ["2026-09-15T20:00:00Z"],
                    "form": ["10-Q"],
                    "items": [""],
                    "size": [100],
                    "isXBRL": [0],
                    "isInlineXBRL": [0],
                    "primaryDocument": ["report.htm"],
                    "primaryDocDescription": ["Quarterly report"],
                }
            },
        }

    source = build_edgar_filing_manifest(["123"], fetch_json=submission)
    manifest_csv = source.write_csv(tmp_path / "primary.csv")
    documents = tmp_path / "documents"
    local = documents / "0000000123" / "000000012326000002" / "report.htm"
    local.parent.mkdir(parents=True)
    local.write_text("<html><body>No exhibit links</body></html>")

    result = discover_offline_exhibits(manifest_csv, documents)
    assert result.coverage["parents_with_no_exhibit_links"] == 1
    assert result.coverage["discovered_exhibit_rows"] == 0
    assert result.coverage["no_exhibit_link_parent_keys"] == [
        "0000000123:0000000123-26-000002:report.htm"
    ]
