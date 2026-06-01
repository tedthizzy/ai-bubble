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
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REVIEWED_STATUSES = {"approved", "overridden", "rejected"}
PRIORITY_RANK = {"critical": 4, "high": 3, "medium": 2, "watch": 1}
AI_RELEVANCE_RANK = {
    "direct_ai_infra": 4,
    "watchlist_entity": 3,
    "physical_execution": 3,
    "compute_economics": 3,
    "not_tagged": 0,
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
    limit: int = 100,
    snippets_per_packet: int = 2,
    snippet_chars: int = 1_200,
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

    selected = sorted(best_by_group.values(), key=_materiality_sort_key)[:limit]
    packets = [
        _packet_from_row(
            row,
            rank=rank,
            artifact_index=artifact_index,
            snippets_per_packet=snippets_per_packet,
            snippet_chars=snippet_chars,
        )
        for rank, row in enumerate(selected, start=1)
    ]
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
    snippets: list[EvidenceSnippet] = []
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
        snippets.append(
            EvidenceSnippet(
                source_uri=artifact.get("source_uri", "") or source_uris[0],
                content_hash=artifact.get("content_hash", "")
                or (content_hashes[0] if content_hashes else ""),
                local_path=str(path),
                document_id=artifact.get("document_id", ""),
                accession_number=artifact.get("accession_number", ""),
                snippet=_best_snippet(text, _query_terms(row), snippet_chars),
            )
        )
        if len(snippets) >= snippets_per_packet:
            break
    return snippets


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


def _snippet_score(text: str, start: int, snippet_chars: int, terms: list[str]) -> int:
    window = text[start : start + snippet_chars]
    return sum(1 for term in terms if term in window)


def _normalize_text(text: str) -> str:
    unescaped = html.unescape(text)
    no_scripts = re.sub(r"(?is)<(script|style).*?</\1>", " ", unescaped)
    no_tags = re.sub(r"(?s)<[^>]+>", " ", no_scripts)
    return re.sub(r"\s+", " ", no_tags).strip()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")
    except OSError:
        return ""


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
