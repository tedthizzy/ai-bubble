"""Materiality-first LLM adjudication packet builder.

This layer turns the broad source-backed adjudication queue into the next
operational worklist: top material blockers with enough source context for automated LLM
adjudication. It does not approve facts by itself.
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import re
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock
from typing import Any
from xml.etree import ElementTree

REVIEWED_STATUSES = {"approved", "overridden", "rejected"}
PRIORITY_RANK = {"critical": 4, "high": 3, "medium": 2, "watch": 1}
AI_RELEVANCE_RANK = {
    "direct_ai_infra": 4,
    "watchlist_entity": 3,
    "physical_execution": 3,
    "compute_economics": 3,
    "not_tagged": 0,
}
_TEXT_CACHE: dict[str, str] = {}
_TEXT_CACHE_LOCK = Lock()
_BINARY_TEXT_SKIP_SUFFIXES = {
    ".bin",
    ".zip",
    ".gz",
    ".bz2",
    ".xz",
    ".pdf",
    ".parquet",
    ".feather",
    ".orc",
    ".avro",
}


@dataclass(frozen=True)
class EvidenceSnippet:
    """Short source excerpt attached to an adjudication packet."""

    source_uri: str
    content_hash: str
    local_path: str
    document_id: str
    accession_number: str
    snippet: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MaterialityAdjudicationPacket:
    """One top material blocker packaged for LLM adjudication."""

    packet_id: str
    rank: int
    review_id: str
    review_group_id: str
    priority: str
    category: str
    subcategory: str
    ecosystem_relevance: str
    entity: str
    counterparty: str
    project_id: str
    project_name: str
    deal_id: str
    source_row_id: str
    materiality_score: float
    exposure_basis_usd: float
    notional_amount_usd: float
    exposure_usd: float
    capacity_mw: float
    risk_score: float
    adjudication_status: str
    adjudication_questions: tuple[str, ...]
    required_decision_fields: tuple[str, ...]
    llm_adjudication_prompt: str
    reason: str
    recommended_action: str
    source_uri: str
    source_uris: tuple[str, ...]
    content_hash: str
    content_hashes: tuple[str, ...]
    page_or_section: str
    evidence_snippets: tuple[EvidenceSnippet, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence_snippets"] = [snippet.to_dict() for snippet in self.evidence_snippets]
        return data


@dataclass(frozen=True)
class MaterialityAdjudicationSummary:
    """Serializable rollup of LLM adjudication packets."""

    packets: int
    source_backed_packets: int
    packets_with_local_evidence_snippets: int
    ai_infra_relevant_packets: int
    categories: dict[str, int]
    subcategories: dict[str, int]
    ecosystem_relevance: dict[str, int]
    total_exposure_basis_usd: float
    top_exposure_basis_usd: float
    top_packets: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MaterialityAdjudicationBatch:
    """Built adjudication packet artifact."""

    packets: list[MaterialityAdjudicationPacket]
    summary: MaterialityAdjudicationSummary


def build_materiality_adjudication_packets(
    data_dirs: list[str | Path] | None = None,
    *,
    limit: int | None = 100,
    snippets_per_packet: int = 2,
    snippet_chars: int = 1_200,
    max_workers: int = 32,
) -> MaterialityAdjudicationBatch:
    """Build materiality-ranked adjudication packets from queue rows."""

    roots = [Path(root) for root in (data_dirs or ["data"])]
    review_rows = _read_rows(roots, [Path("reports") / "review_queue.csv"])
    artifact_index = _artifact_index(roots)
    candidates = [
        row
        for row in review_rows
        if not _is_reviewed_status(row.get("human_review_status", ""))
        and (_field(row, "source_uri") or _json_list(row.get("source_uris")))
    ]

    best_by_group: dict[str, dict[str, str]] = {}
    for row in candidates:
        group_id = _field(row, "review_group_id") or _field(row, "review_id")
        current = best_by_group.get(group_id)
        if current is None or _materiality_sort_key(row) < _materiality_sort_key(current):
            best_by_group[group_id] = row

    ranked_rows = sorted(best_by_group.values(), key=_materiality_sort_key)
    if limit is not None and limit > 0:
        ranked_rows = ranked_rows[:limit]
    indexed_rows = list(enumerate(ranked_rows, start=1))
    if len(indexed_rows) <= 1 or max_workers <= 1:
        packets = [
            _packet_from_row(
                row,
                rank=rank,
                artifact_index=artifact_index,
                snippets_per_packet=snippets_per_packet,
                snippet_chars=snippet_chars,
            )
            for rank, row in indexed_rows
        ]
    else:
        worker_count = min(max(1, max_workers), len(indexed_rows))
        packets_by_rank: dict[int, MaterialityAdjudicationPacket] = {}
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(
                    _packet_from_row,
                    row,
                    rank=rank,
                    artifact_index=artifact_index,
                    snippets_per_packet=snippets_per_packet,
                    snippet_chars=snippet_chars,
                ): rank
                for rank, row in indexed_rows
            }
            for future in as_completed(futures):
                packet = future.result()
                packets_by_rank[packet.rank] = packet
        packets = [packets_by_rank[rank] for rank, _ in indexed_rows]
    summary = _summary(packets)
    return MaterialityAdjudicationBatch(packets=packets, summary=summary)


def write_materiality_adjudication_packets(
    batch: MaterialityAdjudicationBatch,
    output_dir: str | Path,
) -> dict[str, str]:
    """Write materiality-ranked adjudication packets and summary."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    packets_path = out / "materiality_adjudication_packets.csv"
    summary_path = out / "materiality_adjudication_summary.json"
    _write_csv(packets_path, [packet.to_dict() for packet in batch.packets])
    summary_path.write_text(json.dumps(batch.summary.to_dict(), indent=2))
    return {"packets_csv": str(packets_path), "summary_json": str(summary_path)}


