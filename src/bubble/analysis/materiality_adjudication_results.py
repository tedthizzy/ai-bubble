"""Automated adjudication pass over materiality-ranked packets.

This layer records source-backed decisions about whether a materiality packet is
usable as a final metric, only a valid blocker, or still needs deeper extraction.
It is intentionally conservative: source-backed blocker support is not the same
thing as approval for high-confidence report metrics.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

ADJUDICATOR_ID = "codex-materiality-evidence-adjudicator-v1"

FINAL_METRIC_DECISIONS = {"approved_for_metric_use"}
BLOCKER_DECISIONS = {"supported_as_material_blocker", "needs_deeper_extraction"}
REJECT_DECISIONS = {"reject_missing_provenance", "rejected_or_deprioritized"}


@dataclass(frozen=True)
class MaterialityAdjudicationDecision:
    """One automated adjudication result for a materiality packet."""

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
    exposure_basis_usd: float
    decision: str
    metric_use_status: str
    source_support: str
    confidence: float
    supported_amount_usd: float
    metric_group_id: str
    metric_snapshot_date: str
    metric_aggregation_policy: str
    duplicate_or_aggregate: str
    ai_data_center_linkage: str
    risk_bearer: str
    remaining_gap: str
    required_next_extraction: str
    evidence_quote: str
    evidence_quote_refs: tuple[str, ...]
    rationale: str
    adjudicator_id: str
    adjudicated_at: str
    source_uri: str
    source_uris: tuple[str, ...]
    content_hash: str
    content_hashes: tuple[str, ...]
    packet_reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MaterialityAdjudicationDecisionSummary:
    """Rollup for automated materiality adjudication decisions."""

    decisions: int
    source_quote_backed_decisions: int
    supported_as_material_blocker: int
    needs_deeper_extraction: int
    needs_source_retrieval: int
    approved_for_metric_use: int
    rejected_or_deprioritized: int
    ai_infra_relevant_decisions: int
    total_exposure_basis_usd: float
    approved_row_supported_amount_usd: float
    final_metric_supported_amount_usd: float
    final_metric_group_count: int
    blocker_exposure_basis_usd: float
    decisions_by_status: dict[str, int]
    decisions_by_category: dict[str, int]
    top_remaining_gaps: list[dict[str, Any]]
    top_decisions: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MaterialityAdjudicationDecisionBatch:
    """Built automated adjudication result artifact."""

    decisions: list[MaterialityAdjudicationDecision]
    summary: MaterialityAdjudicationDecisionSummary


def build_materiality_adjudication_decisions(
    data_dirs: list[str | Path] | None = None,
    *,
    adjudicated_at: str | None = None,
) -> MaterialityAdjudicationDecisionBatch:
    """Build conservative automated adjudication decisions from packet rows."""

    roots = [Path(root) for root in (data_dirs or ["data"])]
    packets = _read_rows(roots, [Path("reports") / "materiality_adjudication_packets.csv"])
    timestamp = adjudicated_at or datetime.now(UTC).isoformat()
    decisions = [_adjudicate_packet(packet, adjudicated_at=timestamp) for packet in packets]
    summary = _summary(decisions)
    return MaterialityAdjudicationDecisionBatch(decisions=decisions, summary=summary)


def write_materiality_adjudication_decisions(
    batch: MaterialityAdjudicationDecisionBatch,
    output_dir: str | Path,
) -> dict[str, str]:
    """Write automated materiality adjudication decisions and summary."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    decisions_path = out / "materiality_adjudication_decisions.csv"
    summary_path = out / "materiality_adjudication_decision_summary.json"
    _write_csv(decisions_path, [decision.to_dict() for decision in batch.decisions])
    summary_path.write_text(json.dumps(batch.summary.to_dict(), indent=2))
    return {"decisions_csv": str(decisions_path), "summary_json": str(summary_path)}


