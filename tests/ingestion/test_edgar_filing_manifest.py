from __future__ import annotations

import json
import time
from datetime import date
from threading import Lock
from typing import TYPE_CHECKING, Any

from bubble.ingestion.edgar.filing_manifest import (
    build_edgar_filing_manifest,
    score_filing_relevance,
)

if TYPE_CHECKING:
    from pathlib import Path


def _sample_submission() -> dict[str, Any]:
    return {
        "name": "Example AI Infrastructure Corp",
        "tickers": ["AIDC"],
        "filings": {
            "recent": {
                "accessionNumber": [
                    "0000000000-26-000003",
                    "0000000000-26-000002",
                    "0000000000-25-000001",
                    "0000000000-23-000001",
                ],
                "filingDate": ["2026-05-01", "2026-04-10", "2025-02-15", "2023-12-31"],
                "reportDate": ["2026-03-31", "2026-04-10", "2024-12-31", "2023-09-30"],
                "acceptanceDateTime": [
                    "2026-05-01T16:15:00.000Z",
                    "2026-04-10T08:00:00.000Z",
                    "2025-02-15T17:00:00.000Z",
                    "2023-12-31T12:00:00.000Z",
                ],
                "form": ["10-Q", "8-K", "10-K", "8-K"],
                "items": ["", "1.01 2.03 9.01", "", "8.01"],
                "size": [1200000, 400000, 2800000, 100000],
                "isXBRL": [1, 0, 1, 0],
                "isInlineXBRL": [1, 0, 1, 0],
                "primaryDocument": [
                    "aidc-20260331.htm",
                    "credit-agreement.htm",
                    "aidc-20241231.htm",
                    "old-event.htm",
                ],
                "primaryDocDescription": [
                    "Quarterly report",
                    "Material definitive agreement - data center credit agreement",
                    "Annual report with AI infrastructure lease commitments",
                    "Older event",
                ],
            }
        },
    }


def test_build_edgar_filing_manifest_scores_filters_and_preserves_provenance(tmp_path: Path):
    calls: list[str] = []

    def fake_fetch(url: str) -> dict[str, Any]:
        calls.append(url)
        return _sample_submission()

    manifest = build_edgar_filing_manifest(
        ["123"],
        fetch_json=fake_fetch,
        since=date(2025, 1, 1),
        max_filings_per_cik=10,
        max_workers=12,
        sec_requests_per_second=7.5,
        sec_domain_concurrency=5,
        retry_attempts=5,
    )

    assert calls == ["https://data.sec.gov/submissions/CIK0000000123.json"]
    assert manifest.summary.entities_requested == 1
    assert manifest.summary.entities_returned == 1
    assert manifest.summary.total_filings == 3
    assert manifest.summary.forms == {"10-K": 1, "10-Q": 1, "8-K": 1}
    assert manifest.summary.earliest_filing_date == "2025-02-15"
    assert manifest.summary.latest_filing_date == "2026-05-01"
    assert manifest.summary.workers == 1
    assert manifest.summary.sec_requests_per_second == 7.5
    assert manifest.summary.sec_domain_concurrency == 5
    assert manifest.summary.retry_attempts == 5
    assert manifest.summary.include_exhibits is False
    assert manifest.summary.exhibit_index_workers == 4

    prioritized = manifest.prioritized_records()
    assert prioritized[0].form == "8-K"
    assert prioritized[0].accession_number == "0000000000-26-000002"
    assert prioritized[0].filing_url
    assert prioritized[0].filing_url.endswith("/000000000026000002/credit-agreement.htm")
    assert prioritized[0].provenance.source_uri == calls[0]
    assert "item:2.03:direct financial obligation" in prioritized[0].relevance_reasons
    assert "keyword:credit agreement" in prioritized[0].relevance_reasons

    csv_path = manifest.write_csv(tmp_path / "manifest.csv")
    summary_path = manifest.write_summary_json(tmp_path / "summary.json")
    assert csv_path.read_text().splitlines()[0].startswith("cik,company_name,ticker")
    assert json.loads(summary_path.read_text())["burry_relevant_filings"] == 3


def test_score_filing_relevance_prioritizes_burry_signals():
    score, reasons = score_filing_relevance(
        form="8-K",
        items=["1.01", "2.03", "9.01"],
        primary_document="exhibit-10-credit-agreement.htm",
        primary_document_description="Credit agreement for GPU data center project finance",
        is_xbrl=False,
        is_inline_xbrl=False,
    )

    assert score >= 150
    assert "item:1.01:material definitive agreement" in reasons
    assert "item:2.03:direct financial obligation" in reasons
    assert "keyword:data center" in reasons
    assert "keyword:project finance" in reasons
    assert "exhibit:10:material contract exhibit" in reasons