def _packet_from_row(
    row: dict[str, str],
    *,
    rank: int,
    artifact_index: dict[str, dict[str, str]],
    snippets_per_packet: int,
    snippet_chars: int,
) -> MaterialityAdjudicationPacket:
    source_uris = tuple(_source_uris(row))
    content_hashes = tuple(_content_hashes(row))
    snippets = tuple(
        _evidence_snippets(
            row,
            artifact_index=artifact_index,
            snippets_per_packet=snippets_per_packet,
            snippet_chars=snippet_chars,
        )
    )
    questions = tuple(_adjudication_questions(row))
    required_fields = tuple(_required_decision_fields(row))
    prompt = _llm_prompt(row, questions, snippets)
    exposure_basis = _exposure_basis_usd(row)
    packet_id = _packet_id(
        _field(row, "review_id"),
        _field(row, "review_group_id"),
        source_uris,
        content_hashes,
    )
    return MaterialityAdjudicationPacket(
        packet_id=packet_id,
        rank=rank,
        review_id=_field(row, "review_id"),
        review_group_id=_field(row, "review_group_id"),
        priority=_field(row, "priority"),
        category=_field(row, "category"),
        subcategory=_field(row, "subcategory"),
        ecosystem_relevance=_field(row, "ecosystem_relevance"),
        entity=_field(row, "entity"),
        counterparty=_field(row, "counterparty"),
        project_id=_field(row, "project_id"),
        project_name=_field(row, "project_name"),
        deal_id=_field(row, "deal_id"),
        source_row_id=_field(row, "source_row_id"),
        materiality_score=round(_materiality_score(row), 4),
        exposure_basis_usd=round(exposure_basis, 2),
        notional_amount_usd=round(_float(row.get("notional_amount_usd")), 2),
        exposure_usd=round(_float(row.get("exposure_usd")), 2),
        capacity_mw=round(_float(row.get("capacity_mw")), 2),
        risk_score=round(_float(row.get("risk_score")), 4),
        adjudication_status="pending_llm_adjudication",
        adjudication_questions=questions,
        required_decision_fields=required_fields,
        llm_adjudication_prompt=prompt,
        reason=_field(row, "reason"),
        recommended_action=_field(row, "recommended_action"),
        source_uri=source_uris[0] if source_uris else "",
        source_uris=source_uris,
        content_hash=content_hashes[0] if content_hashes else "",
        content_hashes=content_hashes,
        page_or_section=_field(row, "page_or_section"),
        evidence_snippets=snippets,
    )


