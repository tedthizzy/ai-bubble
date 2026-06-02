"""Strict indirect-supplier linkage rule fixtures (relevance scope, indirect tier).

A utility / telecom is an INDIRECT AI/data-center supplier. The strict rule includes its
debt in `watchlist` only when the debt filing itself names a data center / hyperscaler /
colocation -- not on sector membership. Positive = the real Enbridge/Meta case; negatives =
real utility/telecom debt snippets that are silent on data centers (must NOT qualify).
"""

from __future__ import annotations

from bubble.quality.indirect_linkage_rule import is_quote_evidenced_dc_linkage


def test_quote_naming_a_data_center_or_hyperscaler_qualifies() -> None:
    assert is_quote_evidenced_dc_linkage(
        "the project supports Meta's technology and data center operations in the region"
    )
    assert is_quote_evidenced_dc_linkage(
        "proceeds fund a new hyperscale colocation facility leased to a hyperscaler"
    )
    assert is_quote_evidenced_dc_linkage(
        "a power purchase agreement with Microsoft for its data center load"
    )


def test_silent_utility_and_telecom_debt_snippets_do_not_qualify() -> None:
    # Real-shaped utility/telecom debt snippets with no data-center reference -> excluded.
    for quote in (
        "first mortgage bonds, 5.10% series due 2034, of the operating utility",
        "senior notes due 2032 issued under the indenture for general corporate purposes",
        "revolving credit facility for working capital and capital expenditures",
        "Georgia Power Company aggregate principal amount of $750 million senior notes",
    ):
        assert not is_quote_evidenced_dc_linkage(quote), quote


def test_incidental_hyperscaler_name_without_dc_context_does_not_qualify() -> None:
    # A bare vendor mention with no data-center / capacity / PPA context is not enough.
    assert not is_quote_evidenced_dc_linkage(
        "the company uses Amazon Web Services for corporate email and back-office systems"
    )
