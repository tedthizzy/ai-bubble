from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from bubble.analysis.physical_capacity import build_physical_capacity_summary

if TYPE_CHECKING:
    from pathlib import Path


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    assert rows
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_physical_capacity_summary_rolls_up_queue_and_equipment_capacity(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "source_rows" / "queue_records.csv",
        [
            {
                "source_id": "caiso-cluster-15-queue-report",
                "source_uri": "https://example.com/caiso.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "hash-caiso",
                "document_id": "caiso",
                "NET MW POI": "500",
            },
            {
                "source_id": "ercot-gis-report-1",
                "source_uri": "https://example.com/ercot.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "hash-ercot",
                "document_id": "ercot",
                "Project Name": "Giga Texas Data Center",
                "Capacity (MW)": "203",
                "Status": "SS Completed, FIS Completed, IA",
                "Projected COD": "2026-03-15T00:00:00",
                "Interconnecting Entity": "Giga Texas Energy, LLC",
            },
            {
                "source_id": "miso-eras-interconnection-requests",
                "source_uri": "https://example.com/miso.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "hash-miso",
                "document_id": "miso",
                "Project Number": "E0042",
                "Max Summer MW": "100",
                "Max Winter MW": "120",
                "Non-Confidential Summary": (
                    "This resource adequacy need is driven by hyperscale data center load."
                ),
            },
            {
                "source_id": "nyiso-interconnection-queue",
                "source_uri": "https://example.com/nyiso.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "hash-nyiso",
                "document_id": "nyiso",
                "Project Name": "Missing MW",
            },
            {
                "source_id": "spp-active-generation-interconnection-queue",
                "source_uri": "https://example.com/spp.csv",
                "source_type": "grid_interconnection_queue",
                "content_hash": "hash-spp",
                "document_id": "spp",
                "Capacity": "145",
            },
        ],
    )
    _write_csv(
        tmp_path / "source_rows" / "equipment_records.csv",
        [
            {
                "source_id": "eia-860m-generator-inventory-april-2026",
                "source_uri": "https://example.com/eia.xlsx",
                "source_type": "eia",
                "content_hash": "hash-eia",
                "document_id": "eia",
                "sheet_name": "Operating",
                "Nameplate Capacity (MW)": "10.5",
                "Balancing Authority Code": "ERCO",
            },
            {
                "source_id": "eia-860m-generator-inventory-april-2026",
                "source_uri": "https://example.com/eia.xlsx",
                "source_type": "eia",
                "content_hash": "hash-eia",
                "document_id": "eia",
                "sheet_name": "Planned",
                "Nameplate Capacity (MW)": "20",
                "Balancing Authority Code": "ERCO",
                "Plant State": "TX",
            },
            {
                "source_id": "epa-egrid2023-data-rev2",
                "source_uri": "https://example.com/egrid.xlsx",
                "source_type": "epa",
                "content_hash": "hash-epa",
                "document_id": "epa",
                "sheet_name": "GEN23",
                "Generator nameplate capacity (MW)": "30",
            },
            {
                "source_id": "epa-egrid2023-data-rev2",
                "source_uri": "https://example.com/egrid.xlsx",
                "source_type": "epa",
                "content_hash": "hash-epa",
                "document_id": "epa",
                "sheet_name": "GEN23",
                "Generator nameplate capacity (MW)": "NAMEPCAP",
            },
        ],
    )

    summary = build_physical_capacity_summary([tmp_path])

    assert summary.queue_records_scanned == 5
    assert summary.queue_capacity_records == 4
    assert summary.queue_capacity_mw == 968
    assert summary.queue_capacity_by_region_mw == {
        "CAISO": 500,
        "ERCOT": 203,
        "SPP": 145,
        "MISO": 120,
    }
    assert summary.data_center_queue_records == 2
    assert summary.data_center_queue_capacity_mw == 323
    assert summary.data_center_queue_capacity_by_region_mw == {
        "ERCOT": 203,
        "MISO": 120,
    }
    assert summary.data_center_queue_capacity_by_relationship_mw == {
        "direct_data_center_load": 203,
        "supporting_generation_for_data_center_load": 120,
    }
    assert summary.top_data_center_queue_projects[:2] == [
        {
            "project_name": "Giga Texas Data Center",
            "queue_id": "",
            "relationship": "direct_data_center_load",
            "region": "ERCOT",
            "status": "SS Completed, FIS Completed, IA",
            "capacity_mw": 203,
            "requested_in_service_date": "2026-03-15T00:00:00",
            "customer": "Giga Texas Energy, LLC",
            "county": "",
            "state": "",
            "point_of_interconnection": "",
            "data_center_load_description": "",
            "source_id": "ercot-gis-report-1",
            "source_uri": "https://example.com/ercot.xlsx",
            "content_hash": "hash-ercot",
            "record_index": "",
        },
        {
            "project_name": "unknown",
            "queue_id": "E0042",
            "relationship": "supporting_generation_for_data_center_load",
            "region": "MISO",
            "status": "",
            "capacity_mw": 120,
            "requested_in_service_date": "",
            "customer": "",
            "county": "",
            "state": "",
            "point_of_interconnection": "",
            "data_center_load_description": (
                "This resource adequacy need is driven by hyperscale data center load."
            ),
            "source_id": "miso-eras-interconnection-requests",
            "source_uri": "https://example.com/miso.xlsx",
            "content_hash": "hash-miso",
            "record_index": "",
        },
    ]
    assert summary.eia_operating_capacity_mw == 10.5
    assert summary.eia_planned_capacity_mw == 20
    assert summary.egrid_generator_capacity_mw == 30
    assert summary.equipment_capacity_records == 3
    assert summary.eia_operating_capacity_by_region_mw == {"ERCOT": 10.5}
    assert summary.eia_planned_capacity_by_region_mw == {"ERCOT": 20}
    assert summary.physical_stress_indicators[:3] == [
        {
            "region": "CAISO",
            "queue_capacity_mw": 500,
            "eia_planned_capacity_mw": 0,
            "eia_operating_capacity_mw": 0,
            "queue_less_planned_mw": 500,
            "queue_to_planned_ratio": None,
            "queue_to_operating_ratio": None,
            "stress_level": "high",
        },
        {
            "region": "ERCOT",
            "queue_capacity_mw": 203,
            "eia_planned_capacity_mw": 20,
            "eia_operating_capacity_mw": 10.5,
            "queue_less_planned_mw": 183,
            "queue_to_planned_ratio": 10.15,
            "queue_to_operating_ratio": 19.333,
            "stress_level": "high",
        },
        {
            "region": "SPP",
            "queue_capacity_mw": 145,
            "eia_planned_capacity_mw": 0,
            "eia_operating_capacity_mw": 0,
            "queue_less_planned_mw": 145,
            "queue_to_planned_ratio": None,
            "queue_to_operating_ratio": None,
            "stress_level": "high",
        },
    ]
    assert summary.physical_stress_indicators[3] == {
        "region": "MISO",
        "queue_capacity_mw": 120,
        "eia_planned_capacity_mw": 0,
        "eia_operating_capacity_mw": 0,
        "queue_less_planned_mw": 120,
        "queue_to_planned_ratio": None,
        "queue_to_operating_ratio": None,
        "stress_level": "high",
    }
    assert summary.skipped_rows == {
        "egrid_missing_capacity": 1,
        "queue_missing_capacity": 1,
    }
    assert len(summary.source_documents) == 7


