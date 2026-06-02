"""Undrawn-revolver-capacity-as-debt gate (root cause 1, capacity not a drawn obligation).

The size metric is meant to capture committed/drawn debt-like obligations. A few
``approved_for_metric_use`` rows are instead supported by an ``evidence_quote`` describing
undrawn revolver *availability* or a *terminated* commitment -- e.g. Equinix $4.0B ("if ...
borrowed all of the ... available under its revolving credit facility ... would have been
unsecured"), AMD $1.25B ("availability under that ... revolving credit agreement"), McCormick
$2.0B ("terminated $2.0 billion of the commitments ... under the Bridge Facility"). Those are
capacity/commitments, not drawn obligations.

``quote_is_undrawn_capacity_basis`` flags a quote whose basis is undrawn capacity. It requires an
undrawn-capacity marker AND the *absence* of issuance/drawn markers -- the issuance override is
what drops the real false-positive class (notes-issuance rows that mention a revolver only
incidentally, e.g. Amrize "issued $3.4 billion in aggregate principal amount", Equinix $18.1B notes
indentures). Pure functions; the production adjudication gate is Codex's.
"""

from __future__ import annotations

# Undrawn revolver availability / terminated-commitment language (capacity, not a drawn draw).
UNDRAWN_CAPACITY_MARKERS = (
    "available under",
    "availability under",
    "borrowing availability",
    "additional liquidity available",
    "liquidity available",
    "undrawn",
)
# NOTE (precision): this predicate is a RECALL-oriented screen, not a classifier. A substring marker
# cannot bind to the specific supported amount, so a row whose undrawn facility differs from the
# supported obligation still over-flags -- e.g. a quote that reports "total debt" / "total
# indebtedness" (real drawn debt) while also noting an undrawn revolver PORTION (AutoNation $7.7B
# total indebtedness; Getty $1.2B Senior Secured Notes alongside a separate undrawn $150M revolver).
# The total-debt-framing override below catches that class, but raw corpus output MUST still be
# verified per-row -- see the handoff. Deliberately NOT keying on "would have been (un)secured
# indebtedness": that phrase appears in pro-forma debt-RANKING disclosures of real debt.

# Issuance / drawn-obligation language. If present, the supported amount is a real obligation and
# an incidental "available under" must NOT make the row look like undrawn capacity.
ISSUED_OR_DRAWN_MARKERS = (
    "issued $",
    "issue the notes",
    "aggregate principal amount of its",
    "senior notes due",
    "notes due 20",
    "borrowings were outstanding",
    "amount outstanding under",
    "drew $",
    "total indebtedness",
    "total debt was",
)


def _has_terminated_commitment(lowered: str) -> bool:
    """McCormick-class: a commitment that was terminated (capacity removed, not a draw)."""

    return "terminated" in lowered and "commitments" in lowered


def quote_is_undrawn_capacity_basis(text: str) -> bool:
    """True when the quote's basis is undrawn revolver capacity / a terminated commitment."""

    lowered = (text or "").lower()
    if not lowered:
        return False
    if any(marker in lowered for marker in ISSUED_OR_DRAWN_MARKERS):
        return False
    if any(marker in lowered for marker in UNDRAWN_CAPACITY_MARKERS):
        return True
    return _has_terminated_commitment(lowered)


# Base-shelf / resale-registration language: the issuer registers CAPACITY (and a resale component
# where it receives no proceeds), not a committed issuance. Verified on Alphabet $4.25B, Nebius
# $3.16B, Hut 8 $1.0B, Northrim $2.1B -- each a base-prospectus cover, not a drawn obligation.
SHELF_OR_RESALE_MARKERS = (
    "will not receive any proceeds",
    "selling securityholder",
    "selling security holder",
    "selling stockholder",
    "for the account of the selling",
)


def is_shelf_or_resale_basis(text: str) -> bool:
    """True when the quote's basis is a shelf/resale registration, not a committed issuance."""

    lowered = (text or "").lower()
    if not lowered:
        return False
    return any(marker in lowered for marker in SHELF_OR_RESALE_MARKERS)


def is_non_committed_debt_basis(text: str) -> bool:
    """Union of the RC1 capacity/registration-as-debt classes: undrawn capacity OR shelf/resale.

    A True here means the supported amount is NOT evidenced as a drawn/committed obligation -- it is
    revolver availability, a terminated commitment, or a shelf/resale registration -- and warrants
    adjudication review before counting it as debt.
    """

    return quote_is_undrawn_capacity_basis(text) or is_shelf_or_resale_basis(text)
