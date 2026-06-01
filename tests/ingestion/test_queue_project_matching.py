from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from bubble.ingestion.physical.queue_matching import match_data_center_queues_to_projects

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


def test_data_center_queue_matching_writes_audit_and_loader_rows(tmp_path: Path):
    projects = tmp_path / "projects.csv"
    queues = tmp_path / "queue_records.csv"
    matches_output = tmp_path / "queue_project_matches.csv"
    loader_output = tmp_path / "queues.csv"
    _write_csv(
        projects,
        [
            {
                "project_id": "tracker:giga-texas",
                "name": "Giga Texas Datacenter",
                "owner": "Giga Texas Energy, LLC",
                "operator": "",
                "county": "Travis",
                "state": "TX",
                "capacity_mw": "133",
                "source_uri": "https://example.com/projects.csv",
                "source_type": "project_tracker",
                "content_hash": "project-hash",
            }
        ],
    )
    _write_csv(
        queues,
        [
            {
                "source_id": "ercot-gis-report",
                "source_uri": "https://example.com/ercot.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "queue-hash",
                "local_path": "raw/ercot.xlsx",
                "record_index": "9",
                "document_id": "ercot",
                "Project Name": "Giga Texas Data Center",
                "County": "Travis",
                "State": "TX",
                "Capacity (MW)": "133",
                "GIM Study Phase": "SS Completed, FIS Completed, IA",
                "Projected COD": "2025-12-15T00:00:00",
                "Interconnecting Entity": "Giga Texas Energy, LLC",
                "POI Location": "Hornsby Substation",
            },
            {
                "source_id": "miso-eras-interconnection-requests",
                "source_uri": "https://example.com/miso.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "miso-hash",
                "local_path": "raw/miso.xlsx",
                "record_index": "40",
                "Project Number": "E0042",
                "County": "Jasper",
                "State": "IN",
                "Capacity (MW)": "2739.8",
                "Status": "Active",
                "Non-Confidential Summary": (
                    "The resource adequacy need is being driven by a hyperscale data center."
                ),
            },
        ],
    )

    summary = match_data_center_queues_to_projects(
        queue_rows_csv=queues,
        projects_csv=projects,
        matches_output=matches_output,
        queues_output=loader_output,
    )

    matches = _read_csv(matches_output)
    loader_rows = _read_csv(loader_output)
    assert summary.data_center_queue_rows == 2
    assert summary.strong_matches == 1
    assert summary.unmatched_rows == 1
    assert summary.loader_queue_rows == 1
    assert matches[0]["matched_project_id"] == "tracker:giga-texas"
    assert matches[0]["match_status"] == "strong_match"
    assert matches[0]["human_review_status"] == "pending"
    assert matches[1]["queue_relationship"] == "supporting_generation_for_data_center_load"
    assert matches[1]["matched_project_id"] == ""
    assert loader_rows == [
        {
            "project_id": "tracker:giga-texas",
            "queue_id": "ercot-gis-report:9",
            "region": "ercot",
            "status": "agreement_executed",
            "requested_mw": "133",
            "firm_service_mw": "133",
            "requested_in_service_date": "2025-12-15",
            "expected_in_service_date": "2025-12-15",
            "delay_months": "",
            "network_upgrade_cost_usd": "",
            "study_phase": "SS Completed, FIS Completed, IA",
            "notes": "",
            "source_uri": "https://example.com/ercot.xlsx",
            "source_type": "grid_interconnection_queue",
            "source_confidence": "0.99",
            "human_review_status": "pending",
            "page_or_section": "raw/ercot.xlsx#record_index=9",
            "content_hash": "queue-hash",
        }
    ]


def test_queue_matching_normalizes_project_full_state_names(tmp_path: Path):
    projects = tmp_path / "projects.csv"
    queues = tmp_path / "queue_records.csv"
    matches_output = tmp_path / "queue_project_matches.csv"
    loader_output = tmp_path / "queues.csv"
    _write_csv(
        projects,
        [
            {
                "project_id": "tracker:dakota-campus",
                "name": "Dakota AI Data Center",
                "owner": "Dakota Compute LLC",
                "operator": "Dakota Compute LLC",
                "county": "McKenzie County",
                "state": "North Dakota",
                "capacity_mw": "100",
            }
        ],
    )
    _write_csv(
        queues,
        [
            {
                "source_id": "queue-source",
                "source_uri": "https://example.com/queue.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "queue-hash",
                "local_path": "raw/queue.xlsx",
                "record_index": "5",
                "Project Name": "Dakota AI Data Center",
                "County": "McKenzie",
                "State": "ND",
                "Capacity (MW)": "100",
                "Status": "Facility Study",
                "Interconnecting Entity": "Dakota Compute LLC",
            }
        ],
    )

    summary = match_data_center_queues_to_projects(
        queue_rows_csv=queues,
        projects_csv=projects,
        matches_output=matches_output,
        queues_output=loader_output,
    )

    assert summary.loader_queue_rows == 1
    assert _read_csv(matches_output)[0]["matched_project_id"] == "tracker:dakota-campus"
    assert _read_csv(matches_output)[0]["matched_project_state"] == "ND"