def _adjudication_questions(row: dict[str, str]) -> list[str]:
    category = _field(row, "category")
    subcategory = _field(row, "subcategory")
    question_sets = {
        "capital": [
            "Is this a real committed financing or lease obligation, rather than shelf capacity, boilerplate, or aggregate disclosure?",
            "What is the correct economic notional, and is this row a duplicate of another disclosure group?",
            "Who are the borrower/issuer, lender/lessor/noteholder, guarantor, and ultimate risk bearer?",
            "Is there direct AI/data-center linkage, or only broad watchlist-entity relevance?",
            "What maturity, recourse, collateral, and covenant terms must be extracted before using this in leverage metrics?",
        ],
        "contract": [
            "Are tranche notional, maturity, rate, collateral, and guarantor fields explicitly supported by the source text?",
            "Does the tranche create senior, secured, non-recourse, or SPV-layered downside risk?",
            "Which parties bear first-loss, residual, guarantee, or collateral enforcement risk?",
        ],
        "contagion": [
            "Is the contract entity to ownership-graph match legally valid, or only a name collision?",
            "Does the guarantee, collateral, tranche, or non-recourse term create real economic contagion?",
            "Which parent, subsidiary, lender, insurer, trustee, or SPV ultimately absorbs losses on this path?",
        ],
        "physical": [
            "Is the physical/project/queue/permit match source-backed and specific enough to use?",
            "What capacity, COD, permit, power-delivery, or equipment bottleneck is actually evidenced?",
            "Does this physical constraint affect a high-notional AI/data-center capital exposure?",
        ],
        "compute": [
            "Is the GPU depreciation, TAM, payback, EPS, or chip-supply claim sourced from a primary or auditable market source?",
            "What assumption is being stress-tested, and what measured value supports or contradicts it?",
            "Does the claim affect 2026-2027 cash flow, earnings, or capacity-utilization conclusions?",
        ],
        "debt_service_stress": [
            "Are the maturity wall, measured interest, missing-rate, and missing-maturity amounts supported by source rows?",
            "Which missing terms would most change the debt-service stress conclusion?",
            "Is this weak link directly tied to AI/data-center exposure or only broader issuer financing?",
        ],
    }
    if category == "weak_link" and subcategory == "debt_service_stress":
        return question_sets["debt_service_stress"]
    return question_sets.get(category) or [
        "What exact source-backed fact is being adjudicated?",
        "Does the source support the exposure, risk driver, and AI/data-center relevance claimed here?",
        "What confidence level and remaining gap should the report carry after adjudication?",
    ]


def _required_decision_fields(row: dict[str, str]) -> list[str]:
    category = _field(row, "category")
    fields = [
        "decision",
        "confidence",
        "supported_amount_usd",
        "duplicate_or_aggregate",
        "ai_data_center_linkage",
        "remaining_gap",
        "source_quote_refs",
    ]
    if category in {"contract", "contagion"}:
        fields.extend(["recourse", "collateral_scope", "guarantee_scope", "risk_bearer"])
    if category == "physical":
        fields.extend(
            ["supported_capacity_mw", "supported_cod_or_queue_date", "blocking_constraint"]
        )
    if category == "compute":
        fields.extend(["assumption_tested", "measured_value", "period"])
    return fields


def _llm_prompt(
    row: dict[str, str],
    questions: tuple[str, ...],
    snippets: tuple[EvidenceSnippet, ...],
) -> str:
    snippet_text = "\n\n".join(
        f"SOURCE {index}: {snippet.source_uri}\n{snippet.snippet}"
        for index, snippet in enumerate(snippets, start=1)
    )
    if not snippet_text:
        snippet_text = "No local source snippet was resolved; use source URIs and hashes to retrieve evidence before deciding."
    questions_text = "\n".join(f"- {question}" for question in questions)
    return (
        "You are adjudicating a material AI/data-center/financing forensic blocker. "
        "Do not infer missing facts. Approve only source-supported claims.\n\n"
        f"Item: {_field(row, 'category')} / {_field(row, 'subcategory')} / {_field(row, 'priority')}\n"
        f"Entity: {_field(row, 'entity')}\n"
        f"Counterparty: {_field(row, 'counterparty')}\n"
        f"Exposure basis USD: {_exposure_basis_usd(row):,.0f}\n"
        f"Reason: {_field(row, 'reason')}\n\n"
        f"Questions:\n{questions_text}\n\n"
        f"Evidence:\n{snippet_text}"
    )


