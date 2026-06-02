from __future__ import annotations

import json

from bubble.ingestion.compute import extract_economic_commitments


def _row(text: str, **metadata: str) -> dict[str, str]:
    return {
        "source_id": "fixture",
        "source_uri": "https://example.test/source",
        "document_id": "doc-1",
        "metadata": json.dumps(metadata),
        "text": text,
    }


def test_extracts_blended_datacenter_purchase_commitment() -> None:
    row = _row(
        "As of June 30, 2025, purchase commitments primarily relate to "
        "datacenters and include open purchase orders and take-or-pay contracts. "
        "These commitments were $109.953 billion.",
        entity="Microsoft",
    )

    terms = extract_economic_commitments(row)

    assert len(terms) == 1
    term = terms[0]
    assert term.term_type == "datacenter_purchase_commitment"
    assert term.value == "109953000000"
    assert term.binding_tier == "BINDING_BLENDED_BUYER"
    assert "cancellable purchase orders" in term.double_count_caveat
    assert term.entity == "Microsoft"


def test_extracts_not_commenced_datacenter_lease() -> None:
    row = _row(
        "We have entered into datacenter leases that have not yet commenced. "
        "Future lease payments for these leases are $92.7 billion.",
        entity="Microsoft",
    )

    terms = extract_economic_commitments(row)

    assert {(term.term_type, term.value, term.binding_tier) for term in terms} == {
        ("not_commenced_datacenter_lease", "92700000000", "BINDING_LEASE")
    }


def test_extracts_seller_side_rpo_as_mirror_not_additive() -> None:
    row = _row(
        "Remaining performance obligations under our customer contracts were "
        "$60.7 billion. Substantially all revenue is generated under take-or-pay "
        "contracts for AI compute capacity, and customers pay regardless of utilization.",
        entity="CoreWeave",
    )

    terms = extract_economic_commitments(row)

    assert len(terms) == 1
    term = terms[0]
    assert term.term_type == "seller_remaining_performance_obligation"
    assert term.binding_tier == "BINDING_TAKE_OR_PAY_SELLER_MIRROR"
    assert "do not sum with buyer-side" in term.double_count_caveat


def test_excludes_lessor_revenue_projection_from_binding_tally() -> None:
    row = _row(
        "The Polaris Forge colocation leases are expected to generate "
        "anticipated rental revenue of approximately $11 billion over the term.",
        entity="Applied Digital",
        counterparty="CoreWeave",
    )

    terms = extract_economic_commitments(row)

    assert len(terms) == 1
    assert terms[0].term_type == "lessor_revenue_projection"
    assert terms[0].binding_tier == "NON_BINDING_LESSOR_REVENUE"
    assert terms[0].counterparty == "CoreWeave"


def test_extracts_gigawatt_only_capacity_without_dollar_amount() -> None:
    row = _row(
        "Anthropic, Google, and Broadcom announced approximately 3.5 GW of "
        "next-generation TPU capacity from 2027 for AI compute, with no dollar "
        "amount disclosed.",
        entity="Anthropic",
    )

    terms = extract_economic_commitments(row)

    assert {(term.term_type, term.value, term.unit, term.binding_tier) for term in terms} == {
        ("capacity_only_no_dollar", "3.5", "GW", "GIGAWATT_ONLY_NO_DOLLAR")
    }


def test_ignores_generic_debt_and_cash_amounts() -> None:
    row = _row(
        "The company issued $5.0 billion of senior notes and held $2.0 billion "
        "of cash. The disclosure did not discuss datacenter leases, take-or-pay "
        "capacity, or purchase commitments.",
        entity="Generic Issuer",
    )

    assert extract_economic_commitments(row) == []
