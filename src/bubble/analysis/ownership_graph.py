"""Source-backed ownership and consolidation graph construction."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


@dataclass(frozen=True)
class OwnershipNode:
    """A legal-entity node observed in an ownership or consolidation source."""

    node_id: str
    node_id_type: str
    legal_name: str
    entity_status: str
    registration_status: str
    legal_jurisdiction: str
    relationship_count: int
    parent_edge_count: int
    child_edge_count: int
    source_uri_count: int
    source_uris: str
    content_hashes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OwnershipEdge:
    """A source-backed ownership, accounting, or consolidation relationship."""

    child_id: str
    child_id_type: str
    parent_id: str
    parent_id_type: str
    relationship_type: str
    relationship_status: str
    start_date: str
    end_date: str
    period_type: str
    qualifier_dimension: str
    qualifier_category: str
    quantifier_method: str
    quantifier_amount: float | None
    quantifier_units: str
    validation_sources: str
    validation_documents: str
    validation_reference: str
    source_uri: str
    retrieved_at: str
    content_hash: str
    local_path: str
    record_index: str
    document_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OwnershipGraphSummary:
    """Serializable rollup for the ownership graph."""

    rows_scanned: int
    relationships: int
    source_backed_relationships: int
    active_relationships: int
    inactive_relationships: int
    direct_consolidation_edges: int
    ultimate_consolidation_edges: int
    other_relationship_edges: int
    fully_corroborated_relationships: int
    quantified_relationships: int
    nodes: int
    lei_nodes: int
    named_nodes: int
    active_legal_entity_nodes: int
    source_uri_count: int
    content_hash_count: int
    top_parents_by_child_count: list[dict[str, Any]]
    top_children_by_parent_count: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OwnershipGraph:
    """Built ownership graph artifacts."""

    nodes: list[OwnershipNode]
    edges: list[OwnershipEdge]
    summary: OwnershipGraphSummary


def load_ownership_rows(data_dirs: Iterable[str | Path]) -> list[dict[str, str]]:
    """Load source-backed ownership rows from known data directories."""

    rows: list[dict[str, str]] = []
    seen_paths: set[Path] = set()
    for data_dir in data_dirs:
        root = Path(data_dir)
        for path in (
            root / "source_acquisition" / "source_rows" / "ownership_records.csv",
            root / "ownership_records.csv",
        ):
            if not path.exists() or path in seen_paths:
                continue
            seen_paths.add(path)
            with path.open(newline="", errors="ignore") as f:
                rows.extend(dict(row) for row in csv.DictReader(f))
    return rows


def load_lei_reference_rows(data_dirs: Iterable[str | Path]) -> Iterable[dict[str, str]]:
    """Load source-backed LEI reference rows from known data directories."""

    seen_paths: set[Path] = set()
    for data_dir in data_dirs:
        root = Path(data_dir)
        for path in (
            root / "source_acquisition" / "source_rows" / "lei_records.csv",
            root / "lei_records.csv",
        ):
            if not path.exists() or path in seen_paths:
                continue
            seen_paths.add(path)
            with path.open(newline="", errors="ignore") as f:
                for row in csv.DictReader(f):
                    yield dict(row)


def build_ownership_graph(
    rows: Iterable[Mapping[str, str]],
    *,
    lei_rows: Iterable[Mapping[str, str]] | None = None,
) -> OwnershipGraph:
    """Build a deterministic ownership/consolidation graph from source rows."""

    edges: list[OwnershipEdge] = []
    rows_scanned = 0
    for row in rows:
        rows_scanned += 1
        edge = _edge_from_row(row)
        if edge is not None:
            edges.append(edge)

    child_counts: Counter[str] = Counter()
    parent_counts: Counter[str] = Counter()
    role_counts: dict[str, Counter[str]] = defaultdict(Counter)
    source_uris: set[str] = set()
    content_hashes: set[str] = set()
    node_types: dict[str, str] = {}
    node_source_uris: dict[str, set[str]] = defaultdict(set)
    node_content_hashes: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        parent_counts[edge.parent_id] += 1
        child_counts[edge.child_id] += 1
        role_counts[edge.child_id]["child"] += 1
        role_counts[edge.parent_id]["parent"] += 1
        node_types.setdefault(edge.child_id, edge.child_id_type)
        node_types.setdefault(edge.parent_id, edge.parent_id_type)
        if edge.source_uri:
            source_uris.add(edge.source_uri)
            node_source_uris[edge.child_id].add(edge.source_uri)
            node_source_uris[edge.parent_id].add(edge.source_uri)
        if edge.content_hash:
            content_hashes.add(edge.content_hash)
            node_content_hashes[edge.child_id].add(edge.content_hash)
            node_content_hashes[edge.parent_id].add(edge.content_hash)
    lei_reference = _lei_reference(lei_rows or [], allowed_ids=set(role_counts))
    for node_id, reference in lei_reference.items():
        if node_id not in role_counts:
            continue
        source_uri = reference.get("source_uri", "")
        content_hash = reference.get("content_hash", "")
        if source_uri:
            source_uris.add(source_uri)
            node_source_uris[node_id].add(source_uri)
        if content_hash:
            content_hashes.add(content_hash)
            node_content_hashes[node_id].add(content_hash)

    nodes = [
        OwnershipNode(
            node_id=node_id,
            node_id_type=node_types.get(node_id, ""),
            legal_name=lei_reference.get(node_id, {}).get("legal_name", ""),
            entity_status=lei_reference.get(node_id, {}).get("entity_status", ""),
            registration_status=lei_reference.get(node_id, {}).get(
                "registration_status",
                "",
            ),
            legal_jurisdiction=lei_reference.get(node_id, {}).get("legal_jurisdiction", ""),
            relationship_count=sum(role_counts[node_id].values()),
            parent_edge_count=role_counts[node_id]["parent"],
            child_edge_count=role_counts[node_id]["child"],
            source_uri_count=len(node_source_uris[node_id]),
            source_uris="|".join(sorted(node_source_uris[node_id])),
            content_hashes="|".join(sorted(node_content_hashes[node_id])),
        )
        for node_id in role_counts
    ]
    nodes.sort(
        key=lambda node: (
            node.relationship_count,
            node.parent_edge_count,
            node.child_edge_count,
            node.node_id,
        ),
        reverse=True,
    )
    summary = OwnershipGraphSummary(
        rows_scanned=rows_scanned,
        relationships=len(edges),
        source_backed_relationships=sum(1 for edge in edges if edge.source_uri),
        active_relationships=sum(1 for edge in edges if edge.relationship_status == "ACTIVE"),
        inactive_relationships=sum(1 for edge in edges if edge.relationship_status != "ACTIVE"),
        direct_consolidation_edges=sum(
            1 for edge in edges if edge.relationship_type == "IS_DIRECTLY_CONSOLIDATED_BY"
        ),
        ultimate_consolidation_edges=sum(
            1 for edge in edges if edge.relationship_type == "IS_ULTIMATELY_CONSOLIDATED_BY"
        ),
        other_relationship_edges=sum(
            1
            for edge in edges
            if edge.relationship_type
            not in {"IS_DIRECTLY_CONSOLIDATED_BY", "IS_ULTIMATELY_CONSOLIDATED_BY"}
        ),
        fully_corroborated_relationships=sum(
            1 for edge in edges if edge.validation_sources == "FULLY_CORROBORATED"
        ),
        quantified_relationships=sum(1 for edge in edges if edge.quantifier_amount is not None),
        nodes=len(nodes),
        lei_nodes=sum(1 for node in nodes if node.node_id_type == "LEI"),
        named_nodes=sum(1 for node in nodes if node.legal_name),
        active_legal_entity_nodes=sum(1 for node in nodes if node.entity_status == "ACTIVE"),
        source_uri_count=len(source_uris),
        content_hash_count=len(content_hashes),
        top_parents_by_child_count=_top_counter(parent_counts),
        top_children_by_parent_count=_top_counter(child_counts),
    )
    return OwnershipGraph(nodes=nodes, edges=edges, summary=summary)


def write_ownership_graph(graph: OwnershipGraph, output_dir: str | Path) -> dict[str, str]:
    """Write ownership graph nodes, edges, and summary to disk."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    nodes_path = out / "ownership_nodes.csv"
    edges_path = out / "ownership_edges.csv"
    summary_path = out / "ownership_graph_summary.json"
    _write_csv(nodes_path, [node.to_dict() for node in graph.nodes])
    _write_csv(edges_path, [edge.to_dict() for edge in graph.edges])
    summary_path.write_text(json.dumps(graph.summary.to_dict(), indent=2, sort_keys=True))
    return {
        "nodes_csv": str(nodes_path),
        "edges_csv": str(edges_path),
        "summary_json": str(summary_path),
    }