def _evidence_snippets(
    row: dict[str, str],
    *,
    artifact_index: dict[str, dict[str, str]],
    snippets_per_packet: int,
    snippet_chars: int,
) -> list[EvidenceSnippet]:
    scored_snippets: list[tuple[int, EvidenceSnippet]] = []
    seen_paths: set[str] = set()
    source_uris = _source_uris(row)
    content_hashes = _content_hashes(row)
    keys = [*content_hashes, *source_uris]
    for key in keys:
        artifact = artifact_index.get(key)
        if not artifact:
            continue
        local_path = artifact.get("local_path", "")
        if not local_path or local_path in seen_paths:
            continue
        seen_paths.add(local_path)
        path = Path(local_path)
        if not path.exists() or not path.is_file():
            continue
        text = _read_text(path)
        if not text:
            continue
        snippet_text = _best_row_snippet(row, text, snippet_chars)
        if not snippet_text:
            continue
        snippet = EvidenceSnippet(
            source_uri=artifact.get("source_uri", "") or source_uris[0],
            content_hash=artifact.get("content_hash", "")
            or (content_hashes[0] if content_hashes else ""),
            local_path=str(path),
            document_id=artifact.get("document_id", ""),
            accession_number=artifact.get("accession_number", ""),
            snippet=snippet_text,
        )
        scored_snippets.append((_evidence_snippet_score(row, snippet_text), snippet))

    if not scored_snippets:
        fallback = _row_context_fallback_snippet(row)
        if not fallback:
            return []
        scored_snippets.append((1, fallback))

    scored_snippets.sort(
        key=lambda item: (
            item[0],
            _capital_term_hit_count(item[1].snippet),
            len(item[1].snippet),
        ),
        reverse=True,
    )
    snippets: list[EvidenceSnippet] = []
    seen_values: set[tuple[str, str, str]] = set()
    for _, snippet in scored_snippets:
        dedupe_key = (
            snippet.source_uri,
            snippet.content_hash,
            snippet.snippet[:180],
        )
        if dedupe_key in seen_values:
            continue
        seen_values.add(dedupe_key)
        snippets.append(snippet)
        if len(snippets) >= snippets_per_packet:
            break
    return snippets


def _row_context_fallback_snippet(row: dict[str, str]) -> EvidenceSnippet | None:
    """Fallback evidence snippet from row context when source artifacts are non-text.

    This is intentionally limited to physical/compute rows where source systems
    are frequently delivered as binary archives and deterministic match context
    already exists on the row.
    """

    category = _field(row, "category")
    if category not in {"physical", "compute"}:
        return None
    source_uri = _field(row, "source_uri")
    content_hash = _field(row, "content_hash")
    if not source_uri or not content_hash:
        return None
    context_parts = [
        f"Category: {category}",
        f"Subcategory: {_field(row, 'subcategory')}",
        f"Entity: {_field(row, 'entity')}",
        f"Counterparty: {_field(row, 'counterparty')}",
        f"Project: {_field(row, 'project_name')}",
        f"Reason: {_field(row, 'reason')}",
        f"Action: {_field(row, 'recommended_action')}",
        f"Source URI: {source_uri}",
        f"Source section: {_field(row, 'page_or_section')}",
    ]
    snippet = _normalize_text(
        " ".join(part for part in context_parts if part and not part.endswith(": "))
    )
    if not snippet:
        return None
    return EvidenceSnippet(
        source_uri=source_uri,
        content_hash=content_hash,
        local_path="",
        document_id="review_queue_row_context",
        accession_number="",
        snippet=snippet[:1200],
    )


def _artifact_index(roots: list[Path]) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for row in _read_rows(roots, [Path("edgar_acquisition") / "edgar_document_inventory.csv"]):
        artifact = {
            "source_uri": _field(row, "filing_url"),
            "local_path": _field(row, "local_path"),
            "content_hash": _field(row, "content_hash"),
            "document_id": _field(row, "primary_document"),
            "accession_number": _field(row, "accession_number"),
        }
        _index_artifact(index, artifact)
    for row in _read_rows(roots, [Path("source_acquisition") / "source_artifact_inventory.csv"]):
        artifact = {
            "source_uri": _field(row, "source_uri"),
            "local_path": _field(row, "local_path"),
            "content_hash": _field(row, "content_hash"),
            "document_id": _field(row, "document_id"),
            "accession_number": _field(row, "filing_accession"),
        }
        _index_artifact(index, artifact)
    return index


