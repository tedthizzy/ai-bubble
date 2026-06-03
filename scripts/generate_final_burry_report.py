#!/usr/bin/env python
"""
Evidence-gated Burry report generator.

This artifact is intentionally coverage-grounded. It does not invent ecosystem
scale metrics; it reports what source corpus has actually been acquired and
blocks bubble/leverage/timing conclusions until evidence coverage can support them.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bubble.analysis.burry_verdict import synthesize_core_verdict
from bubble.analysis.circular_financing import analyze_circular_financing
from bubble.analysis.circular_financing import load_edges as load_circular_financing_edges
from bubble.analysis.cluster_boundary import (
    aggregate_cluster_boundary,
    load_cluster_boundary,
)
from bubble.analysis.cluster_discovery import discover_structure
from bubble.analysis.cluster_dscr import IssuerFinancials, compute_cluster_interest_coverage
from bubble.analysis.cluster_extension import (
    aggregate_cluster_extension,
    load_cluster_extension,
)
from bubble.analysis.compute_economics import (
    ComputeEconomicsBatch,
    analyze_compute_economics,
    empty_compute_economics_batch,
)
from bubble.analysis.contagion_hubs import compute_contagion_hubs, load_contagion_edges
from bubble.analysis.contagion_propagation import top_contagion_cascades
from bubble.analysis.contract_structure import (
    aggregate_contract_structure,
    load_contract_structure,
)
from bubble.analysis.debt_census import aggregate_debt_census, load_debt_census
from bubble.analysis.debt_service import analyze_debt_service
from bubble.analysis.demand_side import aggregate_demand_side, load_demand_side
from bubble.analysis.ecosystem_scope import scope_deals
from bubble.analysis.end_holders import aggregate_end_holders, load_end_holders
from bubble.analysis.entity_risk_ranking import build_entity_risk_ranking
from bubble.analysis.entity_universe_map import (
    aggregate_entity_universe,
    load_entity_universe_map,
)
from bubble.analysis.equipment_bottlenecks import (
    aggregate_equipment_bottlenecks,
    load_equipment_bottlenecks,
)
from bubble.analysis.evidence import EvidenceGate, SemanticEvidenceBucket, classify_claim_semantics
from bubble.analysis.forensic_fragility_scorecard import score_fragility
from bubble.analysis.gpu_earnings_quality import (
    aggregate_gpu_earnings_quality,
    load_gpu_earnings_quality,
)
from bubble.analysis.gpu_economics import load_gpu_price_evidence, summarize_gpu_depreciation_gap
from bubble.analysis.leading_indicator_monitor import build_leading_indicator_monitor
from bubble.analysis.physical_capacity import build_physical_capacity_summary
from bubble.analysis.physical_execution_summary import build_physical_execution_summary
from bubble.analysis.physical_risk_summary import build_physical_risk_summary
from bubble.analysis.power_exposure import aggregate_power_exposure, load_power_exposure
from bubble.analysis.private_credit_funding import (
    aggregate_private_credit_funding,
    load_private_credit_funding,
)
from bubble.analysis.red_flag_scorecard import (
    aggregate_red_flag_scorecard,
    load_red_flag_scorecard,
)
from bubble.analysis.refi_wall import aggregate_refi_wall, load_debt_census_raw
from bubble.analysis.risk_register import build_risk_register
from bubble.analysis.scenario_stress import stress_cluster
from bubble.analysis.source_coverage import build_source_coverage_report
from bubble.analysis.universe_extrapolation import estimate_universe
from bubble.analysis.utilization_debt_service import (
    aggregate_utilization_debt_service,
    load_utilization_debt_service,
)
from bubble.ingestion.capital import (
    CapitalEvidenceBatch,
    analyze_capital_evidence,
    load_capital_evidence,
)
from bubble.ingestion.compute.loader import load_compute_economics, merge_compute_economics_batches
from bubble.ingestion.satellite import (
    aggregate_satellite_observations,
    load_satellite_observations,
)
from bubble.models.base import HumanReviewStatus, Provenance, SourceType
from bubble.quality.relevance_linkage import summarize_relevance_linkage
from bubble.quality.risk_bearer_classification import summarize_risk_bearer_quality

TARGET_ENTITIES_LOW = 1_200
TARGET_DEALS_LOW = 25_000


def source_coverage_provenance() -> Provenance:
    """Provenance for the local source coverage inventory."""

    return Provenance(
        source_uri="local:source_coverage_report",
        source_type=SourceType.MANUAL_CURATED,
        page_or_section="Local acquired source inventories and extracted CSV rows",
        confidence=0.9,
        human_review_status=HumanReviewStatus.PENDING,
        content_hash=Provenance.compute_content_hash("source_coverage_report:v1"),
    )


def audit_report_evidence(
    metrics: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], float]:
    """Audit current evidence coverage and final-conclusion readiness."""

    gate = EvidenceGate(min_high_confidence=0.75, min_corroborating_sources=2)
    coverage_provenance = source_coverage_provenance()
    coverage_claims = [
        ("coverage.entities", "Source-covered entities", metrics["covered_entities"], "entities"),
        ("coverage.filings", "Source-covered SEC filings", metrics["covered_filings"], "filings"),
        (
            "coverage.documents",
            "Downloaded raw source documents",
            metrics["raw_source_documents"],
            "documents",
        ),
        (
            "coverage.source_backed_deals",
            "Extracted source-backed deals",
            metrics["source_backed_deals"],
            "deals",
        ),
        (
            "coverage.source_backed_compute_rows",
            "Extracted source-backed compute-economics rows",
            metrics["source_backed_compute_rows"],
            "rows",
        ),
        (
            "coverage.catalog_sources",
            "Queued real-source acquisition targets",
            metrics["catalog_sources"],
            "sources",
        ),
        (
            "coverage.projects",
            "Source-covered physical projects",
            metrics["covered_projects"],
            "projects",
        ),
        (
            "coverage.queue_records",
            "Source-covered interconnection queue records",
            metrics["queue_records"],
            "records",
        ),
        (
            "physical.queue_capacity_mw",
            "Source-backed interconnection queue capacity",
            metrics["queue_capacity_mw"],
            "MW",
        ),
        (
            "physical.data_center_queue_capacity_mw",
            "Source-backed active interconnection queue capacity explicitly tied to data-center or hyperscale load",
            metrics["data_center_queue_capacity_mw"],
            "MW",
        ),
        (
            "physical.project_linked_queue_capacity_mw",
            "Source-backed data-center queue capacity linked to tracker project records",
            metrics["queue_project_loader_queue_capacity_mw"],
            "MW",
        ),
        (
            "physical.project_linked_permit_records",
            "Source-backed EPA air records linked to tracker project records",
            metrics["physical_record_permit_loader_rows"],
            "records",
        ),
        (
            "physical.project_linked_equipment_records",
            "Source-backed generator/equipment records linked to tracker project records",
            metrics["physical_record_equipment_loader_rows"],
            "records",
        ),
        (
            "physical.project_linked_equipment_capacity_mw",
            "Source-backed generator/equipment capacity linked to tracker project records",
            metrics["physical_record_equipment_loader_capacity_mw"],
            "MW",
        ),
        (
            "physical_execution.distinct_terms",
            "Distinct source-backed physical execution terms extracted from tracker, queue, and permit rows",
            metrics["physical_execution_distinct_terms"],
            "terms",
        ),
        (
            "physical_execution.projects",
            "Projects with source-backed physical execution terms",
            metrics["physical_execution_projects"],
            "projects",
        ),
        (
            "physical_execution.onsite_generation_mw_term_sum",
            "Term-level source-backed on-site generation MW evidence; not project-deduped capacity",
            metrics["physical_execution_onsite_generation_mw_term_sum"],
            "MW",
        ),
        (
            "physical_execution.behind_the_meter_or_off_grid_terms",
            "Source-backed behind-the-meter or off-grid physical execution terms",
            metrics["physical_execution_risk_term_counts"].get(
                "behind_the_meter_or_off_grid",
                0,
            ),
            "terms",
        ),
        (
            "physical_execution.permit_litigation_or_enforcement_terms",
            "Source-backed permit litigation or enforcement-risk physical execution terms",
            metrics["physical_execution_risk_term_counts"].get(
                "permit_litigation_or_enforcement_risk",
                0,
            ),
            "terms",
        ),
        (
            "physical_execution.queue_bypass_or_no_queue_terms",
            "Source-backed queue-bypass or no-queue physical execution terms",
            metrics["physical_execution_risk_term_counts"].get(
                "queue_bypass_or_no_queue",
                0,
            ),
            "terms",
        ),
        (
            "physical.tracker_capacity_high_mw",
            "Source-backed raw tracker reported data-center capacity high case",
            metrics["tracker_capacity_high_mw"],
            "MW",
        ),
        (
            "physical.tracker_distinct_capacity_high_mw",
            "Source-backed distinct tracker reported data-center capacity high case",
            metrics["tracker_distinct_capacity_high_mw"],
            "MW",
        ),
        (
            "physical.tracker_distinct_pipeline_capacity_high_mw",
            "Source-backed distinct tracker reported non-operating data-center pipeline capacity high case",
            metrics["tracker_distinct_pipeline_capacity_high_mw"],
            "MW",
        ),
        (
            "physical.tracker_investment_usd",
            "Source-backed tracker reported data-center investment",
            metrics["tracker_investment_usd"],
            "USD",
        ),
        (
            "physical.tracker_distinct_investment_usd",
            "Source-backed distinct tracker reported data-center investment",
            metrics["tracker_distinct_investment_usd"],
            "USD",
        ),
        (
            "physical.eia_operating_capacity_mw",
            "Source-backed EIA operating generator capacity",
            metrics["eia_operating_capacity_mw"],
            "MW",
        ),
        (
            "physical.eia_planned_capacity_mw",
            "Source-backed EIA planned generator capacity",
            metrics["eia_planned_capacity_mw"],
            "MW",
        ),
        ("coverage.permits", "Source-covered permit records", metrics["permit_records"], "records"),
    ]
    audits = [
        gate.audit_claim(
            claim_id=claim_id,
            claim=claim,
            value=value,
            unit=unit,
            evidence=[coverage_provenance],
            requires_corroboration=False,
            high_impact=False,
        )
        for claim_id, claim, value, unit in coverage_claims
    ]

    final_claim = gate.audit_claim(
        claim_id="final.bubble_conclusion",
        claim="Final bubble/no-bubble conclusion",
        value="blocked_until_source_coverage_sufficient",
        unit=None,
        evidence=[],
        requires_corroboration=True,
        high_impact=True,
    )
    audits.append(final_claim)
    capped_confidence = gate.cap_report_confidence(0.82, audits)
    return (
        [audit.to_dict() for audit in audits],
        gate.summarize(audits).to_dict(),
        capped_confidence,
    )


def claim_audits_from_metric_payload(payload: Any) -> list[dict[str, Any]]:
    """Extract top-level or nested analyzer claim audits from a metric payload."""

    if not isinstance(payload, dict):
        return []
    direct = payload.get("claim_audits")
    if isinstance(direct, list):
        return [audit for audit in direct if isinstance(audit, dict)]
    evidence_summary = payload.get("evidence_summary")
    if isinstance(evidence_summary, dict):
        nested = evidence_summary.get("claim_audits")
        if isinstance(nested, list):
            return [audit for audit in nested if isinstance(audit, dict)]
    return []


def merge_evidence_audits(
    base_audits: list[dict[str, Any]],
    *metric_payloads: Any,
) -> list[dict[str, Any]]:
    """Append analyzer-level audits to report-level audits, deduped by claim id."""

    merged = list(base_audits)
    seen = {
        str(audit.get("claim_id"))
        for audit in merged
        if isinstance(audit, dict) and audit.get("claim_id")
    }
    for payload in metric_payloads:
        for audit in claim_audits_from_metric_payload(payload):
            claim_id = audit.get("claim_id")
            if not claim_id:
                continue
            claim_key = str(claim_id)
            if claim_key in seen:
                continue
            seen.add(claim_key)
            merged.append(audit)
    return merged


def summarize_evidence_audit_dicts(audits: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize serialized EvidenceGate audits after report-level merging."""

    tiers = [str(audit.get("tier") or "") for audit in audits]
    blocking_issue_count = sum(
        len(issues)
        for audit in audits
        for issues in [audit.get("blocking_issues")]
        if isinstance(issues, list)
    )
    max_confidence = max_permitted_report_confidence_from_audit_dicts(audits)
    return {
        "audited_claims": len(audits),
        "measured_claims": sum(tier == "measured" for tier in tiers),
        "corroborated_claims": sum(tier == "corroborated_estimate" for tier in tiers),
        "inferred_claims": sum(tier == "inferred" for tier in tiers),
        "unsupported_claims": sum(tier == "unsupported" for tier in tiers),
        "semantic_evaluated_claims": sum(
            str(audit.get("semantic_bucket") or "not_evaluated") != "not_evaluated"
            for audit in audits
        ),
        "semantic_committed_debt_claims": sum(
            str(audit.get("semantic_bucket") or "") == "committed_debt" for audit in audits
        ),
        "semantic_asset_or_capacity_claims": sum(
            str(audit.get("semantic_bucket") or "") == "asset_or_capacity" for audit in audits
        ),
        "semantic_equity_or_production_claims": sum(
            str(audit.get("semantic_bucket") or "") == "equity_or_production" for audit in audits
        ),
        "semantic_boilerplate_claims": sum(
            str(audit.get("semantic_bucket") or "") == "boilerplate_only" for audit in audits
        ),
        "semantic_indeterminate_claims": sum(
            str(audit.get("semantic_bucket") or "") == "indeterminate" for audit in audits
        ),
        "high_confidence_eligible_claims": sum(
            bool(audit.get("eligible_for_high_confidence")) for audit in audits
        ),
        "blocking_issue_count": blocking_issue_count,
        "max_permitted_report_confidence": max_confidence,
    }


def max_permitted_report_confidence_from_audit_dicts(
    audits: list[dict[str, Any]],
) -> float:
    """Conservative confidence cap equivalent for serialized audits."""

    if not audits:
        return 0.2
    tiers = {str(audit.get("tier") or "") for audit in audits}
    if "unsupported" in tiers:
        return 0.25
    if "inferred" in tiers:
        return 0.45
    confidences = [
        float(confidence)
        for audit in audits
        for confidence in [audit.get("effective_confidence", audit.get("confidence"))]
        if isinstance(confidence, (int, float)) and not isinstance(confidence, bool)
    ]
    if any(audit.get("blocking_issues") for audit in audits):
        return min(0.6, *confidences) if confidences else 0.6
    return min(0.95, *confidences) if confidences else 0.2


def _source_type_from_uri(source_uri: str) -> SourceType:
    lowered = source_uri.lower()
    source_markers = (
        ("sec.gov", SourceType.SEC_EDGAR),
        ("gleif.org", SourceType.GLEIF),
        ("lei", SourceType.GLEIF),
        ("arcgis.com", SourceType.PROJECT_TRACKER),
        ("fractracker", SourceType.PROJECT_TRACKER),
        ("ferc", SourceType.FERC),
        ("eia.gov", SourceType.EIA),
        ("epa.gov", SourceType.EPA),
    )
    for marker, source_type in source_markers:
        if marker in lowered:
            return source_type
    return SourceType.MANUAL_CURATED


def _review_status_from_text(value: Any) -> HumanReviewStatus:
    try:
        return HumanReviewStatus(str(value))
    except ValueError:
        return HumanReviewStatus.PENDING