def _edge_from_row(row: Mapping[str, str]) -> OwnershipEdge | None:
    child_id = _first(row, "Relationship_StartNode_NodeID", "start_node_id", "child_entity", "lei")
    parent_id = _first(
        row,
        "Relationship_EndNode_NodeID",
        "end_node_id",
        "parent_entity",
        "owner",
        "parent_lei",
    )
    if not child_id or not parent_id or child_id == parent_id:
        return None
    return OwnershipEdge(
        child_id=child_id,
        child_id_type=_first(row, "Relationship_StartNode_NodeIDType", "start_node_id_type"),
        parent_id=parent_id,
        parent_id_type=_first(row, "Relationship_EndNode_NodeIDType", "end_node_id_type"),
        relationship_type=_first(row, "Relationship_RelationshipType", "relationship_type"),
        relationship_status=_first(row, "Relationship_RelationshipStatus", "relationship_status"),
        start_date=_first(row, "Relationship_RelationshipPeriods_RelationshipPeriod_StartDate"),
        end_date=_first(row, "Relationship_RelationshipPeriods_RelationshipPeriod_EndDate"),
        period_type=_first(row, "Relationship_RelationshipPeriods_RelationshipPeriod_PeriodType"),
        qualifier_dimension=_first(
            row,
            "Relationship_RelationshipQualifiers_RelationshipQualifier_QualifierDimension",
        ),
        qualifier_category=_first(
            row,
            "Relationship_RelationshipQualifiers_RelationshipQualifier_QualifierCategory",
        ),
        quantifier_method=_first(
            row,
            "Relationship_RelationshipQuantifiers_RelationshipQuantifier_MeasurementMethod",
        ),
        quantifier_amount=_optional_float(
            _first(row, "Relationship_RelationshipQuantifiers_RelationshipQuantifier_QuantifierAmount")
        ),
        quantifier_units=_first(
            row,
            "Relationship_RelationshipQuantifiers_RelationshipQuantifier_QuantifierUnits",
        ),
        validation_sources=_first(row, "Registration_ValidationSources", "validation_sources"),
        validation_documents=_first(row, "Registration_ValidationDocuments", "validation_documents"),
        validation_reference=_first(row, "Registration_ValidationReference", "validation_reference"),
        source_uri=_first(row, "source_uri"),
        retrieved_at=_first(row, "retrieved_at"),
        content_hash=_first(row, "content_hash"),
        local_path=_first(row, "local_path"),
        record_index=_first(row, "record_index", "source_row_number"),
        document_id=_first(row, "document_id"),
    )