def test_build_edgar_filing_manifest_can_append_exhibit_documents():
    calls: list[str] = []

    def fake_fetch(url: str) -> dict[str, Any]:
        calls.append(url)
        if url.endswith("/index.json"):
            return {
                "directory": {
                    "item": [
                        {"name": "form8k.htm", "size": "1,000"},
                        {"name": "ex10-1-lease-agreement.htm", "size": "2,000"},
                        {"name": "ex4-1-indent.htm", "size": "3,000"},
                        {"name": "ex101.xml", "size": "4,000"},
                        {"name": "image.jpg", "size": "10"},
                    ]
                }
            }
        return {
            "name": "Example AI Infrastructure Corp",
            "tickers": ["AIDC"],
            "filings": {
                "recent": {
                    "accessionNumber": ["0000000000-26-000002"],
                    "filingDate": ["2026-04-10"],
                    "reportDate": ["2026-04-10"],
                    "acceptanceDateTime": ["2026-04-10T08:00:00.000Z"],
                    "form": ["8-K"],
                    "items": ["1.01 9.01"],
                    "size": [400000],
                    "isXBRL": [0],
                    "isInlineXBRL": [0],
                    "primaryDocument": ["form8k.htm"],
                    "primaryDocDescription": ["Material definitive agreement"],
                }
            },
        }

    manifest = build_edgar_filing_manifest(
        ["123"],
        fetch_json=fake_fetch,
        include_exhibits=True,
        max_exhibits_per_filing=10,
        exhibit_index_workers=3,
    )

    assert calls == [
        "https://data.sec.gov/submissions/CIK0000000123.json",
        "https://www.sec.gov/Archives/edgar/data/123/000000000026000002/index.json",
    ]
    assert manifest.summary.total_filings == 1
    assert manifest.summary.total_document_rows == 3
    assert manifest.summary.documents_by_type == {"exhibit": 2, "primary": 1}
    assert manifest.summary.include_exhibits is True
    assert manifest.summary.exhibit_index_workers == 3
    assert len(manifest.records) == 3
    exhibits = [record for record in manifest.records if record.document_type == "exhibit"]
    assert [record.primary_document for record in exhibits] == [
        "ex10-1-lease-agreement.htm",
        "ex4-1-indent.htm",
    ]
    assert all(record.parent_primary_document == "form8k.htm" for record in exhibits)
    assert exhibits[0].filing_url
    assert exhibits[0].filing_url.endswith("/ex10-1-lease-agreement.htm")
    assert exhibits[0].source_uri.endswith("/index.json")
    assert exhibits[0].provenance.source_uri.endswith("/index.json")
    assert "exhibit:10:material contract exhibit" in exhibits[0].relevance_reasons
    assert "exhibit:4:indenture or security instrument exhibit" in exhibits[1].relevance_reasons


def test_exhibit_index_fetches_use_one_global_worker_pool():
    active_index_fetches = 0
    max_active_index_fetches = 0
    lock = Lock()

    def fake_fetch(url: str) -> dict[str, Any]:
        nonlocal active_index_fetches, max_active_index_fetches
        if url.endswith("/index.json"):
            with lock:
                active_index_fetches += 1
                max_active_index_fetches = max(max_active_index_fetches, active_index_fetches)
            time.sleep(0.02)
            with lock:
                active_index_fetches -= 1
            return {
                "directory": {
                    "item": [
                        {"name": "form8k.htm", "size": "1,000"},
                        {"name": "ex10-1-credit-agreement.htm", "size": "2,000"},
                    ]
                }
            }
        return {
            "name": "Example AI Infrastructure Corp",
            "tickers": ["AIDC"],
            "filings": {
                "recent": {
                    "accessionNumber": ["0000000000-26-000002"],
                    "filingDate": ["2026-04-10"],
                    "reportDate": ["2026-04-10"],
                    "acceptanceDateTime": ["2026-04-10T08:00:00.000Z"],
                    "form": ["8-K"],
                    "items": ["1.01 9.01"],
                    "size": [400000],
                    "isXBRL": [0],
                    "isInlineXBRL": [0],
                    "primaryDocument": ["form8k.htm"],
                    "primaryDocDescription": ["Material definitive agreement"],
                }
            },
        }

    manifest = build_edgar_filing_manifest(
        ["123", "456", "789", "101112"],
        fetch_json=fake_fetch,
        include_exhibits=True,
        max_workers=8,
        exhibit_index_workers=2,
        sec_requests_per_second=0,
        sec_domain_concurrency=8,
    )

    assert manifest.summary.entities_requested == 4
    assert manifest.summary.total_filings == 4
    assert manifest.summary.total_document_rows == 8
    assert manifest.summary.documents_by_type == {"exhibit": 4, "primary": 4}
    assert max_active_index_fetches <= 2
