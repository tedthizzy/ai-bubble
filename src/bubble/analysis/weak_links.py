"""Weak-link scoring for the AI/data-center forensic report.

The weak-link layer ranks source-backed candidates where capital exposure,
AI/data-center relevance, and physical execution risk create analyst attention
points. It is a triage layer, not a final conclusion engine.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bubble.analysis.debt_service import DebtServiceEntityRisk, analyze_debt_service
from bubble.analysis.physical_risk_summary import build_physical_risk_summary
from bubble.ingestion.capital import load_capital_evidence
from bubble.ingestion.compute.loader import (
    load_compute_economics,
    merge_compute_economics_batches,
)

if TYPE_CHECKING:
    from bubble.models.compute import CapexPaybackCase
    from bubble.models.deal import Deal

CAPITAL_GRAPH_SUMMARY = "capital_exposure_graph_summary.json"
CAPITAL_GRAPH_EDGES = "capital_exposure_edges.csv"


@dataclass(frozen=True)
class WeakLinkCandidate:
    """A ranked weak-link candidate with source-backed evidence references."""

    weak_link_id: str
    category: str
    risk_score: float
    risk_level: str
    entity: str
    counterparty: str
    project_id: str
    project_name: str
    exposure_usd: float
    capacity_mw: float
    queue_requested_mw: float
    evidence_tier: str
    evidence_source_count: int
    relevance_tags: tuple[str, ...]
    risk_drivers: tuple[str, ...]
    source_uris: tuple[str, ...]
    content_hashes: tuple[str, ...]
    human_review_statuses: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WeakLinkSummary:
    """Serializable rollup of weak-link candidates."""

    candidates: int
    capital_candidates: int
    physical_candidates: int
    debt_service_candidates: int
    combined_candidates: int
    high_or_critical_candidates: int
    source_backed_candidates: int
    ai_infra_relevant_capital_edges: int
    direct_ai_keyword_capital_edges: int
    ai_infra_relevant_notional_usd: float
    top_weak_links: list[dict[str, Any]]
    top_capital_weak_links: list[dict[str, Any]]
    top_physical_weak_links: list[dict[str, Any]]
    top_debt_service_weak_links: list[dict[str, Any]]
    top_combined_weak_links: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WeakLinkBatch:
    """Built weak-link artifacts."""

    candidates: list[WeakLinkCandidate]
    summary: WeakLinkSummary


def build_weak_link_batch(
    data_dirs: list[str | Path] | None = None,
    *,
    top_physical_limit: int = 250,
) -> WeakLinkBatch:
    """Build weak-link candidates from existing source-backed artifacts."""

    roots = [Path(root) for root in (data_dirs or ["data"])]
    graph_summary = _load_first_json(roots, Path("graph") / CAPITAL_GRAPH_SUMMARY)
    capital_edges = _load_capital_edges(roots)
    physical_summary = build_physical_risk_summary(
        [str(root) for root in roots],
        top_limit=top_physical_limit,
    ).to_dict()

    candidates: list[WeakLinkCandidate] = []
    capital_candidates = _capital_candidates(capital_edges)
    physical_candidates = _physical_candidates(physical_summary)
    debt_service_candidates = _debt_service_candidates(roots)
    combined_candidates = _combined_candidates(capital_candidates, physical_candidates)
    candidates.extend(capital_candidates)
    candidates.extend(physical_candidates)
    candidates.extend(debt_service_candidates)
    candidates.extend(combined_candidates)
    candidates.sort(key=lambda candidate: candidate.risk_score, reverse=True)

    summary = WeakLinkSummary(
        candidates=len(candidates),
        capital_candidates=len(capital_candidates),
        physical_candidates=len(physical_candidates),
        debt_service_candidates=len(debt_service_candidates),
        combined_candidates=len(combined_candidates),
        high_or_critical_candidates=sum(
            candidate.risk_level in {"critical", "high"} for candidate in candidates
        ),
        source_backed_candidates=sum(
            candidate.evidence_source_count > 0 for candidate in candidates
        ),
        ai_infra_relevant_capital_edges=int(graph_summary.get("ai_infra_relevant_edges", 0) or 0),
        direct_ai_keyword_capital_edges=int(graph_summary.get("direct_ai_keyword_edges", 0) or 0),
        ai_infra_relevant_notional_usd=float(
            graph_summary.get("ai_infra_relevant_notional_usd", 0) or 0
        ),
        top_weak_links=[candidate.to_dict() for candidate in candidates[:25]],
        top_capital_weak_links=[
            candidate.to_dict()
            for candidate in candidates
            if candidate.category == "capital_exposure"
        ][:15],
        top_physical_weak_links=[
            candidate.to_dict()
            for candidate in candidates
            if candidate.category == "physical_execution"
        ][:15],
        top_debt_service_weak_links=[
            candidate.to_dict()
            for candidate in candidates
            if candidate.category == "debt_service_stress"
        ][:15],
        top_combined_weak_links=[
            candidate.to_dict()
            for candidate in candidates
            if candidate.category == "combined_capital_physical"
        ][:15],
    )
    return WeakLinkBatch(candidates=candidates, summary=summary)


def write_weak_link_batch(batch: WeakLinkBatch, output_dir: str | Path) -> dict[str, str]:
    """Write weak-link candidates and summary to disk."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    candidates_path = out / "weak_link_candidates.csv"
    summary_path = out / "weak_link_summary.json"
    _write_csv(candidates_path, [candidate.to_dict() for candidate in batch.candidates])
    summary_path.write_text(json.dumps(batch.summary.to_dict(), indent=2))
    return {"candidates_csv": str(candidates_path), "summary_json": str(summary_path)}


