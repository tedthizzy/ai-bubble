"""Roll up project-level physical deliverability risk assessments."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bubble.ingestion.physical.loader import (
    PhysicalEvidenceBatch,
    assess_physical_evidence,
    load_physical_evidence,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bubble.models.physical import (
        ConstructionObservation,
        EquipmentRecord,
        InterconnectionQueueItem,
        PermitRecord,
        PhysicalAsset,
        PhysicalRiskAssessment,
    )


@dataclass(frozen=True)
class PhysicalRiskSummary:
    """Serializable rollup of source-backed physical risk scoring."""

    assets_assessed: int
    queue_items: int
    permits: int
    equipment_records: int
    observations: int
    assets_with_queue_evidence: int
    assets_with_permit_evidence: int
    assets_with_equipment_evidence: int
    assets_with_observation_evidence: int
    assets_with_any_physical_evidence: int
    project_linked_queue_capacity_mw: float
    risk_level_counts: dict[str, int]
    critical_or_high_risk_assessments: int
    high_confidence_assessments: int
    top_blockers: list[dict[str, Any]]
    top_risk_projects: list[dict[str, Any]]
    top_source_backed_risk_projects: list[dict[str, Any]]
    top_evidence_gap_projects: list[dict[str, Any]]
    workers: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_physical_risk_summary(
    data_dirs: list[str] | None = None,
    *,
    max_workers: int | None = None,
    top_limit: int = 15,
) -> PhysicalRiskSummary:
    """Load project-linked physical evidence and aggregate deterministic risk scores."""

    batch = _load_physical_batches(data_dirs or ["data"])
    assessments = assess_physical_evidence(batch, max_workers=max_workers)
    workers = _resolved_workers(max_workers, len(batch.assets))
    queue_project_refs = _project_refs(batch.queue_items)
    permit_project_refs = _project_refs(batch.permits)
    equipment_project_refs = _project_refs(batch.equipment)
    observation_project_refs = _project_refs(batch.observations)
    any_evidence_project_refs = (
        queue_project_refs | permit_project_refs | equipment_project_refs | observation_project_refs
    )
    queue_capacity_by_project = _queue_capacity_by_project(batch.queue_items)
    risk_counts = Counter(assessment.risk_level.value for assessment in assessments)
    top_risk_projects = _top_risk_projects(
        batch.assets,
        assessments,
        queue_capacity_by_project,
        top_limit=top_limit,
    )

    return PhysicalRiskSummary(
        assets_assessed=len(assessments),
        queue_items=len(batch.queue_items),
        permits=len(batch.permits),
        equipment_records=len(batch.equipment),
        observations=len(batch.observations),
        assets_with_queue_evidence=len(queue_project_refs),
        assets_with_permit_evidence=len(permit_project_refs),
        assets_with_equipment_evidence=len(equipment_project_refs),
        assets_with_observation_evidence=len(observation_project_refs),
        assets_with_any_physical_evidence=len(any_evidence_project_refs),
        project_linked_queue_capacity_mw=round(sum(queue_capacity_by_project.values()), 3),
        risk_level_counts=dict(sorted(risk_counts.items())),
        critical_or_high_risk_assessments=sum(
            assessment.risk_level.value in {"critical", "high"} for assessment in assessments
        ),
        high_confidence_assessments=sum(
            assessment.high_confidence_eligible for assessment in assessments
        ),
        top_blockers=_top_blockers(assessments, top_limit=top_limit),
        top_risk_projects=top_risk_projects,
        top_source_backed_risk_projects=_top_risk_projects(
            batch.assets,
            [assessment for assessment in assessments if assessment.evidence_source_count > 0],
            queue_capacity_by_project,
            top_limit=top_limit,
        ),
        top_evidence_gap_projects=[
            project for project in top_risk_projects if project["evidence_source_count"] == 0
        ][:top_limit],
        workers=workers,
    )


def write_physical_risk_summary(summary: PhysicalRiskSummary, path: str | Path) -> Path:
    """Write a physical risk summary JSON artifact."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    return output


def _load_physical_batches(data_dirs: list[str]) -> PhysicalEvidenceBatch:
    assets: list[PhysicalAsset] = []
    queue_items: list[InterconnectionQueueItem] = []
    permits: list[PermitRecord] = []
    equipment: list[EquipmentRecord] = []
    observations: list[ConstructionObservation] = []

    for root in data_dirs:
        directory = Path(root) / "physical"
        if not (directory / "projects.csv").exists():
            continue
        batch = load_physical_evidence(directory)
        assets.extend(batch.assets)
        queue_items.extend(batch.queue_items)
        permits.extend(batch.permits)
        equipment.extend(batch.equipment)
        observations.extend(batch.observations)

    return PhysicalEvidenceBatch(
        assets=assets,
        queue_items=queue_items,
        permits=permits,
        equipment=equipment,
        observations=observations,
    )


def _project_refs(
    records: Sequence[
        InterconnectionQueueItem | PermitRecord | EquipmentRecord | ConstructionObservation
    ],
) -> set[str]:
    return {str(record.project_ref) for record in records if record.project_ref}


def _queue_capacity_by_project(queue_items: list[InterconnectionQueueItem]) -> dict[str, float]:
    capacity_by_project: defaultdict[str, float] = defaultdict(float)
    for item in queue_items:
        if item.project_ref and item.requested_mw:
            capacity_by_project[str(item.project_ref)] += item.requested_mw
    return dict(capacity_by_project)


def _top_blockers(
    assessments: list[PhysicalRiskAssessment],
    *,
    top_limit: int,
) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for assessment in assessments:
        counts.update(set(assessment.blockers))
    return [
        {"blocker": blocker, "asset_count": count}
        for blocker, count in counts.most_common(top_limit)
    ]


def _top_risk_projects(
    assets: list[PhysicalAsset],
    assessments: list[PhysicalRiskAssessment],
    queue_capacity_by_project: dict[str, float],
    *,
    top_limit: int,
) -> list[dict[str, Any]]:
    asset_by_project_id = {
        asset.source_project_id: asset for asset in assets if asset.source_project_id
    }
    ranked = sorted(
        assessments,
        key=lambda assessment: (
            assessment.score,
            queue_capacity_by_project.get(str(assessment.project_ref or ""), 0.0),
            assessment.evidence_source_count,
        ),
        reverse=True,
    )
    rows: list[dict[str, Any]] = []
    for assessment in ranked[:top_limit]:
        project_id = str(assessment.project_ref or "")
        asset = asset_by_project_id.get(project_id)
        rows.append(
            {
                "project_id": project_id,
                "asset_name": asset.name if asset else "",
                "owner": str(asset.owner or "") if asset else "",
                "capacity_mw": asset.capacity_mw if asset else None,
                "it_load_mw": asset.it_load_mw if asset else None,
                "queue_requested_mw": round(queue_capacity_by_project.get(project_id, 0.0), 3),
                "risk_level": assessment.risk_level.value,
                "score": assessment.score,
                "expected_delay_months": assessment.expected_delay_months,
                "evidence_tier": assessment.evidence_tier,
                "evidence_source_count": assessment.evidence_source_count,
                "high_confidence_eligible": assessment.high_confidence_eligible,
                "blockers": assessment.blockers[:5],
                "supporting_evidence": assessment.supporting_evidence[:5],
            }
        )
    return rows


def _resolved_workers(max_workers: int | None, asset_count: int) -> int:
    if asset_count <= 1:
        return 1
    if max_workers is not None:
        return min(max(1, max_workers), asset_count)
    return min(32, asset_count)
