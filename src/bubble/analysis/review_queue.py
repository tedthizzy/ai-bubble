"""Source-backed LLM adjudication queue for high-impact forensic claims.

The queue is a prioritization artifact: it does not approve facts or create new
facts. It points analysts to the exact source-backed rows that block higher
confidence conclusions.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from bubble.analysis.capital_exposure_graph import (
    DIRECT_AI_INFRA_PATTERNS,
    WATCHLIST_ENTITY_PATTERNS,
)

CAPITAL_REVIEW_THRESHOLD_USD = 1_000_000_000
CAPITAL_CRITICAL_THRESHOLD_USD = 25_000_000_000
CAPITAL_HIGH_THRESHOLD_USD = 5_000_000_000

DEBT_LIKE_DEAL_TYPES = {
    "debt_facility",
    "bond",
    "lease",
    "preferred_equity",
    "guarantee",
}

REVIEWED_STATUSES = {"approved", "overridden", "rejected"}
PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "watch": 3}


@dataclass(frozen=True)
class ReviewQueueItem:
    """One source-backed row requiring analyst review."""

    review_id: str
    review_group_id: str
    priority: str
    category: str
    subcategory: str
    ecosystem_relevance: str
    relevance_tags: tuple[str, ...]
    entity: str
    counterparty: str
    project_id: str
    project_name: str
    deal_id: str
    source_row_id: str
    notional_amount_usd: float
    exposure_usd: float
    capacity_mw: float
    risk_score: float
    reason: str
    recommended_action: str
    source_uri: str
    source_uris: tuple[str, ...]
    content_hash: str
    content_hashes: tuple[str, ...]
    page_or_section: str
    human_review_status: str
    source_confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReviewQueueSummary:
    """Serializable rollup for the adjudication queue."""

    items: int
    critical_items: int
    high_items: int
    medium_items: int
    watch_items: int
    source_backed_items: int
    pending_items: int
    categories: dict[str, int]
    subcategories: dict[str, int]
    ecosystem_relevance: dict[str, int]
    ai_infra_relevant_items: int
    pending_notional_amount_usd: float
    pending_capital_notional_amount_usd: float
    pending_capital_distinct_group_count: int
    pending_capital_distinct_notional_amount_usd: float
    pending_capital_duplicate_notional_amount_usd: float
    pending_contract_tranche_items: int
    pending_contract_tranche_notional_amount_usd: float
    pending_contagion_path_items: int
    pending_contagion_path_exposure_usd: float
    pending_ai_infra_relevant_capital_notional_amount_usd: float
    pending_ai_infra_relevant_capital_distinct_notional_amount_usd: float
    pending_compute_claim_amount_usd: float
    pending_exposure_usd: float
    pending_capacity_mw: float
    top_items: list[dict[str, Any]]
    top_distinct_capital_items: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReviewQueueBatch:
    """Built adjudication queue artifacts."""

    items: list[ReviewQueueItem]
    summary: ReviewQueueSummary


def build_review_queue(
    data_dirs: list[str | Path] | None = None,
    *,
    capital_review_threshold_usd: float = CAPITAL_REVIEW_THRESHOLD_USD,
) -> ReviewQueueBatch:
    """Build a prioritized LLM adjudication queue from source-backed artifacts."""

    roots = [Path(root) for root in (data_dirs or ["data"])]
    capital_relevance = _capital_relevance_index(roots)
    items: list[ReviewQueueItem] = []
    items.extend(
        _capital_review_items(
            roots,
            threshold_usd=capital_review_threshold_usd,
            capital_relevance=capital_relevance,
        )
    )
    items.extend(_contract_tranche_review_items(roots, capital_relevance=capital_relevance))
    items.extend(_weak_link_review_items(roots))
    items.extend(_contagion_path_review_items(roots))
    items.extend(_physical_match_review_items(roots))
    items.extend(_compute_review_items(roots))

    deduped = _dedupe_items(items)
    deduped.sort(key=_sort_key)
    summary = _summary(deduped)
    return ReviewQueueBatch(items=deduped, summary=summary)


def write_review_queue(batch: ReviewQueueBatch, output_dir: str | Path) -> dict[str, str]:
    """Write the adjudication queue CSV and summary JSON."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    queue_path = out / "review_queue.csv"
    summary_path = out / "review_queue_summary.json"
    _write_csv(queue_path, [item.to_dict() for item in batch.items])
    summary_path.write_text(json.dumps(batch.summary.to_dict(), indent=2))
    return {"queue_csv": str(queue_path), "summary_json": str(summary_path)}


