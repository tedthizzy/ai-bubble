from __future__ import annotations

import csv
import json
from typing import TYPE_CHECKING

from bubble.ingestion.capital.ppa_extraction import extract_ppa_deals

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
        return [dict(row) for row in csv.DictReader(f)]


def test_extract_ppa_deals_normalizes_ferc_rows(tmp_path: Path):
    input_csv = tmp_path / "ppas.csv"
    output_csv = tmp_path / "deals.csv"
    _write_csv(
        input_csv,
        [
            {
                "ID": "2179",
                "Reporting_Entity_CID": "C001557",
                "Reporting_Entity_Name": "Stanton Clean Energy, LLC",
                "Submission_ID": "1280534",
                "PPA_Agreement_ID": "17863",
                "PPA_Type": "Sale",
                "Supply_Type": "Generator Specific",
                "Start_Date": "2003-10-01T00:00:00.000Z",
                "Amount": "43.7",
                "Scheduled_End_Date": "2033-09-30T00:00:00.000Z",
                "Source_Balancing_Authority": "FMPP",
                "Entity_ID": "C001557",
                "Entity_ID_Type_CD": "CID",
                "Entity_Name": "Stanton Clean Energy, LLC",
                "Counterparty_ID": "C003749",
                "Counterparty_ID_Type_CD": "CID",
                "Counterparty_Name": "Florida Municipal Power Agency",
                "Record_Status": "Active",
                "Record_Type": "New",
                "source_uri": "https://data.ferc.gov/api/v1/dataset/17/",
                "source_type": "ferc",
                "content_hash": "abc123",
                "source_id": "ferc-page",
                "local_path": "raw/ppas/page.json",
                "record_index": "0",
            }
        ],
    )

    summary = extract_ppa_deals(input_csv, output_csv)
    rows = _read_csv(output_csv)

    assert summary.deals_written == 1
    assert rows[0]["deal_id"] == "ppa:ferc:2179"
    assert rows[0]["deal_type"] == "ppa"
    assert rows[0]["parties"] == "Stanton Clean Energy, LLC|Florida Municipal Power Agency"
    assert rows[0]["effective_date"] == "2003-10-01"
    assert rows[0]["maturity_date"] == "2033-09-30"
    assert rows[0]["source_type"] == "ferc"
    assert rows[0]["content_hash"] == "abc123"

    roles = json.loads(rows[0]["counterparty_roles"])
    assert roles["seller"] == ["Stanton Clean Energy, LLC"]
    assert roles["buyer"] == ["Florida Municipal Power Agency"]
    assert roles["offtaker"] == ["Florida Municipal Power Agency"]

    key_terms = json.loads(rows[0]["key_terms"])
    assert key_terms["amount_mw"] == 43.7
    assert key_terms["record_status"] == "Active"
    assert key_terms["source_artifact_id"] == "ferc-page"


def test_extract_ppa_deals_skips_obvious_test_company_rows(tmp_path: Path):
    input_csv = tmp_path / "ppas.csv"
    output_csv = tmp_path / "deals.csv"
    _write_csv(
        input_csv,
        [
            {
                "ID": "1",
                "Reporting_Entity_Name": "PRODUCTION TESTCOMPANY 7",
                "Entity_Name": "PRODUCTION TESTCOMPANY 7",
                "Counterparty_Name": "PRODUCTION TESTCOMPANY 7",
                "PPA_Type": "Purchase",
                "source_uri": "https://data.ferc.gov/api/v1/dataset/17/",
                "source_type": "ferc",
            }
        ],
    )

    summary = extract_ppa_deals(input_csv, output_csv)
    rows = _read_csv(output_csv)

    assert summary.source_rows == 1
    assert summary.deals_written == 0
    assert summary.skipped_rows == 1
    assert summary.workers == 1
    assert rows == []


def test_extract_ppa_deals_preserves_row_order_with_parallel_workers(tmp_path: Path):
    input_csv = tmp_path / "ppas.csv"
    output_csv = tmp_path / "deals.csv"
    _write_csv(
        input_csv,
        [
            {
                "ID": str(index),
                "Reporting_Entity_Name": f"Seller {index}",
                "Entity_Name": f"Seller {index}",
                "Counterparty_Name": f"Buyer {index}",
                "PPA_Type": "Sale",
                "source_uri": "https://data.ferc.gov/api/v1/dataset/17/",
                "source_type": "ferc",
            }
            for index in range(1, 9)
        ],
    )

    summary = extract_ppa_deals(input_csv, output_csv, max_workers=4)
    rows = _read_csv(output_csv)

    assert summary.workers == 4
    assert summary.deals_written == 8
    assert [row["deal_id"] for row in rows] == [f"ppa:ferc:{index}" for index in range(1, 9)]
