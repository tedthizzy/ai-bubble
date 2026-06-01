from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from bubble.analysis.physical_risk_summary import build_physical_risk_summary

if TYPE_CHECKING:
    from pathlib import Path


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    assert rows
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_physical_risk_summary_rolls_up_project_linked_evidence(tmp_path: Path):
    physical_dir = tmp_path / "physical"
    common_source = {
        "source_confidence": 0.91,
        "human_review_status": "approved",
    }
    _write_csv(
        physical_dir / "projects.csv",
        [
            {
                "project_id": "campus-1",
                "name": "Evidence Campus",
                "asset_type": "data_center_campus",
                "capacity_mw": 180,
                "it_load_mw": 150,
                "construction_status": "permitted",
                "announced_in_service_date": "2027-06-30",
                "major_equipment": '{"power":"gas turbines"}',
                "source_uri": "tracker:campus-1",
                "source_type": "project_tracker",
                **common_source,
            },
            {
                "project_id": "campus-2",
                "name": "Gap Campus",
                "asset_type": "data_center_campus",
                "capacity_mw": 500,
                "construction_status": "announced",
                "source_uri": "tracker:campus-2",
                "source_type": "project_tracker",
                **common_source,
            },
        ],
    )
    _write_csv(
        physical_dir / "queues.csv",
        [
            {
                "project_id": "campus-1",
                "queue_id": "Q-900",
                "region": "ercot",
                "status": "study",
                "requested_mw": 150,
                "firm_service_mw": 0,
                "delay_months": 18,
                "source_uri": "ercot:queue:Q-900",
                "source_type": "grid_interconnection_queue",
                **common_source,
            }
        ],
    )

    summary = build_physical_risk_summary([str(tmp_path)], max_workers=4)

    assert summary.assets_assessed == 2
    assert summary.queue_items == 1
    assert summary.assets_with_queue_evidence == 1
    assert summary.assets_with_any_physical_evidence == 1
    assert summary.project_linked_queue_capacity_mw == 150
    assert summary.risk_level_counts == {"critical": 1, "moderate": 1}
    assert summary.top_source_backed_risk_projects[0]["project_id"] == "campus-1"
    assert summary.top_evidence_gap_projects[0]["project_id"] == "campus-2"
    assert summary.workers == 2
