from __future__ import annotations

from bubble.analysis.ecosystem_scope import (
    ecosystem_balance_sheet_context_reasons,
    ecosystem_scope_reasons,
    scope_deals,
)
from bubble.models.base import DealType, HumanReviewStatus, Provenance, SourceType
from bubble.models.deal import Deal


def _prov(source_uri: str) -> Provenance:
    return Provenance(
        source_uri=source_uri,
        source_type=SourceType.SEC_EDGAR,
        confidence=0.9,
        human_review_status=HumanReviewStatus.APPROVED,
        content_hash=Provenance.compute_content_hash(source_uri),
    )


def test_core_ai_infra_entity_is_direct_scope_without_keyword() -> None:
    deal = Deal(
        source_deal_id="edgar:0001083301:000000000000000000:bond:wulf",
        deal_type=DealType.BOND,
        title="Corporate notes",
        parties=["TERAWULF INC.", "noteholders"],
        counterparty_roles={"issuer": ["TERAWULF INC."], "noteholder": ["noteholders"]},
        notional_amount_usd=500_000_000,
        provenance=_prov("sec:wulf"),
    )

    assert ecosystem_scope_reasons(deal) == [
        "core_ai_data_center_cik",
        "core_ai_data_center_entity",
    ]
    assert ecosystem_balance_sheet_context_reasons(deal) == []


def test_broad_watchlist_entity_requires_direct_context_for_headline_scope() -> None:
    generic_amazon_bond = Deal(
        source_deal_id="edgar:0001018724:000000000000000000:bond:amazon",
        deal_type=DealType.BOND,
        title="Corporate notes",
        parties=["AMAZON COM INC", "noteholders"],
        counterparty_roles={"issuer": ["AMAZON COM INC"], "noteholder": ["noteholders"]},
        notional_amount_usd=6_000_000_000,
        provenance=_prov("sec:amazon-generic"),
    )
    ai_amazon_facility = Deal(
        source_deal_id="edgar:0001018724:000000000000000001:debt_facility:amazon-ai",
        deal_type=DealType.DEBT_FACILITY,
        title="AI data center infrastructure facility",
        parties=["AMAZON COM INC", "lenders"],
        counterparty_roles={"borrower": ["AMAZON COM INC"], "lender": ["lenders"]},
        notional_amount_usd=2_000_000_000,
        provenance=_prov("sec:amazon-ai"),
    )

    assert ecosystem_scope_reasons(generic_amazon_bond) == []
    assert ecosystem_balance_sheet_context_reasons(generic_amazon_bond) == [
        "watchlist_balance_sheet_cik",
    ]
    assert ecosystem_scope_reasons(ai_amazon_facility) == [
        "direct_ai_data_center_keyword",
    ]

    scoped, summary = scope_deals([generic_amazon_bond, ai_amazon_facility])

    assert scoped == [ai_amazon_facility]
    assert summary.in_scope_deal_count == 1
    assert summary.out_of_scope_deal_count == 1
    assert summary.in_scope_debt_like_notional_usd == 2_000_000_000
    assert summary.out_of_scope_debt_like_notional_usd == 6_000_000_000
    assert summary.balance_sheet_context_deal_count == 1
    assert summary.balance_sheet_context_debt_like_notional_usd == 6_000_000_000
    assert summary.inclusion_reason_counts == {"direct_ai_data_center_keyword": 1}
    assert summary.balance_sheet_context_reason_counts == {"watchlist_balance_sheet_cik": 1}