def _capital_candidates(edges: list[dict[str, Any]]) -> list[WeakLinkCandidate]:
    candidates: list[WeakLinkCandidate] = []
    for edge in edges:
        relevance_tags = tuple(_json_list(edge.get("relevance_tags")))
        if not relevance_tags:
            continue
        exposure = _float(edge.get("notional_usd"))
        score = _capital_score(edge, relevance_tags, exposure)
        risk_drivers = ["AI/data-center relevant capital exposure"]
        if any(tag.startswith("direct:") for tag in relevance_tags):
            risk_drivers.append("Direct AI/data-center/compute keyword evidence")
        elif relevance_tags:
            risk_drivers.append(
                "Watchlist entity exposure; AI-specific linkage needs corroboration"
            )
        if edge.get("deal_type") in {"debt_facility", "bond", "lease", "guarantee"}:
            risk_drivers.append(f"Debt-like deal type: {edge.get('deal_type')}")
        if exposure >= 5_000_000_000:
            risk_drivers.append("Large source-backed notional edge")
        review_statuses = tuple(_json_list(edge.get("human_review_statuses")))
        if "pending" in review_statuses:
            risk_drivers.append("Pending LLM adjudication")

        source_name = str(edge.get("source_name") or "")
        target_name = str(edge.get("target_name") or "")
        candidates.append(
            WeakLinkCandidate(
                weak_link_id=_weak_link_id(
                    "capital", source_name, target_name, edge.get("deal_type")
                ),
                category="capital_exposure",
                risk_score=score,
                risk_level=_risk_level(score),
                entity=source_name,
                counterparty=target_name,
                project_id="",
                project_name="",
                exposure_usd=exposure,
                capacity_mw=0.0,
                queue_requested_mw=0.0,
                evidence_tier="source_backed_pending_review"
                if "pending" in review_statuses
                else "source_backed_reviewed",
                evidence_source_count=len(set(_json_list(edge.get("source_uris")))),
                relevance_tags=relevance_tags,
                risk_drivers=tuple(risk_drivers),
                source_uris=tuple(_json_list(edge.get("source_uris"))[:10]),
                content_hashes=tuple(_json_list(edge.get("content_hashes"))[:10]),
                human_review_statuses=review_statuses,
            )
        )
    return candidates


def _physical_candidates(physical_summary: dict[str, Any]) -> list[WeakLinkCandidate]:
    rows = physical_summary.get("top_source_backed_risk_projects") or []
    candidates: list[WeakLinkCandidate] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        physical_score = _float(row.get("score"))
        capacity = _float(row.get("capacity_mw"))
        queue = _float(row.get("queue_requested_mw"))
        score = min(
            1.0,
            physical_score * 0.7
            + min(max(capacity, queue) / 1_000, 1.0) * 0.15
            + min(_int(row.get("evidence_source_count")) / 5, 1.0) * 0.15,
        )
        blockers = [str(blocker) for blocker in row.get("blockers", []) if blocker]
        project_name = str(row.get("asset_name") or "")
        owner = str(row.get("owner") or "")
        candidates.append(
            WeakLinkCandidate(
                weak_link_id=_weak_link_id("physical", row.get("project_id"), project_name),
                category="physical_execution",
                risk_score=round(score, 4),
                risk_level=_risk_level(score),
                entity=owner,
                counterparty="",
                project_id=str(row.get("project_id") or ""),
                project_name=project_name,
                exposure_usd=0.0,
                capacity_mw=capacity,
                queue_requested_mw=queue,
                evidence_tier=str(row.get("evidence_tier") or ""),
                evidence_source_count=_int(row.get("evidence_source_count")),
                relevance_tags=("direct:data_center",),
                risk_drivers=tuple(blockers[:5]),
                source_uris=tuple(str(uri) for uri in row.get("supporting_evidence", [])[:10]),
                content_hashes=(),
                human_review_statuses=("pending",),
            )
        )
    return candidates


