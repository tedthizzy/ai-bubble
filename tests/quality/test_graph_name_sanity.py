"""Graph name-sanity parity fixtures (RC4: role-leak / covenant-phrase nodes).

Positive cases are the exact malformed strings found in the capital-exposure graph
(covenant fragments, bare role words, truncated entities, leaked test data). Negative
controls are real named SPV/financing LLCs that legitimately contain a role word and
MUST pass, so the gate cannot drop a genuine counterparty.
"""

from __future__ import annotations

from bubble.quality.graph_name_sanity import is_malformed_entity_name


def test_malformed_covenant_and_role_fragments_are_rejected() -> None:
    for name in (
        "Company as obligor or any guarantor",
        "1) the Existing Borrower",
        "Borrowers, the Company",
        "Company as obligor or to any Guarantor",
        "Subsidiary Guarantor",
        "Resigning Borrower",
        "Initial Borrower",
        "Borrower (or from the Company",
        "Lending Service Provider by Borrower",
        "test1",  # leaked test data
    ):
        assert is_malformed_entity_name(name) is True, name


def test_real_named_spv_entities_with_role_words_pass() -> None:
    # These contain borrower/guarantor/lender but are genuine legal names -> must NOT flag.
    # The trailing-clause cases (a corporate token mid-string) are the precision guard:
    # a real entity must pass even when a descriptive/role clause follows its name.
    for name in (
        "Boost Newco Borrower, LLC",
        "Boost Newco Guarantor, LLC",
        "SABRE FINANCIAL BORROWER, LLC",
        "ACF II SOHO MEZZ LENDER LLC",
        "AREEIF Lender MS LLC, a Delaware limited liability company",
        "Southern Company Services, Inc. (as Agent)",
        "ACF II SOHO Mezz Lender LLC, an affiliate of the Investor",
        "National Bank of Canada, as agent and",  # truncated, but a real entity is present
        "JPMorgan Chase Bank, N.A.",
        "Apollo Global Management, Inc.",
        "CoreWeave, Inc.",
    ):
        assert is_malformed_entity_name(name) is False, name


def test_empty_and_role_only_names_are_rejected() -> None:
    assert is_malformed_entity_name("") is True
    assert is_malformed_entity_name("noteholders") is True
    assert is_malformed_entity_name("the lenders party thereto") is True


def test_foreign_suffix_spvs_with_role_words_pass() -> None:
    # International SPV/fund legal names (ownership graph) -> must NOT flag.
    for name in (
        "SBK Borrower B.V.",
        "ESDF II ABL Borrower SCSp",
        "RS LENDER III, S.A R.L.",
        "PUMA LENDER S.A R.L.",
        "Project Borrower S.a r.l.",
        "Acme Lender Pty Ltd",
    ):
        assert is_malformed_entity_name(name) is False, name
