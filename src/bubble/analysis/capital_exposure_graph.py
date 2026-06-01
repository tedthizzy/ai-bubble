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
class CapitalContractNode:
    """Source-backed deal/tranche/collateral/project structure node."""

    node_id: str
    node_type: str
    name: str
    deal_id: str
    deal_type: str
    tranche_id: str
    notional_usd: float
    interest_rate: float | None
    maturity: str
    source_uri: str
    content_hash: str
    human_review_status: str
    relevance_tags: tuple[str, ...]
    risk_flags: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapitalContractEdge:
    """Source-backed structural relationship inside a capital contract."""

    source_id: str
    source_name: str
    source_type: str
    target_id: str
    target_name: str
    target_type: str
    relationship_type: str
    deal_id: str
    deal_type: str
    tranche_id: str
    notional_usd: float
    source_uri: str
    content_hash: str
    human_review_status: str
    relevance_tags: tuple[str, ...]
    risk_flags: tuple[str, ...]

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
    contract_nodes: int
    contract_edges: int
    source_backed_contract_edges: int
    deal_contract_nodes: int
    tranche_contract_nodes: int
    collateral_contract_nodes: int
    guarantee_contract_edges: int
    collateral_contract_edges: int
    project_contract_edges: int
    asset_contract_edges: int
    non_recourse_contracts: int
    bankruptcy_remote_spv_contracts: int
    spv_flagged_contracts: int
    tranche_nodes_with_maturity: int
    tranche_nodes_with_interest_rate: int
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
    top_tranche_contract_nodes: list[dict[str, Any]]
    top_spv_contract_nodes: list[dict[str, Any]]
    top_collateral_contract_edges: list[dict[str, Any]]
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
    contract_nodes: list[CapitalContractNode]
    contract_edges: list[CapitalContractEdge]
    summary: CapitalExposureGraphSummary


