from __future__ import annotations

import csv
from datetime import date
from typing import TYPE_CHECKING

from bubble.graph.client import BubbleGraphClient, InMemoryStore
from bubble.ingestion.physical import (
    assess_physical_evidence,
    ingest_physical_evidence,
    load_physical_evidence,
)
from bubble.models.physical import PhysicalRiskLevel

if TYPE_CHECKING:
    from pathlib import Path


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    assert rows
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_fixture(directory: Path) -> None:
    common_source = {
        "source_confidence": 0.91,
        "human_review_status": "approved",
    }
    _write_csv(
        directory / "projects.csv",
        [
            {
                "project_id": "campus-1",
                "name": "Evidence Campus 1",
                "asset_type": "data_center_campus",
                "capacity_mw": 180,
                "it_load_mw": 150,
                "construction_status": "permitted",
                "announced_in_service_date": "2027-06-30",
                "major_equipment": '{"power":"gas turbines"}',
                "source_uri": "tracker:campus-1",
                "source_type": "project_tracker",
                **common_source,
            }
        ],
    )
    _write_csv(
        directory / "queues.csv",
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
    _write_csv(
        directory / "permits.csv",
        [
            {
                "project_id": "campus-1",
                "permit_id": "AIR-900",
                "authority": "State DEQ",
                "permit_type": "air",
                "status": "contested",
                "capacity_mw": 150,
                "related_generation": "true",
                "public_opposition": "true",
                "source_uri": "deq:air:AIR-900",
                "source_type": "state_deq",
                **common_source,
            }
        ],
    )
    _write_csv(
        directory / "equipment.csv",
        [
            {
                "project_id": "campus-1",
                "equipment_type": "transformer",
                "status": "delayed",
                "vendor": "Transformer Vendor",
                "lead_time_months": 24,
                "source_uri": "company-ir:transformer-delay",
                "source_type": "company_ir",
                **common_source,
            }
        ],
    )
    _write_csv(
        directory / "observations.csv",
        [
            {
                "project_id": "campus-1",
                "observed_on": "2026-12-31",
                "construction_status": "permitted",
                "progress_pct": 0.05,
                "visible_indicators": "graded pad|no substation",
                "source_uri": "satellite:campus-1:2026-12-31",
                "source_type": "satellite",
                **common_source,
            }
        ],
    )


def _memory_graph() -> BubbleGraphClient:
    client = BubbleGraphClient.__new__(BubbleGraphClient)
    client._mode = "memory"
    client._neo_driver = None
    client._memory = InMemoryStore()
    return client


def test_load_physical_evidence_from_csvs_and_score_assessment(tmp_path: Path):
    _write_fixture(tmp_path)

    batch = load_physical_evidence(tmp_path)
    assessments = assess_physical_evidence(batch, as_of=date(2026, 12, 31))

    assert len(batch.assets) == 1
    assert batch.assets[0].source_project_id == "campus-1"
    assert batch.queue_items[0].provenance.source_uri == "ercot:queue:Q-900"
    assert len(assessments) == 1
    assert assessments[0].project_ref == "campus-1"
    assert assessments[0].score == 0.95
    assert assessments[0].risk_level == PhysicalRiskLevel.CRITICAL
    assert assessments[0].evidence_tier == "corroborated_estimate"
    assert assessments[0].high_confidence_eligible is True


def test_load_physical_evidence_includes_optional_queue_derived_projects(tmp_path: Path):
    _write_fixture(tmp_path)
    _write_csv(
        tmp_path / "queue_projects.csv",
        [
            {
                "project_id": "queue-project:abc",
                "name": "Queue-Derived Campus",
                "asset_type": "data_center_campus",
                "county": "Rockland",
                "state": "NY",
                "jurisdiction": "Rockland, NY",
                "capacity_mw": 50,
                "construction_status": "announced",
                "source_uri": "https://example.com/nyiso.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "a" * 64,
                "source_confidence": 0.72,
                "human_review_status": "pending",
            }
        ],
    )

    batch = load_physical_evidence(tmp_path)

    assert len(batch.assets) == 2
    assert {asset.source_project_id for asset in batch.assets} == {
        "campus-1",
        "queue-project:abc",
    }
    assert batch.assets[1].provenance.source_type.value == "grid_interconnection_queue"


def test_ingest_physical_evidence_merges_records_and_assessments(tmp_path: Path):
    _write_fixture(tmp_path)
    graph = _memory_graph()

    summary = ingest_physical_evidence(tmp_path, graph=graph, as_of=date(2026, 12, 31))
    labels = [node["label"] for node in graph.query_nodes()]

    assert summary["assets"] == 1
    assert summary["queue_items"] == 1
    assert summary["permits"] == 1
    assert summary["equipment"] == 1
    assert summary["observations"] == 1
    assert summary["assessments"] == 1
    assert summary["high_confidence_assessments"] == 1
    assert "PhysicalAsset" in labels
    assert "PhysicalRiskAssessment" in labels
    assert graph._memory is not None
    assert graph._memory.relationships[0]["relationship_type"] == "HAS_PHYSICAL_RISK_ASSESSMENT"