def _adjudicate_packet(
    packet: dict[str, str],
    *,
    adjudicated_at: str,
) -> MaterialityAdjudicationDecision:
    source_uris = tuple(_json_list(packet.get("source_uris")) or [_field(packet, "source_uri")])
    content_hashes = tuple(
        _json_list(packet.get("content_hashes")) or [_field(packet, "content_hash")]
    )
    evidence_snippets = _json_dicts(packet.get("evidence_snippets"))
    quote, quote_refs = _best_evidence_quote(packet, evidence_snippets)
    source_support = _source_support(packet, quote, evidence_snippets)
    gaps = _remaining_gaps(packet, quote)
    duplicate_or_aggregate = _duplicate_or_aggregate(packet, quote)
    ai_linkage = _ai_linkage(packet)
    decision = _decision(packet, quote, gaps, source_support)
    metric_use_status = _metric_use_status(packet, decision, gaps)
    confidence = _confidence(decision, source_support, gaps)
    exposure_basis = _float(packet.get("exposure_basis_usd"))
    supported_amount = exposure_basis if metric_use_status == "approved_for_metric_use" else 0.0
    risk_bearer = _risk_bearer(packet, quote, gaps)
    metric_group_id = _metric_group_id(packet, quote, metric_use_status)
    metric_snapshot_date = _metric_snapshot_date(packet, quote, metric_use_status)
    metric_aggregation_policy = _metric_aggregation_policy(packet, quote, metric_use_status)

    return MaterialityAdjudicationDecision(
        packet_id=_field(packet, "packet_id"),
        rank=int(_float(packet.get("rank"))),
        review_id=_field(packet, "review_id"),
        review_group_id=_field(packet, "review_group_id"),
        priority=_field(packet, "priority"),
        category=_field(packet, "category"),
        subcategory=_field(packet, "subcategory"),
        ecosystem_relevance=_field(packet, "ecosystem_relevance"),
        entity=_field(packet, "entity"),
        counterparty=_field(packet, "counterparty"),
        exposure_basis_usd=round(exposure_basis, 2),
        decision=decision,
        metric_use_status=metric_use_status,
        source_support=source_support,
        confidence=confidence,
        supported_amount_usd=round(supported_amount, 2),
        metric_group_id=metric_group_id,
        metric_snapshot_date=metric_snapshot_date,
        metric_aggregation_policy=metric_aggregation_policy,
        duplicate_or_aggregate=duplicate_or_aggregate,
        ai_data_center_linkage=ai_linkage,
        risk_bearer=risk_bearer,
        remaining_gap=" | ".join(gaps),
        required_next_extraction=_required_next_extraction(packet, quote, gaps),
        evidence_quote=quote,
        evidence_quote_refs=quote_refs,
        rationale=_rationale(packet, quote, decision, metric_use_status, source_support, gaps),
        adjudicator_id=ADJUDICATOR_ID,
        adjudicated_at=adjudicated_at,
        source_uri=source_uris[0] if source_uris else "",
        source_uris=source_uris,
        content_hash=content_hashes[0] if content_hashes else "",
        content_hashes=content_hashes,
        packet_reason=_field(packet, "reason"),
    )


def _decision(
    packet: dict[str, str],
    quote: str,
    gaps: list[str],
    source_support: str,
) -> str:
    if source_support == "missing_provenance":
        return "reject_missing_provenance"
    if source_support == "source_uri_only":
        return "needs_source_retrieval"
    if _field(packet, "category") == "capital" and _looks_like_boilerplate(packet, quote):
        return "needs_deeper_extraction"
    if gaps:
        return "needs_deeper_extraction"
    if _has_supporting_terms(packet, quote):
        return "supported_as_material_blocker"
    return "needs_deeper_extraction"


def _metric_use_status(packet: dict[str, str], decision: str, gaps: list[str]) -> str:
    if decision != "supported_as_material_blocker" or gaps:
        return "blocked_pending_extraction"
    if _field(packet, "category") not in {"capital", "contract", "physical", "compute"}:
        return "triage_only"
    if _float(packet.get("exposure_basis_usd")) <= 0:
        return "triage_only"
    return "approved_for_metric_use"


