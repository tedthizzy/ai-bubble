from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from bubble.ingestion.physical.record_matching import (
    _ProjectCandidate,
    _score_project_match,
    _tokens,
    match_physical_records_to_projects,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_record_match_does_not_double_count_name_as_owner_when_owner_absent() -> None:
    """A facility name overlapping the project name must not ALSO be credited as
    separate 'facility_owner_overlap'.

    When a project has no owner/operator, ``party_tokens`` falls back to the
    project name, so probing the facility-name tokens against ``party_tokens``
    re-scores the exact same name overlap a second time (up to +0.28) and adds a
    misleading owner-overlap reason. Owner overlap must require owner tokens that
    are *distinct* from the project name.
    """

    project = _ProjectCandidate.from_row(
        {
            "project_id": "tracker:google-cb",
            "name": "Google Data Center",
            # owner/operator intentionally omitted -> party_text falls back to name
            "city": "Council Bluffs",
            "county": "Pottawattamie",
            "state": "IA",
        }
    )

    confidence, reasons = _score_project_match(
        row_name_tokens=_tokens("Google Data Center"),
        row_city="",
        row_county="",
        project=project,
    )

    # No independent owner signal exists, so no owner-overlap reason may appear.
    assert not any("owner_overlap" in reason for reason in reasons)
    # Name overlap (0.48) + state (0.06); must NOT include the phantom +0.28.
    assert confidence < 0.6


def test_record_match_still_credits_distinct_owner_overlap() -> None:
    """A facility name that overlaps a project's *distinct* owner identity (a
    token not present in the project name) must still be credited as owner
    overlap — the fix only removes the double-count, not legitimate signal."""

    project = _ProjectCandidate.from_row(
        {
            "project_id": "tracker:qts-den1",
            "name": "DEN1",
            "owner": "QTS Realty",
            "operator": "QTS Realty",
            "state": "CO",
        }
    )

    _, reasons = _score_project_match(
        row_name_tokens=_tokens("QTS DEN1"),
        row_city="",
        row_county="",
        project=project,
    )

    assert any("owner_overlap" in reason for reason in reasons)


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


def test_physical_record_matching_writes_permit_and_equipment_loader_rows(tmp_path: Path) -> None:
    projects = tmp_path / "projects.csv"
    permits = tmp_path / "permit_records.csv"
    equipment = tmp_path / "equipment_records.csv"
    permit_matches = tmp_path / "permit_project_matches.csv"
    equipment_matches = tmp_path / "equipment_project_matches.csv"
    permits_output = tmp_path / "permits.csv"
    equipment_output = tmp_path / "equipment.csv"
    _write_csv(
        projects,
        [
            {
                "project_id": "tracker:qts-den1",
                "name": "QTS DEN1 Data Center",
                "owner": "QTS",
                "operator": "QTS",
                "city": "Aurora",
                "county": "Arapahoe",
                "state": "CO",
            },
            {
                "project_id": "tracker:equinix-great-oaks",
                "name": "Equinix Great Oaks Blvd Data Center",
                "owner": "Equinix",
                "operator": "Equinix",
                "city": "San Jose",
                "county": "Santa Clara",
                "state": "CA",
            },
        ],
    )
    _write_csv(
        permits,
        [
            {
                "PGM_SYS_ID": "AIR-QTS-1",
                "REGISTRY_ID": "1101",
                "FACILITY_NAME": "QTS AURORA LLC - QTS DEN1",
                "CITY": "AURORA",
                "COUNTY_NAME": "Arapahoe",
                "STATE": "CO",
                "AIR_POLLUTANT_CLASS_DESC": "Minor Emissions",
                "AIR_OPERATING_STATUS_DESC": "Operating",
                "CURRENT_HPV": "No Violation Identified",
                "source_id": "epa-icis-air",
                "source_uri": "https://example.com/icis.zip",
                "source_type": "epa",
                "content_hash": "permit-hash",
                "local_path": "raw/icis.zip",
                "record_index": "42",
                "document_id": "icis",
            },
            {
                "PGM_SYS_ID": "AIR-METAL",
                "FACILITY_NAME": "CUSTOM METAL SHOP",
                "CITY": "AURORA",
                "COUNTY_NAME": "Arapahoe",
                "STATE": "CO",
                "source_id": "epa-icis-air",
                "source_uri": "https://example.com/icis.zip",
                "source_type": "epa",
                "content_hash": "permit-hash",
                "local_path": "raw/icis.zip",
                "record_index": "43",
            },
        ],
    )
    _write_csv(
        equipment,
        [
            {
                "Plant ID": "62702",
                "Generator ID": "EQ14A",
                "Plant Name": "Equinix Great Oaks Blvd. Fuel Cell",
                "Plant State": "CA",
                "County": "Santa Clara",
                "Prime Mover Code": "FC",
                "Energy Source Code": "NG",
                "Status": "OP",
                "Nameplate Capacity (MW)": "4.0",
                "Operating Month": "1",
                "Operating Year": "2023",
                "source_id": "eia-860m",
                "source_uri": "https://example.com/eia.xlsx",
                "source_type": "eia",
                "content_hash": "equipment-hash",
                "local_path": "raw/eia.xlsx",
                "record_index": "9",
                "document_id": "eia",
            }
        ],
    )

    summary = match_physical_records_to_projects(
        permit_rows_csv=permits,
        equipment_rows_csv=equipment,
        projects_csv=projects,
        permit_matches_output=permit_matches,
        equipment_matches_output=equipment_matches,
        permits_output=permits_output,
        equipment_output=equipment_output,
        max_workers=4,
    )

    permit_loader_rows = _read_csv(permits_output)
    equipment_loader_rows = _read_csv(equipment_output)
    assert summary.permit_rows_scanned == 2
    assert summary.permit_candidate_rows == 1
    assert summary.permit_loader_rows == 1
    assert summary.equipment_rows_scanned == 1
    assert summary.equipment_candidate_rows == 1
    assert summary.equipment_loader_rows == 1
    assert permit_loader_rows[0]["project_id"] == "tracker:qts-den1"
    assert permit_loader_rows[0]["permit_id"] == "AIR-QTS-1"
    assert permit_loader_rows[0]["status"] == "issued"
    assert permit_loader_rows[0]["related_generation"] == "true"
    assert equipment_loader_rows[0]["project_id"] == "tracker:equinix-great-oaks"
    assert equipment_loader_rows[0]["equipment_type"] == "generator"
    assert equipment_loader_rows[0]["status"] == "installed"
    assert equipment_loader_rows[0]["capacity_mw"] == "4"
    assert _read_csv(permit_matches)[0]["match_status"] == "strong_match"
    assert _read_csv(equipment_matches)[0]["match_status"] == "strong_match"


def test_physical_record_matching_normalizes_full_state_names(tmp_path: Path) -> None:
    projects = tmp_path / "projects.csv"
    permits = tmp_path / "permit_records.csv"
    equipment = tmp_path / "equipment_records.csv"
    permit_matches = tmp_path / "permit_project_matches.csv"
    equipment_matches = tmp_path / "equipment_project_matches.csv"
    permits_output = tmp_path / "permits.csv"
    equipment_output = tmp_path / "equipment.csv"
    _write_csv(
        projects,
        [
            {
                "project_id": "tracker:ohio-campus",
                "name": "Buckeye AI Data Center",
                "owner": "Buckeye Compute LLC",
                "operator": "Buckeye Compute LLC",
                "city": "Columbus",
                "county": "Franklin County",
                "state": "Ohio",
            }
        ],
    )
    _write_csv(
        permits,
        [
            {
                "PGM_SYS_ID": "AIR-OH-1",
                "FACILITY_NAME": "BUCKEYE AI DATA CENTER",
                "CITY": "COLUMBUS",
                "COUNTY_NAME": "Franklin",
                "STATE": "OH",
                "AIR_OPERATING_STATUS_DESC": "Operating",
                "source_id": "epa-icis-air",
                "source_uri": "https://example.com/icis.zip",
                "source_type": "epa",
                "content_hash": "permit-hash",
                "local_path": "raw/icis.zip",
                "record_index": "1",
            }
        ],
    )
    _write_csv(equipment, [{"Plant Name": "not relevant", "source_uri": "https://example.com"}])

    summary = match_physical_records_to_projects(
        permit_rows_csv=permits,
        equipment_rows_csv=equipment,
        projects_csv=projects,
        permit_matches_output=permit_matches,
        equipment_matches_output=equipment_matches,
        permits_output=permits_output,
        equipment_output=equipment_output,
        max_workers=2,
    )

    assert summary.permit_loader_rows == 1
    assert _read_csv(permit_matches)[0]["matched_project_id"] == "tracker:ohio-campus"
    assert _read_csv(permit_matches)[0]["matched_project_state"] == "OH"
