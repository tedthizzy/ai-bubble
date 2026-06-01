"""
CSV loader for source-backed capital/deal evidence.

Expected files in a directory:
- deals.csv
- tranches.csv (optional)

Every row must carry source_uri. Optional row fields source_type, source_confidence,
human_review_status, page_or_section, and content_hash override provenance defaults.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from bubble.analysis.capital_structure import CapitalStructureAnalyzer, CapitalStructureMetrics
from bubble.graph.client import get_graph_client
from bubble.models.base import DealType, HumanReviewStatus, Provenance, SourceType
from bubble.models.deal import Deal, DebtTranche
from bubble.quality.source_invariants import assert_source_row

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bubble.graph.client import BubbleGraphClient


@dataclass(frozen=True)
class CapitalEvidenceBatch:
    """Loaded deal evidence."""

    deals: list[Deal]


def load_capital_evidence(directory: str | Path) -> CapitalEvidenceBatch:
    """Load source-backed deal and tranche CSVs from a directory."""
    base = Path(directory)
    tranche_rows_by_deal = _tranche_rows_by_deal(_read_csv(base / "tranches.csv", required=False))
    deals = [
        _deal_from_row(row, tranche_rows_by_deal.get(_required(row, "deal_id"), []))
        for row in _read_csv(base / "deals.csv", required=True)
    ]
    return CapitalEvidenceBatch(deals=deals)


def analyze_capital_evidence(
    batch: CapitalEvidenceBatch,
    *,
    analyzer: CapitalStructureAnalyzer | None = None,
    as_of: date | None = None,
    near_term_end: date | None = None,
) -> CapitalStructureMetrics:
    """Run capital-structure analysis on loaded deals."""
    capital_analyzer = analyzer or CapitalStructureAnalyzer()
    return capital_analyzer.analyze(batch.deals, as_of=as_of, near_term_end=near_term_end)


def ingest_capital_evidence(
    directory: str | Path,
    *,
    graph: BubbleGraphClient | None = None,
    as_of: date | None = None,
    near_term_end: date | None = None,
) -> dict[str, Any]:
    """Load source-backed deals, merge them into the graph, and return capital metrics."""
    graph_client = graph or get_graph_client()
    batch = load_capital_evidence(directory)
    metrics = analyze_capital_evidence(batch, as_of=as_of, near_term_end=near_term_end)

    deal_node_ids = {
        deal.source_deal_id or str(deal.id): graph_client.merge_deal(deal) for deal in batch.deals
    }
    return {
        "deals": len(batch.deals),
        "deal_node_ids": deal_node_ids,
        "tranches": sum(len(deal.debt_tranches) for deal in batch.deals),
        "debt_like_deals": metrics.debt_like_deal_count,
        "debt_like_notional_usd": metrics.debt_like_notional_usd,
        "distinct_debt_like_deals": metrics.distinct_debt_like_deal_count,
        "distinct_debt_like_notional_usd": metrics.distinct_debt_like_notional_usd,
        "duplicate_candidate_deals": metrics.duplicate_candidate_deal_count,
        "duplicate_candidate_notional_usd": metrics.duplicate_candidate_notional_usd,
        "aggregate_obligation_distinct_deals": metrics.aggregate_obligation_distinct_deal_count,
        "aggregate_obligation_distinct_notional_usd": (
            metrics.aggregate_obligation_distinct_notional_usd
        ),
        "off_balance_sheet_usd": metrics.off_balance_sheet_usd,
        "guarantee_linked_usd": metrics.guarantee_linked_usd,
        "spv_or_non_recourse_usd": metrics.spv_or_non_recourse_usd,
        "reviewed_debt_like_notional_usd": metrics.reviewed_debt_like_notional_usd,
        "pending_review_debt_like_notional_usd": (metrics.pending_review_debt_like_notional_usd),
        "notional_review_required_usd": metrics.notional_review_required_usd,
        "notional_review_required_deals": metrics.notional_review_required_deal_count,
        "near_term_refinancing_usd": metrics.near_term_refinancing_usd,
        "top_10_concentration_pct": metrics.top_10_concentration_pct,
        "high_confidence_claims": metrics.evidence_summary["high_confidence_eligible_claims"],
        "metrics": metrics.to_dict(),
    }


def _read_csv(path: Path, *, required: bool) -> list[dict[str, str]]:
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return []
    with path.open(newline="") as f:
        return [
            {key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(f)
        ]


def _tranche_rows_by_deal(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(_required(row, "deal_id"), []).append(row)
    return grouped


def _deal_from_row(row: dict[str, str], tranche_rows: Sequence[dict[str, str]]) -> Deal:
    deal_id = _required(row, "deal_id")
    return Deal(
        source_deal_id=deal_id,
        deal_type=_enum_value(DealType, row.get("deal_type"), DealType.OTHER),
        title=_optional_str(row.get("title")),
        parties=_split(row.get("parties")) or [_required(row, "primary_party")],
        counterparty_roles=_roles(row.get("counterparty_roles")),
        announced_date=_optional_date(row.get("announced_date")),
        effective_date=_optional_date(row.get("effective_date")),
        maturity_date=_optional_date(row.get("maturity_date")),
        notional_amount_usd=_optional_float(row.get("notional_amount_usd")),
        currency=row.get("currency") or "USD",
        debt_tranches=[_tranche_from_row(tranche_row) for tranche_row in tranche_rows],
        is_non_recourse=_optional_bool(row.get("is_non_recourse")),
        bankruptcy_remote_spv=_optional_bool(row.get("bankruptcy_remote_spv")),
        key_terms=_json_dict(row.get("key_terms")),
        collateral=_split(row.get("collateral")),
        guarantees=_split(row.get("guarantees")),
        linked_projects=_split(row.get("linked_projects")),
        linked_assets=_split(row.get("linked_assets")),
        is_related_party=_bool(row.get("is_related_party")),
        concentration_risk_flag=_bool(row.get("concentration_risk_flag")),
        provenance=_provenance_from_row(
            row,
            default_source_type=SourceType.SEC_EDGAR,
            identity=f"deal:{deal_id}",
        ),
        confidence=_optional_float(row.get("confidence")) or 0.85,
    )


def _tranche_from_row(row: dict[str, str]) -> DebtTranche:
    tranche_key = ":".join(
        [
            _required(row, "deal_id"),
            row.get("tranche_id") or row.get("name") or "unknown",
        ]
    )
    return DebtTranche(
        name=_required(row, "name"),
        seniority=_optional_int(row.get("seniority")) or 1,
        notional_usd=_required_float(row, "notional_usd"),
        interest_rate=_optional_float(row.get("interest_rate")),
        maturity=_optional_date(row.get("maturity")),
        recourse=_bool(row.get("recourse")),
        collateral_description=_optional_str(row.get("collateral_description")),
        guarantors=_split(row.get("guarantors")),
        provenance=_provenance_from_row(
            row,
            default_source_type=SourceType.SEC_EDGAR,
            identity=f"tranche:{tranche_key}",
        ),
        confidence=_optional_float(row.get("confidence")) or 0.85,
    )


def _provenance_from_row(
    row: dict[str, str],
    *,
    default_source_type: SourceType,
    identity: str,
) -> Provenance:
    assert_source_row(row, context=identity)
    source_uri = _required(row, "source_uri")
    source_type = _enum_value(SourceType, row.get("source_type"), default_source_type)
    raw_confidence = row.get("source_confidence") or row.get("provenance_confidence")
    confidence = _optional_float(raw_confidence) or 0.85
    content_hash = row.get("content_hash") or Provenance.compute_content_hash(
        json.dumps({"identity": identity, "row": row}, sort_keys=True)
    )
    return Provenance(
        source_uri=source_uri,
        source_type=source_type,
        page_or_section=_optional_str(row.get("page_or_section")),
        confidence=confidence,
        human_review_status=_enum_value(
            HumanReviewStatus,
            row.get("human_review_status"),
            HumanReviewStatus.PENDING,
        ),
        content_hash=content_hash,
    )


def _required(row: dict[str, str], key: str) -> str:
    value = row.get(key)
    if not value:
        raise ValueError(f"CSV row missing required field: {key}")
    return value


def _required_float(row: dict[str, str], key: str) -> float:
    value = _optional_float(row.get(key))
    if value is None:
        raise ValueError(f"CSV row missing required numeric field: {key}")
    return value


def _optional_str(value: str | None) -> str | None:
    return value if value else None


def _optional_float(value: str | None) -> float | None:
    if not value:
        return None
    return float(value.replace(",", "").replace("$", ""))


def _optional_int(value: str | None) -> int | None:
    parsed = _optional_float(value)
    return int(parsed) if parsed is not None else None


def _optional_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _bool(value: str | None) -> bool:
    return bool(_optional_bool(value))


def _optional_bool(value: str | None) -> bool | None:
    if not value:
        return None
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _split(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.replace(";", "|").split("|") if part.strip()]


def _roles(value: str | None) -> dict[str, list[str]]:
    if not value:
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("counterparty_roles must be a JSON object")
    roles: dict[str, list[str]] = {}
    for role, entities in parsed.items():
        if isinstance(entities, str):
            roles[str(role)] = _split(entities)
        elif isinstance(entities, list):
            roles[str(role)] = [str(entity) for entity in entities]
        else:
            raise ValueError("counterparty_roles values must be strings or arrays")
    return roles


def _json_dict(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object")
    return cast("dict[str, Any]", parsed)


def _enum_value[EnumT: StrEnum](enum_cls: type[EnumT], value: str | None, default: EnumT) -> EnumT:
    if not value:
        return default
    normalized = value.strip().lower()
    try:
        return enum_cls(normalized)
    except ValueError:
        by_name = enum_cls.__members__.get(value.strip().upper())
        if by_name is not None:
            return by_name
        return default