def _debt_service_candidates(roots: list[Path]) -> list[WeakLinkCandidate]:
    deals = _load_report_deals(roots)
    if not deals:
        return []
    payback_cases = _load_payback_cases(roots)
    metrics = analyze_debt_service(deals, payback_cases)
    return [_debt_service_candidate(risk) for risk in metrics.top_entity_debt_service_risks[:25]]


def _debt_service_candidate(risk: DebtServiceEntityRisk) -> WeakLinkCandidate:
    score = _debt_service_score(risk)
    source_uris = _unique(
        [
            *(item.source_uri for item in risk.top_obligations),
            *(item.source_uri for item in risk.top_coverage_gaps),
        ]
    )
    content_hashes = _unique(
        [
            *(item.content_hash for item in risk.top_obligations),
            *(item.content_hash for item in risk.top_coverage_gaps),
        ]
    )
    statuses = tuple(
        sorted(
            {
                item.human_review_status or "pending"
                for item in [*risk.top_obligations, *risk.top_coverage_gaps]
            }
        )
        or {"pending"}
    )
    drivers = _debt_service_risk_drivers(risk)
    return WeakLinkCandidate(
        weak_link_id=_weak_link_id(
            "debt_service",
            risk.entity,
            risk.peak_maturity_quarter,
            risk.distinct_notional_usd,
        ),
        category="debt_service_stress",
        risk_score=score,
        risk_level=_risk_level(score),
        entity=risk.entity,
        counterparty="",
        project_id="",
        project_name="",
        exposure_usd=round(risk.distinct_notional_usd, 2),
        capacity_mw=0.0,
        queue_requested_mw=0.0,
        evidence_tier="source_backed_pending_review"
        if "pending" in statuses
        else "source_backed_reviewed",
        evidence_source_count=len(source_uris),
        relevance_tags=("direct:debt_service",),
        risk_drivers=tuple(drivers),
        source_uris=tuple(source_uris[:10]),
        content_hashes=tuple(content_hashes[:10]),
        human_review_statuses=statuses,
    )


def _debt_service_score(risk: DebtServiceEntityRisk) -> float:
    score = (
        min(
            risk.maturity_wall_measured_annual_interest_usd_2024_2030 / 1_000_000_000,
            1.0,
        )
        * 0.25
    )
    score += min(risk.maturity_wall_notional_usd_2024_2030 / 25_000_000_000, 1.0) * 0.25
    score += (
        min(
            risk.maturity_wall_missing_rate_notional_usd_2024_2030 / 10_000_000_000,
            1.0,
        )
        * 0.2
    )
    score += min(risk.notional_missing_maturity_usd / 10_000_000_000, 1.0) * 0.15
    score += min(risk.measured_annual_interest_usd / 1_000_000_000, 1.0) * 0.1
    if _is_near_term_peak(risk.peak_maturity_quarter):
        score += 0.05
    return round(min(score, 1.0), 4)


def _debt_service_risk_drivers(risk: DebtServiceEntityRisk) -> list[str]:
    drivers = ["Entity-level source-backed debt-service stress"]
    if risk.measured_annual_interest_usd:
        drivers.append(
            f"Measured annual interest/debt-service proxy ${risk.measured_annual_interest_usd:,.0f}"
        )
    if risk.maturity_wall_notional_usd_2024_2030:
        drivers.append(f"2024-2030 maturity wall ${risk.maturity_wall_notional_usd_2024_2030:,.0f}")
    if risk.maturity_wall_missing_rate_notional_usd_2024_2030:
        drivers.append(
            "Missing-rate maturity wall "
            f"${risk.maturity_wall_missing_rate_notional_usd_2024_2030:,.0f}"
        )
    if risk.notional_missing_maturity_usd:
        drivers.append(f"Missing maturity notional ${risk.notional_missing_maturity_usd:,.0f}")
    if risk.peak_maturity_quarter:
        drivers.append(f"Peak maturity quarter {risk.peak_maturity_quarter}")
    drivers.extend(risk.review_priority_reasons[:5])
    return drivers