def _capital_review_items(
    roots: list[Path],
    *,
    threshold_usd: float,
    capital_relevance: dict[str, tuple[str, ...]],
) -> list[ReviewQueueItem]:
    items: list[ReviewQueueItem] = []
    seen_deals: set[str] = set()
    for row in _read_rows(
        roots, [Path("edgar_acquisition") / "deals.csv", Path("capital") / "deals.csv"]
    ):
        deal_id = _field(row, "deal_id")
        if deal_id and deal_id in seen_deals:
            continue
        if deal_id:
            seen_deals.add(deal_id)
        deal_type = _field(row, "deal_type")
        notional = _float(row.get("notional_amount_usd"))
        status = _field(row, "human_review_status") or "pending"
        if _is_reviewed_status(status):
            continue
        if deal_type not in DEBT_LIKE_DEAL_TYPES:
            continue
        if notional < threshold_usd:
            continue
        key_terms = _json_dict(row.get("key_terms"))
        reasons = [
            f"pending adjudication status: {status}",
            f"debt-like deal type: {deal_type}",
            f"notional ${notional:,.0f}",
        ]
        context_kind = str(key_terms.get("notional_context_kind") or "").strip()
        extraction_method = str(key_terms.get("extraction_method") or "").strip()
        if context_kind:
            reasons.append(f"notional context: {context_kind}")
        if key_terms.get("requires_llm_adjudication") or key_terms.get("requires_human_review"):
            reasons.append("source extraction marked requires LLM adjudication")
        if extraction_method:
            reasons.append(f"extraction method: {extraction_method}")

        source_uri = _field(row, "source_uri")
        content_hash = _field(row, "content_hash")
        relevance_tags = _capital_relevance_tags(row, capital_relevance)
        ecosystem_relevance = _ecosystem_relevance("capital", relevance_tags)
        items.append(
            ReviewQueueItem(
                review_id=_review_id("capital_notional", deal_id, source_uri, content_hash),
                review_group_id=_capital_review_group_id(
                    row,
                    notional=notional,
                    context_kind=context_kind,
                ),
                priority=_capital_priority(notional),
                category="capital",
                subcategory="high_notional_debt_like_candidate",
                ecosystem_relevance=ecosystem_relevance,
                relevance_tags=relevance_tags,
                entity=_field(row, "primary_party"),
                counterparty=_counterparty_from_row(row),
                project_id="",
                project_name="",
                deal_id=deal_id,
                source_row_id=deal_id,
                notional_amount_usd=round(notional, 2),
                exposure_usd=0.0,
                capacity_mw=0.0,
                risk_score=0.0,
                reason=_reason(reasons),
                recommended_action=(
                    "Confirm notional context, maturity, parties, counterparty roles, "
                    "and whether the row is a duplicate or aggregate obligation."
                ),
                source_uri=source_uri,
                source_uris=(source_uri,) if source_uri else (),
                content_hash=content_hash,
                content_hashes=(content_hash,) if content_hash else (),
                page_or_section=_field(row, "page_or_section"),
                human_review_status=status,
                source_confidence=_float(row.get("source_confidence") or row.get("confidence")),
            )
        )
    return items


def _contract_tranche_review_items(
    roots: list[Path],
    *,
    capital_relevance: dict[str, tuple[str, ...]],
) -> list[ReviewQueueItem]:
    items: list[ReviewQueueItem] = []
    seen: set[tuple[str, str, str, str]] = set()
    deal_rows = _deal_rows_by_id(roots)
    for row in _read_rows(
        roots, [Path("edgar_acquisition") / "tranches.csv", Path("capital") / "tranches.csv"]
    ):
        deal_id = _field(row, "deal_id")
        deal_row = deal_rows.get(deal_id, {})
        tranche_id = _field(row, "tranche_id") or _field(row, "name")
        source_uri = _field(row, "source_uri")
        content_hash = _field(row, "content_hash")
        key = (deal_id, tranche_id, source_uri, content_hash)
        if key in seen:
            continue
        seen.add(key)
        status = _field(row, "human_review_status") or "pending"
        if _is_reviewed_status(status):
            continue
        notional = _float(row.get("notional_usd"))
        if notional < CAPITAL_REVIEW_THRESHOLD_USD:
            continue
        collateral = _field(row, "collateral_description")
        guarantors = _field(row, "guarantors")
        counterparty = guarantors or _counterparty_from_row(deal_row)
        maturity = _field(row, "maturity")
        interest_rate = _field(row, "interest_rate")
        relevance_tags = _contract_tranche_relevance_tags(
            row,
            capital_relevance,
            deal_row=deal_row,
        )
        items.append(
            ReviewQueueItem(
                review_id=_review_id(
                    "contract_tranche",
                    deal_id,
                    tranche_id,
                    source_uri,
                    content_hash,
                ),
                review_group_id=_review_id(
                    "contract_tranche_group",
                    deal_id,
                    tranche_id,
                    f"{notional:.2f}",
                    maturity,
                ),
                priority=_capital_priority(notional),
                category="contract",
                subcategory="contract_tranche_terms",
                ecosystem_relevance=_ecosystem_relevance("contract", relevance_tags),
                relevance_tags=relevance_tags,
                entity=_field(deal_row, "primary_party") or deal_id,
                counterparty=counterparty,
                project_id="",
                project_name="",
                deal_id=deal_id,
                source_row_id=f"{deal_id}:{tranche_id}",
                notional_amount_usd=round(notional, 2),
                exposure_usd=0.0,
                capacity_mw=0.0,
                risk_score=0.0,
                reason=_reason(
                    [
                        "pending contract tranche review",
                        f"tranche: {_field(row, 'name')}" if _field(row, "name") else "",
                        f"notional ${notional:,.0f}",
                        f"maturity {maturity}" if maturity else "",
                        f"interest rate {interest_rate}" if interest_rate else "",
                        "collateral terms present" if collateral else "",
                        f"guarantors: {guarantors}" if guarantors else "",
                    ]
                ),
                recommended_action=(
                    "Confirm tranche notional, maturity, rate, seniority, collateral package, "
                    "guarantee scope, recourse, and whether this tranche duplicates an aggregate "
                    "deal-level notional."
                ),
                source_uri=source_uri,
                source_uris=(source_uri,) if source_uri else (),
                content_hash=content_hash,
                content_hashes=(content_hash,) if content_hash else (),
                page_or_section=_field(row, "page_or_section"),
                human_review_status=status,
                source_confidence=_float(row.get("source_confidence") or row.get("confidence")),
            )
        )
    return items


