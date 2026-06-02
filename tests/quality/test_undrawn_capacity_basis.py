"""Undrawn-revolver-capacity-as-debt fixtures (RC1, capacity not drawn obligation).

A handful of ``approved_for_metric_use`` rows are supported by an ``evidence_quote`` that
describes undrawn revolver *availability* / a *terminated* commitment, not a drawn or issued
obligation -- e.g. Equinix $4.0B ("if ... borrowed all of the ... available under its revolving
credit facility ... would have been unsecured"), AMD $1.25B ("availability under that ...
revolving credit agreement"). Positives are the real undrawn-capacity quotes (verified against
``materiality_adjudication_decisions.csv``); negatives are genuinely issued/drawn debt quotes
that must NOT flag (Amrize "issued $3.4B aggregate principal", a notes issuance, a drawn revolver).
"""

from __future__ import annotations

from bubble.quality.undrawn_capacity_basis import (
    is_non_committed_debt_basis,
    is_shelf_or_resale_basis,
    quote_is_undrawn_capacity_basis,
)


def test_undrawn_revolver_and_terminated_commitment_quotes_flag() -> None:
    for quote in (
        # Equinix $4.0B -- hypothetical draw of undrawn availability
        "if Equinix, Inc. borrowed all of the approximately $4.0 billion available under its "
        "revolving credit facility, $4.0 billion of such borrowings would have been unsecured "
        "indebtedness",
        # AMD $1.25B -- revolver availability counted as liquidity
        "AMD's cash, cash equivalents, and short-term investment balances, together with the "
        "availability under that certain revolving credit agreement with Wells Fargo Bank, N.A.",
        # Westlake $1.5B -- explicit no-borrowings + borrowing availability
        "Westlake had no borrowings outstanding and no outstanding letters of credit under its "
        "revolving credit facility and had $1.5 billion of borrowing availability under its "
        "revolving credit facility",
        # McCormick $2.0B -- terminated bridge commitment
        "Effective April 28, 2026, McCormick terminated $2.0 billion of the commitments of the "
        "Commitment Parties under the Bridge Facility",
    ):
        assert quote_is_undrawn_capacity_basis(quote) is True, quote[:50]


def test_issued_or_drawn_debt_quotes_do_not_flag() -> None:
    for quote in (
        # Amrize $3.4B -- genuinely issued debt (negative control; must NOT flag)
        "In connection with the Spin-off, we issued $3.4 billion in aggregate principal amount",
        # A notes issuance -- real drawn/issued debt
        "$1,500,000,000 aggregate principal amount of its 5.45% senior notes due 2032",
        # A drawn revolver -- borrowings actually outstanding
        "As of March 31, 2026, $1,347.0 million of borrowings were outstanding under our "
        "Revolving Credit Facility",
        # Plain term-loan draw
        "the Borrower drew $600 million under the Delayed Draw Term Loan on the closing date",
        # AutoNation-class: a "total indebtedness" disclosure of real drawn debt that also notes an
        # undrawn revolver portion -- the supported amount is the real debt, not the undrawn part.
        "had approximately $7.7 billion of total indebtedness including borrowings under our credit "
        "agreement and our existing senior notes, with an undrawn portion remaining on the revolver",
        # Getty-class: a "total debt was" disclosure whose amount is notes, alongside a separate
        # small undrawn revolver.
        "Total debt was $2.7 billion, which included $1.2 billion in Senior Secured Notes; the "
        "Company has $150.0 million available through its Revolver, which remains undrawn",
        # Discriminator (synthetic): a notes issuance that ALSO mentions revolver availability.
        # The supported amount is the issued notes, not the revolver -- the issuance language must
        # override the incidental "available under" (this is the real false-positive class I dropped:
        # notes-issuance rows where "available" appears incidentally).
        "we will issue the notes; the Company also had $5.0 billion of additional liquidity "
        "available under its revolving credit facility, and $5,000,000,000 aggregate principal "
        "amount of its senior notes due 2035",
    ):
        assert quote_is_undrawn_capacity_basis(quote) is False, quote[:50]


def test_empty_and_unrelated_quotes_do_not_flag() -> None:
    assert quote_is_undrawn_capacity_basis("") is False
    assert quote_is_undrawn_capacity_basis("Governing Law The notes and the indentures") is False


def test_shelf_or_resale_registration_quotes_flag() -> None:
    for quote in (
        # Alphabet $4.25B -- no-proceeds resale
        "we will not receive any proceeds from the sale of securities by selling securityholders",
        # Nebius / Hut 8 -- base-shelf "may offer" language
        "We or our selling securityholders may also loan or pledge securities covered by this prospectus",
        "We and/or the selling securityholders will identify the specific plan of distribution",
        "We or the selling securityholders may offer and sell these securities from time to time",
    ):
        assert is_shelf_or_resale_basis(quote) is True, quote[:50]


def test_real_issuance_is_not_shelf_or_resale() -> None:
    for quote in (
        "$1,500,000,000 aggregate principal amount of its 5.45% senior notes due 2032",
        "the Borrower drew $600 million under the Delayed Draw Term Loan on the closing date",
        "6.192% Senior Secured Notes due 2042 Indenture dated as of April 30, 2026",
    ):
        assert is_shelf_or_resale_basis(quote) is False, quote[:50]


def test_non_committed_debt_basis_unions_both_classes() -> None:
    # undrawn capacity
    assert is_non_committed_debt_basis("availability under that revolving credit agreement") is True
    # shelf/resale
    assert is_non_committed_debt_basis("the selling securityholders may offer these securities") is True
    # real committed debt -> False
    assert is_non_committed_debt_basis("$2,000,000,000 aggregate principal amount of senior notes due 2031") is False
