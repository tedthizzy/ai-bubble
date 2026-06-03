"""AI-direct contagion-hub aggregation."""

from __future__ import annotations

from bubble.analysis.contagion_hubs import compute_contagion_hubs


def _edge(entity, *, customers=None, suppliers=None, lenders=None, investors=None):
    def _cps(names):
        return [
            {"name": n, "source_uri": "https://sec.gov/x", "quote": f"q:{n}"} for n in names or []
        ]

    return {
        "entity": entity,
        "top_customers": _cps(customers),
        "gpu_suppliers": _cps(suppliers),
        "lenders_or_agents": _cps(lenders),
        "strategic_investors": _cps(investors),
    }


def test_blocks_without_edges() -> None:
    assert compute_contagion_hubs([])["status"].startswith("blocked")


def test_shared_supplier_is_top_hub() -> None:
    edges = [
        _edge(
            "CoreWeave, Inc.", suppliers=["NVIDIA Corporation"], customers=["Microsoft Corporation"]
        ),
        _edge("IREN Limited", suppliers=["NVIDIA Corp"], customers=["Microsoft"]),
        _edge("TeraWulf Inc.", suppliers=["Nvidia"], customers=["Google LLC"]),
    ]
    out = compute_contagion_hubs(edges)

    assert out["status"] == "source_backed"
    assert out["issuer_count"] == 3
    # NVIDIA touches all 3 issuers -> top hub, with name variants canonicalized.
    nvidia = next(h for h in out["top_contagion_hubs"] if h["counterparty"] == "NVIDIA")
    assert nvidia["issuer_count"] == 3
    assert nvidia["category"] == "gpu_supplier"
    # Microsoft shared across 2 issuers (CoreWeave + IREN).
    msft = next(h for h in out["top_contagion_hubs"] if h["counterparty"] == "Microsoft")
    assert msft["issuer_count"] == 2


def test_unshared_counterparties_excluded() -> None:
    edges = [
        _edge("A", customers=["UniqueCustomerOne"]),
        _edge("B", customers=["UniqueCustomerTwo"]),
    ]
    out = compute_contagion_hubs(edges)
    # No counterparty is shared across >=2 issuers.
    assert out["shared_hub_count"] == 0


def test_concentration_pct_carried() -> None:
    edges = [
        {
            "entity": "CoreWeave",
            "top_customers": [
                {"name": "Microsoft", "revenue_concentration_pct": 67, "source_uri": "x"}
            ],
            "gpu_suppliers": [{"name": "NVIDIA", "source_uri": "x"}],
            "lenders_or_agents": [],
            "strategic_investors": [],
        },
        {
            "entity": "IREN",
            "top_customers": [{"name": "Microsoft", "source_uri": "x"}],
            "gpu_suppliers": [{"name": "NVIDIA", "source_uri": "x"}],
            "lenders_or_agents": [],
            "strategic_investors": [],
        },
    ]
    out = compute_contagion_hubs(edges)
    msft = next(h for h in out["top_contagion_hubs"] if h["counterparty"] == "Microsoft")
    assert msft["max_revenue_concentration_pct"] == 67