def test_physical_capacity_summary_skips_completed_or_withdrawn_queue_rows(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "source_rows" / "queue_records.csv",
        [
            {
                "source_id": "pjm-planning-queues-xml",
                "source_uri": "https://example.com/pjm.xml",
                "source_type": "grid_interconnection_queue",
                "content_hash": "hash-pjm",
                "document_id": "pjm",
                "ProjectNumber": "PJM-ACTIVE",
                "Status": "Active",
                "MaximumFacilityOutput": "450",
            },
            {
                "source_id": "pjm-planning-queues-xml",
                "source_uri": "https://example.com/pjm.xml",
                "source_type": "grid_interconnection_queue",
                "content_hash": "hash-pjm",
                "document_id": "pjm",
                "ProjectNumber": "PJM-WITHDRAWN",
                "Status": "Withdrawn",
                "MaximumFacilityOutput": "999",
            },
            {
                "source_id": "iso-ne-public-queue-1",
                "source_uri": "https://example.com/isone.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "hash-iso",
                "document_id": "iso",
                "Position": "1100",
                "Project Status": "Under Study",
                "Net MW": "0",
                "Summer MW": "200",
            },
        ],
    )

    summary = build_physical_capacity_summary([tmp_path])

    assert summary.queue_records_scanned == 3
    assert summary.queue_capacity_records == 2
    assert summary.queue_capacity_mw == 650
    assert summary.queue_capacity_by_region_mw == {"PJM": 450, "ISO-NE": 200}
    assert summary.skipped_rows == {"queue_out_of_scope_status": 1}


