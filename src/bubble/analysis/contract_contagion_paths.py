"""Source-backed contract-to-ownership contagion path construction."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

HIGH_IMPACT_RELATIONSHIPS = {
    "DEAL_RISK_BEARER",
    "GUARANTEED_BY",
    "OBLIGATED_UNDER_DEAL",
    "OBLIGOR_TO_TRANCHE",
    "SECURED_BY_COLLATERAL",
    "TRANCHE_GUARANTEED_BY",
    "TRANCHE_RISK_BEARER",
}

OWNERSHIP_RELATIONSHIPS = {
    "IS_DIRECTLY_CONSOLIDATED_BY",
    "IS_ULTIMATELY_CONSOLIDATED_BY",
}


@dataclass(frozen=True)
class ContractContagionPath:
    """One source-backed contract path, optionally expanded through ownership."""

    path_id: str
    path_type: str
    risk_level: str
    risk_score: float
    start_entity_name: str
    start_contract_node_id: str
    start_ownership_node_id: str
    contract_relationship_type: str
    contract_counterparty_name: str
    contract_counterparty_type: str
    deal_id: str
    deal_type: str
    tranche_id: str
    notional_usd: float
    path_depth: int
    ownership_path_node_ids: tuple[str, ...]
    ownership_path_names: tuple[str, ...]
    ownership_relationship_types: tuple[str, ...]
    ownership_validation_sources: tuple[str, ...]
    ownership_quantifiers: tuple[str, ...]
    relevance_tags: tuple[str, ...]
    risk_flags: tuple[str, ...]
    reason: str
    source_uris: tuple[str, ...]
    content_hashes: tuple[str, ...]
    human_review_statuses: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContractContagionSummary:
    """Serializable rollup of joined contract/ownership contagion paths."""

    contract_edges_scanned: int
    high_impact_contract_edges: int
    ownership_nodes_indexed: int
    ownership_edges_indexed: int
    contract_entity_name_matches: int
    paths: int
    source_backed_paths: int
    ownership_expanded_paths: int
    contract_only_paths: int
    ai_infra_relevant_paths: int
    guarantee_paths: int
    collateral_paths: int
    non_recourse_paths: int
    spv_paths: int
    high_or_critical_paths: int
    total_notional_usd: float
    ai_infra_relevant_notional_usd: float
    top_paths: list[dict[str, Any]]
    top_ownership_expanded_paths: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContractContagionBatch:
    """Built contagion path artifacts."""

    paths: list[ContractContagionPath]
    summary: ContractContagionSummary


def build_contract_contagion_paths(
    data_dirs: list[str | Path] | None = None,
    *,
    min_notional_usd: float = 1_000_000_000,
    max_ownership_depth: int = 3,
    max_paths: int = 10_000,
) -> ContractContagionBatch:
    """Join source-backed contract edges to ownership/consolidation paths."""

    roots = [Path(root) for root in (data_dirs or ["data"])]
    contract_edges = _read_rows(roots, Path("graph") / "capital_contract_edges.csv")
    ownership_nodes = _read_rows(roots, Path("graph") / "ownership_nodes.csv")
    ownership_edges = _read_rows(roots, Path("graph") / "ownership_edges.csv")
    name_index = _ownership_name_index(ownership_nodes)
    node_names = _ownership_node_names(ownership_nodes)
    parent_edges = _ownership_parent_edges(ownership_edges)

    high_impact_edges = [
        edge
        for edge in contract_edges
        if _is_high_impact_contract_edge(edge, min_notional_usd=min_notional_usd)
    ]
    paths: list[ContractContagionPath] = []
    matched_names: set[str] = set()
    seen_path_ids: set[str] = set()
    for edge in high_impact_edges:
        paths.extend(_contract_only_paths(edge, seen_path_ids=seen_path_ids, max_paths=max_paths))
        for entity in _entity_endpoints(edge):
            ownership_ids = name_index.get(_normalize_name(entity["name"]), [])
            if ownership_ids:
                matched_names.add(_normalize_name(entity["name"]))
            for ownership_id in ownership_ids[:3]:
                for ownership_path in _ownership_paths(
                    ownership_id,
                    parent_edges,
                    max_depth=max_ownership_depth,
                ):
                    if len(paths) >= max_paths:
                        break
                    path = _ownership_expanded_path(
                        edge,
                        entity,
                        ownership_id,
                        ownership_path,
                        node_names,
                    )
                    if path.path_id in seen_path_ids:
                        continue
                    seen_path_ids.add(path.path_id)
                    paths.append(path)
                if len(paths) >= max_paths:
                    break
            if len(paths) >= max_paths:
                break
        if len(paths) >= max_paths:
            break

    paths.sort(key=lambda path: (path.risk_score, path.notional_usd, path.path_depth), reverse=True)
    summary = _summary(
        paths,
        contract_edges_scanned=len(contract_edges),
        high_impact_contract_edges=len(high_impact_edges),
        ownership_nodes_indexed=len(ownership_nodes),
        ownership_edges_indexed=sum(len(edges) for edges in parent_edges.values()),
        contract_entity_name_matches=len(matched_names),
    )
    return ContractContagionBatch(paths=paths, summary=summary)


def write_contract_contagion_paths(
    batch: ContractContagionBatch,
    output_dir: str | Path,
) -> dict[str, str]:
    """Write contagion path CSV and summary JSON."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths_path = out / "contract_contagion_paths.csv"
    summary_path = out / "contract_contagion_summary.json"
    _write_csv(paths_path, [path.to_dict() for path in batch.paths])
    summary_path.write_text(json.dumps(batch.summary.to_dict(), indent=2))
    return {"paths_csv": str(paths_path), "summary_json": str(summary_path)}


