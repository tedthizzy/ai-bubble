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

from bubble.analysis.compute_economics import (
    ComputeEconomicsBatch,
    analyze_compute_economics,
    empty_compute_economics_batch,
)
from bubble.analysis.debt_service import analyze_debt_service
from bubble.analysis.ecosystem_scope import scope_deals
from bubble.analysis.evidence import EvidenceGate, SemanticEvidenceBucket, classify_claim_semantics
from bubble.analysis.physical_capacity import build_physical_capacity_summary
from bubble.analysis.physical_risk_summary import build_physical_risk_summary
from bubble.analysis.source_coverage import build_source_coverage_report
from bubble.ingestion.capital import (
    CapitalEvidenceBatch,
    analyze_capital_evidence,
    load_capital_evidence,
)
from bubble.ingestion.compute.loader import load_compute_economics, merge_compute_economics_batches
from bubble.models.base import HumanReviewStatus, Provenance, SourceType
from bubble.quality.relevance_linkage import summarize_relevance_linkage

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
    capital_exposure_graph_summary: dict[str, Any],
    contract_contagion_summary: dict[str, Any],
    materiality_adjudication_decision_summary: dict[str, Any] | None = None,
    materiality_relevance_summary: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Audit high-impact scalar values surfaced directly in Burry answers."""

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
        "review_queue.pending_ai_infra_relevant_capital_distinct_notional",
        "AI-infra-relevant distinct pending capital review-queue notional",
        review_queue_summary.get(
            "pending_ai_infra_relevant_capital_distinct_notional_amount_usd"
        ),
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
                "measured_rate_notional_usd",
                "distinct_missing_rate_notional_usd",
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
        "debt_service.distinct_missing_rate_notional",
        "Distinct debt-like notional still missing explicit rate evidence",
        debt_service_metrics_dict.get("distinct_missing_rate_notional_usd"),
        debt_evidence,
    )
    add(
        "debt_service.maturity_wall_notional_2024_2030",
        "Debt-service maturity-wall notional through 2030",
        debt_service_metrics_dict.get("maturity_wall_notional_usd_2024_2030"),
        debt_evidence,
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
    ):
        rows = capital_exposure_graph_summary.get(key, [])
        if not isinstance(rows, list):
            continue
        for index, row in enumerate(rows[:10]):
            if not isinstance(row, dict):
                continue
            row_id = str(row.get("component_id") or row.get("node_id") or index)
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
    compute_artifact = artifact_provenance(
        source_uri="local:compute_economics_metrics",
        page_or_section="compute-economics analyzer rollup",
        payload={
            key: compute_metrics_dict.get(key)
            for key in (
                "total_gpu_capex_usd",
                "compute_asset_count",
                "gpu_price_observation_count",
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


def build_burry_report(data_dirs: list[str] | None = None) -> dict[str, Any]:
    resolved_data_dirs = data_dirs or ["data"]
    coverage = build_source_coverage_report(resolved_data_dirs)
    physical_capacity = build_physical_capacity_summary(resolved_data_dirs)
    physical_risk = build_physical_risk_summary(resolved_data_dirs)
    queue_match_summary = load_queue_project_match_summary(resolved_data_dirs)
    physical_record_match_summary = load_physical_record_match_summary(resolved_data_dirs)
    entity_universe_summary = load_entity_universe_summary(resolved_data_dirs)
    capital_exposure_graph_summary = load_capital_exposure_graph_summary(resolved_data_dirs)
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
    coverage_dict = coverage.to_dict()
    physical_capacity_dict = physical_capacity.to_dict()
    physical_risk_dict = physical_risk.to_dict()
    capital_metrics_dict = capital_metrics.to_dict()
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
        "contract_contagion_ai_infra_relevant_notional_usd": contract_contagion_summary.get(
            "ai_infra_relevant_notional_usd",
            0,
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
        "compute_eps_impact_count": compute_metrics.eps_impact_count,
        "compute_chip_supply_observation_count": compute_metrics.chip_supply_observation_count,
        "compute_total_gpu_capex_usd": compute_metrics.total_gpu_capex_usd,
        "compute_gpu_depreciation_red_flag_count": (
            compute_metrics.gpu_depreciation_red_flag_count
        ),
        "compute_tam_red_flag_count": compute_metrics.tam_red_flag_count,
        "compute_payback_red_flag_count": compute_metrics.payback_red_flag_count,
        "compute_eps_red_flag_count": compute_metrics.eps_red_flag_count,
        "compute_chip_supply_red_flag_count": compute_metrics.chip_supply_red_flag_count,
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
                capital_exposure_graph_summary=capital_exposure_graph_summary,
                contract_contagion_summary=contract_contagion_summary,
                materiality_adjudication_decision_summary=(
                    materiality_adjudication_decision_summary
                ),
                materiality_relevance_summary=materiality_relevance,
            )
        },
    )
    evidence_summary = summarize_evidence_audit_dicts(evidence_audits)
    capped_bubble_confidence = round(
        min(0.82, evidence_summary["max_permitted_report_confidence"]),
        4,
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
        "physical_risk_summary": physical_risk_dict,
        "queue_project_match_summary": queue_match_summary,
        "physical_record_match_summary": physical_record_match_summary,
        "capital_structure": capital_metrics_dict,
        "compute_economics": compute_metrics_dict,
        "debt_service_mismatch": debt_service_metrics_dict,
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
                "answer": "Blocked. The source corpus is not yet broad enough for a defensible binary conclusion.",
                "confidence": capped_bubble_confidence,
                "required_next_evidence": [
                    "Source-backed leverage and maturity schedules",
                    "Project-level power/permit/queue records",
                    "Lease/PPA/take-or-pay contract coverage",
                    "Ownership and guarantee paths",
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
                "current_tam_claims": compute_metrics.tam_claim_count,
                "current_payback_cases": compute_metrics.payback_case_count,
                "current_eps_impacts": compute_metrics.eps_impact_count,
                "current_chip_supply_observations": (compute_metrics.chip_supply_observation_count),
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
            "Ingest ISO queue records for ERCOT, PJM, MISO, CAISO, NYISO, and SPP.",
            "Ingest state PUC/EPA/local permit records for top project geographies.",
            "Ingest ownership registry records and project tracker rows.",
            "Load extracted deal candidates through the capital evidence pipeline after review.",
            "Load compute economics evidence for GPU depreciation, rental rates, TAM claims, capex payback, EPS depreciation impact, and chip supply.",
            "Acquire contract-level coupon, interest-rate, amortization, rent schedule, utilization, and contracted-revenue evidence for debt-service coverage.",
        ],
    }
    return report


def main() -> None:
    report = build_burry_report()

    out_dir = Path("data/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M")

    json_path = out_dir / f"BURRY_REPORT_EvidenceGated_{ts}.json"
    json_path.write_text(json.dumps(report, indent=2))

    md_path = out_dir / f"BURRY_REPORT_EvidenceGated_{ts}.md"
    md = f"""# Evidence-Gated Burry Report - AI/Data Center/Financing Ecosystem

**Generated:** {report["metadata"]["generated_at"]}
**High-confidence final:** {report["metadata"]["high_confidence_final"]}
**Evidence-gated bubble confidence:** {report["executive_summary"]["bubble_confidence"]:.0%}

## Executive Summary
{report["executive_summary"]["overall_assessment"]}

{report["executive_summary"]["coverage_sentence"]}

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