def test_physical_capacity_summary_reports_distinct_tracker_capacity(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "physical" / "projects.csv",
        [
            {
                "project_id": "server:meta-huntsville",
                "name": "Meta Huntsville Data Center",
                "city": "Huntsville",
                "county": "Madison",
                "state": "Alabama",
                "jurisdiction": "Madison County, Alabama",
                "operator": "Meta Platforms, Inc.",
                "source_id": "server-country-all-projects",
                "source_uri": "https://servercountry.org/data/all_projects.csv",
                "source_type": "project_tracker",
                "content_hash": "hash-server",
                "capacity_mw_low": "214",
                "capacity_mw_high": "214",
                "investment_usd": "1500000000",
                "construction_status": "in_service",
            },
            {
                "project_id": "fractracker:meta-huntsville",
                "name": "Meta Data Center",
                "city": "Huntsville",
                "county": "Madison",
                "state": "AL",
                "jurisdiction": "Madison, AL",
                "operator": "Meta",
                "source_id": "fractracker-data-centers-000000-001000",
                "source_uri": "https://services.arcgis.com/example/query",
                "source_type": "project_tracker",
                "content_hash": "hash-frac",
                "capacity_mw_low": "100",
                "capacity_mw_high": "200",
                "investment_usd": "800000000",
                "construction_status": "in_service",
            },
            {
                "project_id": "server:other-campus",
                "name": "Other Campus",
                "city": "Dallas",
                "county": "Dallas",
                "state": "TX",
                "jurisdiction": "Dallas, TX",
                "operator": "OtherCo",
                "source_id": "server-country-all-projects",
                "source_uri": "https://servercountry.org/data/all_projects.csv",
                "source_type": "project_tracker",
                "content_hash": "hash-server",
                "capacity_mw_low": "50",
                "capacity_mw_high": "100",
                "investment_usd": "200000000",
                "construction_status": "announced",
            },
        ],
    )

    summary = build_physical_capacity_summary([tmp_path])

    assert summary.tracker_project_records_scanned == 3
    assert summary.tracker_capacity_high_mw == 514
    assert summary.tracker_distinct_projects == 3
    assert summary.tracker_duplicate_groups == 0
    assert summary.tracker_duplicate_rows_collapsed == 0
    assert summary.tracker_distinct_capacity_high_mw == 514
    assert summary.tracker_distinct_capacity_low_mw == 364
    assert summary.tracker_distinct_operating_capacity_high_mw == 414
    assert summary.tracker_distinct_pipeline_capacity_high_mw == 100
    assert summary.tracker_distinct_investment_usd == 2_500_000_000
    assert summary.tracker_distinct_capacity_by_status_mw == {
        "in_service": 414,
        "announced": 100,
    }
    assert summary.tracker_distinct_capacity_by_state_mw == {"AL": 414, "TX": 100}