def test_queue_matching_allows_exact_project_name_for_supporting_relationship(
    tmp_path: Path,
):
    projects = tmp_path / "projects.csv"
    queues = tmp_path / "queue_records.csv"
    matches_output = tmp_path / "queue_project_matches.csv"
    loader_output = tmp_path / "queues.csv"
    _write_csv(
        projects,
        [
            {
                "project_id": "tracker:st-lawrence",
                "name": "St Lawrence Data and Agricultural Center",
                "owner": "Petawatt Holdings",
                "operator": "Petawatt Holdings",
                "county": "St. Lawrence",
                "state": "NY",
                "capacity_mw": "200",
            }
        ],
    )
    _write_csv(
        queues,
        [
            {
                "source_id": "nyiso-interconnection-queue",
                "source_uri": "https://example.com/nyiso.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "queue-hash",
                "local_path": "raw/nyiso.xlsx",
                "record_index": "97",
                "Project Name": "St Lawrence Data and Agricultural Center",
                "County": "St. Lawrence",
                "State": "NY",
                "Capacity (MW)": "200",
                "Status": "Study",
                "Interconnection Customer": "ZeroC Data Centers, LLC",
            }
        ],
    )

    summary = match_data_center_queues_to_projects(
        queue_rows_csv=queues,
        projects_csv=projects,
        matches_output=matches_output,
        queues_output=loader_output,
    )

    matches = _read_csv(matches_output)
    assert summary.loader_queue_rows == 1
    assert matches[0]["queue_relationship"] == "supporting_generation_for_data_center_load"
    assert matches[0]["match_reasons"].endswith("supporting_queue_project_name_overlap")
    assert matches[0]["matched_project_id"] == "tracker:st-lawrence"


def test_queue_matching_uses_terawulf_wulf_alias_without_lowering_threshold(
    tmp_path: Path,
):
    projects = tmp_path / "projects.csv"
    queues = tmp_path / "queue_records.csv"
    matches_output = tmp_path / "queue_project_matches.csv"
    loader_output = tmp_path / "queues.csv"
    _write_csv(
        projects,
        [
            {
                "project_id": "tracker:lake-mariner",
                "name": "TeraWulf Lake Mariner",
                "owner": "TeraWulf",
                "operator": "TeraWulf",
                "county": "Niagara",
                "state": "NY",
                "capacity_mw": "750",
            }
        ],
    )
    _write_csv(
        queues,
        [
            {
                "source_id": "nyiso-interconnection-queue",
                "source_uri": "https://example.com/nyiso.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "queue-hash",
                "local_path": "raw/nyiso.xlsx",
                "record_index": "131",
                "Project Name": "Wulf Compute Data Center II",
                "County": "Niagara",
                "State": "NY",
                "Capacity (MW)": "250",
                "Status": "Study",
                "Interconnection Customer": "TeraWulf Brookings LLC",
            }
        ],
    )

    summary = match_data_center_queues_to_projects(
        queue_rows_csv=queues,
        projects_csv=projects,
        matches_output=matches_output,
        queues_output=loader_output,
    )

    matches = _read_csv(matches_output)
    assert summary.loader_queue_rows == 1
    assert matches[0]["match_status"] == "strong_match"
    assert "partial_name_overlap" in matches[0]["match_reasons"]
    assert "capacity_mismatch_penalty" in matches[0]["match_reasons"]
    assert matches[0]["matched_project_id"] == "tracker:lake-mariner"


