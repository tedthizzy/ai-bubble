from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from bubble.ingestion.physical.construction_observations import (
    extract_construction_observations_from_projects,
)
from bubble.ingestion.physical.loader import load_physical_evidence

if TYPE_CHECKING:
    from pathlib import Path


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def test_extract_construction_observations_from_projects_writes_source_backed_rows(
    tmp_path: Path,
) -> None:
    projects = tmp_path / "projects.csv"
    observations = tmp_path / "observations.csv"
    _write_csv(
        projects,
        [
            {
                "project_id": "tracker:campus-1",
                "name": "Campus One",
                "asset_type": "data_center_campus",
                "construction_status": "under_construction",
                "permit_status": "permitted",
                "capacity_mw": "250",
                "announced_in_service_date": "2027-12",
                "tracker_status": "under-construction",
                "tracker_last_updated": "2026-02-05",
                "source_uri": "https://example.com/projects.csv",
                "source_type": "project_tracker",
                "retrieved_at": "2026-06-01T04:53:35+00:00",
                "source_confidence": "0.75",
                "human_review_status": "pending",
                "page_or_section": "raw/projects.csv#record_index=4",
                "content_hash": "c" * 64,
                "source_id": "tracker",
                "document_id": "projects",
                "local_path": "raw/projects.csv",
                "record_index": "4",
            },
            {
                "project_id": "tracker:campus-2",
                "name": "Campus Two",
                "construction_status": "in_service",
                "tracker_status": "operational",
                "source_uri": "https://example.com/projects.csv",
                "source_type": "project_tracker",
                "retrieved_at": "2026-06-01T04:53:35+00:00",
                "content_hash": "d" * 64,
            },
        ],
    )

    summary = extract_construction_observations_from_projects(
        projects,
        observations,
        max_workers=4,
    )

    rows = _read_csv(observations)
    assert summary.source_rows == 2
    assert summary.observations_written == 2
    assert summary.workers == 2
    assert summary.by_status == {"in_service": 1, "under_construction": 1}
    assert rows[0]["project_id"] == "tracker:campus-1"
    assert rows[0]["observed_on"] == "2026-02-05"
    assert rows[0]["construction_status"] == "under_construction"
    assert rows[0]["retrieved_at"] == "2026-06-01T04:53:35+00:00"
    assert "tracker_status:under-construction" in rows[0]["visible_indicators"]
    assert "capacity_mw:250" in rows[0]["visible_indicators"]
    assert rows[1]["observed_on"] == "2026-06-01"


def test_physical_loader_uses_observation_retrieval_timestamp(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "projects.csv",
        [
            {
                "project_id": "campus-1",
                "name": "Evidence Campus",
                "asset_type": "data_center_campus",
                "construction_status": "announced",
                "source_uri": "https://example.com/projects.csv",
                "source_type": "project_tracker",
                "content_hash": "a" * 64,
            }
        ],
    )
    _write_csv(
        tmp_path / "observations.csv",
        [
            {
                "project_id": "campus-1",
                "observed_on": "2026-02-05",
                "construction_status": "under_construction",
                "visible_indicators": "tracker_status:under-construction",
                "source_uri": "https://example.com/projects.csv",
                "source_type": "project_tracker",
                "retrieved_at": "2026-06-01T04:53:35+00:00",
                "content_hash": "b" * 64,
            }
        ],
    )

    batch = load_physical_evidence(tmp_path)

    assert len(batch.observations) == 1
    assert batch.observations[0].provenance.retrieved_at.isoformat() == (
        "2026-06-01T04:53:35+00:00"
    )