def _is_high_impact_contract_edge(
    edge: dict[str, str],
    *,
    min_notional_usd: float,
) -> bool:
    if _float(edge.get("notional_usd")) < min_notional_usd:
        return False
    if not edge.get("source_uri"):
        return False
    relationship = edge.get("relationship_type") or ""
    if relationship in HIGH_IMPACT_RELATIONSHIPS:
        return True
    return bool(_json_list(edge.get("relevance_tags")) or _json_list(edge.get("risk_flags")))


def _contract_only_paths(
    edge: dict[str, str],
    *,
    seen_path_ids: set[str],
    max_paths: int,
) -> list[ContractContagionPath]:
    relationship = edge.get("relationship_type") or ""
    if relationship not in {"SECURED_BY_COLLATERAL", "GUARANTEED_BY", "TRANCHE_GUARANTEED_BY"}:
        return []
    if len(seen_path_ids) >= max_paths:
        return []
    path = _path_from_parts(
        edge,
        path_type="contract_only",
        start_entity_name=_contract_source_name(edge),
        start_contract_node_id=edge.get("source_id", ""),
        start_ownership_node_id="",
        contract_counterparty_name=edge.get("target_name", ""),
        contract_counterparty_type=edge.get("target_type", ""),
        ownership_path=[],
        node_names={},
    )
    if path.path_id in seen_path_ids:
        return []
    seen_path_ids.add(path.path_id)
    return [path]


def _ownership_expanded_path(
    edge: dict[str, str],
    entity: dict[str, str],
    ownership_id: str,
    ownership_path: list[dict[str, str]],
    node_names: dict[str, str],
) -> ContractContagionPath:
    counterparty_name, counterparty_type = _counterparty_for_entity(edge, entity["node_id"])
    return _path_from_parts(
        edge,
        path_type="ownership_expanded",
        start_entity_name=entity["name"],
        start_contract_node_id=entity["node_id"],
        start_ownership_node_id=ownership_id,
        contract_counterparty_name=counterparty_name,
        contract_counterparty_type=counterparty_type,
        ownership_path=ownership_path,
        node_names=node_names,
    )


