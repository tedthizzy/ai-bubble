from datetime import date

from bubble.analysis.physical_risk import PhysicalRiskEngine
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
    PhysicalRiskLevel,
)


def _prov(
    source_type: SourceType,
    source_uri: str,
    *,
    confidence: float = 0.9,
    status: HumanReviewStatus = HumanReviewStatus.APPROVED,
) -> Provenance:
    return Provenance(
        source_uri=source_uri,
        source_type=source_type,
        confidence=confidence,
        human_review_status=status,
        content_hash=Provenance.compute_content_hash(source_uri),
    )


def _asset(**overrides) -> PhysicalAsset:
    defaults = {
        "name": "Test AI Campus",
        "asset_type": AssetType.DATA_CENTER_CAMPUS,
        "capacity_mw": 180.0,
        "it_load_mw": 150.0,
        "construction_status": ConstructionStatus.ANNOUNCED,
        "announced_in_service_date": "2027-06-30",
        "major_equipment": {"power": "gas turbines"},
        "provenance": _prov(SourceType.PROJECT_TRACKER, "tracker:test-campus"),
    }
    defaults.update(overrides)
    return PhysicalAsset(**defaults)


def test_physical_risk_scores_critical_when_power_permit_equipment_and_progress_fail():
    engine = PhysicalRiskEngine()
    asset = _asset()
    queue = InterconnectionQueueItem(
        queue_id="Q-1",
        region=GridRegion.ERCOT,
        status=InterconnectionStatus.STUDY,
        requested_mw=150,
        firm_service_mw=0,
        delay_months=18,
        provenance=_prov(SourceType.GRID_QUEUE, "ercot:queue:q-1"),
    )
    permit = PermitRecord(
        permit_id="AIR-1",
        authority="State DEQ",
        permit_type="air",
        status=PermitDecisionStatus.CONTESTED,
        related_generation=True,
        capacity_mw=150,
        public_opposition=True,
        provenance=_prov(SourceType.STATE_DEQ, "deq:air-1"),
    )
    transformer = EquipmentRecord(
        equipment_type=EquipmentType.TRANSFORMER,
        status=EquipmentStatus.DELAYED,
        lead_time_months=24,
        provenance=_prov(SourceType.COMPANY_IR, "company:transformer-delay"),
    )
    observation = ConstructionObservation(
        observed_on=date(2026, 12, 31),
        construction_status=ConstructionStatus.PERMITTED,
        progress_pct=0.05,
        provenance=_prov(SourceType.SATELLITE, "satellite:test-campus:2026-12-31"),
    )

    assessment = engine.assess(
        asset,
        queue_items=[queue],
        permits=[permit],
        equipment=[transformer],
        observations=[observation],
        as_of=date(2026, 12, 31),
    )

    assert assessment.score == 0.95
    assert assessment.risk_level == PhysicalRiskLevel.CRITICAL
    assert assessment.components == {
        "interconnection": 0.4,
        "permits": 0.25,
        "equipment": 0.2,
        "construction": 0.1,
    }
    assert assessment.expected_delay_months == 24
    assert assessment.evidence_tier == "corroborated_estimate"
    assert assessment.high_confidence_eligible is True
    assert len(assessment.blockers) == 5


def test_physical_risk_scores_low_when_firm_power_permits_equipment_and_progress_align():
    engine = PhysicalRiskEngine()
    asset = _asset(construction_status=ConstructionStatus.UNDER_CONSTRUCTION)
    queue = InterconnectionQueueItem(
        queue_id="Q-2",
        region=GridRegion.PJM,
        status=InterconnectionStatus.AGREEMENT_EXECUTED,
        requested_mw=150,
        firm_service_mw=150,
        delay_months=0,
        provenance=_prov(SourceType.GRID_QUEUE, "pjm:queue:q-2"),
    )
    permit = PermitRecord(
        permit_id="AIR-2",
        authority="State DEQ",
        permit_type="air",
        status=PermitDecisionStatus.ISSUED,
        related_generation=True,
        capacity_mw=150,
        provenance=_prov(SourceType.STATE_DEQ, "deq:air-2"),
    )
    turbine = EquipmentRecord(
        equipment_type=EquipmentType.GAS_TURBINE,
        status=EquipmentStatus.DELIVERED,
        lead_time_months=12,
        provenance=_prov(SourceType.COMPANY_IR, "company:turbine-delivered"),
    )
    observation = ConstructionObservation(
        observed_on=date(2026, 12, 31),
        construction_status=ConstructionStatus.UNDER_CONSTRUCTION,
        progress_pct=0.65,
        provenance=_prov(SourceType.SATELLITE, "satellite:test-campus:progress"),
    )

    assessment = engine.assess(
        asset,
        queue_items=[queue],
        permits=[permit],
        equipment=[turbine],
        observations=[observation],
        as_of=date(2026, 12, 31),
    )

    assert assessment.score == 0.0
    assert assessment.risk_level == PhysicalRiskLevel.LOW
    assert assessment.blockers == []
    assert assessment.high_confidence_eligible is True


def test_missing_physical_evidence_creates_moderate_risk_and_blocks_high_confidence():
    engine = PhysicalRiskEngine()

    assessment = engine.assess(_asset(), as_of=date(2026, 12, 31))

    assert assessment.score == 0.67
    assert assessment.risk_level == PhysicalRiskLevel.HIGH
    assert assessment.evidence_tier == "unsupported"
    assert assessment.high_confidence_eligible is False
    assert "No source-backed grid interconnection record attached." in assessment.blockers


def test_physical_risk_project_ref_prefers_source_project_id():
    engine = PhysicalRiskEngine()

    assessment = engine.assess(
        _asset(source_project_id="campus-1", owner="Owner LLC"),
        as_of=date(2026, 12, 31),
    )

    assert assessment.project_ref == "campus-1"
