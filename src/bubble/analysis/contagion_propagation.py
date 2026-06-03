"""Multi-hop contagion propagation over the AI-direct counterparty graph.

The shared-hub map (contagion_hubs) is the NODE layer; this is the PROPAGATION
layer. For a shock to a counterparty hub it computes which issuers are directly
hit (hop 1), the debt at risk (weighted by the source-backed debt census), and
the second-order counterparties exposed through those issuers (hop 2) -- i.e.
the loss-cascade path, with every edge traceable to a filing.
"""

from __future__ import annotations

import re
from typing import Any

from bubble.analysis.contagion_hubs import _CATEGORIES, _canonical_counterparty

_ISSUER_SUFFIX_RE = re.compile(
    r"\b(inc|incorporated|corp|corporation|limited|ltd|llc|n\.?v\.?|plc|group|technologies|"
    r"holdings|co|company)\b\.?",
    re.I,
)


def _short_issuer(name: Any) -> str:
    head = re.split(r"[,(—-]", str(name or ""))[0]
    head = _ISSUER_SUFFIX_RE.sub("", head)
    return re.sub(r"\s+", " ", head).strip()


def build_contagion_graph(
    edges: list[dict[str, Any]],
    debt_census: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bipartite issuer<->counterparty graph with issuer debt weights."""

    issuer_to_cps: dict[str, set[tuple[str, str]]] = {}
    cp_to_issuers: dict[str, set[str]] = {}
    cp_categories: dict[str, set[str]] = {}
    for edge in edges:
        issuer = _short_issuer(edge.get("entity"))
        if not issuer:
            continue
        issuer_to_cps.setdefault(issuer, set())
        for category, key in _CATEGORIES.items():
            for cp in edge.get(key) or []:
                if not isinstance(cp, dict):
                    continue
                canonical = _canonical_counterparty(str(cp.get("name") or ""))
                if not canonical or canonical == issuer:
                    continue
                issuer_to_cps[issuer].add((category, canonical))
                cp_to_issuers.setdefault(canonical, set()).add(issuer)
                cp_categories.setdefault(canonical, set()).add(category)

    debt_by_issuer: dict[str, float] = {}
    for row in (debt_census or {}).get("per_issuer") or []:
        debt_by_issuer[_short_issuer(row.get("entity"))] = float(row.get("total_debt_usd") or 0.0)

    return {
        "issuer_to_cps": issuer_to_cps,
        "cp_to_issuers": cp_to_issuers,
        "cp_categories": cp_categories,
        "debt_by_issuer": debt_by_issuer,
    }


def propagate_shock(graph: dict[str, Any], origin: str) -> dict[str, Any]:
    """Loss cascade from a shock to one counterparty hub."""

    directly_hit = sorted(graph["cp_to_issuers"].get(origin, set()))
    debt_at_risk = round(sum(graph["debt_by_issuer"].get(i, 0.0) for i in directly_hit), 2)
    # hop 2: other counterparties reached through the directly-hit issuers
    second_order: dict[str, set[str]] = {}
    for issuer in directly_hit:
        for _category, cp in graph["issuer_to_cps"].get(issuer, set()):
            if cp == origin:
                continue
            second_order.setdefault(cp, set()).add(issuer)
    second_order_ranked = [
        {"counterparty": cp, "via_issuers": len(issuers)}
        for cp, issuers in sorted(second_order.items(), key=lambda kv: len(kv[1]), reverse=True)
    ]
    categories = sorted(graph.get("cp_categories", {}).get(origin, set()))
    return {
        "origin": origin,
        "origin_categories": categories,
        "is_demand_or_supply_hub": any(
            c in ("customer", "gpu_supplier", "strategic_investor") for c in categories
        ),
        "directly_hit_issuers": directly_hit,
        "directly_hit_count": len(directly_hit),
        "debt_at_risk_usd": debt_at_risk,
        "second_order_counterparties": second_order_ranked[:10],
    }


def top_contagion_cascades(
    edges: list[dict[str, Any]],
    debt_census: dict[str, Any] | None = None,
    *,
    min_issuers: int = 2,
    top_n: int = 6,
) -> dict[str, Any]:
    """Rank counterparty hubs by the loss cascade their failure would trigger."""

    if not edges:
        return {"status": "blocked_no_contagion_edges"}

    graph = build_contagion_graph(edges, debt_census)
    cascades = [
        propagate_shock(graph, cp)
        for cp, issuers in graph["cp_to_issuers"].items()
        if len(issuers) >= min_issuers
    ]
    # Rank by debt at risk, then breadth of issuers hit.
    cascades.sort(key=lambda c: (c["debt_at_risk_usd"], c["directly_hit_count"]), reverse=True)
    return {
        "status": "source_backed",
        "issuer_count": len(graph["issuer_to_cps"]),
        "cascades": cascades[:top_n],
        "note": (
            "Loss cascade per shared counterparty: failure/withdrawal of a hub directly stresses the "
            "issuers it touches (debt_at_risk_usd from the source-backed census) and propagates to "
            "their other counterparties at hop 2. This is the scoped multi-hop contagion engine for "
            "the AI-direct core; debt_at_risk uses census total debt, an upper bound on the directly "
            "exposed leverage, not a probability-weighted loss."
        ),
    }