def build_capital_exposure_graph(deals: list[Deal]) -> CapitalExposureGraph:
    """Build a source-backed exposure graph from capital deal evidence."""

    node_acc: dict[str, _NodeAccumulator] = {}
    edge_acc: dict[tuple[str, str, str, str], _EdgeAccumulator] = {}
    contract_node_acc: dict[str, CapitalContractNode] = {}
    contract_edge_acc: dict[
        tuple[str, str, str, str, str, str],
        CapitalContractEdge,
    ] = {}
    generic_skipped = 0
    deals_with_edges = 0
    high_notional_unmapped: list[dict[str, Any]] = []
    all_source_uris: set[str] = set()

    for deal in deals:
        all_source_uris.add(deal.provenance.source_uri)
        contract_nodes, contract_edges, _contract_skipped = _contract_graph_for_deal(deal)
        for node in contract_nodes:
            _merge_contract_node(contract_node_acc, node)
        for contract_edge in contract_edges:
            _merge_contract_edge(contract_edge_acc, contract_edge)

        deal_edges, skipped = _edges_for_deal(deal)
        generic_skipped += skipped
        if deal_edges:
            deals_with_edges += 1
        elif _deal_notional(deal) >= 25_000_000_000:
            high_notional_unmapped.append(_unmapped_deal_row(deal, ["no_named_counterparty_edge"]))

        for deal_edge in deal_edges:
            key = (
                deal_edge["source_id"],
                deal_edge["target_id"],
                deal_edge["relationship_type"],
                deal_edge["deal_type"],
            )
            acc = edge_acc.get(key)
            if acc is None:
                acc = _EdgeAccumulator(
                    source_id=deal_edge["source_id"],
                    source_name=deal_edge["source_name"],
                    target_id=deal_edge["target_id"],
                    target_name=deal_edge["target_name"],
                    relationship_type=deal_edge["relationship_type"],
                    deal_type=deal_edge["deal_type"],
                )
                edge_acc[key] = acc
            acc.roles.add(deal_edge["role"])
            acc.deal_ids.add(deal_edge["deal_id"])
            acc.source_uris.add(deal_edge["source_uri"])
            acc.content_hashes.add(deal_edge["content_hash"])
            acc.human_review_statuses.add(deal_edge["human_review_status"])
            acc.relevance_tags.update(deal_edge["relevance_tags"])
            acc.notional_usd += deal_edge["notional_usd"]
            acc.ppa_capacity_mw += deal_edge["ppa_capacity_mw"]

            _add_node(
                node_acc,
                deal_edge["source_id"],
                deal_edge["source_name"],
                deal_edge["source_role"],
                deal_edge["deal_id"],
                deal_edge["source_uri"],
                deal_edge["notional_usd"],
            )
            _add_node(
                node_acc,
                deal_edge["target_id"],
                deal_edge["target_name"],
                deal_edge["target_role"],
                deal_edge["deal_id"],
                deal_edge["source_uri"],
                deal_edge["notional_usd"],
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
    contract_nodes = list(contract_node_acc.values())
    contract_nodes.sort(
        key=lambda node: (node.notional_usd, node.node_type == "tranche", node.name),
        reverse=True,
    )
    contract_edges = list(contract_edge_acc.values())
    contract_edges.sort(
        key=lambda edge: (edge.notional_usd, edge.relationship_type, edge.source_name),
        reverse=True,
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

    summary = _build_capital_exposure_summary(
        deals_scanned=len(deals),
        deals_with_edges=deals_with_edges,
        generic_skipped=generic_skipped,
        all_source_uris=all_source_uris,
        nodes=nodes,
        edges=edges,
        contract_nodes=contract_nodes,
        contract_edges=contract_edges,
        components=components,
        largest_component=largest_component,
        largest_component_risk=largest_component_risk,
        component_risks=component_risks,
        contagion_hubs=contagion_hubs,
        high_notional_unmapped=high_notional_unmapped,
    )
    return CapitalExposureGraph(
        nodes=nodes,
        edges=edges,
        contract_nodes=contract_nodes,
        contract_edges=contract_edges,
        summary=summary,
    )


def _build_capital_exposure_summary(
    *,
    deals_scanned: int,
    deals_with_edges: int,
    generic_skipped: int,
    all_source_uris: set[str],
    nodes: list[CapitalExposureNode],
    edges: list[CapitalExposureEdge],
    contract_nodes: list[CapitalContractNode],
    contract_edges: list[CapitalContractEdge],
    components: list[set[str]],
    largest_component: set[str],
    largest_component_risk: CapitalExposureComponentRisk | None,
    component_risks: list[CapitalExposureComponentRisk],
    contagion_hubs: list[CapitalExposureContagionHub],
    high_notional_unmapped: list[dict[str, Any]],
) -> CapitalExposureGraphSummary:
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
    tranche_contract_nodes = [node for node in contract_nodes if node.node_type == "tranche"]
    spv_contract_nodes = [
        node
        for node in contract_nodes
        if node.node_type in {"deal", "tranche"}
        and any(flag in node.risk_flags for flag in ("spv_signal", "bankruptcy_remote_spv"))
    ]
    collateral_contract_edges = [
        edge for edge in contract_edges if edge.relationship_type == "SECURED_BY_COLLATERAL"
    ]
    return CapitalExposureGraphSummary(
        deals_scanned=deals_scanned,
        deals_with_edges=deals_with_edges,
        deals_without_named_counterparty_edges=deals_scanned - deals_with_edges,
        nodes=len(nodes),
        edges=len(edges),
        source_backed_edges=sum(1 for edge in edges if edge.source_uris),
        debt_like_edges=sum(
            1 for edge in edges if edge.deal_type in _deal_type_values(DEBT_LIKE_DEAL_TYPES)
        ),
        ppa_edges=sum(1 for edge in edges if edge.deal_type == DealType.PPA.value),
        edges_with_notional=sum(1 for edge in edges if edge.notional_usd > 0),
        contract_nodes=len(contract_nodes),
        contract_edges=len(contract_edges),
        source_backed_contract_edges=sum(1 for edge in contract_edges if edge.source_uri),
        deal_contract_nodes=sum(1 for node in contract_nodes if node.node_type == "deal"),
        tranche_contract_nodes=len(tranche_contract_nodes),
        collateral_contract_nodes=sum(
            1 for node in contract_nodes if node.node_type == "collateral"
        ),
        guarantee_contract_edges=sum(
            1
            for edge in contract_edges
            if edge.relationship_type in {"GUARANTEED_BY", "TRANCHE_GUARANTEED_BY"}
        ),
        collateral_contract_edges=len(collateral_contract_edges),
        project_contract_edges=sum(
            1 for edge in contract_edges if edge.relationship_type == "LINKED_TO_PROJECT"
        ),
        asset_contract_edges=sum(
            1 for edge in contract_edges if edge.relationship_type == "LINKED_TO_ASSET"
        ),
        non_recourse_contracts=sum(
            1
            for node in contract_nodes
            if node.node_type in {"deal", "tranche"} and "non_recourse" in node.risk_flags
        ),
        bankruptcy_remote_spv_contracts=sum(
            1
            for node in contract_nodes
            if node.node_type in {"deal", "tranche"} and "bankruptcy_remote_spv" in node.risk_flags
        ),
        spv_flagged_contracts=len(spv_contract_nodes),
        tranche_nodes_with_maturity=sum(1 for node in tranche_contract_nodes if node.maturity),
        tranche_nodes_with_interest_rate=sum(
            1 for node in tranche_contract_nodes if node.interest_rate is not None
        ),
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
        largest_component_edges=largest_component_risk.edge_count if largest_component_risk else 0,
        largest_component_notional_usd=largest_component_risk.notional_usd
        if largest_component_risk
        else 0.0,
        largest_component_ai_infra_relevant_notional_usd=(
            largest_component_risk.ai_infra_relevant_notional_usd if largest_component_risk else 0.0
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
            hub.to_dict() for hub in contagion_hubs if hub.ai_infra_relevant_notional_usd > 0
        ][:25],
        top_tranche_contract_nodes=[node.to_dict() for node in tranche_contract_nodes[:25]],
        top_spv_contract_nodes=[node.to_dict() for node in spv_contract_nodes[:25]],
        top_collateral_contract_edges=[edge.to_dict() for edge in collateral_contract_edges[:25]],
        high_notional_unmapped_deals=high_notional_unmapped[:25],
    )


def write_capital_exposure_graph(
    graph: CapitalExposureGraph, output_dir: str | Path
) -> dict[str, str]:
    """Write graph nodes, edges, and summary to disk."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    nodes_path = out / "capital_exposure_nodes.csv"
    edges_path = out / "capital_exposure_edges.csv"
    contract_nodes_path = out / "capital_contract_nodes.csv"
    contract_edges_path = out / "capital_contract_edges.csv"
    summary_path = out / "capital_exposure_graph_summary.json"

    _write_csv(nodes_path, [node.to_dict() for node in graph.nodes])
    _write_csv(edges_path, [edge.to_dict() for edge in graph.edges])
    _write_csv(contract_nodes_path, [node.to_dict() for node in graph.contract_nodes])
    _write_csv(contract_edges_path, [edge.to_dict() for edge in graph.contract_edges])
    summary_path.write_text(json.dumps(graph.summary.to_dict(), indent=2))
    return {
        "nodes_csv": str(nodes_path),
        "edges_csv": str(edges_path),
        "contract_nodes_csv": str(contract_nodes_path),
        "contract_edges_csv": str(contract_edges_path),
        "summary_json": str(summary_path),
    }


def _contract_graph_for_deal(
    deal: Deal,
) -> tuple[list[CapitalContractNode], list[CapitalContractEdge], int]:
    deal_id = _deal_ref(deal)
    deal_node_id = _deal_contract_node_id(deal)
    deal_name = deal.title or deal_id
    relevance_tags = _deal_relevance_tags(deal)
    deal_flags = _deal_risk_flags(deal)
    notional = _deal_notional(deal)
    nodes = [_deal_contract_node(deal, deal_node_id, deal_name, relevance_tags, deal_flags)]
    edges: list[CapitalContractEdge] = []
    obligors, risk_bearers, guarantors = _deal_contract_participants(deal)
    generic_skipped = _add_contract_entity_edges(
        nodes,
        edges,
        entities=obligors,
        entity_as_source=True,
        anchor_id=deal_node_id,
        anchor_name=deal_name,
        anchor_type="deal",
        relationship_type="OBLIGATED_UNDER_DEAL",
        deal=deal,
        tranche_id="",
        notional_usd=notional,
        source_uri=deal.provenance.source_uri,
        content_hash=deal.provenance.content_hash,
        human_review_status=deal.provenance.human_review_status.value,
        relevance_tags=relevance_tags,
        risk_flags=deal_flags,
    )
    generic_skipped += _add_contract_entity_edges(
        nodes,
        edges,
        entities=risk_bearers,
        entity_as_source=False,
        anchor_id=deal_node_id,
        anchor_name=deal_name,
        anchor_type="deal",
        relationship_type="DEAL_RISK_BEARER",
        deal=deal,
        tranche_id="",
        notional_usd=notional,
        source_uri=deal.provenance.source_uri,
        content_hash=deal.provenance.content_hash,
        human_review_status=deal.provenance.human_review_status.value,
        relevance_tags=relevance_tags,
        risk_flags=deal_flags,
    )
    generic_skipped += _add_contract_entity_edges(
        nodes,
        edges,
        entities=guarantors,
        entity_as_source=False,
        anchor_id=deal_node_id,
        anchor_name=deal_name,
        anchor_type="deal",
        relationship_type="GUARANTEED_BY",
        deal=deal,
        tranche_id="",
        notional_usd=notional,
        source_uri=deal.provenance.source_uri,
        content_hash=deal.provenance.content_hash,
        human_review_status=deal.provenance.human_review_status.value,
        relevance_tags=relevance_tags,
        risk_flags=(*deal_flags, "guarantee_linked"),
    )
    _add_deal_collateral_project_asset_edges(
        nodes,
        edges,
        deal=deal,
        deal_node_id=deal_node_id,
        deal_name=deal_name,
        notional_usd=notional,
        relevance_tags=relevance_tags,
        risk_flags=deal_flags,
    )
    for index, tranche in enumerate(deal.debt_tranches, start=1):
        generic_skipped += _add_tranche_contract_graph(
            nodes,
            edges,
            deal=deal,
            deal_node_id=deal_node_id,
            deal_name=deal_name,
            index=index,
            tranche=tranche,
            obligors=obligors,
            risk_bearers=risk_bearers,
            guarantors=guarantors,
            relevance_tags=relevance_tags,
        )
    return nodes, edges, generic_skipped


def _deal_contract_node(
    deal: Deal,
    deal_node_id: str,
    deal_name: str,
    relevance_tags: tuple[str, ...],
    deal_flags: tuple[str, ...],
) -> CapitalContractNode:
    return _contract_node(
        node_id=deal_node_id,
        node_type="deal",
        name=deal_name,
        deal_id=_deal_ref(deal),
        deal_type=deal.deal_type.value,
        tranche_id="",
        notional_usd=_deal_notional(deal),
        interest_rate=None,
        maturity=_date_text(deal.maturity_date),
        source_uri=deal.provenance.source_uri,
        content_hash=deal.provenance.content_hash,
        human_review_status=deal.provenance.human_review_status.value,
        relevance_tags=relevance_tags,
        risk_flags=deal_flags,
    )


def _deal_contract_participants(
    deal: Deal,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]], list[tuple[str, str]]]:
    if deal.deal_type == DealType.PPA:
        obligors = _role_entities(deal.counterparty_roles, PPA_SOURCE_ROLES) or _party_entities(
            deal.parties[:1],
            "seller",
        )
        risk_bearers = _role_entities(deal.counterparty_roles, PPA_TARGET_ROLES) or _party_entities(
            deal.parties[1:],
            "counterparty",
        )
    else:
        obligors = _role_entities(deal.counterparty_roles, OBLIGOR_ROLES) or _party_entities(
            deal.parties[:1],
            _source_role_for_deal(deal),
        )
        risk_bearers = _role_entities(deal.counterparty_roles, RISK_BEARER_ROLES)
        if not risk_bearers:
            risk_bearers = _party_entities(deal.parties[1:], "counterparty")
    return obligors, risk_bearers, _guarantor_entities(deal)


def _add_contract_entity_edges(
    nodes: list[CapitalContractNode],
    edges: list[CapitalContractEdge],
    *,
    entities: Iterable[tuple[str, str]],
    entity_as_source: bool,
    anchor_id: str,
    anchor_name: str,
    anchor_type: str,
    relationship_type: str,
    deal: Deal,
    tranche_id: str,
    notional_usd: float,
    source_uri: str,
    content_hash: str,
    human_review_status: str,
    relevance_tags: tuple[str, ...],
    risk_flags: tuple[str, ...],
) -> int:
    generic_skipped = 0
    for entity, role in entities:
        entity_node = _entity_contract_node(entity, role, deal, relevance_tags)
        if entity_node is None:
            generic_skipped += 1
            continue
        nodes.append(entity_node)
        source = (entity_node.node_id, entity_node.name, "entity")
        target = (anchor_id, anchor_name, anchor_type)
        if not entity_as_source:
            source, target = target, source
        edges.append(
            _contract_edge(
                source_id=source[0],
                source_name=source[1],
                source_type=source[2],
                target_id=target[0],
                target_name=target[1],
                target_type=target[2],
                relationship_type=relationship_type,
                deal=deal,
                tranche_id=tranche_id,
                notional_usd=notional_usd,
                source_uri=source_uri,
                content_hash=content_hash,
                human_review_status=human_review_status,
                relevance_tags=relevance_tags,
                risk_flags=risk_flags,
            )
        )
    return generic_skipped


def _add_deal_collateral_project_asset_edges(
    nodes: list[CapitalContractNode],
    edges: list[CapitalContractEdge],
    *,
    deal: Deal,
    deal_node_id: str,
    deal_name: str,
    notional_usd: float,
    relevance_tags: tuple[str, ...],
    risk_flags: tuple[str, ...],
) -> None:
    _add_collateral_contract_edges(
        nodes,
        edges,
        source_id=deal_node_id,
        source_name=deal_name,
        source_type="deal",
        deal=deal,
        tranche_id="",
        collateral_descriptions=deal.collateral,
        notional_usd=notional_usd,
        source_uri=deal.provenance.source_uri,
        content_hash=deal.provenance.content_hash,
        human_review_status=deal.provenance.human_review_status.value,
        relevance_tags=relevance_tags,
        risk_flags=risk_flags,
    )
    _add_project_asset_contract_edges(
        nodes,
        edges,
        source_id=deal_node_id,
        source_name=deal_name,
        source_type="deal",
        deal=deal,
        notional_usd=notional_usd,
        relevance_tags=relevance_tags,
        risk_flags=risk_flags,
    )


def _add_tranche_contract_graph(
    nodes: list[CapitalContractNode],
    edges: list[CapitalContractEdge],
    *,
    deal: Deal,
    deal_node_id: str,
    deal_name: str,
    index: int,
    tranche: Any,
    obligors: list[tuple[str, str]],
    risk_bearers: list[tuple[str, str]],
    guarantors: list[tuple[str, str]],
    relevance_tags: tuple[str, ...],
) -> int:
    deal_id = _deal_ref(deal)
    tranche_id = _tranche_ref(deal_id, index, tranche.name)
    tranche_node_id = _tranche_contract_node_id(deal_id, index, tranche.name)
    tranche_flags = _tranche_risk_flags(deal, tranche)
    tranche_tags = tuple(sorted(set(relevance_tags) | set(_tranche_relevance_tags(tranche))))
    tranche_name = f"{deal_name} - {tranche.name}"
    tranche_notional = float(tranche.notional_usd)
    nodes.append(
        _contract_node(
            node_id=tranche_node_id,
            node_type="tranche",
            name=tranche_name,
            deal_id=deal_id,
            deal_type=deal.deal_type.value,
            tranche_id=tranche_id,
            notional_usd=tranche_notional,
            interest_rate=tranche.interest_rate,
            maturity=_date_text(tranche.maturity),
            source_uri=tranche.provenance.source_uri,
            content_hash=tranche.provenance.content_hash,
            human_review_status=tranche.provenance.human_review_status.value,
            relevance_tags=tranche_tags,
            risk_flags=tranche_flags,
        )
    )
    edges.append(
        _contract_edge(
            source_id=deal_node_id,
            source_name=deal_name,
            source_type="deal",
            target_id=tranche_node_id,
            target_name=tranche_name,
            target_type="tranche",
            relationship_type="HAS_TRANCHE",
            deal=deal,
            tranche_id=tranche_id,
            notional_usd=tranche_notional,
            source_uri=tranche.provenance.source_uri,
            content_hash=tranche.provenance.content_hash,
            human_review_status=tranche.provenance.human_review_status.value,
            relevance_tags=tranche_tags,
            risk_flags=tranche_flags,
        )
    )
    generic_skipped = _add_contract_entity_edges(
        nodes,
        edges,
        entities=obligors,
        entity_as_source=True,
        anchor_id=tranche_node_id,
        anchor_name=tranche_name,
        anchor_type="tranche",
        relationship_type="OBLIGOR_TO_TRANCHE",
        deal=deal,
        tranche_id=tranche_id,
        notional_usd=tranche_notional,
        source_uri=tranche.provenance.source_uri,
        content_hash=tranche.provenance.content_hash,
        human_review_status=tranche.provenance.human_review_status.value,
        relevance_tags=tranche_tags,
        risk_flags=tranche_flags,
    )
    generic_skipped += _add_contract_entity_edges(
        nodes,
        edges,
        entities=risk_bearers,
        entity_as_source=False,
        anchor_id=tranche_node_id,
        anchor_name=tranche_name,
        anchor_type="tranche",
        relationship_type="TRANCHE_RISK_BEARER",
        deal=deal,
        tranche_id=tranche_id,
        notional_usd=tranche_notional,
        source_uri=tranche.provenance.source_uri,
        content_hash=tranche.provenance.content_hash,
        human_review_status=tranche.provenance.human_review_status.value,
        relevance_tags=tranche_tags,
        risk_flags=tranche_flags,
    )
    generic_skipped += _add_contract_entity_edges(
        nodes,
        edges,
        entities=_dedupe_role_entities(
            [(str(entity), "guarantor") for entity in tranche.guarantors] + guarantors
        ),
        entity_as_source=False,
        anchor_id=tranche_node_id,
        anchor_name=tranche_name,
        anchor_type="tranche",
        relationship_type="TRANCHE_GUARANTEED_BY",
        deal=deal,
        tranche_id=tranche_id,
        notional_usd=tranche_notional,
        source_uri=tranche.provenance.source_uri,
        content_hash=tranche.provenance.content_hash,
        human_review_status=tranche.provenance.human_review_status.value,
        relevance_tags=tranche_tags,
        risk_flags=(*tranche_flags, "guarantee_linked"),
    )
    _add_collateral_contract_edges(
        nodes,
        edges,
        source_id=tranche_node_id,
        source_name=tranche_name,
        source_type="tranche",
        deal=deal,
        tranche_id=tranche_id,
        collateral_descriptions=[
            item for item in [tranche.collateral_description, *deal.collateral] if item
        ],
        notional_usd=tranche_notional,
        source_uri=tranche.provenance.source_uri,
        content_hash=tranche.provenance.content_hash,
        human_review_status=tranche.provenance.human_review_status.value,
        relevance_tags=tranche_tags,
        risk_flags=tranche_flags,
    )
    return generic_skipped


def _contract_node(
    *,
    node_id: str,
    node_type: str,
    name: str,
    deal_id: str,
    deal_type: str,
    tranche_id: str,
    notional_usd: float,
    interest_rate: float | None,
    maturity: str,
    source_uri: str,
    content_hash: str,
    human_review_status: str,
    relevance_tags: tuple[str, ...],
    risk_flags: tuple[str, ...],
) -> CapitalContractNode:
    return CapitalContractNode(
        node_id=node_id,
        node_type=node_type,
        name=name,
        deal_id=deal_id,
        deal_type=deal_type,
        tranche_id=tranche_id,
        notional_usd=round(notional_usd, 2),
        interest_rate=interest_rate,
        maturity=maturity,
        source_uri=source_uri,
        content_hash=content_hash,
        human_review_status=human_review_status,
        relevance_tags=tuple(sorted(set(relevance_tags))),
        risk_flags=tuple(sorted(set(risk_flags))),
    )


def _contract_edge(
    *,
    source_id: str,
    source_name: str,
    source_type: str,
    target_id: str,
    target_name: str,
    target_type: str,
    relationship_type: str,
    deal: Deal,
    tranche_id: str,
    notional_usd: float,
    source_uri: str,
    content_hash: str,
    human_review_status: str,
    relevance_tags: tuple[str, ...],
    risk_flags: tuple[str, ...],
) -> CapitalContractEdge:
    return CapitalContractEdge(
        source_id=source_id,
        source_name=source_name,
        source_type=source_type,
        target_id=target_id,
        target_name=target_name,
        target_type=target_type,
        relationship_type=relationship_type,
        deal_id=_deal_ref(deal),
        deal_type=deal.deal_type.value,
        tranche_id=tranche_id,
        notional_usd=round(notional_usd, 2),
        source_uri=source_uri,
        content_hash=content_hash,
        human_review_status=human_review_status,
        relevance_tags=tuple(sorted(set(relevance_tags))),
        risk_flags=tuple(sorted(set(risk_flags))),
    )


def _entity_contract_node(
    entity: str,
    role: str,
    deal: Deal,
    relevance_tags: tuple[str, ...],
) -> CapitalContractNode | None:
    name = str(entity).strip()
    if not name or _is_generic_entity(name):
        return None
    risk_flags = ("spv_signal",) if _looks_like_spv_name(name) else ()
    return _contract_node(
        node_id=_entity_id(name),
        node_type="entity",
        name=name,
        deal_id=_deal_ref(deal),
        deal_type=deal.deal_type.value,
        tranche_id="",
        notional_usd=0.0,
        interest_rate=None,
        maturity="",
        source_uri=deal.provenance.source_uri,
        content_hash=deal.provenance.content_hash,
        human_review_status=deal.provenance.human_review_status.value,
        relevance_tags=relevance_tags,
        risk_flags=(_normalize_role(role), *risk_flags),
    )


def _add_collateral_contract_edges(
    nodes: list[CapitalContractNode],
    edges: list[CapitalContractEdge],
    *,
    source_id: str,
    source_name: str,
    source_type: str,
    deal: Deal,
    tranche_id: str,
    collateral_descriptions: Iterable[str],
    notional_usd: float,
    source_uri: str,
    content_hash: str,
    human_review_status: str,
    relevance_tags: tuple[str, ...],
    risk_flags: tuple[str, ...],
) -> None:
    for index, description in enumerate(collateral_descriptions, start=1):
        clean = " ".join(str(description).split())
        if not clean:
            continue
        collateral_id = _collateral_node_id(clean)
        collateral_name = clean[:240]
        collateral_flags = (*risk_flags, "collateralized")
        nodes.append(
            _contract_node(
                node_id=collateral_id,
                node_type="collateral",
                name=collateral_name,
                deal_id=_deal_ref(deal),
                deal_type=deal.deal_type.value,
                tranche_id=tranche_id,
                notional_usd=notional_usd,
                interest_rate=None,
                maturity="",
                source_uri=source_uri,
                content_hash=content_hash,
                human_review_status=human_review_status,
                relevance_tags=relevance_tags,
                risk_flags=collateral_flags,
            )
        )
        edges.append(
            _contract_edge(
                source_id=source_id,
                source_name=source_name,
                source_type=source_type,
                target_id=collateral_id,
                target_name=collateral_name,
                target_type="collateral",
                relationship_type="SECURED_BY_COLLATERAL",
                deal=deal,
                tranche_id=tranche_id or f"collateral:{index}",
                notional_usd=notional_usd,
                source_uri=source_uri,
                content_hash=content_hash,
                human_review_status=human_review_status,
                relevance_tags=relevance_tags,
                risk_flags=collateral_flags,
            )
        )


def _add_project_asset_contract_edges(
    nodes: list[CapitalContractNode],
    edges: list[CapitalContractEdge],
    *,
    source_id: str,
    source_name: str,
    source_type: str,
    deal: Deal,
    notional_usd: float,
    relevance_tags: tuple[str, ...],
    risk_flags: tuple[str, ...],
) -> None:
    for project in deal.linked_projects:
        clean = str(project).strip()
        if not clean:
            continue
        node_id = _project_node_id(clean)
        nodes.append(
            _contract_node(
                node_id=node_id,
                node_type="project",
                name=clean,
                deal_id=_deal_ref(deal),
                deal_type=deal.deal_type.value,
                tranche_id="",
                notional_usd=0.0,
                interest_rate=None,
                maturity="",
                source_uri=deal.provenance.source_uri,
                content_hash=deal.provenance.content_hash,
                human_review_status=deal.provenance.human_review_status.value,
                relevance_tags=relevance_tags,
                risk_flags=risk_flags,
            )
        )
        edges.append(
            _contract_edge(
                source_id=source_id,
                source_name=source_name,
                source_type=source_type,
                target_id=node_id,
                target_name=clean,
                target_type="project",
                relationship_type="LINKED_TO_PROJECT",
                deal=deal,
                tranche_id="",
                notional_usd=notional_usd,
                source_uri=deal.provenance.source_uri,
                content_hash=deal.provenance.content_hash,
                human_review_status=deal.provenance.human_review_status.value,
                relevance_tags=relevance_tags,
                risk_flags=risk_flags,
            )
        )
    for asset in deal.linked_assets:
        clean = str(asset).strip()
        if not clean:
            continue
        node_id = _asset_node_id(clean)
        nodes.append(
            _contract_node(
                node_id=node_id,
                node_type="asset",
                name=clean,
                deal_id=_deal_ref(deal),
                deal_type=deal.deal_type.value,
                tranche_id="",
                notional_usd=0.0,
                interest_rate=None,
                maturity="",
                source_uri=deal.provenance.source_uri,
                content_hash=deal.provenance.content_hash,
                human_review_status=deal.provenance.human_review_status.value,
                relevance_tags=relevance_tags,
                risk_flags=risk_flags,
            )
        )
        edges.append(
            _contract_edge(
                source_id=source_id,
                source_name=source_name,
                source_type=source_type,
                target_id=node_id,
                target_name=clean,
                target_type="asset",
                relationship_type="LINKED_TO_ASSET",
                deal=deal,
                tranche_id="",
                notional_usd=notional_usd,
                source_uri=deal.provenance.source_uri,
                content_hash=deal.provenance.content_hash,
                human_review_status=deal.provenance.human_review_status.value,
                relevance_tags=relevance_tags,
                risk_flags=risk_flags,
            )
        )


def _merge_contract_node(
    nodes: dict[str, CapitalContractNode],
    node: CapitalContractNode,
) -> None:
    current = nodes.get(node.node_id)
    if current is None:
        nodes[node.node_id] = node
        return
    nodes[node.node_id] = CapitalContractNode(
        node_id=current.node_id,
        node_type=current.node_type,
        name=current.name,
        deal_id=current.deal_id or node.deal_id,
        deal_type=current.deal_type or node.deal_type,
        tranche_id=current.tranche_id or node.tranche_id,
        notional_usd=max(current.notional_usd, node.notional_usd),
        interest_rate=current.interest_rate
        if current.interest_rate is not None
        else node.interest_rate,
        maturity=current.maturity or node.maturity,
        source_uri=current.source_uri or node.source_uri,
        content_hash=current.content_hash or node.content_hash,
        human_review_status=current.human_review_status or node.human_review_status,
        relevance_tags=tuple(sorted(set(current.relevance_tags) | set(node.relevance_tags))),
        risk_flags=tuple(sorted(set(current.risk_flags) | set(node.risk_flags))),
    )


def _merge_contract_edge(
    edges: dict[tuple[str, str, str, str, str, str], CapitalContractEdge],
    edge: CapitalContractEdge,
) -> None:
    key = (
        edge.source_id,
        edge.target_id,
        edge.relationship_type,
        edge.deal_id,
        edge.tranche_id,
        edge.content_hash,
    )
    current = edges.get(key)
    if current is None:
        edges[key] = edge
        return
    edges[key] = CapitalContractEdge(
        source_id=current.source_id,
        source_name=current.source_name,
        source_type=current.source_type,
        target_id=current.target_id,
        target_name=current.target_name,
        target_type=current.target_type,
        relationship_type=current.relationship_type,
        deal_id=current.deal_id,
        deal_type=current.deal_type,
        tranche_id=current.tranche_id,
        notional_usd=max(current.notional_usd, edge.notional_usd),
        source_uri=current.source_uri or edge.source_uri,
        content_hash=current.content_hash or edge.content_hash,
        human_review_status=current.human_review_status or edge.human_review_status,
        relevance_tags=tuple(sorted(set(current.relevance_tags) | set(edge.relevance_tags))),
        risk_flags=tuple(sorted(set(current.risk_flags) | set(edge.risk_flags))),
    )


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


def _guarantor_entities(deal: Deal) -> list[tuple[str, str]]:
    return _dedupe_role_entities(
        [
            *_role_entities(deal.counterparty_roles, {"guarantor"}),
            *((str(entity), "guarantor") for entity in deal.guarantees),
        ]
    )


def _deal_ref(deal: Deal) -> str:
    return deal.source_deal_id or str(deal.id)


def _deal_contract_node_id(deal: Deal) -> str:
    return f"contract:deal:{_stable_fragment(_deal_ref(deal))}"


def _tranche_contract_node_id(deal_id: str, index: int, name: str) -> str:
    return f"contract:tranche:{_stable_fragment(deal_id)}:{index}:{_stable_fragment(name)}"


def _tranche_ref(deal_id: str, index: int, name: str) -> str:
    return f"{deal_id}:tranche:{index}:{_stable_fragment(name)}"


def _collateral_node_id(description: str) -> str:
    return f"collateral:{hashlib.sha256(description.lower().encode()).hexdigest()[:16]}"


def _project_node_id(name: str) -> str:
    return f"project:{_stable_fragment(name)}"


def _asset_node_id(name: str) -> str:
    return f"asset:{_stable_fragment(name)}"


def _stable_fragment(value: str) -> str:
    tokens = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if tokens:
        return tokens[:80]
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def _date_text(value: Any) -> str:
    return value.isoformat() if value else ""


def _deal_risk_flags(deal: Deal) -> tuple[str, ...]:
    flags: set[str] = set()
    if deal.is_non_recourse:
        flags.add("non_recourse")
    if deal.bankruptcy_remote_spv:
        flags.update({"bankruptcy_remote_spv", "spv_signal"})
    if deal.is_related_party:
        flags.add("related_party")
    if deal.concentration_risk_flag:
        flags.add("concentration_risk")
    if deal.collateral:
        flags.add("collateralized")
    if deal.guarantees or _role_entities(deal.counterparty_roles, {"guarantor"}):
        flags.add("guarantee_linked")
    if _deal_has_spv_signal(deal):
        flags.add("spv_signal")
    if deal.debt_tranches:
        flags.add("tranched")
    flags.update(_notional_scope_risk_flags(deal))
    return tuple(sorted(flags))


def _notional_scope_risk_flags(deal: Deal) -> set[str]:
    flags: set[str] = set()
    commitment_scope = str(deal.key_terms.get("notional_commitment_scope") or "").strip().lower()
    if commitment_scope == "aggregate_snapshot_non_specific":
        flags.update({"aggregate_snapshot", "non_specific_obligation"})
    elif commitment_scope == "shelf_capacity_non_specific":
        flags.update({"shelf_capacity", "non_specific_obligation"})
    context_kind = str(deal.key_terms.get("notional_context_kind") or "").strip().lower()
    if context_kind.startswith("aggregate_"):
        flags.add("aggregate_snapshot")
        if context_kind == "aggregate_shelf_capacity":
            flags.add("shelf_capacity")
    if bool(deal.key_terms.get("notional_non_specific_obligation")):
        flags.add("non_specific_obligation")
    return flags


def _tranche_risk_flags(deal: Deal, tranche: Any) -> tuple[str, ...]:
    flags = set(_deal_risk_flags(deal))
    if tranche.collateral_description:
        flags.add("collateralized")
    if tranche.guarantors:
        flags.add("guarantee_linked")
    if tranche.maturity:
        flags.add("maturity_wall")
    if tranche.interest_rate is not None:
        flags.add("priced_debt")
    if tranche.recourse:
        flags.add("recourse")
    return tuple(sorted(flags))


def _tranche_relevance_tags(tranche: Any) -> tuple[str, ...]:
    text = " ".join(
        [
            str(tranche.name),
            tranche.collateral_description or "",
            " ".join(str(guarantor) for guarantor in tranche.guarantors),
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


def _deal_has_spv_signal(deal: Deal) -> bool:
    text = " ".join(
        [
            deal.title or "",
            " ".join(str(party) for party in deal.parties),
            json.dumps(deal.counterparty_roles, sort_keys=True),
            json.dumps(deal.key_terms, sort_keys=True, default=str),
        ]
    )
    return _looks_like_spv_name(text)


def _looks_like_spv_name(value: str) -> bool:
    return bool(
        re.search(
            r"\b(spv|special purpose|bankruptcy[- ]?remote|project company|"
            r"issuer llc|issuer ltd|holdings llc)\b",
            value,
            re.I,
        )
    )


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
            edge for edge in edges if edge.source_id in component and edge.target_id in component
        ]
        source_uris = {uri for edge in component_edges for uri in edge.source_uris if uri}
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
            node_by_id[neighbor_id] for neighbor_id in counterparties if neighbor_id in node_by_id
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
                risk_bearer_neighbor_count=sum(
                    _is_risk_bearer_node(item) for item in neighbor_nodes
                ),
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