def test_physical_capacity_summary_collapses_exact_named_tracker_sites(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "physical" / "projects.csv",
        [
            {
                "project_id": "server:homer-city",
                "name": "Homer City Energy Campus",
                "city": "Homer City",
                "state": "Pennsylvania",
                "operator": "Homer City Redevelopment, LLC",
                "source_id": "server-country-all-projects",
                "source_uri": "https://servercountry.org/data/all_projects.csv",
                "source_type": "project_tracker",
                "content_hash": "hash-server",
                "capacity_mw_high": "4500",
                "investment_usd": "10000000000",
                "construction_status": "announced",
            },
            {
                "project_id": "fractracker:homer-city",
                "name": "Homer City Energy Campus",
                "city": "Homer City",
                "state": "PA",
                "address": "1750 Power Plant Road",
                "operator": "Homer City Redevelopment",
                "source_id": "fractracker-data-centers-000000-001000",
                "source_uri": "https://services.arcgis.com/example/query",
                "source_type": "project_tracker",
                "content_hash": "hash-frac",
                "capacity_mw_high": "4500",
                "investment_usd": "12000000000",
                "construction_status": "announced",
            },
        ],
    )

    summary = build_physical_capacity_summary([tmp_path])

    assert summary.tracker_capacity_high_mw == 9000
    assert summary.tracker_distinct_projects == 1
    assert summary.tracker_duplicate_groups == 1
    assert summary.tracker_duplicate_rows_collapsed == 1
    assert summary.tracker_distinct_capacity_high_mw == 4500
    assert summary.tracker_distinct_pipeline_capacity_high_mw == 4500
    assert summary.tracker_distinct_investment_usd == 12_000_000_000


def test_physical_capacity_summary_keeps_same_name_different_cities_distinct(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "physical" / "projects.csv",
        [
            {
                "project_id": "cielo:hudson",
                "name": "Cielo Digital Infrastructure",
                "city": "Hudson",
                "state": "CO",
                "operator": "Cielo Digital Infrastructure",
                "source_id": "fractracker-data-centers-000000-001000",
                "source_uri": "https://services.arcgis.com/example/query",
                "source_type": "project_tracker",
                "content_hash": "hash-cielo",
                "capacity_mw_high": "500",
                "construction_status": "announced",
            },
            {
                "project_id": "cielo:kansas-city",
                "name": "Cielo Digital Infrastructure",
                "city": "Kansas City",
                "state": "MO",
                "operator": "Cielo Digital Infrastructure",
                "source_id": "fractracker-data-centers-000000-001000",
                "source_uri": "https://services.arcgis.com/example/query",
                "source_type": "project_tracker",
                "content_hash": "hash-cielo",
                "capacity_mw_high": "500",
                "construction_status": "announced",
            },
        ],
    )

    summary = build_physical_capacity_summary([tmp_path])

    assert summary.tracker_capacity_high_mw == 1000
    assert summary.tracker_distinct_projects == 2
    assert summary.tracker_duplicate_groups == 0
    assert summary.tracker_duplicate_rows_collapsed == 0
    assert summary.tracker_distinct_capacity_high_mw == 1000


def test_physical_capacity_summary_keeps_delayed_and_mechanical_statuses(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "physical" / "projects.csv",
        [
            {
                "project_id": "delayed-campus",
                "name": "Delayed Campus",
                "state": "TX",
                "source_id": "tracker",
                "source_uri": "https://example.com/tracker.csv",
                "source_type": "project_tracker",
                "content_hash": "hash-delayed",
                "capacity_mw_high": "300",
                "construction_status": "delayed",
            },
            {
                "project_id": "commissioning-campus",
                "name": "Commissioning Campus",
                "state": "VA",
                "source_id": "tracker",
                "source_uri": "https://example.com/tracker.csv",
                "source_type": "project_tracker",
                "content_hash": "hash-mechanical",
                "capacity_mw_high": "125",
                "construction_status": "mechanical_completion",
            },
        ],
    )

    summary = build_physical_capacity_summary([tmp_path])

    assert summary.tracker_distinct_pipeline_capacity_high_mw == 425
    assert summary.tracker_distinct_capacity_by_status_mw == {
        "delayed": 300,
        "mechanical_completion": 125,
    }