def test_queue_matching_uses_donovan_typo_alias_for_tracker_operator(
    tmp_path: Path,
):
    projects = tmp_path / "projects.csv"
    queues = tmp_path / "queue_records.csv"
    matches_output = tmp_path / "queue_project_matches.csv"
    loader_output = tmp_path / "queues.csv"
    _write_csv(
        projects,
        [
            {
                "project_id": "tracker:treetop",
                "name": "Treetop Development Project",
                "owner": "onovan Drive Holdings LLC",
                "operator": "onovan Drive Holdings LLC",
                "county": "Dutchess",
                "state": "NY",
                "capacity_mw": "1000",
            }
        ],
    )
    _write_csv(
        queues,
        [
            {
                "source_id": "nyiso-interconnection-queue",
                "source_uri": "https://example.com/nyiso.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "queue-hash",
                "local_path": "raw/nyiso.xlsx",
                "record_index": "136",
                "Project Name": "1 Gig Data Center East Fishkill, NY",
                "County": "Dutchess",
                "State": "NY",
                "Capacity (MW)": "1000",
                "Status": "Study",
                "Interconnection Customer": "Donovan Drive Holdings LLC",
            }
        ],
    )

    summary = match_data_center_queues_to_projects(
        queue_rows_csv=queues,
        projects_csv=projects,
        matches_output=matches_output,
        queues_output=loader_output,
    )

    matches = _read_csv(matches_output)
    assert summary.loader_queue_rows == 1
    assert matches[0]["match_status"] == "strong_match"
    assert "strong_customer_owner_overlap" in matches[0]["match_reasons"]
    assert matches[0]["matched_project_id"] == "tracker:treetop"


def test_queue_matching_keeps_capacity_mismatch_but_loads_strong_name_location_match(
    tmp_path: Path,
):
    projects = tmp_path / "projects.csv"
    queues = tmp_path / "queue_records.csv"
    matches_output = tmp_path / "queue_project_matches.csv"
    loader_output = tmp_path / "queues.csv"
    _write_csv(
        projects,
        [
            {
                "project_id": "tracker:north-east-data",
                "name": "BlockFusion aka North East Data Center LLC",
                "owner": "",
                "operator": "",
                "county": "Niagara",
                "state": "NY",
                "capacity_mw": "50",
            }
        ],
    )
    _write_csv(
        queues,
        [
            {
                "source_id": "nyiso-interconnection-queue",
                "source_uri": "https://example.com/nyiso.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "queue-hash",
                "local_path": "raw/nyiso.xlsx",
                "record_index": "138",
                "Project Name": "North East Data LLC Data Center",
                "County": "Niagara",
                "State": "NY",
                "Capacity (MW)": "500",
                "Status": "Study",
                "Interconnection Customer": "North East Data LLC",
            }
        ],
    )

    summary = match_data_center_queues_to_projects(
        queue_rows_csv=queues,
        projects_csv=projects,
        matches_output=matches_output,
        queues_output=loader_output,
    )

    matches = _read_csv(matches_output)
    assert summary.loader_queue_rows == 1
    assert matches[0]["match_status"] == "strong_match"
    assert "capacity_mismatch_softened_by_name_location" in matches[0]["match_reasons"]
    assert "capacity_mismatch_penalty" in matches[0]["match_reasons"]
    assert matches[0]["matched_project_id"] == "tracker:north-east-data"


def test_unmatched_direct_load_rows_write_queue_derived_projects(tmp_path: Path):
    projects = tmp_path / "projects.csv"
    queues = tmp_path / "queue_records.csv"
    matches_output = tmp_path / "queue_project_matches.csv"
    loader_output = tmp_path / "queues.csv"
    queue_projects_output = tmp_path / "queue_projects.csv"
    _write_csv(
        projects,
        [
            {
                "project_id": "tracker:known-campus",
                "name": "Known Campus",
                "owner": "Known Owner LLC",
                "operator": "Known Owner LLC",
                "county": "Albany",
                "state": "NY",
                "capacity_mw": "50",
            }
        ],
    )
    _write_csv(
        queues,
        [
            {
                "source_id": "nyiso-interconnection-queue",
                "source_uri": "https://example.com/nyiso.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "queue-hash-a",
                "local_path": "raw/nyiso.xlsx",
                "record_index": "120",
                "Project Name": "Hudson Valley Data Center",
                "County": "Rockland",
                "State": "NY",
                "Capacity (MW)": "50",
                "Status": "Study",
                "Requested In-Service Date": "2027-06-01",
                "Interconnection Customer": "Robert Delcalzo",
                "POI Location": "Rockland Substation",
            },
            {
                "source_id": "nyiso-interconnection-queue",
                "source_uri": "https://example.com/nyiso.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "queue-hash-b",
                "local_path": "raw/nyiso.xlsx",
                "record_index": "1696",
                "Project Name": "Hudson Valley Data Center",
                "County": "Rockland",
                "State": "NY",
                "Capacity (MW)": "50",
                "Status": "Study",
                "Requested In-Service Date": "2027-09-01",
                "Interconnection Customer": "Equity Suffern Developers, LLC",
                "POI Location": "Rockland Substation",
            },
        ],
    )

    summary = match_data_center_queues_to_projects(
        queue_rows_csv=queues,
        projects_csv=projects,
        matches_output=matches_output,
        queues_output=loader_output,
        queue_projects_output=queue_projects_output,
    )

    queue_projects = _read_csv(queue_projects_output)
    loader_rows = _read_csv(loader_output)
    assert summary.unmatched_rows == 2
    assert summary.queue_derived_projects == 1
    assert summary.queue_derived_queue_rows == 2
    assert summary.loader_queue_rows == 2
    assert queue_projects[0]["project_id"].startswith("queue-project:")
    assert queue_projects[0]["name"] == "Hudson Valley Data Center"
    assert queue_projects[0]["source_type"] == "grid_interconnection_queue"
    assert queue_projects[0]["tracker_status"] == "queue_derived_direct_load"
    assert queue_projects[0]["owner"] == "Robert Delcalzo|Equity Suffern Developers, LLC"
    assert {row["project_id"] for row in loader_rows} == {queue_projects[0]["project_id"]}


