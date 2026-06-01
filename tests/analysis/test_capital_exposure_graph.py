from bubble.analysis.capital_exposure_graph import build_capital_exposure_graph
from bubble.models.base import DealType, HumanReviewStatus, Provenance, SourceType
from bubble.models.deal import Deal


def _provenance(source_uri: str) -> Provenance:
    return Provenance(
        source_uri=source_uri,
        source_type=SourceType.SEC_EDGAR,
        confidence=0.9,
        human_review_status=HumanReviewStatus.PENDING,
        content_hash=Provenance.compute_content_hash(source_uri),
    )


def test_capital_exposure_graph_builds_named_source_backed_edges() -> None:
    deal = Deal(
        source_deal_id="deal-1",
        deal_type=DealType.DEBT_FACILITY,
        title="GPU collateral facility for CoreWeave data center cluster",
        parties=["CoreWeave SPV", "Apollo Credit"],
        counterparty_roles={
            "borrower": ["CoreWeave SPV"],
            "lender": ["Apollo Credit"],
            "administrative_agent": ["JPMorgan Chase Bank"],
        },
        notional_amount_usd=1_500_000_000,
        provenance=_provenance("sec:credit"),
        confidence=0.9,
    )

    graph = build_capital_exposure_graph([deal])

    assert graph.summary.deals_scanned == 1
    assert graph.summary.nodes == 3
    assert graph.summary.edges == 2
    assert graph.summary.source_backed_edges == 2
    assert graph.summary.debt_like_edges == 2
    assert graph.summary.ai_infra_relevant_edges == 2
    assert graph.summary.direct_ai_keyword_edges == 2
    assert graph.summary.ai_infra_relevant_notional_usd == 3_000_000_000
    assert graph.summary.total_edge_notional_usd == 3_000_000_000
    assert graph.edges[0].source_name == "CoreWeave SPV"
    assert "direct:compute" in graph.edges[0].relevance_tags
    assert {edge.target_name for edge in graph.edges} == {"Apollo Credit", "JPMorgan Chase Bank"}
    assert graph.summary.top_components_by_notional[0]["node_count"] == 3
    assert graph.summary.top_components_by_notional[0]["ai_infra_relevant_notional_usd"] == (
        3_000_000_000
    )
    assert graph.summary.ai_infra_component_count == 1
    assert graph.summary.top_ai_infra_component_nodes == 3
    assert graph.summary.top_ai_infra_component_edges == 2
    assert graph.summary.top_ai_infra_component_notional_usd == 3_000_000_000
    assert graph.summary.top_ai_infra_components_by_notional[0]["node_count"] == 3
    assert graph.summary.top_contagion_hubs[0]["name"] == "CoreWeave SPV"
    assert graph.summary.top_contagion_hubs[0]["distinct_counterparties"] == 2
    assert graph.summary.top_contagion_hubs[0]["risk_bearer_neighbor_count"] == 2
    assert graph.summary.top_ai_infra_contagion_hubs[0]["name"] == "CoreWeave SPV"


def test_capital_exposure_graph_keeps_ai_component_separate_from_broad_market_graph() -> None:
    ai_deal = Deal(
        source_deal_id="ai-deal",
        deal_type=DealType.DEBT_FACILITY,
        title="GPU cloud data center facility",
        parties=["CoreWeave SPV", "Apollo Credit"],
        counterparty_roles={
            "borrower": ["CoreWeave SPV"],
            "lender": ["Apollo Credit"],
        },
        notional_amount_usd=1_500_000_000,
        provenance=_provenance("sec:ai-credit"),
        confidence=0.9,
    )
    unrelated_deal = Deal(
        source_deal_id="non-ai-deal",
        deal_type=DealType.DEBT_FACILITY,
        title="Warehouse revolving credit facility",
        parties=["Retail Borrower Inc.", "Regional Bank"],
        counterparty_roles={
            "borrower": ["Retail Borrower Inc."],
            "lender": ["Regional Bank"],
        },
        notional_amount_usd=10_000_000_000,
        provenance=_provenance("sec:retail-credit"),
        confidence=0.9,
    )

    graph = build_capital_exposure_graph([ai_deal, unrelated_deal])

    assert graph.summary.connected_components == 2
    assert graph.summary.top_components_by_notional[0]["notional_usd"] == 10_000_000_000
    assert graph.summary.ai_infra_component_count == 1
    assert graph.summary.top_ai_infra_component_notional_usd == 1_500_000_000
    assert graph.summary.top_ai_infra_components_by_notional[0]["top_entities"][0]["name"] == (
        "CoreWeave SPV"
    )
    assert graph.summary.top_ai_infra_contagion_hubs[0]["name"] == "CoreWeave SPV"


def test_capital_exposure_graph_skips_generic_counterparties_and_preserves_ppa_capacity() -> None:
    generic_bond = Deal(
        source_deal_id="deal-2",
        deal_type=DealType.BOND,
        title="Senior notes",
        parties=["Akamai", "noteholders"],
        counterparty_roles={"issuer": ["Akamai"], "noteholder": ["noteholders"]},
        notional_amount_usd=2_000_000_000,
        provenance=_provenance("sec:bond"),
        confidence=0.8,
    )
    ppa = Deal(
        source_deal_id="ppa-1",
        deal_type=DealType.PPA,
        title="Power purchase agreement",
        parties=["Solar Project LLC", "Utility Buyer"],
        counterparty_roles={
            "seller": ["Solar Project LLC"],
            "offtaker": ["Utility Buyer"],
        },
        key_terms={"amount_mw": 125},
        provenance=_provenance("ferc:ppa"),
        confidence=0.9,
    )

    graph = build_capital_exposure_graph([generic_bond, ppa])

    assert graph.summary.deals_scanned == 2
    assert graph.summary.deals_with_edges == 1
    assert graph.summary.generic_counterparty_mentions_skipped == 1
    assert graph.summary.ppa_edges == 1
    assert graph.summary.ppa_capacity_mw == 125
    assert graph.edges[0].relationship_type == "PPA_COUNTERPARTY"


def test_capital_exposure_graph_rejects_broken_counterparty_clauses() -> None:
    deal = Deal(
        source_deal_id="deal-3",
        deal_type=DealType.DEBT_FACILITY,
        title="Credit agreement",
        parties=["Example Borrower Inc.", "banks named therein, JPMorgan Chase Bank, N.A."],
        counterparty_roles={
            "borrower": ["Example Borrower Inc."],
            "financier": [
                "banks named therein, JPMorgan Chase Bank, N.A.",
                "Wells Fargo Bank, National Association",
            ],
        },
        notional_amount_usd=5_000_000_000,
        provenance=_provenance("sec:broken-clause"),
        confidence=0.8,
    )

    graph = build_capital_exposure_graph([deal])

    assert graph.summary.generic_counterparty_mentions_skipped == 1
    assert graph.summary.edges == 1
    assert graph.edges[0].target_name == "Wells Fargo Bank, National Association"
