"""Claim-semantics gate-dimension fixtures (evidence-gate blind spot).

A quote can be quote-backed (provenance 0.78) yet semantically wrong; the semantic
dimension must cap those. Fixtures use the real mis-extraction quotes + real debt
controls.
"""

from __future__ import annotations

from bubble.quality.claim_semantics import (
    classify_claim_semantics,
    classify_claim_with_context,
    semantic_gate_confidence,
)


def test_committed_debt_quotes_pass() -> None:
    assert (
        classify_claim_semantics("$5 billion senior unsecured revolving credit agreement")["bucket"]
        == "committed_debt"
    )
    assert classify_claim_semantics(
        "$730 million aggregate principal amount of first lien notes due 2031"
    )["is_committed_debt"]


def test_asset_capacity_and_boilerplate_quotes_are_not_committed_debt() -> None:
    # Truist "loans held for investment" — an asset.
    assert (
        classify_claim_semantics(
            "consolidated loans and leases held for investment of $329.2 billion"
        )["bucket"]
        == "asset_or_capacity"
    )
    # PennyMac webcast boilerplate.
    assert (
        classify_claim_semantics(
            "The webcast can be accessed at pfsi.pennymac.com and a replay will be available"
        )["bucket"]
        == "boilerplate_only"
    )
    # Asset wins even when the quote also mentions notes (servicing deck).
    assert (
        classify_claim_semantics(
            "Servicing portfolio UPB of $733.6 billion; non-Agency subordinate notes"
        )["bucket"]
        == "asset_or_capacity"
    )


def test_gate_caps_quote_backed_but_semantically_wrong_claims() -> None:
    # A webcast boilerplate figure that is quote_backed at 0.78 must NOT stay high.
    boiler = semantic_gate_confidence(0.78, "The webcast can be accessed at pfsi.pennymac.com")
    assert boiler["effective_confidence"] == 0.25
    assert boiler["high_confidence_eligible"] is False

    # An asset figure is capped too.
    asset = semantic_gate_confidence(0.78, "total loans of $4.7 billion held for investment")
    assert asset["high_confidence_eligible"] is False

    # A genuine committed-debt claim keeps its provenance confidence.
    debt = semantic_gate_confidence(0.78, "$5 billion senior unsecured term loan facility")
    assert debt["effective_confidence"] == 0.78
    assert debt["high_confidence_eligible"] is True


def test_context_enrichment_resolves_indeterminate() -> None:
    # Terse quote (indeterminate alone) + debt subcategory -> committed_debt.
    assert (
        classify_claim_with_context(
            "the obligations referred to in clauses (i) through (iv)",
            subcategory="contract_tranche_terms",
        )["bucket"]
        == "committed_debt"
    )
    # Debt counterparty resolves it too.
    assert (
        classify_claim_with_context(
            "terse fragment", counterparty="JPMorgan, as Administrative Agent"
        )["bucket"]
        == "committed_debt"
    )
    # A non-debt subcategory (interconnection queue) -> flagged mis-categorized.
    assert (
        classify_claim_with_context(
            "Developer/Interconnection Customer | Project Name", subcategory="queue_project_match"
        )["bucket"]
        == "non_debt_miscategorized"
    )
    # An affirmative asset quote is NOT rescued by a debt subcategory.
    assert (
        classify_claim_with_context(
            "total loans of $4.7 billion held for investment", subcategory="contract_tranche_terms"
        )["bucket"]
        == "asset_or_capacity"
    )


def test_collateral_guarantee_lender_language_resolves_to_committed_debt() -> None:
    # Debt-agreement collateral/guarantee/lender/rate language -> committed_debt.
    for q in (
        "the obligations are secured by a first priority security interest",
        "guaranteed by the Guarantors on a senior basis",
        "the Lenders party thereto, at a rate equal to SOFR plus the applicable margin",
        "$2.0 billion of borrowings outstanding under the revolving facility",
    ):
        assert classify_claim_semantics(q)["bucket"] == "committed_debt"
    # Asset language still wins over a co-occurring lender word.
    assert (
        classify_claim_semantics("servicing portfolio UPB of $733B; lenders to the trust")["bucket"]
        == "asset_or_capacity"
    )


def test_equity_and_mortgage_production_are_flagged_not_committed_debt() -> None:
    # Equity / mortgage-production primary subject -> equity_or_production (block).
    assert (
        classify_claim_semantics("convert into Shares of Alibaba Health Information")["bucket"]
        == "equity_or_production"
    )
    assert (
        classify_claim_semantics("Mortgage closed loan production for the year ended")["bucket"]
        == "equity_or_production"
    )
    assert (
        classify_claim_semantics("any shares of our common stock sold will be sold")["bucket"]
        == "equity_or_production"
    )
    # A convertible NOTE is debt, not equity, despite mentioning shares.
    assert (
        classify_claim_semantics(
            "convertible senior notes convertible into shares at a conversion price"
        )["bucket"]
        == "committed_debt"
    )
    # A real credit agreement with an incidental 'shares' word stays committed_debt.
    assert (
        classify_claim_semantics(
            "entered into a $5 billion revolving credit agreement; proceeds may fund share repurchase"
        )["bucket"]
        == "committed_debt"
    )


def test_quarterly_earnings_results_snippets_are_boilerplate_not_committed_debt() -> None:
    # Real residual mis-extractions: a quarterly-earnings / results-announcement header
    # carries a balance-sheet or production figure, not a debt instrument. A mortgage
    # REIT's earnings release (PennyMac-style) and an 8-K Item 2.02 'Results of
    # Operations' header must NOT be rescued into the debt metric by a debt subcategory
    # or a 'noteholders' counterparty role.
    for q in (
        "PennyMac Mortgage Investment Trust Reports Fourth Quarter and Full-Year 2025 Results",
        "Results of Operations and Financial Condition. On October 28, 2025, Carrier Global Corp",
        "today reported net income attributable to common shareholders of $312.4 million",
    ):
        assert classify_claim_semantics(q)["bucket"] == "boilerplate_only"
        # Subcategory/counterparty context must NOT rescue an earnings header.
        assert (
            classify_claim_with_context(
                q, subcategory="contract_tranche_terms", counterparty="noteholders"
            )["bucket"]
            == "boilerplate_only"
        )
    # Negative control: a genuine notes snippet with the same 'noteholders' context is
    # still committed_debt (earnings markers are checked AFTER committed-debt).
    assert (
        classify_claim_with_context(
            "senior notes due 2030 in an aggregate principal amount of $1.0 billion",
            subcategory="contract_tranche_terms",
            counterparty="noteholders",
        )["bucket"]
        == "committed_debt"
    )
    # Negative control: a peripheral trustee/DTC prospectus snippet with NO earnings
    # phrase stays indeterminate at the quote level, so subcategory context can still
    # resolve it for reselection -- the earnings markers must not over-reach.
    assert (
        classify_claim_semantics(
            "payments will generally be senior to those of noteholders in respect of all funds"
        )["bucket"]
        == "indeterminate"
    )