def _index_artifact(index: dict[str, dict[str, str]], artifact: dict[str, str]) -> None:
    for key in (artifact.get("content_hash", ""), artifact.get("source_uri", "")):
        if key and key not in index:
            index[key] = artifact


def _summary(packets: list[MaterialityAdjudicationPacket]) -> MaterialityAdjudicationSummary:
    categories = Counter(packet.category for packet in packets)
    subcategories = Counter(packet.subcategory for packet in packets)
    relevance = Counter(packet.ecosystem_relevance for packet in packets)
    return MaterialityAdjudicationSummary(
        packets=len(packets),
        source_backed_packets=sum(1 for packet in packets if packet.source_uri),
        packets_with_local_evidence_snippets=sum(
            1 for packet in packets if packet.evidence_snippets
        ),
        ai_infra_relevant_packets=sum(
            1 for packet in packets if packet.ecosystem_relevance != "not_tagged"
        ),
        categories=dict(sorted(categories.items())),
        subcategories=dict(sorted(subcategories.items())),
        ecosystem_relevance=dict(sorted(relevance.items())),
        total_exposure_basis_usd=round(sum(packet.exposure_basis_usd for packet in packets), 2),
        top_exposure_basis_usd=round(packets[0].exposure_basis_usd, 2) if packets else 0.0,
        top_packets=[packet.to_dict() for packet in packets[:25]],
    )


def _materiality_sort_key(row: dict[str, str]) -> tuple[float, float, float, str]:
    return (
        -_materiality_score(row),
        -_exposure_basis_usd(row),
        -_float(row.get("risk_score")),
        _field(row, "review_id"),
    )


def _materiality_score(row: dict[str, str]) -> float:
    exposure_basis = _exposure_basis_usd(row)
    exposure_component = min(math.log10(max(exposure_basis, 1.0)) * 40, 500)
    priority_component = PRIORITY_RANK.get(_field(row, "priority"), 0) * 200
    relevance_component = AI_RELEVANCE_RANK.get(_field(row, "ecosystem_relevance"), 0) * 75
    risk_component = min(_float(row.get("risk_score")), 1.0) * 100
    category_component = {
        "capital": 80,
        "contract": 90,
        "contagion": 95,
        "weak_link": 100,
        "physical": 70,
        "compute": 70,
    }.get(_field(row, "category"), 0)
    return (
        priority_component
        + relevance_component
        + exposure_component
        + risk_component
        + category_component
    )


def _exposure_basis_usd(row: dict[str, str]) -> float:
    notional = _float(row.get("notional_amount_usd"))
    exposure = _float(row.get("exposure_usd"))
    capacity_proxy = _float(row.get("capacity_mw")) * 10_000_000
    return max(notional, exposure, capacity_proxy)


def _query_terms(row: dict[str, str]) -> list[str]:
    values = [
        _field(row, "counterparty"),
        _field(row, "project_name"),
        _field(row, "deal_id"),
        _field(row, "source_row_id"),
        _field(row, "subcategory").replace("_", " "),
        _field(row, "reason"),
        _field(row, "recommended_action"),
        _field(row, "entity"),
    ]
    values.extend(_amount_query_terms(_exposure_basis_usd(row)))
    if "aggregate_lease_obligation" in _field(row, "reason"):
        values.extend(
            [
                "data centers",
                "future lease payments",
                "not yet commenced",
                "not yet recorded",
                "finance lease obligations",
            ]
        )
    category_terms = {
        "capital": ["committed", "lease", "facility", "notional", "maturity", "borrower"],
        "contract": ["collateral", "guarantor", "maturity", "interest", "tranche"],
        "contagion": ["guarantee", "collateral", "non-recourse", "subsidiary", "parent"],
        "physical": ["interconnection", "queue", "permit", "capacity", "megawatt"],
        "compute": ["gpu", "depreciation", "useful life", "rental", "supply"],
        "weak_link": ["maturity", "interest", "debt", "stress", "collateral"],
    }
    values.extend(category_terms.get(_field(row, "category"), []))
    terms: list[str] = []
    for value in values:
        terms.extend(
            term
            for term in re.split(r"[^A-Za-z0-9.$-]+", value)
            if len(term) >= 4
            and term.lower()
            not in {
                "inc",
                "corp",
                "company",
                "llc",
                "pending",
                "adjudication",
                "status",
                "source",
            }
        )
    return terms