def _remaining_gaps(packet: dict[str, str], quote: str) -> list[str]:
    text = _combined_text(packet, quote)
    gaps: list[str] = []
    if not quote:
        gaps.append("local source quote not resolved")
    if _requires_aggregate_split(packet, quote):
        gaps.append("split aggregate disclosure from specific committed obligation")
    if "preliminary prospectus" in text or "not complete and may be changed" in text:
        gaps.append("confirm final prospectus or underlying agreement terms")
    if "shelf" in text:
        gaps.append("distinguish shelf capacity from committed financing")
    if "missing-rate" in text or "missing explicit rate" in text:
        gaps.append("extract explicit interest/rent rate evidence")
    if "missing-maturity" in text or "missing maturity" in text:
        gaps.append("extract explicit maturity or payment schedule evidence")
    gaps.extend(_category_gaps(packet, quote))
    return list(dict.fromkeys(gaps))


def _category_gaps(packet: dict[str, str], text: str) -> list[str]:
    text_lower = text.lower()
    category = _field(packet, "category")
    reason_text = _field(packet, "reason").lower()
    counterparty_text = _field(packet, "counterparty").lower()
    gaps: list[str] = []
    if category == "capital" and _is_source_backed_aggregate_obligation_snapshot(packet, text):
        return gaps
    if category == "capital" and _is_non_specific_capital_candidate_without_term_evidence(
        packet, text
    ):
        gaps.append("acquire underlying agreement or debt schedule clause for term-level extraction")
        return gaps
    if category == "capital" and _requires_aggregate_split(packet, text):
        # Aggregate/shelf rows are blocked on committed-obligation splitting first.
        # Do not stack term-level party/collateral/recourse gaps until a specific
        # contract-level source row is extracted.
        return gaps
    if category in {"capital", "contract"}:
        if not _field(packet, "counterparty") and not _inferred_counterparty_from_quote(text):
            gaps.append("extract named counterparty and role")
        unsecured_scope_present = _contains_any(
            text_lower,
            [
                "senior unsecured",
                "unsecured general obligations",
                "unsecured obligations",
                "none of which was secured debt",
                "without collateral",
            ],
        )
        issuer_note_scope_present = _contains_any(text_lower, ["indenture", "issuer"]) and _contains_any(
            text_lower, ["notes", "noteholders"]
        )
        secured_lender_scope_present = _contains_any(
            reason_text,
            [
                "pending contract tranche review; tranche:",
                "transaction_facility",
                "transaction_principal",
            ],
        ) and _contains_any(
            counterparty_text,
            [
                "lender",
                "lenders",
                "administrative agent",
                "collateral agent",
                "noteholders",
            ],
        )
        guarantee_scope_present = _contains_any(
            reason_text,
            [
                "guarantee scope present",
                "guarantor terms present",
                "guarantee terms present",
            ],
        )
        if not (
            guarantee_scope_present
            or unsecured_scope_present
            or issuer_note_scope_present
            or secured_lender_scope_present
            or _contains_any(text_lower, ["recourse", "non-recourse", "guarantee", "guarantor"])
        ):
            gaps.append("determine recourse and guarantee scope")
        collateral_scope_present = _contains_any(
            reason_text,
            [
                "collateral terms present",
                "collateral scope present",
                "secured terms present",
            ],
        )
        if not (
            collateral_scope_present
            or unsecured_scope_present
            or _contains_any(text_lower, ["collateral", "secured", "security interest", "pledge"])
        ):
            gaps.append("determine collateral scope")
    if category == "contagion" and not _contains_any(
        text_lower, ["parent", "subsidiary", "guarantee"]
    ):
        gaps.append("validate legal-entity path and risk transfer mechanism")
    if category == "physical" and not _contains_any(
        text_lower, ["queue", "permit", "interconnection"]
    ):
        gaps.append("confirm queue, permit, or interconnection record linkage")
    if category == "compute" and not _contains_any(
        text_lower, ["depreciation", "useful life", "rental", "supply", "gpu"]
    ):
        gaps.append("attach direct compute-economics source evidence")
    return gaps


def _required_next_extraction(packet: dict[str, str], quote: str, gaps: list[str]) -> str:
    if gaps:
        return " | ".join(gaps)
    if _is_source_backed_aggregate_obligation_snapshot(packet, quote):
        return (
            "persist aggregate obligation snapshot by issuer, disclosure date, amount, "
            "and source quote; do not treat as an individual contract"
        )
    category = _field(packet, "category")
    defaults = {
        "capital": "persist amount, parties, maturity, recourse, collateral, and duplicate-group decision",
        "contract": "persist tranche amount, rate, maturity, collateral, guarantees, and downside bearer",
        "contagion": "persist legal-entity match, risk-transfer mechanism, and loss bearer",
        "physical": "persist capacity, project linkage, queue/permit status, and blocker date",
        "compute": "persist measured assumption, period, source price/rate/policy, and EPS impact",
        "weak_link": "persist underlying source rows and move composite risk to metric-specific decisions",
    }
    return defaults.get(category, "persist source-supported decision fields")


