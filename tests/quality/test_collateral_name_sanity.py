"""Collateral-name-sanity fixtures (contract-graph collateral layer, 79% prose).

A collateral node name should be a short identifier ("first priority lien on substantially
all assets", "pledged equity of the Borrower"). The contract graph instead fills most
collateral names with covenant / business-description PROSE (a BDC strategy paragraph, a lien
covenant clause). Positives are the real malformed prose; negatives are genuine short
collateral identifiers that must pass.
"""

from __future__ import annotations

from bubble.quality.collateral_name_sanity import is_prose_collateral_name


def test_covenant_and_business_prose_collateral_names_are_flagged() -> None:
    for name in (
        "We focus on investing in privately originated senior secured loans which are generally "
        "debt instruments that pay floating interest rates and rank ahead of subordinated debt",
        "amount of the obligations secured by the lien extended, renewed, refinanced, refunded or "
        "replaced and any expenses of the Guarantor and its Subsidiaries",
        "(a) Amounts held in the LC Cash Collateral Account shall be the property of the Credit "
        "Facility Agent for the benefit of the Issuing Banks",
        "provided that the Borrower shall have demonstrated by delivery of an updated Base Case",
    ):
        assert is_prose_collateral_name(name) is True, name[:40]


def test_short_collateral_identifiers_pass() -> None:
    for name in (
        "first priority lien on substantially all assets",
        "pledged equity interests of the Borrower",
        "first mortgage on the Polaris Forge 2 facility",
        "first lien",
        "second lien",
        "Notes payable secured by mortgage servicing assets",
    ):
        assert is_prose_collateral_name(name) is False, name


def test_overlong_name_is_flagged_and_empty_is_safe() -> None:
    assert is_prose_collateral_name("x" * 130) is True
    assert is_prose_collateral_name("") is False  # empty -> not prose (a separate missing-name case)
