"""
Physical deliverability risk scoring.

This is the bridge between announced AI/data-center capacity and physical
reality: grid interconnection, permits, long-lead equipment, and observed
construction progress.
"""

from __future__ import annotations

from datetime import date

from bubble.analysis.evidence import EvidenceGate
from bubble.models.base import HumanReviewStatus, Provenance, SourceType
from bubble.models.physical import (
    ConstructionObservation,
    ConstructionStatus,
    EquipmentRecord,
    EquipmentStatus,
    EquipmentType,
    InterconnectionQueueItem,
    PermitDecisionStatus,
    PermitRecord,
    PhysicalAsset,
    PhysicalRiskAssessment,
    PhysicalRiskLevel,
)


class PhysicalRiskEngine:
    """Score data-center physical deliverability risk from source-backed records."""

    VERSION = "physical-risk-v1"

    def __init__(self, evidence_gate: EvidenceGate | None = None) -> None:
        self.evidence_gate = evidence_gate or EvidenceGate()

    def assess(
        self,
        asset: PhysicalAsset,
        *,
        queue_items: list[InterconnectionQueueItem] | None = None,
        permits: list[PermitRecord] | None = None,
        equipment: list[EquipmentRecord] | None = None,
        observations: list[ConstructionObservation] | None = None,
        as_of: date | None = None,
    ) -> PhysicalRiskAssessment:
        queue_items = queue_items or []
        permits = permits or []
        equipment = equipment or []
        observations = observations or []
        as_of = as_of or date.today()

        components: dict[str, float] = {}
        blockers: list[str] = []

        components["interconnection"] = self._interconnection_risk(asset, queue_items, blockers)
        components["permits"] = self._permit_risk(asset, permits, equipment, blockers)
        components["equipment"] = self._equipment_risk(asset, equipment, blockers)
        components["construction"] = self._construction_risk(asset, observations, blockers, as_of)

        score = round(min(1.0, sum(components.values())), 4)
        evidence = [item.provenance for item in [*queue_items, *permits, *equipment, *observations]]
        audit = self.evidence_gate.audit_claim(
            claim_id=f"physical-risk:{asset.id}",
            claim=f"Physical deliverability risk for {asset.name}",
            value=score,
            unit="0-1 score",
            evidence=evidence,
            requires_corroboration=True,
            high_impact=True,
        )
        assessment_confidence = min(0.9, audit.confidence if evidence else 0.35)
        if audit.blocking_issues:
            assessment_confidence = min(assessment_confidence, 0.6)

        delay_months = self._expected_delay_months(queue_items, equipment)
        supporting_evidence = [record.source_uri for record in audit.sources if record.source_uri]

        return PhysicalRiskAssessment(
            project_ref=asset.source_project_id or asset.owner,
            asset_ref=str(asset.id),
            score=score,
            risk_level=self._risk_level(score),
            components=components,
            blockers=blockers,
            expected_delay_months=delay_months,
            evidence_tier=audit.tier.value,
            evidence_source_count=audit.source_count,
            evidence_source_types=audit.source_types,
            high_confidence_eligible=audit.eligible_for_high_confidence,
            supporting_evidence=supporting_evidence,
            methodology_version=self.VERSION,
            attributes={"evidence_blocking_issues": audit.blocking_issues},
            confidence=assessment_confidence,
            provenance=Provenance(
                source_uri=f"analysis:{self.VERSION}",
                source_type=SourceType.INFERRED,
                confidence=assessment_confidence,
                human_review_status=HumanReviewStatus.PENDING,
                content_hash=Provenance.compute_content_hash(
                    f"{asset.id}:{score}:{components}:{blockers}:{supporting_evidence}"
                ),
            ),
        )

    def _interconnection_risk(
        self,
        asset: PhysicalAsset,
        queue_items: list[InterconnectionQueueItem],
        blockers: list[str],
    ) -> float:
        required_mw = asset.it_load_mw or asset.capacity_mw
        if not queue_items:
            blockers.append("No source-backed grid interconnection record attached.")
            return 0.25

        firm_items = [item for item in queue_items if item.has_firm_power(required_mw)]
        max_delay = max((item.delay_months or 0 for item in queue_items), default=0)
        risk = 0.0
        if not firm_items:
            risk += 0.25
            blockers.append("No queue record shows firm power for the required load.")
        if max_delay >= 12:
            risk += 0.15
            blockers.append(f"Grid queue delay is at least {max_delay} months.")
        return min(0.4, risk)

    def _permit_risk(
        self,
        asset: PhysicalAsset,
        permits: list[PermitRecord],
        equipment: list[EquipmentRecord],
        blockers: list[str],
    ) -> float:
        requires_generation_permit = any(
            item.equipment_type in {EquipmentType.GAS_TURBINE, EquipmentType.GENERATOR}
            for item in equipment
        ) or "gas" in " ".join(str(v).lower() for v in asset.major_equipment.values())

        relevant_permits = [permit for permit in permits if permit.related_generation]
        if requires_generation_permit and not relevant_permits:
            blockers.append(
                "On-site generation appears required, but no generation permit is attached."
            )
            return 0.2
        if not permits:
            blockers.append("No source-backed permit record attached.")
            return 0.12

        worst_status = self._worst_permit_status(permits)
        if worst_status in {PermitDecisionStatus.DENIED, PermitDecisionStatus.WITHDRAWN}:
            blockers.append(f"Permit status is {worst_status.value}.")
            return 0.3
        if worst_status == PermitDecisionStatus.CONTESTED:
            blockers.append("Permit is contested.")
            return 0.25
        if worst_status in {
            PermitDecisionStatus.APPLIED,
            PermitDecisionStatus.DRAFT,
            PermitDecisionStatus.UNKNOWN,
        }:
            blockers.append(f"Permit status is only {worst_status.value}.")
            return 0.15
        return 0.0

    def _equipment_risk(
        self,
        asset: PhysicalAsset,
        equipment: list[EquipmentRecord],
        blockers: list[str],
    ) -> float:
        if not equipment:
            if (asset.it_load_mw or asset.capacity_mw or 0) >= 100:
                blockers.append("Large project has no source-backed long-lead equipment record.")
                return 0.12
            return 0.05

        risk = 0.0
        for item in equipment:
            if item.status in {EquipmentStatus.NOT_ORDERED, EquipmentStatus.UNKNOWN}:
                risk = max(risk, 0.12)
                blockers.append(f"{item.equipment_type.value} status is {item.status.value}.")
            if item.status == EquipmentStatus.DELAYED or (item.lead_time_months or 0) >= 18:
                risk = max(risk, 0.2)
                blockers.append(
                    f"{item.equipment_type.value} lead time or delay is at least "
                    f"{item.lead_time_months or 'unknown'} months."
                )
        return risk

    def _construction_risk(
        self,
        asset: PhysicalAsset,
        observations: list[ConstructionObservation],
        blockers: list[str],
        as_of: date,
    ) -> float:
        latest_status = (
            max(observations, key=lambda item: item.observed_on).construction_status
            if observations
            else asset.construction_status
        )
        if latest_status in {
            ConstructionStatus.IN_SERVICE,
            ConstructionStatus.MECHANICAL_COMPLETION,
        }:
            return 0.0

        target_date = self._parse_date(asset.announced_in_service_date)
        if (
            target_date
            and (target_date - as_of).days <= 540
            and latest_status
            in {
                ConstructionStatus.ANNOUNCED,
                ConstructionStatus.PERMITTED,
            }
        ):
            blockers.append(
                "Project is near target in-service date but not visibly under construction."
            )
            return 0.1
        if latest_status == ConstructionStatus.DELAYED:
            blockers.append("Construction status is delayed.")
            return 0.1
        return 0.0

    @staticmethod
    def _worst_permit_status(permits: list[PermitRecord]) -> PermitDecisionStatus:
        rank = {
            PermitDecisionStatus.DENIED: 7,
            PermitDecisionStatus.WITHDRAWN: 6,
            PermitDecisionStatus.CONTESTED: 5,
            PermitDecisionStatus.UNKNOWN: 4,
            PermitDecisionStatus.DRAFT: 3,
            PermitDecisionStatus.APPLIED: 2,
            PermitDecisionStatus.NOT_FOUND: 2,
            PermitDecisionStatus.ISSUED: 1,
            PermitDecisionStatus.NOT_REQUIRED: 0,
        }
        return max((permit.status for permit in permits), key=lambda status: rank[status])

    @staticmethod
    def _expected_delay_months(
        queue_items: list[InterconnectionQueueItem],
        equipment: list[EquipmentRecord],
    ) -> int | None:
        delays = [item.delay_months or 0 for item in queue_items]
        delays.extend(
            item.lead_time_months or 0
            for item in equipment
            if item.status == EquipmentStatus.DELAYED
        )
        max_delay = max(delays, default=0)
        return max_delay or None

    @staticmethod
    def _risk_level(score: float) -> PhysicalRiskLevel:
        if score >= 0.75:
            return PhysicalRiskLevel.CRITICAL
        if score >= 0.5:
            return PhysicalRiskLevel.HIGH
        if score >= 0.25:
            return PhysicalRiskLevel.MODERATE
        return PhysicalRiskLevel.LOW

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