def _weak_link_review_items(roots: list[Path]) -> list[ReviewQueueItem]:
    rows = _read_rows(roots, [Path("reports") / "weak_link_candidates.csv"])
    items: list[ReviewQueueItem] = []
    for row in rows:
        risk_level = _field(row, "risk_level")
        statuses = _json_list(row.get("human_review_statuses"))
        if statuses and all(_is_reviewed_status(status) for status in statuses):
            continue
        exposure = _float(row.get("exposure_usd"))
        capacity = max(_float(row.get("capacity_mw")), _float(row.get("queue_requested_mw")))
        if risk_level not in {"critical", "high"} and exposure < 5_000_000_000 and capacity < 500:
            continue
        source_uris = tuple(_json_list(row.get("source_uris")))
        content_hashes = tuple(_json_list(row.get("content_hashes")))
        drivers = _json_list(row.get("risk_drivers"))
        weak_link_id = _field(row, "weak_link_id")
        relevance_tags = tuple(_json_list(row.get("relevance_tags")))
        ecosystem_relevance = _ecosystem_relevance(_field(row, "category"), relevance_tags)
        items.append(
            ReviewQueueItem(
                review_id=_review_id(
                    "weak_link", weak_link_id, source_uris[:1], content_hashes[:1]
                ),
                review_group_id=_review_id("weak_link_group", weak_link_id),
                priority=risk_level if risk_level in PRIORITY_ORDER else "medium",
                category="weak_link",
                subcategory=_field(row, "category"),
                ecosystem_relevance=ecosystem_relevance,
                relevance_tags=relevance_tags,
                entity=_field(row, "entity"),
                counterparty=_field(row, "counterparty"),
                project_id=_field(row, "project_id"),
                project_name=_field(row, "project_name"),
                deal_id="",
                source_row_id=weak_link_id,
                notional_amount_usd=0.0,
                exposure_usd=round(exposure, 2),
                capacity_mw=round(capacity, 2),
                risk_score=_float(row.get("risk_score")),
                reason=_reason([f"weak-link risk level: {risk_level}", *drivers[:4]]),
                recommended_action=(
                    "Open the linked source rows and confirm the capital/physical linkage, "
                    "exposure amount, and risk drivers before relying on this candidate."
                ),
                source_uri=source_uris[0] if source_uris else "",
                source_uris=source_uris,
                content_hash=content_hashes[0] if content_hashes else "",
                content_hashes=content_hashes,
                page_or_section="weak_link_candidates.csv",
                human_review_status=";".join(statuses) if statuses else "pending",
                source_confidence=0.0,
            )
        )
    return items


def _contagion_path_review_items(roots: list[Path]) -> list[ReviewQueueItem]:
    rows = _read_rows(roots, [Path("reports") / "contract_contagion_paths.csv"])
    items: list[ReviewQueueItem] = []
    for row in rows:
        statuses = tuple(_json_list(row.get("human_review_statuses")))
        if statuses and all(_is_reviewed_status(status) for status in statuses):
            continue
        notional = _float(row.get("notional_usd"))
        risk_level = _field(row, "risk_level")
        if risk_level not in {"critical", "high"} and notional < 5_000_000_000:
            continue
        relevance_tags = tuple(_json_list(row.get("relevance_tags")))
        source_uris = tuple(_json_list(row.get("source_uris")))
        content_hashes = tuple(_json_list(row.get("content_hashes")))
        path_id = _field(row, "path_id")
        path_type = _field(row, "path_type")
        items.append(
            ReviewQueueItem(
                review_id=_review_id(
                    "contagion_path", path_id, source_uris[:1], content_hashes[:1]
                ),
                review_group_id=_review_id(
                    "contagion_path_group",
                    _field(row, "deal_id"),
                    _field(row, "tranche_id"),
                    _field(row, "start_entity_name"),
                    _field(row, "contract_counterparty_name"),
                    _field(row, "ownership_path_node_ids"),
                ),
                priority=risk_level if risk_level in PRIORITY_ORDER else "medium",
                category="contagion",
                subcategory=path_type or "contract_contagion_path",
                ecosystem_relevance=_ecosystem_relevance("contagion", relevance_tags),
                relevance_tags=relevance_tags,
                entity=_field(row, "start_entity_name"),
                counterparty=_field(row, "contract_counterparty_name"),
                project_id="",
                project_name="",
                deal_id=_field(row, "deal_id"),
                source_row_id=path_id,
                notional_amount_usd=0.0,
                exposure_usd=round(notional, 2),
                capacity_mw=0.0,
                risk_score=_float(row.get("risk_score")),
                reason=_field(row, "reason"),
                recommended_action=(
                    "Confirm the contract edge, ownership/legal-name match, parent path, "
                    "guarantee/collateral scope, and whether the path is economically "
                    "contagious before using it in downside-bearer conclusions."
                ),
                source_uri=source_uris[0] if source_uris else "",
                source_uris=source_uris,
                content_hash=content_hashes[0] if content_hashes else "",
                content_hashes=content_hashes,
                page_or_section="contract_contagion_paths.csv",
                human_review_status=";".join(statuses) if statuses else "pending",
                source_confidence=0.0,
            )
        )
    return items


