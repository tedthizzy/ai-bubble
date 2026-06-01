from __future__ import annotations

import csv
import json
from typing import TYPE_CHECKING

from bubble.analysis.source_coverage import build_source_coverage_report
from bubble.ingestion.capital.lease_extraction import extract_lease_agreements

if TYPE_CHECKING:
    from pathlib import Path


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def test_extract_lease_agreements_joins_edgar_inventory_provenance(tmp_path: Path):
    deals_csv = tmp_path / "edgar_acquisition" / "deals.csv"
    inventory_csv = tmp_path / "edgar_acquisition" / "edgar_document_inventory.csv"
    output_csv = tmp_path / "capital" / "lease_agreements.csv"
    source_uri = "https://www.sec.gov/Archives/edgar/data/1/000000000126000001/ex10-1.htm"
    content_hash = "a" * 64
    key_terms = {
        "accession_number": "0000000001-26-000001",
        "document_local_path": "data/edgar_acquisition/documents/0001/ex10-1.htm",
        "document_type": "exhibit",
        "filing_date": "2026-05-01",
        "filing_form": "8-K",
        "manifest_relevance_reasons": ["exhibit:10:material contract exhibit"],
        "manifest_relevance_score": 200,
        "primary_document": "ex10-1.htm",
    }
    roles = {"lessee": ["AI Tenant Inc."], "lessor": ["Data Center Landlord LLC"]}
    _write_csv(
        deals_csv,
        [
            {
                "deal_id": "edgar:0000000001:000000000126000001:lease:aaaaaaaaaaaa",
                "deal_type": "lease",
                "title": "AI Tenant Inc. - SEC exhibit ex10-1.htm",
                "parties": "AI Tenant Inc.|Data Center Landlord LLC",
                "primary_party": "AI Tenant Inc.",
                "counterparty_roles": json.dumps(roles),
                "notional_amount_usd": "75000000",
                "maturity_date": "2031-05-01",
                "currency": "USD",
                "source_uri": source_uri,
                "source_type": "sec_edgar",
                "source_confidence": "0.86",
                "human_review_status": "pending",
                "page_or_section": "8-K 0000000001-26-000001 ex10-1.htm",
                "content_hash": content_hash,
                "confidence": "0.86",
                "key_terms": json.dumps(key_terms),
            },
            {
                "deal_id": "seed-lease",
                "deal_type": "lease",
                "title": "Seed row",
                "parties": "A|B",
                "source_uri": "seed:bad",
                "source_type": "manual_curated",
                "content_hash": "b" * 64,
            },
            {
                "deal_id": "debt-1",
                "deal_type": "debt_facility",
                "title": "Debt row",
                "parties": "A|Bank",
                "source_uri": source_uri,
                "source_type": "sec_edgar",
                "content_hash": content_hash,
            },
        ],
    )
    _write_csv(
        inventory_csv,
        [
            {
                "cik": "0000000001",
                "company_name": "AI Tenant Inc.",
                "form": "8-K",
                "accession_number": "0000000001-26-000001",
                "filing_date": "2026-05-01",
                "primary_document": "ex10-1.htm",
                "document_type": "exhibit",
                "parent_primary_document": "tenant-20260501.htm",
                "filing_url": source_uri,
                "local_path": "data/edgar_acquisition/documents/0001/ex10-1.htm",
                "content_hash": content_hash,
                "byte_count": "1200",
                "text_char_count": "900",
                "relevance_score": "200",
                "relevance_reasons": "form:8-K|exhibit:10:material contract exhibit",
                "downloaded_at": "2026-06-01T10:00:00+00:00",
            }
        ],
    )

    summary = extract_lease_agreements(
        deals_csv=deals_csv,
        inventory_csv=inventory_csv,
        output_csv=output_csv,
        max_workers=4,
    )
    rows = _read_csv(output_csv)

    assert summary.source_rows == 3
    assert summary.lease_candidates == 2
    assert summary.agreements_written == 1
    assert summary.skipped_rows == 1
    assert summary.inventory_matches == 1
    assert rows[0]["deal_id"] == "edgar:0000000001:000000000126000001:lease:aaaaaaaaaaaa"
    assert rows[0]["lessee"] == "AI Tenant Inc."
    assert rows[0]["lessor"] == "Data Center Landlord LLC"
    assert rows[0]["filing_accession"] == "0000000001-26-000001"
    assert rows[0]["document_id"] == "sec-edgar:0000000001:000000000126000001:ex10-1.htm"
    assert rows[0]["source_document_kind"] == "sec_exhibit_agreement"
    assert rows[0]["is_agreement_exhibit"] == "true"
    assert rows[0]["retrieved_at"] == "2026-06-01T10:00:00+00:00"
    assert rows[0]["content_hash"] == content_hash


def test_source_coverage_dedupes_lease_agreement_corpus_with_extracted_deals(tmp_path: Path):
    source_uri = "https://www.sec.gov/Archives/edgar/data/1/000000000126000001/ex10-1.htm"
    content_hash = "a" * 64
    lease_row = {
        "deal_id": "edgar:0000000001:000000000126000001:lease:aaaaaaaaaaaa",
        "deal_type": "lease",
        "title": "Lease agreement",
        "parties": "AI Tenant Inc.|Data Center Landlord LLC",
        "source_uri": source_uri,
        "source_type": "sec_edgar",
        "content_hash": content_hash,
    }
    _write_csv(tmp_path / "edgar_acquisition" / "deals.csv", [lease_row])
    _write_csv(
        tmp_path / "capital" / "lease_agreements.csv",
        [
            {
                **lease_row,
                "agreement_id": "lease_agreement:edgar:0000000001:000000000126000001:lease:aaaaaaaaaaaa",
                "lessee": "AI Tenant Inc.",
                "lessor": "Data Center Landlord LLC",
                "retrieved_at": "2026-06-01T10:00:00+00:00",
                "filing_accession": "0000000001-26-000001",
                "document_id": "sec-edgar:0000000001:000000000126000001:ex10-1.htm",
            }
        ],
    )

    report = build_source_coverage_report([tmp_path])

    assert report.raw_rows_by_corpus["lease_agreements"] == 1
    assert report.extracted_deals == 1
    assert report.lease_agreements == 1
    assert report.source_backed_deals == 1
    assert report.deal_types == {"lease": 1}