def _amount_query_terms(amount: float) -> list[str]:
    if amount <= 0:
        return []
    terms = [f"{amount:.0f}"]
    if amount >= 1_000_000_000:
        billions = amount / 1_000_000_000
        compact = f"{billions:g}"
        terms.extend([compact, f"${compact}", f"{compact} billion"])
    elif amount >= 1_000_000:
        millions = amount / 1_000_000
        compact = f"{millions:g}"
        terms.extend([compact, f"${compact}", f"{compact} million"])
    return terms


def _best_snippet(text: str, terms: list[str], snippet_chars: int) -> str:
    normalized = _normalize_text(text)
    if not normalized:
        return ""
    lowered = normalized.lower()
    unique_terms = list(dict.fromkeys(term.lower() for term in terms if len(term) >= 4))
    candidate_starts = [0]
    for term in unique_terms:
        index = lowered.find(term)
        while index >= 0 and len(candidate_starts) < 80:
            candidate_starts.append(max(0, index - snippet_chars // 3))
            index = lowered.find(term, index + len(term))
    start = max(
        candidate_starts,
        key=lambda candidate: _snippet_score(lowered, candidate, snippet_chars, unique_terms),
    )
    end = min(len(normalized), start + snippet_chars)
    return normalized[start:end].strip()


def _best_row_snippet(row: dict[str, str], text: str, snippet_chars: int) -> str:
    base = _best_snippet(text, _query_terms(row), snippet_chars)
    scope_candidate = _best_snippet(text, _capital_scope_query_terms(row), snippet_chars)
    scope_score = _scope_clause_hit_count(scope_candidate)
    if scope_score >= 2 and scope_score > _scope_clause_hit_count(base):
        return scope_candidate
    if not _is_non_specific_capital_candidate_row(row):
        return base
    contract_terms = _capital_term_query_terms(row)
    contract_candidate = _best_snippet(text, contract_terms, snippet_chars)
    if _capital_term_hit_count(contract_candidate) > _capital_term_hit_count(base):
        return contract_candidate
    return base


def _evidence_snippet_score(row: dict[str, str], snippet: str) -> int:
    lower_terms = list(dict.fromkeys(term.lower() for term in _query_terms(row) if len(term) >= 4))
    score = _snippet_score(snippet.lower(), 0, len(snippet), lower_terms)
    if _field(row, "category") in {"capital", "contract"}:
        score += _capital_term_hit_count(snippet) * 8
        score += _scope_clause_hit_count(snippet) * 12
    if _is_non_specific_capital_candidate_row(row):
        term_hits = _capital_term_hit_count(snippet)
        if term_hits == 0:
            score -= 30
        score += term_hits * 6
    score -= _boilerplate_penalty(snippet) * 7
    return score


def _capital_term_query_terms(row: dict[str, str]) -> list[str]:
    terms = [
        "credit agreement",
        "revolving credit facility",
        "term loan",
        "indenture",
        "administrative agent",
        "collateral agent",
        "secured",
        "unsecured",
        "guarantee",
        "guarantor",
        "maturity",
        "interest rate",
        "coupon",
        "notes due",
        "principal amount",
        "entered into",
    ]
    terms.extend(_amount_query_terms(_exposure_basis_usd(row)))
    return terms


def _capital_scope_query_terms(row: dict[str, str]) -> list[str]:
    if _field(row, "category") not in {"capital", "contract", "contagion", "weak_link"}:
        return []
    terms = [
        "security documents",
        "collateral documents",
        "security agreement",
        "collateral agreement",
        "loan and security agreement",
        "senior secured",
        "secured by",
        "shall be secured",
        "are secured by",
        "is secured by",
        "will be secured by",
        "substantially all assets",
        "first priority",
        "first-priority",
        "first lien",
        "second lien",
        "borrowing base",
        "pledges",
        "pledged",
        "grants a security interest",
        "unsecured obligations",
        "unsecured indebtedness",
        "senior unsecured",
        "without collateral",
        "non-recourse",
        "limited recourse",
        "guaranteed by",
        "guarantees of",
        "guaranty",
        "full and unconditional guarantee",
    ]
    terms.extend(_amount_query_terms(_exposure_basis_usd(row)))
    return terms


def _capital_term_hit_count(snippet: str) -> int:
    lowered = snippet.lower()
    markers = [
        "credit agreement",
        "revolving credit facility",
        "term loan",
        "indenture",
        "administrative agent",
        "collateral agent",
        "secured",
        "unsecured",
        "guarantee",
        "guarantor",
        "maturity",
        "interest rate",
        "coupon",
        "notes due",
        "principal amount",
        "entered into",
    ]
    return sum(1 for marker in markers if marker in lowered)


def _scope_clause_hit_count(snippet: str) -> int:
    lowered = snippet.lower()
    strong_markers = [
        "security documents",
        "collateral documents",
        "loan and security agreement",
        "asset-based revolving credit agreement",
        "asset based revolving credit agreement",
        "senior secured",
        "secured by",
        "shall be secured",
        "are secured by",
        "is secured by",
        "will be secured by",
        "substantially all assets",
        "first priority",
        "first-priority",
        "first lien",
        "second lien",
        "borrowing base",
        "grants a security interest",
        "pledges",
        "pledged",
        "unsecured obligations",
        "unsecured indebtedness",
        "senior unsecured",
        "without collateral",
        "non-recourse",
        "limited recourse",
        "guaranteed by",
        "guarantees of",
        "full and unconditional guarantee",
    ]
    generic_markers = [
        "security agreement",
        "collateral agreement",
        "security interest",
        "collateral agent",
        "guarantees",
        "guarantors",
        "guaranty",
        "recourse",
    ]
    strong_hits = sum(1 for marker in strong_markers if marker in lowered)
    generic_hits = sum(1 for marker in generic_markers if marker in lowered)
    if _contains_definition_only_scope(lowered):
        if not _has_executable_scope_clause(lowered):
            return 0
        generic_hits = max(0, generic_hits - 2)
    return strong_hits * 2 + generic_hits


def _has_executable_scope_clause(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "shall be secured",
            "are secured by",
            "is secured by",
            "will be secured by",
            "grants a security interest",
            "guaranteed by",
            "full and unconditional guarantee",
            "without collateral",
            "non-recourse",
            "senior unsecured",
            "unsecured indebtedness",
            "unsecured obligations",
        )
    )


def _contains_definition_only_scope(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "lien means",
            "permitted liens",
            "debt rating",
            "unsecured debt issued by the borrower",
            "secured by any lien on property",
        )
    )