def _path_from_parts(
    edge: dict[str, str],
    *,
    path_type: str,
    start_entity_name: str,
    start_contract_node_id: str,
    start_ownership_node_id: str,
    contract_counterparty_name: str,
    contract_counterparty_type: str,
    ownership_path: list[dict[str, str]],
    node_names: dict[str, str],
) -> ContractContagionPath:
    relevance_tags = tuple(_json_list(edge.get("relevance_tags")))
    risk_flags = tuple(_json_list(edge.get("risk_flags")))
    notional = _float(edge.get("notional_usd"))
    ownership_node_ids = tuple(_ownership_node_path(start_ownership_node_id, ownership_path))
    ownership_names = tuple(node_names.get(node_id, node_id) for node_id in ownership_node_ids)
    relationship_types = tuple(edge.get("relationship_type", "") for edge in ownership_path)
    validation_sources = tuple(edge.get("validation_sources", "") for edge in ownership_path)
    quantifiers = tuple(_ownership_quantifier(edge) for edge in ownership_path)
    source_uris = tuple(
        item
        for item in [
            edge.get("source_uri", ""),
            *(ownership_edge.get("source_uri", "") for ownership_edge in ownership_path),
        ]
        if item
    )
    content_hashes = tuple(
        item
        for item in [
            edge.get("content_hash", ""),
            *(ownership_edge.get("content_hash", "") for ownership_edge in ownership_path),
        ]
        if item
    )
    score = _risk_score(
        notional=notional,
        relationship_type=edge.get("relationship_type", ""),
        relevance_tags=relevance_tags,
        risk_flags=risk_flags,
        path_depth=len(ownership_path),
    )
    reason = _reason(edge, risk_flags, relevance_tags, path_type, len(ownership_path))
    path_id = _path_id(
        path_type,
        start_contract_node_id,
        start_ownership_node_id,
        edge.get("target_id", ""),
        edge.get("deal_id", ""),
        edge.get("tranche_id", ""),
        ownership_node_ids,
        edge.get("content_hash", ""),
    )
    return ContractContagionPath(
        path_id=path_id,
        path_type=path_type,
        risk_level=_risk_level(score),
        risk_score=round(score, 4),
        start_entity_name=start_entity_name,
        start_contract_node_id=start_contract_node_id,
        start_ownership_node_id=start_ownership_node_id,
        contract_relationship_type=edge.get("relationship_type", ""),
        contract_counterparty_name=contract_counterparty_name,
        contract_counterparty_type=contract_counterparty_type,
        deal_id=edge.get("deal_id", ""),
        deal_type=edge.get("deal_type", ""),
        tranche_id=edge.get("tranche_id", ""),
        notional_usd=round(notional, 2),
        path_depth=len(ownership_path),
        ownership_path_node_ids=ownership_node_ids,
        ownership_path_names=ownership_names,
        ownership_relationship_types=relationship_types,
        ownership_validation_sources=validation_sources,
        ownership_quantifiers=quantifiers,
        relevance_tags=relevance_tags,
        risk_flags=risk_flags,
        reason=reason,
        source_uris=source_uris,
        content_hashes=content_hashes,
        human_review_statuses=tuple(
            item
            for item in [edge.get("human_review_status", ""), "ownership_source_backed"]
            if item and (item != "ownership_source_backed" or ownership_path)
        ),
    )


def _entity_endpoints(edge: dict[str, str]) -> list[dict[str, str]]:
    endpoints: list[dict[str, str]] = []
    if edge.get("source_type") == "entity":
        endpoints.append(
            {"node_id": edge.get("source_id", ""), "name": edge.get("source_name", "")}
        )
    if edge.get("target_type") == "entity":
        endpoints.append(
            {"node_id": edge.get("target_id", ""), "name": edge.get("target_name", "")}
        )
    return [endpoint for endpoint in endpoints if endpoint["node_id"] and endpoint["name"]]