def _combined_candidates(
    capital_candidates: list[WeakLinkCandidate],
    physical_candidates: list[WeakLinkCandidate],
) -> list[WeakLinkCandidate]:
    capital_by_entity: dict[str, list[WeakLinkCandidate]] = {}
    for candidate in capital_candidates:
        for name in (candidate.entity, candidate.counterparty):
            key = _match_key(name)
            if key:
                capital_by_entity.setdefault(key, []).append(candidate)

    combined: list[WeakLinkCandidate] = []
    for physical in physical_candidates:
        keys = {_match_key(physical.entity), _match_key(physical.project_name)}
        keys.discard("")
        matched = []
        for key in keys:
            matched.extend(capital_by_entity.get(key, []))
        for capital in sorted(matched, key=lambda item: item.risk_score, reverse=True)[:3]:
            score = min(1.0, capital.risk_score * 0.55 + physical.risk_score * 0.45)
            combined.append(
                WeakLinkCandidate(
                    weak_link_id=_weak_link_id(
                        "combined",
                        capital.entity,
                        capital.counterparty,
                        physical.project_id,
                    ),
                    category="combined_capital_physical",
                    risk_score=round(score, 4),
                    risk_level=_risk_level(score),
                    entity=capital.entity or physical.entity,
                    counterparty=capital.counterparty,
                    project_id=physical.project_id,
                    project_name=physical.project_name,
                    exposure_usd=capital.exposure_usd,
                    capacity_mw=physical.capacity_mw,
                    queue_requested_mw=physical.queue_requested_mw,
                    evidence_tier=f"{capital.evidence_tier}+{physical.evidence_tier}",
                    evidence_source_count=(
                        capital.evidence_source_count + physical.evidence_source_count
                    ),
                    relevance_tags=tuple(
                        sorted(set(capital.relevance_tags + physical.relevance_tags))
                    ),
                    risk_drivers=tuple(
                        list(capital.risk_drivers[:3]) + list(physical.risk_drivers[:3])
                    ),
                    source_uris=tuple(
                        list(capital.source_uris[:5]) + list(physical.source_uris[:5])
                    ),
                    content_hashes=capital.content_hashes[:5],
                    human_review_statuses=tuple(
                        sorted(set(capital.human_review_statuses + physical.human_review_statuses))
                    ),
                )
            )
    return combined


def _capital_score(edge: dict[str, Any], relevance_tags: tuple[str, ...], exposure: float) -> float:
    score = min(exposure / 20_000_000_000, 1.0) * 0.45
    if any(tag.startswith("direct:") for tag in relevance_tags):
        score += 0.25
    elif relevance_tags:
        score += 0.05
    if edge.get("deal_type") in {"debt_facility", "bond", "lease", "guarantee"}:
        score += 0.2
    if "pending" in _json_list(edge.get("human_review_statuses")):
        score += 0.05
    return round(min(score, 1.0), 4)


def _risk_level(score: float) -> str:
    if score >= 0.8:
        return "critical"
    if score >= 0.6:
        return "high"
    if score >= 0.35:
        return "medium"
    return "watch"


def _load_capital_edges(roots: list[Path]) -> list[dict[str, Any]]:
    for root in roots:
        path = root / "graph" / CAPITAL_GRAPH_EDGES
        if path.exists():
            with path.open(newline="") as f:
                return [dict(row) for row in csv.DictReader(f)]
    return []


def _load_report_deals(roots: list[Path]) -> list[Deal]:
    deals: list[Deal] = []
    seen: set[str] = set()
    for root in roots:
        for directory in [root / "capital", root / "edgar_acquisition"]:
            deals_csv = directory / "deals.csv"
            if not deals_csv.exists() or deals_csv.stat().st_size == 0:
                continue
            batch = load_capital_evidence(directory)
            for deal in batch.deals:
                key = deal.source_deal_id or f"{deal.provenance.source_uri}:{deal.title}"
                if key in seen:
                    continue
                seen.add(key)
                deals.append(deal)
    return deals


def _load_payback_cases(roots: list[Path]) -> list[CapexPaybackCase]:
    batches = []
    for root in roots:
        compute_dir = root / "compute"
        if compute_dir.exists():
            batches.append(load_compute_economics(compute_dir))
    if not batches:
        return []
    return merge_compute_economics_batches(batches).payback_cases


def _load_first_json(roots: list[Path], relative_path: Path) -> dict[str, Any]:
    for root in roots:
        path = root / relative_path
        if path.exists():
            loaded = json.loads(path.read_text())
            if isinstance(loaded, dict):
                return loaded
    return {}


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


def _int(value: Any) -> int:
    return int(_float(value))


def _is_near_term_peak(quarter: str | None) -> bool:
    if not quarter:
        return False
    match = re.fullmatch(r"(\d{4})-Q[1-4]", quarter)
    return bool(match and int(match.group(1)) <= 2027)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _weak_link_id(*parts: Any) -> str:
    raw = "|".join(str(part) for part in parts)
    return "weak-link:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def _match_key(name: str) -> str:
    tokens = re.sub(r"[^a-z0-9]+", " ", name.lower()).split()
    ignored = {
        "co",
        "company",
        "corp",
        "corporation",
        "data",
        "center",
        "centre",
        "inc",
        "llc",
        "ltd",
        "the",
    }
    tokens = [token for token in tokens if token not in ignored]
    return " ".join(tokens[:4])