def _confidence(decision: str, source_support: str, gaps: list[str]) -> float:
    base = {
        "supported_as_material_blocker": 0.78,
        "needs_deeper_extraction": 0.62,
        "needs_source_retrieval": 0.35,
        "reject_missing_provenance": 0.1,
        "rejected_or_deprioritized": 0.25,
    }.get(decision, 0.4)
    if source_support != "quote_backed":
        base = min(base, 0.4)
    if gaps:
        base = min(base, max(0.45, base - min(len(gaps), 4) * 0.06))
    return round(base, 4)


def _source_support(
    packet: dict[str, str],
    quote: str,
    evidence_snippets: list[dict[str, Any]],
) -> str:
    has_source_uri = bool(_field(packet, "source_uri") or _json_list(packet.get("source_uris")))
    has_hash = bool(
        _field(packet, "content_hash")
        or any(_json_list(packet.get("content_hashes")))
        or any(str(snippet.get("content_hash") or "") for snippet in evidence_snippets)
    )
    if not has_source_uri or not has_hash:
        return "missing_provenance"
    if quote:
        return "quote_backed"
    return "source_uri_only"


def _duplicate_or_aggregate(packet: dict[str, str], quote: str) -> str:
    text = _combined_text(packet, quote)
    if "aggregate" in text or "duplicate" in text:
        return "yes"
    if "single" in text and "obligation" in text:
        return "no"
    return "unknown"


def _metric_group_id(
    packet: dict[str, str],
    quote: str,
    metric_use_status: str,
) -> str:
    if metric_use_status not in FINAL_METRIC_DECISIONS:
        return ""
    if _is_source_backed_aggregate_obligation_snapshot(packet, quote):
        entity_key = re.sub(r"[^a-z0-9]+", "-", _field(packet, "entity").lower()).strip("-")
        subcategory_key = re.sub(
            r"[^a-z0-9]+",
            "-",
            (_field(packet, "subcategory") or "capital").lower(),
        ).strip("-")
        return f"aggregate-obligation-snapshot:{entity_key}:{subcategory_key}"
    if _field(packet, "review_group_id"):
        return f"review-group:{_field(packet, 'review_group_id')}"
    if _field(packet, "packet_id"):
        return f"packet:{_field(packet, 'packet_id')}"
    return ""


def _metric_snapshot_date(
    packet: dict[str, str],
    quote: str,
    metric_use_status: str,
) -> str:
    if metric_use_status not in FINAL_METRIC_DECISIONS:
        return ""
    if _is_source_backed_aggregate_obligation_snapshot(packet, quote):
        parsed = _as_of_date(quote) or _date_from_text(_field(packet, "reason"))
        return parsed.isoformat() if parsed else ""
    parsed = _date_from_text(quote) or _date_from_text(_field(packet, "reason"))
    return parsed.isoformat() if parsed else ""


def _metric_aggregation_policy(
    packet: dict[str, str],
    quote: str,
    metric_use_status: str,
) -> str:
    if metric_use_status not in FINAL_METRIC_DECISIONS:
        return ""
    if _is_source_backed_aggregate_obligation_snapshot(packet, quote):
        return "latest_snapshot_per_metric_group"
    return "sum_distinct_metric_rows"


def _ai_linkage(packet: dict[str, str]) -> str:
    relevance = _field(packet, "ecosystem_relevance")
    if relevance == "direct_ai_infra":
        return "direct"
    if relevance == "physical_execution":
        return "physical"
    if relevance == "compute_economics":
        return "compute"
    if relevance == "watchlist_entity":
        return "watchlist"
    return "not_established"