def _physical_match_review_items(roots: list[Path]) -> list[ReviewQueueItem]:
    configs = [
        (
            Path("physical") / "queue_project_matches.csv",
            "queue_project_match",
            "queue-to-project match",
            "matched_project_owner",
            "queue_customer",
            "matched_project_id",
            "matched_project_name",
            "queue_capacity_mw",
        ),
        (
            Path("physical") / "permit_project_matches.csv",
            "permit_project_match",
            "permit-to-project match",
            "matched_project_owner",
            "facility_name",
            "matched_project_id",
            "matched_project_name",
            "",
        ),
        (
            Path("physical") / "equipment_project_matches.csv",
            "equipment_project_match",
            "equipment-to-project match",
            "matched_project_owner",
            "plant_name",
            "matched_project_id",
            "matched_project_name",
            "capacity_mw",
        ),
    ]
    items: list[ReviewQueueItem] = []
    for (
        relative_path,
        subcategory,
        label,
        entity_field,
        counterparty_field,
        project_id_field,
        project_name_field,
        capacity_field,
    ) in configs:
        for row in _read_rows(roots, [relative_path]):
            status = _field(row, "human_review_status") or "pending"
            if _is_reviewed_status(status):
                continue
            match_status = _field(row, "match_status")
            if match_status not in {"strong_match", "candidate_match"}:
                continue
            confidence = _float(row.get("match_confidence"))
            capacity = _float(row.get(capacity_field)) if capacity_field else 0.0
            source_uri = _field(row, "source_uri")
            content_hash = _field(row, "content_hash")
            reasons = [
                f"pending {label}",
                f"match status: {match_status}",
                f"match confidence: {confidence:.2f}" if confidence else "",
                _field(row, "match_reasons"),
            ]
            items.append(
                ReviewQueueItem(
                    review_id=_review_id(subcategory, _field(row, "match_id"), source_uri),
                    review_group_id=_review_id(
                        "physical_group",
                        subcategory,
                        _field(row, project_id_field),
                        _field(row, "match_id"),
                    ),
                    priority=_physical_priority(match_status, confidence, capacity),
                    category="physical",
                    subcategory=subcategory,
                    ecosystem_relevance="physical_execution",
                    relevance_tags=("direct:data_center",),
                    entity=_field(row, entity_field),
                    counterparty=_field(row, counterparty_field),
                    project_id=_field(row, project_id_field),
                    project_name=_field(row, project_name_field),
                    deal_id="",
                    source_row_id=_field(row, "match_id"),
                    notional_amount_usd=0.0,
                    exposure_usd=0.0,
                    capacity_mw=round(capacity, 2),
                    risk_score=round(confidence, 4),
                    reason=_reason(reasons),
                    recommended_action=(
                        "Confirm that name, owner/customer, location, and capacity evidence "
                        "refer to the same physical project before treating the match as linked."
                    ),
                    source_uri=source_uri,
                    source_uris=(source_uri,) if source_uri else (),
                    content_hash=content_hash,
                    content_hashes=(content_hash,) if content_hash else (),
                    page_or_section=_field(row, "page_or_section"),
                    human_review_status=status,
                    source_confidence=confidence,
                )
            )
    return items


def _compute_review_items(roots: list[Path]) -> list[ReviewQueueItem]:
    items: list[ReviewQueueItem] = []
    items.extend(_eps_review_items(roots))
    items.extend(_tam_review_items(roots))
    items.extend(_payback_review_items(roots))
    items.extend(_chip_supply_review_items(roots))
    items.extend(_depreciation_policy_review_items(roots))
    items.extend(_gpu_price_review_items(roots))
    return items


def _eps_review_items(roots: list[Path]) -> list[ReviewQueueItem]:
    items: list[ReviewQueueItem] = []
    for row in _read_rows(roots, [Path("compute") / "eps_depreciation_impacts.csv"]):
        if _is_reviewed_status(_field(row, "human_review_status")):
            continue
        disclosed_depreciation = _float(row.get("disclosed_depreciation_usd"))
        gpu_capex = _float(row.get("gpu_capex_estimate_usd"))
        eps_impact = _float(row.get("disclosed_eps_impact_usd"))
        if max(disclosed_depreciation, gpu_capex) < 1_000_000_000 and eps_impact == 0:
            continue
        reasons = [
            "pending EPS/depreciation impact review",
            f"disclosed depreciation ${disclosed_depreciation:,.0f}"
            if disclosed_depreciation
            else "",
            f"GPU capex estimate ${gpu_capex:,.0f}" if gpu_capex else "",
            f"disclosed EPS impact {eps_impact:g}" if eps_impact else "",
        ]
        items.append(
            _compute_item(
                row,
                priority="high"
                if max(disclosed_depreciation, gpu_capex) >= 1_000_000_000
                else "medium",
                subcategory="eps_depreciation_impact",
                source_row_id=_field(row, "impact_id"),
                amount=disclosed_depreciation or gpu_capex,
                reason=_reason(reasons),
                action=(
                    "Confirm disclosed depreciation, EPS impact, useful-life assumption, "
                    "and whether accelerated economic depreciation should be modeled."
                ),
            )
        )
    return items