def _boilerplate_penalty(snippet: str) -> int:
    lowered = snippet.lower()
    markers = [
        "forward-looking statements",
        "about ",
        "table of contents",
        "exhibit 99",
        "prospectus supplement",
        "risk factors",
    ]
    return sum(1 for marker in markers if marker in lowered)


def _snippet_score(text: str, start: int, snippet_chars: int, terms: list[str]) -> int:
    window = text[start : start + snippet_chars]
    return sum(1 for term in terms if term in window)


def _normalize_text(text: str) -> str:
    unescaped = html.unescape(text)
    no_scripts = re.sub(r"(?is)<(script|style).*?</\1>", " ", unescaped)
    no_tags = re.sub(r"(?s)<[^>]+>", " ", no_scripts)
    return re.sub(r"\s+", " ", no_tags).strip()


def _read_text(path: Path) -> str:
    path_key = str(path)
    with _TEXT_CACHE_LOCK:
        cached = _TEXT_CACHE.get(path_key)
    if cached is not None:
        return cached
    try:
        text = _read_xlsx_text(path)
        if not text:
            text = _read_plain_text(path)
    except OSError:
        text = ""
    with _TEXT_CACHE_LOCK:
        _TEXT_CACHE[path_key] = text
    return text


def _read_plain_text(path: Path) -> str:
    if path.suffix.lower() in _BINARY_TEXT_SKIP_SUFFIXES:
        return ""
    raw = path.read_bytes()
    if _looks_binary_bytes(raw):
        return ""
    return raw.decode("utf-8", errors="ignore")