def _risk_bearer(packet: dict[str, str], quote: str, gaps: list[str]) -> str:
    counterparty = _field(packet, "counterparty")
    text = _combined_text(packet, quote)
    inferred_counterparty = _inferred_counterparty_from_quote(quote)
    if _is_source_backed_aggregate_obligation_snapshot(packet, quote):
        entity = _field(packet, "entity")
        return (
            f"aggregate obligation snapshot for {entity}; counterparties not itemized"
            if entity
            else "aggregate obligation snapshot; counterparties not itemized"
        )
    if "risk bearer" in " ".join(gaps):
        return "unknown"
    if counterparty and _contains_any(text, ["lender", "noteholder", "trustee", "secured party"]):
        return counterparty
    if counterparty:
        return f"candidate: {counterparty}"
    if inferred_counterparty:
        return f"inferred: {inferred_counterparty}"
    return "unknown"


def _inferred_counterparty_from_quote(quote: str) -> str:
    if not quote:
        return ""
    lenders_clause = re.search(
        r"(?:the lenders named therein|the lenders party thereto)\s*,\s*(?P<name>[^;]{2,180}?)\s*,\s*as\s+(?:the\s+)?(?:administrative|collateral|facility|syndication)\s+agent\b",
        quote,
        flags=re.IGNORECASE,
    )
    if lenders_clause:
        candidate = _normalize_counterparty_candidate(lenders_clause.group("name"))
        if candidate:
            return candidate

    role_clause = re.search(
        r"(?P<prefix>[^;]{2,320}?)\s*,\s*as\s+(?:the\s+)?(?:administrative|collateral|facility|syndication)\s+agent\b|(?P<prefix_trustee>[^;]{2,320}?)\s*,\s*as\s+(?:the\s+)?trustee\b",
        quote,
        flags=re.IGNORECASE,
    )
    if not role_clause:
        return ""

    prefix = role_clause.group("prefix") or role_clause.group("prefix_trustee") or ""
    fragments = [
        part.strip(" ,")
        for part in re.split(r"\bwith\b|\band\b", prefix, flags=re.IGNORECASE)
        if part.strip(" ,")
    ]
    for fragment in reversed(fragments):
        candidate = _normalize_counterparty_candidate(fragment)
        if candidate and _looks_like_counterparty_name(candidate):
            return candidate
    candidate = _normalize_counterparty_candidate(prefix)
    if candidate and _looks_like_counterparty_name(candidate):
        return candidate
    return ""