def _tam_review_items(roots: list[Path]) -> list[ReviewQueueItem]:
    items: list[ReviewQueueItem] = []
    for row in _read_rows(roots, [Path("compute") / "tam_claims.csv"]):
        if _is_reviewed_status(_field(row, "human_review_status")):
            continue
        tam = _float(row.get("stated_tam_usd"))
        implied_capture = _float(row.get("implied_revenue_capture_assumption_pct"))
        if tam < 100_000_000_000 and implied_capture < 20:
            continue
        priority = "high" if tam >= 1_000_000_000_000 or implied_capture >= 20 else "medium"
        items.append(
            _compute_item(
                row,
                priority=priority,
                subcategory="tam_reality_check",
                source_row_id=_field(row, "claim_id"),
                amount=tam,
                reason=_reason(
                    [
                        "pending TAM sanity-check review",
                        f"stated TAM ${tam:,.0f}",
                        (
                            f"implied revenue capture {implied_capture:.1f}%"
                            if implied_capture
                            else ""
                        ),
                    ]
                ),
                action=(
                    "Compare the stated TAM with source-backed realized revenue, pricing, "
                    "utilization, and deliverable compute capacity."
                ),
            )
        )
    return items


def _payback_review_items(roots: list[Path]) -> list[ReviewQueueItem]:
    items: list[ReviewQueueItem] = []
    for row in _read_rows(roots, [Path("compute") / "capex_payback_cases.csv"]):
        if _is_reviewed_status(_field(row, "human_review_status")):
            continue
        capex = _float(row.get("capex_usd"))
        revenue = _float(row.get("annual_revenue_run_rate_usd"))
        gross_margin = _float(row.get("gross_margin_pct"))
        if capex < 500_000_000 and revenue and gross_margin:
            continue
        priority = "high" if capex >= 5_000_000_000 else "medium"
        missing = []
        if not revenue:
            missing.append("annual revenue run rate")
        if not gross_margin:
            missing.append("gross margin")
        items.append(
            _compute_item(
                row,
                priority=priority,
                subcategory="capex_payback_case",
                source_row_id=_field(row, "case_id"),
                amount=capex,
                reason=_reason(
                    [
                        "pending capex payback review",
                        f"capex ${capex:,.0f}",
                        f"missing {', '.join(missing)}" if missing else "",
                    ]
                ),
                action=(
                    "Confirm capex, contracted revenue, run-rate revenue, utilization, "
                    "gross margin, power cost, and debt service before using payback math."
                ),
            )
        )
    return items


def _chip_supply_review_items(roots: list[Path]) -> list[ReviewQueueItem]:
    items: list[ReviewQueueItem] = []
    for row in _read_rows(roots, [Path("compute") / "chip_supply_observations.csv"]):
        if _is_reviewed_status(_field(row, "human_review_status")):
            continue
        announced_gpus = _float(row.get("announced_gpu_count"))
        delivered_gpus = _float(row.get("delivered_gpu_count"))
        announced_mw = _float(row.get("announced_mw"))
        delivery_gap = announced_gpus - delivered_gpus if announced_gpus else 0.0
        if announced_gpus < 10_000 and announced_mw < 100 and delivery_gap <= 0:
            continue
        priority = "high" if announced_mw >= 250 or delivery_gap >= 10_000 else "medium"
        items.append(
            _compute_item(
                row,
                priority=priority,
                subcategory="chip_supply_observation",
                source_row_id=_field(row, "observation_id"),
                amount=0.0,
                capacity=announced_mw,
                reason=_reason(
                    [
                        "pending chip supply review",
                        f"announced GPUs {announced_gpus:,.0f}" if announced_gpus else "",
                        f"delivery gap {delivery_gap:,.0f}" if delivery_gap > 0 else "",
                        f"announced MW {announced_mw:,.0f}" if announced_mw else "",
                    ]
                ),
                action=(
                    "Confirm announced versus delivered GPU count, delivery window, supplier, "
                    "and MW conversion before using supply-gap claims."
                ),
            )
        )
    return items


def _depreciation_policy_review_items(roots: list[Path]) -> list[ReviewQueueItem]:
    items: list[ReviewQueueItem] = []
    for row in _read_rows(roots, [Path("compute") / "depreciation_policies.csv"]):
        if _is_reviewed_status(_field(row, "human_review_status")):
            continue
        useful_life = _float(row.get("accounting_useful_life_years"))
        asset_class = _field(row, "asset_class").lower()
        if useful_life < 5 or not any(
            term in asset_class for term in ("gpu", "server", "equipment")
        ):
            continue
        items.append(
            _compute_item(
                row,
                priority="medium",
                subcategory="gpu_depreciation_policy",
                source_row_id=_field(row, "policy_id"),
                amount=0.0,
                reason=_reason(
                    [
                        "pending compute depreciation policy review",
                        f"asset class: {_field(row, 'asset_class')}",
                        f"accounting useful life {useful_life:g} years",
                    ]
                ),
                action=(
                    "Confirm asset class coverage and compare accounting useful life with "
                    "observed economic life for the relevant GPU/server generation."
                ),
            )
        )
    return items


