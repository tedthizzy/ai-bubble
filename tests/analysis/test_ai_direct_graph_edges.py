"""AI-direct cluster injection into the capital-exposure graph."""

from __future__ import annotations

import json
from pathlib import Path

from bubble.analysis.ai_direct_graph_edges import build_ai_direct_deals
from bubble.analysis.capital_exposure_graph import build_capital_exposure_graph

_CENSUS = [
    {
        "stack": {
            "entity": "CoreWeave, Inc.",
            "ticker": "CRWV",
            "total_debt_usd": 25_000_000_000,
            "facilities": [{"name": "DDTL 5.0", "principal_usd": 3_100_000_000}],
        }
    },
    {"stack": {"entity": "Nebius Group N.V.", "total_debt_usd": 4_000_000_000, "facilities": []}},
]

_CONTAGION = [
    {
        "entity": "CoreWeave, Inc. (CRWV) — CIK 0001769628",
        "top_customers": [
            {
                "name": "Microsoft Corporation",
                "revenue_concentration_pct": 67,
                "quote": "q",
                "source_uri": "sec:crwv",
            },
            {
                "name": "OpenAI OpCo, LLC",
                "revenue_concentration_pct": None,
                "quote": "q",
                "source_uri": "sec:crwv",
            },
        ],
        "gpu_suppliers": [
            {"name": "NVIDIA Corporation", "quote": "q", "source_uri": "sec:crwv"},
            {
                "name": "Three unnamed suppliers (names not disclosed in 10-K)",
                "quote": "q",
                "source_uri": "sec:crwv",
            },
        ],
        "lenders_or_agents": [
            {
                "name": "Morgan Stanley Senior Funding, Inc.",
                "role": "admin_agent and lead arranger",
                "quote": "q",
                "source_uri": "sec:crwv",
            },
            {
                "name": "Goldman Sachs Bank USA",
                "role": "lender",
                "quote": "q",
                "source_uri": "sec:crwv",
            },
        ],
        "strategic_investors": [
            {
                "name": "NVIDIA Corporation",
                "stake_or_amount": "$2 billion equity investment",
                "quote": "q",
                "source_uri": "sec:crwv",
            },
        ],
    },
    {
        "entity": "Nebius Group N.V. (NBIS)",
        "top_customers": [
            {
                "name": "Microsoft Corporation",
                "revenue_concentration_pct": 40,
                "quote": "q",
                "source_uri": "sec:nbis",
            }
        ],
        "gpu_suppliers": [{"name": "NVIDIA Corporation", "quote": "q", "source_uri": "sec:nbis"}],
        "lenders_or_agents": [
            {
                "name": "Goldman Sachs Bank USA",
                "role": "lender",
                "quote": "q",
                "source_uri": "sec:nbis",
            }
        ],
        "strategic_investors": [],
    },
]


def test_builds_source_backed_cluster_deals() -> None:
    deals = build_ai_direct_deals(_CENSUS, _CONTAGION)
    assert deals, "should emit cluster deals"
    # Every deal carries provenance.
    assert all(d.provenance.source_uri for d in deals)
    # Debt notional attributed once per issuer (lead arranger only).
    lead_debt = [
        d
        for d in deals
        if d.source_deal_id and d.source_deal_id.startswith("ai-direct-debt:CoreWeave")
    ]
    notional_bearing = [d for d in lead_debt if (d.notional_amount_usd or 0) > 0]
    assert len(notional_bearing) == 1
    assert notional_bearing[0].notional_amount_usd == 25_000_000_000


def test_unnamed_suppliers_are_skipped_not_fabricated() -> None:
    deals = build_ai_direct_deals(_CENSUS, _CONTAGION)
    supplier_targets = {
        d.parties[1] for d in deals if d.source_deal_id and "supplier" in d.source_deal_id
    }
    assert "NVIDIA" in supplier_targets  # canonicalized
    assert not any("unnamed" in s.lower() for s in supplier_targets)


def test_injected_cluster_creates_shared_counterparty_hubs() -> None:
    deals = build_ai_direct_deals(_CENSUS, _CONTAGION)
    graph = build_capital_exposure_graph(deals)
    edges = graph.edges
    names = {e.target_name for e in edges} | {e.source_name for e in edges}
    # Cluster issuers, the GPU supplier, anchor customer, and a lender are all nodes.
    # Issuers join across fixtures on the normalized short name.
    assert "CoreWeave" in names
    assert "NVIDIA" in names  # canonicalized
    assert "Microsoft" in names  # canonicalized
    # NVIDIA + Microsoft + Goldman each touch BOTH issuers -> shared hubs.
    hub_names = {h["name"] for h in graph.summary.top_contagion_hubs}
    assert "NVIDIA" in hub_names or "Microsoft" in hub_names
    # The cluster debt is ai-infra relevant (GPU/data-center keywords present).
    assert graph.summary.ai_infra_relevant_notional_usd >= 25_000_000_000


def test_real_fixtures_inject_cleanly() -> None:
    census = json.loads(Path("handoffs/ai_direct_debt_census_20260603.json").read_text())
    contagion = json.loads(Path("handoffs/ai_direct_contagion_edges_20260603.json").read_text())
    deals = build_ai_direct_deals(census, contagion)
    assert len(deals) >= 11  # at least one debt deal per issuer
    graph = build_capital_exposure_graph(deals)
    # The real cluster debt dwarfs the prior ~$5B Equinix AI-infra mass.
    assert graph.summary.ai_infra_relevant_notional_usd > 50_000_000_000
