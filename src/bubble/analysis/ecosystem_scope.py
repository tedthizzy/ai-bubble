"""Scope filters for AI/data-center ecosystem report metrics."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from bubble.ingestion.edgar.seeds import KNOWN_PROJECTS, PRIVATE_SEEDS, PUBLIC_SEEDS
from bubble.models.base import DealType

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bubble.models.deal import Deal


def _canonical_entity_key(name: str) -> str:
    tokens = re.sub(r"[^a-z0-9]+", " ", name.lower()).split()
    suffixes = {
        "co",
        "company",
        "corp",
        "corporation",
        "inc",
        "incorporated",
        "llc",
        "ltd",
        "limited",
        "plc",
    }
    while tokens and tokens[-1] in suffixes:
        tokens = tokens[:-1]
    return " ".join(tokens)


PUBLIC_AI_INFRA_CIKS = {
    "0000827876",  # CleanSpark
    "0001083301",  # TeraWulf
    "0001144879",  # Applied Digital
    "0001878848",  # IREN
    "0002021728",  # Cerebras
    "0002042022",  # WhiteFiber / Bit Digital AI infrastructure disclosures
}

DIRECT_PUBLIC_SEED_TYPES = {
    "ai_infra_pureplay",
    "data_center_reit",
}

CONTEXT_PUBLIC_SEED_TYPES = {
    "cloud_provider",
    "construction_services",
    "equipment_supplier",
    "financier",
    "hyperscaler",
    "power_generator",
    "power_utility",
}

PUBLIC_AI_INFRA_ENTITY_NAMES = {
    "Applied Digital",
    "Bit Digital",
    "Cipher Mining",
    "CleanSpark",
    "Core Scientific",
    "Hut 8",
    "IREN",
    "MARA Holdings",
    "Nebius",
    "Riot Platforms",
    "TeraWulf",
    "WhiteFiber",
}

DIRECT_PRIVATE_ENTITY_TYPES = {
    "ai_infra_pureplay",
    "ai_pureplay",
}

DIRECT_PRIVATE_ENTITY_NAMES = {
    metadata["name"]
    for metadata in PRIVATE_SEEDS
    if metadata.get("type") in DIRECT_PRIVATE_ENTITY_TYPES
}

DIRECT_ECOSYSTEM_CIKS = {
    cik
    for cik, metadata in PUBLIC_SEEDS.items()
    if metadata.get("type") in DIRECT_PUBLIC_SEED_TYPES
} | PUBLIC_AI_INFRA_CIKS

CONTEXT_ECOSYSTEM_CIKS = {
    cik
    for cik, metadata in PUBLIC_SEEDS.items()
    if metadata.get("type") in CONTEXT_PUBLIC_SEED_TYPES
}

DIRECT_ECOSYSTEM_ENTITY_NAMES = {
    *(
        metadata["name"]
        for metadata in PUBLIC_SEEDS.values()
        if metadata.get("type") in DIRECT_PUBLIC_SEED_TYPES
    ),
    *PUBLIC_AI_INFRA_ENTITY_NAMES,
    *DIRECT_PRIVATE_ENTITY_NAMES,
    *(metadata["name"] for metadata in KNOWN_PROJECTS),
}

CONTEXT_ECOSYSTEM_ENTITY_NAMES = {
    metadata["name"]
    for metadata in PUBLIC_SEEDS.values()
    if metadata.get("type") in CONTEXT_PUBLIC_SEED_TYPES
}

DIRECT_ECOSYSTEM_ENTITY_KEYS = {
    _canonical_entity_key(name) for name in DIRECT_ECOSYSTEM_ENTITY_NAMES
}
CONTEXT_ECOSYSTEM_ENTITY_KEYS = {
    _canonical_entity_key(name) for name in CONTEXT_ECOSYSTEM_ENTITY_NAMES
}

AI_DATA_CENTER_KEYWORDS = (
    "accelerated computing",
    "ai cluster",
    "ai data center",
    "ai datacenter",
    "ai factory",
    "ai infrastructure",
    "ai supercomputer",
    "artificial intelligence",
    "b200",
    "blackwell",
    "cloud gpu",
    "cloud infrastructure",
    "colocation",
    "data center",
    "data centers",
    "datacenter",
    "datacenters",
    "gb200",
    "gb300",
    "gpu",
    "gpu cloud",
    "gpu cluster",
    "h100",
    "h200",
    "high performance computing",
    "hyperscale",
    "hyperscaler",
    "nvidia gpu",
    "openai",
    "rubin",
    "supercomputer",
    "xai",
)

DEBT_LIKE_DEAL_TYPES = {
    DealType.DEBT_FACILITY,
    DealType.BOND,
    DealType.LEASE,
    DealType.PREFERRED_EQUITY,
    DealType.GUARANTEE,
}


@dataclass(frozen=True)
class EcosystemScopeSummary:
    """Summary of report-scope filtering for loaded capital deals."""

    deal_count_scanned: int
    in_scope_deal_count: int
    out_of_scope_deal_count: int
    debt_like_deal_count_scanned: int
    in_scope_debt_like_deal_count: int
    out_of_scope_debt_like_deal_count: int
    debt_like_notional_scanned_usd: float
    in_scope_debt_like_notional_usd: float
    out_of_scope_debt_like_notional_usd: float
    balance_sheet_context_deal_count: int
    balance_sheet_context_debt_like_deal_count: int
    balance_sheet_context_debt_like_notional_usd: float
    inclusion_reason_counts: dict[str, int]
    balance_sheet_context_reason_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def scope_deals(deals: Sequence[Deal]) -> tuple[list[Deal], EcosystemScopeSummary]:
    """Return deals in the AI/data-center ecosystem scope plus a filter summary."""

    in_scope: list[Deal] = []
    reason_counts: dict[str, int] = {}
    balance_sheet_context: list[Deal] = []
    context_reason_counts: dict[str, int] = {}
    for deal in deals:
        reasons = ecosystem_scope_reasons(deal)
        if reasons:
            in_scope.append(deal)
            for reason in reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            continue
        context_reasons = ecosystem_balance_sheet_context_reasons(deal)
        if context_reasons:
            balance_sheet_context.append(deal)
            for reason in context_reasons:
                context_reason_counts[reason] = context_reason_counts.get(reason, 0) + 1

    debt_like = [deal for deal in deals if _is_debt_like(deal)]
    in_scope_debt_like = [deal for deal in in_scope if _is_debt_like(deal)]
    balance_sheet_context_debt_like = [
        deal for deal in balance_sheet_context if _is_debt_like(deal)
    ]
    debt_like_notional = sum(_deal_notional(deal) for deal in debt_like)
    in_scope_debt_like_notional = sum(_deal_notional(deal) for deal in in_scope_debt_like)
    balance_sheet_context_debt_like_notional = sum(
        _deal_notional(deal) for deal in balance_sheet_context_debt_like
    )

    summary = EcosystemScopeSummary(
        deal_count_scanned=len(deals),
        in_scope_deal_count=len(in_scope),
        out_of_scope_deal_count=len(deals) - len(in_scope),
        debt_like_deal_count_scanned=len(debt_like),
        in_scope_debt_like_deal_count=len(in_scope_debt_like),
        out_of_scope_debt_like_deal_count=len(debt_like) - len(in_scope_debt_like),
        debt_like_notional_scanned_usd=round(debt_like_notional, 2),
        in_scope_debt_like_notional_usd=round(in_scope_debt_like_notional, 2),
        out_of_scope_debt_like_notional_usd=round(
            debt_like_notional - in_scope_debt_like_notional,
            2,
        ),
        balance_sheet_context_deal_count=len(balance_sheet_context),
        balance_sheet_context_debt_like_deal_count=len(balance_sheet_context_debt_like),
        balance_sheet_context_debt_like_notional_usd=round(
            balance_sheet_context_debt_like_notional,
            2,
        ),
        inclusion_reason_counts=dict(sorted(reason_counts.items())),
        balance_sheet_context_reason_counts=dict(sorted(context_reason_counts.items())),
    )
    return in_scope, summary


def is_ecosystem_deal(deal: Deal) -> bool:
    """Return True when the deal belongs in report-scope ecosystem metrics."""

    return bool(ecosystem_scope_reasons(deal))


def ecosystem_scope_reasons(deal: Deal) -> list[str]:
    """Return deterministic reasons a deal is in AI/data-center ecosystem scope."""

    reasons: list[str] = []
    cik = _deal_cik(deal)
    if cik and cik in DIRECT_ECOSYSTEM_CIKS:
        reasons.append("core_ai_data_center_cik")

    entity_keys = {_canonical_entity_key(entity) for entity in _deal_entities(deal)}
    if entity_keys & DIRECT_ECOSYSTEM_ENTITY_KEYS:
        reasons.append("core_ai_data_center_entity")

    text = _deal_text(deal)
    if any(keyword in text for keyword in AI_DATA_CENTER_KEYWORDS):
        reasons.append("direct_ai_data_center_keyword")

    return reasons


def ecosystem_balance_sheet_context_reasons(deal: Deal) -> list[str]:
    """Return reasons a broad ecosystem watchlist row is context, not headline scope."""

    reasons: list[str] = []
    cik = _deal_cik(deal)
    if cik and cik in CONTEXT_ECOSYSTEM_CIKS:
        reasons.append("watchlist_balance_sheet_cik")

    entity_keys = {_canonical_entity_key(entity) for entity in _deal_entities(deal)}
    if entity_keys & CONTEXT_ECOSYSTEM_ENTITY_KEYS:
        reasons.append("watchlist_balance_sheet_entity")

    return reasons


def _deal_cik(deal: Deal) -> str | None:
    raw_id = deal.source_deal_id or ""
    match = re.match(r"^edgar:(?P<cik>\d{1,10}):", raw_id)
    if not match:
        return None
    return match.group("cik").zfill(10)


def _deal_entities(deal: Deal) -> list[str]:
    entities = [str(entity) for entity in deal.parties]
    for role_entities in deal.counterparty_roles.values():
        entities.extend(str(entity) for entity in role_entities)
    entities.extend(str(entity) for entity in deal.linked_projects)
    entities.extend(str(entity) for entity in deal.linked_assets)
    return entities


def _deal_text(deal: Deal) -> str:
    parts: list[str] = [
        deal.title or "",
        deal.provenance.page_or_section or "",
        " ".join(_deal_entities(deal)),
    ]
    if deal.key_terms:
        parts.append(json.dumps(deal.key_terms, sort_keys=True, default=str))
    if deal.collateral:
        parts.append(" ".join(deal.collateral))
    if deal.guarantees:
        parts.append(" ".join(str(entity) for entity in deal.guarantees))
    return " ".join(parts).lower()


def _is_debt_like(deal: Deal) -> bool:
    return deal.deal_type in DEBT_LIKE_DEAL_TYPES or bool(deal.debt_tranches)


def _deal_notional(deal: Deal) -> float:
    tranche_total = sum(tranche.notional_usd for tranche in deal.debt_tranches)
    if tranche_total:
        return tranche_total
    return float(deal.notional_amount_usd or 0.0)