def _counterparty_for_entity(edge: dict[str, str], entity_node_id: str) -> tuple[str, str]:
    if edge.get("source_id") == entity_node_id:
        return edge.get("target_name", ""), edge.get("target_type", "")
    return edge.get("source_name", ""), edge.get("source_type", "")


def _contract_source_name(edge: dict[str, str]) -> str:
    return edge.get("source_name", "") or edge.get("target_name", "")


def _ownership_paths(
    start_id: str,
    parent_edges: dict[str, list[dict[str, str]]],
    *,
    max_depth: int,
    max_paths_per_start: int = 4,
) -> list[list[dict[str, str]]]:
    paths: list[list[dict[str, str]]] = []
    queue: deque[tuple[str, list[dict[str, str]]]] = deque([(start_id, [])])
    while queue and len(paths) < max_paths_per_start:
        current, path = queue.popleft()
        if len(path) >= max_depth:
            continue
        for edge in parent_edges.get(current, [])[:4]:
            if edge.get("parent_id") in _path_node_ids(start_id, path):
                continue
            next_path = [*path, edge]
            paths.append(next_path)
            queue.append((edge.get("parent_id", ""), next_path))
            if len(paths) >= max_paths_per_start:
                break
    return paths


def _ownership_parent_edges(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    parent_edges: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("relationship_status") != "ACTIVE":
            continue
        if row.get("relationship_type") not in OWNERSHIP_RELATIONSHIPS:
            continue
        if not row.get("source_uri"):
            continue
        parent_edges[row.get("child_id", "")].append(row)
    for edges in parent_edges.values():
        edges.sort(key=_ownership_edge_rank, reverse=True)
    return parent_edges


def _ownership_name_index(rows: list[dict[str, str]]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        name = _normalize_name(row.get("legal_name", ""))
        node_id = row.get("node_id", "")
        if name and node_id:
            index[name].append(node_id)
    return index


def _ownership_node_names(rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        row.get("node_id", ""): row.get("legal_name", "") or row.get("node_id", "")
        for row in rows
        if row.get("node_id")
    }


def _ownership_edge_rank(edge: dict[str, str]) -> tuple[int, int, float]:
    return (
        1 if edge.get("relationship_type") == "IS_DIRECTLY_CONSOLIDATED_BY" else 0,
        1 if edge.get("validation_sources") == "FULLY_CORROBORATED" else 0,
        _float(edge.get("quantifier_amount")),
    )


def _ownership_node_path(start_id: str, path: list[dict[str, str]]) -> list[str]:
    if not start_id:
        return []
    return [start_id, *(edge.get("parent_id", "") for edge in path if edge.get("parent_id"))]


def _path_node_ids(start_id: str, path: list[dict[str, str]]) -> set[str]:
    return set(_ownership_node_path(start_id, path))


def _ownership_quantifier(edge: dict[str, str]) -> str:
    amount = edge.get("quantifier_amount") or ""
    units = edge.get("quantifier_units") or ""
    method = edge.get("quantifier_method") or ""
    return " ".join(part for part in (amount, units, method) if part)


def _risk_score(
    *,
    notional: float,
    relationship_type: str,
    relevance_tags: tuple[str, ...],
    risk_flags: tuple[str, ...],
    path_depth: int,
) -> float:
    score = min(notional / 25_000_000_000, 1.0) * 0.35
    score += min(path_depth / 3, 1.0) * 0.15
    if any(tag.startswith("direct:") for tag in relevance_tags):
        score += 0.15
    elif relevance_tags:
        score += 0.08
    if {"spv_signal", "bankruptcy_remote_spv", "non_recourse"}.intersection(risk_flags):
        score += 0.15
    if "guarantee" in relationship_type.lower() or "guarantee_linked" in risk_flags:
        score += 0.1
    if "collateral" in relationship_type.lower() or "collateralized" in risk_flags:
        score += 0.1
    return min(score, 1.0)


def _risk_level(score: float) -> str:
    if score >= 0.8:
        return "critical"
    if score >= 0.6:
        return "high"
    if score >= 0.35:
        return "medium"
    return "watch"


def _reason(
    edge: dict[str, str],
    risk_flags: tuple[str, ...],
    relevance_tags: tuple[str, ...],
    path_type: str,
    path_depth: int,
) -> str:
    parts = [
        f"{path_type.replace('_', ' ')} contagion path",
        f"contract relationship: {edge.get('relationship_type', '')}",
        f"notional ${_float(edge.get('notional_usd')):,.0f}",
    ]
    if path_depth:
        parts.append(f"ownership/control path depth {path_depth}")
    if risk_flags:
        parts.append(f"risk flags: {', '.join(risk_flags[:6])}")
    if relevance_tags:
        parts.append(f"relevance: {', '.join(relevance_tags[:4])}")
    return "; ".join(part for part in parts if part)


def _summary(
    paths: list[ContractContagionPath],
    *,
    contract_edges_scanned: int,
    high_impact_contract_edges: int,
    ownership_nodes_indexed: int,
    ownership_edges_indexed: int,
    contract_entity_name_matches: int,
) -> ContractContagionSummary:
    ai_paths = [path for path in paths if path.relevance_tags]
    return ContractContagionSummary(
        contract_edges_scanned=contract_edges_scanned,
        high_impact_contract_edges=high_impact_contract_edges,
        ownership_nodes_indexed=ownership_nodes_indexed,
        ownership_edges_indexed=ownership_edges_indexed,
        contract_entity_name_matches=contract_entity_name_matches,
        paths=len(paths),
        source_backed_paths=sum(1 for path in paths if path.source_uris),
        ownership_expanded_paths=sum(1 for path in paths if path.path_type == "ownership_expanded"),
        contract_only_paths=sum(1 for path in paths if path.path_type == "contract_only"),
        ai_infra_relevant_paths=len(ai_paths),
        guarantee_paths=sum("GUARANTEE" in path.contract_relationship_type for path in paths),
        collateral_paths=sum(
            path.contract_relationship_type == "SECURED_BY_COLLATERAL" for path in paths
        ),
        non_recourse_paths=sum("non_recourse" in path.risk_flags for path in paths),
        spv_paths=sum(
            bool({"spv_signal", "bankruptcy_remote_spv"}.intersection(path.risk_flags))
            for path in paths
        ),
        high_or_critical_paths=sum(path.risk_level in {"critical", "high"} for path in paths),
        total_notional_usd=round(sum(path.notional_usd for path in paths), 2),
        ai_infra_relevant_notional_usd=round(sum(path.notional_usd for path in ai_paths), 2),
        top_paths=[path.to_dict() for path in paths[:25]],
        top_ownership_expanded_paths=[
            path.to_dict() for path in paths if path.path_type == "ownership_expanded"
        ][:25],
    )


def _path_id(*parts: Any) -> str:
    raw = "|".join(str(part) for part in parts)
    return "contagion:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def _read_rows(roots: list[Path], relative_path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for root in roots:
        path = root / relative_path
        if not path.exists() or path.stat().st_size == 0:
            continue
        with path.open(newline="", errors="ignore") as f:
            rows.extend(
                {str(key): (value or "").strip() for key, value in row.items() if key is not None}
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
            return [str(item) for item in loaded]
    return []


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(str(value).replace(",", "").replace("$", ""))
    except ValueError:
        return 0.0


def _normalize_name(value: str) -> str:
    tokens = re.sub(r"[^a-z0-9]+", " ", value.lower()).split()
    suffixes = {"co", "company", "corp", "corporation", "inc", "llc", "ltd", "limited"}
    while tokens and tokens[-1] in suffixes:
        tokens = tokens[:-1]
    return " ".join(tokens)
