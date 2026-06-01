"""Source-backed capital exposure graph construction.

This module turns extracted deal evidence into a deterministic entity exposure
network. It is intentionally conservative: edges are created only from named
deal parties/roles carried by source-backed rows, and generic placeholders such
as "noteholders" are counted as unmapped rather than promoted to entity nodes.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bubble.analysis.entity_filters import is_generic_entity_name
from bubble.models.base import DealType

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from bubble.models.deal import Deal


DEBT_LIKE_DEAL_TYPES = {
    DealType.DEBT_FACILITY,
    DealType.BOND,
    DealType.LEASE,
    DealType.PREFERRED_EQUITY,
    DealType.GUARANTEE,
}

OBLIGOR_ROLES = {
    "borrower",
    "issuer",
    "lessee",
    "tenant",
    "obligor",
    "debtor",
    "company",
    "grantor",
}

RISK_BEARER_ROLES = {
    "administrative_agent",
    "agent",
    "arranger",
    "bondholder",
    "collateral_agent",
    "financier",
    "guarantor",
    "indenture_trustee",
    "insurer",
    "lender",
    "lessor",
    "noteholder",
    "trustee",
}

PPA_SOURCE_ROLES = {"seller", "reporting_entity", "generator", "project_company"}
PPA_TARGET_ROLES = {"buyer", "offtaker", "utility", "counterparty"}

ENTITY_SUFFIX_TOKENS = {
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

DIRECT_AI_INFRA_PATTERNS = {
    "ai_keyword": re.compile(r"\b(ai|artificial intelligence)\b", re.I),
    "data_center": re.compile(r"\bdata[- ]?cent(er|re)s?\b|\bdatacent(er|re)s?\b", re.I),
    "compute": re.compile(r"\bcompute\b|\bgpu\b|\bh100\b|\bh200\b|\bblackwell\b|\brubin\b", re.I),
    "cloud": re.compile(r"\bhyperscale\b|\bcloud\b|\bcolocation\b", re.I),
    "power_for_data_center": re.compile(
        r"\b(data[- ]?cent(er|re)|hyperscale|ai)\b.{0,80}\b(power|load|interconnection|ppa)\b",
        re.I,
    ),
}

WATCHLIST_ENTITY_PATTERNS = {
    "amazon_or_aws": re.compile(r"\b(amazon|aws)\b", re.I),
    "alphabet_or_google": re.compile(r"\b(alphabet|google)\b", re.I),
    "microsoft": re.compile(r"\bmicrosoft\b", re.I),
    "meta": re.compile(r"\bmeta platforms?\b|\bfacebook\b", re.I),
    "oracle": re.compile(r"\boracle\b", re.I),
    "openai": re.compile(r"\bopenai\b", re.I),
    "xai": re.compile(r"\bxai\b|\bx\.ai\b", re.I),
    "nvidia": re.compile(r"\bnvidia\b", re.I),
    "amd": re.compile(r"\badvanced micro devices\b|\bamd\b", re.I),
    "broadcom": re.compile(r"\bbroadcom\b", re.I),
    "coreweave": re.compile(r"\bcoreweave\b", re.I),
    "equinix": re.compile(r"\bequinix\b", re.I),
    "digital_realty": re.compile(r"\bdigital realty\b", re.I),
    "qts": re.compile(r"\bqts\b", re.I),
    "vantage": re.compile(r"\bvantage data centers?\b", re.I),
    "databank": re.compile(r"\bdatabank\b", re.I),
    "supermicro": re.compile(r"\bsuper micro\b|\bsupermicro\b", re.I),
}


@dataclass(frozen=True)
class CapitalExposureNode:
    """An entity node in the source-backed exposure network."""

    node_id: str
    name: str
    roles: tuple[str, ...]
    deal_count: int
    exposure_usd: float
    source_uri_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapitalExposureEdge:
    """Aggregated exposure relationship between two named entities."""

    source_id: str
    source_name: str
    target_id: str
    target_name: str
    relationship_type: str
    deal_type: str
    roles: tuple[str, ...]
    deal_count: int
    notional_usd: float
    ppa_capacity_mw: float
    source_deal_ids: tuple[str, ...]
    source_uris: tuple[str, ...]
    content_hashes: tuple[str, ...]
    human_review_statuses: tuple[str, ...]
    relevance_tags: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapitalExposureComponentRisk:
    """One connected source-backed exposure cluster."""

    component_id: str
    node_count: int
    edge_count: int
    notional_usd: float
    ai_infra_relevant_notional_usd: float
    ppa_capacity_mw: float
    source_uri_count: int
    top_entities: list[dict[str, Any]]
    top_edges: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapitalExposureContagionHub:
    """Entity-level concentration point in the source-backed exposure graph."""

    node_id: str
    name: str
    roles: tuple[str, ...]
    incident_edge_count: int
    distinct_counterparties: int
    deal_count: int
    incident_notional_usd: float
    ai_infra_relevant_notional_usd: float
    ppa_capacity_mw: float
    source_uri_count: int
    risk_bearer_neighbor_count: int
    obligor_neighbor_count: int
    relevance_tags: tuple[str, ...]
    top_counterparties: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapitalExposureGraphSummary:
    """Serializable rollup of the capital exposure graph."""

    deals_scanned: int
    deals_with_edges: int
    deals_without_named_counterparty_edges: int
    nodes: int
    edges: int
    source_backed_edges: int
    debt_like_edges: int
    ppa_edges: int
    edges_with_notional: int
    ai_infra_relevant_edges: int
    direct_ai_keyword_edges: int
    watchlist_entity_edges: int
    ai_infra_relevant_notional_usd: float
    generic_counterparty_mentions_skipped: int
    total_edge_notional_usd: float
    ppa_capacity_mw: float
    distinct_source_uris: int
    connected_components: int
    largest_component_nodes: int
    largest_component_edges: int
    largest_component_notional_usd: float
    largest_component_ai_infra_relevant_notional_usd: float
    ai_infra_component_count: int
    top_ai_infra_component_nodes: int
    top_ai_infra_component_edges: int
    top_ai_infra_component_notional_usd: float
    top_entities_by_exposure: list[dict[str, Any]]
    top_risk_bearers: list[dict[str, Any]]
    top_obligors: list[dict[str, Any]]
    top_exposure_edges: list[dict[str, Any]]
    top_ai_infra_exposure_edges: list[dict[str, Any]]
    top_components_by_notional: list[dict[str, Any]]
    top_ai_infra_components_by_notional: list[dict[str, Any]]
    top_contagion_hubs: list[dict[str, Any]]
    top_ai_infra_contagion_hubs: list[dict[str, Any]]
    high_notional_unmapped_deals: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class _NodeAccumulator:
    name: str
    roles: set[str] = field(default_factory=set)
    deal_ids: set[str] = field(default_factory=set)
    source_uris: set[str] = field(default_factory=set)
    exposure_usd: float = 0.0


@dataclass
class _EdgeAccumulator:
    source_id: str
    source_name: str
    target_id: str
    target_name: str
    relationship_type: str
    deal_type: str
    roles: set[str] = field(default_factory=set)
    deal_ids: set[str] = field(default_factory=set)
    source_uris: set[str] = field(default_factory=set)
    content_hashes: set[str] = field(default_factory=set)
    human_review_statuses: set[str] = field(default_factory=set)
    relevance_tags: set[str] = field(default_factory=set)
    notional_usd: float = 0.0
    ppa_capacity_mw: float = 0.0


@dataclass(frozen=True)
class CapitalExposureGraph:
    """Built graph artifacts."""

    nodes: list[CapitalExposureNode]
    edges: list[CapitalExposureEdge]
    summary: CapitalExposureGraphSummary


def build_capital_exposure_graph(deals: list[Deal]) -> CapitalExposureGraph:
    """Build a source-backed exposure graph from capital deal evidence."""

    node_acc: dict[str, _NodeAccumulator] = {}
    edge_acc: dict[tuple[str, str, str, str], _EdgeAccumulator] = {}
    generic_skipped = 0
    deals_with_edges = 0
    high_notional_unmapped: list[dict[str, Any]] = []
    all_source_uris: set[str] = set()

    for deal in deals:
        all_source_uris.add(deal.provenance.source_uri)
        deal_edges, skipped = _edges_for_deal(deal)
        generic_skipped += skipped
        if deal_edges:
            deals_with_edges += 1
        elif _deal_notional(deal) >= 25_000_000_000:
            high_notional_unmapped.append(_unmapped_deal_row(deal, ["no_named_counterparty_edge"]))

        for edge in deal_edges:
            key = (
                edge["source_id"],
                edge["target_id"],
                edge["relationship_type"],
                edge["deal_type"],
            )
            acc = edge_acc.get(key)
            if acc is None:
                acc = _EdgeAccumulator(
                    source_id=edge["source_id"],
                    source_name=edge["source_name"],
                    target_id=edge["target_id"],
                    target_name=edge["target_name"],
                    relationship_type=edge["relationship_type"],
                    deal_type=edge["deal_type"],
                )
                edge_acc[key] = acc
            acc.roles.add(edge["role"])
            acc.deal_ids.add(edge["deal_id"])
            acc.source_uris.add(edge["source_uri"])
            acc.content_hashes.add(edge["content_hash"])
            acc.human_review_statuses.add(edge["human_review_status"])
            acc.relevance_tags.update(edge["relevance_tags"])
            acc.notional_usd += edge["notional_usd"]
            acc.ppa_capacity_mw += edge["ppa_capacity_mw"]

            _add_node(
                node_acc,
                edge["source_id"],
                edge["source_name"],
                edge["source_role"],
                edge["deal_id"],
                edge["source_uri"],
                edge["notional_usd"],
            )
            _add_node(
                node_acc,
                edge["target_id"],
                edge["target_name"],
                edge["target_role"],
                edge["deal_id"],
                edge["source_uri"],
                edge["notional_usd"],
            )

    nodes = [
        CapitalExposureNode(
            node_id=node_id,
            name=acc.name,
            roles=tuple(sorted(acc.roles)),
            deal_count=len(acc.deal_ids),
            exposure_usd=round(acc.exposure_usd, 2),
            source_uri_count=len(acc.source_uris),
        )
        for node_id, acc in node_acc.items()
    ]
    nodes.sort(key=lambda node: (node.exposure_usd, node.deal_count, node.name), reverse=True)

    edges = [
        CapitalExposureEdge(
            source_id=acc.source_id,
            source_name=acc.source_name,
            target_id=acc.target_id,
            target_name=acc.target_name,
            relationship_type=acc.relationship_type,
            deal_type=acc.deal_type,
            roles=tuple(sorted(acc.roles)),
            deal_count=len(acc.deal_ids),
            notional_usd=round(acc.notional_usd, 2),
            ppa_capacity_mw=round(acc.ppa_capacity_mw, 3),
            source_deal_ids=tuple(sorted(acc.deal_ids)[:25]),
            source_uris=tuple(sorted(acc.source_uris)[:25]),
            content_hashes=tuple(sorted(acc.content_hashes)[:25]),
            human_review_statuses=tuple(sorted(acc.human_review_statuses)),
            relevance_tags=tuple(sorted(acc.relevance_tags)),
        )
        for acc in edge_acc.values()
    ]
    edges.sort(
        key=lambda edge: (edge.notional_usd, edge.deal_count, edge.ppa_capacity_mw), reverse=True
    )

    components = _connected_components(edges)
    largest_component = max(components, key=len, default=set())
    largest_component_id = _component_id(largest_component) if largest_component else ""
    component_risks = _component_risks(components, edges, nodes)
    largest_component_risk = next(
        (
            component
            for component in component_risks
            if component.component_id == largest_component_id
        ),
        None,
    )
    contagion_hubs = _contagion_hubs(edges, nodes)

    top_entities = [node.to_dict() for node in nodes[:25]]
    top_risk_bearers = [
        node.to_dict() for node in nodes if set(node.roles).intersection(RISK_BEARER_ROLES)
    ][:25]
    top_obligors = [
        node.to_dict()
        for node in nodes
        if set(node.roles).intersection(OBLIGOR_ROLES | PPA_SOURCE_ROLES)
    ][:25]
    ai_relevant_edges = [edge for edge in edges if edge.relevance_tags]
    direct_ai_edges = [
        edge
        for edge in ai_relevant_edges
        if any(tag.startswith("direct:") for tag in edge.relevance_tags)
    ]
    watchlist_edges = [
        edge
        for edge in ai_relevant_edges
        if any(tag.startswith("watchlist:") for tag in edge.relevance_tags)
    ]
    ai_components = _connected_components(ai_relevant_edges)
    ai_component_risks = _component_risks(ai_components, ai_relevant_edges, nodes)
    top_ai_component = ai_component_risks[0] if ai_component_risks else None

    summary = CapitalExposureGraphSummary(
        deals_scanned=len(deals),
        deals_with_edges=deals_with_edges,
        deals_without_named_counterparty_edges=len(deals) - deals_with_edges,
        nodes=len(nodes),
        edges=len(edges),
        source_backed_edges=sum(1 for edge in edges if edge.source_uris),
        debt_like_edges=sum(
            1 for edge in edges if edge.deal_type in _deal_type_values(DEBT_LIKE_DEAL_TYPES)
        ),
        ppa_edges=sum(1 for edge in edges if edge.deal_type == DealType.PPA.value),
        edges_with_notional=sum(1 for edge in edges if edge.notional_usd > 0),
        ai_infra_relevant_edges=len(ai_relevant_edges),
        direct_ai_keyword_edges=len(direct_ai_edges),
        watchlist_entity_edges=len(watchlist_edges),
        ai_infra_relevant_notional_usd=round(
            sum(edge.notional_usd for edge in ai_relevant_edges), 2
        ),
        generic_counterparty_mentions_skipped=generic_skipped,
        total_edge_notional_usd=round(sum(edge.notional_usd for edge in edges), 2),
        ppa_capacity_mw=round(sum(edge.ppa_capacity_mw for edge in edges), 3),
        distinct_source_uris=len(all_source_uris),
        connected_components=len(components),
        largest_component_nodes=len(largest_component),
        largest_component_edges=largest_component_risk.edge_count
        if largest_component_risk
        else 0,
        largest_component_notional_usd=largest_component_risk.notional_usd
        if largest_component_risk
        else 0.0,
        largest_component_ai_infra_relevant_notional_usd=(
            largest_component_risk.ai_infra_relevant_notional_usd
            if largest_component_risk
            else 0.0
        ),
        ai_infra_component_count=len(ai_components),
        top_ai_infra_component_nodes=top_ai_component.node_count if top_ai_component else 0,
        top_ai_infra_component_edges=top_ai_component.edge_count if top_ai_component else 0,
        top_ai_infra_component_notional_usd=top_ai_component.notional_usd
        if top_ai_component
        else 0.0,
        top_entities_by_exposure=top_entities,
        top_risk_bearers=top_risk_bearers,
        top_obligors=top_obligors,
        top_exposure_edges=[edge.to_dict() for edge in edges[:25]],
        top_ai_infra_exposure_edges=[edge.to_dict() for edge in ai_relevant_edges[:25]],
        top_components_by_notional=[component.to_dict() for component in component_risks[:15]],
        top_ai_infra_components_by_notional=[
            component.to_dict() for component in ai_component_risks[:15]
        ],
        top_contagion_hubs=[hub.to_dict() for hub in contagion_hubs[:25]],
        top_ai_infra_contagion_hubs=[
            hub.to_dict()
            for hub in contagion_hubs
            if hub.ai_infra_relevant_notional_usd > 0
        ][:25],
        high_notional_unmapped_deals=high_notional_unmapped[:25],
    )
    return CapitalExposureGraph(nodes=nodes, edges=edges, summary=summary)


def write_capital_exposure_graph(
    graph: CapitalExposureGraph, output_dir: str | Path
) -> dict[str, str]:
    """Write graph nodes, edges, and summary to disk."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    nodes_path = out / "capital_exposure_nodes.csv"
    edges_path = out / "capital_exposure_edges.csv"
    summary_path = out / "capital_exposure_graph_summary.json"

    _write_csv(nodes_path, [node.to_dict() for node in graph.nodes])
    _write_csv(edges_path, [edge.to_dict() for edge in graph.edges])
    summary_path.write_text(json.dumps(graph.summary.to_dict(), indent=2))
    return {
        "nodes_csv": str(nodes_path),
        "edges_csv": str(edges_path),
        "summary_json": str(summary_path),
    }