def _gpu_price_review_items(roots: list[Path]) -> list[ReviewQueueItem]:
    frontier_generations = {"a100", "h100", "h200", "b100", "b200", "gb200", "gb300", "blackwell"}
    items: list[ReviewQueueItem] = []
    for row in _read_rows(roots, [Path("compute") / "gpu_price_observations.csv"]):
        if _is_reviewed_status(_field(row, "human_review_status")):
            continue
        generation = _field(row, "gpu_generation").lower()
        if generation not in frontier_generations:
            continue
        price = _float(row.get("observed_secondary_price_usd"))
        rental = _float(row.get("observed_cloud_rental_rate_usd_per_hour"))
        if not price and not rental:
            continue
        items.append(
            _compute_item(
                row,
                priority="watch",
                subcategory="gpu_price_observation",
                source_row_id=_field(row, "observation_id"),
                amount=price,
                reason=_reason(
                    [
                        "pending GPU price/rental observation review",
                        f"GPU generation: {_field(row, 'gpu_generation')}",
                        f"secondary price ${price:,.0f}" if price else "",
                        f"rental ${rental:g}/hour" if rental else "",
                    ]
                ),
                action=(
                    "Confirm SKU comparability, region, provider, contract term, and whether "
                    "the observation is comparable to the depreciation time series."
                ),
            )
        )
    return items


def _compute_item(
    row: dict[str, str],
    *,
    priority: str,
    subcategory: str,
    source_row_id: str,
    amount: float,
    reason: str,
    action: str,
    capacity: float = 0.0,
) -> ReviewQueueItem:
    source_uri = _field(row, "source_uri")
    content_hash = _field(row, "content_hash")
    return ReviewQueueItem(
        review_id=_review_id("compute", subcategory, source_row_id, source_uri, content_hash),
        review_group_id=_review_id("compute_group", subcategory, source_row_id),
        priority=priority,
        category="compute",
        subcategory=subcategory,
        ecosystem_relevance="compute_economics",
        relevance_tags=("direct:compute",),
        entity=_field(row, "entity") or _field(row, "provider_or_marketplace"),
        counterparty=_field(row, "supplier") or _field(row, "provider_or_marketplace"),
        project_id=_field(row, "project_or_cluster_id"),
        project_name=_field(row, "project_or_cluster_id"),
        deal_id="",
        source_row_id=source_row_id,
        notional_amount_usd=round(amount, 2),
        exposure_usd=0.0,
        capacity_mw=round(capacity, 2),
        risk_score=0.0,
        reason=reason,
        recommended_action=action,
        source_uri=source_uri,
        source_uris=(source_uri,) if source_uri else (),
        content_hash=content_hash,
        content_hashes=(content_hash,) if content_hash else (),
        page_or_section=_field(row, "page_or_section"),
        human_review_status=_field(row, "human_review_status") or "pending",
        source_confidence=_float(row.get("source_confidence") or row.get("confidence")),
    )


def _dedupe_items(items: list[ReviewQueueItem]) -> list[ReviewQueueItem]:
    best_by_key: dict[str, ReviewQueueItem] = {}
    for item in items:
        key = "|".join(
            [
                item.category,
                item.subcategory,
                item.deal_id,
                item.source_row_id,
                item.source_uri,
                item.content_hash,
            ]
        )
        current = best_by_key.get(key)
        if current is None or _sort_key(item) < _sort_key(current):
            best_by_key[key] = item
    return list(best_by_key.values())


