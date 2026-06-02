"""Automated adjudication pass over materiality-ranked packets.

This layer records source-backed decisions about whether a materiality packet is
usable as a final metric, only a valid blocker, or still needs deeper extraction.
It is intentionally conservative: source-backed blocker support is not the same
thing as approval for high-confidence report metrics.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bubble.analysis.evidence import SemanticEvidenceBucket, classify_claim_semantics

if TYPE_CHECKING:
    from collections.abc import Callable

ADJUDICATOR_ID = "codex-materiality-evidence-adjudicator-v1"

FINAL_METRIC_DECISIONS = {"approved_for_metric_use"}
BLOCKER_DECISIONS = {"supported_as_material_blocker", "needs_deeper_extraction"}
REJECT_DECISIONS = {"reject_missing_provenance", "rejected_or_deprioritized"}
MEGA_OBLIGATION_REVIEW_THRESHOLD_USD = 50_000_000_000
DIRECT_AI_OPERATOR_ENTITY_MARKERS = (
    "applied digital",
    "american bitcoin",
    "cerebras",
    "cleanspark",
    "coreweave",
    "hut 8",
    "iren",
    "mara holdings",
    "marathon digital",
    "nebius",
    "terawulf",
)
DIRECT_AI_OPERATOR_CONTEXT_MARKERS = (
    "coreweave",
    "data center",
    "data centers",
    "galaxy helios",
    "helios campus",
)
STRONG_COMMITTED_DEBT_RESELECTION_MARKERS = (
    "aggregate principal amount",
    "credit agreement",
    "credit and guaranty agreement",
    "delayed draw term loan",
    "entered into certain commitment letters",
    "entered into an indenture",
    "indenture with respect to the notes",
    "issued pursuant to",
    "lenders party",
    "notes due",
    "senior secured obligations",
    "senior unsecured notes",
    "term loan facility",
)


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
    metric_dedupe_quote: str
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
    row_context_backed_decisions: int
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


@dataclass(frozen=True)
class _SemanticQuoteCandidate:
    """Candidate replacement quote from a same-filing decision or packet snippet."""

    packet_id: str
    evidence_quote: str
    evidence_quote_refs: tuple[str, ...]
    allow_general_reselection: bool


def build_materiality_adjudication_decisions(
    data_dirs: list[str | Path] | None = None,
    *,
    adjudicated_at: str | None = None,
    max_workers: int = 32,
) -> MaterialityAdjudicationDecisionBatch:
    """Build conservative automated adjudication decisions from packet rows."""

    roots = [Path(root) for root in (data_dirs or ["data"])]
    packets = _read_rows(roots, [Path("reports") / "materiality_adjudication_packets.csv"])
    timestamp = adjudicated_at or datetime.now(UTC).isoformat()
    if len(packets) <= 1 or max_workers <= 1:
        decisions = [_adjudicate_packet(packet, adjudicated_at=timestamp) for packet in packets]
    else:
        worker_count = min(max(1, max_workers), len(packets))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(_adjudicate_packet, packet, adjudicated_at=timestamp): index
                for index, packet in enumerate(packets)
            }
            by_index: dict[int, MaterialityAdjudicationDecision] = {}
            for future in as_completed(futures):
                by_index[futures[future]] = future.result()
        decisions = [by_index[index] for index in range(len(packets))]
    decisions = _reselect_semantic_quotes(decisions, packets)
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
    ai_linkage = _ai_linkage(packet, quote)
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
        metric_dedupe_quote=quote,
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
    if gaps:
        return "needs_deeper_extraction"
    if _has_supporting_terms(packet, quote):
        return "supported_as_material_blocker"
    return "needs_deeper_extraction"


def _metric_use_status(packet: dict[str, str], decision: str, gaps: list[str]) -> str:
    if decision != "supported_as_material_blocker" or gaps:
        return "blocked_pending_extraction"
    if _field(packet, "category") not in {"capital", "contract"}:
        return "triage_only"
    if _float(packet.get("exposure_basis_usd")) <= 0:
        return "triage_only"
    return "approved_for_metric_use"


def _remaining_gaps(packet: dict[str, str], quote: str) -> list[str]:
    text = _combined_text(packet, quote)
    gaps: list[str] = []
    if not quote:
        gaps.append("local source quote not resolved")
    if _field(packet, "category") == "capital" and _looks_like_boilerplate(packet, quote):
        gaps.append("confirm final prospectus or underlying agreement terms")
    if _looks_like_resale_registration_not_committed_debt(packet, quote):
        gaps.append("distinguish resale registration from committed financing")
    gaps.extend(_currency_gaps(packet, quote))
    if _aggregate_lease_context_conflicts_with_quote(packet, quote):
        gaps.append("confirm lease obligation source rather than debt securities prospectus")
    if _looks_like_asset_or_capacity_not_debt(
        packet, quote
    ) or _looks_like_undrawn_capacity_not_debt(packet, quote):
        gaps.append("split asset, UPB, or financing-capacity disclosure from committed debt")
    semantic_gap_by_bucket = {
        SemanticEvidenceBucket.ASSET_OR_CAPACITY: (
            "split asset, UPB, or financing-capacity disclosure from committed debt"
        ),
        SemanticEvidenceBucket.EQUITY_OR_PRODUCTION: (
            "split equity, share, or mortgage-production disclosure from committed debt"
        ),
        SemanticEvidenceBucket.BOILERPLATE_ONLY: (
            "confirm source quote contains specific committed obligation terms"
        ),
    }
    semantic_bucket = classify_claim_semantics(text)
    if semantic_gap := semantic_gap_by_bucket.get(semantic_bucket):
        gaps.append(semantic_gap)
    if _requires_mega_obligation_confirmation(packet, quote):
        gaps.append("confirm mega-obligation amount is committed debt, not assets or capacity")
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
    gaps.extend(_category_gaps(packet, text, quote))
    return list(dict.fromkeys(gaps))


def _category_gaps(packet: dict[str, str], text: str, quote: str = "") -> list[str]:
    text_lower = text.lower()
    category = _field(packet, "category")
    reason_text = _field(packet, "reason").lower()
    counterparty_text = _field(packet, "counterparty").lower()
    gaps: list[str] = []
    early_gap = _early_category_gap(packet, text, text_lower)
    if early_gap is not None:
        return [early_gap] if early_gap else gaps
    if category in {"capital", "contract"}:
        if (
            not _field(packet, "counterparty")
            and not _inferred_counterparty_from_quote(quote or text)
            and not _is_note_offering_without_named_counterparty(packet, text_lower, reason_text)
        ):
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
        unsecured_scope_present = (
            unsecured_scope_present
            or _is_note_offering_without_collateral_scope(packet, text_lower, reason_text)
        )
        issuer_note_scope_present = _contains_any(
            text_lower, ["indenture", "issuer"]
        ) and _contains_any(text_lower, ["notes", "noteholders"])
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
                "bank",
                "n.a",
                "trust",
                "financial institution",
                "financial institutions",
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
        mortgage_bond_scope_present = _is_mortgage_bond_scope_present(text_lower)
        if not (
            guarantee_scope_present
            or mortgage_bond_scope_present
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
            or mortgage_bond_scope_present
            or unsecured_scope_present
            or _contains_any(text_lower, _collateral_scope_terms())
        ):
            gaps.append("determine collateral scope")
    if category == "contagion" and not _contains_any(
        text_lower, ["parent", "subsidiary", "guarantee"]
    ):
        if _looks_like_non_contract_financing_disclosure(text_lower):
            gaps.append(
                "acquire underlying agreement or debt schedule clause for term-level extraction"
            )
        elif not _has_source_backed_ownership_path(packet, text_lower):
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


def _early_category_gap(packet: dict[str, str], text: str, text_lower: str) -> str | None:
    category = _field(packet, "category")
    if category == "capital" and _is_source_backed_aggregate_obligation_snapshot(packet, text):
        return ""
    if category == "capital" and _is_non_specific_capital_candidate_without_term_evidence(
        packet, text
    ):
        return "acquire underlying agreement or debt schedule clause for term-level extraction"
    if category in {"capital", "contract"} and _looks_like_non_contract_financing_disclosure(
        text_lower
    ):
        if category == "capital":
            return "split aggregate disclosure from specific committed obligation"
        return "acquire underlying agreement or debt schedule clause for term-level extraction"
    if category == "capital" and _requires_aggregate_split(packet, text):
        # Aggregate/shelf rows are blocked on committed-obligation splitting first.
        # Do not stack term-level party/collateral/recourse gaps until a specific
        # contract-level source row is extracted.
        return ""
    return None


def _is_note_offering_without_named_counterparty(
    packet: dict[str, str],
    text_lower: str,
    reason_text: str,
) -> bool:
    has_note_markers = _has_note_offering_markers(text_lower)
    if not has_note_markers:
        return False
    if _is_facility_tranche_context(reason_text):
        return False
    has_primary_note_offering = _has_primary_note_offering_markers(text_lower)
    if _contains_any(reason_text, ["debt-like deal type: bond", "tranche: notes"]):
        return True
    if _has_lender_facility_markers(text_lower):
        return has_primary_note_offering
    # Upstream deterministic extraction sometimes mis-tags note offerings as
    # debt facilities. Keep this fallback narrow to note/indenture language.
    return _contains_any(
        text_lower,
        [
            "prospectus",
            "indenture",
            "debt securities",
            "series of debt securities",
            "aggregate principal amount",
            "notes due",
            "senior notes",
            "subordinated notes",
            "noteholders",
            "noteholder",
        ],
    )


def _is_note_offering_without_collateral_scope(
    packet: dict[str, str],
    text_lower: str,
    reason_text: str,
) -> bool:
    if _contains_any(text_lower, ["secured notes", "collateral", "security interest", "pledge"]):
        return False
    if _contains_any(
        text_lower,
        [
            "unsecured",
            "senior unsecured",
            "unsecured obligations",
            "none of which was secured debt",
            "without collateral",
            "structurally senior",
        ],
    ):
        return True
    if _has_lender_facility_markers(text_lower):
        return False
    if not _is_note_offering_without_named_counterparty(packet, text_lower, reason_text):
        return False
    if _contains_any(text_lower, ["senior notes due", "notes due"]) and _contains_any(
        text_lower,
        ["prospectus", "offering", "aggregate principal amount"],
    ):
        return True
    return _contains_any(text_lower, ["indenture"]) and _contains_any(
        text_lower, ["notes", "noteholders"]
    )


def _looks_like_non_contract_financing_disclosure(text: str) -> bool:
    if _contains_any(
        text,
        [
            "entered into a credit agreement",
            "credit agreement dated",
            "administrative agent",
            "collateral agent",
            "lenders party thereto",
            "term loan",
            "revolving credit",
            "bridge loan",
            "facility agreement",
            "as trustee",
        ],
    ):
        return False
    generic_markers = [
        "the securities may be offered by us or by selling security holders",
        "those terms may include",
        "common shares",
        "ordinary shares",
        "equity distribution agreement",
        "controlled equity offering",
        "purchase contracts",
        "warrants",
        "depositary shares",
        "before you invest in our common stock",
        "investment objective is to generate current income",
        "capital appreciation",
        "estimated commission with respect to the fund's common shares",
        "terms of the debt securities will include",
        "dtc also facilitates",
        "post-trade settlement",
        "book-entry transfers and pledges",
    ]
    return _contains_any(text, generic_markers)


def _has_note_offering_markers(text: str) -> bool:
    return _contains_any(
        text,
        [
            "prospectus",
            "notes due",
            "senior notes",
            "subordinated notes",
            "debt securities",
            "indenture",
            "noteholders",
            "noteholder",
            "aggregate principal amount",
            "series of debt securities",
        ],
    )


def _has_lender_facility_markers(text: str) -> bool:
    return _contains_any(
        text,
        [
            "credit agreement",
            "administrative agent",
            "collateral agent",
            "facility agent",
            "lenders party thereto",
            "lenders named therein",
            "revolving credit",
            "term loan",
            "bridge loan",
            "delayed draw term loan",
            "syndicated facility",
        ],
    )


def _is_facility_tranche_context(reason_text: str) -> bool:
    return _contains_any(
        reason_text,
        [
            "tranche: term loan",
            "tranche: revolving",
            "tranche: revolver",
            "tranche: credit facility",
            "tranche: bridge loan",
            "tranche: delayed draw",
        ],
    )


def _has_primary_note_offering_markers(text: str) -> bool:
    if not _contains_any(text, ["notes", "bonds", "debentures"]):
        return False
    if re.search(
        r"\b(?:senior|secured|unsecured|first lien|mortgage|collateral trust)?\s*"
        r"(?:notes|bonds|debentures)\s+due\s+\d{4}\b",
        text,
    ):
        return True
    if re.search(
        r"\baggregate principal amount of [^.;]{0,80}?(?:notes|bonds|debentures)\b",
        text,
    ):
        return True
    if re.search(
        r"\$\s*[\d,.]+(?:\s*(?:million|billion|trillion))?\s+of\s+"
        r"(?:(?:senior|secured|unsecured|first lien|second lien|subordinated|mortgage|"
        r"collateral trust)\s+)*(?:notes|bonds|debentures)\b",
        text,
    ):
        return True
    return _contains_any(
        text,
        [
            "notes were issued",
            "notes will be issued",
            "notes were priced",
            "notes will be guaranteed",
            "notes were guaranteed",
            "commenced an offering",
            "offering of notes",
            "issued under an indenture",
        ],
    )


def _has_source_backed_ownership_path(packet: dict[str, str], text: str) -> bool:
    reason = _field(packet, "reason").lower()
    if not _contains_any(
        reason, ["ownership expanded contagion path", "ownership/control path depth"]
    ):
        return False
    source_uris = " ".join(_json_list(packet.get("source_uris"))).lower()
    has_sec = "sec.gov" in source_uris
    has_lei = "leidata.gleif.org" in source_uris
    has_path_depth = _contains_any(
        reason, ["ownership/control path depth", "contract relationship:"]
    )
    return has_sec and has_lei and has_path_depth


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
    row_context_backed = any(
        str(snippet.get("document_id") or "").strip().lower() == "review_queue_row_context"
        for snippet in evidence_snippets
    )
    if quote:
        if row_context_backed:
            return "row_context_backed"
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
    instrument_key = _metric_source_instrument_key(packet)
    if instrument_key:
        amount_key = _metric_amount_key(_float(packet.get("exposure_basis_usd")))
        return f"source-instrument:{instrument_key}:amount:{amount_key}"
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
    if _metric_source_instrument_key(packet):
        return "max_amount_per_source_instrument"
    return "sum_distinct_metric_rows"


def _metric_source_instrument_key(packet: dict[str, str]) -> str:
    content_hashes = sorted(
        {
            value
            for value in (
                _json_list(packet.get("content_hashes")) or [_field(packet, "content_hash")]
            )
            if value
        }
    )
    if content_hashes:
        return "hashes:" + ",".join(content_hashes)
    source_uris = sorted(
        {
            value
            for value in (_json_list(packet.get("source_uris")) or [_field(packet, "source_uri")])
            if value
        }
    )
    if source_uris:
        return "uris:" + ",".join(source_uris)
    return ""


def _metric_amount_key(amount: float) -> str:
    return str(round(amount))


def _ai_linkage(packet: dict[str, str], quote: str) -> str:
    relevance = _field(packet, "ecosystem_relevance")
    direct_relevance = {
        "direct_ai_infra": "direct",
        "physical_execution": "physical",
        "compute_economics": "compute",
    }.get(relevance)
    if direct_relevance:
        return direct_relevance
    if _is_direct_ai_operator_entity(_field(packet, "entity")):
        return "direct"
    if _has_direct_ai_operator_context(packet, quote):
        return "direct"
    if relevance == "watchlist_entity":
        return "watchlist"
    return "not_established"


def _is_direct_ai_operator_entity(entity: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", " ", entity.lower()).strip()
    padded = f" {normalized} "
    return any(f" {marker} " in padded for marker in DIRECT_AI_OPERATOR_ENTITY_MARKERS)


def _has_direct_ai_operator_context(packet: dict[str, str], quote: str) -> bool:
    entity = _field(packet, "entity").lower()
    if "galaxy digital" not in entity and "galaxy helios" not in entity:
        return False
    text = _combined_text(packet, quote).lower()
    return _contains_any(text, list(DIRECT_AI_OPERATOR_CONTEXT_MARKERS))


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
    candidate = _counterparty_from_named_role_patterns(quote)
    if candidate:
        return candidate
    candidate = _counterparty_from_lenders_clause(quote)
    if candidate:
        return candidate
    quote_lower = quote.lower()
    if ", as" in quote_lower and ("agent" in quote_lower or "trustee" in quote_lower):
        return _counterparty_from_agent_or_trustee_clause(quote)
    return ""


def _counterparty_from_named_role_patterns(quote: str) -> str:
    agent_role = (
        r"(?:(?:administrative|collateral|facility|syndication)"
        r"(?:\s+and\s+(?:administrative|collateral|facility|syndication))?\s+)?agent"
    )
    financial_name = (
        r"[A-Z][A-Za-z0-9 .,&'()/-]{2,180}?"
        r"(?:Bank(?:,?\s*N\.A\.?)?|N\.A\.?|Securities(?:\s+LLC|,\s+LLC)?|"
        r"Capital Markets LLC|Trust Company|National Association|"
        r"AG(?:,\s+[A-Za-z ]+ Branch)?|PLC|LLC|Inc\.?|Corp(?:oration)?)"
    )
    underwriter_names = rf"{financial_name}(?:\s*(?:,|and)\s*{financial_name})*"
    candidate = _counterparty_from_defined_borrower_label(quote, financial_name)
    if candidate:
        return candidate
    quote_lower = quote.lower()
    patterns: list[str] = []
    if "commitment parties" in quote_lower and (
        "commitment letter" in quote_lower or "financing commitment" in quote_lower
    ):
        patterns.append(
            r"\b(?:debt commitment letter|commitment letter|financing commitment)\b[\s\S]{0,180}?\bwith\s+(?P<name>[^()]{2,320}?)\s*\(\s*(?:(?:together|collectively)\s*,?\s*)?(?:the\s+)?[\"'“”]?Commitment Parties[\"'“”]?\s*\)\s*,?\s*pursuant to which\b"
        )
    if "agent" in quote_lower:
        patterns.extend(
            [
                rf"\bamong\b[\s\S]{{2,360}}?\bas\s+borrower\s*,\s*(?P<name>{financial_name})\s*,\s*as\s+(?:the\s+)?{agent_role}\b",
                rf"(?P<name>{financial_name})\s*,\s*as\s+(?:the\s+)?{agent_role}\b",
                rf"\bwith\s+(?P<name>[A-Z][A-Za-z0-9 .,&'/-]{{2,220}}?)\s*,?\s+(?:as|serving as)\s+(?:the\s+)?{agent_role}\b",
            ]
        )
    if _contains_any(quote_lower, ["arranger", "bookrunner", "placement agent"]):
        patterns.append(
            r"(?P<name>[A-Z][^.;]{2,220}?)\s+(?:served as|as)\s+(?:joint\s+)?(?:lead\s+)?(?:arrangers?|bookrunners?|placement agents?)\b"
        )
    if "representatives of the several" in quote_lower:
        patterns.extend(
            [
                r"\bwith\s+(?P<name>[A-Z][^;]{2,320}?)\s*,?\s+as\s+representatives?\s+of\s+the\s+several\s+(?:underwriters|initial purchasers)\b",
                rf"(?P<name>{underwriter_names})\s*,?\s+as\s+representatives?\s+of\s+the\s+several\s+(?:underwriters|initial purchasers)\b",
                r"(?P<name>[A-Z][^;]{2,320}?)\s*,?\s+acting\s+for\s+themselves\s+and\s+as\s+representatives?\s+of\s+the\s+several\s+underwriters\b",
            ]
        )
    if "joint book-running managers" in quote_lower:
        patterns.append(
            r"(?P<name>[A-Z][^.;]{2,260}?)\s+(?:are|were)\s+acting\s+as\s+joint\s+book-running\s+managers\b"
        )
    if "trustee" in quote_lower:
        patterns.append(
            r"\btrustee\s+(?P<name>[A-Z][A-Za-z0-9 .,&'/-]{2,180}(?:National Association|Trust Company|N\.A\.?|LLC|Inc\.?|Bank))\b"
        )
    for pattern in patterns:
        match = re.search(pattern, quote, flags=re.IGNORECASE)
        if not match:
            continue
        candidate = _normalize_counterparty_candidate(match.group("name"))
        if candidate and _looks_like_counterparty_name(candidate):
            return candidate
    return ""


def _counterparty_from_defined_borrower_label(quote: str, financial_name: str) -> str:
    label = re.search(
        r"\(\s*(?:the\s+)?[\"'“”]?(?:Initial\s+)?Borrower[\"'“”]?\s*\)",
        quote,
        flags=re.IGNORECASE,
    )
    if not label:
        return ""
    prefix = quote[max(0, label.start() - 220) : label.start()]
    prefix = re.split(r"[.;]\s+", prefix)[-1]
    tail = re.split(
        r"\)\s*,|\bparent\s+company\s+to\s+|\b(?:to|by|among|with)\s+",
        prefix.strip(" ,"),
        flags=re.IGNORECASE,
    )[-1].strip(" ,")
    match = re.search(rf"(?P<name>{financial_name})\s*$", tail, flags=re.IGNORECASE)
    if not match:
        return ""
    candidate = _normalize_counterparty_candidate(match.group("name"))
    return candidate if candidate and _looks_like_counterparty_name(candidate) else ""


def _counterparty_from_lenders_clause(quote: str) -> str:
    lenders_clause = re.search(
        r"(?:the lenders named therein|the lenders party thereto)\s*,\s*(?P<name>[^;]{2,180}?)\s*,\s*as\s+(?:the\s+)?(?:administrative|collateral|facility|syndication)\s+agent\b",
        quote,
        flags=re.IGNORECASE,
    )
    if lenders_clause:
        candidate = _normalize_counterparty_candidate(lenders_clause.group("name"))
        if candidate:
            return candidate
    return ""


def _counterparty_from_agent_or_trustee_clause(quote: str) -> str:
    role_clause = re.search(
        r",\s*as\s+(?:the\s+)?(?:(?:(?:administrative|collateral|facility|syndication)(?:\s+and\s+(?:administrative|collateral|facility|syndication))?\s+)?agent|trustee)\b",
        quote,
        flags=re.IGNORECASE,
    )
    if not role_clause:
        return ""

    prefix = quote[max(0, role_clause.start() - 320) : role_clause.start()]
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
    candidate = re.sub(
        r"^.*\bamong\s+the\s+(?:company|issuer)\s+and\s+",
        "",
        candidate,
        flags=re.IGNORECASE,
    )
    candidate = re.sub(
        r"^.*\bamong\s+the\s+(?:company|issuer)\s*,\s*(?:the\s+)?(?:lenders\s+named\s+therein|lenders\s+party\s+thereto)\s*,\s*",
        "",
        candidate,
        flags=re.IGNORECASE,
    )
    candidate = re.sub(
        r"^.*\b(?:lenders|banks|guarantors|subsidiary guarantors)[^,;]{0,160}?\band\s+",
        "",
        candidate,
        flags=re.IGNORECASE,
    )
    candidate = re.sub(r"\s*,\s*as\s+.*$", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(
        r"\s*,?\s*acting\s+for\s+themselves\s+and\s+as\s+.*$",
        "",
        candidate,
        flags=re.IGNORECASE,
    )
    candidate = re.sub(
        r"\s+(?:are|were)\s+acting\s+as\s+.*$",
        "",
        candidate,
        flags=re.IGNORECASE,
    )
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
            "financial group",
            "morgan stanley",
            "goldman sachs",
            "citigroup",
            "jpmorgan",
            "mufg",
            "mitsubishi ufj",
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
            "bond",
            "bonds",
            "mortgage bond",
            "mortgage bonds",
            "lease",
            "obligation",
            "commitment",
            "commitments",
        ],
        "contract": ["collateral", "guarantor", "interest", "maturity", "tranche"],
        "contagion": ["guarantee", "collateral", "parent", "subsidiary", "non-recourse"],
        "physical": ["queue", "permit", "interconnection", "capacity", "mw"],
        "compute": ["gpu", "depreciation", "useful life", "rental", "supply"],
        "weak_link": [
            "maturity",
            "interest",
            "debt",
            "lease",
            "credit",
            "notes",
            "queue",
            "permit",
            "interconnection",
            "capacity",
            "mw",
            "construction",
            "in-service",
            "planned",
        ],
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
        ],
    )


def _looks_like_resale_registration_not_committed_debt(
    packet: dict[str, str],
    quote: str,
) -> bool:
    if _field(packet, "category") not in {"capital", "contract"}:
        return False
    text = _combined_text(packet, quote)
    if not _has_resale_registration_markers(text):
        return False
    return not (
        _has_primary_note_offering_markers(text) or _has_lender_facility_markers(text)
    )


def _has_resale_registration_markers(text: str) -> bool:
    return _contains_any(
        text,
        [
            "will not receive any proceeds",
            "selling securityholder",
            "selling security holder",
            "selling stockholder",
            "for the account of the selling",
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
    best_snippet = max(text_snippets, key=lambda item: _quote_score(item[1], terms))
    snippet_meta = best_snippet[0]
    snippet_texts = [text for _, text in text_snippets]
    best_text = best_snippet[1]
    if _should_limit_quote_to_committed_financing_snippet(packet, best_text, snippet_texts):
        quote = _combined_best_quote([best_text], terms)
    else:
        quote = _combined_best_quote(snippet_texts, terms)
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


def _should_limit_quote_to_committed_financing_snippet(
    packet: dict[str, str],
    best_text: str,
    snippets: list[str],
) -> bool:
    if _field(packet, "category") not in {"capital", "contract"}:
        return False
    lowered_best = best_text.lower()
    if not (
        _has_primary_note_offering_markers(lowered_best)
        or _has_lender_facility_markers(lowered_best)
    ):
        return False
    return any(
        _has_resale_registration_markers(snippet.lower())
        and not (
            _has_primary_note_offering_markers(snippet.lower())
            or _has_lender_facility_markers(snippet.lower())
        )
        for snippet in snippets
        if snippet != best_text
    )


def _combined_best_quote(snippets: list[str], terms: list[str]) -> str:
    role_clause = _best_clause_from_snippets(snippets, terms, _best_named_counterparty_role_clause)
    scope_clause = _best_clause_from_snippets(snippets, terms, _best_scope_clause)
    best_sentence = _best_sentence(
        max(snippets, key=lambda snippet: _quote_score(snippet, terms)), terms
    )
    clauses = [clause for clause in [role_clause, scope_clause, best_sentence] if clause]
    combined: list[str] = []
    seen: set[str] = set()
    for clause in clauses:
        key = clause[:160].lower()
        if key in seen:
            continue
        seen.add(key)
        combined.append(clause)
    quote = " ".join(combined).strip()
    if len(quote) <= 650:
        return quote
    if role_clause and scope_clause:
        role_part = _trim_window_around_terms(
            role_clause, _named_counterparty_role_markers(), max_len=315
        )
        scope_part = _trim_window_around_terms(scope_clause, _scope_quote_terms(), max_len=315)
        return f"{role_part} {scope_part}"[:650].strip()
    return quote[:650].strip()


def _best_clause_from_snippets(
    snippets: list[str],
    terms: list[str],
    clause_picker: Callable[[list[str], list[str]], str],
) -> str:
    clauses: list[str] = []
    for snippet in snippets:
        parts = [part.strip() for part in re.split(r"(?<=[.;:])\s+", snippet) if part.strip()]
        clause = clause_picker(parts, terms)
        if clause:
            clauses.append(clause)
    if not clauses:
        return ""
    return max(clauses, key=lambda clause: _quote_score(clause.lower(), terms))


def _best_sentence(text: str, terms: list[str]) -> str:
    if not text:
        return ""
    parts = [part.strip() for part in re.split(r"(?<=[.;:])\s+", text) if part.strip()]
    if not parts:
        return text
    role_clause = _best_named_counterparty_role_clause(parts, terms)
    if role_clause:
        return role_clause
    scope_clause = _best_scope_clause(parts, terms)
    if scope_clause:
        return scope_clause
    sentence = max(parts, key=lambda part: _quote_score(part.lower(), terms))
    if len(sentence) >= 120:
        return sentence
    index = parts.index(sentence)
    neighbors = parts[max(0, index - 1) : index + 2]
    return " ".join(neighbors)


def _best_named_counterparty_role_clause(parts: list[str], terms: list[str]) -> str:
    role_windows: list[str] = []
    for index, part in enumerate(parts):
        if not _contains_any(part.lower(), _named_counterparty_role_markers()):
            continue
        window = " ".join(parts[max(0, index - 2) : index + 2]).strip()
        if _has_named_counterparty_role_evidence(window.lower()):
            role_windows.append(window)
    if not role_windows:
        return ""
    return max(role_windows, key=lambda window: _quote_score(window.lower(), terms))[:650].strip()


def _best_scope_clause(parts: list[str], terms: list[str]) -> str:
    scope_windows: list[str] = []
    for index, part in enumerate(parts):
        if not _contains_any(part.lower(), _scope_quote_terms()):
            continue
        window = " ".join(parts[max(0, index - 1) : index + 2]).strip()
        if _has_financing_scope_evidence(window.lower()):
            scope_windows.append(window)
    if not scope_windows:
        return ""
    window = max(scope_windows, key=lambda value: _quote_score(value.lower(), terms))
    return _trim_window_around_terms(window, _scope_quote_terms(), max_len=650)


def _trim_window_around_terms(text: str, terms: list[str], max_len: int) -> str:
    if len(text) <= max_len:
        return text.strip()
    lowered = text.lower()
    positions = [index for term in terms if term and (index := lowered.find(term.lower())) >= 0]
    if not positions:
        return text[:max_len].strip()
    start = max(0, min(positions) - 180)
    if start + max_len > len(text):
        start = max(0, len(text) - max_len)
    return text[start : start + max_len].strip()


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
    if _field(packet, "category") in {"capital", "contract"}:
        terms.extend(_scope_quote_terms())
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


def _scope_quote_terms() -> list[str]:
    return [
        "senior unsecured",
        "unsecured",
        "unsecured indebtedness",
        "unsecured obligations",
        "non-recourse",
        "non recourse",
        "recourse",
        "guarantee",
        "guarantees",
        "guarantor",
        "guarantors",
        "collateral",
        "collateral agreement",
        "collateral document",
        "collateral documents",
        "secured by",
        "senior secured",
        "secured",
        "security interest",
        "security agreement",
        "security document",
        "security documents",
        "loan and security agreement",
        "first lien",
        "first-lien",
        "first lien notes",
        "first-lien notes",
        "second lien",
        "second-lien",
        "second lien notes",
        "second-lien notes",
        "first mortgage bond",
        "first mortgage bonds",
        "collateral trust mortgage bond",
        "collateral trust mortgage bonds",
        "first and refunding mortgage bond",
        "first and refunding mortgage bonds",
        "asset-based revolving credit agreement",
        "asset based revolving credit agreement",
        "borrowing base",
        "pledge",
        "pledged",
        "gpu-backed",
        "gpu backed",
        "asset-backed",
        "asset backed",
        "infrastructure-backed",
        "infrastructure backed",
    ]


def _collateral_scope_terms() -> list[str]:
    return [
        "collateral",
        "collateral agreement",
        "collateral document",
        "collateral documents",
        "secured",
        "security interest",
        "security agreement",
        "security document",
        "security documents",
        "loan and security agreement",
        "first mortgage bond",
        "first mortgage bonds",
        "collateral trust mortgage bond",
        "collateral trust mortgage bonds",
        "first and refunding mortgage bond",
        "first and refunding mortgage bonds",
        "asset-based revolving credit agreement",
        "asset based revolving credit agreement",
        "borrowing base",
        "pledge",
        "pledged",
        "gpu-backed",
        "gpu backed",
        "asset-backed",
        "asset backed",
        "infrastructure-backed",
        "infrastructure backed",
    ]


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


def _is_mortgage_bond_scope_present(text: str) -> bool:
    return _contains_any(
        text,
        [
            "first mortgage bond",
            "first mortgage bonds",
            "collateral trust mortgage bond",
            "collateral trust mortgage bonds",
            "first and refunding mortgage bond",
            "first and refunding mortgage bonds",
        ],
    )


def _quote_score(text: str, terms: list[str]) -> int:
    lowered = text.lower()
    score = sum(1 for term in terms if term in lowered)
    if _has_named_counterparty_role_evidence(lowered):
        score += 10
    if _has_financing_scope_evidence(lowered):
        score += 8
    return score


def _has_named_counterparty_role_evidence(text: str) -> bool:
    if not _contains_any(text, _named_counterparty_role_markers()):
        return False
    return _contains_any(
        text,
        [
            "bank",
            "trust",
            "capital",
            "credit",
            "securities",
            "morgan stanley",
            "goldman",
            "citigroup",
            "jpmorgan",
            "barclays",
            "mufg",
            "mitsubishi",
            "wells fargo",
            "bofa",
            "deutsche bank",
            "mizuho",
            "lenders named",
            "lenders party",
            "underwriter",
            "underwriters",
        ],
    )


def _has_financing_scope_evidence(text: str) -> bool:
    if not _contains_any(text, _scope_quote_terms()):
        return False
    return _contains_any(
        text,
        [
            "credit agreement",
            "facility",
            "financing",
            "loan",
            "notes",
            "debt",
            "indenture",
            "indebtedness",
            "obligation",
            "obligations",
            "collateral",
            "guarantor",
            "guarantors",
        ],
    )


def _named_counterparty_role_markers() -> list[str]:
    return [
        "administrative and collateral agent",
        "administrative agent",
        "collateral agent",
        "facility agent",
        "syndication agent",
        "lead arranger",
        "lead arrangers",
        "bookrunner",
        "bookrunners",
        "commitment parties",
        "initial purchasers",
        "underwriters",
        "book-running managers",
        "joint book-running managers",
        "placement agent",
        "placement agents",
        "trustee",
    ]


def _clean_snippet_text(value: str) -> str:
    if not value:
        return ""
    if value.lstrip().startswith("PK\x03\x04"):
        return ""
    control_chars = sum(1 for char in value if ord(char) < 32 and char not in {"\t", "\n", "\r"})
    if control_chars / max(len(value), 1) > 0.02:
        return ""
    return _normalize(value)


def _reselect_semantic_quotes(
    decisions: list[MaterialityAdjudicationDecision],
    packets: list[dict[str, str]] | None = None,
) -> list[MaterialityAdjudicationDecision]:
    """Replace weak approved quotes with stronger same-filing committed-debt clauses."""

    packet_by_id = {_field(packet, "packet_id"): packet for packet in packets or []}
    by_hash_and_entity: dict[tuple[str, str], list[_SemanticQuoteCandidate]] = {}
    for decision in decisions:
        entity_key = _entity_reselection_key(decision.entity)
        if not entity_key:
            continue
        candidate = _SemanticQuoteCandidate(
            packet_id=decision.packet_id,
            evidence_quote=decision.evidence_quote,
            evidence_quote_refs=decision.evidence_quote_refs,
            allow_general_reselection=True,
        )
        for content_hash in decision.content_hashes or (decision.content_hash,):
            if content_hash:
                by_hash_and_entity.setdefault((content_hash, entity_key), []).append(candidate)
    for packet in packets or []:
        entity_key = _entity_reselection_key(_field(packet, "entity"))
        if not entity_key:
            continue
        for snippet in _json_dicts(packet.get("evidence_snippets")):
            quote = _clean_snippet_text(str(snippet.get("snippet") or ""))
            content_hash = str(snippet.get("content_hash") or _field(packet, "content_hash"))
            if not quote or not content_hash:
                continue
            refs = tuple(
                value
                for value in [
                    str(snippet.get("source_uri") or _field(packet, "source_uri")),
                    content_hash,
                    str(snippet.get("document_id") or ""),
                ]
                if value
            )
            candidate = _SemanticQuoteCandidate(
                packet_id=_field(packet, "packet_id"),
                evidence_quote=quote,
                evidence_quote_refs=refs,
                allow_general_reselection=False,
            )
            by_hash_and_entity.setdefault((content_hash, entity_key), []).append(candidate)

    reselected: list[MaterialityAdjudicationDecision] = []
    for decision in decisions:
        replacement = _semantic_quote_reselection_candidate(
            decision,
            by_hash_and_entity,
            packet_by_id.get(decision.packet_id),
        )
        reselected.append(replacement or decision)
    return reselected


def _semantic_quote_reselection_candidate(
    decision: MaterialityAdjudicationDecision,
    by_hash_and_entity: dict[tuple[str, str], list[_SemanticQuoteCandidate]],
    packet: dict[str, str] | None,
) -> MaterialityAdjudicationDecision | None:
    if decision.metric_use_status != "approved_for_metric_use":
        return None
    semantic_bucket = _report_semantic_bucket(decision)
    needs_exact_amount_quote = not _exact_amount_committed_reselection_quote(
        decision.evidence_quote,
        decision.exposure_basis_usd,
    )
    if semantic_bucket != SemanticEvidenceBucket.INDETERMINATE and not needs_exact_amount_quote:
        return None

    entity_key = _entity_reselection_key(decision.entity)
    if not entity_key:
        return None

    terms = _decision_quote_terms(decision)
    current_score = _quote_score(decision.evidence_quote, terms)
    candidates: list[tuple[_SemanticQuoteCandidate, str]] = []
    seen_candidates: set[tuple[str, tuple[str, ...], str]] = set()
    for content_hash in decision.content_hashes or (decision.content_hash,):
        for candidate in by_hash_and_entity.get((content_hash, entity_key), []):
            if candidate.packet_id == decision.packet_id:
                continue
            candidate_key = (
                candidate.packet_id,
                candidate.evidence_quote_refs,
                candidate.evidence_quote[:160],
            )
            if candidate_key in seen_candidates:
                continue
            seen_candidates.add(candidate_key)
            replacement_quote = _semantic_reselection_quote(
                candidate.evidence_quote,
                terms,
                current_score,
                decision.exposure_basis_usd,
                allow_general_reselection=(
                    candidate.allow_general_reselection
                    and semantic_bucket == SemanticEvidenceBucket.INDETERMINATE
                ),
            )
            if replacement_quote:
                candidates.append((candidate, replacement_quote))
    if not candidates:
        return None

    best, best_quote = max(
        candidates,
        key=lambda item: _quote_score(item[1], terms),
    )
    reselect_reason = (
        "because the original quote was semantically indeterminate"
        if semantic_bucket == SemanticEvidenceBucket.INDETERMINATE
        else "because the original quote lacked exact amount committed-instrument text"
    )
    reselect_note = (
        f"Evidence quote reselected from same source filing "
        f"packet {best.packet_id} {reselect_reason}."
    )
    rationale = f"{decision.rationale} {reselect_note}"
    if packet is not None:
        return _replace_decision_quote_disposition(
            decision,
            packet,
            best_quote,
            best.evidence_quote_refs,
            reselect_note,
        )
    return replace(
        decision,
        evidence_quote=best_quote,
        evidence_quote_refs=best.evidence_quote_refs,
        rationale=rationale,
    )


def _replace_decision_quote_disposition(
    decision: MaterialityAdjudicationDecision,
    packet: dict[str, str],
    quote: str,
    quote_refs: tuple[str, ...],
    reselect_note: str,
) -> MaterialityAdjudicationDecision:
    evidence_snippets = _json_dicts(packet.get("evidence_snippets"))
    source_support = _source_support(packet, quote, evidence_snippets)
    gaps = _remaining_gaps(packet, quote)
    decision_status = _decision(packet, quote, gaps, source_support)
    metric_use_status = _metric_use_status(packet, decision_status, gaps)
    exposure_basis = _float(packet.get("exposure_basis_usd"))
    supported_amount = (
        exposure_basis if metric_use_status == "approved_for_metric_use" else 0.0
    )
    metric_group_id = (
        decision.metric_group_id
        if metric_use_status == decision.metric_use_status == "approved_for_metric_use"
        else _metric_group_id(packet, quote, metric_use_status)
    )
    metric_snapshot_date = (
        decision.metric_snapshot_date
        if metric_use_status == decision.metric_use_status == "approved_for_metric_use"
        else _metric_snapshot_date(packet, quote, metric_use_status)
    )
    metric_aggregation_policy = (
        decision.metric_aggregation_policy
        if metric_use_status == decision.metric_use_status == "approved_for_metric_use"
        else _metric_aggregation_policy(packet, quote, metric_use_status)
    )
    rationale = (
        f"{_rationale(packet, quote, decision_status, metric_use_status, source_support, gaps)} "
        f"{reselect_note}"
    )
    return replace(
        decision,
        decision=decision_status,
        metric_use_status=metric_use_status,
        source_support=source_support,
        confidence=_confidence(decision_status, source_support, gaps),
        supported_amount_usd=round(supported_amount, 2),
        metric_group_id=metric_group_id,
        metric_snapshot_date=metric_snapshot_date,
        metric_aggregation_policy=metric_aggregation_policy,
        duplicate_or_aggregate=_duplicate_or_aggregate(packet, quote),
        ai_data_center_linkage=_ai_linkage(packet, quote),
        risk_bearer=_risk_bearer(packet, quote, gaps),
        remaining_gap=" | ".join(gaps),
        required_next_extraction=_required_next_extraction(packet, quote, gaps),
        evidence_quote=quote,
        evidence_quote_refs=quote_refs,
        rationale=rationale,
    )


def _semantic_reselection_quote(
    quote: str,
    terms: list[str],
    current_score: int,
    amount: float,
    *,
    allow_general_reselection: bool,
) -> str:
    if exact_quote := _exact_amount_committed_reselection_quote(quote, amount):
        return exact_quote
    if not allow_general_reselection:
        return ""
    if classify_claim_semantics(quote) != SemanticEvidenceBucket.COMMITTED_DEBT:
        return ""
    quote_lower = quote.lower()
    if not _contains_any(quote_lower, list(STRONG_COMMITTED_DEBT_RESELECTION_MARKERS)):
        return ""
    return quote if _quote_score(quote, terms) > current_score else ""


def _exact_amount_committed_reselection_quote(quote: str, amount: float) -> str:
    if amount <= 0:
        return ""
    for candidate_amount, amount_span in _usd_nominal_amount_matches(quote):
        if not _amounts_close(amount, candidate_amount, tolerance=0.02):
            continue
        if _exact_amount_reselection_blocked_context(quote, amount_span):
            continue
        if _has_committed_instrument_phrase_near_amount(quote, amount_span):
            return _trim_window_around_span(quote, amount_span, max_len=650)
    return ""


def _exact_amount_reselection_blocked_context(
    text: str,
    amount_span: tuple[int, int],
) -> bool:
    context = text[max(0, amount_span[0] - 140) : amount_span[1] + 180].lower()
    blocked_patterns = [
        r"\bability\s+to\s+borrow\b",
        r"\bborrow\s+up\s+to\b",
        r"\bup\s+to\s+an\s+additional\b",
        r"\bavailable\s+under\b",
        r"\bavailability\s+under\b",
        r"\bunused\b",
        r"\bunborrowed\b",
        r"\bcommercial\s+paper\s+program\b",
    ]
    return any(re.search(pattern, context) for pattern in blocked_patterns)


def _has_committed_instrument_phrase_near_amount(
    text: str,
    amount_span: tuple[int, int],
    *,
    max_distance: int = 35,
) -> bool:
    phrase_patterns = [
        r"\baggregate\s+principal\s+amount\b",
        r"\bnotes?\s+due\s+\d{4}\b",
        r"\bsenior\s+(?:secured|unsecured)\s+notes?\b",
        r"\brevolving\s+credit\s+facility\b",
        r"\bdelayed\s+draw\s+term\s+loan\s+facility\b",
        r"\bterm\s+loan\s+facility\b",
    ]
    lowered = text.lower()
    for pattern in phrase_patterns:
        for match in re.finditer(pattern, lowered):
            if _span_distance(amount_span, match.span()) <= max_distance:
                return True
    return False


def _span_distance(left: tuple[int, int], right: tuple[int, int]) -> int:
    if left[1] < right[0]:
        return right[0] - left[1]
    if right[1] < left[0]:
        return left[0] - right[1]
    return 0


def _trim_window_around_span(
    text: str,
    span: tuple[int, int],
    *,
    max_len: int,
) -> str:
    if len(text) <= max_len:
        return text.strip()
    center = (span[0] + span[1]) // 2
    start = max(0, center - (max_len // 2))
    if start + max_len > len(text):
        start = max(0, len(text) - max_len)
    return text[start : start + max_len].strip()


def _report_semantic_bucket(decision: MaterialityAdjudicationDecision) -> SemanticEvidenceBucket:
    text = " ".join(
        value
        for value in (decision.evidence_quote, decision.packet_reason, decision.rationale)
        if value
    )
    return classify_claim_semantics(text)


def _decision_quote_terms(decision: MaterialityAdjudicationDecision) -> list[str]:
    return _quote_terms(
        {
            "entity": decision.entity,
            "counterparty": decision.counterparty,
            "category": decision.category,
            "subcategory": decision.subcategory,
            "reason": decision.packet_reason,
            "exposure_basis_usd": str(decision.exposure_basis_usd),
        }
    )


def _entity_reselection_key(entity: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", entity.lower()).strip("-")


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
        row_context_backed_decisions=sum(
            decision.source_support == "row_context_backed" for decision in decisions
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
    return sum(
        decision.supported_amount_usd
        for decision in _final_metric_representative_decisions(decisions)
    )


def _final_metric_group_count(decisions: list[MaterialityAdjudicationDecision]) -> int:
    return len(_final_metric_representative_decisions(decisions))


def _final_metric_representative_decisions(
    decisions: list[MaterialityAdjudicationDecision],
) -> list[MaterialityAdjudicationDecision]:
    direct: list[MaterialityAdjudicationDecision] = []
    grouped: dict[str, MaterialityAdjudicationDecision] = {}
    for decision in decisions:
        if decision.metric_use_status not in FINAL_METRIC_DECISIONS:
            continue
        if decision.metric_aggregation_policy == "latest_snapshot_per_metric_group":
            group_key = decision.metric_group_id or decision.packet_id
            current = grouped.get(group_key)
            if current is None or _snapshot_sort_key(decision) > _snapshot_sort_key(current):
                grouped[group_key] = decision
            continue
        if decision.metric_aggregation_policy == "max_amount_per_source_instrument":
            group_key = decision.metric_group_id or decision.packet_id
            current = grouped.get(group_key)
            if current is None or decision.supported_amount_usd > current.supported_amount_usd:
                grouped[group_key] = decision
            continue
        direct.append(decision)
    representatives = [*direct, *grouped.values()]
    representatives = _collapse_metric_representatives(
        representatives,
        key_fn=_source_hash_metric_dedupe_key,
    )
    representatives = _collapse_metric_representatives(
        representatives,
        key_fn=_economic_quote_metric_dedupe_key,
    )
    representatives = _collapse_metric_representatives(
        representatives,
        key_fn=_economic_obligation_metric_dedupe_key,
    )
    representatives = _collapse_metric_representatives(
        representatives,
        key_fn=_accession_amount_metric_dedupe_key,
    )
    return _collapse_cross_filing_instrument_representatives(representatives)


def _collapse_metric_representatives(
    representatives: list[MaterialityAdjudicationDecision],
    *,
    key_fn: Callable[[MaterialityAdjudicationDecision], tuple[str, tuple[str, ...], str] | None],
) -> list[MaterialityAdjudicationDecision]:
    collapsed: dict[tuple[str, tuple[str, ...], str], MaterialityAdjudicationDecision] = {}
    unkeyed: list[MaterialityAdjudicationDecision] = []
    for decision in representatives:
        dedupe_key = key_fn(decision)
        if not dedupe_key:
            unkeyed.append(decision)
            continue
        current = collapsed.get(dedupe_key)
        if current is None or _metric_representative_sort_key(
            decision
        ) > _metric_representative_sort_key(current):
            collapsed[dedupe_key] = decision
    return [*unkeyed, *collapsed.values()]


def _source_hash_metric_dedupe_key(
    decision: MaterialityAdjudicationDecision,
) -> tuple[str, tuple[str, ...], str] | None:
    hashes = tuple(sorted(hash_value for hash_value in decision.content_hashes if hash_value))
    if not hashes and decision.content_hash:
        hashes = (decision.content_hash,)
    if not hashes:
        return None
    amount_key = _metric_amount_key(decision.supported_amount_usd)
    if not amount_key or amount_key == "0":
        return None
    return "source-hash", hashes, amount_key


def _economic_quote_metric_dedupe_key(
    decision: MaterialityAdjudicationDecision,
) -> tuple[str, tuple[str, ...], str] | None:
    if decision.metric_aggregation_policy != "max_amount_per_source_instrument":
        return None
    entity_key = re.sub(r"[^a-z0-9]+", "-", decision.entity.lower()).strip("-")
    amount_key = _metric_amount_key(decision.supported_amount_usd)
    stable_quote = decision.metric_dedupe_quote or decision.evidence_quote
    quote_key = _normalized_quote_fingerprint(stable_quote)
    if not entity_key or not amount_key or amount_key == "0" or not quote_key:
        return None
    return "economic-quote", (entity_key, amount_key), quote_key


def _economic_obligation_metric_dedupe_key(
    decision: MaterialityAdjudicationDecision,
) -> tuple[str, tuple[str, ...], str] | None:
    if decision.metric_aggregation_policy != "max_amount_per_source_instrument":
        return None
    entity_key = re.sub(r"[^a-z0-9]+", "-", decision.entity.lower()).strip("-")
    amount_key = _metric_amount_key(decision.supported_amount_usd)
    if not entity_key or not amount_key or amount_key == "0":
        return None
    subcategory_key = re.sub(r"[^a-z0-9]+", "-", decision.subcategory.lower()).strip("-")
    snapshot_key = decision.metric_snapshot_date[:7]
    counterparty_key = re.sub(r"[^a-z0-9]+", "-", decision.counterparty.lower()).strip("-")[:48]
    discriminators = tuple(
        value for value in (subcategory_key, snapshot_key, counterparty_key) if value
    )
    return "economic-obligation", (entity_key, amount_key, *discriminators), "v1"


_SEC_ACCESSION_RE = re.compile(r"/(\d{18})/")


def _sec_accession(source_uri: str) -> str:
    match = _SEC_ACCESSION_RE.search(source_uri or "")
    return match.group(1) if match else ""


def _accession_amount_metric_dedupe_key(
    decision: MaterialityAdjudicationDecision,
) -> tuple[str, tuple[str, ...], str] | None:
    if decision.metric_aggregation_policy != "max_amount_per_source_instrument":
        return None
    entity_key = re.sub(r"[^a-z0-9]+", "-", decision.entity.lower()).strip("-")
    amount_key = _metric_amount_key(decision.supported_amount_usd)
    accession = _sec_accession(decision.source_uri)
    if not entity_key or not amount_key or amount_key == "0" or not accession:
        return None
    return "accession-amount", (entity_key, accession), amount_key


_INSTRUMENT_DESCRIPTOR_RE = re.compile(r"(\d{1,2}\.\d{2,3})\s?%|due (\d{4})", re.I)
_ENTITY_SUFFIX_RE = re.compile(
    r"\b(holdco|landco|opco|computeco|hpc holdings|eln-?\d+|far-?\d+|spv|borrower|holdings|llc"
    r"|inc|corp|co|l\.?p\.?|ltd|plc|finance|funding|trust|series \w+)\b",
    re.I,
)


def _entity_root_key(entity: str) -> str:
    stripped = _ENTITY_SUFFIX_RE.sub("", entity.lower())
    return re.sub(r"[^a-z0-9]", "", stripped)[:12]


def _instrument_descriptor_tokens(quote: str) -> frozenset[str]:
    tokens: set[str] = set()
    for coupon, year in _INSTRUMENT_DESCRIPTOR_RE.findall(quote or ""):
        if coupon:
            tokens.add(f"c{coupon}")
        if year:
            tokens.add(f"y{year}")
    return frozenset(tokens)


def _has_strict_common_instrument_fingerprint(
    descriptors: list[frozenset[str]],
) -> bool:
    if not descriptors or not all(descriptors):
        return False
    common = set.intersection(*(set(descriptor) for descriptor in descriptors))
    return any(token.startswith("c") for token in common) and any(
        token.startswith("y") for token in common
    )


def _collapse_cross_filing_instrument_representatives(
    representatives: list[MaterialityAdjudicationDecision],
) -> list[MaterialityAdjudicationDecision]:
    keyed: dict[tuple[str, str], list[MaterialityAdjudicationDecision]] = {}
    unkeyed: list[MaterialityAdjudicationDecision] = []
    for decision in representatives:
        if decision.metric_aggregation_policy != "max_amount_per_source_instrument":
            unkeyed.append(decision)
            continue
        entity_key = _entity_root_key(decision.entity)
        amount_key = _metric_amount_key(decision.supported_amount_usd)
        accession = _sec_accession(decision.source_uri)
        if not entity_key or not amount_key or amount_key == "0" or not accession:
            unkeyed.append(decision)
            continue
        keyed.setdefault((entity_key, amount_key), []).append(decision)

    collapsed: list[MaterialityAdjudicationDecision] = []
    for decisions in keyed.values():
        accessions = {_sec_accession(decision.source_uri) for decision in decisions}
        descriptors = [
            _instrument_descriptor_tokens(decision.metric_dedupe_quote or decision.evidence_quote)
            for decision in decisions
        ]
        if len(accessions) > 1 and _has_strict_common_instrument_fingerprint(descriptors):
            collapsed.append(max(decisions, key=_metric_representative_sort_key))
        else:
            collapsed.extend(decisions)
    return [*unkeyed, *collapsed]


def _normalized_quote_fingerprint(quote: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", quote.lower()).strip()
    if len(normalized) < 80:
        return ""
    return hashlib.sha1(normalized.encode()).hexdigest()


def _metric_representative_sort_key(
    decision: MaterialityAdjudicationDecision,
) -> tuple[int, tuple[str, int], float]:
    policy_rank = {
        "max_amount_per_source_instrument": 2,
        "latest_snapshot_per_metric_group": 1,
    }.get(decision.metric_aggregation_policy, 0)
    return (
        policy_rank,
        _snapshot_sort_key(decision),
        decision.supported_amount_usd,
    )


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
    if _is_committed_contract_value_disclosure(packet, text):
        return True
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
    if _aggregate_lease_context_conflicts_with_quote(
        packet, quote
    ) or _looks_like_debt_outstanding_snapshot(text):
        return True
    if _is_committed_contract_value_disclosure(packet, text):
        return False
    hard_non_specific_markers = [
        "from time to time, we may offer",
        "may periodically offer",
        "create and issue further first mortgage bonds",
        "create and issue further collateral trust mortgage bonds",
    ]
    has_hard_non_specific_terms = _contains_any(text, hard_non_specific_markers)
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
    has_specific_terms = _contains_any(reason, explicit_specific_markers) or _contains_any(
        text,
        ["tranche", "credit agreement", "term loan", "revolver", "indenture"],
    )
    if has_specific_terms and not has_hard_non_specific_terms:
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
        "may periodically offer",
        "create and issue further first mortgage bonds",
        "create and issue further collateral trust mortgage bonds",
        "may issue up to",
        "registration statement",
    ]
    return (
        has_hard_non_specific_terms
        or _contains_any(text, explicit_non_specific_markers)
        or "aggregate" in text
    )


def _looks_like_asset_or_capacity_not_debt(packet: dict[str, str], quote: str) -> bool:
    if _field(packet, "category") not in {"capital", "contract"}:
        return False
    if _is_source_backed_aggregate_obligation_snapshot(packet, quote):
        return False
    text = _combined_text(packet, quote)
    asset_or_capacity_markers = [
        "servicing portfolio upb",
        "total upb",
        "by upb",
        "unpaid principal balance",
        "mortgage servicing rights",
        "msr fair value",
        "msr term notes",
        "financing capacity",
        "eligible for repurchase",
        "loans and leases held for investment",
        "loans held for investment",
        "average credit card and other loans",
        "end-of-period credit card and other loans",
        "loans at fair value",
        "asset-backed financing of variable interest entities",
        "tangible net worth",
        "not deposits or other obligations of a bank",
        "enterprise valuation",
        "purchase price paid",
        "aggregate purchase price",
        "completion of acquisition or disposition of assets",
        "net income of",
        "return on average assets",
        "return on average tangible common equity",
        "tangible book value",
        "market capitalization",
        "efficiency ratio",
        "loan growth",
        "gross credit losses",
        "loans / loans hfi",
        "loan-to-deposit",
        "loan - to - deposit",
        "client deposits",
        "core deposits",
        "gross loan portfolio",
    ]
    boilerplate_markers = [
        "webcast can be accessed",
        "forward-looking statements involve",
        "conference call, conference id",
        "underwriters or agents and their associates may be customers",
        "validity of the securities will be passed upon",
        "clearstream participants are recognized financial institutions",
        "available for certain fee-based wrap accounts",
        "fee-based wrap accounts",
        "entity name tax id number",
        "authorized signatory",
        "unless otherwise defined herein",
        "same meanings as in the prospectus",
    ]
    return _contains_any(text, asset_or_capacity_markers) or _contains_any(
        text, boilerplate_markers
    )


def _looks_like_undrawn_capacity_not_debt(packet: dict[str, str], quote: str) -> bool:
    if _field(packet, "category") not in {"capital", "contract"}:
        return False
    if _is_source_backed_aggregate_obligation_snapshot(packet, quote):
        return False
    text = _combined_text(packet, quote).lower()
    amount_clauses = _amount_bound_capacity_clauses(
        text, _float(packet.get("exposure_basis_usd"))
    )
    if amount_clauses:
        return any(_amount_clause_is_undrawn_capacity(clause) for clause in amount_clauses)
    if _is_underwriter_commitment_boilerplate(text):
        return False
    if _has_committed_debt_amount_markers(text):
        return False
    return _has_terminated_commitment_capacity(text)


def _amount_bound_capacity_clauses(text: str, amount: float) -> list[str]:
    if amount <= 0 or not text:
        return []
    raw_parts = [part.strip() for part in re.split(r"(?<=[.;:])\s+|,\s+", text) if part.strip()]
    if not raw_parts:
        return []
    terms = _specific_amount_terms(amount)
    clauses: list[str] = []
    seen: set[str] = set()
    for index, part in enumerate(raw_parts):
        part_lower = part.lower()
        if not any(term in part_lower for term in terms):
            continue
        window = " || ".join(raw_parts[index : index + 3]).strip()
        key = window[:240]
        if key in seen:
            continue
        seen.add(key)
        clauses.append(window)
    return clauses


def _specific_amount_terms(amount: float) -> list[str]:
    terms: list[str] = []
    for term in _amount_quote_terms(amount):
        normalized = term.lower().strip()
        if not normalized:
            continue
        if (
            "$" in normalized
            or "." in normalized
            or "million" in normalized
            or "billion" in normalized
            or "trillion" in normalized
            or len(normalized) >= 7
        ):
            terms.append(normalized)
    return list(dict.fromkeys(terms))


def _amount_clause_is_undrawn_capacity(clause: str) -> bool:
    lowered = clause.lower()
    amount_part = lowered.split(" || ", maxsplit=1)[0]
    bridge_capacity = _contains_any(
        amount_part, ["bridge loan facility", "bridge facility"]
    ) and _contains_any(lowered, ["terminated", "reduced to zero", "reduced to z"])
    if bridge_capacity:
        return True
    if _amount_part_has_committed_debt_markers(amount_part):
        return False
    if _is_underwriter_commitment_boilerplate(lowered):
        return False
    direct_capacity = _contains_any(
        amount_part,
        [
            "commitments available",
            "availability under",
            "available under",
        ],
    )
    revolver_capacity = _contains_any(
        amount_part,
        ["revolving credit agreement", "revolving credit facility", "revolver"],
    ) and _contains_any(
        lowered,
        [
            "no borrowings",
            "available and undrawn",
            "fully undrawn",
            "commitments available",
            "availability under",
            "available under",
            "borrowing availability",
        ],
    )
    free_capacity = _contains_any(
        lowered,
        [
            "available and undrawn",
            "fully undrawn",
            "borrowing availability under",
            "availability under",
        ],
    )
    return (
        direct_capacity
        or revolver_capacity
        or _has_terminated_commitment_capacity(lowered)
        or free_capacity
    )


def _amount_part_has_committed_debt_markers(text: str) -> bool:
    return _contains_any(
        text,
        [
            "aggregate principal amount",
            "existing senior unsecured notes",
            "existing senior secured notes",
            "senior unsecured notes",
            "senior secured notes",
            "issued",
            "issuance and sale",
            "notes due",
            "term loans borrowed",
            "repay all existing indebtedness",
        ],
    )


def _has_committed_debt_amount_markers(text: str) -> bool:
    return _contains_any(
        text,
        [
            "aggregate principal amount",
            "existing senior unsecured notes",
            "existing senior secured notes",
            "issued $",
            "issuance and sale",
            "notes due",
            "term loans borrowed",
            "repay all existing indebtedness",
        ],
    )


def _has_terminated_commitment_capacity(text: str) -> bool:
    return (
        _contains_any(text, ["terminated", "reduced to zero", "reduced to z"])
        and _contains_any(text, ["commitment", "commitments", "bridge facility"])
    )


def _is_underwriter_commitment_boilerplate(text: str) -> bool:
    return _contains_any(
        text,
        [
            "underwriting agreement",
            "non-defaulting underwriters",
            "purchase commitments of",
            "purchase commitments of the non-defaulting underwriters",
        ],
    )


def _requires_mega_obligation_confirmation(packet: dict[str, str], quote: str) -> bool:
    if _field(packet, "category") not in {"capital", "contract"}:
        return False
    if _float(packet.get("exposure_basis_usd")) <= MEGA_OBLIGATION_REVIEW_THRESHOLD_USD:
        return False
    if _is_source_backed_aggregate_obligation_snapshot(packet, quote):
        return False
    if _looks_like_asset_or_capacity_not_debt(packet, quote):
        return True
    return not _has_strong_mega_committed_debt_evidence(packet, quote)


def _has_strong_mega_committed_debt_evidence(packet: dict[str, str], quote: str) -> bool:
    text = _combined_text(packet, quote)
    reason = _field(packet, "reason").lower()
    if _contains_any(
        text,
        [
            "prospectus supplement",
            "registration statement",
            "from time to time",
            "may offer",
            "may issue",
        ],
    ):
        return False
    has_committed_action = _contains_any(
        text,
        [
            "entered into",
            "issued",
            "completed its offering",
            "completed the offering",
            "borrowed",
            "incurred",
        ],
    ) or _contains_any(reason, ["commitment scope: specific_transaction_commitment"])
    has_debt_instrument = _contains_any(
        text,
        [
            "credit agreement",
            "term loan",
            "revolving credit facility",
            "bridge loan",
            "indenture",
            "senior notes",
            "secured notes",
            "unsecured notes",
            "aggregate principal amount",
        ],
    )
    has_term_detail = _contains_any(
        text,
        [
            "matures",
            "maturity",
            "due 20",
            "interest at",
            "interest rate",
            "bear interest",
            "sofr",
            "administrative agent",
            "trustee",
            "guarantor",
            "guaranteed by",
            "secured by",
        ],
    )
    return has_committed_action and has_debt_instrument and has_term_detail


def _is_committed_contract_value_disclosure(packet: dict[str, str], text: str) -> bool:
    reason = _field(packet, "reason").lower()
    is_lease_or_service_contract = _contains_any(
        reason,
        [
            "debt-like deal type: lease",
            "notional context: lease",
            "notional context: contract",
        ],
    ) or _contains_any(text, ["lease agreement", "lease agreements", "service agreement"])
    if not is_lease_or_service_contract:
        return False
    if not _contains_any(
        text,
        [
            "entered into",
            "executed",
            "signed",
            "commenced",
        ],
    ):
        return False
    if not _contains_any(
        text,
        [
            "aggregate contractual value",
            "total contract value",
            "contractual value",
            "contract value",
            "minimum contracted revenue",
            "minimum lease payments",
        ],
    ):
        return False
    return not _contains_any(
        text,
        [
            "prospectus supplement",
            "registration statement",
            "from time to time",
            "may offer",
            "may issue",
            "ability to borrow",
            "available to borrow",
            "available to draw",
            "total liabilities",
            "servicing portfolio upb",
            "total consolidated long-term debt",
        ],
    )


def _looks_like_debt_outstanding_snapshot(text: str) -> bool:
    if _is_mortgage_bond_scope_present(text):
        has_principal_amount = _contains_any(
            text,
            ["aggregate principal amount", "principal amount"],
        )
        has_outstanding_mortgage_principal = _contains_any(
            text,
            [
                "outstanding first mortgage",
                "outstanding collateral trust mortgage",
                "outstanding indebtedness",
            ],
        ) or bool(
            re.search(
                r"\boutstanding\s+\$?\s*[\d,.]+(?:\s*(?:million|billion|trillion))?\s+"
                r"aggregate\s+principal\s+amount\s+of\s+(?:our\s+)?"
                r"(?:(?:first|collateral\s+trust|first\s+and\s+refunding)\s+)?"
                r"mortgage\s+bonds?\b",
                text,
            )
        )
        if has_principal_amount and _contains_any(
            text,
            ["were outstanding", "was outstanding", "outstanding under"],
        ):
            return True
        if (
            has_principal_amount
            and _contains_any(
                text,
                [
                    "repay or redeem",
                    "repay at maturity",
                    "repayment at maturity",
                    "offer to prepay",
                    "prepay",
                ],
            )
            and has_outstanding_mortgage_principal
        ):
            return True
    return _contains_any(
        text,
        [
            "total principal debt outstanding",
            "total consolidated long-term debt",
            "total liabilities",
            "debt due within one year",
            "on an as adjusted basis",
            "had approximately",
            "including $",
        ],
    ) and _contains_any(
        text,
        [
            "outstanding",
            "consolidated indebtedness",
            "consolidated long-term debt",
            "total liabilities",
        ],
    )


def _aggregate_lease_context_conflicts_with_quote(packet: dict[str, str], quote: str) -> bool:
    reason = _field(packet, "reason").lower()
    if "aggregate_lease_obligation" not in reason:
        return False
    quote_lower = quote.lower()
    if not quote_lower:
        return False
    has_lease_evidence = _contains_any(
        quote_lower,
        [
            "future lease payments",
            "lease payments",
            "operating lease obligations",
            "finance lease obligations",
            "entered into leases",
            "leases primarily related to data centers",
        ],
    )
    if has_lease_evidence:
        return False
    return _contains_any(
        quote_lower,
        [
            "description of debt securities",
            "we may offer secured or unsecured debt securities",
            "debt securities and the indenture",
            "series of debt securities",
            "the notes were issued pursuant to an indenture",
        ],
    ) and _contains_any(quote_lower, ["indenture", "debt securities", "notes"])


def _requires_foreign_currency_conversion(packet: dict[str, str], quote: str) -> bool:
    if _field(packet, "category") not in {"capital", "contract"}:
        return False
    recorded_amount = _float(packet.get("exposure_basis_usd"))
    if recorded_amount <= 0:
        return False
    text = _combined_text(packet, quote)
    return any(
        _amounts_close(recorded_amount, nominal_amount)
        for nominal_amount in _hk_dollar_nominal_amounts(text)
    )


def _currency_gaps(packet: dict[str, str], quote: str) -> list[str]:
    gaps: list[str] = []
    if _requires_foreign_currency_conversion(packet, quote):
        gaps.append("convert non-USD notional to USD before metric use")
    if _requires_mixed_currency_quote_reselection(packet, quote):
        gaps.append(
            "extract USD-equivalent or reselect source quote for non-USD/mixed-currency obligation"
        )
    return gaps


def _requires_mixed_currency_quote_reselection(packet: dict[str, str], quote: str) -> bool:
    if _field(packet, "category") not in {"capital", "contract"}:
        return False
    recorded_amount = _float(packet.get("exposure_basis_usd"))
    if recorded_amount <= 0 or not quote:
        return False
    foreign_amounts = _non_hkd_foreign_nominal_amounts(quote)
    if not foreign_amounts:
        return False
    return not any(
        _amounts_close(recorded_amount, usd_amount) for usd_amount in _usd_nominal_amounts(quote)
    )


def _hk_dollar_nominal_amounts(text: str) -> list[float]:
    amounts: list[float] = []
    for match in re.finditer(
        r"\bHK\$\s*(?P<amount>\d+(?:,\d{3})*(?:\.\d+)?)\s*"
        r"(?P<unit>trillion|billion|million|bn|b|m)?\b",
        text,
        flags=re.IGNORECASE,
    ):
        amount = _float(match.group("amount").replace(",", ""))
        unit = (match.group("unit") or "").lower()
        if unit in {"trillion"}:
            amount *= 1_000_000_000_000
        elif unit in {"billion", "bn", "b"}:
            amount *= 1_000_000_000
        elif unit in {"million", "m"}:
            amount *= 1_000_000
        if amount > 0:
            amounts.append(amount)
    return amounts


def _non_hkd_foreign_nominal_amounts(text: str) -> list[float]:
    amounts: list[float] = []
    patterns = [
        r"\b(?:C\$|CAD\s*\$?)\s*(?P<amount>\d+(?:,\d{3})*(?:\.\d+)?)\s*"
        r"(?P<unit>trillion|billion|million|bn|b|m)?\b",
        r"\b(?:A\$|AUD\s*\$?)\s*(?P<amount>\d+(?:,\d{3})*(?:\.\d+)?)\s*"
        r"(?P<unit>trillion|billion|million|bn|b|m)?\b",
        r"\b(?:S\$|SGD\s*\$?)\s*(?P<amount>\d+(?:,\d{3})*(?:\.\d+)?)\s*"
        r"(?P<unit>trillion|billion|million|bn|b|m)?\b",
        r"\b(?:€|EUR\s*)\s*(?P<amount>\d+(?:,\d{3})*(?:\.\d+)?)\s*"
        r"(?P<unit>trillion|billion|million|bn|b|m)?\b",
        r"\b(?:£|GBP\s*)\s*(?P<amount>\d+(?:,\d{3})*(?:\.\d+)?)\s*"
        r"(?P<unit>trillion|billion|million|bn|b|m)?\b",
        r"\b(?:¥|JPY\s*)\s*(?P<amount>\d+(?:,\d{3})*(?:\.\d+)?)\s*"
        r"(?P<unit>trillion|billion|million|bn|b|m)?\b",
    ]
    for pattern in patterns:
        amounts.extend(_nominal_amounts_from_pattern(text, pattern))
    return amounts


def _usd_nominal_amounts(text: str) -> list[float]:
    patterns = [
        r"\bUS\$\s*(?P<amount>\d+(?:,\d{3})*(?:\.\d+)?)\s*"
        r"(?P<unit>trillion|billion|million|bn|b|m)?\b",
        r"(?<![A-Za-z])\$\s*(?P<amount>\d+(?:,\d{3})*(?:\.\d+)?)\s*"
        r"(?P<unit>trillion|billion|million|bn|b|m)?\b",
    ]
    amounts: list[float] = []
    for pattern in patterns:
        amounts.extend(_nominal_amounts_from_pattern(text, pattern))
    return amounts


def _usd_nominal_amount_matches(text: str) -> list[tuple[float, tuple[int, int]]]:
    patterns = [
        r"\bUS\$\s*(?P<amount>\d+(?:,\d{3})*(?:\.\d+)?)\s*"
        r"(?P<unit>trillion|billion|million|bn|b|m)?\b",
        r"(?<![A-Za-z])\$\s*(?P<amount>\d+(?:,\d{3})*(?:\.\d+)?)\s*"
        r"(?P<unit>trillion|billion|million|bn|b|m)?\b",
    ]
    matches: list[tuple[float, tuple[int, int]]] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            amount = _float(match.group("amount").replace(",", ""))
            unit = (match.group("unit") or "").lower()
            if unit in {"trillion"}:
                amount *= 1_000_000_000_000
            elif unit in {"billion", "bn", "b"}:
                amount *= 1_000_000_000
            elif unit in {"million", "m"}:
                amount *= 1_000_000
            if amount > 0:
                matches.append((amount, match.span()))
    return matches


def _nominal_amounts_from_pattern(text: str, pattern: str) -> list[float]:
    amounts: list[float] = []
    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        amount = _float(match.group("amount").replace(",", ""))
        unit = (match.group("unit") or "").lower()
        if unit in {"trillion"}:
            amount *= 1_000_000_000_000
        elif unit in {"billion", "bn", "b"}:
            amount *= 1_000_000_000
        elif unit in {"million", "m"}:
            amount *= 1_000_000
        if amount > 0:
            amounts.append(amount)
    return amounts


def _amounts_close(left: float, right: float, *, tolerance: float = 0.05) -> bool:
    if left <= 0 or right <= 0:
        return False
    return abs(left - right) / max(left, right) <= tolerance


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