def _looks_binary_bytes(raw: bytes) -> bool:
    if not raw:
        return False
    sample = raw[:8192]
    if b"\x00" in sample:
        return True
    printable = 0
    for byte in sample:
        if byte in {9, 10, 13} or 32 <= byte <= 126:
            printable += 1
    return printable / len(sample) < 0.75


def _read_xlsx_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix not in {".xlsx", ".xlsm", ".xltx", ".xltm", ".bin"}:
        return ""
    try:
        with zipfile.ZipFile(path) as archive:
            sheet_names = sorted(
                name
                for name in archive.namelist()
                if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
            )
            if not sheet_names:
                return ""
            shared_strings = _xlsx_shared_strings(archive)
            rows: list[str] = []
            for sheet_name in sheet_names:
                rows.extend(_xlsx_sheet_rows(archive, sheet_name, shared_strings))
                if len(rows) >= 25_000:
                    break
            return "\n".join(rows[:25_000])
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError):
        return ""


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    path = "xl/sharedStrings.xml"
    if path not in archive.namelist():
        return []
    raw = archive.read(path)
    root = ElementTree.fromstring(raw)
    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    strings: list[str] = []
    for item in root.findall(f"{namespace}si"):
        parts = [node.text or "" for node in item.findall(f".//{namespace}t")]
        strings.append("".join(parts).strip())
    return strings


def _xlsx_sheet_rows(
    archive: zipfile.ZipFile,
    sheet_name: str,
    shared_strings: list[str],
) -> list[str]:
    raw = archive.read(sheet_name)
    root = ElementTree.fromstring(raw)
    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rows: list[str] = []
    for row in root.findall(f".//{namespace}row"):
        values: list[str] = []
        for cell in row.findall(f"{namespace}c"):
            raw_value = cell.findtext(f"{namespace}v", default="").strip()
            inline_value = "".join(
                node.text or "" for node in cell.findall(f".//{namespace}is/{namespace}t")
            ).strip()
            value = inline_value or raw_value
            if not value:
                continue
            if cell.get("t") == "s":
                try:
                    shared_value = shared_strings[int(value)]
                except (ValueError, IndexError):
                    shared_value = value
                values.append(shared_value)
            else:
                values.append(value)
        if values:
            rows.append(" | ".join(values))
        if len(rows) >= 4_000:
            break
    return rows


def _source_uris(row: dict[str, str]) -> list[str]:
    values = _json_list(row.get("source_uris"))
    single = _field(row, "source_uri")
    if single:
        values.insert(0, single)
    return list(dict.fromkeys(value for value in values if value))


def _content_hashes(row: dict[str, str]) -> list[str]:
    values = _json_list(row.get("content_hashes"))
    single = _field(row, "content_hash")
    if single:
        values.insert(0, single)
    return list(dict.fromkeys(value for value in values if value))


def _is_reviewed_status(status: str) -> bool:
    statuses = [part.strip().lower() for part in status.replace(";", "|").split("|")]
    return any(status in REVIEWED_STATUSES for status in statuses)


def _is_non_specific_capital_candidate_row(row: dict[str, str]) -> bool:
    if _field(row, "category") != "capital":
        return False
    reason = _field(row, "reason").lower()
    return any(
        marker in reason
        for marker in [
            "commitment scope: candidate_requires_adjudication",
            "notional context: candidate_notional",
            "source extraction marked requires llm adjudication",
        ]
    )


def _packet_id(*parts: Any) -> str:
    raw = "|".join(
        json.dumps(part, sort_keys=True) if isinstance(part, tuple) else str(part) for part in parts
    )
    return "adjudication:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def _read_rows(roots: list[Path], relative_paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for root in roots:
        for relative_path in relative_paths:
            path = root / relative_path
            if not path.exists() or path.stat().st_size == 0:
                continue
            with path.open(newline="", errors="ignore") as f:
                rows.extend(
                    {
                        str(key): (value or "").strip()
                        for key, value in row.items()
                        if key is not None
                    }
                    for row in csv.DictReader(f)
                )
    return rows


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
            return [item.strip() for item in value.split("|") if item.strip()]
        if isinstance(loaded, list):
            return [str(item) for item in loaded if str(item)]
    return []


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(str(value).replace(",", "").replace("$", ""))
    except ValueError:
        return 0.0


def _field(row: dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()
