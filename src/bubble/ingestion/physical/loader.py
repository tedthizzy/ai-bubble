"""
CSV loader for physical deliverability evidence.

Expected files in a directory:
- projects.csv
- queue_projects.csv (optional queue-derived direct load projects)
- queues.csv
- permits.csv
- equipment.csv
- observations.csv

Every row must carry source_uri. Optional row fields source_type, source_confidence,
human_review_status, page_or_section, and content_hash override provenance defaults.
"""

from __future__ import annotations

import csv
import json
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from bubble.analysis.physical_risk import PhysicalRiskEngine
from bubble.graph.client import get_graph_client
from bubble.models.base import HumanReviewStatus, Provenance, SourceType
from bubble.models.physical import (
    AssetType,
    ConstructionObservation,
    ConstructionStatus,
    EquipmentRecord,
    EquipmentStatus,
    EquipmentType,
    GridRegion,
    InterconnectionQueueItem,
    InterconnectionStatus,
    PermitDecisionStatus,
    PermitRecord,
    PhysicalAsset,
    PhysicalRiskAssessment,
)
from bubble.quality.source_invariants import assert_source_row

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from bubble.graph.client import BubbleGraphClient


@dataclass(frozen=True)
class PhysicalEvidenceBatch:
    """Loaded physical evidence grouped by project/source id."""

    assets: list[PhysicalAsset]
    queue_items: list[InterconnectionQueueItem]
    permits: list[PermitRecord]
    equipment: list[EquipmentRecord]
    observations: list[ConstructionObservation]

    def asset_by_project_id(self) -> dict[str, PhysicalAsset]:
        return {
            asset.source_project_id: asset
            for asset in self.assets
            if asset.source_project_id is not None
        }

    def queue_items_for(self, project_id: str) -> list[InterconnectionQueueItem]:
        return [item for item in self.queue_items if item.project_ref == project_id]

    def permits_for(self, project_id: str) -> list[PermitRecord]:
        return [item for item in self.permits if item.project_ref == project_id]

    def equipment_for(self, project_id: str) -> list[EquipmentRecord]:
        return [item for item in self.equipment if item.project_ref == project_id]

    def observations_for(self, project_id: str) -> list[ConstructionObservation]:
        return [item for item in self.observations if item.project_ref == project_id]


def load_physical_evidence(directory: str | Path) -> PhysicalEvidenceBatch:
    """Load source-backed physical evidence CSVs from a directory."""
    base = Path(directory)
    project_rows = [
        *_read_csv(base / "projects.csv", required=True),
        *_read_csv(base / "queue_projects.csv", required=False),
    ]
    assets = [_asset_from_row(row) for row in project_rows]

    return PhysicalEvidenceBatch(
        assets=assets,
        queue_items=[
            _queue_item_from_row(row) for row in _read_csv(base / "queues.csv", required=False)
        ],
        permits=[_permit_from_row(row) for row in _read_csv(base / "permits.csv", required=False)],
        equipment=[
            _equipment_from_row(row) for row in _read_csv(base / "equipment.csv", required=False)
        ],
        observations=[
            _observation_from_row(row)
            for row in _read_csv(base / "observations.csv", required=False)
        ],
    )


def assess_physical_evidence(
    batch: PhysicalEvidenceBatch,
    *,
    engine: PhysicalRiskEngine | None = None,
    as_of: date | None = None,
    max_workers: int | None = None,
) -> list[PhysicalRiskAssessment]:
    """Run physical-risk scoring for every project with a source_project_id."""
    risk_engine = engine or PhysicalRiskEngine()
    assets = list(batch.asset_by_project_id().items())
    workers = _assessment_workers(max_workers, len(assets))
    queue_by_project = _records_by_project(batch.queue_items)
    permit_by_project = _records_by_project(batch.permits)
    equipment_by_project = _records_by_project(batch.equipment)
    observation_by_project = _records_by_project(batch.observations)
    if workers == 1:
        return [
            _assess_asset(
                risk_engine,
                project_id,
                asset,
                queue_by_project,
                permit_by_project,
                equipment_by_project,
                observation_by_project,
                as_of,
            )
            for project_id, asset in assets
        ]

    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(
            executor.map(
                lambda item: _assess_asset(
                    risk_engine,
                    item[0],
                    item[1],
                    queue_by_project,
                    permit_by_project,
                    equipment_by_project,
                    observation_by_project,
                    as_of,
                ),
                assets,
            )
        )