def _summary(items: list[ReviewQueueItem]) -> ReviewQueueSummary:
    priorities = Counter(item.priority for item in items)
    categories = Counter(item.category for item in items)
    subcategories = Counter(item.subcategory for item in items)
    ecosystem_relevance = Counter(item.ecosystem_relevance for item in items)
    distinct_capital_items = _distinct_capital_items(items)
    relevant_capital_items = [item for item in items if _is_ai_infra_relevant_item(item)]
    relevant_distinct_capital_items = [
        item for item in distinct_capital_items if _is_ai_infra_relevant_item(item)
    ]
    pending_capital_notional = sum(
        item.notional_amount_usd
        for item in items
        if item.category == "capital" and not _is_reviewed_status(item.human_review_status)
    )
    pending_capital_distinct_notional = sum(
        item.notional_amount_usd
        for item in distinct_capital_items
        if not _is_reviewed_status(item.human_review_status)
    )
    pending_contract_tranche_items = [
        item
        for item in items
        if item.category == "contract"
        and item.subcategory == "contract_tranche_terms"
        and not _is_reviewed_status(item.human_review_status)
    ]
    pending_contagion_path_items = [
        item
        for item in items
        if item.category == "contagion" and not _is_reviewed_status(item.human_review_status)
    ]
    return ReviewQueueSummary(
        items=len(items),
        critical_items=priorities.get("critical", 0),
        high_items=priorities.get("high", 0),
        medium_items=priorities.get("medium", 0),
        watch_items=priorities.get("watch", 0),
        source_backed_items=sum(1 for item in items if item.source_uri),
        pending_items=sum(1 for item in items if not _is_reviewed_status(item.human_review_status)),
        categories=dict(sorted(categories.items())),
        subcategories=dict(sorted(subcategories.items())),
        ecosystem_relevance=dict(sorted(ecosystem_relevance.items())),
        ai_infra_relevant_items=sum(_is_ai_infra_relevant_item(item) for item in items),
        pending_notional_amount_usd=round(
            sum(
                item.notional_amount_usd
                for item in items
                if not _is_reviewed_status(item.human_review_status)
            ),
            2,
        ),
        pending_capital_notional_amount_usd=round(pending_capital_notional, 2),
        pending_capital_distinct_group_count=len(distinct_capital_items),
        pending_capital_distinct_notional_amount_usd=round(
            pending_capital_distinct_notional,
            2,
        ),
        pending_capital_duplicate_notional_amount_usd=round(
            max(0.0, pending_capital_notional - pending_capital_distinct_notional),
            2,
        ),
        pending_contract_tranche_items=len(pending_contract_tranche_items),
        pending_contract_tranche_notional_amount_usd=round(
            sum(item.notional_amount_usd for item in pending_contract_tranche_items),
            2,
        ),
        pending_contagion_path_items=len(pending_contagion_path_items),
        pending_contagion_path_exposure_usd=round(
            sum(item.exposure_usd for item in pending_contagion_path_items),
            2,
        ),
        pending_ai_infra_relevant_capital_notional_amount_usd=round(
            sum(
                item.notional_amount_usd
                for item in relevant_capital_items
                if not _is_reviewed_status(item.human_review_status)
            ),
            2,
        ),
        pending_ai_infra_relevant_capital_distinct_notional_amount_usd=round(
            sum(
                item.notional_amount_usd
                for item in relevant_distinct_capital_items
                if not _is_reviewed_status(item.human_review_status)
            ),
            2,
        ),
        pending_compute_claim_amount_usd=round(
            sum(
                item.notional_amount_usd
                for item in items
                if item.category == "compute" and not _is_reviewed_status(item.human_review_status)
            ),
            2,
        ),
        pending_exposure_usd=round(
            sum(
                item.exposure_usd
                for item in items
                if not _is_reviewed_status(item.human_review_status)
            ),
            2,
        ),
        pending_capacity_mw=round(
            sum(
                item.capacity_mw
                for item in items
                if not _is_reviewed_status(item.human_review_status)
            ),
            2,
        ),
        top_items=[item.to_dict() for item in items[:25]],
        top_distinct_capital_items=[item.to_dict() for item in distinct_capital_items[:25]],
    )


def _read_rows(roots: list[Path], relative_paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for root in roots:
        for relative_path in relative_paths:
            path = root / relative_path
            if not path.exists() or path.stat().st_size == 0:
                continue
            with path.open(newline="") as f:
                reader = csv.DictReader(f)
                rows.extend(
                    {
                        str(key): (value or "").strip()
                        for key, value in row.items()
                        if key is not None
                    }
                    for row in reader
                )
    return rows


def _deal_rows_by_id(roots: list[Path]) -> dict[str, dict[str, str]]:
    rows = _read_rows(
        roots, [Path("edgar_acquisition") / "deals.csv", Path("capital") / "deals.csv"]
    )
    return {_field(row, "deal_id"): row for row in rows if _field(row, "deal_id")}


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    fieldnames = list(rows[0])
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(value) for key, value in row.items()})


def _csv_value(value: Any) -> str | int | float:
    if isinstance(value, tuple | list | dict):
        return json.dumps(value)
    if value is None:
        return ""
    if isinstance(value, bool | int | float | str):
        return value
    return str(value)


def _sort_key(item: ReviewQueueItem) -> tuple[int, int, float, float, float, str]:
    return (
        PRIORITY_ORDER.get(item.priority, 9),
        -_relevance_rank(item.ecosystem_relevance),
        -item.notional_amount_usd,
        -item.exposure_usd,
        -max(item.capacity_mw, item.risk_score),
        item.review_id,
    )


def _capital_priority(notional: float) -> str:
    if notional >= CAPITAL_CRITICAL_THRESHOLD_USD:
        return "critical"
    if notional >= CAPITAL_HIGH_THRESHOLD_USD:
        return "high"
    return "medium"


def _capital_relevance_index(roots: list[Path]) -> dict[str, tuple[str, ...]]:
    tags_by_key: dict[str, set[str]] = {}
    rows = _read_rows(roots, [Path("graph") / "capital_exposure_edges.csv"])
    for row in rows:
        tags = set(_json_list(row.get("relevance_tags")))
        if not tags:
            continue
        for key in [
            *_json_list(row.get("source_deal_ids")),
            *_json_list(row.get("source_uris")),
            *_json_list(row.get("content_hashes")),
        ]:
            if key:
                tags_by_key.setdefault(key, set()).update(tags)
    return {key: tuple(sorted(tags)) for key, tags in tags_by_key.items()}


