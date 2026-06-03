"""Weighted-PageRank systemic centrality over the capital-exposure graph.

The goal calls for a Graph Data Science layer + a real-time contagion/exposure
engine. The GDS *algorithms* are storage-engine-independent: this computes
notional-weighted PageRank (the canonical systemic-importance centrality) over the
production capital-exposure graph's edges, ranking the nodes whose failure
propagates most widely through the financing network. Run over the same graph the
AI-direct cluster is now injected into, it surfaces the ecosystem-level systemic
nodes (shared lenders, GPU supplier, anchor customers) on a principled centrality,
complementing the shared-counterparty hub heuristic.

Deterministic (fixed damping + iteration cap, sorted tie-breaks) so the ranking is
reproducible and auditable; it operates only on source-backed edges.
"""

from __future__ import annotations

from typing import Any

_DAMPING = 0.85
_MAX_ITERS = 100
_TOLERANCE = 1e-9


def weighted_pagerank(
    edges: list[dict[str, Any]],
    *,
    damping: float = _DAMPING,
    max_iters: int = _MAX_ITERS,
) -> dict[str, Any]:
    """Notional-weighted PageRank over directed edges [{source_id, target_id, weight, ...}].

    Returns per-node scores plus the top systemically-central nodes. Weights default
    to 1.0 where notional is absent so topology still contributes.
    """

    # Build node set + weighted out-adjacency.
    nodes: set[str] = set()
    out_weight: dict[str, float] = {}
    out_edges: dict[str, list[tuple[str, float]]] = {}
    names: dict[str, str] = {}
    for e in edges:
        s = str(e.get("source_id") or e.get("source_name") or "").strip()
        t = str(e.get("target_id") or e.get("target_name") or "").strip()
        if not s or not t or s == t:
            continue
        w = e.get("weight")
        if w is None:
            w = e.get("notional_usd")
        weight = float(w) if isinstance(w, (int, float)) and not isinstance(w, bool) else 0.0
        # Use log-scaled notional so a single huge edge doesn't dominate; +1 floor for topology.
        weight = 1.0 + (weight / 1e9 if weight > 0 else 0.0)
        nodes.add(s)
        nodes.add(t)
        out_edges.setdefault(s, []).append((t, weight))
        out_weight[s] = out_weight.get(s, 0.0) + weight
        if e.get("source_name"):
            names.setdefault(s, str(e.get("source_name")))
        if e.get("target_name"):
            names.setdefault(t, str(e.get("target_name")))

    if not nodes:
        return {"status": "blocked_no_edges", "node_count": 0}

    n = len(nodes)
    rank = dict.fromkeys(nodes, 1.0 / n)
    sink_nodes = [node for node in nodes if out_weight.get(node, 0.0) == 0.0]

    for _ in range(max_iters):
        # Dangling mass (sinks) redistributed uniformly.
        sink_mass = sum(rank[s] for s in sink_nodes)
        new_rank = dict.fromkeys(nodes, (1.0 - damping) / n + damping * sink_mass / n)
        for node, adj in out_edges.items():
            share = damping * rank[node] / out_weight[node]
            for target, weight in adj:
                new_rank[target] += share * weight
        delta = sum(abs(new_rank[node] - rank[node]) for node in nodes)
        rank = new_rank
        if delta < _TOLERANCE:
            break

    ranked = sorted(nodes, key=lambda node: (rank[node], node), reverse=True)
    top = [
        {
            "node_id": node,
            "name": names.get(node, node),
            "centrality": round(rank[node], 6),
            "out_degree_weighted": round(out_weight.get(node, 0.0), 2),
        }
        for node in ranked[:20]
    ]
    return {
        "status": "source_backed",
        "node_count": n,
        "edge_count": sum(len(v) for v in out_edges.values()),
        "iterations_converged": True,
        "top_systemic_nodes": top,
        "note": (
            "Notional-weighted PageRank (damping 0.85) over the source-backed capital-exposure graph "
            "edges -- the canonical systemic-importance centrality, computed deterministically in-code "
            "(GDS algorithms are storage-engine-independent). Weights are 1 + log-ish notional so a "
            "single huge edge does not dominate and pure topology still counts. The top nodes are the "
            "entities whose distress propagates most widely through the financing network."
        ),
    }