def _first(row: Mapping[str, str], *keys: str) -> str:
    for key in keys:
        value = str(row.get(key, "") or "").strip()
        if value:
            return value
    return ""


def _optional_float(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _top_counter(counter: Counter[str], limit: int = 25) -> list[dict[str, Any]]:
    return [
        {"node_id": node_id, "relationship_count": count}
        for node_id, count in counter.most_common(limit)
    ]


def _lei_reference(
    rows: Iterable[Mapping[str, str]],
    *,
    allowed_ids: set[str] | None = None,
) -> dict[str, dict[str, str]]:
    reference: dict[str, dict[str, str]] = {}
    for row in rows:
        lei = _first(row, "LEI", "lei")
        if not lei:
            continue
        if allowed_ids is not None and lei not in allowed_ids:
            continue
        reference[lei] = {
            "legal_name": _first(row, "Entity_LegalName", "legal_name", "name"),
            "entity_status": _first(row, "Entity_EntityStatus", "entity_status"),
            "registration_status": _first(
                row,
                "Registration_RegistrationStatus",
                "registration_status",
            ),
            "legal_jurisdiction": _first(
                row,
                "Entity_LegalJurisdiction",
                "legal_jurisdiction",
            ),
            "source_uri": _first(row, "source_uri"),
            "content_hash": _first(row, "content_hash"),
        }
    return reference


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        if not fieldnames:
            return
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
