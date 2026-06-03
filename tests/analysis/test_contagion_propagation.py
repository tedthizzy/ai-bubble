"""Multi-hop contagion propagation."""

from __future__ import annotations

from bubble.analysis.contagion_propagation import build_contagion_graph, top_contagion_cascades


def _edge(entity, *, suppliers=None, customers=None):
    def _cps(names):
        return [{"name": n, "source_uri": "x"} for n in names or []]

    return {
        "entity": entity,
        "top_customers": _cps(customers),
        "gpu_suppliers": _cps(suppliers),
        "lenders_or_agents": [],
        "strategic_investors": [],
    }


def _census(debts: dict[str, float]):
    return {"per_issuer": [{"entity": e, "total_debt_usd": d} for e, d in debts.items()]}


def test_blocks_without_edges() -> None:
    assert top_contagion_cascades([])["status"].startswith("blocked")


def test_shock_propagates_debt_at_risk_and_second_order() -> None:
    edges = [
        _edge("CoreWeave, Inc. (CRWV)", suppliers=["NVIDIA"], customers=["Microsoft"]),
        _edge("IREN Limited", suppliers=["NVIDIA"], customers=["Microsoft"]),
        _edge("TeraWulf Inc.", suppliers=["NVIDIA"], customers=["Fluidstack"]),
    ]
    census = _census(
        {"CoreWeave": 25_000_000_000, "IREN": 4_000_000_000, "TeraWulf": 5_000_000_000}
    )
    out = top_contagion_cascades(edges, census)

    assert out["status"] == "source_backed"
    nvidia = next(c for c in out["cascades"] if c["origin"] == "NVIDIA")
    # NVIDIA shock hits all 3 issuers; debt at risk = sum of their census debt.
    assert nvidia["directly_hit_count"] == 3
    assert nvidia["debt_at_risk_usd"] == 34_000_000_000
    # Microsoft is a second-order counterparty reached via CoreWeave + IREN.
    msft = next(
        c for c in nvidia["second_order_counterparties"] if c["counterparty"] == "Microsoft"
    )
    assert msft["via_issuers"] == 2


def test_graph_excludes_self_and_unknown_debt_defaults_zero() -> None:
    edges = [_edge("CoreWeave", customers=["Microsoft"])]
    graph = build_contagion_graph(edges, _census({}))
    # No census debt -> default 0, graph still builds.
    assert "CoreWeave" in graph["issuer_to_cps"]
    assert graph["debt_by_issuer"].get("CoreWeave", 0.0) == 0.0