def test_unmatched_supporting_generation_rows_write_queue_derived_power_projects(
    tmp_path: Path,
):
    projects = tmp_path / "projects.csv"
    queues = tmp_path / "queue_records.csv"
    matches_output = tmp_path / "queue_project_matches.csv"
    loader_output = tmp_path / "queues.csv"
    queue_projects_output = tmp_path / "queue_projects.csv"
    _write_csv(
        projects,
        [
            {
                "project_id": "tracker:known-campus",
                "name": "Known Campus",
                "owner": "Known Owner LLC",
                "operator": "Known Owner LLC",
                "county": "Albany",
                "state": "NY",
                "capacity_mw": "50",
            }
        ],
    )
    _write_csv(
        queues,
        [
            {
                "source_id": "miso-eras-interconnection-requests",
                "source_uri": "https://example.com/miso.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "miso-hash-a",
                "local_path": "raw/miso.xlsx",
                "record_index": "40",
                "Project Number": "E0042",
                "Project Name": "Combined Cycle",
                "County": "Jasper",
                "State": "IN",
                "Capacity (MW)": "2739.8",
                "Status": "Active",
                "In-Service Date": "2028-08-01T00:00:00",
                "Interconnection Customer": "Northern Indiana Public Services Company LLC",
                "POI Name": "Schahfer Gen Sta",
                "Non-Confidential Summary": (
                    "The Schahfer Project will address load growth that includes "
                    "hyperscale data centers."
                ),
            },
            {
                "source_id": "miso-eras-interconnection-requests",
                "source_uri": "https://example.com/miso.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "miso-hash-b",
                "local_path": "raw/miso.xlsx",
                "record_index": "41",
                "Project Number": "E0043",
                "Project Name": "Combined Cycle",
                "County": "Richland",
                "State": "LA",
                "Capacity (MW)": "1531.4",
                "Status": "Active",
                "In-Service Date": "2028-08-04T00:00:00",
                "Interconnection Customer": "Entergy Louisiana, LLC",
                "POI Name": "West Fork Creek 230kV Substation",
                "Non-Confidential Summary": (
                    "The resource adequacy need is being driven by a hyperscale data center."
                ),
            },
            {
                "source_id": "miso-eras-interconnection-requests",
                "source_uri": "https://example.com/miso.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "miso-hash-c",
                "local_path": "raw/miso.xlsx",
                "record_index": "42",
                "Project Number": "E0044",
                "Project Name": "Combined Cycle",
                "County": "Richland",
                "State": "LA",
                "Capacity (MW)": "1531.4",
                "Status": "Active",
                "In-Service Date": "2028-08-04T00:00:00",
                "Interconnection Customer": "Entergy Louisiana, LLC",
                "POI Name": "West Fork Creek 230kV Substation",
                "Non-Confidential Summary": (
                    "The resource adequacy need is being driven by a hyperscale data center."
                ),
            },
        ],
    )

    summary = match_data_center_queues_to_projects(
        queue_rows_csv=queues,
        projects_csv=projects,
        matches_output=matches_output,
        queues_output=loader_output,
        queue_projects_output=queue_projects_output,
    )

    queue_projects = _read_csv(queue_projects_output)
    loader_rows = _read_csv(loader_output)
    assert summary.unmatched_rows == 3
    assert summary.queue_derived_projects == 2
    assert summary.queue_derived_queue_rows == 3
    assert summary.loader_queue_rows == 3
    assert {row["asset_type"] for row in queue_projects} == {"power_generation"}
    assert {row["capacity_basis"] for row in queue_projects} == {"generation_queue_requested_mw"}
    assert {row["tracker_status"] for row in queue_projects} == {
        "queue_derived_supporting_generation"
    }
    assert {row["project_id"] for row in loader_rows} == {
        row["project_id"] for row in queue_projects
    }
