from __future__ import annotations

import csv
import json
from typing import TYPE_CHECKING

from bubble.ingestion.physical.tracker_extraction import extract_tracker_projects

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


def test_extract_tracker_projects_normalizes_server_country_and_fractracker_rows(
    tmp_path: Path,
):
    source = tmp_path / "tracker_records.csv"
    output = tmp_path / "projects.csv"
    _write_csv(
        source,
        [
            {
                "source_id": "server-country-all-projects",
                "source_uri": "https://servercountry.org/data/all_projects.csv",
                "source_type": "project_tracker",
                "content_hash": "hash-server",
                "local_path": "raw/server.csv",
                "record_index": "0",
                "projectName": "Mega Campus",
                "state": "Texas",
                "county": "Example County",
                "status": "under-construction",
                "sponsors": "Sponsor LLC",
                "operators": "Operator LLC",
                "tenants": "Tenant LLC",
                "powerCapacityMW": "250",
                "itLoadMW": "200",
                "investmentUSD": "1000000000",
                "expectedCompletionDate": "2027-12",
            },
            {
                "source_id": "fractracker-data-centers-000000-001000",
                "source_uri": "https://services.arcgis.com/example/query",
                "source_type": "project_tracker",
                "content_hash": "hash-frac",
                "local_path": "raw/fractracker.json",
                "record_index": "1",
                "facility_id": "42",
                "facility_name": "Range Campus",
                "state": "VA",
                "county": "Loudoun",
                "status": "Proposed",
                "operator_name": "CloudCo",
                "tenant": "AI Tenant",
                "mw_low": "150",
                "mw_high": "1000",
                "project_cost": "$6 billion",
                "expected_date_online": "2028",
                "location_confidence": "High",
                "lat": "39.1",
                "long": "-77.5",
                "info_source_1": "https://example.com/source",
            },
        ],
    )

    summary = extract_tracker_projects(source, output)
    rows = _read_csv(output)

    assert summary.source_rows == 2
    assert summary.projects_written == 2
    assert summary.workers == 2
    assert summary.capacity_records == 2
    assert summary.capacity_low_mw == 400
    assert summary.capacity_high_mw == 1250
    assert summary.investment_records == 2
    assert summary.investment_usd == 7_000_000_000
    assert rows[0]["project_id"] == "server-country-all-projects:mega-campus"
    assert rows[0]["capacity_mw"] == "250"
    assert rows[0]["construction_status"] == "under_construction"
    assert rows[0]["page_or_section"] == "raw/server.csv#record_index=0"
    assert rows[1]["project_id"] == "fractracker-data-centers-000000-001000:42"
    assert rows[1]["capacity_mw_low"] == "150"
    assert rows[1]["capacity_mw_high"] == "1000"
    assert rows[1]["investment_usd"] == "6000000000"
    assert rows[1]["source_confidence"] == "0.85"
    equipment = json.loads(rows[1]["major_equipment"])
    assert equipment["info_sources"] == ["https://example.com/source"]


def test_extract_tracker_projects_preserves_row_order_with_parallel_workers(
    tmp_path: Path,
):
    source = tmp_path / "tracker_records.csv"
    output = tmp_path / "projects.csv"
    _write_csv(
        source,
        [
            {
                "source_id": "tracker",
                "source_uri": "https://example.com/tracker.csv",
                "source_type": "project_tracker",
                "record_index": str(index),
                "projectName": f"Campus {index}",
                "state": "TX",
                "status": "Proposed",
            }
            for index in range(1, 9)
        ],
    )

    summary = extract_tracker_projects(source, output, max_workers=4)
    rows = _read_csv(output)

    assert summary.workers == 4
    assert summary.projects_written == 8
    assert [row["project_id"] for row in rows] == [
        f"tracker:campus-{index}" for index in range(1, 9)
    ]