def ingest_physical_evidence(
    directory: str | Path,
    *,
    graph: BubbleGraphClient | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    """
    Load physical evidence, score it, and merge records into the graph.

    This works in in-memory mode and Neo4j mode through BubbleGraphClient.merge_node.
    """
    graph_client = graph or get_graph_client()
    batch = load_physical_evidence(directory)
    assessments = assess_physical_evidence(batch, as_of=as_of)
    asset_node_ids = {
        asset.source_project_id: graph_client.merge_node("PhysicalAsset", asset)
        for asset in batch.assets
    }

    record_counts = {
        "queue_items": _merge_records(graph_client, "InterconnectionQueueItem", batch.queue_items),
        "permits": _merge_records(graph_client, "PermitRecord", batch.permits),
        "equipment": _merge_records(graph_client, "EquipmentRecord", batch.equipment),
        "observations": _merge_records(graph_client, "ConstructionObservation", batch.observations),
    }

    assessment_count = 0
    for assessment in assessments:
        assessment_id = graph_client.merge_node("PhysicalRiskAssessment", assessment)
        asset_id = str(assessment.asset_ref or "")
        if asset_id:
            graph_client.add_relationship(asset_id, assessment_id, "HAS_PHYSICAL_RISK_ASSESSMENT")
        assessment_count += 1

    return {
        "assets": len(batch.assets),
        "asset_node_ids": asset_node_ids,
        **record_counts,
        "assessments": assessment_count,
        "high_confidence_assessments": sum(
            assessment.high_confidence_eligible for assessment in assessments
        ),
        "critical_or_high_risk_assessments": sum(
            assessment.risk_level.value in {"critical", "high"} for assessment in assessments
        ),
    }


def _assess_asset(
    engine: PhysicalRiskEngine,
    project_id: str,
    asset: PhysicalAsset,
    queue_by_project: Mapping[str, list[InterconnectionQueueItem]],
    permit_by_project: Mapping[str, list[PermitRecord]],
    equipment_by_project: Mapping[str, list[EquipmentRecord]],
    observation_by_project: Mapping[str, list[ConstructionObservation]],
    as_of: date | None,
) -> PhysicalRiskAssessment:
    return engine.assess(
        asset,
        queue_items=queue_by_project.get(project_id, []),
        permits=permit_by_project.get(project_id, []),
        equipment=equipment_by_project.get(project_id, []),
        observations=observation_by_project.get(project_id, []),
        as_of=as_of,
    )


def _assessment_workers(max_workers: int | None, asset_count: int) -> int:
    if asset_count <= 1:
        return 1
    if max_workers is not None:
        return min(max(1, max_workers), asset_count)
    return min(32, max(1, os.cpu_count() or 1), asset_count)


def _records_by_project[
    T: InterconnectionQueueItem | PermitRecord | EquipmentRecord | ConstructionObservation,
](records: Sequence[T]) -> dict[str, list[T]]:
    grouped: dict[str, list[T]] = {}
    for record in records:
        if not record.project_ref:
            continue
        grouped.setdefault(str(record.project_ref), []).append(record)
    return grouped


def _read_csv(path: Path, *, required: bool) -> list[dict[str, str]]:
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return []
    with path.open(newline="") as f:
        return [
            {key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(f)
        ]


def _asset_from_row(row: dict[str, str]) -> PhysicalAsset:
    project_id = _required(row, "project_id")
    return PhysicalAsset(
        source_project_id=project_id,
        name=_required(row, "name"),
        asset_type=_enum_value(AssetType, row.get("asset_type"), AssetType.DATA_CENTER_CAMPUS),
        location_lat=_optional_float(row.get("location_lat")),
        location_lon=_optional_float(row.get("location_lon")),
        address=_optional_str(row.get("address")),
        jurisdiction=_optional_str(row.get("jurisdiction")),
        capacity_mw=_optional_float(row.get("capacity_mw")),
        it_load_mw=_optional_float(row.get("it_load_mw")),
        owner=_optional_str(row.get("owner")),
        operator=_optional_str(row.get("operator")),
        tenants=_split(row.get("tenants")),
        permit_status=_optional_str(row.get("permit_status")),
        construction_status=_enum_value(
            ConstructionStatus,
            row.get("construction_status"),
            ConstructionStatus.ANNOUNCED,
        ),
        announced_in_service_date=_optional_str(row.get("announced_in_service_date")),
        actual_in_service_date=_optional_str(row.get("actual_in_service_date")),
        major_equipment=_json_dict(row.get("major_equipment")),
        equipment_lead_time_months=_optional_int(row.get("equipment_lead_time_months")),
        linked_deals=_split(row.get("linked_deals")),
        provenance=_provenance_from_row(
            row,
            default_source_type=SourceType.PROJECT_TRACKER,
            identity=f"project:{project_id}",
        ),
        confidence=_optional_float(row.get("confidence")) or 0.85,
    )


def _queue_item_from_row(row: dict[str, str]) -> InterconnectionQueueItem:
    queue_id = _required(row, "queue_id")
    return InterconnectionQueueItem(
        project_ref=_required(row, "project_id"),
        queue_id=queue_id,
        region=_enum_value(GridRegion, row.get("region"), GridRegion.UNKNOWN),
        status=_enum_value(
            InterconnectionStatus,
            row.get("status"),
            InterconnectionStatus.UNKNOWN,
        ),
        requested_mw=_optional_float(row.get("requested_mw")),
        firm_service_mw=_optional_float(row.get("firm_service_mw")),
        requested_in_service_date=_optional_date(row.get("requested_in_service_date")),
        expected_in_service_date=_optional_date(row.get("expected_in_service_date")),
        delay_months=_optional_int(row.get("delay_months")),
        network_upgrade_cost_usd=_optional_float(row.get("network_upgrade_cost_usd")),
        study_phase=_optional_str(row.get("study_phase")),
        notes=_optional_str(row.get("notes")),
        provenance=_provenance_from_row(
            row,
            default_source_type=SourceType.GRID_QUEUE,
            identity=f"queue:{queue_id}",
        ),
        confidence=_optional_float(row.get("confidence")) or 0.85,
    )


def _permit_from_row(row: dict[str, str]) -> PermitRecord:
    permit_id = _required(row, "permit_id")
    return PermitRecord(
        project_ref=_required(row, "project_id"),
        permit_id=permit_id,
        authority=_required(row, "authority"),
        permit_type=_required(row, "permit_type"),
        status=_enum_value(
            PermitDecisionStatus,
            row.get("status"),
            PermitDecisionStatus.UNKNOWN,
        ),
        application_date=_optional_date(row.get("application_date")),
        issued_date=_optional_date(row.get("issued_date")),
        capacity_mw=_optional_float(row.get("capacity_mw")),
        related_generation=_bool(row.get("related_generation")),
        public_opposition=_bool(row.get("public_opposition")),
        notes=_optional_str(row.get("notes")),
        provenance=_provenance_from_row(
            row,
            default_source_type=SourceType.STATE_DEQ,
            identity=f"permit:{permit_id}",
        ),
        confidence=_optional_float(row.get("confidence")) or 0.85,
    )


def _equipment_from_row(row: dict[str, str]) -> EquipmentRecord:
    equipment_key = ":".join(
        [
            _required(row, "project_id"),
            row.get("equipment_type") or "unknown",
            row.get("vendor") or "unknown",
        ]
    )
    return EquipmentRecord(
        project_ref=_required(row, "project_id"),
        equipment_type=_enum_value(EquipmentType, row.get("equipment_type"), EquipmentType.OTHER),
        status=_enum_value(EquipmentStatus, row.get("status"), EquipmentStatus.UNKNOWN),
        vendor=_optional_str(row.get("vendor")),
        capacity_mw=_optional_float(row.get("capacity_mw")),
        ordered_date=_optional_date(row.get("ordered_date")),
        expected_delivery_date=_optional_date(row.get("expected_delivery_date")),
        actual_delivery_date=_optional_date(row.get("actual_delivery_date")),
        lead_time_months=_optional_int(row.get("lead_time_months")),
        notes=_optional_str(row.get("notes")),
        provenance=_provenance_from_row(
            row,
            default_source_type=SourceType.COMPANY_IR,
            identity=f"equipment:{equipment_key}",
        ),
        confidence=_optional_float(row.get("confidence")) or 0.85,
    )


def _observation_from_row(row: dict[str, str]) -> ConstructionObservation:
    project_id = _required(row, "project_id")
    observed_on = _optional_date(row.get("observed_on"))
    if observed_on is None:
        raise ValueError(f"observations.csv row for {project_id} requires observed_on")
    return ConstructionObservation(
        project_ref=project_id,
        observed_on=observed_on,
        construction_status=_enum_value(
            ConstructionStatus,
            row.get("construction_status"),
            ConstructionStatus.ANNOUNCED,
        ),
        progress_pct=_optional_float(row.get("progress_pct")),
        visible_indicators=_split(row.get("visible_indicators")),
        notes=_optional_str(row.get("notes")),
        provenance=_provenance_from_row(
            row,
            default_source_type=SourceType.SATELLITE,
            identity=f"observation:{project_id}:{observed_on.isoformat()}",
        ),
        confidence=_optional_float(row.get("confidence")) or 0.85,
    )


def _merge_records(
    graph: BubbleGraphClient,
    label: str,
    records: Sequence[
        InterconnectionQueueItem | PermitRecord | EquipmentRecord | ConstructionObservation
    ],
) -> int:
    for record in records:
        graph.merge_node(label, record)
    return len(records)


def _provenance_from_row(
    row: dict[str, str],
    *,
    default_source_type: SourceType,
    identity: str,
) -> Provenance:
    assert_source_row(row, context=identity)
    source_uri = _required(row, "source_uri")
    source_type = _enum_value(SourceType, row.get("source_type"), default_source_type)
    raw_confidence = row.get("source_confidence") or row.get("provenance_confidence")
    confidence = _optional_float(raw_confidence) or 0.85
    content_hash = row.get("content_hash") or Provenance.compute_content_hash(
        json.dumps({"identity": identity, "row": row}, sort_keys=True)
    )
    retrieved_at = _optional_datetime(row.get("retrieved_at"))
    return Provenance(
        source_uri=source_uri,
        source_type=source_type,
        retrieved_at=retrieved_at or datetime.now(UTC),
        page_or_section=_optional_str(row.get("page_or_section")),
        confidence=confidence,
        human_review_status=_enum_value(
            HumanReviewStatus,
            row.get("human_review_status"),
            HumanReviewStatus.PENDING,
        ),
        content_hash=content_hash,
    )


def _required(row: dict[str, str], key: str) -> str:
    value = row.get(key)
    if not value:
        raise ValueError(f"CSV row missing required field: {key}")
    return value


def _optional_str(value: str | None) -> str | None:
    return value if value else None


def _optional_float(value: str | None) -> float | None:
    if not value:
        return None
    return float(value.replace(",", "").replace("$", ""))


def _optional_int(value: str | None) -> int | None:
    parsed = _optional_float(value)
    return int(parsed) if parsed is not None else None


def _optional_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _optional_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _bool(value: str | None) -> bool:
    if not value:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _split(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.replace(";", "|").split("|") if part.strip()]


def _json_dict(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object")
    return cast("dict[str, Any]", parsed)


def _enum_value[EnumT: StrEnum](enum_cls: type[EnumT], value: str | None, default: EnumT) -> EnumT:
    if not value:
        return default
    normalized = value.strip().lower()
    try:
        return enum_cls(normalized)
    except ValueError:
        by_name = enum_cls.__members__.get(value.strip().upper())
        if by_name is not None:
            return by_name
        return default