def _edges_for_deal(deal: Deal) -> tuple[list[dict[str, Any]], int]:
    notional = _deal_notional(deal)
    ppa_capacity = _ppa_capacity_mw(deal)
    deal_id = deal.source_deal_id or str(deal.id)
    source_uri = deal.provenance.source_uri
    content_hash = deal.provenance.content_hash
    human_review_status = deal.provenance.human_review_status.value
    relevance_tags = _deal_relevance_tags(deal)

    if deal.deal_type == DealType.PPA:
        source_entities = _role_entities(
            deal.counterparty_roles, PPA_SOURCE_ROLES
        ) or _party_entities(
            deal.parties[:1],
            "seller",
        )
        target_entities = _role_entities(
            deal.counterparty_roles, PPA_TARGET_ROLES
        ) or _party_entities(
            deal.parties[1:],
            "counterparty",
        )
        relationship_type = "PPA_COUNTERPARTY"
    else:
        source_entities = _role_entities(deal.counterparty_roles, OBLIGOR_ROLES) or _party_entities(
            deal.parties[:1],
            _source_role_for_deal(deal),
        )
        target_entities = _role_entities(deal.counterparty_roles, RISK_BEARER_ROLES)
        if not target_entities:
            target_entities = _party_entities(deal.guarantees, "guarantor") or _party_entities(
                deal.parties[1:],
                "counterparty",
            )
        relationship_type = _relationship_type_for_deal(deal)

    edges: list[dict[str, Any]] = []
    generic_skipped = 0
    for source, source_role in source_entities:
        source_name = str(source).strip()
        if not source_name or _is_generic_entity(source_name):
            generic_skipped += 1
            continue
        for target, role in target_entities:
            target_name = str(target).strip()
            if not target_name or target_name == source_name:
                continue
            if _is_generic_entity(target_name):
                generic_skipped += 1
                continue
            source_id = _entity_id(source_name)
            target_id = _entity_id(target_name)
            if source_id == target_id:
                continue
            edges.append(
                {
                    "source_id": source_id,
                    "source_name": source_name,
                    "target_id": target_id,
                    "target_name": target_name,
                    "source_role": source_role,
                    "target_role": role,
                    "relationship_type": relationship_type,
                    "deal_type": deal.deal_type.value,
                    "role": role,
                    "deal_id": deal_id,
                    "notional_usd": notional,
                    "ppa_capacity_mw": ppa_capacity if deal.deal_type == DealType.PPA else 0.0,
                    "source_uri": source_uri,
                    "content_hash": content_hash,
                    "human_review_status": human_review_status,
                    "relevance_tags": relevance_tags,
                }
            )
    return edges, generic_skipped