def _capital_relevance_tags(
    row: dict[str, str],
    capital_relevance: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    tags: set[str] = set()
    for key in (_field(row, "deal_id"), _field(row, "source_uri"), _field(row, "content_hash")):
        tags.update(capital_relevance.get(key, ()))
    search_text = " ".join(
        [
            _field(row, "primary_party"),
            _counterparty_from_row(row),
            _field(row, "title"),
            _field(row, "page_or_section"),
            _field(row, "source_uri"),
            row.get("key_terms") or "",
        ]
    )
    tags.update(
        f"watchlist:{name}"
        for name, pattern in WATCHLIST_ENTITY_PATTERNS.items()
        if pattern.search(search_text)
    )
    tags.update(
        f"direct:{name}"
        for name, pattern in DIRECT_AI_INFRA_PATTERNS.items()
        if pattern.search(search_text)
    )
    return tuple(sorted(tags))


def _contract_tranche_relevance_tags(
    row: dict[str, str],
    capital_relevance: dict[str, tuple[str, ...]],
    *,
    deal_row: dict[str, str],
) -> tuple[str, ...]:
    tags: set[str] = set()
    for key in (
        _field(row, "deal_id"),
        _field(row, "source_uri"),
        _field(row, "content_hash"),
    ):
        tags.update(capital_relevance.get(key, ()))
    search_text = " ".join(
        [
            _field(row, "deal_id"),
            _field(row, "tranche_id"),
            _field(row, "name"),
            _field(row, "collateral_description"),
            _field(row, "guarantors"),
            _field(row, "source_uri"),
            _field(deal_row, "primary_party"),
            _counterparty_from_row(deal_row),
            _field(deal_row, "title"),
            _field(deal_row, "key_terms"),
        ]
    )
    tags.update(
        f"watchlist:{name}"
        for name, pattern in WATCHLIST_ENTITY_PATTERNS.items()
        if pattern.search(search_text)
    )
    tags.update(
        f"direct:{name}"
        for name, pattern in DIRECT_AI_INFRA_PATTERNS.items()
        if pattern.search(search_text)
    )
    return tuple(sorted(tags))


def _capital_review_group_id(
    row: dict[str, str],
    *,
    notional: float,
    context_kind: str,
) -> str:
    key_terms = _json_dict(row.get("key_terms"))
    primary_party = _normalize_group_part(_field(row, "primary_party"))
    counterparty = _normalize_group_part(_counterparty_from_row(row))
    deal_type = _field(row, "deal_type")
    maturity = _field(row, "maturity_date")
    if context_kind.startswith("aggregate_"):
        return _review_id(
            "capital_group",
            "aggregate",
            primary_party,
            deal_type,
            context_kind,
            f"{notional:.2f}",
        )
    accession = str(key_terms.get("accession_number") or "").strip()
    if accession:
        return _review_id(
            "capital_group",
            primary_party,
            counterparty,
            deal_type,
            context_kind,
            f"{notional:.2f}",
            maturity,
            accession,
        )
    return _review_id(
        "capital_group",
        primary_party,
        counterparty,
        deal_type,
        context_kind,
        f"{notional:.2f}",
        maturity,
    )


def _ecosystem_relevance(category: str, relevance_tags: tuple[str, ...]) -> str:
    if any(tag.startswith("direct:") for tag in relevance_tags):
        return "direct_ai_infra"
    if any(tag.startswith("watchlist:") for tag in relevance_tags):
        return "watchlist_entity"
    if "physical" in category:
        return "physical_execution"
    if "compute" in category:
        return "compute_economics"
    return "not_tagged"


def _distinct_capital_items(items: list[ReviewQueueItem]) -> list[ReviewQueueItem]:
    by_group: dict[str, ReviewQueueItem] = {}
    for item in items:
        if item.category != "capital" or _is_reviewed_status(item.human_review_status):
            continue
        current = by_group.get(item.review_group_id)
        if current is None or _sort_key(item) < _sort_key(current):
            by_group[item.review_group_id] = item
    distinct = list(by_group.values())
    distinct.sort(key=_sort_key)
    return distinct


def _is_ai_infra_relevant_item(item: ReviewQueueItem) -> bool:
    return item.ecosystem_relevance in {
        "direct_ai_infra",
        "watchlist_entity",
        "physical_execution",
        "compute_economics",
    }


def _relevance_rank(relevance: str) -> int:
    return {
        "direct_ai_infra": 4,
        "watchlist_entity": 3,
        "physical_execution": 3,
        "compute_economics": 3,
        "not_tagged": 0,
    }.get(relevance, 0)


def _normalize_group_part(value: str) -> str:
    return " ".join(value.lower().split())


def _physical_priority(match_status: str, confidence: float, capacity_mw: float) -> str:
    if capacity_mw >= 1_000:
        return "critical"
    if match_status == "strong_match" and (confidence >= 0.9 or capacity_mw >= 250):
        return "high"
    return "medium"


def _counterparty_from_row(row: dict[str, str]) -> str:
    roles = _json_dict(row.get("counterparty_roles"))
    for preferred_role in ("lender", "financier", "lessor", "guarantor", "buyer", "offtaker"):
        entities = roles.get(preferred_role)
        if isinstance(entities, list) and entities:
            return str(entities[0])
    parties = [part.strip() for part in _field(row, "parties").split("|") if part.strip()]
    primary = _field(row, "primary_party")
    for party in parties:
        if party != primary:
            return party
    return ""


def _reason(parts: list[str]) -> str:
    return "; ".join(part for part in parts if part)


def _field(row: dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value or not isinstance(value, str):
        return {}
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _json_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if not value:
        return []
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        if isinstance(loaded, list):
            return [str(item) for item in loaded]
    return []


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(str(value).replace(",", "").replace("$", ""))
    except ValueError:
        return 0.0


def _is_reviewed_status(status: str) -> bool:
    statuses = [part.strip().lower() for part in status.replace(",", ";").split(";") if part]
    return bool(statuses) and all(part in REVIEWED_STATUSES for part in statuses)


def _review_id(*parts: Any) -> str:
    raw = "|".join(str(part) for part in parts)
    return "review:" + hashlib.sha256(raw.encode()).hexdigest()[:16]
