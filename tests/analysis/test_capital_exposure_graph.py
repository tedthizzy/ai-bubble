from bubble.analysis.capital_exposure_graph import build_capital_exposure_graph
from bubble.models.base import DealType, HumanReviewStatus, Provenance, SourceType
from bubble.models.deal import Deal, DebtTranche


def _provenance(source_uri: str, *, content_hash: str | None = None) -> Provenance:
    return Provenance(
        source_uri=source_uri,
        source_type=SourceType.SEC_EDGAR,
        confidence=0.9,
        human_review_status=HumanReviewStatus.PENDING,
        content_hash=content_hash or Provenance.compute_content_hash(source_uri),
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
    assert graph.summary.nodes == 2
    assert graph.summary.edges == 1
    assert graph.summary.source_backed_edges == 1
    assert graph.summary.debt_like_edges == 1
    assert graph.summary.ai_infra_relevant_edges == 1
    assert graph.summary.direct_ai_keyword_edges == 1
    assert graph.summary.ai_infra_relevant_notional_usd == 1_500_000_000
    assert graph.summary.total_edge_notional_usd == 1_500_000_000
    assert graph.edges[0].source_name == "CoreWeave SPV"
    assert "direct:compute" in graph.edges[0].relevance_tags
    assert {edge.target_name for edge in graph.edges} == {"Apollo Credit"}
    assert graph.summary.top_components_by_notional[0]["node_count"] == 2
    assert graph.summary.top_components_by_notional[0]["ai_infra_relevant_notional_usd"] == (
        1_500_000_000
    )
    assert graph.summary.ai_infra_component_count == 1
    assert graph.summary.top_ai_infra_component_nodes == 2
    assert graph.summary.top_ai_infra_component_edges == 1
    assert graph.summary.top_ai_infra_component_notional_usd == 1_500_000_000
    assert graph.summary.top_ai_infra_components_by_notional[0]["node_count"] == 2
    assert graph.summary.top_contagion_hubs[0]["name"] == "CoreWeave SPV"
    assert graph.summary.top_contagion_hubs[0]["distinct_counterparties"] == 1
    assert graph.summary.top_contagion_hubs[0]["risk_bearer_neighbor_count"] == 1
    assert graph.summary.top_ai_infra_contagion_hubs[0]["name"] == "CoreWeave SPV"


def test_capital_exposure_graph_excludes_agent_only_counterparties() -> None:
    deal = Deal(
        source_deal_id="agent-only-deal",
        deal_type=DealType.DEBT_FACILITY,
        title="GPU data center facility with agent-only counterparties",
        parties=[
            "CoreWeave SPV",
            "lenders party thereto",
            "JPMorgan Chase Bank",
            "U.S. Bank Trust Company, National Association",
        ],
        counterparty_roles={
            "borrower": ["CoreWeave SPV"],
            "lender": ["lenders party thereto"],
            "administrative_agent": ["JPMorgan Chase Bank"],
            "collateral_agent": ["U.S. Bank Trust Company, National Association"],
            "financier": [
                "JPMorgan Chase Bank",
                "U.S. Bank Trust Company, National Association",
            ],
        },
        notional_amount_usd=1_500_000_000,
        provenance=_provenance("sec:agent-only"),
        confidence=0.9,
    )

    graph = build_capital_exposure_graph([deal])

    assert graph.edges == []
    assert graph.summary.edges == 0
    assert graph.summary.generic_counterparty_mentions_skipped == 1
    assert graph.summary.high_notional_unmapped_deals == []


def test_capital_exposure_graph_filters_guarantor_clause_fragments() -> None:
    fragment = Deal(
        source_deal_id="guarantor-fragment",
        deal_type=DealType.DEBT_FACILITY,
        title="Credit agreement with guarantor clause fragment",
        parties=["Example Borrower Inc.", "TotalEnergies Capital USA and the Guarantor"],
        counterparty_roles={
            "borrower": ["Example Borrower Inc."],
            "guarantor": ["TotalEnergies Capital USA and the Guarantor"],
        },
        notional_amount_usd=500_000_000,
        provenance=_provenance("sec:guarantor-fragment"),
        confidence=0.9,
    )
    valid = Deal(
        source_deal_id="valid-guarantor",
        deal_type=DealType.DEBT_FACILITY,
        title="Credit agreement with named guarantor",
        parties=["Example Borrower Inc.", "Boost Newco Guarantor, LLC"],
        counterparty_roles={
            "borrower": ["Example Borrower Inc."],
            "guarantor": ["Boost Newco Guarantor, LLC"],
        },
        notional_amount_usd=600_000_000,
        provenance=_provenance("sec:valid-guarantor"),
        confidence=0.9,
    )

    graph = build_capital_exposure_graph([fragment, valid])

    assert [edge.target_name for edge in graph.edges] == ["Boost Newco Guarantor, LLC"]
    assert graph.edges[0].notional_usd == 600_000_000
    assert graph.summary.generic_counterparty_mentions_skipped == 1


def test_capital_exposure_graph_dedupes_duplicate_source_instrument_notional() -> None:
    content_hash = Provenance.compute_content_hash("same-credit-agreement")
    duplicate_a = Deal(
        source_deal_id="deal-duplicate-a",
        deal_type=DealType.DEBT_FACILITY,
        title="GPU cloud credit agreement",
        parties=["CoreWeave SPV", "Apollo Credit"],
        counterparty_roles={
            "borrower": ["CoreWeave SPV"],
            "lender": ["Apollo Credit"],
        },
        notional_amount_usd=3_500_000_000,
        provenance=_provenance("sec:credit-copy-a", content_hash=content_hash),
        confidence=0.9,
    )
    duplicate_b = Deal(
        source_deal_id="deal-duplicate-b",
        deal_type=DealType.DEBT_FACILITY,
        title="GPU cloud credit agreement duplicate filing",
        parties=["CoreWeave SPV", "Apollo Credit"],
        counterparty_roles={
            "borrower": ["CoreWeave SPV"],
            "lender": ["Apollo Credit"],
        },
        notional_amount_usd=3_500_000_000,
        provenance=_provenance("sec:credit-copy-b", content_hash=content_hash),
        confidence=0.9,
    )

    graph = build_capital_exposure_graph([duplicate_a, duplicate_b])

    assert graph.summary.deals_scanned == 2
    assert graph.summary.deals_with_edges == 2
    assert graph.summary.edges == 1
    assert graph.edges[0].deal_count == 2
    assert set(graph.edges[0].source_uris) == {"sec:credit-copy-a", "sec:credit-copy-b"}
    assert graph.edges[0].content_hashes == (content_hash,)
    assert graph.edges[0].notional_usd == 3_500_000_000
    assert graph.summary.total_edge_notional_usd == 3_500_000_000
    assert graph.summary.ai_infra_relevant_notional_usd == 3_500_000_000
    assert graph.nodes[0].exposure_usd == 3_500_000_000


def test_capital_exposure_graph_builds_contract_structure_graph() -> None:
    tranche = DebtTranche(
        name="Senior secured term loan",
        seniority=1,
        notional_usd=1_500_000_000,
        interest_rate=0.0725,
        maturity="2028-06-30",
        collateral_description="first-priority liens on GPU servers and accounts receivable",
        guarantors=["Example Parent LLC"],
        provenance=_provenance("sec:credit#tranche-a"),
        confidence=0.88,
    )
    deal = Deal(
        source_deal_id="deal-contract-1",
        deal_type=DealType.DEBT_FACILITY,
        title="CoreWeave SPV GPU collateral credit facility",
        parties=["CoreWeave SPV LLC", "Apollo Credit"],
        counterparty_roles={
            "borrower": ["CoreWeave SPV LLC"],
            "lender": ["Apollo Credit"],
            "guarantor": ["Example Parent LLC"],
        },
        debt_tranches=[tranche],
        is_non_recourse=True,
        bankruptcy_remote_spv=True,
        collateral=["substantially all GPU server collateral"],
        guarantees=["Example Parent LLC"],
        linked_projects=["CoreWeave Campus"],
        linked_assets=["NVIDIA H100 cluster"],
        provenance=_provenance("sec:credit"),
        confidence=0.9,
    )

    graph = build_capital_exposure_graph([deal])
    relationship_types = {edge.relationship_type for edge in graph.contract_edges}

    assert graph.summary.contract_nodes >= 9
    assert graph.summary.contract_edges >= 12
    assert graph.summary.source_backed_contract_edges == graph.summary.contract_edges
    assert graph.summary.deal_contract_nodes == 1
    assert graph.summary.tranche_contract_nodes == 1
    assert graph.summary.collateral_contract_nodes == 2
    assert graph.summary.guarantee_contract_edges == 2
    assert graph.summary.collateral_contract_edges == 3
    assert graph.summary.project_contract_edges == 1
    assert graph.summary.asset_contract_edges == 1
    assert graph.summary.non_recourse_contracts == 2
    assert graph.summary.bankruptcy_remote_spv_contracts == 2
    assert graph.summary.spv_flagged_contracts == 2
    assert graph.summary.tranche_nodes_with_maturity == 1
    assert graph.summary.tranche_nodes_with_interest_rate == 1
    assert "HAS_TRANCHE" in relationship_types
    assert "SECURED_BY_COLLATERAL" in relationship_types
    assert "TRANCHE_GUARANTEED_BY" in relationship_types
    assert graph.summary.top_tranche_contract_nodes[0]["source_uri"] == "sec:credit#tranche-a"
    assert graph.summary.top_collateral_contract_edges[0]["content_hash"]


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


def test_capital_exposure_graph_marks_non_specific_obligation_flags() -> None:
    deal = Deal(
        source_deal_id="aggregate-1",
        deal_type=DealType.BOND,
        title="Shelf registration for notes",
        parties=["Issuer Inc.", "noteholders"],
        counterparty_roles={"issuer": ["Issuer Inc."], "noteholder": ["noteholders"]},
        notional_amount_usd=25_000_000_000,
        key_terms={
            "notional_context_kind": "aggregate_shelf_capacity",
            "notional_commitment_scope": "shelf_capacity_non_specific",
            "notional_non_specific_obligation": True,
        },
        provenance=_provenance("sec:shelf"),
        confidence=0.85,
    )

    graph = build_capital_exposure_graph([deal])
    risk_flags = set(graph.contract_nodes[0].risk_flags)

    assert "aggregate_snapshot" in risk_flags
    assert "shelf_capacity" in risk_flags
    assert "non_specific_obligation" in risk_flags


def test_capital_exposure_graph_skips_non_actionable_collateral_language() -> None:
    deal = Deal(
        source_deal_id="deal-collateral-risk-factor",
        deal_type=DealType.DEBT_FACILITY,
        title="Credit agreement risk factors",
        parties=["Example Borrower LLC", "Example Lender Bank"],
        counterparty_roles={
            "borrower": ["Example Borrower LLC"],
            "lender": ["Example Lender Bank"],
        },
        notional_amount_usd=4_000_000_000,
        collateral=[
            (
                "As a result, investors may not be able to liquidate their investment readily, "
                "and lenders may not readily accept the notes as collateral for loans."
            )
        ],
        provenance=_provenance("sec:collateral-risk-factor"),
        confidence=0.8,
    )

    graph = build_capital_exposure_graph([deal])

    assert graph.summary.collateral_contract_edges == 0
    assert graph.summary.collateral_contract_nodes == 0
    assert all(edge.relationship_type != "SECURED_BY_COLLATERAL" for edge in graph.contract_edges)