def _relationship_type_for_deal(deal: Deal) -> str:
    if deal.deal_type == DealType.DEBT_FACILITY:
        return "OWES_OR_BORROWS_FROM"
    if deal.deal_type == DealType.BOND:
        return "ISSUED_TO_OR_TRUSTEE_FOR"
    if deal.deal_type == DealType.LEASE:
        return "LEASE_OBLIGATION_TO"
    if deal.deal_type == DealType.GUARANTEE:
        return "GUARANTEED_BY"
    if deal.deal_type == DealType.PREFERRED_EQUITY:
        return "PREFERRED_EQUITY_FROM"
    return "CONTRACT_EXPOSURE_TO"


def _source_role_for_deal(deal: Deal) -> str:
    if deal.deal_type == DealType.BOND:
        return "issuer"
    if deal.deal_type == DealType.LEASE:
        return "lessee"
    if deal.deal_type == DealType.PPA:
        return "seller"
    return "obligor"


def _role_entities(
    roles: Mapping[str, list[str]],
    wanted_roles: set[str],
) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    for role, entities in roles.items():
        normalized_role = _normalize_role(role)
        if normalized_role not in wanted_roles:
            continue
        results.extend((entity, normalized_role) for entity in entities)
    return _dedupe_role_entities(results)


def _party_entities(parties: Iterable[str], role: str) -> list[tuple[str, str]]:
    return _dedupe_role_entities((str(party), role) for party in parties)