def _normalize_counterparty_candidate(raw: str) -> str:
    candidate = _normalize(raw)
    candidate = re.sub(r"\s*,\s*as\s+.*$", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(
        r"^(?:among|with|and|the lenders named therein|the lenders party thereto)\b[:,\s-]*",
        "",
        candidate,
        flags=re.IGNORECASE,
    )
    candidate = candidate.strip(" ,.;:-")
    if len(candidate) < 4:
        return ""
    if _contains_any(candidate.lower(), ["credit agreement", "bridge loan credit agreement"]):
        return ""
    return candidate


def _looks_like_counterparty_name(candidate: str) -> bool:
    lowered = candidate.lower()
    return _contains_any(
        lowered,
        [
            "bank",
            "trust",
            "capital",
            "credit",
            "securities",
            "llc",
            "inc",
            "corp",
            "corporation",
            "ltd",
            "plc",
            "n.a",
            "association",
            "partners",
            "holdings",
            "funding",
        ],
    )


def _rationale(
    packet: dict[str, str],
    quote: str,
    decision: str,
    metric_use_status: str,
    source_support: str,
    gaps: list[str],
) -> str:
    category = _field(packet, "category")
    exposure = _float(packet.get("exposure_basis_usd"))
    if (
        metric_use_status == "approved_for_metric_use"
        and _is_source_backed_aggregate_obligation_snapshot(packet, quote)
    ):
        return (
            f"Source-backed aggregate obligation snapshot is usable for aggregate "
            f"metrics at ${exposure:,.0f}; it is not treated as an individual contract."
        )
    if decision == "supported_as_material_blocker":
        return (
            f"Source-backed {category} blocker remains material at "
            f"${exposure:,.0f}; metric status is {metric_use_status}."
        )
    if decision == "needs_deeper_extraction":
        return (
            f"Source-backed {category} blocker is material at ${exposure:,.0f}, "
            f"but final metric use is blocked by: {' | '.join(gaps)}."
        )
    return f"Decision {decision}; source support is {source_support}."


def _has_supporting_terms(packet: dict[str, str], quote: str) -> bool:
    text = _combined_text(packet, quote)
    category = _field(packet, "category")
    terms = {
        "capital": [
            "credit agreement",
            "facility",
            "loan",
            "notes",
            "lease",
            "obligation",
            "commitment",
            "commitments",
        ],
        "contract": ["collateral", "guarantor", "interest", "maturity", "tranche"],
        "contagion": ["guarantee", "collateral", "parent", "subsidiary", "non-recourse"],
        "physical": ["queue", "permit", "interconnection", "capacity", "mw"],
        "compute": ["gpu", "depreciation", "useful life", "rental", "supply"],
        "weak_link": ["maturity", "interest", "debt", "lease", "credit", "notes"],
    }.get(category, [])
    return _contains_any(text, terms)


def _looks_like_boilerplate(packet: dict[str, str], quote: str) -> bool:
    text = _combined_text(packet, quote)
    return _contains_any(
        text,
        [
            "not an offer to sell",
            "preliminary prospectus",
            "not complete and may be changed",
            "registration statement",
        ],
    )


def _best_evidence_quote(
    packet: dict[str, str],
    snippets: list[dict[str, Any]],
) -> tuple[str, tuple[str, ...]]:
    if not snippets:
        return "", ()
    terms = _quote_terms(packet)
    text_snippets = [
        (item, _clean_snippet_text(str(item.get("snippet") or ""))) for item in snippets
    ]
    text_snippets = [(item, text) for item, text in text_snippets if text]
    if not text_snippets:
        return "", ()
    best_snippet = max(
        text_snippets,
        key=lambda item: _quote_score(item[1], terms),
    )
    snippet = best_snippet[1]
    snippet_meta = best_snippet[0]
    sentence = _best_sentence(snippet, terms)
    quote = sentence[:650].strip()
    refs = tuple(
        value
        for value in [
            str(snippet_meta.get("source_uri") or ""),
            str(snippet_meta.get("content_hash") or ""),
            str(snippet_meta.get("document_id") or ""),
        ]
        if value
    )
    return quote, refs


def _best_sentence(text: str, terms: list[str]) -> str:
    if not text:
        return ""
    parts = [part.strip() for part in re.split(r"(?<=[.;:])\s+", text) if part.strip()]
    if not parts:
        return text
    sentence = max(parts, key=lambda part: _quote_score(part.lower(), terms))
    if len(sentence) >= 120:
        return sentence
    index = parts.index(sentence)
    neighbors = parts[max(0, index - 1) : index + 2]
    return " ".join(neighbors)


def _quote_terms(packet: dict[str, str]) -> list[str]:
    raw_terms = [
        _field(packet, "entity"),
        _field(packet, "counterparty"),
        _field(packet, "category"),
        _field(packet, "subcategory").replace("_", " "),
        _field(packet, "reason"),
    ]
    terms: list[str] = []
    terms.extend(_amount_quote_terms(_float(packet.get("exposure_basis_usd"))))
    if "aggregate_lease_obligation" in _field(packet, "reason"):
        terms.extend(
            [
                "data centers",
                "future lease payments",
                "not yet commenced",
                "not yet recorded",
                "finance lease obligations",
            ]
        )
    for value in raw_terms:
        terms.extend(
            term.lower()
            for term in re.split(r"[^A-Za-z0-9.$-]+", value)
            if len(term) >= 4
            and term.lower()
            not in {
                "pending",
                "adjudication",
                "source",
                "status",
                "candidate",
                "extraction",
                "marked",
                "requires",
            }
        )
    return list(dict.fromkeys(terms))


def _amount_quote_terms(amount: float) -> list[str]:
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


def _quote_score(text: str, terms: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if term in lowered)


def _clean_snippet_text(value: str) -> str:
    if not value:
        return ""
    if value.lstrip().startswith("PK\x03\x04"):
        return ""
    control_chars = sum(1 for char in value if ord(char) < 32 and char not in {"\t", "\n", "\r"})
    if control_chars / max(len(value), 1) > 0.02:
        return ""
    return _normalize(value)


def _summary(
    decisions: list[MaterialityAdjudicationDecision],
) -> MaterialityAdjudicationDecisionSummary:
    status_counts = Counter(decision.decision for decision in decisions)
    category_counts = Counter(decision.category for decision in decisions)
    gap_counts: Counter[str] = Counter()
    for decision in decisions:
        for gap in decision.remaining_gap.split(" | "):
            if gap:
                gap_counts[gap] += 1
    return MaterialityAdjudicationDecisionSummary(
        decisions=len(decisions),
        source_quote_backed_decisions=sum(
            decision.source_support == "quote_backed" for decision in decisions
        ),
        supported_as_material_blocker=status_counts.get("supported_as_material_blocker", 0),
        needs_deeper_extraction=status_counts.get("needs_deeper_extraction", 0),
        needs_source_retrieval=status_counts.get("needs_source_retrieval", 0),
        approved_for_metric_use=sum(
            decision.metric_use_status in FINAL_METRIC_DECISIONS for decision in decisions
        ),
        rejected_or_deprioritized=sum(
            decision.decision in REJECT_DECISIONS for decision in decisions
        ),
        ai_infra_relevant_decisions=sum(
            decision.ai_data_center_linkage != "not_established" for decision in decisions
        ),
        total_exposure_basis_usd=round(
            sum(decision.exposure_basis_usd for decision in decisions),
            2,
        ),
        approved_row_supported_amount_usd=round(
            sum(decision.supported_amount_usd for decision in decisions),
            2,
        ),
        final_metric_supported_amount_usd=round(
            _deduped_final_metric_supported_amount(decisions),
            2,
        ),
        final_metric_group_count=_final_metric_group_count(decisions),
        blocker_exposure_basis_usd=round(
            sum(
                decision.exposure_basis_usd
                for decision in decisions
                if decision.decision in BLOCKER_DECISIONS
            ),
            2,
        ),
        decisions_by_status=dict(sorted(status_counts.items())),
        decisions_by_category=dict(sorted(category_counts.items())),
        top_remaining_gaps=[
            {"gap": gap, "count": count} for gap, count in gap_counts.most_common(15)
        ],
        top_decisions=[decision.to_dict() for decision in decisions[:25]],
    )


def _deduped_final_metric_supported_amount(
    decisions: list[MaterialityAdjudicationDecision],
) -> float:
    direct_sum = 0.0
    grouped: dict[str, MaterialityAdjudicationDecision] = {}
    for decision in decisions:
        if decision.metric_use_status not in FINAL_METRIC_DECISIONS:
            continue
        if decision.metric_aggregation_policy == "latest_snapshot_per_metric_group":
            key = decision.metric_group_id or decision.packet_id
            current = grouped.get(key)
            if current is None or _snapshot_sort_key(decision) > _snapshot_sort_key(current):
                grouped[key] = decision
            continue
        direct_sum += decision.supported_amount_usd
    return direct_sum + sum(decision.supported_amount_usd for decision in grouped.values())


def _final_metric_group_count(decisions: list[MaterialityAdjudicationDecision]) -> int:
    direct_count = 0
    grouped: set[str] = set()
    for decision in decisions:
        if decision.metric_use_status not in FINAL_METRIC_DECISIONS:
            continue
        if decision.metric_aggregation_policy == "latest_snapshot_per_metric_group":
            grouped.add(decision.metric_group_id or decision.packet_id)
        else:
            direct_count += 1
    return direct_count + len(grouped)


def _snapshot_sort_key(decision: MaterialityAdjudicationDecision) -> tuple[str, int]:
    return (decision.metric_snapshot_date, decision.rank * -1)


def _combined_text(packet: dict[str, str], quote: str) -> str:
    return " ".join(
        [
            _field(packet, "category"),
            _field(packet, "subcategory"),
            _field(packet, "reason"),
            _field(packet, "recommended_action"),
            quote,
        ]
    ).lower()


def _is_source_backed_aggregate_obligation_snapshot(
    packet: dict[str, str],
    quote: str,
) -> bool:
    text = _combined_text(packet, quote)
    if _field(packet, "category") != "capital":
        return False
    if _float(packet.get("exposure_basis_usd")) <= 0:
        return False
    if _contains_any(
        text,
        [
            "aggregate_shelf_capacity",
            "registration statement",
            "prospectus supplement",
            "from time to time",
            "may offer",
            "may issue",
        ],
    ):
        return False
    is_aggregate_lease = _contains_any(
        text,
        ["aggregate_lease_obligation", "future lease payments", "operating lease obligations"],
    )
    if is_aggregate_lease:
        return _contains_any(
            text,
            [
                "future lease payments",
                "lease payments",
                "operating lease obligations",
                "finance lease obligations",
            ],
        ) and _contains_any(
            text,
            [
                "not yet recorded",
                "not yet commenced",
                "entered into leases",
                "consolidated balance sheets",
            ],
        )
    is_aggregate_commitment_snapshot = _contains_any(
        text,
        [
            "aggregate_commitment_snapshot",
            "purchase commitments",
            "commitments were",
            "remaining commitments",
            "total commitments",
            "aggregate commitments",
        ],
    )
    return is_aggregate_commitment_snapshot and "as of " in text


def _requires_aggregate_split(packet: dict[str, str], quote: str) -> bool:
    if _is_source_backed_aggregate_obligation_snapshot(packet, quote):
        return False
    text = _combined_text(packet, quote)
    reason = _field(packet, "reason").lower()
    explicit_specific_markers = [
        "commitment scope: specific_transaction_commitment",
        "notional context: transaction_",
        "pending contract tranche review; tranche:",
        "credit agreement",
        "facility",
        "term loan",
        "revolver",
        "bridge loan",
        "indenture",
        "entered into",
        "repaid all outstanding obligations",
    ]
    if _contains_any(reason, explicit_specific_markers):
        return False
    if _contains_any(text, ["tranche", "credit agreement", "term loan", "revolver", "indenture"]):
        return False

    explicit_non_specific_markers = [
        "commitment scope: aggregate_snapshot_non_specific",
        "commitment scope: shelf_capacity_non_specific",
        "commitment scope: candidate_requires_adjudication",
        "notional context: aggregate_lease_obligation",
        "notional context: aggregate_commitment_snapshot",
        "notional context: aggregate_shelf_capacity",
        "notional context: candidate_notional",
        "shelf capacity",
        "from time to time, we may offer",
        "may issue up to",
        "registration statement",
    ]
    if _contains_any(text, explicit_non_specific_markers):
        return True
    return "aggregate" in text


def _as_of_date(text: str) -> date | None:
    return _date_from_regex(
        text,
        r"\bas of\s+"
        r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(?P<day>\d{1,2}),\s+(?P<year>\d{4})",
    )


def _date_from_text(text: str) -> date | None:
    return _date_from_regex(
        text,
        r"\b"
        r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(?P<day>\d{1,2}),\s+(?P<year>\d{4})",
    )


def _date_from_regex(text: str, pattern: str) -> date | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    month = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }[match.group("month").lower()]
    return date(int(match.group("year")), month, int(match.group("day")))


def _contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _is_non_specific_capital_candidate_without_term_evidence(
    packet: dict[str, str],
    quote: str,
) -> bool:
    if _field(packet, "category") != "capital":
        return False
    reason = _field(packet, "reason").lower()
    if not _contains_any(
        reason,
        [
            "commitment scope: candidate_requires_adjudication",
            "notional context: candidate_notional",
            "source extraction marked requires llm adjudication",
        ],
    ):
        return False
    quote_text = quote.lower()
    term_level_markers = [
        "credit agreement",
        "facility",
        "term loan",
        "revolver",
        "indenture",
        "trustee",
        "administrative agent",
        "collateral agent",
        "lenders party thereto",
        "entered into",
        "secured",
        "unsecured",
        "collateral",
        "guarantee",
        "guarantor",
        "maturity",
        "interest rate",
        "coupon",
        "notes due",
    ]
    return not _contains_any(quote_text, term_level_markers)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


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
        return [str(item) for item in value if str(item)]
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


def _json_dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if not value or not isinstance(value, str):
        return []
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return [item for item in loaded if isinstance(item, dict)]


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(str(value).replace(",", "").replace("$", ""))
    except ValueError:
        return 0.0


def _field(row: dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()