def _retrieved_at_from_text(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def artifact_provenance(
    *,
    source_uri: str,
    page_or_section: str,
    payload: Any,
    confidence: float = 0.74,
) -> Provenance:
    """Provenance for deterministic local summary artifacts used by the report."""

    return Provenance(
        source_uri=source_uri,
        source_type=SourceType.MANUAL_CURATED,
        page_or_section=page_or_section,
        confidence=confidence,
        human_review_status=HumanReviewStatus.PENDING,
        content_hash=Provenance.compute_content_hash(
            json.dumps(_artifact_fingerprint(payload), sort_keys=True, default=str)
        ),
    )


def _artifact_fingerprint(payload: Any) -> dict[str, Any]:
    """Compact, deterministic identity for potentially large summary artifacts."""

    if not isinstance(payload, dict):
        return {"type": type(payload).__name__, "value": str(payload)[:500]}
    fingerprint: dict[str, Any] = {"keys": sorted(str(key) for key in payload)}
    scalar_values: dict[str, Any] = {}
    collection_sizes: dict[str, int] = {}
    for key, value in payload.items():
        key_text = str(key)
        if isinstance(value, (str, int, float, bool)) or value is None:
            scalar_values[key_text] = value
        elif isinstance(value, (list, dict)):
            collection_sizes[key_text] = len(value)
    fingerprint["scalars"] = scalar_values
    fingerprint["collection_sizes"] = collection_sizes
    return fingerprint


def row_provenance(
    item: dict[str, Any],
    *,
    fallback_section: str,
    max_sources: int = 25,
) -> list[Provenance]:
    """Build source provenance from serialized report/source rows."""

    raw_uris = item.get("source_uris") or item.get("source_uri") or []
    if isinstance(raw_uris, str):
        source_uris = [raw_uris]
    elif isinstance(raw_uris, list):
        source_uris = [str(uri) for uri in raw_uris if uri]
    else:
        source_uris = []
    raw_hashes = item.get("content_hashes") or item.get("content_hash") or []
    if isinstance(raw_hashes, str):
        content_hashes = [raw_hashes]
    elif isinstance(raw_hashes, list):
        content_hashes = [str(content_hash) for content_hash in raw_hashes if content_hash]
    else:
        content_hashes = []
    confidence = item.get("source_confidence")
    source_confidence = (
        float(confidence)
        if isinstance(confidence, (int, float)) and not isinstance(confidence, bool)
        else 0.75
    )
    status = _review_status_from_text(
        item.get("human_review_status")
        or (item.get("human_review_statuses") or [HumanReviewStatus.PENDING.value])[0]
    )
    retrieved_at = _retrieved_at_from_text(item.get("retrieved_at"))
    page_or_section = str(item.get("page_or_section") or fallback_section)
    provenances: list[Provenance] = []
    for index, source_uri in enumerate(source_uris[:max_sources]):
        content_hash = (
            content_hashes[index]
            if index < len(content_hashes)
            else Provenance.compute_content_hash(f"{source_uri}:{page_or_section}")
        )
        provenance_kwargs: dict[str, Any] = {}
        if retrieved_at is not None:
            provenance_kwargs["retrieved_at"] = retrieved_at
        provenances.append(
            Provenance(
                source_uri=source_uri,
                source_type=_source_type_from_uri(source_uri),
                page_or_section=page_or_section,
                confidence=source_confidence,
                human_review_status=status,
                content_hash=content_hash,
                **provenance_kwargs,
            )
        )
    return provenances


def row_list_provenance(
    rows: list[Any],
    *,
    fallback_section: str,
    max_sources: int = 25,
) -> list[Provenance]:
    provenances: list[Provenance] = []
    for row in rows:
        if isinstance(row, dict):
            provenances.extend(
                row_provenance(
                    row,
                    fallback_section=fallback_section,
                    max_sources=max(1, max_sources - len(provenances)),
                )
            )
        if len(provenances) >= max_sources:
            break
    return provenances


def audit_scalar_claim(
    gate: EvidenceGate,
    *,
    claim_id: str,
    claim: str,
    value: Any,
    unit: str,
    evidence: list[Provenance],
    requires_corroboration: bool = True,
    semantic_text: str | None = None,
    semantic_required: bool = False,
) -> dict[str, Any] | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    audit = gate.audit_claim(
        claim_id=claim_id,
        claim=claim,
        value=round(float(value), 2),
        unit=unit,
        evidence=evidence,
        requires_corroboration=requires_corroboration,
        high_impact=True,
        semantic_text=semantic_text,
        semantic_required=semantic_required,
    ).to_dict()
    return dict(audit)


def report_answer_metric_audits(  # noqa: PLR0912, PLR0915
    *,
    timing_signal_summary: dict[str, Any],
    review_queue_summary: dict[str, Any],
    weak_link_summary: dict[str, Any],
    debt_service_metrics_dict: dict[str, Any],
    compute_metrics_dict: dict[str, Any],
    capital_metrics_dict: dict[str, Any] | None = None,
    capital_scope_summary_dict: dict[str, Any] | None = None,
    capital_exposure_graph_summary: dict[str, Any],
    contract_contagion_summary: dict[str, Any],
    materiality_adjudication_summary: dict[str, Any] | None = None,
    materiality_adjudication_decision_summary: dict[str, Any] | None = None,
    materiality_relevance_summary: dict[str, Any] | None = None,
    mismatch_ratios: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Audit high-impact scalar values surfaced directly in Burry answers.

    Now also audits key Burry mismatch ratios (DSCR at realistic util, physical deliverable %,
    GPU life gap, missing-rate fragility) so they can affect the evidence gate.
    """

    gate = EvidenceGate(min_high_confidence=0.75, min_corroborating_sources=2)
    audits: list[dict[str, Any]] = []

    def add(
        claim_id: str,
        claim: str,
        value: Any,
        evidence: list[Provenance],
        *,
        unit: str = "USD",
        requires_corroboration: bool = True,
        semantic_text: str | None = None,
        semantic_required: bool = False,
    ) -> None:
        audit = audit_scalar_claim(
            gate,
            claim_id=claim_id,
            claim=claim,
            value=value,
            unit=unit,
            evidence=evidence,
            requires_corroboration=requires_corroboration,
            semantic_text=semantic_text,
            semantic_required=semantic_required,
        )
        if audit is not None:
            audits.append(audit)

    timing_artifact = artifact_provenance(
        source_uri="local:data/reports/timing_signal_summary.json",
        page_or_section="source-backed timing signal rollup",
        payload=timing_signal_summary,
    )
    timing_rows = timing_signal_summary.get("top_signals", [])
    timing_row_evidence = row_list_provenance(
        timing_rows if isinstance(timing_rows, list) else [],
        fallback_section="timing_signal_summary.top_signals",
    )
    timing_evidence = [timing_artifact, *timing_row_evidence]
    add(
        "timing.capital_refinancing_2024_2030",
        "Source-backed timing-signal capital refinancing through 2030",
        timing_signal_summary.get("capital_refinancing_usd_2024_2030"),
        timing_evidence,
    )
    add(
        "timing.ai_infra_capital_refinancing_2024_2030",
        "AI-infra-relevant timing-signal capital refinancing through 2030",
        timing_signal_summary.get("ai_infra_capital_refinancing_usd_2024_2030"),
        timing_evidence,
    )
    add(
        "timing.capital_refinancing_forward_from_as_of",
        "Forward timing-signal capital refinancing from the report as-of quarter",
        timing_signal_summary.get("capital_refinancing_forward_from_as_of_usd"),
        timing_evidence,
    )
    add(
        "timing.ai_infra_capital_refinancing_forward_from_as_of",
        "Forward AI-infra-relevant timing-signal capital refinancing from the report as-of quarter",
        timing_signal_summary.get("ai_infra_capital_refinancing_forward_from_as_of_usd"),
        timing_evidence,
    )
    add(
        "timing.capital_refinancing_historical_to_as_of",
        "Historical-to-as-of timing-signal capital refinancing included in the 2024-2030 wall",
        timing_signal_summary.get("capital_refinancing_historical_to_as_of_usd"),
        timing_evidence,
    )
    add(
        "timing.ai_infra_capital_refinancing_historical_to_as_of",
        "Historical-to-as-of AI-infra timing-signal capital refinancing included in the 2024-2030 wall",
        timing_signal_summary.get("ai_infra_capital_refinancing_historical_to_as_of_usd"),
        timing_evidence,
    )
    add(
        "timing.compute_amount_2024_2030",
        "Source-backed compute timing-signal amount through 2030",
        timing_signal_summary.get("compute_amount_usd_2024_2030"),
        timing_evidence,
    )
    top_quarters = timing_signal_summary.get("top_quarters", [])
    if isinstance(top_quarters, list):
        for index, quarter in enumerate(top_quarters[:10]):
            if not isinstance(quarter, dict):
                continue
            quarter_evidence = [timing_artifact, *timing_row_evidence]
            label = str(quarter.get("quarter") or index)
            add(
                f"timing.top_quarter.{label}.capital_refinancing",
                f"Capital refinancing timing signal in quarter {label}",
                quarter.get("capital_refinancing_usd"),
                quarter_evidence,
            )
            add(
                f"timing.top_quarter.{label}.compute_amount",
                f"Compute amount timing signal in quarter {label}",
                quarter.get("compute_amount_usd"),
                quarter_evidence,
            )
    if isinstance(timing_rows, list):
        for index, row in enumerate(timing_rows[:25]):
            if not isinstance(row, dict):
                continue
            add(
                f"timing.top_signal.{row.get('signal_id') or index}.amount",
                "Top timing signal amount",
                row.get("amount_usd"),
                row_provenance(row, fallback_section="timing_signal_summary.top_signals"),
                requires_corroboration=False,
            )

    review_rows = review_queue_summary.get("top_distinct_capital_items", [])
    if isinstance(review_rows, list):
        for index, row in enumerate(review_rows[:25]):
            if not isinstance(row, dict):
                continue
            add(
                f"review_queue.distinct_capital_item.{row.get('review_id') or index}.notional",
                "Top distinct capital review queue notional",
                row.get("notional_amount_usd"),
                row_provenance(
                    row, fallback_section="review_queue_summary.top_distinct_capital_items"
                ),
                requires_corroboration=False,
            )

    review_artifact = artifact_provenance(
        source_uri="local:data/reports/review_queue_summary.json",
        page_or_section="review queue aggregate rollup",
        payload={
            key: review_queue_summary.get(key)
            for key in (
                "pending_capital_distinct_notional_amount_usd",
                "pending_ai_infra_relevant_capital_distinct_notional_amount_usd",
                "pending_compute_claim_amount_usd",
            )
        },
    )
    review_row_evidence = row_list_provenance(
        review_rows if isinstance(review_rows, list) else [],
        fallback_section="review_queue_summary.top_distinct_capital_items",
    )
    review_evidence = [review_artifact, *review_row_evidence]
    add(
        "review_queue.pending_capital_distinct_notional",
        "Distinct pending capital review-queue notional",
        review_queue_summary.get("pending_capital_distinct_notional_amount_usd"),
        review_evidence,
        requires_corroboration=False,
    )
    add(
        "review_queue.pending_notional_gross",
        "Gross pending review-queue notional before distinct-dedupe; diagnostic only",
        review_queue_summary.get("pending_notional_amount_usd"),
        review_evidence,
        requires_corroboration=False,
    )
    add(
        "review_queue.pending_exposure_gross",
        "Gross pending review-queue exposure before distinct-dedupe; diagnostic only",
        review_queue_summary.get("pending_exposure_usd"),
        review_evidence,
        requires_corroboration=False,
    )
    add(
        "review_queue.pending_capital_notional_gross",
        "Gross pending capital review-queue notional before distinct-dedupe; diagnostic only",
        review_queue_summary.get("pending_capital_notional_amount_usd"),
        review_evidence,
        requires_corroboration=False,
    )
    add(
        "review_queue.pending_capital_duplicate_notional",
        "Duplicate candidate notional inside pending capital review queue",
        review_queue_summary.get("pending_capital_duplicate_notional_amount_usd"),
        review_evidence,
        requires_corroboration=False,
    )
    add(
        "review_queue.pending_ai_infra_relevant_capital_notional_gross",
        "Gross AI-infra-relevant pending capital review-queue notional before distinct-dedupe",
        review_queue_summary.get("pending_ai_infra_relevant_capital_notional_amount_usd"),
        review_evidence,
        requires_corroboration=False,
    )
    add(
        "review_queue.pending_contagion_path_exposure_path_summed",
        "Pending contagion-path review exposure, path-summed and multiplicity-inflated",
        review_queue_summary.get("pending_contagion_path_exposure_usd"),
        review_evidence,
        requires_corroboration=False,
    )
    add(
        "review_queue.pending_ai_infra_relevant_capital_distinct_notional",
        "AI-infra-relevant distinct pending capital review-queue notional",
        review_queue_summary.get("pending_ai_infra_relevant_capital_distinct_notional_amount_usd"),
        review_evidence,
        requires_corroboration=False,
    )
    add(
        "review_queue.pending_compute_claim_amount",
        "Pending compute claim amount in the review queue",
        review_queue_summary.get("pending_compute_claim_amount_usd"),
        review_evidence,
        requires_corroboration=False,
    )

    weak_link_artifact = artifact_provenance(
        source_uri="local:data/reports/weak_link_summary.json",
        page_or_section="weak-link analyzer aggregate rollup",
        payload={
            key: weak_link_summary.get(key)
            for key in (
                "ai_infra_relevant_notional_usd",
                "top_weak_links",
                "top_debt_service_weak_links",
            )
        },
    )
    weak_link_rows: list[Any] = []
    for key in ("top_weak_links", "top_debt_service_weak_links"):
        rows = weak_link_summary.get(key, [])
        if isinstance(rows, list):
            weak_link_rows.extend(rows[:25])
    weak_link_evidence = [
        weak_link_artifact,
        *row_list_provenance(weak_link_rows, fallback_section="weak_link_summary.top_rows"),
    ]
    add(
        "weak_link.ai_infra_relevant_notional",
        "AI-infra-relevant weak-link exposure rollup",
        weak_link_summary.get("ai_infra_relevant_notional_usd"),
        weak_link_evidence,
    )
    for index, row in enumerate(weak_link_rows):
        if not isinstance(row, dict):
            continue
        add(
            f"weak_link.{row.get('weak_link_id') or index}.exposure",
            "Top weak-link exposure surfaced in Burry answers",
            row.get("exposure_usd"),
            row_provenance(row, fallback_section="weak_link_summary.top_rows"),
            requires_corroboration=False,
        )

    debt_artifact = artifact_provenance(
        source_uri="local:debt_service_metrics",
        page_or_section="debt-service analyzer rollup",
        payload={
            key: debt_service_metrics_dict.get(key)
            for key in (
                "distinct_debt_like_notional_usd",
                "measured_rate_notional_usd",
                "distinct_missing_rate_notional_usd",
                "distinct_notional_missing_maturity_usd",
                "top_debt_service_quarters",
                "top_distinct_debt_service_quarters",
                "top_entity_debt_service_risks",
            )
        },
    )
    all_debt_obligation_rows: list[Any] = []
    for row_key in ("top_debt_service_obligations", "top_debt_service_coverage_gaps"):
        rows = debt_service_metrics_dict.get(row_key, [])
        if isinstance(rows, list):
            all_debt_obligation_rows.extend(rows[:15])
    debt_evidence = [
        debt_artifact,
        *row_list_provenance(
            all_debt_obligation_rows,
            fallback_section="debt_service_metrics.top_obligations",
        ),
    ]
    add(
        "debt_service.measured_rate_notional",
        "Debt-like notional with explicit measured source-backed rates",
        debt_service_metrics_dict.get("measured_rate_notional_usd"),
        debt_evidence,
    )
    add(
        "debt_service.distinct_debt_like_notional",
        "Distinct debt-like notional in the debt-service analyzer",
        debt_service_metrics_dict.get("distinct_debt_like_notional_usd"),
        debt_evidence,
    )
    add(
        "debt_service.distinct_missing_rate_notional",
        "Distinct debt-like notional still missing explicit rate evidence",
        debt_service_metrics_dict.get("distinct_missing_rate_notional_usd"),
        debt_evidence,
    )
    add(
        "debt_service.distinct_missing_maturity_notional",
        "Distinct debt-like notional still missing maturity-date evidence",
        debt_service_metrics_dict.get("distinct_notional_missing_maturity_usd"),
        debt_evidence,
    )
    add(
        "debt_service.notional_missing_maturity",
        "Debt-like notional still missing maturity-date evidence before distinct-dedupe",
        debt_service_metrics_dict.get("notional_missing_maturity_usd"),
        debt_evidence,
        requires_corroboration=False,
    )
    add(
        "debt_service.distinct_measured_rate_notional",
        "Distinct debt-like notional with measured source-backed rates",
        debt_service_metrics_dict.get("distinct_measured_rate_notional_usd"),
        debt_evidence,
        requires_corroboration=False,
    )
    add(
        "debt_service.maturity_wall_notional_2024_2030",
        "Debt-service maturity-wall notional through 2030",
        debt_service_metrics_dict.get("maturity_wall_notional_usd_2024_2030"),
        debt_evidence,
    )
    add(
        "debt_service.distinct_maturity_wall_notional_2024_2030",
        "Distinct debt-service maturity-wall notional through 2030",
        debt_service_metrics_dict.get("distinct_maturity_wall_notional_usd_2024_2030"),
        debt_evidence,
        requires_corroboration=False,
    )
    add(
        "debt_service.out_of_scope_debt_like_notional",
        "Debt-like notional excluded from debt-service scope",
        debt_service_metrics_dict.get("out_of_scope_debt_like_notional_usd"),
        debt_evidence,
        requires_corroboration=False,
    )
    for key in ("top_debt_service_quarters", "top_distinct_debt_service_quarters"):
        rows = debt_service_metrics_dict.get(key, [])
        if not isinstance(rows, list):
            continue
        for index, row in enumerate(rows[:10]):
            if not isinstance(row, dict):
                continue
            row_evidence = [
                debt_artifact,
                *row_list_provenance(
                    row.get("top_obligations", []),
                    fallback_section=f"debt_service_metrics.{key}",
                ),
            ]
            add(
                f"debt_service.{key}.{row.get('quarter') or index}.maturing_notional",
                "Top debt-service quarter maturing notional",
                row.get("maturing_notional_usd"),
                row_evidence,
            )
    entity_rows = debt_service_metrics_dict.get("top_entity_debt_service_risks", [])
    if isinstance(entity_rows, list):
        for index, row in enumerate(entity_rows[:15]):
            if not isinstance(row, dict):
                continue
            entity_evidence = [
                debt_artifact,
                *row_list_provenance(
                    row.get("top_obligations", []),
                    fallback_section="debt_service_metrics.top_entity_debt_service_risks",
                ),
            ]
            entity_key = str(row.get("entity") or index).lower().replace(" ", "-")
            add(
                f"debt_service.entity.{entity_key}.distinct_notional",
                "Entity-level debt-service distinct notional",
                row.get("distinct_notional_usd"),
                entity_evidence,
            )
            add(
                f"debt_service.entity.{entity_key}.measured_rate_notional",
                "Entity-level debt-service measured-rate notional",
                row.get("measured_rate_notional_usd"),
                entity_evidence,
            )
            add(
                f"debt_service.entity.{entity_key}.maturity_wall_notional",
                "Entity-level debt-service maturity wall notional through 2030",
                row.get("maturity_wall_notional_usd_2024_2030"),
                entity_evidence,
            )

    graph_artifact = artifact_provenance(
        source_uri="local:data/graph/capital_exposure_graph_summary.json",
        page_or_section="capital exposure graph summary",
        payload=capital_exposure_graph_summary,
    )
    add(
        "capital_exposure.total_edge_notional",
        "Total capital-exposure graph edge notional",
        capital_exposure_graph_summary.get("total_edge_notional_usd"),
        [graph_artifact],
        requires_corroboration=False,
    )
    add(
        "capital_exposure.ai_infra_relevant_notional",
        "AI-infra-relevant capital-exposure graph edge notional",
        capital_exposure_graph_summary.get("ai_infra_relevant_notional_usd"),
        [graph_artifact],
        requires_corroboration=False,
    )
    add(
        "capital_exposure.ppa_capacity_mw",
        "Capital-exposure graph PPA capacity",
        capital_exposure_graph_summary.get("ppa_capacity_mw"),
        [graph_artifact],
        unit="MW",
        requires_corroboration=False,
    )
    add(
        "capital_exposure.largest_component_notional",
        "Largest capital-exposure graph component notional",
        capital_exposure_graph_summary.get("largest_component_notional_usd"),
        [graph_artifact],
        requires_corroboration=False,
    )
    add(
        "capital_exposure.largest_component_ai_infra_notional",
        "Largest capital-exposure graph component AI-infra-relevant notional",
        capital_exposure_graph_summary.get("largest_component_ai_infra_relevant_notional_usd"),
        [graph_artifact],
        requires_corroboration=False,
    )
    add(
        "capital_exposure.top_ai_infra_component_notional",
        "Top AI-infra capital-exposure component notional",
        capital_exposure_graph_summary.get("top_ai_infra_component_notional_usd"),
        [graph_artifact],
        requires_corroboration=False,
    )
    for key in (
        "top_components_by_notional",
        "top_ai_infra_components_by_notional",
        "top_contagion_hubs",
        "top_ai_infra_contagion_hubs",
        "top_ai_infra_risk_bearers",
        "top_ai_infra_obligors",
        "top_ai_infra_ppa_offtakers",
        "top_ai_infra_ppa_offtaker_families",
    ):
        rows = capital_exposure_graph_summary.get(key, [])
        if not isinstance(rows, list):
            continue
        for index, row in enumerate(rows[:10]):
            if not isinstance(row, dict):
                continue
            row_id = str(
                row.get("component_id") or row.get("node_id") or row.get("family_id") or index
            )
            add(
                f"capital_exposure.{key}.{row_id}.notional",
                f"Capital exposure graph {key} notional",
                row.get("notional_usd") or row.get("incident_notional_usd"),
                [graph_artifact],
                requires_corroboration=False,
            )
            add(
                f"capital_exposure.{key}.{row_id}.ai_infra_notional",
                f"Capital exposure graph {key} AI-infra notional",
                row.get("ai_infra_relevant_notional_usd")
                or row.get("ai_infra_relevant_exposure_usd"),
                [graph_artifact],
                requires_corroboration=False,
            )
            add(
                f"capital_exposure.{key}.{row_id}.ppa_capacity",
                f"Capital exposure graph {key} PPA capacity",
                row.get("ppa_capacity_mw"),
                [graph_artifact],
                unit="MW",
                requires_corroboration=False,
            )
            top_entities = row.get("top_entities", [])
            if isinstance(top_entities, list):
                for entity_index, entity in enumerate(top_entities[:10]):
                    if not isinstance(entity, dict):
                        continue
                    add(
                        (
                            f"capital_exposure.{key}.{row_id}.entity."
                            f"{entity.get('node_id') or entity_index}.exposure"
                        ),
                        "Capital exposure graph top entity exposure",
                        entity.get("exposure_usd"),
                        [graph_artifact],
                        requires_corroboration=False,
                    )

    contagion_artifact = artifact_provenance(
        source_uri="local:data/reports/contract_contagion_summary.json",
        page_or_section="contract contagion path summary",
        payload=contract_contagion_summary,
    )
    top_paths = contract_contagion_summary.get("top_paths", [])
    contagion_path_evidence = row_list_provenance(
        top_paths if isinstance(top_paths, list) else [],
        fallback_section="contract_contagion_summary.top_paths",
    )
    add(
        "contract_contagion.ai_infra_relevant_notional",
        "AI-infra-relevant contract-contagion path notional",
        contract_contagion_summary.get("ai_infra_relevant_notional_usd"),
        [contagion_artifact, *contagion_path_evidence],
    )
    add(
        "contract_contagion.total_path_summed_notional",
        "Contract-contagion path-summed notional",
        contract_contagion_summary.get("total_notional_usd"),
        [contagion_artifact, *contagion_path_evidence],
    )
    compute_artifact = artifact_provenance(
        source_uri="local:compute_economics_metrics",
        page_or_section="compute-economics analyzer rollup",
        payload={
            key: compute_metrics_dict.get(key)
            for key in (
                "total_gpu_capex_usd",
                "compute_asset_count",
                "gpu_price_observation_count",
                "gpu_depreciation_blocked_generation_count",
                "tam_blocked_claim_count",
                "payback_case_count",
                "payback_blocked_case_count",
                "payback_missing_debt_service_count",
                "eps_blocked_impact_count",
                "chip_supply_blocked_observation_count",
            )
        },
    )
    add(
        "compute.total_gpu_capex",
        "Compute-economics total GPU capex estimate",
        compute_metrics_dict.get("total_gpu_capex_usd"),
        [compute_artifact],
        requires_corroboration=False,
    )
    add(
        "compute.gpu_depreciation_blocked_generations",
        "Compute-economics GPU generations missing comparable depreciation inputs",
        compute_metrics_dict.get("gpu_depreciation_blocked_generation_count"),
        [compute_artifact],
        unit="generations",
        requires_corroboration=False,
    )
    add(
        "compute.tam_blocked_claims",
        "Compute-economics TAM claims missing realized-revenue comparators",
        compute_metrics_dict.get("tam_blocked_claim_count"),
        [compute_artifact],
        unit="claims",
        requires_corroboration=False,
    )
    add(
        "compute.payback_blocked_cases",
        "Compute-economics payback cases missing required cash-flow inputs",
        compute_metrics_dict.get("payback_blocked_case_count"),
        [compute_artifact],
        unit="cases",
        requires_corroboration=False,
    )
    add(
        "compute.payback_missing_debt_service_cases",
        "Compute-economics payback cases missing debt-service coverage inputs",
        compute_metrics_dict.get("payback_missing_debt_service_count"),
        [compute_artifact],
        unit="cases",
        requires_corroboration=False,
    )
    add(
        "compute.eps_blocked_impacts",
        "Compute-economics EPS impact cases missing modeled economic depreciation",
        compute_metrics_dict.get("eps_blocked_impact_count"),
        [compute_artifact],
        unit="cases",
        requires_corroboration=False,
    )
    add(
        "compute.chip_supply_blocked_observations",
        "Compute-economics chip-supply observations missing delivered-count comparators",
        compute_metrics_dict.get("chip_supply_blocked_observation_count"),
        [compute_artifact],
        unit="observations",
        requires_corroboration=False,
    )
    capital_metrics = capital_metrics_dict or {}
    capital_metrics_artifact = artifact_provenance(
        source_uri="local:capital_structure_metrics",
        page_or_section="capital-structure analyzer rollup",
        payload={
            key: capital_metrics.get(key)
            for key in (
                "distinct_total_notional_usd",
                "distinct_debt_like_notional_usd",
                "duplicate_candidate_notional_usd",
            )
        },
    )
    add(
        "capital.distinct_total_notional",
        "Distinct capital-structure notional after duplicate-candidate collapse",
        capital_metrics.get("distinct_total_notional_usd"),
        [capital_metrics_artifact],
        requires_corroboration=False,
    )
    capital_scope = capital_scope_summary_dict or {}
    capital_scope_artifact = artifact_provenance(
        source_uri="local:capital_scope_summary",
        page_or_section="capital scope rollup",
        payload={
            key: capital_scope.get(key)
            for key in (
                "out_of_scope_debt_like_notional_usd",
                "balance_sheet_context_debt_like_notional_usd",
            )
        },
    )
    add(
        "capital.out_of_scope_debt_like_notional",
        "Debt-like notional excluded from capital metric scope",
        capital_scope.get("out_of_scope_debt_like_notional_usd"),
        [capital_scope_artifact],
        requires_corroboration=False,
    )
    add(
        "capital.balance_sheet_context_debt_like_notional",
        "Debt-like notional excluded as balance-sheet context rather than committed exposure",
        capital_scope.get("balance_sheet_context_debt_like_notional_usd"),
        [capital_scope_artifact],
        requires_corroboration=False,
    )
    materiality_packet_summary = materiality_adjudication_summary or {}
    materiality_packet_artifact = artifact_provenance(
        source_uri="local:data/reports/materiality_adjudication_summary.json",
        page_or_section="materiality adjudication packet rollup",
        payload={
            key: materiality_packet_summary.get(key)
            for key in (
                "total_exposure_basis_usd",
                "packets",
                "source_backed_packets",
            )
        },
    )
    add(
        "materiality_adjudication.total_exposure_basis_gross",
        "Gross materiality packet exposure basis before metric eligibility and dedupe",
        materiality_packet_summary.get("total_exposure_basis_usd"),
        [materiality_packet_artifact],
        requires_corroboration=False,
    )
    materiality_summary = materiality_adjudication_decision_summary or {}
    materiality_artifact = artifact_provenance(
        source_uri="local:data/reports/materiality_adjudication_decision_summary.json",
        page_or_section="materiality adjudication metric rollup",
        payload={
            key: materiality_summary.get(key)
            for key in (
                "approved_for_metric_use",
                "approved_row_supported_amount_usd",
                "final_metric_supported_amount_usd",
                "final_metric_group_count",
            )
        },
    )
    add(
        "materiality_adjudication.approved_row_supported_amount_gross",
        "Approved materiality row-level supported amount before final metric dedupe",
        materiality_summary.get("approved_row_supported_amount_usd"),
        [materiality_artifact],
        requires_corroboration=False,
    )
    add(
        "materiality_adjudication.final_metric_supported_amount",
        "Broader materiality-adjudicated supported exposure after metric dedupe",
        materiality_summary.get("final_metric_supported_amount_usd"),
        [materiality_artifact],
        requires_corroboration=False,
    )
    relevance_summary = materiality_relevance_summary or {}
    relevance_artifact = artifact_provenance(
        source_uri="local:data/reports/materiality_adjudication_decisions.csv",
        page_or_section="materiality final metric linkage split",
        payload={
            key: relevance_summary.get(key)
            for key in (
                "total_usd",
                "direct_usd",
                "watchlist_usd",
                "established_usd",
                "not_established_usd",
                "final_metric_group_count",
            )
        },
    )
    add(
        "materiality_relevance.direct_ai_linked_amount",
        "Deduped final materiality metric tagged direct AI/data-center linked",
        relevance_summary.get("direct_usd"),
        [relevance_artifact],
        requires_corroboration=False,
    )
    add(
        "materiality_relevance.watchlist_ai_linked_amount",
        "Deduped final materiality metric tagged AI/data-center watchlist linked",
        relevance_summary.get("watchlist_usd"),
        [relevance_artifact],
        requires_corroboration=False,
    )
    add(
        "materiality_relevance.established_ai_linked_amount",
        "Deduped final materiality metric with established AI/data-center linkage",
        relevance_summary.get("established_usd"),
        [relevance_artifact],
        requires_corroboration=False,
    )
    add(
        "materiality_relevance.not_established_amount",
        "Deduped final materiality metric with no established AI/data-center linkage tag",
        relevance_summary.get("not_established_usd"),
        [relevance_artifact],
        requires_corroboration=False,
    )

    # Burry mismatch ratios (the "assumptions baked in, how fragile" claims)
    if mismatch_ratios:
        m = mismatch_ratios
        mismatch_artifact = artifact_provenance(
            source_uri="local:compute_burry_mismatch_ratios",
            page_or_section="Burry separation test mismatch ratios from source-backed debt, compute, physical, and queue artifacts",
            payload=m,
        )

        # Cash flow fragility at realistic utilization
        cf = m.get("cash_flow_mismatch", {})
        if cf.get("median_dscr_at_realistic_util") is not None:
            add(
                "mismatch.cash_flow.dscr_at_realistic_util",
                "Median debt service coverage ratio at conservative realistic sustained utilization (~28%)",
                cf.get("median_dscr_at_realistic_util"),
                [mismatch_artifact],
                unit="ratio",
            )
        if cf.get("median_base_dscr_from_cases") is not None:
            add(
                "mismatch.cash_flow.base_dscr_from_payback_cases",
                "Median base DSCR from source-backed payback / cash flow cases (higher assumed utilization)",
                cf.get("median_base_dscr_from_cases"),
                [mismatch_artifact],
                unit="ratio",
            )

        # Source-backed cluster interest coverage from per-issuer primary filings.
        cdscr = m.get("cluster_interest_coverage", {})
        if cdscr.get("status") == "source_backed":
            add(
                "mismatch.cash_flow.cluster_ebitda_interest_coverage",
                "AI-direct cluster aggregate EBITDA / annual interest expense, from per-issuer "
                "primary 10-K/10-Q financials (adversarially verified). Below ~1 means operations "
                "do not cover interest before any principal; this figure is propped by a single "
                "issuer (negative ex-CoreWeave).",
                cdscr.get("cluster_ebitda_interest_coverage"),
                [mismatch_artifact],
                unit="ratio",
            )

        # Circular / reciprocal vendor financing (NVIDIA supplier-AND-investor round-trips).
        circ = m.get("circular_financing", {})
        if circ.get("status") == "source_backed":
            circ_hub = circ.get("reciprocal_hub") or {}
            verified_loops = circ.get("filing_verified_reciprocal_loops") or []
            loop_edge_rows = [
                edge
                for loop in verified_loops
                for edge in (loop.get("edges") or [])
                if edge.get("source_uri")
            ]
            circ_evidence = [
                mismatch_artifact,
                *row_list_provenance(
                    loop_edge_rows,
                    fallback_section="circular_financing.filing_verified_reciprocal_loops",
                ),
            ]
            if circ_hub.get("filing_verified_reciprocal_capital_usd"):
                add(
                    "mismatch.circular_financing.filing_verified_reciprocal_capital_usd",
                    "NVIDIA equity injected into GPU-cloud customers that ALSO carry a filing-verified "
                    "GPU-purchase return leg (reciprocal / round-trip capital, CoreWeave + Nebius). The "
                    "dominant supplier funds the buyers, so this much take-or-pay demand is not "
                    "arm's-length -- the Lucent/Nortel vendor-financing tell, here partly filing-verified.",
                    circ_hub.get("filing_verified_reciprocal_capital_usd"),
                    circ_evidence,
                    unit="USD",
                )
            if circ_hub.get("filing_verified_round_trip_count"):
                add(
                    "mismatch.circular_financing.filing_verified_round_trip_count",
                    "Count of filing-verified reciprocal loops where NVIDIA is BOTH the dominant GPU "
                    "supplier and an equity investor in the same customer (both legs from primary filings).",
                    circ_hub.get("filing_verified_round_trip_count"),
                    circ_evidence,
                    unit="count",
                )

        # Demand-side (hyperscaler/offtaker) source-backed aggregates.
        dsf = m.get("demand_side_funding", {})
        if dsf.get("status") == "source_backed":
            add(
                "mismatch.demand_side.aggregate_ai_capex_usd",
                "Aggregate AI/data-center capex of the demand-side players (hyperscalers + NVIDIA + "
                "Oracle), from primary 10-K/10-Q. Cash-coverage by operating cash flow is the "
                "bear-vs-bubble test for the demand side.",
                dsf.get("aggregate_ai_capex_usd"),
                [mismatch_artifact],
                unit="USD",
            )
            add(
                "mismatch.demand_side.aggregate_datacenter_purchase_commitments_usd",
                "Aggregate datacenter purchase/take-or-pay commitments of the demand-side players "
                "(upper bound on the contracted revenue that could flow to the financed core).",
                dsf.get("aggregate_datacenter_purchase_commitments_usd"),
                [mismatch_artifact],
                unit="USD",
            )

        # Power / ratepayer exposure (the ratepayer leg of who-bears-downside).
        pwr = m.get("power_ratepayer_exposure", {})
        if pwr.get("status") == "source_backed" and pwr.get("ratepayer_socialized_usd"):
            add(
                "mismatch.power.ratepayer_socialized_usd",
                "AI-datacenter generation/grid build socialized to RATEPAYERS (general rate base "
                "incl. half of mixed), from utility 10-Ks + PUC dockets. The hidden downside leg: "
                "ordinary ratepayers, not the AI buildout, bear the stranded-asset risk.",
                pwr.get("ratepayer_socialized_usd"),
                [mismatch_artifact],
                unit="USD",
            )

        # Ultimate end-holders (who really bears the loss). Audit the share of
        # disclosed holders routed to households (insurer/pension/index funds).
        eh = m.get("ultimate_end_holders", {})
        if eh.get("status") == "source_backed" and eh.get("household_routed_count_pct") is not None:
            add(
                "mismatch.end_holders.household_routed_count_pct",
                "Share of DISCLOSED end-holders (SEC 13F-HR / SC 13G-13D / S-1 & 10-K beneficial "
                "ownership) of the AI-direct cluster's public securities that route to households "
                "(insurers / pensions / passive index funds). The final leg of who-bears-downside. "
                "Coverage is partial: private-placement DDTL/SPV debt holders are not 13-F-visible.",
                eh.get("household_routed_count_pct"),
                [mismatch_artifact],
                unit="percent",
            )
            add(
                "mismatch.end_holders.filing_verified_holders",
                "Count of cluster-security holders independently tied to a specific SEC ownership "
                "filing (exact share/percent match) — the evidentiary base of the end-holder leg.",
                eh.get("filing_verified_holders"),
                [mismatch_artifact],
                unit="count",
            )

        # Forensic red-flag scorecard (per-issuer Burry checklist from filings).
        rfs = m.get("red_flag_scorecard", {})
        if rfs.get("status") == "source_backed":
            add(
                "mismatch.red_flags.issuers_with_serious_accounting_flag",
                "Count of financed-cluster issuers carrying a filing-tied SERIOUS accounting red flag "
                "(going-concern doubt / material weakness in internal controls / restatement / auditor "
                "change), from per-issuer SEC filings (adversarially verified; unsourced serious flags "
                "rejected). A pervasive serious-flag rate is a systemic forensic tell, not idiosyncratic.",
                len(rfs.get("issuers_with_serious_accounting_flag") or []),
                [mismatch_artifact],
                unit="count",
            )
            add(
                "mismatch.red_flags.filing_verified_present_flags",
                "Total PRESENT red flags across the cluster tied to a specific SEC filing (the "
                "evidentiary base of the forensic scorecard; absent/unsourced flags do not count).",
                rfs.get("filing_verified_present_flags"),
                [mismatch_artifact],
                unit="count",
            )

        # Satellite construction-progress: Sentinel-2 change detection on announced sites.
        sat = m.get("satellite_construction", {})
        if sat.get("status") == "source_backed" and sat.get("active_construction_pct") is not None:
            add(
                "mismatch.satellite.active_construction_pct",
                "Share of announced AI data-center mega-sites showing ACTIVE construction / built-up "
                "change on Sentinel-2 before/after imagery (NDVI down + bare/built-up up). A primary, "
                "non-filing physical check: a low rate means most announced capacity shows no ground "
                "footprint yet -- the announced-but-not-built physical-mismatch signal. (Cloud/seasonal "
                "noise applies; read with the tracker construction-status proxy.)",
                sat.get("active_construction_pct"),
                [mismatch_artifact],
                unit="percent",
            )
            add(
                "mismatch.satellite.no_change_sites",
                "Count of satellite-observed AI mega-sites with NO significant ground change between "
                "the before/after windows -- the high-capacity ones are the clearest stranding / "
                "timeline-slippage tells.",
                sat.get("no_change_sites"),
                [mismatch_artifact],
                unit="count",
            )

        # Production Neo4j graph backend: the capital-exposure graph loaded + analyzed in-DB.
        n4 = m.get("neo4j_production_graph", {})
        load_block = n4.get("load") or {}
        if load_block.get("status") == "loaded":
            add(
                "mismatch.neo4j.edges_in_db",
                "Capital-exposure graph edges loaded into the PRODUCTION Neo4j store and verified "
                "in-database (the graph engine is now Neo4j-backed, not only CSV/in-memory). Native "
                "Cypher analytics run in the DB; the AI-infra mass computed in Neo4j cross-validates "
                "the in-code figure.",
                load_block.get("edges_in_db"),
                [mismatch_artifact],
                unit="count",
            )

        # Graph Data Science: weighted-PageRank systemic centrality over the graph.
        gc = m.get("graph_systemic_centrality", {})
        if gc.get("status") == "source_backed" and gc.get("node_count"):
            add(
                "mismatch.graph_centrality.node_count",
                "Nodes scored by notional-weighted PageRank systemic centrality over the source-backed "
                "capital-exposure graph (GDS algorithm, deterministic in-code). The top_systemic_nodes "
                "are the entities whose distress propagates most widely; ecosystem-wide these are the "
                "major utility/energy counterparties (the broad corpus is mostly non-AI), while the "
                "AI-cluster-specific systemic nodes (NVIDIA/Microsoft/shared lenders) are in the "
                "contagion-hub layer.",
                gc.get("node_count"),
                [mismatch_artifact],
                unit="count",
            )

        # Forensic fragility: first-principles tipping conditions met (no borrowed thresholds).
        fs = m.get("fragility_scorecard", {})
        if fs.get("status") == "source_backed":
            add(
                "mismatch.fragility.first_principles_conditions_met",
                "Number of DEFENSIBLE first-principles economic tipping conditions satisfied by the "
                "data (debt outlives GPU collateral; a single customer is >50% of revenue; the majority "
                "of announced capacity is un-built). External-framework numeric thresholds are NOT "
                "adopted; recourse + tail-size have no principled binary and report magnitude instead "
                "(both show the loss is bounded -- parent-equity-borne, small leveraged tail).",
                fs.get("first_principles_conditions_met"),
                [mismatch_artifact],
                unit="count",
            )

        # Verified cluster extension (new members, recourse disentangled from JV).
        cx = m.get("cluster_extension", {})
        if cx.get("status") == "source_backed":
            add(
                "mismatch.cluster_extension.new_recourse_debt_usd",
                "RECOURSE debt added by the verified new financed-cluster members (Crusoe, EdgeConneX, "
                "Bitfarms, Bit Digital), with non-recourse JV/project-SPV debt disentangled out (e.g. "
                "Crusoe's ~$9.6B Oracle-lease JV debt excluded). The honest increment to the cluster's "
                "recourse leverage -- the headline associated debt is far larger.",
                cx.get("new_recourse_debt_usd"),
                [mismatch_artifact],
                unit="USD",
            )

        # GPU depreciation earnings-quality (restate D&A at economic life).
        geq = m.get("gpu_earnings_quality", {})
        if geq.get("status") == "source_backed" and geq.get("issuers_with_restatement"):
            add(
                "mismatch.gpu_earnings.cluster_da_understatement_usd",
                "Annual depreciation the cluster UNDERSTATES by booking GPUs over 5-6+yr vs their ~3yr "
                "economic life (restated on the source-backed compute PP&E). This much pre-tax earnings "
                "is overstated each year -- honest depreciation makes the cash-flow-negative cluster "
                "look worse. Economic life is a labeled assumption; PP&E + useful life are primary.",
                geq.get("cluster_annual_da_understatement_usd"),
                [mismatch_artifact],
                unit="USD",
            )

        # Capture-recapture estimate of the TRUE universe (INFERRED-capped extrapolation).
        ux = m.get("universe_extrapolation", {})
        if ux.get("status") == "inferred_capped" and ux.get("estimated_true_universe_mid"):
            add(
                "mismatch.universe_extrapolation.estimated_true_universe_mid",
                "Capture-recapture (Chapman) estimate of the TRUE AI-infra entity universe from "
                "overlapping observable sources -- a principled population estimate (NOT an assumed "
                "fraction), CAPPED at INFERRED tier (<=0.45). The load-bearing point: even at the "
                "estimated true size, the distress cluster stays a small bounded share, so the scoped "
                "(not ecosystem-wide) conclusion survives the unobserved. Near-disjoint source pairs "
                "excluded; never drives the verdict.",
                ux.get("estimated_true_universe_mid"),
                [mismatch_artifact],
                unit="count",
            )

        # Empirical entity-universe composition (deep-modeled count + structural split).
        eum = m.get("entity_universe_map", {})
        if eum.get("status") == "source_backed":
            add(
                "mismatch.entity_universe.classified_count",
                "Count of data-derived AI-infra entities (project owners + capital-graph AI nodes + "
                "boundary sweep) classified into structural buckets, each with a sourced bucket + "
                "public-filer status + AI-infra-debt flag. The deep-modeled entity universe; most are "
                "demand/power/supply/private context, NOT the leveraged-distress thesis.",
                eum.get("entity_count"),
                [mismatch_artifact],
                unit="count",
            )
            add(
                "mismatch.entity_universe.confirmed_financed_leveraged",
                "Adversarially-confirmed financed_ai_infra_leveraged entities across the whole universe "
                "-- the empirical size of the bubble-distress cluster (vs hyperscaler-demand / REIT / "
                "utility / supplier / crypto / private-developer buckets).",
                eum.get("confirmed_financed_leveraged_count"),
                [mismatch_artifact],
                unit="count",
            )

        # Unsupervised cluster discovery (data-driven boundary, not asserted).
        cdsc = m.get("cluster_discovery", {})
        if cdsc.get("status") == "source_backed":
            add(
                "mismatch.cluster_discovery.fragile_cluster_size",
                "Size of the DISCOVERED fragile (cash-flow-negative / sub-1x-coverage) sub-cluster from "
                "unsupervised clustering of the public issuers' scale-free financials (StandardScaler -> "
                "PCA -> KMeans, k by silhouette + GMM BIC, bootstrap-stability checked). Membership is "
                "discovered then labelled, NOT hand-picked; at small n read with the silhouette + "
                f"stability ({cdsc.get('bootstrap_stability')}).",
                len(cdsc.get("fragile_cluster_members") or []),
                [mismatch_artifact],
                unit="count",
            )

        # Named refinancing wall (specific near-term maturities from the census).
        rw = m.get("refi_wall", {})
        if rw.get("status") == "source_backed":
            add(
                "mismatch.refi_wall.near_term_2025_2027_usd",
                "Cluster debt maturing near-term (2025-2027) from the primary-sourced census, named at "
                "the facility level -- the specific refinancing the negative-carry issuers must roll "
                "(see near_term_named_facilities + most-exposed issuers for the entity detail).",
                rw.get("near_term_2025_2027_usd"),
                [mismatch_artifact],
                unit="USD",
            )
            add(
                "mismatch.refi_wall.peak_year_usd",
                f"Largest single maturity-year wall (peak {rw.get('peak_maturity_year')}) in the dated "
                "census facilities -- where the bulk of the refinancing risk concentrates.",
                rw.get("peak_year_usd"),
                [mismatch_artifact],
                unit="USD",
            )

        # Cluster-boundary test (is the financed-AI cluster bounded?).
        cb = m.get("cluster_boundary", {})
        if cb.get("status") == "source_backed":
            add(
                "mismatch.cluster_boundary.qualify_rate_pct",
                "Share of adjacent candidate names (crypto-miners / HPC pivots probed near the cluster) "
                "that qualify as GENUINE financed AI-infra under the adversarial in-scope gate. A low "
                "rate is a scoping finding: the financed-AI cluster is bounded and specific, reinforcing "
                "the scoped (not ecosystem-wide) verdict rather than enlarging the cluster.",
                cb.get("qualify_rate_pct"),
                [mismatch_artifact],
                unit="percent",
            )

        # Contract-level recourse structure (who bears the loss, from the agreements).
        cs = m.get("contract_structure", {})
        if cs.get("status") == "source_backed":
            add(
                "mismatch.contract_structure.filing_verified_facilities",
                "Number of cluster debt facilities whose recourse / guarantee / SPV / collateral "
                "structure was verified against the actual credit-agreement or guaranty exhibit. The "
                "contract-level basis for who-bears-downside (parent equity vs ring-fenced SPV "
                "creditors); non-recourse / bankruptcy-remote claims rejected unless the document "
                "states them.",
                cs.get("filing_verified_facilities"),
                [mismatch_artifact],
                unit="count",
            )
            add(
                "mismatch.contract_structure.gpu_collateralized_facilities",
                "Number of contract-verified facilities explicitly secured by GPUs -- the collateral "
                "whose recovery value the GPU-depreciation-gap leg puts in question.",
                cs.get("gpu_collateralized_facilities"),
                [mismatch_artifact],
                unit="count",
            )

        # Per-entity weakest-links ranking (who cracks first).
        err = m.get("entity_risk_ranking", {})
        if err.get("status") == "source_backed":
            add(
                "mismatch.entity_ranking.entities_ranked",
                "Number of cluster entities ranked by a composite of filing-verified forensic red-flag "
                "score + financial fragility (negative EBITDA / net loss / leverage). The per-entity "
                "weakest-links view: the top names are where a distress event is most likely to surface "
                "first; each entity's concerns trace to the red-flag and financials layers.",
                err.get("entity_count"),
                [mismatch_artifact],
                unit="count",
            )

        # Utilization vs debt-service mismatch (deal/entity-level).
        uds = m.get("utilization_debt_service", {})
        if uds.get("status") == "source_backed":
            if uds.get("median_contracted_coverage_ratio") is not None:
                add(
                    "mismatch.utilization.median_contracted_coverage_ratio",
                    "Median ratio of contracted revenue run-rate to annual debt service across the "
                    "issuers that filed both (deal/entity-level). <1x means even fully-utilized "
                    "contracted backlog does not cover the obligations. Only filing-verified inputs "
                    "contribute; numerator/denominator kind labeled, nothing invented.",
                    uds.get("median_contracted_coverage_ratio"),
                    [mismatch_artifact],
                    unit="ratio",
                )
            add(
                "mismatch.utilization.issuers_contracted_coverage_below_1",
                "Count of issuers whose CONTRACTED revenue is below their debt service (coverage < 1x) "
                "-- a structural mismatch independent of a utilization-miss tail.",
                uds.get("issuers_contracted_coverage_below_1"),
                [mismatch_artifact],
                unit="count",
            )

        # Top actionable-risk register (cross-layer synthesis).
        rr = m.get("risk_register", {})
        if rr.get("status") == "source_backed":
            add(
                "mismatch.risk_register.severity_5_count",
                "Count of severity-5 (highest) risks in the ranked cross-layer risk register, each "
                "anchored to a source-backed computed number across the verified layers "
                "(cash-flow/refi/concentration/contagion/forensic). Synthesis for an analyst, not a "
                "new claim -- every anchor traces to its layer's evidence.",
                rr.get("severity_5_count"),
                [mismatch_artifact],
                unit="count",
            )
            add(
                "mismatch.risk_register.source_backed_risk_count",
                "Number of top risks whose evidence anchor is source-backed (vs illustrative) in the "
                "ranked register.",
                rr.get("source_backed_risk_count"),
                [mismatch_artifact],
                unit="count",
            )

        # Debt-side funding routing (who funds the lenders that hold cluster debt).
        pcf = m.get("private_credit_funding", {})
        if pcf.get("status") == "source_backed":
            if pcf.get("median_insurance_funded_share_pct") is not None:
                add(
                    "mismatch.private_credit.median_insurance_funded_share_pct",
                    "Median insurance/annuity-funded share of the cluster private-credit lenders' "
                    "credit capital (from the lenders' own 10-Ks/earnings; e.g. Apollo/Athene, "
                    "Blackstone, KKR/Global Atlantic). High = the cluster's private-placement DEBT "
                    "loss routes to policyholders/retirees -- the debt-side leg of who-bears-downside "
                    "that 13-F equity data cannot show. Aggregate funding mix, not per-facility.",
                    pcf.get("median_insurance_funded_share_pct"),
                    [mismatch_artifact],
                    unit="percent",
                )
            add(
                "mismatch.private_credit.lenders_with_household_routed_funding",
                "Count of cluster private-credit lenders drawing a material share of credit capital "
                "from insurance/annuity or pension balance sheets (loss routes to households).",
                pcf.get("lenders_with_household_routed_funding"),
                [mismatch_artifact],
                unit="count",
            )

        # Supply-side equipment bottlenecks (can they physically build it). Audit
        # the count of verified chokepoints that gate the buildout + max lead time.
        equip = m.get("equipment_bottlenecks", {})
        if equip.get("status") == "source_backed":
            add(
                "mismatch.equipment.gating_chokepoint_count",
                "Number of AI data-center supply-chain chokepoints (TSMC CoWoS, HBM, GPUs, gas "
                "turbines, transformers, gensets, cooling, electrical labor) that are BOTH a "
                "hard/material constraint AND gate the buildout, from supplier filings (10-K/10-Q/"
                "earnings calls, adversarially verified). A physical cap on revenue conversion "
                "independent of demand or financing; single-source gates propagate a shock to all "
                "downstream issuers at once.",
                equip.get("gating_chokepoint_count"),
                [mismatch_artifact],
                unit="count",
            )
            if equip.get("max_lead_time_months") is not None:
                add(
                    "mismatch.equipment.max_lead_time_months",
                    "Longest verified equipment lead time across the gating chokepoints (months) — "
                    "the slowest physical input the announced buildout must wait on.",
                    equip.get("max_lead_time_months"),
                    [mismatch_artifact],
                    unit="months",
                )

        # Forward cash-flow stress (how severely it cracks). Audit the adverse-case
        # cluster coverage and breach count from the source-backed base financials.
        sstress = m.get("scenario_stress", {})
        if sstress.get("status") == "source_backed":
            adverse: dict[str, Any] = next(
                (s for s in (sstress.get("scenarios") or []) if s.get("scenario") == "adverse"),
                {},
            )
            if adverse.get("cluster_stressed_interest_coverage") is not None:
                add(
                    "mismatch.scenario_stress.adverse_cluster_coverage",
                    "Cluster interest coverage under the ADVERSE scenario (25% utilization miss + "
                    "200bp rate shock + GPU-life compression) on the source-backed 11-issuer "
                    "financials; <1x = the financed core cannot cover interest under a moderate "
                    "demand/financing shock. Stress params are labeled assumptions; base is primary.",
                    adverse.get("cluster_stressed_interest_coverage"),
                    [mismatch_artifact],
                    unit="ratio",
                )
                add(
                    "mismatch.scenario_stress.adverse_issuers_breaching",
                    "Number of issuers breaching (coverage<1 or negative EBITDA) under the adverse "
                    "scenario — the count of the financed cluster pushed into distress by a moderate, "
                    "non-tail shock.",
                    adverse.get("issuers_breaching"),
                    [mismatch_artifact],
                    unit="count",
                )

        # Physical deliverability mismatch. We audit the honest tracker
        # construction-status proxy, NOT the strong-queue-match figure (which is
        # a coverage-limited join artifact until the ISO queues are ingested).
        phys = m.get("physical_mismatch", {})
        if phys.get("announced_only_mw_pct") is not None:
            add(
                "mismatch.physical.announced_only_mw_pct",
                "% of tracker-announced AI/data-center MW still only announced (not built/under "
                "construction); high = stranding/timeline-slippage risk. Non-primary tracker status; "
                "a firm-vs-queue rate needs load-interconnection data (the ingested ISO queues are "
                "generation-side, a weak lens for data-center load).",
                phys.get("announced_only_mw_pct"),
                [mismatch_artifact],
                unit="percent",
            )

        # GPU life / depreciation assumption fragility
        gpu = m.get("gpu_economics_mismatch", {})
        if gpu.get("median_useful_life_gap_years") is not None:
            add(
                "mismatch.gpu.useful_life_gap_years",
                "Median gap between accounting useful life and observed economic/secondary market life (positive = overstated asset life)",
                gpu.get("median_useful_life_gap_years"),
                [mismatch_artifact],
                unit="years",
            )

        # Debt missing rate (interest rate assumption fragility on the wall)
        debt = m.get("debt_refinancing_mismatch", {})
        if debt.get("missing_rate_pct_of_debt_like_notional") is not None:
            add(
                "mismatch.debt.missing_explicit_rate_pct",
                "% of debt-like notional lacking explicit interest rate (hidden burden + refi fragility)",
                debt.get("missing_rate_pct_of_debt_like_notional"),
                [mismatch_artifact],
                unit="percent",
            )

    return audits


def load_report_capital_evidence(data_dirs: list[str]) -> CapitalEvidenceBatch:
    """Load all report-ready deal CSVs under known acquisition/evidence directories."""

    deals = []
    seen: set[str] = set()
    for root in data_dirs:
        base = Path(root)
        for directory in [
            base / "capital",
            base / "edgar_acquisition",
        ]:
            deals_csv = directory / "deals.csv"
            if not deals_csv.exists():
                continue
            batch = load_capital_evidence(directory)
            for deal in batch.deals:
                key = deal.source_deal_id or f"{deal.provenance.source_uri}:{deal.title}"
                if key in seen:
                    continue
                seen.add(key)
                deals.append(deal)
    return CapitalEvidenceBatch(deals=deals)


def load_report_compute_economics(data_dirs: list[str]) -> ComputeEconomicsBatch:
    """Load all report-ready compute economics evidence under known data directories."""

    batches = []
    for root in data_dirs:
        compute_dir = Path(root) / "compute"
        if compute_dir.exists():
            batches.append(load_compute_economics(compute_dir))
    return merge_compute_economics_batches(batches) if batches else empty_compute_economics_batch()


def load_queue_project_match_summary(data_dirs: list[str]) -> dict[str, Any]:
    """Load optional queue-to-project match summary emitted by the matcher script."""

    for root in data_dirs:
        summary_path = Path(root) / "reports" / "queue_project_match_summary.json"
        if summary_path.exists():
            loaded = json.loads(summary_path.read_text())
            if isinstance(loaded, dict):
                return loaded
    return {}


def load_physical_record_match_summary(data_dirs: list[str]) -> dict[str, Any]:
    """Load optional permit/equipment-to-project match summary emitted by the matcher."""

    for root in data_dirs:
        summary_path = Path(root) / "reports" / "physical_record_match_summary.json"
        if summary_path.exists():
            loaded = json.loads(summary_path.read_text())
            if isinstance(loaded, dict):
                return loaded
    return {}


def load_entity_universe_summary(data_dirs: list[str]) -> dict[str, Any]:
    """Load optional source-backed entity universe summary."""

    for root in data_dirs:
        summary_path = Path(root) / "entity_universe" / "entity_universe.summary.json"
        if summary_path.exists():
            loaded = json.loads(summary_path.read_text())
            if isinstance(loaded, dict):
                return loaded
    return {}


def load_capital_exposure_graph_summary(data_dirs: list[str]) -> dict[str, Any]:
    """Load optional source-backed capital exposure graph summary."""

    for root in data_dirs:
        summary_path = Path(root) / "graph" / "capital_exposure_graph_summary.json"
        if summary_path.exists():
            loaded = json.loads(summary_path.read_text())
            if isinstance(loaded, dict):
                return loaded
    return {}


def load_graph_centrality(data_dirs: list[str]) -> dict[str, Any]:
    """Load optional weighted-PageRank systemic-centrality artifact."""

    for root in data_dirs:
        path = Path(root) / "graph" / "graph_centrality.json"
        if path.exists():
            loaded = json.loads(path.read_text())
            if isinstance(loaded, dict):
                return loaded
    return {}


def load_neo4j_analytics(data_dirs: list[str]) -> dict[str, Any]:
    """Load optional production-Neo4j load + in-database analytics artifact."""

    for root in data_dirs:
        path = Path(root) / "graph" / "neo4j_analytics.json"
        if path.exists():
            loaded = json.loads(path.read_text())
            if isinstance(loaded, dict):
                return loaded
    return {}


def load_ownership_graph_summary(data_dirs: list[str]) -> dict[str, Any]:
    """Load optional source-backed ownership/consolidation graph summary."""

    for root in data_dirs:
        summary_path = Path(root) / "graph" / "ownership_graph_summary.json"
        if summary_path.exists():
            loaded = json.loads(summary_path.read_text())
            if isinstance(loaded, dict):
                return loaded
    return {}


def load_weak_link_summary(data_dirs: list[str]) -> dict[str, Any]:
    """Load optional weak-link summary emitted by the weak-link builder."""

    for root in data_dirs:
        summary_path = Path(root) / "reports" / "weak_link_summary.json"
        if summary_path.exists():
            loaded = json.loads(summary_path.read_text())
            if isinstance(loaded, dict):
                return loaded
    return {}


def load_contract_contagion_summary(data_dirs: list[str]) -> dict[str, Any]:
    """Load optional source-backed contract/ownership contagion path summary."""

    for root in data_dirs:
        summary_path = Path(root) / "reports" / "contract_contagion_summary.json"
        if summary_path.exists():
            loaded = json.loads(summary_path.read_text())
            if isinstance(loaded, dict):
                return loaded
    return {}


def load_review_queue_summary(data_dirs: list[str]) -> dict[str, Any]:
    """Load optional source-backed LLM adjudication queue summary."""

    for root in data_dirs:
        summary_path = Path(root) / "reports" / "review_queue_summary.json"
        if summary_path.exists():
            loaded = json.loads(summary_path.read_text())
            if isinstance(loaded, dict):
                return loaded
    return {}


def load_materiality_adjudication_summary(data_dirs: list[str]) -> dict[str, Any]:
    """Load optional materiality-ranked LLM adjudication packet summary."""

    for root in data_dirs:
        summary_path = Path(root) / "reports" / "materiality_adjudication_summary.json"
        if summary_path.exists():
            loaded = json.loads(summary_path.read_text())
            if isinstance(loaded, dict):
                return loaded
    return {}


def load_materiality_adjudication_decision_summary(data_dirs: list[str]) -> dict[str, Any]:
    """Load optional automated materiality adjudication decision summary."""

    for root in data_dirs:
        summary_path = Path(root) / "reports" / "materiality_adjudication_decision_summary.json"
        if summary_path.exists():
            loaded = json.loads(summary_path.read_text())
            if isinstance(loaded, dict):
                return loaded
    return {}


def load_materiality_adjudication_decisions(data_dirs: list[str]) -> list[dict[str, str]]:
    """Load automated materiality adjudication decision rows for report QA."""

    for root in data_dirs:
        decisions_path = Path(root) / "reports" / "materiality_adjudication_decisions.csv"
        if not decisions_path.exists():
            continue
        with decisions_path.open(newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    return []


def _float_value(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def capital_materiality_scope_fields(
    *,
    capital_debt_like_notional_usd: float,
    materiality_decision_summary: dict[str, Any],
) -> dict[str, Any]:
    """Label the two report size metrics so they are not read as contradictions."""

    materiality_final = _float_value(
        materiality_decision_summary.get("final_metric_supported_amount_usd")
    )
    scope_ratio = (
        round(materiality_final / capital_debt_like_notional_usd, 4)
        if capital_debt_like_notional_usd
        else 0.0
    )
    return {
        "capital_metric_scope": "curated_capital_structure_deal_graph",
        "materiality_metric_scope": ("broader_materiality_adjudication_supported_exposure"),
        "materiality_final_metric_supported_amount_usd": materiality_final,
        "materiality_final_metric_group_count": materiality_decision_summary.get(
            "final_metric_group_count",
            0,
        ),
        "capital_to_materiality_scope_ratio": scope_ratio,
        "metric_scope_note": (
            "current_debt_like_notional_usd is the curated capital-structure "
            "deal-graph estimate. materiality_final_metric_supported_amount_usd "
            "is a broader adjudicated source-backed support total after "
            "source-instrument and economic-obligation dedupe; it is not directly "
            "additive to, or a contradiction of, the curated capital-structure metric."
        ),
    }


def materiality_relevance_scope_fields(
    materiality_relevance_summary: dict[str, Any],
) -> dict[str, Any]:
    """Label the thesis-scope split inside the broader materiality metric."""

    return {
        "materiality_relevance_scope": ("deduped_final_metric_split_by_ai_data_center_linkage"),
        "materiality_direct_ai_linked_usd": materiality_relevance_summary.get(
            "direct_usd",
            0,
        ),
        "materiality_watchlist_ai_linked_usd": materiality_relevance_summary.get(
            "watchlist_usd",
            0,
        ),
        "materiality_established_ai_linked_usd": materiality_relevance_summary.get(
            "established_usd",
            0,
        ),
        "materiality_not_established_linkage_usd": materiality_relevance_summary.get(
            "not_established_usd",
            0,
        ),
        "materiality_direct_ai_linked_pct": materiality_relevance_summary.get(
            "direct_pct",
            0,
        ),
        "materiality_established_ai_linked_pct": materiality_relevance_summary.get(
            "established_pct",
            0,
        ),
        "materiality_not_established_linkage_pct": materiality_relevance_summary.get(
            "not_established_pct",
            0,
        ),
        "metric_relevance_note": (
            "The broader materiality metric is split by current adjudicated "
            "AI/data-center linkage. direct and watchlist rows are established "
            "thesis-linked support; not_established rows are source-backed "
            "obligations whose AI/data-center linkage has not yet been proven and "
            "must not be described as direct AI-bubble leverage."
        ),
    }


def _pct(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def debt_service_timing_coverage_fields(
    debt_service_metrics_dict: dict[str, Any],
) -> dict[str, Any]:
    """Summarize maturity/rate coverage limits for the crack-window answer."""

    distinct_obligations = int(
        _float_value(debt_service_metrics_dict.get("distinct_obligations_count"))
    )
    distinct_missing_maturity = int(
        _float_value(debt_service_metrics_dict.get("distinct_obligations_missing_maturity_count"))
    )
    distinct_debt_like_notional = _float_value(
        debt_service_metrics_dict.get("distinct_debt_like_notional_usd")
    )
    distinct_missing_maturity_notional = _float_value(
        debt_service_metrics_dict.get("distinct_notional_missing_maturity_usd")
    )
    distinct_missing_rate_notional = _float_value(
        debt_service_metrics_dict.get("distinct_missing_rate_notional_usd")
    )
    measured_rate_coverage_pct = _float_value(
        debt_service_metrics_dict.get("distinct_measured_rate_notional_coverage_pct")
    )
    maturity_covered_obligations = max(distinct_obligations - distinct_missing_maturity, 0)
    maturity_covered_notional = max(
        distinct_debt_like_notional - distinct_missing_maturity_notional,
        0.0,
    )

    return {
        "current_distinct_debt_service_obligations": distinct_obligations,
        "current_distinct_debt_service_obligations_missing_maturity": (distinct_missing_maturity),
        "current_distinct_debt_service_maturity_obligation_coverage_pct": _pct(
            maturity_covered_obligations,
            distinct_obligations,
        ),
        "current_distinct_debt_service_debt_like_notional_usd": distinct_debt_like_notional,
        "current_distinct_debt_service_notional_missing_maturity_usd": (
            distinct_missing_maturity_notional
        ),
        "current_distinct_debt_service_maturity_notional_coverage_pct": _pct(
            maturity_covered_notional,
            distinct_debt_like_notional,
        ),
        "current_distinct_debt_service_missing_rate_notional_usd": (distinct_missing_rate_notional),
        "current_distinct_debt_service_measured_rate_notional_coverage_pct": (
            measured_rate_coverage_pct
        ),
        "current_timing_maturity_wall_coverage_note": (
            "The crack-window maturity wall is a floor, not a complete schedule: "
            f"{distinct_missing_maturity:,} of {distinct_obligations:,} distinct debt-service "
            f"obligations and ${distinct_missing_maturity_notional:,.0f} of distinct "
            "debt-like notional still lack maturity-date evidence; distinct measured-rate "
            f"notional coverage is {measured_rate_coverage_pct:.2f}%."
        ),
    }


def graph_parity_basis_fields(
    *,
    capital_exposure_graph_summary: dict[str, Any],
    contract_contagion_summary: dict[str, Any],
    review_queue_summary: dict[str, Any],
) -> dict[str, Any]:
    """Label graph notional bases so path sums are not read as exposures."""

    contract_paths = int(_float_value(contract_contagion_summary.get("paths")))
    contract_ai_paths = int(_float_value(contract_contagion_summary.get("ai_infra_relevant_paths")))
    contract_total_notional = _float_value(contract_contagion_summary.get("total_notional_usd"))
    contract_ai_notional = _float_value(
        contract_contagion_summary.get("ai_infra_relevant_notional_usd")
    )
    capital_total_notional = _float_value(
        capital_exposure_graph_summary.get("total_edge_notional_usd")
    )
    capital_ai_notional = _float_value(
        capital_exposure_graph_summary.get("ai_infra_relevant_notional_usd")
    )
    distinct_ai_reconciler = _float_value(
        review_queue_summary.get("pending_ai_infra_relevant_capital_distinct_notional_amount_usd")
    )

    return {
        "current_capital_exposure_notional_basis": ("deduped_edge_level_financing_notional"),
        "current_capital_exposure_total_edge_notional_usd": capital_total_notional,
        "current_capital_exposure_ai_infra_relevant_notional_usd": capital_ai_notional,
        "current_contract_contagion_notional_basis": (
            "path_summed_multiplicity_inflated_not_exposure"
        ),
        "current_contract_contagion_total_notional_usd": contract_total_notional,
        "current_contract_contagion_path_count": contract_paths,
        "current_contract_contagion_average_path_notional_usd": _safe_average(
            contract_total_notional,
            contract_paths,
        ),
        "current_contract_contagion_ai_infra_notional_basis": (
            "path_summed_multiplicity_inflated_not_exposure"
        ),
        "current_contract_contagion_ai_infra_relevant_notional_usd": contract_ai_notional,
        "current_contract_contagion_ai_infra_path_count": contract_ai_paths,
        "current_contract_contagion_ai_infra_average_path_notional_usd": _safe_average(
            contract_ai_notional,
            contract_ai_paths,
        ),
        "current_ai_infra_distinct_capital_reconciler_notional_usd": distinct_ai_reconciler,
        "current_ai_infra_distinct_capital_reconciler_basis": (
            "deduped_distinct_pending_capital_notional_not_path_summed"
        ),
        "current_graph_parity_note": (
            "Capital graph notional is deduped edge-level financing exposure; "
            "contract-contagion notional is path-summed across graph paths and "
            "is multiplicity-inflated, so it must not be quoted as headline "
            "AI/data-center exposure. Use the distinct AI-infra pending-capital "
            "basis as the cross-layer reconciler."
        ),
    }


def _safe_average(total: float, count: int) -> float:
    if count <= 0:
        return 0.0
    return round(total / count, 2)


def materiality_semantic_summary(decisions: list[dict[str, str]]) -> dict[str, Any]:
    """Summarize semantic validity for approved materiality metric rows."""

    approved_rows = [
        row
        for row in decisions
        if row.get("decision") == "approved_for_metric_use"
        or row.get("metric_use_status") == "approved_for_metric_use"
    ]
    bucket_counts = {bucket.value: 0 for bucket in SemanticEvidenceBucket}
    top_semantic_flags: list[dict[str, Any]] = []
    top_indeterminate: list[dict[str, Any]] = []

    for row in approved_rows:
        semantic_text = " ".join(
            value
            for value in (
                row.get("evidence_quote", ""),
                row.get("packet_reason", ""),
                row.get("rationale", ""),
            )
            if value
        )
        bucket = classify_claim_semantics(semantic_text)
        bucket_counts[bucket.value] += 1
        if bucket in {
            SemanticEvidenceBucket.ASSET_OR_CAPACITY,
            SemanticEvidenceBucket.EQUITY_OR_PRODUCTION,
            SemanticEvidenceBucket.BOILERPLATE_ONLY,
        }:
            top_semantic_flags.append(_materiality_semantic_row(row, bucket))
        elif bucket == SemanticEvidenceBucket.INDETERMINATE:
            top_indeterminate.append(_materiality_semantic_row(row, bucket))

    return {
        "approved_metric_rows_scanned": len(approved_rows),
        "semantic_committed_debt_rows": bucket_counts[SemanticEvidenceBucket.COMMITTED_DEBT.value],
        "semantic_asset_or_capacity_rows": bucket_counts[
            SemanticEvidenceBucket.ASSET_OR_CAPACITY.value
        ],
        "semantic_equity_or_production_rows": bucket_counts[
            SemanticEvidenceBucket.EQUITY_OR_PRODUCTION.value
        ],
        "semantic_boilerplate_rows": bucket_counts[SemanticEvidenceBucket.BOILERPLATE_ONLY.value],
        "semantic_indeterminate_rows": bucket_counts[SemanticEvidenceBucket.INDETERMINATE.value],
        "semantic_not_evaluated_rows": bucket_counts[SemanticEvidenceBucket.NOT_EVALUATED.value],
        "semantic_hard_flag_rows": (
            bucket_counts[SemanticEvidenceBucket.ASSET_OR_CAPACITY.value]
            + bucket_counts[SemanticEvidenceBucket.EQUITY_OR_PRODUCTION.value]
            + bucket_counts[SemanticEvidenceBucket.BOILERPLATE_ONLY.value]
        ),
        "top_semantic_flags": top_semantic_flags[:25],
        "top_indeterminate_review_rows": top_indeterminate[:25],
    }


def _materiality_semantic_row(
    row: dict[str, str],
    bucket: SemanticEvidenceBucket,
) -> dict[str, Any]:
    amount = _float_value(row.get("supported_amount_usd"))
    return {
        "packet_id": row.get("packet_id"),
        "entity": row.get("entity"),
        "counterparty": row.get("counterparty"),
        "supported_amount_usd": amount,
        "semantic_bucket": bucket.value,
        "source_uri": row.get("source_uri"),
        "content_hash": row.get("content_hash"),
        "evidence_quote": row.get("evidence_quote", "")[:500],
    }


def load_timing_signal_summary(data_dirs: list[str]) -> dict[str, Any]:
    """Load optional source-backed crack-window timing signal summary."""

    for root in data_dirs:
        summary_path = Path(root) / "reports" / "timing_signal_summary.json"
        if summary_path.exists():
            loaded = json.loads(summary_path.read_text())
            if isinstance(loaded, dict):
                return loaded
    return {}


def load_source_invariant_audit(data_dirs: list[str]) -> dict[str, Any]:
    """Load optional production source/provenance invariant audit."""

    for root in data_dirs:
        summary_path = Path(root) / "reports" / "source_invariant_audit.json"
        if summary_path.exists():
            loaded = json.loads(summary_path.read_text())
            if isinstance(loaded, dict):
                return loaded
    return {}


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    """Lightweight CSV loader for mismatch ratio source data (no pandas dep)."""
    if not path.exists():
        return []
    try:
        with path.open(newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def _load_json_rows(path: Path) -> list[dict[str, Any]]:
    """Load a JSON-list fixture as rows (empty on missing/malformed)."""
    if not path.exists():
        return []
    try:
        loaded = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    return [r for r in loaded if isinstance(r, dict)] if isinstance(loaded, list) else []


def compute_burry_mismatch_ratios(  # noqa: PLR0912, PLR0915
    *,
    debt_service_metrics: Any,
    compute_metrics: Any,
    physical_capacity: Any,
    queue_match_summary: dict[str, Any],
    physical_record_match_summary: dict[str, Any],
    resolved_data_dirs: list[str],
    payback_cases: list[Any] | None = None,
) -> dict[str, Any]:
    """
    Turn raw source-backed numbers into Burry-style mismatch ratios.

    These directly implement the "assumptions baked in, how fragile" test:
    - Cash flow at realistic (low) utilization vs. debt service.
    - Physical: announced capacity that is actually deliverable (queue+permit+equipment backed).
    - GPU: accounting life vs. observed economic/obsolescence life.
    - Debt: missing explicit rate exposure as % of the refinancing wall.

    Each ratio includes supporting counts, conservative assumptions used, and notes
    so it can be evidence-audited and surfaced as a first-class claim.
    """
    ratios: dict[str, Any] = {
        "cash_flow_mismatch": {},
        "physical_mismatch": {},
        "gpu_economics_mismatch": {},
        "debt_refinancing_mismatch": {},
        "scenario_stress_examples": {},
        "notes": "Ratios are computed from source-backed artifacts (EDGAR contracts, tracker projects, queue matches, payback cases, GPU secondary/rental observations) where the required per-deal inputs are disclosed. Where they are not, the ratio is marked blocked or illustrative_only rather than presented as source-backed. Conservative 'realistic' assumptions are applied and labeled where direct per-deal revenue/utilization are not disclosed.",
        "computation_timestamp": None,
    }

    # 1. Debt / refinancing mismatch (missing rate is a direct fragility signal)
    try:
        distinct_debt = getattr(debt_service_metrics, "distinct_debt_like_notional_usd", 0.0) or 0.0
        missing_rate = getattr(debt_service_metrics, "missing_rate_notional_usd", 0.0) or 0.0
        if distinct_debt > 0:
            ratios["debt_refinancing_mismatch"]["missing_rate_pct_of_debt_like_notional"] = round(
                (missing_rate / distinct_debt) * 100, 1
            )
        ratios["debt_refinancing_mismatch"]["measured_annual_interest_usd"] = getattr(
            debt_service_metrics, "measured_annual_interest_usd", 0.0
        )
        ratios["debt_refinancing_mismatch"]["missing_rate_notional_usd"] = missing_rate
        wall_24_30 = (
            getattr(debt_service_metrics, "maturity_wall_notional_usd_2024_2030", 0.0) or 0.0
        )
        if wall_24_30 > 0:
            ratios["debt_refinancing_mismatch"]["maturity_wall_2024_2030_notional_usd"] = wall_24_30
    except Exception:
        pass

    # 2. GPU economics mismatch (life assumption fragility)
    try:
        gpu_risks = getattr(compute_metrics, "top_gpu_depreciation_risks", []) or []
        gaps = []
        for r in gpu_risks:
            g = getattr(r, "useful_life_gap_years", None)
            if g is not None:
                gaps.append(g)
        if gaps:
            ratios["gpu_economics_mismatch"]["median_useful_life_gap_years"] = round(
                sum(gaps) / len(gaps), 1
            )
            ratios["gpu_economics_mismatch"]["generations_with_gap"] = len(gaps)
            ratios["gpu_economics_mismatch"]["red_flag_generations"] = sum(
                1 for r in gpu_risks if getattr(r, "red_flag", False)
            )
        ratios["gpu_economics_mismatch"]["accounting_vs_modeled_life_note"] = (
            "Positive gap = accounting useful life longer than observed secondary market / rental rate compression implies. Classic bubble signal per Burry-style depreciation reality check."
        )
    except Exception:
        pass

    # 2b. Source-backed GPU depreciation gap (book life vs observed rental-yield
    # compression), from the adversarially-verified GPU price/rental evidence.
    try:
        gpu_gap = summarize_gpu_depreciation_gap(
            load_gpu_price_evidence(Path("handoffs/gpu_price_evidence_20260603.json"))
        )
        if gpu_gap.get("status") == "source_backed":
            ratios["gpu_economics_mismatch"]["source_backed_gap"] = gpu_gap
    except Exception:
        pass

    # 3. Cash flow mismatch at realistic utilization
    # Use payback cases (they carry utilization_pct, revenue, power, debt_service)
    realistic_util = (
        0.28  # conservative sustained for many AI infra workloads per industry cross-checks
    )
    cf_examples = []
    base_dscrs = []
    stressed_dscrs = []

    cases = payback_cases or []
    cases_scanned = 0
    missing_input_counts = {"annual_debt_service": 0, "utilization_pct": 0, "revenue": 0}
    for case in cases[:50]:  # bounded for speed
        try:
            cases_scanned += 1
            util = getattr(case, "utilization_pct", None)
            rev = getattr(case, "annual_revenue_run_rate_usd", None) or getattr(
                case, "contracted_revenue_usd", None
            )
            power = getattr(case, "annual_power_cost_usd", None) or 0.0
            debt_svc = getattr(case, "annual_debt_service_usd", None)
            if not rev:
                missing_input_counts["revenue"] += 1
            if not debt_svc:
                missing_input_counts["annual_debt_service"] += 1
            if not (util and util > 0):
                missing_input_counts["utilization_pct"] += 1
            if rev and debt_svc and util and util > 0:
                # scale revenue to realistic util
                scale = realistic_util / util
                realistic_rev = rev * scale
                # very rough gross cash after power (ignore other opex for conservative signal)
                cash = max(0.0, realistic_rev - (power or 0.0))
                dscr_real = cash / debt_svc if debt_svc > 0 else None
                if dscr_real is not None:
                    cf_examples.append(
                        {
                            "entity": getattr(case, "entity", None),
                            "assumed_util_pct": round(util * 100, 1),
                            "realistic_util_pct": round(realistic_util * 100, 1),
                            "dscr_at_realistic_util": round(dscr_real, 2),
                        }
                    )
                    # also capture a 'base' from the case if it had one
                    if (
                        hasattr(case, "debt_service_coverage_ratio")
                        and case.debt_service_coverage_ratio
                    ):
                        base_dscrs.append(case.debt_service_coverage_ratio)
                    stressed_dscrs.append(dscr_real)
        except Exception:
            continue

    if cf_examples:
        ratios["cash_flow_mismatch"]["realistic_utilization_used_pct"] = round(
            realistic_util * 100, 1
        )
        ratios["cash_flow_mismatch"]["example_cases"] = cf_examples[:5]
        if stressed_dscrs:
            ratios["cash_flow_mismatch"]["median_dscr_at_realistic_util"] = round(
                sum(stressed_dscrs) / len(stressed_dscrs), 2
            )
        if base_dscrs:
            ratios["cash_flow_mismatch"]["median_base_dscr_from_cases"] = round(
                sum(base_dscrs) / len(base_dscrs), 2
            )
        ratios["cash_flow_mismatch"]["cases_with_utilization_data"] = len(cf_examples)
        ratios["cash_flow_mismatch"]["source_backed"] = True
        ratios["cash_flow_mismatch"]["note"] = (
            f"Revenue scaled linearly to {int(realistic_util * 100)}% sustained utilization (common conservative assumption for non-hyperscaler or ramping AI loads). "
            "Power cost held constant. Actual DSCR would also reflect opex, taxes, and contract holes."
        )
    else:
        # Skepticism-first: do not emit a coverage ratio when the per-case inputs a
        # real DSCR requires are not source-backed. Surface the gap explicitly with
        # the missing inputs named, so it is an actionable extraction target rather
        # than an absent or assumed number.
        ratios["cash_flow_mismatch"]["status"] = "blocked_missing_source_backed_inputs"
        ratios["cash_flow_mismatch"]["source_backed"] = False
        ratios["cash_flow_mismatch"]["cases_scanned"] = cases_scanned
        ratios["cash_flow_mismatch"]["missing_inputs"] = sorted(
            name for name, count in missing_input_counts.items() if count
        )
        ratios["cash_flow_mismatch"]["note"] = (
            "No source-backed cash-flow mismatch ratio computed: the scanned payback "
            "cases lack the per-case inputs a DSCR requires (see missing_inputs). "
            "Reported as an explicit pending gap, not an assumed ratio."
        )

    # 3b. Source-backed cluster interest coverage from per-issuer primary-filing
    # financials (the DSCR the per-case payback path is blocked on). Reads the
    # adversarially-verified AI-direct issuer financials fixture if present.
    try:
        issuer_rows = _load_csv_rows(Path("handoffs/fixtures/ai_direct_issuer_financials.csv"))

        def _num(row: dict[str, str], key: str) -> float | None:
            value = row.get(key)
            if not value:
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        issuers: list[IssuerFinancials] = [
            IssuerFinancials(
                entity=row.get("entity", ""),
                revenue_usd=_num(row, "revenue_usd"),
                ebitda_usd=_num(row, "ebitda_usd"),
                operating_income_usd=_num(row, "operating_income_usd"),
                net_income_usd=_num(row, "net_income_usd"),
                total_debt_usd=_num(row, "total_debt_usd"),
                annual_interest_expense_usd=_num(row, "annual_interest_expense_usd"),
                annual_debt_service_usd=_num(row, "annual_debt_service_usd"),
                period=str(row.get("period", ""))[:30],
                source_uri=row.get("primary_source_uri", ""),
                source_backed=True,
            )
            for row in issuer_rows
            if (row.get("verification_overall") or "").strip() == "source_backed"
        ]
        if issuers:
            ratios["cluster_interest_coverage"] = compute_cluster_interest_coverage(issuers)
        # Forward-looking cash-flow stress on the same source-backed rows.
        stress = stress_cluster(
            [
                {
                    "entity": row.get("entity", ""),
                    "revenue_usd": _num(row, "revenue_usd"),
                    "ebitda_usd": _num(row, "ebitda_usd"),
                    "annual_interest_expense_usd": _num(row, "annual_interest_expense_usd"),
                    "verification_overall": (row.get("verification_overall") or "").strip(),
                }
                for row in issuer_rows
            ]
        )
        if stress.get("status") == "source_backed":
            ratios["scenario_stress"] = stress
    except Exception:
        pass

    # 4. Physical mismatch: deliverable vs announced.
    # The strong-queue-match % is NOT a deliverability rate. The ISO
    # interconnection queues ARE fully ingested (queue_records.csv carries all
    # PJM / CAISO / ISO-NE / SPP / NYISO / ERCOT / MISO records), but those are
    # GENERATION-side supply queues: only a tiny fraction of records are
    # data-center LOADS, which largely interconnect through a separate process
    # not captured here. So matching tracker data-center projects against
    # generation queues under-counts deliverability by construction. Read
    # deliverability from the tracker's construction-status fields instead.
    try:
        projs: list[dict[str, str]] = []
        matches: list[dict[str, str]] = []
        for root in resolved_data_dirs:
            projs = _load_csv_rows(Path(root) / "physical" / "projects.csv")
            matches = _load_csv_rows(Path(root) / "physical" / "queue_project_matches.csv")
            if projs:
                break

        def _proj_mw(p: dict[str, str]) -> float:
            for key in ("capacity_mw", "it_load_mw", "capacity_mw_high"):
                val = p.get(key)
                if val:
                    try:
                        return float(val)
                    except (TypeError, ValueError):
                        return 0.0
            return 0.0

        total_announced_mw = sum(_proj_mw(p) for p in projs)
        if total_announced_mw > 100:  # only trust if we have a meaningful sample
            status_mw: dict[str, float] = {}
            permit_not_confirmed_mw = 0.0
            for p in projs:
                pmw = _proj_mw(p)
                st = (p.get("construction_status") or "").strip().lower() or "unspecified"
                status_mw[st] = status_mw.get(st, 0.0) + pmw
                if (p.get("permit_status") or "").strip().lower() == "not_confirmed":
                    permit_not_confirmed_mw += pmw
            strong_ids = {
                m.get("matched_project_id")
                for m in matches
                if (m.get("match_status") or "").lower().startswith("strong")
                or float(m.get("match_confidence") or 0) >= 0.8
            }
            strong_matched_mw = sum(_proj_mw(p) for p in projs if p.get("project_id") in strong_ids)

            # The matcher's ACTUAL input: the fully-ingested ISO queue records.
            ingested_records = 0
            ingested_by_source: dict[str, int] = {}
            for root in resolved_data_dirs:
                qr = _load_csv_rows(
                    Path(root) / "source_acquisition" / "source_rows" / "queue_records.csv"
                )
                if qr:
                    ingested_records = len(qr)
                    for r in qr:
                        src = (r.get("source_id") or "").split("-")[0].lower() or "unknown"
                        ingested_by_source[src] = ingested_by_source.get(src, 0) + 1
                    break
            dc_related = int(queue_match_summary.get("data_center_queue_rows") or 0)
            strong_matched_projects = int(queue_match_summary.get("matched_rows") or 0)

            def _pct(mw: float) -> float:
                return round(100 * mw / total_announced_mw, 1)

            pm = ratios["physical_mismatch"]
            pm["total_announced_mw_in_sample"] = round(total_announced_mw, 1)
            # (a) honest deliverability proxy from tracker construction status
            pm["in_service_mw_pct"] = _pct(status_mw.get("in_service", 0.0))
            pm["under_construction_mw_pct"] = _pct(status_mw.get("under_construction", 0.0))
            pm["announced_only_mw_pct"] = _pct(status_mw.get("announced", 0.0))
            pm["cancelled_or_delayed_mw_pct"] = _pct(
                status_mw.get("cancelled", 0.0) + status_mw.get("delayed", 0.0)
            )
            pm["permit_not_confirmed_mw_pct"] = _pct(permit_not_confirmed_mw)
            pm["deliverability_proxy_source"] = (
                "third_party_project_tracker_construction_status_non_primary"
            )
            # (b) the queue-match figure, correctly explained (NOT a deliverability rate)
            pm["strong_queue_matched_mw"] = round(strong_matched_mw, 1)
            pm["strong_queue_match_coverage_pct"] = _pct(strong_matched_mw)
            pm["queue_match_status"] = "weak_lens_generation_queue_not_data_center_load"
            pm["iso_queue_records_ingested"] = ingested_records
            pm["iso_queue_records_by_source"] = ingested_by_source
            pm["data_center_related_queue_records"] = dc_related
            pm["strong_matched_to_tracker_projects"] = strong_matched_projects
            pm["note"] = (
                f"strong_queue_match_coverage_pct ({_pct(strong_matched_mw)}%) is NOT a "
                f"deliverability rate. The ISO interconnection queues ARE fully ingested "
                f"({ingested_records} records {ingested_by_source}), but they are GENERATION-side "
                f"supply queues: only {dc_related} of {ingested_records} records are "
                f"data-center-load related ({strong_matched_projects} strong-matched to tracker "
                "projects). Data-center LOADS largely interconnect through a separate "
                "load-study process not in these generation queues, so queue-matching "
                "under-counts data-center deliverability by construction. Deliverability is "
                "therefore read from the tracker's construction-status (non-primary): most "
                "announced AI/data-center MW is not yet built or permitted (high announced_only + "
                "permit_not_confirmed) -- a directional stranding/timeline signal. A true "
                "firm-vs-queue rate needs utility large-load / load-interconnection data, not "
                "generation queues."
            )
    except Exception:
        pass

    # 5. Simple scenario stress example using the (now data-influenced) engine
    try:
        source_backed_base = ratios.get("cash_flow_mismatch", {}).get("median_base_dscr_from_cases")
        base_for_stress = source_backed_base if source_backed_base else 1.15
        sse = ratios["scenario_stress_examples"]
        sse["base_dscr_used_for_stress"] = round(base_for_stress, 2)
        sse["base_dscr_source_backed"] = bool(source_backed_base)
        # We can't easily instantiate full graph here without the client; provide the
        # parameters so the engine can be called later with this base.
        sse["adverse_stressed_dscr_example"] = round(
            max(0.2, base_for_stress * (1 - 0.25) / 1.15), 2
        )  # approx adverse
        sse["tail_stressed_dscr_example"] = round(max(0.2, base_for_stress * (1 - 0.55) / 2.0), 2)
        if source_backed_base:
            sse["note"] = (
                "Example mismatch ratios from applying conservative utilization + depreciation "
                "stress to a SOURCE-BACKED base DSCR. Full per-entity run requires the graph "
                "client + entity linkage."
            )
        else:
            # The base DSCR is a conservative default, not derived from disclosure. Label it
            # honestly so the stress example is never read as the cluster's real coverage.
            sse["illustrative_only"] = True
            sse["status"] = "illustrative_no_source_backed_base_dscr"
            sse["note"] = (
                "ILLUSTRATIVE ONLY: no source-backed base DSCR was available, so a conservative "
                "default (1.15) demonstrates the stress mechanics. These example ratios are NOT "
                "source-backed and must not be read as the AI-direct cluster's actual coverage."
            )
    except Exception:
        pass

    return ratios


def build_burry_report(data_dirs: list[str] | None = None) -> dict[str, Any]:  # noqa: PLR0912, PLR0915
    resolved_data_dirs = data_dirs or ["data"]
    coverage = build_source_coverage_report(resolved_data_dirs)
    physical_capacity = build_physical_capacity_summary(resolved_data_dirs)
    physical_execution = build_physical_execution_summary(resolved_data_dirs)
    physical_risk = build_physical_risk_summary(resolved_data_dirs)
    queue_match_summary = load_queue_project_match_summary(resolved_data_dirs)
    physical_record_match_summary = load_physical_record_match_summary(resolved_data_dirs)
    entity_universe_summary = load_entity_universe_summary(resolved_data_dirs)
    capital_exposure_graph_summary = load_capital_exposure_graph_summary(resolved_data_dirs)
    graph_centrality = load_graph_centrality(resolved_data_dirs)
    neo4j_analytics = load_neo4j_analytics(resolved_data_dirs)
    ownership_graph_summary = load_ownership_graph_summary(resolved_data_dirs)
    weak_link_summary = load_weak_link_summary(resolved_data_dirs)
    contract_contagion_summary = load_contract_contagion_summary(resolved_data_dirs)
    review_queue_summary = load_review_queue_summary(resolved_data_dirs)
    materiality_adjudication_summary = load_materiality_adjudication_summary(
        resolved_data_dirs,
    )
    materiality_adjudication_decision_summary = load_materiality_adjudication_decision_summary(
        resolved_data_dirs
    )
    materiality_adjudication_decisions = load_materiality_adjudication_decisions(
        resolved_data_dirs,
    )
    materiality_semantics = materiality_semantic_summary(materiality_adjudication_decisions)
    materiality_relevance = summarize_relevance_linkage(materiality_adjudication_decisions)
    timing_signal_summary = load_timing_signal_summary(resolved_data_dirs)
    source_invariant_audit = load_source_invariant_audit(resolved_data_dirs)
    raw_capital_batch = load_report_capital_evidence(resolved_data_dirs)
    scoped_capital_deals, capital_scope_summary = scope_deals(raw_capital_batch.deals)
    capital_batch = CapitalEvidenceBatch(deals=scoped_capital_deals)
    capital_metrics = analyze_capital_evidence(capital_batch)
    compute_batch = load_report_compute_economics(resolved_data_dirs)
    compute_metrics = analyze_compute_economics(compute_batch)
    debt_service_metrics = analyze_debt_service(
        raw_capital_batch.deals,
        compute_batch.payback_cases,
    )
    mismatch_ratios = compute_burry_mismatch_ratios(
        debt_service_metrics=debt_service_metrics,
        compute_metrics=compute_metrics,
        physical_capacity=physical_capacity,
        queue_match_summary=queue_match_summary,
        physical_record_match_summary=physical_record_match_summary,
        resolved_data_dirs=resolved_data_dirs,
        payback_cases=getattr(compute_batch, "payback_cases", None),
    )
    if graph_centrality.get("status") == "source_backed":
        mismatch_ratios["graph_systemic_centrality"] = graph_centrality
    if (neo4j_analytics.get("load") or {}).get("status") == "loaded":
        mismatch_ratios["neo4j_production_graph"] = neo4j_analytics
    satellite_aggregate = aggregate_satellite_observations(
        load_satellite_observations(Path("data/physical/satellite_observations.json"))
    )
    if satellite_aggregate.get("status") == "source_backed":
        mismatch_ratios["satellite_construction"] = satellite_aggregate
    # Tiered Burry verdict synthesized from the verified evidence: source-backed
    # cluster cash-flow fragility + the adversarially stress-tested thesis
    # premises. Scoped to the AI-direct core; the ecosystem binary stays gated.
    thesis_findings: list[dict[str, Any]] = []
    findings_path = Path("handoffs/ai_direct_thesis_stress_findings_20260602.json")
    if findings_path.exists():
        try:
            loaded = json.loads(findings_path.read_text())
            if isinstance(loaded, list):
                thesis_findings = [f for f in loaded if isinstance(f, dict)]
        except (json.JSONDecodeError, OSError):
            thesis_findings = []
    debt_census_aggregate = aggregate_debt_census(
        load_debt_census(Path("handoffs/ai_direct_debt_census_20260603.json"))
    )
    contagion_edges = load_contagion_edges(Path("handoffs/ai_direct_contagion_edges_20260603.json"))
    contagion_hubs = compute_contagion_hubs(contagion_edges)
    if contagion_hubs.get("status") == "source_backed":
        contagion_hubs["top_loss_cascades"] = top_contagion_cascades(
            contagion_edges, debt_census_aggregate
        ).get("cascades")
    circular_financing_aggregate = analyze_circular_financing(
        load_circular_financing_edges(Path("handoffs/ai_circular_financing_edges_20260603.json"))
    )
    if circular_financing_aggregate.get("status") == "source_backed":
        mismatch_ratios["circular_financing"] = circular_financing_aggregate
    demand_side_aggregate = aggregate_demand_side(
        load_demand_side(Path("handoffs/ai_demand_side_funding_20260603.json"))
    )
    if demand_side_aggregate.get("status") == "source_backed":
        mismatch_ratios["demand_side_funding"] = demand_side_aggregate
    power_exposure_aggregate = aggregate_power_exposure(
        load_power_exposure(Path("handoffs/ai_power_ratepayer_exposure_20260603.json"))
    )
    if power_exposure_aggregate.get("status") == "source_backed":
        mismatch_ratios["power_ratepayer_exposure"] = power_exposure_aggregate
    end_holders_aggregate = aggregate_end_holders(
        load_end_holders(Path("handoffs/ai_direct_end_holders_20260603.json"))
    )
    if end_holders_aggregate.get("status") == "source_backed":
        mismatch_ratios["ultimate_end_holders"] = end_holders_aggregate
    equipment_bottlenecks_aggregate = aggregate_equipment_bottlenecks(
        load_equipment_bottlenecks(Path("handoffs/ai_equipment_bottlenecks_20260603.json"))
    )
    if equipment_bottlenecks_aggregate.get("status") == "source_backed":
        mismatch_ratios["equipment_bottlenecks"] = equipment_bottlenecks_aggregate
    private_credit_funding_aggregate = aggregate_private_credit_funding(
        load_private_credit_funding(Path("handoffs/ai_private_credit_funding_20260603.json"))
    )
    if private_credit_funding_aggregate.get("status") == "source_backed":
        mismatch_ratios["private_credit_funding"] = private_credit_funding_aggregate
    red_flag_scorecard_aggregate = aggregate_red_flag_scorecard(
        load_red_flag_scorecard(Path("handoffs/ai_cluster_red_flags_20260603.json"))
    )
    if red_flag_scorecard_aggregate.get("status") == "source_backed":
        mismatch_ratios["red_flag_scorecard"] = red_flag_scorecard_aggregate
    entity_risk_ranking = build_entity_risk_ranking(
        red_flag_scorecard_aggregate,
        _load_csv_rows(Path("handoffs/fixtures/ai_direct_issuer_financials.csv")),
    )
    if entity_risk_ranking.get("status") == "source_backed":
        mismatch_ratios["entity_risk_ranking"] = entity_risk_ranking
    contract_structure_aggregate = aggregate_contract_structure(
        load_contract_structure(Path("handoffs/ai_cluster_contract_structure_20260603.json"))
    )
    if contract_structure_aggregate.get("status") == "source_backed":
        mismatch_ratios["contract_structure"] = contract_structure_aggregate
    cluster_boundary_aggregate = aggregate_cluster_boundary(
        load_cluster_boundary(Path("handoffs/ai_cluster_breadth_candidates_20260603.json"))
    )
    if cluster_boundary_aggregate.get("status") == "source_backed":
        mismatch_ratios["cluster_boundary"] = cluster_boundary_aggregate
    cluster_discovery = discover_structure(
        _load_csv_rows(Path("handoffs/fixtures/ai_direct_issuer_financials.csv"))
    )
    if cluster_discovery.get("status") == "source_backed":
        mismatch_ratios["cluster_discovery"] = cluster_discovery
    entity_universe_map = aggregate_entity_universe(
        load_entity_universe_map(Path("handoffs/ai_entity_universe_classified_20260603.json"))
    )
    if entity_universe_map.get("status") == "source_backed":
        mismatch_ratios["entity_universe_map"] = entity_universe_map
    universe_extrapolation = estimate_universe(
        _load_json_rows(Path("handoffs/ai_entity_universe_20260603.json")),
        observed_distress_count=(entity_universe_map.get("by_bucket") or {}).get(
            "financed_ai_infra_leveraged"
        ),
    )
    if universe_extrapolation.get("status") == "inferred_capped":
        mismatch_ratios["universe_extrapolation"] = universe_extrapolation
    gpu_earnings_quality = aggregate_gpu_earnings_quality(
        load_gpu_earnings_quality(Path("handoffs/ai_gpu_earnings_quality_20260603.json"))
    )
    if gpu_earnings_quality.get("status") == "source_backed":
        mismatch_ratios["gpu_earnings_quality"] = gpu_earnings_quality
    cluster_extension = aggregate_cluster_extension(
        load_cluster_extension(Path("handoffs/ai_new_cluster_members_20260603.json"))
    )
    if cluster_extension.get("status") == "source_backed":
        mismatch_ratios["cluster_extension"] = cluster_extension
    # Max disclosed single-customer concentration (CoreWeave ~67% Microsoft, filing-verified)
    # feeds the existential-concentration first-principles test in the fragility scorecard.
    mismatch_ratios["_max_single_customer_pct"] = 67
    fragility_scorecard = score_fragility(mismatch_ratios, debt_census=debt_census_aggregate)
    if fragility_scorecard.get("status") == "source_backed":
        mismatch_ratios["fragility_scorecard"] = fragility_scorecard
    refi_wall_aggregate = aggregate_refi_wall(
        load_debt_census_raw(Path("handoffs/ai_direct_debt_census_20260603.json"))
    )
    if refi_wall_aggregate.get("status") == "source_backed":
        mismatch_ratios["refi_wall"] = refi_wall_aggregate
    leading_indicator_monitor = build_leading_indicator_monitor(mismatch_ratios)
    if leading_indicator_monitor.get("status") == "source_backed":
        mismatch_ratios["leading_indicator_monitor"] = leading_indicator_monitor
    utilization_debt_service_aggregate = aggregate_utilization_debt_service(
        load_utilization_debt_service(Path("handoffs/ai_utilization_debt_service_20260603.json"))
    )
    if utilization_debt_service_aggregate.get("status") == "source_backed":
        mismatch_ratios["utilization_debt_service"] = utilization_debt_service_aggregate
    risk_register = build_risk_register(
        mismatch_ratios, debt_census=debt_census_aggregate, contagion_hubs=contagion_hubs
    )
    if risk_register.get("status") == "source_backed":
        mismatch_ratios["risk_register"] = risk_register
    ai_direct_core_verdict = synthesize_core_verdict(
        cluster_dscr=mismatch_ratios.get("cluster_interest_coverage", {}),
        thesis_findings=thesis_findings,
        established_ai_usd=float(materiality_relevance.get("established_usd") or 0.0),
        direct_ai_usd=float(materiality_relevance.get("direct_usd") or 0.0),
        not_established_pct=float(materiality_relevance.get("not_established_pct") or 0.0),
        metric_total_usd=float(materiality_relevance.get("total_usd") or 0.0),
        timing_summary=timing_signal_summary,
        debt_census=debt_census_aggregate,
        demand_side=demand_side_aggregate,
        gpu_gap_source_backed=(
            mismatch_ratios.get("gpu_economics_mismatch", {})
            .get("source_backed_gap", {})
            .get("status")
            == "source_backed"
        ),
        contagion_hubs=contagion_hubs,
        power_exposure=power_exposure_aggregate,
        scenario_stress=mismatch_ratios.get("scenario_stress", {}),
        end_holders=end_holders_aggregate,
        equipment_bottlenecks=equipment_bottlenecks_aggregate,
        private_credit_funding=private_credit_funding_aggregate,
        red_flag_scorecard=red_flag_scorecard_aggregate,
        risk_register=risk_register,
        utilization_debt_service=utilization_debt_service_aggregate,
        entity_risk_ranking=entity_risk_ranking,
        contract_structure=contract_structure_aggregate,
        cluster_boundary=cluster_boundary_aggregate,
        refi_wall=refi_wall_aggregate,
        circular_financing=circular_financing_aggregate,
    )
    coverage_dict = coverage.to_dict()
    physical_capacity_dict = physical_capacity.to_dict()
    physical_risk_dict = physical_risk.to_dict()
    capital_metrics_dict = capital_metrics.to_dict()
    downside_bearer_quality = summarize_risk_bearer_quality(
        [exposure.to_dict() for exposure in capital_metrics.downside_bearers]
    )
    capital_scope_summary_dict = capital_scope_summary.to_dict()
    compute_metrics_dict = compute_metrics.to_dict()
    debt_service_metrics_dict = debt_service_metrics.to_dict()
    entity_universe_distinct_entities = int(
        entity_universe_summary.get("distinct_entities", 0) or 0
    )
    entity_universe_mentions_extracted = int(
        entity_universe_summary.get("mentions_extracted", 0) or 0
    )
    entity_universe_cik_matches = int(entity_universe_summary.get("cik_matches", 0) or 0)
    entity_universe_high_confidence_cik_matches = int(
        entity_universe_summary.get("high_confidence_cik_matches", 0) or 0
    )
    entity_universe_expanded_ciks = int(entity_universe_summary.get("expanded_ciks", 0) or 0)
    source_backed_normalized_entities = entity_universe_distinct_entities or coverage.entities
    metrics = {
        "covered_entities": coverage.entities,
        "source_backed_normalized_entities": source_backed_normalized_entities,
        "entity_universe_distinct_entities": entity_universe_distinct_entities,
        "entity_universe_mentions_extracted": entity_universe_mentions_extracted,
        "entity_universe_cik_matches": entity_universe_cik_matches,
        "entity_universe_high_confidence_cik_matches": (
            entity_universe_high_confidence_cik_matches
        ),
        "entity_universe_expanded_ciks": entity_universe_expanded_ciks,
        "capital_exposure_graph_nodes": capital_exposure_graph_summary.get("nodes", 0),
        "capital_exposure_graph_edges": capital_exposure_graph_summary.get("edges", 0),
        "capital_exposure_graph_source_backed_edges": capital_exposure_graph_summary.get(
            "source_backed_edges", 0
        ),
        "capital_exposure_graph_debt_like_edges": capital_exposure_graph_summary.get(
            "debt_like_edges", 0
        ),
        "capital_exposure_graph_ai_infra_relevant_edges": capital_exposure_graph_summary.get(
            "ai_infra_relevant_edges", 0
        ),
        "capital_exposure_graph_direct_ai_keyword_edges": capital_exposure_graph_summary.get(
            "direct_ai_keyword_edges", 0
        ),
        "capital_exposure_graph_ai_infra_relevant_notional_usd": (
            capital_exposure_graph_summary.get("ai_infra_relevant_notional_usd", 0)
        ),
        "capital_exposure_graph_total_edge_notional_usd": capital_exposure_graph_summary.get(
            "total_edge_notional_usd", 0
        ),
        "capital_exposure_graph_connected_components": capital_exposure_graph_summary.get(
            "connected_components", 0
        ),
        "capital_exposure_graph_largest_component_nodes": capital_exposure_graph_summary.get(
            "largest_component_nodes", 0
        ),
        "capital_exposure_graph_largest_component_notional_usd": (
            capital_exposure_graph_summary.get("largest_component_notional_usd", 0)
        ),
        "capital_exposure_graph_largest_component_ai_infra_relevant_notional_usd": (
            capital_exposure_graph_summary.get(
                "largest_component_ai_infra_relevant_notional_usd",
                0,
            )
        ),
        "capital_exposure_graph_ai_infra_component_count": (
            capital_exposure_graph_summary.get("ai_infra_component_count", 0)
        ),
        "capital_exposure_graph_top_ai_infra_component_notional_usd": (
            capital_exposure_graph_summary.get("top_ai_infra_component_notional_usd", 0)
        ),
        "ownership_graph_nodes": ownership_graph_summary.get("nodes", 0),
        "ownership_graph_relationships": ownership_graph_summary.get("relationships", 0),
        "ownership_graph_source_backed_relationships": ownership_graph_summary.get(
            "source_backed_relationships", 0
        ),
        "ownership_graph_active_relationships": ownership_graph_summary.get(
            "active_relationships", 0
        ),
        "ownership_graph_direct_consolidation_edges": ownership_graph_summary.get(
            "direct_consolidation_edges", 0
        ),
        "ownership_graph_ultimate_consolidation_edges": ownership_graph_summary.get(
            "ultimate_consolidation_edges", 0
        ),
        "weak_link_candidates": weak_link_summary.get("candidates", 0),
        "weak_link_high_or_critical_candidates": weak_link_summary.get(
            "high_or_critical_candidates", 0
        ),
        "weak_link_combined_candidates": weak_link_summary.get("combined_candidates", 0),
        "weak_link_debt_service_candidates": weak_link_summary.get(
            "debt_service_candidates",
            0,
        ),
        "weak_link_source_backed_candidates": weak_link_summary.get("source_backed_candidates", 0),
        "contract_contagion_paths": contract_contagion_summary.get("paths", 0),
        "contract_contagion_source_backed_paths": contract_contagion_summary.get(
            "source_backed_paths",
            0,
        ),
        "contract_contagion_ownership_expanded_paths": contract_contagion_summary.get(
            "ownership_expanded_paths",
            0,
        ),
        "contract_contagion_high_or_critical_paths": contract_contagion_summary.get(
            "high_or_critical_paths",
            0,
        ),
        "contract_contagion_ai_infra_relevant_paths": contract_contagion_summary.get(
            "ai_infra_relevant_paths",
            0,
        ),
        "contract_contagion_total_notional_usd": contract_contagion_summary.get(
            "total_notional_usd",
            0,
        ),
        "contract_contagion_notional_basis": ("path_summed_multiplicity_inflated_not_exposure"),
        "contract_contagion_ai_infra_relevant_notional_usd": contract_contagion_summary.get(
            "ai_infra_relevant_notional_usd",
            0,
        ),
        "contract_contagion_ai_infra_notional_basis": (
            "path_summed_multiplicity_inflated_not_exposure"
        ),
        "review_queue_items": review_queue_summary.get("items", 0),
        "review_queue_critical_items": review_queue_summary.get("critical_items", 0),
        "review_queue_high_items": review_queue_summary.get("high_items", 0),
        "review_queue_pending_items": review_queue_summary.get("pending_items", 0),
        "review_queue_source_backed_items": review_queue_summary.get("source_backed_items", 0),
        "review_queue_pending_notional_amount_usd": review_queue_summary.get(
            "pending_notional_amount_usd",
            0,
        ),
        "review_queue_pending_capital_notional_amount_usd": review_queue_summary.get(
            "pending_capital_notional_amount_usd",
            0,
        ),
        "review_queue_pending_capital_distinct_group_count": review_queue_summary.get(
            "pending_capital_distinct_group_count",
            0,
        ),
        "review_queue_pending_capital_distinct_notional_amount_usd": review_queue_summary.get(
            "pending_capital_distinct_notional_amount_usd",
            0,
        ),
        "review_queue_pending_capital_duplicate_notional_amount_usd": review_queue_summary.get(
            "pending_capital_duplicate_notional_amount_usd",
            0,
        ),
        "review_queue_pending_ai_infra_relevant_capital_notional_amount_usd": (
            review_queue_summary.get(
                "pending_ai_infra_relevant_capital_notional_amount_usd",
                0,
            )
        ),
        "review_queue_pending_ai_infra_relevant_capital_distinct_notional_amount_usd": (
            review_queue_summary.get(
                "pending_ai_infra_relevant_capital_distinct_notional_amount_usd",
                0,
            )
        ),
        "review_queue_pending_compute_claim_amount_usd": review_queue_summary.get(
            "pending_compute_claim_amount_usd",
            0,
        ),
        "review_queue_pending_contagion_path_items": review_queue_summary.get(
            "pending_contagion_path_items",
            0,
        ),
        "review_queue_pending_contagion_path_exposure_usd": review_queue_summary.get(
            "pending_contagion_path_exposure_usd",
            0,
        ),
        "review_queue_pending_exposure_usd": review_queue_summary.get(
            "pending_exposure_usd",
            0,
        ),
        "review_queue_pending_capacity_mw": review_queue_summary.get(
            "pending_capacity_mw",
            0,
        ),
        "materiality_adjudication_packets": materiality_adjudication_summary.get(
            "packets",
            0,
        ),
        "materiality_adjudication_source_backed_packets": (
            materiality_adjudication_summary.get("source_backed_packets", 0)
        ),
        "materiality_adjudication_packets_with_local_evidence_snippets": (
            materiality_adjudication_summary.get(
                "packets_with_local_evidence_snippets",
                0,
            )
        ),
        "materiality_adjudication_ai_infra_relevant_packets": (
            materiality_adjudication_summary.get("ai_infra_relevant_packets", 0)
        ),
        "materiality_adjudication_total_exposure_basis_usd": (
            materiality_adjudication_summary.get("total_exposure_basis_usd", 0)
        ),
        "materiality_adjudication_decisions": materiality_adjudication_decision_summary.get(
            "decisions",
            0,
        ),
        "materiality_adjudication_supported_as_material_blocker": (
            materiality_adjudication_decision_summary.get(
                "supported_as_material_blocker",
                0,
            )
        ),
        "materiality_adjudication_needs_deeper_extraction": (
            materiality_adjudication_decision_summary.get("needs_deeper_extraction", 0)
        ),
        "materiality_adjudication_source_quote_backed_decisions": (
            materiality_adjudication_decision_summary.get("source_quote_backed_decisions", 0)
        ),
        "materiality_adjudication_row_context_backed_decisions": (
            materiality_adjudication_decision_summary.get("row_context_backed_decisions", 0)
        ),
        "materiality_adjudication_unresolved_decisions": (
            materiality_adjudication_decision_summary.get("needs_deeper_extraction", 0)
            + materiality_adjudication_decision_summary.get("needs_source_retrieval", 0)
        ),
        "materiality_adjudication_decision_coverage_pct": round(
            (
                (
                    materiality_adjudication_decision_summary.get("decisions", 0)
                    / materiality_adjudication_summary.get("packets", 1)
                )
                * 100
            )
            if materiality_adjudication_summary.get("packets", 0)
            else 0.0,
            2,
        ),
        "materiality_adjudication_unresolved_decision_pct": round(
            (
                (
                    (
                        materiality_adjudication_decision_summary.get(
                            "needs_deeper_extraction",
                            0,
                        )
                        + materiality_adjudication_decision_summary.get(
                            "needs_source_retrieval",
                            0,
                        )
                    )
                    / materiality_adjudication_decision_summary.get("decisions", 1)
                )
                * 100
            )
            if materiality_adjudication_decision_summary.get("decisions", 0)
            else 0.0,
            2,
        ),
        "materiality_adjudication_approved_for_metric_use": (
            materiality_adjudication_decision_summary.get("approved_for_metric_use", 0)
        ),
        "materiality_adjudication_approved_row_supported_amount_usd": (
            materiality_adjudication_decision_summary.get(
                "approved_row_supported_amount_usd",
                materiality_adjudication_decision_summary.get(
                    "final_metric_supported_amount_usd",
                    0,
                ),
            )
        ),
        "materiality_adjudication_final_metric_supported_amount_usd": (
            materiality_adjudication_decision_summary.get(
                "final_metric_supported_amount_usd",
                0,
            )
        ),
        "materiality_adjudication_final_metric_group_count": (
            materiality_adjudication_decision_summary.get("final_metric_group_count", 0)
        ),
        "materiality_relevance_direct_ai_linked_usd": materiality_relevance.get(
            "direct_usd",
            0,
        ),
        "materiality_relevance_watchlist_ai_linked_usd": materiality_relevance.get(
            "watchlist_usd",
            0,
        ),
        "materiality_relevance_established_ai_linked_usd": materiality_relevance.get(
            "established_usd",
            0,
        ),
        "materiality_relevance_not_established_linkage_usd": materiality_relevance.get(
            "not_established_usd",
            0,
        ),
        "materiality_relevance_direct_ai_linked_pct": materiality_relevance.get(
            "direct_pct",
            0,
        ),
        "materiality_relevance_established_ai_linked_pct": materiality_relevance.get(
            "established_pct",
            0,
        ),
        "materiality_relevance_not_established_linkage_pct": materiality_relevance.get(
            "not_established_pct",
            0,
        ),
        "timing_signal_count": timing_signal_summary.get("signals", 0),
        "timing_signal_source_backed_count": timing_signal_summary.get(
            "source_backed_signals",
            0,
        ),
        "timing_signal_critical_or_high_count": timing_signal_summary.get(
            "critical_or_high_signals",
            0,
        ),
        "timing_signal_ai_infra_relevant_count": timing_signal_summary.get(
            "ai_infra_relevant_signals",
            0,
        ),
        "timing_signal_peak_stress_quarter": timing_signal_summary.get("peak_stress_quarter"),
        "timing_signal_candidate_stress_window_start": timing_signal_summary.get(
            "candidate_stress_window_start"
        ),
        "timing_signal_candidate_stress_window_end": timing_signal_summary.get(
            "candidate_stress_window_end"
        ),
        "timing_signal_capital_refinancing_usd_2024_2030": (
            timing_signal_summary.get("capital_refinancing_usd_2024_2030", 0)
        ),
        "timing_signal_ai_infra_capital_refinancing_usd_2024_2030": (
            timing_signal_summary.get("ai_infra_capital_refinancing_usd_2024_2030", 0)
        ),
        "timing_signal_capital_refinancing_forward_from_as_of_usd": (
            timing_signal_summary.get("capital_refinancing_forward_from_as_of_usd", 0)
        ),
        "timing_signal_ai_infra_capital_refinancing_forward_from_as_of_usd": (
            timing_signal_summary.get(
                "ai_infra_capital_refinancing_forward_from_as_of_usd",
                0,
            )
        ),
        "timing_signal_forward_refinancing_as_of_quarter": (
            timing_signal_summary.get("forward_refinancing_as_of_quarter")
        ),
        "timing_signal_forward_peak_refinancing_quarter": (
            timing_signal_summary.get("forward_peak_refinancing_quarter")
        ),
        "timing_signal_forward_peak_ai_infra_refinancing_quarter": (
            timing_signal_summary.get("forward_peak_ai_infra_refinancing_quarter")
        ),
        "timing_signal_physical_capacity_mw_2024_2030": timing_signal_summary.get(
            "physical_capacity_mw_2024_2030",
            0,
        ),
        "timing_signal_compute_amount_usd_2024_2030": timing_signal_summary.get(
            "compute_amount_usd_2024_2030",
            0,
        ),
        "timing_signal_chip_supply_capacity_mw_2024_2030": timing_signal_summary.get(
            "chip_supply_capacity_mw_2024_2030",
            0,
        ),
        "covered_filings": coverage.filings,
        "raw_source_documents": coverage.source_documents,
        "covered_projects": coverage.projects,
        "queue_records": coverage.queue_records,
        "equipment_records": coverage.equipment_records,
        "permit_records": coverage.permit_records,
        "lei_records": coverage.lei_records,
        "ownership_records": coverage.ownership_records,
        "tracker_records": coverage.tracker_records,
        "ppas": coverage.ppas,
        "lease_agreements": coverage.lease_agreements,
        "extracted_deals": coverage.extracted_deals,
        "source_backed_deals": coverage.source_backed_deals,
        "coverage_compute_economics_rows": coverage.compute_economics_rows,
        "source_backed_compute_rows": coverage.source_backed_compute_rows,
        "coverage_compute_assets": coverage.compute_assets,
        "coverage_gpu_price_observations": coverage.gpu_price_observations,
        "coverage_depreciation_policies": coverage.depreciation_policies,
        "coverage_tam_claims": coverage.tam_claims,
        "coverage_capex_payback_cases": coverage.capex_payback_cases,
        "coverage_eps_depreciation_impacts": coverage.eps_depreciation_impacts,
        "coverage_chip_supply_observations": coverage.chip_supply_observations,
        "debt_service_deals_scanned": debt_service_metrics.deal_count_scanned,
        "capital_deals_in_scope": capital_scope_summary.in_scope_deal_count,
        "capital_deals_out_of_scope": capital_scope_summary.out_of_scope_deal_count,
        "capital_debt_like_deals_in_scope": (capital_scope_summary.in_scope_debt_like_deal_count),
        "capital_debt_like_deals_out_of_scope": (
            capital_scope_summary.out_of_scope_debt_like_deal_count
        ),
        "capital_debt_like_notional_in_scope_usd": (
            capital_scope_summary.in_scope_debt_like_notional_usd
        ),
        "capital_debt_like_notional_out_of_scope_usd": (
            capital_scope_summary.out_of_scope_debt_like_notional_usd
        ),
        "capital_balance_sheet_context_deals": (
            capital_scope_summary.balance_sheet_context_deal_count
        ),
        "capital_balance_sheet_context_debt_like_deals": (
            capital_scope_summary.balance_sheet_context_debt_like_deal_count
        ),
        "capital_balance_sheet_context_debt_like_notional_usd": (
            capital_scope_summary.balance_sheet_context_debt_like_notional_usd
        ),
        "debt_service_scoped_deals": debt_service_metrics.scoped_deal_count,
        "debt_service_out_of_scope_deals": debt_service_metrics.out_of_scope_deal_count,
        "debt_service_debt_like_deals": debt_service_metrics.debt_like_deal_count,
        "debt_service_out_of_scope_debt_like_deals": (
            debt_service_metrics.out_of_scope_debt_like_deal_count
        ),
        "debt_service_debt_like_notional_usd": debt_service_metrics.debt_like_notional_usd,
        "debt_service_distinct_debt_like_notional_usd": (
            debt_service_metrics.distinct_debt_like_notional_usd
        ),
        "debt_service_out_of_scope_debt_like_notional_usd": (
            debt_service_metrics.out_of_scope_debt_like_notional_usd
        ),
        "debt_service_obligations": debt_service_metrics.obligations_count,
        "debt_service_distinct_obligations": debt_service_metrics.distinct_obligations_count,
        "debt_service_duplicate_candidate_obligations": (
            debt_service_metrics.duplicate_candidate_obligation_count
        ),
        "debt_service_duplicate_candidate_notional_usd": (
            debt_service_metrics.duplicate_candidate_notional_usd
        ),
        "debt_service_explicit_rate_obligations": (
            debt_service_metrics.explicit_rate_obligation_count
        ),
        "debt_service_measured_rate_obligations": (
            debt_service_metrics.measured_rate_obligation_count
        ),
        "debt_service_missing_rate_obligations": (
            debt_service_metrics.missing_rate_obligation_count
        ),
        "debt_service_rate_outlier_obligations": (
            debt_service_metrics.rate_outlier_obligation_count
        ),
        "debt_service_explicit_rate_notional_usd": (
            debt_service_metrics.explicit_rate_notional_usd
        ),
        "debt_service_measured_rate_notional_usd": (
            debt_service_metrics.measured_rate_notional_usd
        ),
        "debt_service_missing_rate_notional_usd": (debt_service_metrics.missing_rate_notional_usd),
        "debt_service_rate_outlier_notional_usd": (debt_service_metrics.rate_outlier_notional_usd),
        "debt_service_measured_annual_interest_usd": (
            debt_service_metrics.measured_annual_interest_usd
        ),
        "debt_service_measured_rate_notional_coverage_pct": (
            debt_service_metrics.measured_rate_notional_coverage_pct
        ),
        "debt_service_distinct_measured_rate_notional_usd": (
            debt_service_metrics.distinct_measured_rate_notional_usd
        ),
        "debt_service_distinct_missing_rate_notional_usd": (
            debt_service_metrics.distinct_missing_rate_notional_usd
        ),
        "debt_service_distinct_measured_annual_interest_usd": (
            debt_service_metrics.distinct_measured_annual_interest_usd
        ),
        "debt_service_distinct_measured_rate_notional_coverage_pct": (
            debt_service_metrics.distinct_measured_rate_notional_coverage_pct
        ),
        "debt_service_obligations_missing_maturity": (
            debt_service_metrics.obligations_missing_maturity_count
        ),
        "debt_service_notional_missing_maturity_usd": (
            debt_service_metrics.notional_missing_maturity_usd
        ),
        "debt_service_distinct_obligations_missing_maturity": (
            debt_service_metrics.distinct_obligations_missing_maturity_count
        ),
        "debt_service_distinct_notional_missing_maturity_usd": (
            debt_service_metrics.distinct_notional_missing_maturity_usd
        ),
        "debt_service_maturity_wall_notional_usd_2024_2030": (
            debt_service_metrics.maturity_wall_notional_usd_2024_2030
        ),
        "debt_service_maturity_wall_measured_annual_interest_usd_2024_2030": (
            debt_service_metrics.maturity_wall_measured_annual_interest_usd_2024_2030
        ),
        "debt_service_maturity_wall_missing_rate_notional_usd_2024_2030": (
            debt_service_metrics.maturity_wall_missing_rate_notional_usd_2024_2030
        ),
        "debt_service_distinct_maturity_wall_notional_usd_2024_2030": (
            debt_service_metrics.distinct_maturity_wall_notional_usd_2024_2030
        ),
        "debt_service_distinct_maturity_wall_measured_annual_interest_usd_2024_2030": (
            debt_service_metrics.distinct_maturity_wall_measured_annual_interest_usd_2024_2030
        ),
        "debt_service_distinct_maturity_wall_missing_rate_notional_usd_2024_2030": (
            debt_service_metrics.distinct_maturity_wall_missing_rate_notional_usd_2024_2030
        ),
        "debt_service_payback_cases_with_debt_service": (
            debt_service_metrics.payback_cases_with_debt_service
        ),
        "debt_service_payback_cases_missing_debt_service": (
            debt_service_metrics.payback_cases_missing_debt_service
        ),
        "debt_service_cash_flow_mismatch_red_flags": (
            debt_service_metrics.cash_flow_mismatch_red_flag_count
        ),
        "catalog_sources": coverage.catalog_sources,
        "catalog_sources_by_corpus": coverage.catalog_sources_by_corpus,
        "acquisition_artifacts_attempted": coverage.acquisition_artifacts_attempted,
        "acquisition_artifacts_acquired": coverage.acquisition_artifacts_acquired,
        "acquisition_errors": coverage.acquisition_errors,
        "source_invariant_audit_passed": source_invariant_audit.get("passed", False),
        "source_invariant_files_scanned": source_invariant_audit.get("files_scanned", 0),
        "source_invariant_rows_scanned": source_invariant_audit.get("rows_scanned", 0),
        "source_invariant_uri_values_checked": source_invariant_audit.get(
            "source_uri_values_checked", 0
        ),
        "source_invariant_violation_count": source_invariant_audit.get("violation_count", 0),
        "source_invariant_warning_count": source_invariant_audit.get("warning_count", 0),
        "queue_capacity_mw": physical_capacity.queue_capacity_mw,
        "queue_capacity_records": physical_capacity.queue_capacity_records,
        "data_center_queue_records": physical_capacity.data_center_queue_records,
        "data_center_queue_capacity_mw": physical_capacity.data_center_queue_capacity_mw,
        "data_center_queue_capacity_by_region_mw": (
            physical_capacity.data_center_queue_capacity_by_region_mw
        ),
        "data_center_queue_capacity_by_relationship_mw": (
            physical_capacity.data_center_queue_capacity_by_relationship_mw
        ),
        "top_data_center_queue_projects": physical_capacity.top_data_center_queue_projects[:10],
        "queue_project_matched_rows": queue_match_summary.get("matched_rows", 0),
        "queue_project_strong_matches": queue_match_summary.get("strong_matches", 0),
        "queue_project_candidate_matches": queue_match_summary.get("candidate_matches", 0),
        "queue_project_loader_queue_rows": queue_match_summary.get("loader_queue_rows", 0),
        "queue_project_loader_queue_capacity_mw": queue_match_summary.get(
            "loader_queue_capacity_mw", 0
        ),
        "physical_record_permit_loader_rows": physical_record_match_summary.get(
            "permit_loader_rows", 0
        ),
        "physical_record_equipment_loader_rows": physical_record_match_summary.get(
            "equipment_loader_rows", 0
        ),
        "physical_record_equipment_loader_capacity_mw": physical_record_match_summary.get(
            "equipment_loader_capacity_mw", 0
        ),
        "tracker_project_records_scanned": physical_capacity.tracker_project_records_scanned,
        "tracker_capacity_records": physical_capacity.tracker_capacity_records,
        "tracker_capacity_low_mw": physical_capacity.tracker_capacity_low_mw,
        "tracker_capacity_high_mw": physical_capacity.tracker_capacity_high_mw,
        "tracker_it_load_mw": physical_capacity.tracker_it_load_mw,
        "tracker_investment_usd": physical_capacity.tracker_investment_usd,
        "tracker_distinct_projects": physical_capacity.tracker_distinct_projects,
        "tracker_duplicate_groups": physical_capacity.tracker_duplicate_groups,
        "tracker_duplicate_rows_collapsed": physical_capacity.tracker_duplicate_rows_collapsed,
        "tracker_distinct_capacity_records": physical_capacity.tracker_distinct_capacity_records,
        "tracker_distinct_capacity_low_mw": physical_capacity.tracker_distinct_capacity_low_mw,
        "tracker_distinct_capacity_high_mw": physical_capacity.tracker_distinct_capacity_high_mw,
        "tracker_distinct_pipeline_capacity_high_mw": (
            physical_capacity.tracker_distinct_pipeline_capacity_high_mw
        ),
        "tracker_distinct_operating_capacity_high_mw": (
            physical_capacity.tracker_distinct_operating_capacity_high_mw
        ),
        "tracker_distinct_cancelled_capacity_high_mw": (
            physical_capacity.tracker_distinct_cancelled_capacity_high_mw
        ),
        "tracker_distinct_investment_usd": physical_capacity.tracker_distinct_investment_usd,
        "tracker_distinct_capacity_by_status_mw": (
            physical_capacity.tracker_distinct_capacity_by_status_mw
        ),
        "tracker_distinct_capacity_by_state_mw": (
            physical_capacity.tracker_distinct_capacity_by_state_mw
        ),
        "tracker_capacity_by_status_mw": physical_capacity.tracker_capacity_by_status_mw,
        "tracker_capacity_by_source_mw": physical_capacity.tracker_capacity_by_source_mw,
        "eia_operating_capacity_mw": physical_capacity.eia_operating_capacity_mw,
        "eia_planned_capacity_mw": physical_capacity.eia_planned_capacity_mw,
        "egrid_generator_capacity_mw": physical_capacity.egrid_generator_capacity_mw,
        "top_physical_stress_indicators": physical_capacity.physical_stress_indicators[:10],
        "physical_risk_assets_assessed": physical_risk.assets_assessed,
        "physical_risk_queue_items": physical_risk.queue_items,
        "physical_risk_assets_with_queue_evidence": physical_risk.assets_with_queue_evidence,
        "physical_risk_assets_with_permit_evidence": physical_risk.assets_with_permit_evidence,
        "physical_risk_assets_with_equipment_evidence": (
            physical_risk.assets_with_equipment_evidence
        ),
        "physical_risk_project_linked_queue_capacity_mw": (
            physical_risk.project_linked_queue_capacity_mw
        ),
        "physical_risk_level_counts": physical_risk.risk_level_counts,
        "physical_risk_critical_or_high_risk_assessments": (
            physical_risk.critical_or_high_risk_assessments
        ),
        "physical_risk_high_confidence_assessments": (physical_risk.high_confidence_assessments),
        "top_physical_risk_projects": physical_risk.top_risk_projects[:10],
        "top_physical_risk_blockers": physical_risk.top_blockers[:10],
        "physical_execution_term_rows": physical_execution.term_rows,
        "physical_execution_distinct_terms": physical_execution.distinct_terms,
        "physical_execution_duplicate_term_rows_collapsed": (
            physical_execution.duplicate_term_rows_collapsed
        ),
        "physical_execution_projects": physical_execution.projects,
        "physical_execution_by_term_type": physical_execution.distinct_by_term_type,
        "physical_execution_onsite_generation_mw_term_sum": (
            physical_execution.onsite_generation_mw_term_sum
        ),
        "physical_execution_physical_generation_capacity_mw_term_sum": (
            physical_execution.physical_generation_capacity_mw_term_sum
        ),
        "physical_execution_utility_generation_capacity_mw_term_sum": (
            physical_execution.utility_generation_capacity_mw_term_sum
        ),
        "physical_execution_risk_term_counts": physical_execution.risk_term_counts,
        "top_physical_execution_mw_terms": physical_execution.top_mw_terms[:10],
        "top_physical_execution_risk_terms": physical_execution.top_risk_terms[:10],
        "target_entities_low": TARGET_ENTITIES_LOW,
        "target_deals_low": TARGET_DEALS_LOW,
        "entity_coverage_pct_of_low_target": round(
            (source_backed_normalized_entities / TARGET_ENTITIES_LOW) * 100, 2
        ),
        "deal_coverage_pct_of_low_target": round(
            (coverage.source_backed_deals / TARGET_DEALS_LOW) * 100, 2
        ),
        "capital_deal_count": capital_metrics.deal_count,
        "capital_debt_like_deal_count": capital_metrics.debt_like_deal_count,
        "capital_total_notional_usd": capital_metrics.total_notional_usd,
        "capital_debt_like_notional_usd": capital_metrics.debt_like_notional_usd,
        "capital_distinct_deal_count": capital_metrics.distinct_deal_count,
        "capital_distinct_total_notional_usd": capital_metrics.distinct_total_notional_usd,
        "capital_distinct_debt_like_deal_count": capital_metrics.distinct_debt_like_deal_count,
        "capital_distinct_debt_like_notional_usd": (
            capital_metrics.distinct_debt_like_notional_usd
        ),
        "capital_duplicate_candidate_deal_count": capital_metrics.duplicate_candidate_deal_count,
        "capital_duplicate_candidate_notional_usd": (
            capital_metrics.duplicate_candidate_notional_usd
        ),
        "capital_top_duplicate_candidate_groups": [
            group.to_dict() for group in capital_metrics.top_duplicate_candidate_groups[:10]
        ],
        "capital_aggregate_obligation_deal_count": capital_metrics.aggregate_obligation_deal_count,
        "capital_aggregate_obligation_notional_usd": (
            capital_metrics.aggregate_obligation_notional_usd
        ),
        "capital_aggregate_obligation_distinct_deal_count": (
            capital_metrics.aggregate_obligation_distinct_deal_count
        ),
        "capital_aggregate_obligation_distinct_notional_usd": (
            capital_metrics.aggregate_obligation_distinct_notional_usd
        ),
        "capital_off_balance_sheet_usd": capital_metrics.off_balance_sheet_usd,
        "capital_off_balance_sheet_pct": capital_metrics.off_balance_sheet_pct,
        "capital_guarantee_linked_deal_count": capital_metrics.guarantee_linked_deal_count,
        "capital_guarantee_linked_usd": capital_metrics.guarantee_linked_usd,
        "capital_spv_or_non_recourse_deal_count": (capital_metrics.spv_or_non_recourse_deal_count),
        "capital_spv_or_non_recourse_usd": capital_metrics.spv_or_non_recourse_usd,
        "capital_reviewed_deal_count": capital_metrics.reviewed_deal_count,
        "capital_reviewed_total_notional_usd": capital_metrics.reviewed_total_notional_usd,
        "capital_reviewed_debt_like_deal_count": capital_metrics.reviewed_debt_like_deal_count,
        "capital_reviewed_debt_like_notional_usd": (
            capital_metrics.reviewed_debt_like_notional_usd
        ),
        "capital_pending_review_deal_count": capital_metrics.pending_review_deal_count,
        "capital_pending_review_total_notional_usd": (
            capital_metrics.pending_review_total_notional_usd
        ),
        "capital_pending_review_debt_like_deal_count": (
            capital_metrics.pending_review_debt_like_deal_count
        ),
        "capital_pending_review_debt_like_notional_usd": (
            capital_metrics.pending_review_debt_like_notional_usd
        ),
        "capital_notional_review_required_deal_count": (
            capital_metrics.notional_review_required_deal_count
        ),
        "capital_notional_review_required_usd": capital_metrics.notional_review_required_usd,
        "capital_notional_review_required_distinct_deal_count": (
            capital_metrics.notional_review_required_distinct_deal_count
        ),
        "capital_notional_review_required_distinct_usd": (
            capital_metrics.notional_review_required_distinct_usd
        ),
        "capital_top_notional_review_items": [
            item.to_dict() for item in capital_metrics.top_notional_review_items[:10]
        ],
        "capital_top_notional_review_distinct_items": [
            item.to_dict() for item in capital_metrics.top_notional_review_distinct_items[:10]
        ],
        "capital_near_term_refinancing_usd": capital_metrics.near_term_refinancing_usd,
        "capital_top_10_concentration_pct": capital_metrics.top_10_concentration_pct,
        "capital_refinancing_wall_by_quarter": capital_metrics.refinancing_wall_by_quarter,
        "capital_top_exposures": [
            exposure.to_dict() for exposure in capital_metrics.top_exposures[:10]
        ],
        "capital_downside_bearers": [
            exposure.to_dict() for exposure in capital_metrics.downside_bearers[:15]
        ],
        "capital_downside_bearer_quality": downside_bearer_quality,
        "capital_unmapped_downside_bearer_deal_count": (
            capital_metrics.unmapped_downside_bearer_deal_count
        ),
        "capital_unmapped_downside_bearer_mention_count": (
            capital_metrics.unmapped_downside_bearer_mention_count
        ),
        "capital_unmapped_downside_bearer_usd": (capital_metrics.unmapped_downside_bearer_usd),
        "compute_asset_count": compute_metrics.compute_asset_count,
        "compute_gpu_price_observation_count": compute_metrics.gpu_price_observation_count,
        "compute_depreciation_policy_count": compute_metrics.depreciation_policy_count,
        "compute_tam_claim_count": compute_metrics.tam_claim_count,
        "compute_payback_case_count": compute_metrics.payback_case_count,
        "compute_payback_blocked_case_count": compute_metrics.payback_blocked_case_count,
        "compute_payback_missing_debt_service_count": (
            compute_metrics.payback_missing_debt_service_count
        ),
        "compute_eps_impact_count": compute_metrics.eps_impact_count,
        "compute_chip_supply_observation_count": compute_metrics.chip_supply_observation_count,
        "compute_total_gpu_capex_usd": compute_metrics.total_gpu_capex_usd,
        "compute_gpu_depreciation_red_flag_count": (
            compute_metrics.gpu_depreciation_red_flag_count
        ),
        "compute_gpu_depreciation_blocked_generation_count": (
            compute_metrics.gpu_depreciation_blocked_generation_count
        ),
        "compute_tam_red_flag_count": compute_metrics.tam_red_flag_count,
        "compute_tam_blocked_claim_count": compute_metrics.tam_blocked_claim_count,
        "compute_payback_red_flag_count": compute_metrics.payback_red_flag_count,
        "compute_eps_red_flag_count": compute_metrics.eps_red_flag_count,
        "compute_eps_blocked_impact_count": compute_metrics.eps_blocked_impact_count,
        "compute_chip_supply_red_flag_count": compute_metrics.chip_supply_red_flag_count,
        "compute_chip_supply_blocked_observation_count": (
            compute_metrics.chip_supply_blocked_observation_count
        ),
    }
    evidence_audits, _, _ = audit_report_evidence(metrics)
    evidence_audits = merge_evidence_audits(
        evidence_audits,
        capital_metrics_dict,
        compute_metrics_dict,
        debt_service_metrics_dict,
        {
            "claim_audits": report_answer_metric_audits(
                timing_signal_summary=timing_signal_summary,
                review_queue_summary=review_queue_summary,
                weak_link_summary=weak_link_summary,
                debt_service_metrics_dict=debt_service_metrics_dict,
                compute_metrics_dict=compute_metrics_dict,
                capital_metrics_dict=capital_metrics_dict,
                capital_scope_summary_dict=capital_scope_summary_dict,
                capital_exposure_graph_summary=capital_exposure_graph_summary,
                contract_contagion_summary=contract_contagion_summary,
                materiality_adjudication_summary=materiality_adjudication_summary,
                materiality_adjudication_decision_summary=(
                    materiality_adjudication_decision_summary
                ),
                materiality_relevance_summary=materiality_relevance,
                mismatch_ratios=mismatch_ratios,
            )
        },
    )
    evidence_summary = summarize_evidence_audit_dicts(evidence_audits)
    capped_bubble_confidence = round(
        min(0.82, evidence_summary["max_permitted_report_confidence"]),
        4,
    )
    debt_service_timing_coverage = debt_service_timing_coverage_fields(debt_service_metrics_dict)
    graph_parity_basis = graph_parity_basis_fields(
        capital_exposure_graph_summary=capital_exposure_graph_summary,
        contract_contagion_summary=contract_contagion_summary,
        review_queue_summary=review_queue_summary,
    )

    missing = coverage.missing_corpora
    report = {
        "metadata": {
            "title": "EVIDENCE-GATED BURRY REPORT - AI/Data Center/Financing Ecosystem",
            "version": "source-coverage-gated-v2",
            "generated_at": datetime.now(UTC).isoformat(),
            "methodology": (
                "Coverage-grounded report. Final market conclusions are blocked until "
                "source-backed filings, documents, project records, physical records, and deals "
                "reach sufficient breadth and LLM adjudication status."
            ),
            "adjudication_note": (
                "Legacy fields named human_review_status or reviewed_* mean LLM "
                "adjudication status in this system; no required operator gate is assumed."
            ),
            "high_confidence_final": False,
        },
        "source_coverage": coverage_dict,
        "entity_universe_summary": entity_universe_summary,
        "capital_exposure_graph": capital_exposure_graph_summary,
        "ownership_graph": ownership_graph_summary,
        "weak_links": weak_link_summary,
        "contract_contagion_paths": contract_contagion_summary,
        "review_queue": review_queue_summary,
        "materiality_adjudication": materiality_adjudication_summary,
        "materiality_adjudication_decisions": materiality_adjudication_decision_summary,
        "materiality_relevance_linkage": materiality_relevance,
        "timing_signals": timing_signal_summary,
        "source_invariant_audit": source_invariant_audit,
        "capital_scope": capital_scope_summary_dict,
        "physical_capacity_summary": physical_capacity_dict,
        "physical_execution_summary": physical_execution.to_dict(),
        "physical_risk_summary": physical_risk_dict,
        "queue_project_match_summary": queue_match_summary,
        "physical_record_match_summary": physical_record_match_summary,
        "capital_structure": capital_metrics_dict,
        "compute_economics": compute_metrics_dict,
        "debt_service_mismatch": debt_service_metrics_dict,
        "burry_separation_test": mismatch_ratios,
        "ai_direct_core_verdict": ai_direct_core_verdict,
        "key_metrics": metrics,
        "executive_summary": {
            "overall_assessment": (
                "Final bubble/no-bubble conclusion is not yet supported. Current output is a "
                "source acquisition and evidence coverage report, not an investment conclusion."
            ),
            "bubble_confidence": capped_bubble_confidence,
            "evidence_gate_passed": False,
            "missing_source_corpora": missing,
            "coverage_sentence": (
                f"Covered {coverage.filings} filings, "
                f"{source_backed_normalized_entities} source-backed normalized entities, "
                f"{coverage.projects} projects, and {coverage.source_backed_deals} "
                f"source-backed deals. Compute economics coverage has "
                f"{coverage.source_backed_compute_rows} source-backed rows. "
                f"Physical execution extraction has "
                f"{physical_execution.distinct_terms} distinct source-backed terms "
                f"across {physical_execution.projects} projects. "
                f"Entity expansion found "
                f"{entity_universe_expanded_ciks} SEC CIK matches from "
                f"{entity_universe_mentions_extracted} source-backed mentions. "
                f"Acquisition catalog currently queues {coverage.catalog_sources} "
                f"source targets; {coverage.acquisition_artifacts_acquired}/"
                f"{coverage.acquisition_artifacts_attempted} attempted artifacts are acquired. "
                f"The LLM adjudication queue currently has "
                f"{review_queue_summary.get('items', 0)} source-backed blocker items. "
                f"The materiality-first pass has packaged "
                f"{materiality_adjudication_summary.get('packets', 0)} top blockers "
                f"for automated LLM adjudication. "
                f"The automated adjudication decision pass has source-quote-backed "
                f"{materiality_adjudication_decision_summary.get('source_quote_backed_decisions', 0)} "
                f"and row-context-backed "
                f"{materiality_adjudication_decision_summary.get('row_context_backed_decisions', 0)} "
                f"packet decisions and currently approves "
                f"{materiality_adjudication_decision_summary.get('approved_for_metric_use', 0)} "
                f"rows for metric use across "
                f"{materiality_adjudication_decision_summary.get('final_metric_group_count', 0)} "
                f"deduped metric groups, with "
                f"{materiality_adjudication_decision_summary.get('needs_deeper_extraction', 0)} "
                f"rows still requiring deeper extraction. "
                f"Within the deduped final materiality metric, "
                f"${materiality_relevance.get('established_usd', 0) / 1_000_000_000_000:.3f}T "
                f"has established direct/watchlist AI-data-center linkage while "
                f"{materiality_relevance.get('not_established_pct', 0) * 100:.1f}% "
                f"does not yet have established thesis linkage. "
                f"The timing calendar currently has "
                f"{timing_signal_summary.get('source_backed_signals', 0)} "
                f"source-backed crack-window signals. "
                f"The debt-service pass has measured "
                f"${debt_service_metrics.measured_annual_interest_usd:,.0f} of annual "
                f"interest/debt-service proxy from explicit source-backed rates, with "
                f"${debt_service_metrics.missing_rate_notional_usd:,.0f} of debt-like "
                f"notional still missing explicit rate evidence."
            ),
        },
        "burry_question_answers": {
            "is_this_a_bubble": {
                "answer": (
                    "Tiered. ECOSYSTEM-WIDE: not assessable as a clean ratio -- the broad "
                    "materiality metric is dominated by non-AI debt, so the AI-linked share is not "
                    "a meaningful denominator and no defensible total-AI-leverage figure exists "
                    "yet; the broad binary stays gated. AI-DIRECT CORE: "
                    f"{ai_direct_core_verdict.get('core_verdict')} at confidence "
                    f"{ai_direct_core_verdict.get('core_verdict_confidence')} -- source-backed "
                    "cash-flow fragility (7 of 11 issuers loss-making, refinancing-dependent, "
                    "GPU-collateralized, holed take-or-pay) in the financed cluster, resting mainly "
                    "on the one source-backed interest-coverage leg. See 'ai_direct_core_verdict' "
                    "for the scoped verdict, reconciled crack timing, weakest links, data gaps, and "
                    "bear case."
                ),
                "ecosystem_confidence": capped_bubble_confidence,
                "ai_direct_core_verdict": ai_direct_core_verdict,
                "burry_separation_test_reference": "See top-level 'burry_separation_test' for the actual mismatch ratios (cluster DSCR, deliverable capacity %, GPU life gap, missing-rate %). These are the assumption-fragility signals that turn raw notional into a bubble diagnosis.",
                "required_next_evidence": [
                    "Exhaustive (not curated-floor) AI-direct maturity census",
                    "Load-interconnection / utility large-load-study data for a real data-center "
                    "firm-vs-queue rate (generation ISO queues are already ingested but are the "
                    "wrong lens for load)",
                    "AI-direct GPU-SPV debt into the capital-exposure graph",
                    "NVIDIA->OpenAI ($100B framework) filing verification to close the macro "
                    "round-trip loop (the NVIDIA<->CoreWeave and NVIDIA<->Nebius reciprocal loops "
                    "are now filing-verified; see 'circular_financing')",
                ],
            },
            "how_large": {
                "answer": (
                    "Partially measured, still not final. Current source-backed deal coverage "
                    "now supports a preliminary capital-structure calculation, but extraction "
                    "review and broader SEC/SPV coverage are still required before this can be "
                    "treated as ecosystem leverage."
                ),
                "current_source_backed_deals": coverage.source_backed_deals,
                "low_target_deals": TARGET_DEALS_LOW,
                "current_capital_deal_count": capital_metrics.deal_count,
                "current_debt_like_notional_usd": capital_metrics.debt_like_notional_usd,
                "current_distinct_debt_like_notional_usd": (
                    capital_metrics.distinct_debt_like_notional_usd
                ),
                **capital_materiality_scope_fields(
                    capital_debt_like_notional_usd=capital_metrics.debt_like_notional_usd,
                    materiality_decision_summary=materiality_adjudication_decision_summary,
                ),
                **materiality_relevance_scope_fields(materiality_relevance),
                "current_duplicate_candidate_notional_usd": (
                    capital_metrics.duplicate_candidate_notional_usd
                ),
                "current_aggregate_obligation_distinct_notional_usd": (
                    capital_metrics.aggregate_obligation_distinct_notional_usd
                ),
                "current_total_notional_usd": capital_metrics.total_notional_usd,
                "current_reviewed_debt_like_notional_usd": (
                    capital_metrics.reviewed_debt_like_notional_usd
                ),
                "current_pending_review_debt_like_notional_usd": (
                    capital_metrics.pending_review_debt_like_notional_usd
                ),
                "current_notional_review_required_usd": (
                    capital_metrics.notional_review_required_usd
                ),
                "current_notional_review_required_distinct_usd": (
                    capital_metrics.notional_review_required_distinct_usd
                ),
                "top_notional_review_items": [
                    item.to_dict() for item in capital_metrics.top_notional_review_items[:10]
                ],
                "top_notional_review_distinct_items": [
                    item.to_dict()
                    for item in capital_metrics.top_notional_review_distinct_items[:10]
                ],
                "top_review_queue_items": review_queue_summary.get("top_items", [])[:10],
                "top_materiality_adjudication_packets": materiality_adjudication_summary.get(
                    "top_packets",
                    [],
                )[:10],
                "top_materiality_adjudication_decisions": (
                    materiality_adjudication_decision_summary.get("top_decisions", [])[:10]
                ),
                "top_distinct_capital_review_queue_items": review_queue_summary.get(
                    "top_distinct_capital_items",
                    [],
                )[:10],
                "current_guarantee_linked_usd": capital_metrics.guarantee_linked_usd,
                "current_spv_or_non_recourse_usd": capital_metrics.spv_or_non_recourse_usd,
                "current_measured_annual_debt_service_usd": (
                    debt_service_metrics.measured_annual_interest_usd
                ),
                "current_debt_service_measured_rate_notional_usd": (
                    debt_service_metrics.measured_rate_notional_usd
                ),
                "current_debt_service_missing_rate_notional_usd": (
                    debt_service_metrics.missing_rate_notional_usd
                ),
                "current_debt_service_rate_outlier_notional_usd": (
                    debt_service_metrics.rate_outlier_notional_usd
                ),
            },
            "when_cracks": {
                "answer": (
                    "Partially measured, still not final. The report now computes source-backed "
                    "refinancing, physical delivery, and compute-economics timing signals, but "
                    "the crack window remains a candidate until the largest maturities, project "
                    "COD dates, utilization evidence, power delays, and compute assumptions are "
                    "LLM-adjudicated and corroborated."
                ),
                "current_timing_signal_count": timing_signal_summary.get("signals", 0),
                "current_timing_source_backed_signals": timing_signal_summary.get(
                    "source_backed_signals",
                    0,
                ),
                "current_timing_critical_or_high_signals": timing_signal_summary.get(
                    "critical_or_high_signals",
                    0,
                ),
                "current_timing_ai_infra_relevant_signals": timing_signal_summary.get(
                    "ai_infra_relevant_signals",
                    0,
                ),
                "candidate_peak_stress_quarter": timing_signal_summary.get("peak_stress_quarter"),
                "candidate_stress_window_start": timing_signal_summary.get(
                    "candidate_stress_window_start"
                ),
                "candidate_stress_window_end": timing_signal_summary.get(
                    "candidate_stress_window_end"
                ),
                "leading_indicator_monitor": leading_indicator_monitor,
                "current_timing_capital_refinancing_usd_2024_2030": (
                    timing_signal_summary.get("capital_refinancing_usd_2024_2030", 0)
                ),
                "current_timing_ai_infra_capital_refinancing_usd_2024_2030": (
                    timing_signal_summary.get(
                        "ai_infra_capital_refinancing_usd_2024_2030",
                        0,
                    )
                ),
                "current_timing_forward_refinancing_as_of_quarter": (
                    timing_signal_summary.get("forward_refinancing_as_of_quarter")
                ),
                "current_timing_capital_refinancing_historical_to_as_of_usd": (
                    timing_signal_summary.get(
                        "capital_refinancing_historical_to_as_of_usd",
                        0,
                    )
                ),
                "current_timing_ai_infra_capital_refinancing_historical_to_as_of_usd": (
                    timing_signal_summary.get(
                        "ai_infra_capital_refinancing_historical_to_as_of_usd",
                        0,
                    )
                ),
                "current_timing_capital_refinancing_forward_from_as_of_usd": (
                    timing_signal_summary.get(
                        "capital_refinancing_forward_from_as_of_usd",
                        0,
                    )
                ),
                "current_timing_ai_infra_capital_refinancing_forward_from_as_of_usd": (
                    timing_signal_summary.get(
                        "ai_infra_capital_refinancing_forward_from_as_of_usd",
                        0,
                    )
                ),
                "current_timing_forward_peak_refinancing_quarter": (
                    timing_signal_summary.get("forward_peak_refinancing_quarter")
                ),
                "current_timing_forward_peak_refinancing_usd": (
                    timing_signal_summary.get("forward_peak_refinancing_usd", 0)
                ),
                "current_timing_forward_peak_ai_infra_refinancing_quarter": (
                    timing_signal_summary.get("forward_peak_ai_infra_refinancing_quarter")
                ),
                "current_timing_forward_peak_ai_infra_refinancing_usd": (
                    timing_signal_summary.get(
                        "forward_peak_ai_infra_refinancing_usd",
                        0,
                    )
                ),
                "current_timing_physical_capacity_mw_2024_2030": (
                    timing_signal_summary.get("physical_capacity_mw_2024_2030", 0)
                ),
                "current_timing_compute_amount_usd_2024_2030": timing_signal_summary.get(
                    "compute_amount_usd_2024_2030",
                    0,
                ),
                "current_timing_chip_supply_capacity_mw_2024_2030": (
                    timing_signal_summary.get("chip_supply_capacity_mw_2024_2030", 0)
                ),
                "current_top_timing_quarters": timing_signal_summary.get("top_quarters", [])[:10],
                "current_top_timing_signals": timing_signal_summary.get("top_signals", [])[:10],
                **debt_service_timing_coverage,
                "current_queue_records": coverage.queue_records,
                "current_queue_capacity_mw": physical_capacity.queue_capacity_mw,
                "current_data_center_queue_records": physical_capacity.data_center_queue_records,
                "current_data_center_queue_capacity_mw": (
                    physical_capacity.data_center_queue_capacity_mw
                ),
                "top_data_center_queue_projects": (
                    physical_capacity.top_data_center_queue_projects[:10]
                ),
                "current_queue_project_strong_matches": queue_match_summary.get(
                    "strong_matches", 0
                ),
                "current_project_linked_queue_capacity_mw": queue_match_summary.get(
                    "loader_queue_capacity_mw", 0
                ),
                "current_physical_risk_assets_assessed": physical_risk.assets_assessed,
                "current_physical_risk_assets_with_queue_evidence": (
                    physical_risk.assets_with_queue_evidence
                ),
                "current_physical_risk_assets_with_permit_evidence": (
                    physical_risk.assets_with_permit_evidence
                ),
                "current_physical_risk_assets_with_equipment_evidence": (
                    physical_risk.assets_with_equipment_evidence
                ),
                "current_physical_risk_critical_or_high_assessments": (
                    physical_risk.critical_or_high_risk_assessments
                ),
                "top_physical_risk_projects": physical_risk.top_risk_projects[:10],
                "top_physical_risk_blockers": physical_risk.top_blockers[:10],
                "current_physical_execution_distinct_terms": physical_execution.distinct_terms,
                "current_physical_execution_projects": physical_execution.projects,
                "current_physical_execution_onsite_generation_mw_term_sum": (
                    physical_execution.onsite_generation_mw_term_sum
                ),
                "current_physical_execution_risk_term_counts": (
                    physical_execution.risk_term_counts
                ),
                "top_physical_execution_mw_terms": physical_execution.top_mw_terms[:10],
                "top_physical_execution_risk_terms": physical_execution.top_risk_terms[:10],
                "current_eia_planned_capacity_mw": physical_capacity.eia_planned_capacity_mw,
                "current_permit_records": coverage.permit_records,
                "current_refinancing_wall_by_quarter": (
                    capital_metrics.refinancing_wall_by_quarter
                ),
                "current_top_weak_links": weak_link_summary.get("top_weak_links", [])[:15],
                "current_top_debt_service_weak_links": weak_link_summary.get(
                    "top_debt_service_weak_links",
                    [],
                )[:15],
                "current_top_review_queue_items": review_queue_summary.get("top_items", [])[:10],
                "current_top_materiality_adjudication_packets": (
                    materiality_adjudication_summary.get("top_packets", [])[:10]
                ),
                "current_top_materiality_adjudication_decisions": (
                    materiality_adjudication_decision_summary.get("top_decisions", [])[:10]
                ),
                "current_refinancing_wall_review_status": {
                    "reviewed_debt_like_notional_usd": (
                        capital_metrics.reviewed_debt_like_notional_usd
                    ),
                    "pending_review_debt_like_notional_usd": (
                        capital_metrics.pending_review_debt_like_notional_usd
                    ),
                },
                "current_compute_payback_red_flags": compute_metrics.payback_red_flag_count,
                "current_eps_depreciation_red_flags": compute_metrics.eps_red_flag_count,
                "current_measured_annual_debt_service_usd": (
                    debt_service_metrics.measured_annual_interest_usd
                ),
                "current_distinct_measured_annual_debt_service_usd": (
                    debt_service_metrics.distinct_measured_annual_interest_usd
                ),
                "current_debt_service_missing_rate_notional_usd": (
                    debt_service_metrics.missing_rate_notional_usd
                ),
                "current_distinct_debt_service_missing_rate_notional_usd": (
                    debt_service_metrics.distinct_missing_rate_notional_usd
                ),
                "current_debt_service_measured_rate_notional_coverage_pct": (
                    debt_service_metrics.measured_rate_notional_coverage_pct
                ),
                "current_distinct_debt_service_measured_rate_notional_coverage_pct": (
                    debt_service_metrics.distinct_measured_rate_notional_coverage_pct
                ),
                "current_cash_flow_mismatch_red_flags": (
                    debt_service_metrics.cash_flow_mismatch_red_flag_count
                ),
                "current_debt_service_maturity_wall_by_quarter": (
                    debt_service_metrics.debt_service_wall_by_quarter
                ),
                "current_distinct_debt_service_maturity_wall_by_quarter": (
                    debt_service_metrics.distinct_debt_service_wall_by_quarter
                ),
                "current_top_debt_service_quarters": [
                    item.to_dict() for item in debt_service_metrics.top_debt_service_quarters[:10]
                ],
                "current_top_distinct_debt_service_quarters": [
                    item.to_dict()
                    for item in debt_service_metrics.top_distinct_debt_service_quarters[:10]
                ],
                "current_top_debt_service_duplicate_candidate_groups": [
                    item.to_dict()
                    for item in debt_service_metrics.top_duplicate_candidate_groups[:10]
                ],
                "current_top_entity_debt_service_risks": [
                    item.to_dict()
                    for item in debt_service_metrics.top_entity_debt_service_risks[:15]
                ],
                "current_top_debt_service_obligations": [
                    item.to_dict()
                    for item in debt_service_metrics.top_debt_service_obligations[:10]
                ],
                "current_top_debt_service_coverage_gaps": [
                    item.to_dict()
                    for item in debt_service_metrics.top_debt_service_coverage_gaps[:10]
                ],
                "current_top_cash_flow_mismatch_cases": [
                    item.to_dict()
                    for item in debt_service_metrics.top_cash_flow_mismatch_cases[:10]
                ],
            },
            "hidden_risks_and_contagion": {
                "answer": (
                    "Partially measured, still not final. A source-backed capital exposure "
                    "graph now ranks connected risk components and contagion hubs from "
                    "extracted deal counterparties; capacity-weighted PPA offtaker "
                    "concentration now surfaces hyperscaler demand-side hubs that carry MW "
                    "rather than dollar notional; and a contract/ownership path layer joins "
                    "tranche, collateral, guarantee, SPV, and parent-control evidence where "
                    "exact legal-name matches exist. Full contagion mapping still requires "
                    "broader LLM-adjudicated counterparty, ownership, insurer, and contract-"
                    "term coverage."
                ),
                "current_ownership_records": coverage.ownership_records,
                "current_ownership_graph_nodes": ownership_graph_summary.get("nodes", 0),
                "current_ownership_graph_relationships": ownership_graph_summary.get(
                    "relationships", 0
                ),
                "current_ownership_graph_active_relationships": ownership_graph_summary.get(
                    "active_relationships", 0
                ),
                "current_ownership_graph_direct_consolidation_edges": (
                    ownership_graph_summary.get("direct_consolidation_edges", 0)
                ),
                "current_ownership_graph_ultimate_consolidation_edges": (
                    ownership_graph_summary.get("ultimate_consolidation_edges", 0)
                ),
                "current_top_ownership_parents": ownership_graph_summary.get(
                    "top_parents_by_child_count", []
                )[:10],
                "current_capital_exposure_nodes": capital_exposure_graph_summary.get("nodes", 0),
                "current_capital_exposure_edges": capital_exposure_graph_summary.get("edges", 0),
                "current_capital_exposure_source_backed_edges": (
                    capital_exposure_graph_summary.get("source_backed_edges", 0)
                ),
                "current_capital_exposure_ai_infra_relevant_edges": (
                    capital_exposure_graph_summary.get("ai_infra_relevant_edges", 0)
                ),
                "current_capital_exposure_direct_ai_keyword_edges": (
                    capital_exposure_graph_summary.get("direct_ai_keyword_edges", 0)
                ),
                "current_capital_exposure_connected_components": (
                    capital_exposure_graph_summary.get("connected_components", 0)
                ),
                "current_capital_exposure_largest_component_notional_usd": (
                    capital_exposure_graph_summary.get("largest_component_notional_usd", 0)
                ),
                "current_capital_exposure_largest_component_ai_infra_relevant_notional_usd": (
                    capital_exposure_graph_summary.get(
                        "largest_component_ai_infra_relevant_notional_usd",
                        0,
                    )
                ),
                "current_capital_exposure_ai_infra_component_count": (
                    capital_exposure_graph_summary.get("ai_infra_component_count", 0)
                ),
                "current_capital_exposure_top_ai_infra_component_nodes": (
                    capital_exposure_graph_summary.get("top_ai_infra_component_nodes", 0)
                ),
                "current_capital_exposure_top_ai_infra_component_edges": (
                    capital_exposure_graph_summary.get("top_ai_infra_component_edges", 0)
                ),
                "current_capital_exposure_top_ai_infra_component_notional_usd": (
                    capital_exposure_graph_summary.get("top_ai_infra_component_notional_usd", 0)
                ),
                "current_top_ai_infra_capital_exposure_edges": capital_exposure_graph_summary.get(
                    "top_ai_infra_exposure_edges",
                    [],
                )[:10],
                "current_top_ai_infra_obligors": capital_exposure_graph_summary.get(
                    "top_ai_infra_obligors",
                    [],
                )[:10],
                "current_top_capital_exposure_components": capital_exposure_graph_summary.get(
                    "top_components_by_notional",
                    [],
                )[:10],
                "current_top_ai_infra_capital_exposure_components": (
                    capital_exposure_graph_summary.get(
                        "top_ai_infra_components_by_notional",
                        [],
                    )[:10]
                ),
                "current_top_capital_contagion_hubs": capital_exposure_graph_summary.get(
                    "top_contagion_hubs",
                    [],
                )[:10],
                "current_top_ai_infra_contagion_hubs": capital_exposure_graph_summary.get(
                    "top_ai_infra_contagion_hubs",
                    [],
                )[:10],
                "current_top_ai_infra_ppa_offtakers": capital_exposure_graph_summary.get(
                    "top_ai_infra_ppa_offtakers",
                    [],
                )[:10],
                "current_top_ai_infra_ppa_offtaker_families": (
                    capital_exposure_graph_summary.get(
                        "top_ai_infra_ppa_offtaker_families",
                        [],
                    )[:10]
                ),
                "current_contract_contagion_paths": contract_contagion_summary.get("paths", 0),
                "current_contract_contagion_source_backed_paths": (
                    contract_contagion_summary.get("source_backed_paths", 0)
                ),
                "current_contract_contagion_ownership_expanded_paths": (
                    contract_contagion_summary.get("ownership_expanded_paths", 0)
                ),
                "current_contract_contagion_high_or_critical_paths": (
                    contract_contagion_summary.get("high_or_critical_paths", 0)
                ),
                "current_contract_contagion_ai_infra_relevant_paths": (
                    contract_contagion_summary.get("ai_infra_relevant_paths", 0)
                ),
                "current_contract_contagion_ai_infra_relevant_notional_usd": (
                    contract_contagion_summary.get("ai_infra_relevant_notional_usd", 0)
                ),
                **graph_parity_basis,
                "current_top_contract_contagion_paths": contract_contagion_summary.get(
                    "top_paths",
                    [],
                )[:10],
                "current_top_ownership_expanded_contract_contagion_paths": (
                    contract_contagion_summary.get("top_ownership_expanded_paths", [])[:10]
                ),
                "current_guarantee_linked_usd": capital_metrics.guarantee_linked_usd,
                "current_spv_or_non_recourse_usd": capital_metrics.spv_or_non_recourse_usd,
                "current_notional_review_required_usd": (
                    capital_metrics.notional_review_required_usd
                ),
                "current_notional_review_required_distinct_usd": (
                    capital_metrics.notional_review_required_distinct_usd
                ),
                "current_top_review_queue_items": review_queue_summary.get("top_items", [])[:10],
                "current_top_materiality_adjudication_packets": (
                    materiality_adjudication_summary.get("top_packets", [])[:10]
                ),
                "current_top_materiality_adjudication_decisions": (
                    materiality_adjudication_decision_summary.get("top_decisions", [])[:10]
                ),
                "current_top_debt_service_weak_links": weak_link_summary.get(
                    "top_debt_service_weak_links",
                    [],
                )[:15],
            },
            "who_bears_downside": {
                "answer": (
                    "Partially measured, still not final. Current extraction can identify some "
                    "bearer roles from structured deal rows, and the capital graph now separates "
                    "AI/data-center-linked risk bearers from the raw non-thesis bearer ranking. "
                    "Counterparty extraction from SEC agreements remains incomplete and pending "
                    "LLM adjudication."
                ),
                "current_extracted_deals": coverage.extracted_deals,
                "current_downside_bearers": [
                    exposure.to_dict() for exposure in capital_metrics.downside_bearers[:15]
                ],
                "current_downside_bearer_quality": downside_bearer_quality,
                "current_top_ai_infra_risk_bearers": capital_exposure_graph_summary.get(
                    "top_ai_infra_risk_bearers",
                    [],
                )[:10],
                "current_unmapped_downside_bearer_deal_count": (
                    capital_metrics.unmapped_downside_bearer_deal_count
                ),
                "current_unmapped_downside_bearer_mention_count": (
                    capital_metrics.unmapped_downside_bearer_mention_count
                ),
                "current_unmapped_downside_bearer_usd": (
                    capital_metrics.unmapped_downside_bearer_usd
                ),
            },
            "compute_economics": {
                "answer": (
                    "Blocked until GPU depreciation, price/rental, TAM, payback, EPS, and "
                    "chip-supply rows are loaded with source URI, retrieval timestamp, and "
                    "raw content hash."
                    if compute_metrics.status == "blocked_missing_compute_economics_evidence"
                    else "Partially measured. Compute economics rows are loaded, but final "
                    "bubble timing still requires corroborated utilization, price, and supply "
                    "evidence across entities."
                ),
                "status": compute_metrics.status,
                "current_compute_assets": compute_metrics.compute_asset_count,
                "current_gpu_price_observations": compute_metrics.gpu_price_observation_count,
                "current_gpu_depreciation_blocked_generations": (
                    compute_metrics.gpu_depreciation_blocked_generation_count
                ),
                "current_tam_claims": compute_metrics.tam_claim_count,
                "current_tam_blocked_claims": compute_metrics.tam_blocked_claim_count,
                "current_payback_cases": compute_metrics.payback_case_count,
                "current_payback_blocked_cases": compute_metrics.payback_blocked_case_count,
                "current_payback_missing_debt_service_cases": (
                    compute_metrics.payback_missing_debt_service_count
                ),
                "current_eps_impacts": compute_metrics.eps_impact_count,
                "current_eps_blocked_impacts": compute_metrics.eps_blocked_impact_count,
                "current_chip_supply_observations": (compute_metrics.chip_supply_observation_count),
                "current_chip_supply_blocked_observations": (
                    compute_metrics.chip_supply_blocked_observation_count
                ),
                "top_gpu_depreciation_risks": [
                    item.to_dict() for item in compute_metrics.top_gpu_depreciation_risks[:10]
                ],
                "top_payback_stress_cases": [
                    item.to_dict() for item in compute_metrics.top_payback_stress_cases[:10]
                ],
                "top_eps_impacts": [
                    item.to_dict() for item in compute_metrics.top_eps_impacts[:10]
                ],
                "debt_service_status": debt_service_metrics.status,
                "current_payback_cases_with_debt_service": (
                    debt_service_metrics.payback_cases_with_debt_service
                ),
                "current_payback_cases_missing_debt_service": (
                    debt_service_metrics.payback_cases_missing_debt_service
                ),
                "current_cash_flow_mismatch_red_flags": (
                    debt_service_metrics.cash_flow_mismatch_red_flag_count
                ),
                "top_cash_flow_mismatch_cases": [
                    item.to_dict()
                    for item in debt_service_metrics.top_cash_flow_mismatch_cases[:10]
                ],
            },
        },
        "evidence_quality": {
            "summary": evidence_summary,
            "materiality_semantic_summary": materiality_semantics,
            "claim_audits": evidence_audits,
        },
        "next_required_acquisition": [
            "Run EDGAR manifest acquisition across all public watchlist CIKs.",
            "Download prioritized EDGAR source documents and exhibit attachments.",
            "Acquire utility large-load / load-interconnection studies (the generation ISO queues "
            "for ERCOT/PJM/MISO/CAISO/NYISO/SPP are already ingested but do not capture data-center load).",
            "Ingest state PUC/EPA/local permit records for top project geographies.",
            "Ingest ownership registry records and project tracker rows.",
            "Load extracted deal candidates through the capital evidence pipeline after review.",
            "Load compute economics evidence for GPU depreciation, rental rates, TAM claims, capex payback, EPS depreciation impact, and chip supply.",
            "Acquire contract-level coupon, interest-rate, amortization, rent schedule, utilization, and contracted-revenue evidence for debt-service coverage.",
        ],
    }
    return report


def _methodology_appendix(report: dict[str, Any], verdict: dict[str, Any]) -> str:
    """A methodology / assumptions / limitations appendix (Final Report Output-Quality item)."""

    audits = len(report.get("evidence_quality", {}).get("claim_audits", []) or [])
    return (
        "## Methodology, Assumptions & Limitations\n\n"
        "**Data used.** Primary SEC/SEDAR filings (10-K, 10-Q, 8-K, 20-F, S-1, DEF 14A, SC 13D/13G, "
        "Form 4, credit-agreement & guaranty exhibits), supplier earnings calls/IR, utility 10-Ks + "
        "PUC dockets, and the broad acquired corpus (filings, deals, projects, ISO queues, ownership/"
        "LEI). Every cluster layer is built from an adversarially-verified handoff fixture whose rows "
        "carry a source URI and a filing-verified vs analyst-flagged vs rejected verdict.\n\n"
        "**Evidence discipline.** Each claim is tiered (MEASURED > CORROBORATED > SINGLE-SOURCE > "
        "INFERRED > UNSUPPORTED); the report confidence is capped by its weakest load-bearing claim "
        f"(any UNSUPPORTED -> 0.25). {audits} per-metric claim audits trace figures to evidence. "
        "Source-backed and illustrative/blocked legs are labeled distinctly throughout; nothing is "
        "asserted above its tier.\n\n"
        "**Key assumptions (labeled, not hidden).** Forward scenario stress parameters (utilization "
        "miss, rate shock, GPU-life compression) are assumptions applied to primary-sourced base "
        "financials. Recourse classification, household-routing buckets, and severity weights are "
        "stated conventions. Per-lender syndicate allocations, per-DDTL-facility debt-holder "
        "attribution, and realistic-utilization DSCR are NOT publicly disclosed and are left "
        "illustrative or null rather than estimated as fact.\n\n"
        "**Limitations.** (1) Depth is on a bounded ~8-11 issuer financed core, not the full "
        "1,200-2,000-entity ambition; the cluster-boundary test shows adjacent crypto-AI names mostly "
        "fail the in-scope gate, so the core is specific, not exhaustive. (2) The ecosystem-wide gate "
        "is held at 0.25 BY DESIGN -- the broad metric is mostly non-AI debt, so no defensible "
        "total-AI denominator exists. (3) Per-deal utilization/debt-service disclosure is thin; the "
        "leg quantifies that opacity rather than papering over it. (4) The knowledge graph is "
        "CSV-backed with the cluster injected, not a production Neo4j+GDS engine; satellite/FOIA and "
        "continuous live ingest are scaffolded, not fully integrated. The scoped-core conclusions are "
        "grounded; the ecosystem-scale ambition is explicitly incomplete.\n"
    )


def _executive_conclusion(verdict: dict[str, Any]) -> str:
    """A crisp scoped binary conclusion + confidence + timeline + top risks for the top of the report."""

    if not verdict or not verdict.get("core_verdict"):
        return ""
    ct = verdict.get("crack_timing", {}) or {}
    fwd = (ct.get("forward_scenarios") or {}) if isinstance(ct, dict) else {}
    risks = (verdict.get("top_actionable_risks", {}) or {}).get("risks") or []
    top3 = "; ".join(
        f"({r.get('rank')}) {r.get('title')}" for r in risks[:3]
    )
    sev = str(fwd.get("severity_read") or "").split(".")[0]
    return (
        "## Scoped Burry Conclusion\n\n"
        f"**Financed AI-direct core — `{verdict.get('core_verdict')}` at confidence "
        f"{verdict.get('core_verdict_confidence')}.** "
        "Bubble dynamics ARE present in the financed neocloud/data-center cluster: source-backed "
        "cash-flow fragility, an accounting-integrity overlay, and concentrated contagion. "
        f"**Ecosystem-wide — `{verdict.get('ecosystem_verdict')}`** (the broad debt metric is mostly "
        "non-AI, so no defensible total-AI denominator exists; this is a scope statement, not a clean "
        "bill of health).\n\n"
        f"**When it cracks:** near-term refinancing pressure {ct.get('near_term_pressure_window', 'n/a')}; "
        f"forward stress — {sev or 'see scenario table'}.\n\n"
        f"**Top risks:** {top3 or 'see register below'}.\n\n"
        "_Confidence is deliberately not a near-certainty: the credible non-bubble case and "
        "forward-assumption dependence discount it. Every figure below is tagged source-backed vs "
        "illustrative; the ecosystem evidence gate remains held at 0.25 by design._\n"
    )


def _verdict_layer_lines(verdict: dict[str, Any]) -> dict[str, str]:  # noqa: PLR0912
    """Build the one-line per-layer summaries for the verdict markdown section."""

    _ds = verdict.get("demand_side_funding", {}) or {}
    if _ds.get("aggregate_ai_capex_usd") is not None:
        demand_line = (
            f"aggregate AI capex ${round((_ds.get('aggregate_ai_capex_usd') or 0) / 1e9, 1)}B, "
            f"cash-coverage of capex {_ds.get('cash_coverage_of_capex')}x, "
            f"{_ds.get('cash_funded_players')}/{_ds.get('player_count')} players self-funding; "
            f"commitments to the core ${round((_ds.get('aggregate_datacenter_purchase_commitments_usd') or 0) / 1e9, 1)}B. "
            f"{_ds.get('bear_case_read', '')}"
        )
    else:
        demand_line = "pending source-backed demand-side extraction."

    _pw = verdict.get("power_ratepayer_exposure", {}) or {}
    if _pw.get("ratepayer_socialized_pct") is not None:
        power_line = (
            f"AI-datacenter load {round((_pw.get('total_ai_datacenter_load_mw') or 0) / 1000, 1)} GW; "
            f"~{_pw.get('ratepayer_socialized_pct')}% of generation/grid build "
            f"(${round((_pw.get('ratepayer_socialized_usd') or 0) / 1e9, 1)}B) socialized to ratepayers. "
            f"{_pw.get('ratepayer_downside_read', '')}"
        )
    else:
        power_line = "pending source-backed utility/ratepayer extraction."

    _eh = verdict.get("ultimate_end_holders", {}) or {}
    if _eh.get("total_kept_holders") is not None:
        _eh_bucket = _eh.get("count_by_routing_bucket", {}) or {}
        holder_line = (
            f"{_eh.get('filing_verified_holders')}/{_eh.get('total_kept_holders')} disclosed holders "
            f"filing-verified across {_eh.get('entity_count')} entities; household-routed "
            f"(insurer/pension/index) {_eh.get('household_routed_count_pct')}% by count "
            f"(~{_eh.get('household_routed_value_pct')}% by disclosed value); "
            f"buckets {_eh_bucket}. {str(_eh.get('ultimate_downside_read', '')).split(':')[0]}. "
            f"Caveat: private-placement DDTL/SPV debt holders are not 13-F-visible."
        )
    else:
        holder_line = "pending source-backed end-holder extraction."

    _dr = (_eh.get("debt_side_funding_routing") or {}) if isinstance(_eh, dict) else {}
    if _dr.get("lender_count") is not None:
        holder_line += (
            f" Debt side: {_dr.get('lenders_with_household_routed_funding')}/{_dr.get('lender_count')} "
            f"private-credit lenders draw material insurance/pension funding (median "
            f"~{_dr.get('median_insurance_funded_share_pct')}% insurance-funded; "
            f"{_dr.get('filing_verified_sources')} sources filing-verified) — the cluster's "
            f"private-placement debt loss routes to policyholders/retirees, the channel 13-F equity "
            f"data cannot show."
        )

    _eq = verdict.get("supply_side_equipment_constraints", {}) or {}
    if _eq.get("chokepoint_count") is not None:
        equip_line = (
            f"{_eq.get('gating_chokepoint_count')}/{_eq.get('chokepoint_count')} verified supply-chain "
            f"chokepoints gate the buildout (lead times up to ~{_eq.get('max_lead_time_months')} months, "
            f"median ~{_eq.get('median_lead_time_months')}); single-source/duopoly: "
            f"{', '.join((_eq.get('single_source_or_duopoly_chokepoints') or [])[:6])}. "
            f"{_eq.get('filing_verified_suppliers')} suppliers filing-verified. "
            f"{str(_eq.get('constraint_read', '')).split(':')[0]}."
        )
    else:
        equip_line = "pending source-backed equipment-bottleneck extraction."

    _rf = verdict.get("forensic_red_flags", {}) or {}
    if _rf.get("issuer_count") is not None:
        _serious = _rf.get("issuers_with_serious_accounting_flag") or []
        _common = _rf.get("most_common_flags") or {}
        _top = ", ".join(f"{k} ({v})" for k, v in list(_common.items())[:4])
        _hr = ", ".join(
            f"{h.get('issuer')} ({h.get('red_flag_score')})"
            for h in (_rf.get("highest_risk_issuers") or [])[:3]
        )
        red_flag_line = (
            f"{len(_serious)}/{_rf.get('issuer_count')} issuers carry a filing-tied SERIOUS "
            f"accounting flag; {_rf.get('filing_verified_present_flags')} present flags filing-verified. "
            f"Most common: {_top}. Highest-risk: {_hr}. {str(_rf.get('red_flag_read', '')).split(':')[0]}."
        )
    else:
        red_flag_line = "pending source-backed red-flag extraction."

    _ud = verdict.get("utilization_debt_service_mismatch", {}) or {}
    if _ud.get("issuer_count") is not None:
        util_line = (
            f"{_ud.get('issuers_with_contracted_coverage')}/{_ud.get('issuer_count')} issuers filed "
            f"enough to compute a contracted-revenue coverage ratio (median "
            f"~{_ud.get('median_contracted_coverage_ratio')}x; "
            f"{_ud.get('issuers_contracted_coverage_below_1')} below 1x); "
            f"{_ud.get('issuers_with_disclosed_utilization')} disclosed a utilization/contracted-capacity "
            f"figure. {str(_ud.get('mismatch_read', '')).split(':')[0]}."
        )
    else:
        util_line = "pending source-backed utilization/debt-service extraction."

    return {
        "demand_line": demand_line,
        "power_line": power_line,
        "holder_line": holder_line,
        "equip_line": equip_line,
        "red_flag_line": red_flag_line,
        "util_line": util_line,
    }


def main() -> None:
    report = build_burry_report()

    out_dir = Path("data/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M")

    json_path = out_dir / f"BURRY_REPORT_EvidenceGated_{ts}.json"
    json_path.write_text(json.dumps(report, indent=2))

    md_path = out_dir / f"BURRY_REPORT_EvidenceGated_{ts}.md"
    verdict = report.get("ai_direct_core_verdict", {})
    _ct = verdict.get("crack_timing", {}) if isinstance(verdict, dict) else {}

    def _bullets(items: Any) -> str:
        return "\n".join(f"- {item}" for item in (items or [])) or "- (none)"

    _lines = _verdict_layer_lines(verdict)
    demand_line = _lines["demand_line"]
    power_line = _lines["power_line"]
    holder_line = _lines["holder_line"]
    equip_line = _lines["equip_line"]
    red_flag_line = _lines["red_flag_line"]
    util_line = _lines["util_line"]

    md_verdict = f"""## The Verdict (Tiered)

**AI-direct core:** `{verdict.get("core_verdict")}` at confidence **{verdict.get("core_verdict_confidence")}**.
**Ecosystem-wide:** `{verdict.get("ecosystem_verdict")}` — {verdict.get("ecosystem_verdict_basis", "")}

The split is deliberate: the financed AI-direct cluster shows source-backed fragility, but it is a
specific named cluster, not a fixed % of the broad metric (which is dominated by non-AI debt), so an
ecosystem-wide bubble call is not supported.

**Cluster-boundary test (is the financed cluster bounded?):** {(
    f"only {len((_cbt := verdict.get('cluster_boundary_test', {}) or {}).get('qualified_financed_ai_infra') or [])}"
    f" of {_cbt.get('candidate_count')} adjacent candidate names qualify as genuine financed AI-infra "
    f"({', '.join(_cbt.get('qualified_financed_ai_infra') or []) or 'none'}); "
    f"{str(_cbt.get('boundary_read', '')).split(':')[0]} — reinforces the scoped (not ecosystem-wide) call."
) if (verdict.get('cluster_boundary_test', {}) or {}).get('candidate_count') is not None
    else 'pending source-backed boundary sweep.'}

**Demand side (hyperscaler/offtaker funding — the bear-case test):** {demand_line}

**Power / ratepayer exposure (the hidden downside leg):** {power_line}

**Ultimate end-holders (who really eats it — SEC ownership filings):** {holder_line}

**Supply-side equipment bottlenecks (can they physically build it — supplier filings):** {equip_line}

**Forensic red flags (per-issuer Burry checklist — SEC filings):** {red_flag_line}

**Utilization vs debt service (deal/entity-level — does contracted revenue cover the obligations?):** {util_line}

**Source-backed fragility facts (primary 10-K/10-Q, adversarially verified):**
{_bullets(verdict.get("source_backed_fragility_facts"))}

**Evidence basis:** the verdict rests mainly on the one fully source-backed leg
({", ".join(verdict.get("evidence_basis", {}).get("source_backed_legs", []))}); these legs are
blocked/illustrative, not yet proof: {"; ".join(verdict.get("evidence_basis", {}).get("blocked_or_illustrative_legs", []))}.

**How large (scoped core):** primary-sourced 11-issuer debt census — cluster total debt
**${round(float((verdict.get("how_large_scoped_core", {}) or {}).get("cluster_total_debt_usd") or 0) / 1e9, 1)}B**
(vs the broader $3.62T materiality metric, which is mostly non-AI debt and not the AI-direct figure).

**When it cracks (from the census maturity schedule):**
{_ct.get("maturity_profile", "")}
- Peak maturity year: **{_ct.get("peak_maturity_year")}** | 2030-2033 share: **{_ct.get("pct_2030_2033")}%** | near-term 2025-2027: **{_ct.get("pct_near_term_2025_2027")}%**
- Near-term refinancing pressure (timing engine): **{_ct.get("near_term_pressure_window")}**

**Named refinancing wall (specific facilities, from the census):** {(
    f"${round((_rw := _ct.get('named_refi_wall', {}) or {}).get('total_dated_debt_usd', 0) / 1e9, 1)}B dated debt; "
    f"peak {_rw.get('peak_maturity_year')} (${round((_rw.get('peak_year_usd') or 0) / 1e9, 1)}B); near-term "
    f"2025-2027 ${round((_rw.get('near_term_2025_2027_usd') or 0) / 1e9, 1)}B ({_rw.get('near_term_pct_of_dated_debt')}%). "
    f"Most-exposed near-term: "
    + ", ".join(f"{x.get('issuer')} (${round((x.get('near_term_maturities_usd') or 0) / 1e9, 2)}B)"
                for x in (_rw.get('near_term_most_exposed_issuers') or [])[:4])
) if (_ct.get('named_refi_wall', {}) or {}).get('total_dated_debt_usd') is not None
    else 'pending source-backed refi-wall synthesis.'}
{_bullets(f"{f.get('issuer')} — {f.get('facility')}: ${round((f.get('principal_usd') or 0) / 1e9, 2)}B due {f.get('maturity_year')}" for f in ((_ct.get('named_refi_wall', {}) or {}).get('near_term_named_facilities') or [])[:6])}

Earlier triggers:
{_bullets(_ct.get("earlier_triggers"))}

Leading indicators:
{_bullets(_ct.get("leading_indicators"))}

**How severely it cracks (forward cash-flow stress — base financials primary-sourced, stress params labeled assumptions):**
{(
    "\n".join(
        f"- **{s.get('scenario')}** (util miss {s.get('utilization_miss_pct')}%, +{s.get('rate_shock_bps')}bp): "
        f"cluster coverage **{s.get('cluster_interest_coverage')}x**, "
        f"{s.get('issuers_breaching')}/{s.get('issuer_count')} issuers breaching "
        f"({s.get('issuers_negative_ebitda')} negative-EBITDA)"
        for s in (_fs.get("by_scenario") or [])
    )
    if (_fs := (_ct.get("forward_scenarios") or {})).get("by_scenario")
    else "- pending source-backed issuer financials."
)}
{(_ct.get("forward_scenarios") or {}).get("severity_read", "")}

**Weakest links in the capital structure:**
{_bullets(verdict.get("weakest_links"))}

**Weakest links ranked by entity (composite of forensic flags + financial fragility — who cracks first, and why):**
{_bullets(f"#{e.get('rank')} {e.get('entity')} (risk {e.get('composite_risk_score')}): {'; '.join(e.get('key_concerns', []))}" for e in (verdict.get("weakest_links_ranked", {}) or {}).get("weakest_links_top", []) or [])}

**Who bears the downside (by disclosed facility recourse):**
{_bullets(f"{k}: ${round(v / 1e9, 1)}B" for k, v in sorted(((verdict.get("who_bears_downside_quantified", {}) or {}).get("by_recourse_class_usd", {}) or {}).items(), key=lambda kv: -kv[1]))}
{(verdict.get("who_bears_downside_quantified", {}) or {}).get("note", "")}

**Who bears the downside (CONTRACT-LEVEL, from the actual credit agreements):** {(
    f"{(_cl := verdict.get('contract_level_recourse', {}) or {}).get('filing_verified_facilities')}/"
    f"{_cl.get('facility_count')} facilities contract-verified; recourse "
    f"{_cl.get('recourse_breakdown_counts')}; {_cl.get('named_borrower_spv_facilities')} named-SPV, "
    f"{_cl.get('bankruptcy_remote_facilities')} bankruptcy-remote, {_cl.get('gpu_collateralized_facilities')} "
    f"GPU-collateralized. {str(_cl.get('who_bears_downside_read', '')).split(':')[0]}."
) if (verdict.get('contract_level_recourse', {}) or {}).get('facility_count') is not None
    else 'pending source-backed contract-structure extraction.'}

**Contagion hubs (counterparties shared across the cluster — where a shock propagates):**
{_bullets(f"{h.get('counterparty')} ({h.get('category')}) — touches {h.get('issuer_count')} issuers: {', '.join(h.get('issuers', []))}" for h in (verdict.get("contagion_hubs", {}) or {}).get("top_contagion_hubs", []) or [])}

**Loss cascades (multi-hop: a shock to the hub → directly-hit issuers + census debt at risk → 2nd-order):**
{_bullets(f"{c.get('origin')} ({'/'.join(c.get('origin_categories', []))}){' [demand/supply]' if c.get('is_demand_or_supply_hub') else ' [infrastructure]'} → {c.get('directly_hit_count')} issuers, ${round((c.get('debt_at_risk_usd') or 0) / 1e9, 1)}B at risk → 2nd-order: {', '.join(s.get('counterparty') for s in (c.get('second_order_counterparties') or [])[:3])}" for c in (verdict.get("contagion_hubs", {}) or {}).get("top_loss_cascades", []) or [])}

**Top actionable risks (ranked, cross-layer synthesis — severity 1-5, each anchored to a sourced number):**
{_bullets(f"#{r.get('rank')} [S{r.get('severity')}/{r.get('source_status')}] {r.get('title')} — {r.get('evidence')} ({r.get('backing_layer')})" for r in (verdict.get("top_actionable_risks", {}) or {}).get("risks", []) or [])}

**Top risks (affirmatively-held premises):**
{_bullets(f"{r.get('premise')} [{r.get('tier')}/{r.get('verdict')}]: {r.get('finding')}" for r in verdict.get("top_risks", []))}

**Open data gaps (NOT counted as fragility support):**
{_bullets(f"{g.get('premise')}: {g.get('finding')}" for g in verdict.get("data_gaps", []))}

**Confidence derivation (transparent):** {json.dumps(verdict.get("confidence_derivation", {}))}

**Bear case (the counterweight, taken seriously):** {verdict.get("bear_case", {}).get("summary", "")} (confidence {verdict.get("bear_case", {}).get("confidence")})

**Caveats:**
{_bullets(verdict.get("caveats"))}
"""

    md = f"""# Evidence-Gated Burry Report - AI/Data Center/Financing Ecosystem

**Generated:** {report["metadata"]["generated_at"]}
**High-confidence final:** {report["metadata"]["high_confidence_final"]}
**Evidence-gated bubble confidence:** {report["executive_summary"]["bubble_confidence"]:.0%}

## Executive Summary
{report["executive_summary"]["overall_assessment"]}

{report["executive_summary"]["coverage_sentence"]}

{_executive_conclusion(verdict)}
{md_verdict}

## Burry's Separation Test (Mismatch Ratios)
**Core principle:** Big aggregate notional is irrelevant without testing the assumptions it rests on.
These ratios quantify the three key mismatches Burry would probe first.

{json.dumps(report.get("burry_separation_test", {}), indent=2)}

**Interpretation guidance (from the ratios above):**
- Cash flow: DSCR at realistic low utilization (e.g. 28%) vs. the higher utilization baked into debt models / payback cases. <<1.0x = cash flow collapse risk even if headline revenue looks fine.
- Physical: % of announced/tracker capacity that has strong corroborating queue (or permit/equipment) linkage. Low % = high stranding / delay risk for the debt sized against that capacity.
- GPU economics: Accounting useful life minus observed secondary/rental market compression. Large positive gap = current depreciation (and thus earnings/cash flow) is understated.
- Debt refi: % of the wall lacking explicit rates. High missing-rate % + near-term maturities = forced equity raises, higher rates, or default when rolled.

If 2+ of these mismatches are large on source-backed data for the AI-direct core, the capital structure is a bubble regardless of headline $T totals.

## Key Metrics
{json.dumps(report["key_metrics"], indent=2)}

## Source Coverage
{json.dumps(report["source_coverage"], indent=2)}

## Source Invariant Audit
{json.dumps(report["source_invariant_audit"], indent=2)}

## Entity Universe
{json.dumps(report["entity_universe_summary"], indent=2)}

## Capital Exposure Graph
{json.dumps(report["capital_exposure_graph"], indent=2)}

## Ownership Graph
{json.dumps(report["ownership_graph"], indent=2)}

## Weak Links
{json.dumps(report["weak_links"], indent=2)}

## Contract Contagion Paths
{json.dumps(report["contract_contagion_paths"], indent=2)}

## Adjudication Queue
{json.dumps(report["review_queue"], indent=2)}

## Materiality Adjudication
{json.dumps(report["materiality_adjudication"], indent=2)}

## Materiality Adjudication Decisions
{json.dumps(report["materiality_adjudication_decisions"], indent=2)}

## Materiality Relevance Linkage
{json.dumps(report["materiality_relevance_linkage"], indent=2)}

## Timing Signals
{json.dumps(report["timing_signals"], indent=2)}

## Physical Capacity Summary
{json.dumps(report["physical_capacity_summary"], indent=2)}

## Physical Execution Summary
{json.dumps(report["physical_execution_summary"], indent=2)}

## Physical Risk Summary
{json.dumps(report["physical_risk_summary"], indent=2)}

## Queue Project Match Summary
{json.dumps(report["queue_project_match_summary"], indent=2)}

## Physical Record Match Summary
{json.dumps(report["physical_record_match_summary"], indent=2)}

## Capital Structure
{json.dumps(report["capital_structure"], indent=2)}

## Compute Economics
{json.dumps(report["compute_economics"], indent=2)}

## Debt-Service Mismatch
{json.dumps(report["debt_service_mismatch"], indent=2)}

## Evidence Quality
{json.dumps(report["evidence_quality"]["summary"], indent=2)}

## Blocked Burry Questions
{json.dumps(report["burry_question_answers"], indent=2)}

{_methodology_appendix(report, verdict)}
See the accompanying JSON for full structured data.
"""
    md_path.write_text(md)

    print("Evidence-gated Burry report delivered:")
    print(f"  JSON: {json_path}")
    print(f"  MD:   {md_path}")
    print(
        "\nEvidence gate status: not high-confidence final; source coverage remains insufficient."
    )


if __name__ == "__main__":
    main()