def _dedupe_role_entities(items: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[tuple[str, str]] = []
    for entity, role in items:
        key = (_entity_id(str(entity)), role)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((str(entity), role))
    return deduped


def _deal_notional(deal: Deal) -> float:
    tranche_total = sum(tranche.notional_usd for tranche in deal.debt_tranches)
    if tranche_total:
        return float(tranche_total)
    return float(deal.notional_amount_usd or 0.0)


def _ppa_capacity_mw(deal: Deal) -> float:
    for key in ("amount_adjusted_mw", "amount_mw", "capacity_mw"):
        value = deal.key_terms.get(key)
        if value is None or value == "":
            continue
        if not isinstance(value, int | float | str):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0


def _unmapped_deal_row(deal: Deal, reasons: list[str]) -> dict[str, Any]:
    return {
        "deal_ref": deal.source_deal_id or str(deal.id),
        "deal_type": deal.deal_type.value,
        "title": deal.title,
        "notional_usd": _deal_notional(deal),
        "parties": list(deal.parties),
        "source_uri": deal.provenance.source_uri,
        "human_review_status": deal.provenance.human_review_status.value,
        "reasons": reasons,
    }


def _deal_relevance_tags(deal: Deal) -> tuple[str, ...]:
    text = " ".join(
        [
            deal.title or "",
            " ".join(str(party) for party in deal.parties),
            json.dumps(deal.counterparty_roles, sort_keys=True),
            json.dumps(deal.key_terms, sort_keys=True, default=str),
            " ".join(str(project) for project in deal.linked_projects),
            " ".join(str(asset) for asset in deal.linked_assets),
        ]
    )
    tags = [
        f"direct:{name}"
        for name, pattern in DIRECT_AI_INFRA_PATTERNS.items()
        if pattern.search(text)
    ]
    tags.extend(
        f"watchlist:{name}"
        for name, pattern in WATCHLIST_ENTITY_PATTERNS.items()
        if pattern.search(text)
    )
    return tuple(sorted(set(tags)))


def _add_node(
    nodes: dict[str, _NodeAccumulator],
    node_id: str,
    name: str,
    role: str,
    deal_id: str,
    source_uri: str,
    exposure_usd: float,
) -> None:
    acc = nodes.get(node_id)
    if acc is None:
        acc = _NodeAccumulator(name=name)
        nodes[node_id] = acc
    acc.roles.add(role)
    acc.deal_ids.add(deal_id)
    acc.source_uris.add(source_uri)
    acc.exposure_usd += exposure_usd


def _connected_components(edges: list[CapitalExposureEdge]) -> list[set[str]]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        adjacency[edge.source_id].add(edge.target_id)
        adjacency[edge.target_id].add(edge.source_id)

    seen: set[str] = set()
    components: list[set[str]] = []
    for node_id in adjacency:
        if node_id in seen:
            continue
        component: set[str] = set()
        queue: deque[str] = deque([node_id])
        seen.add(node_id)
        while queue:
            current = queue.popleft()
            component.add(current)
            for neighbor in adjacency[current]:
                if neighbor in seen:
                    continue
                seen.add(neighbor)
                queue.append(neighbor)
        components.append(component)
    return components


def _component_risks(
    components: list[set[str]],
    edges: list[CapitalExposureEdge],
    nodes: list[CapitalExposureNode],
) -> list[CapitalExposureComponentRisk]:
    node_by_id = {node.node_id: node for node in nodes}
    risks: list[CapitalExposureComponentRisk] = []
    for component in components:
        component_edges = [
            edge
            for edge in edges
            if edge.source_id in component and edge.target_id in component
        ]
        source_uris = {
            uri
            for edge in component_edges
            for uri in edge.source_uris
            if uri
        }
        top_nodes = sorted(
            (node_by_id[node_id] for node_id in component if node_id in node_by_id),
            key=lambda node: (node.exposure_usd, node.deal_count, node.name),
            reverse=True,
        )[:10]
        top_edges = sorted(
            component_edges,
            key=lambda edge: (edge.notional_usd, edge.deal_count, edge.ppa_capacity_mw),
            reverse=True,
        )[:10]
        risks.append(
            CapitalExposureComponentRisk(
                component_id=_component_id(component),
                node_count=len(component),
                edge_count=len(component_edges),
                notional_usd=round(sum(edge.notional_usd for edge in component_edges), 2),
                ai_infra_relevant_notional_usd=round(
                    sum(edge.notional_usd for edge in component_edges if edge.relevance_tags),
                    2,
                ),
                ppa_capacity_mw=round(sum(edge.ppa_capacity_mw for edge in component_edges), 3),
                source_uri_count=len(source_uris),
                top_entities=[_component_node_row(node) for node in top_nodes],
                top_edges=[_component_edge_row(edge) for edge in top_edges],
            )
        )
    risks.sort(
        key=lambda risk: (
            risk.notional_usd,
            risk.ai_infra_relevant_notional_usd,
            risk.edge_count,
            risk.node_count,
        ),
        reverse=True,
    )
    return risks


def _contagion_hubs(
    edges: list[CapitalExposureEdge],
    nodes: list[CapitalExposureNode],
) -> list[CapitalExposureContagionHub]:
    node_by_id = {node.node_id: node for node in nodes}
    incident_edges: dict[str, list[CapitalExposureEdge]] = defaultdict(list)
    for edge in edges:
        incident_edges[edge.source_id].append(edge)
        incident_edges[edge.target_id].append(edge)

    hubs: list[CapitalExposureContagionHub] = []
    for node in nodes:
        node_edges = incident_edges.get(node.node_id, [])
        if not node_edges:
            continue
        counterparties = _counterparty_rollups(node.node_id, node_edges, node_by_id)
        neighbor_nodes = [
            node_by_id[neighbor_id]
            for neighbor_id in counterparties
            if neighbor_id in node_by_id
        ]
        source_uris = {uri for edge in node_edges for uri in edge.source_uris if uri}
        relevance_tags = sorted({tag for edge in node_edges for tag in edge.relevance_tags})
        hubs.append(
            CapitalExposureContagionHub(
                node_id=node.node_id,
                name=node.name,
                roles=node.roles,
                incident_edge_count=len(node_edges),
                distinct_counterparties=len(counterparties),
                deal_count=node.deal_count,
                incident_notional_usd=round(sum(edge.notional_usd for edge in node_edges), 2),
                ai_infra_relevant_notional_usd=round(
                    sum(edge.notional_usd for edge in node_edges if edge.relevance_tags),
                    2,
                ),
                ppa_capacity_mw=round(sum(edge.ppa_capacity_mw for edge in node_edges), 3),
                source_uri_count=len(source_uris),
                risk_bearer_neighbor_count=sum(_is_risk_bearer_node(item) for item in neighbor_nodes),
                obligor_neighbor_count=sum(_is_obligor_node(item) for item in neighbor_nodes),
                relevance_tags=tuple(relevance_tags),
                top_counterparties=[
                    _counterparty_row(neighbor_id, row, node_by_id)
                    for neighbor_id, row in sorted(
                        counterparties.items(),
                        key=lambda item: (
                            item[1]["ai_infra_relevant_notional_usd"],
                            item[1]["notional_usd"],
                            item[1]["edge_count"],
                        ),
                        reverse=True,
                    )[:10]
                ],
            )
        )

    hubs.sort(
        key=lambda hub: (
            hub.ai_infra_relevant_notional_usd,
            hub.incident_notional_usd,
            hub.distinct_counterparties,
            hub.incident_edge_count,
        ),
        reverse=True,
    )
    return hubs


def _counterparty_rollups(
    node_id: str,
    edges: list[CapitalExposureEdge],
    node_by_id: dict[str, CapitalExposureNode],
) -> dict[str, dict[str, Any]]:
    counterparties: dict[str, dict[str, Any]] = {}
    for edge in edges:
        neighbor_id = edge.target_id if edge.source_id == node_id else edge.source_id
        row = counterparties.setdefault(
            neighbor_id,
            {
                "name": node_by_id[neighbor_id].name if neighbor_id in node_by_id else neighbor_id,
                "edge_count": 0,
                "notional_usd": 0.0,
                "ai_infra_relevant_notional_usd": 0.0,
                "ppa_capacity_mw": 0.0,
                "relationship_types": set(),
                "deal_types": set(),
                "source_uris": set(),
            },
        )
        row["edge_count"] += 1
        row["notional_usd"] += edge.notional_usd
        if edge.relevance_tags:
            row["ai_infra_relevant_notional_usd"] += edge.notional_usd
        row["ppa_capacity_mw"] += edge.ppa_capacity_mw
        row["relationship_types"].add(edge.relationship_type)
        row["deal_types"].add(edge.deal_type)
        row["source_uris"].update(edge.source_uris)
    return counterparties


def _component_id(component: set[str]) -> str:
    raw = "|".join(sorted(component))
    return "component:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def _component_node_row(node: CapitalExposureNode) -> dict[str, Any]:
    return {
        "node_id": node.node_id,
        "name": node.name,
        "roles": node.roles,
        "deal_count": node.deal_count,
        "exposure_usd": node.exposure_usd,
    }


def _component_edge_row(edge: CapitalExposureEdge) -> dict[str, Any]:
    return {
        "source_name": edge.source_name,
        "target_name": edge.target_name,
        "relationship_type": edge.relationship_type,
        "deal_type": edge.deal_type,
        "notional_usd": edge.notional_usd,
        "ppa_capacity_mw": edge.ppa_capacity_mw,
        "relevance_tags": edge.relevance_tags,
        "source_uri_count": len(edge.source_uris),
    }


def _counterparty_row(
    neighbor_id: str,
    row: dict[str, Any],
    node_by_id: dict[str, CapitalExposureNode],
) -> dict[str, Any]:
    neighbor = node_by_id.get(neighbor_id)
    return {
        "node_id": neighbor_id,
        "name": row["name"],
        "roles": neighbor.roles if neighbor else (),
        "edge_count": row["edge_count"],
        "notional_usd": round(row["notional_usd"], 2),
        "ai_infra_relevant_notional_usd": round(row["ai_infra_relevant_notional_usd"], 2),
        "ppa_capacity_mw": round(row["ppa_capacity_mw"], 3),
        "relationship_types": tuple(sorted(row["relationship_types"])),
        "deal_types": tuple(sorted(row["deal_types"])),
        "source_uri_count": len(row["source_uris"]),
    }


def _is_risk_bearer_node(node: CapitalExposureNode) -> bool:
    return bool(set(node.roles).intersection(RISK_BEARER_ROLES))


def _is_obligor_node(node: CapitalExposureNode) -> bool:
    return bool(set(node.roles).intersection(OBLIGOR_ROLES | PPA_SOURCE_ROLES))


def _is_generic_entity(name: str) -> bool:
    return is_generic_entity_name(name)


def _entity_id(name: str) -> str:
    tokens = re.sub(r"[^a-z0-9]+", " ", name.lower()).split()
    if len(tokens) >= 2 and tokens[-2:] == ["n", "a"]:
        tokens = tokens[:-2]
    while tokens and tokens[-1] in ENTITY_SUFFIX_TOKENS:
        tokens = tokens[:-1]
    normalized = "-".join(tokens)
    return f"entity:{normalized or 'unknown'}"


def _normalize_role(role: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", role.lower()).strip("_")


def _deal_type_values(deal_types: set[DealType]) -> set[str]:
    return {deal_type.value for deal_type in deal_types}


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
    if isinstance(value, bool | int | float | str):
        return value
    if value is None:
        return ""
    return str(value)
