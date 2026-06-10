"""Cross-filing strict-collapse fixtures (the -$48.8B layer's verified rule).

The cross-filing fingerprint collapse must use the STRICT rule -- collapse an (entity, rounded-amount)
bucket spanning 2+ accessions ONLY IF a single coupon/maturity token is common to EVERY member (and
every member has a non-empty descriptor). Verified to reproduce $48.78B / 25 groups (7/7 checked).
The negative controls below pin down the two over-collapse traps found during design:
(a) pairwise union-find (A-B share X, B-C share Y, no token common to ALL) -> must NOT collapse;
(b) a member with an empty descriptor -> must NOT collapse the bucket.
"""

from __future__ import annotations

from bubble.quality.cross_filing_duplication import summarize_cross_filing_collapse


def _row(entity: str, amount: float, accession: str, quote: str) -> dict[str, object]:
    return {"entity": entity, "amount_usd": amount, "accession": accession, "evidence_quote": quote}


def test_same_instrument_across_two_filings_collapses() -> None:
    rows = [
        _row(
            "Hut 8 Corp.", 3_250_000_000, "acc1", "Announces Pricing of $3.25 Billion 6.192% notes"
        ),
        _row(
            "Hut 8 Corp.", 3_250_000_000, "acc2", "6.192% Senior Secured Notes due 2042 Indenture"
        ),
    ]
    out = summarize_cross_filing_collapse(rows)
    assert out["collapsed_group_count"] == 1
    assert out["collapsed_excess_usd"] == 3_250_000_000  # (2 filings - 1) * amount


def test_union_find_trap_does_not_collapse() -> None:
    # A-B share the 5.000% coupon; B-C share "due 2031"; but NO token is common to all three.
    rows = [
        _row("Acme", 1_000_000_000, "acc1", "5.000% notes due 2030"),
        _row("Acme", 1_000_000_000, "acc2", "5.000% notes due 2031"),
        _row("Acme", 1_000_000_000, "acc3", "6.250% notes due 2031"),
    ]
    out = summarize_cross_filing_collapse(rows)
    assert out["collapsed_group_count"] == 0
    assert out["collapsed_excess_usd"] == 0


def test_member_with_empty_descriptor_does_not_collapse() -> None:
    rows = [
        _row("Acme", 1_000_000_000, "acc1", "5.000% senior notes due 2030"),
        _row("Acme", 1_000_000_000, "acc2", "5.000% senior notes due 2030"),
        _row(
            "Acme",
            1_000_000_000,
            "acc3",
            "the Company entered into a material definitive agreement",
        ),
    ]
    out = summarize_cross_filing_collapse(rows)
    assert (
        out["collapsed_group_count"] == 0
    )  # one member has no coupon/maturity -> strict rule abstains


def test_distinct_fingerprints_do_not_collapse() -> None:
    rows = [
        _row("Acme", 1_000_000_000, "acc1", "4.350% notes due 2029"),
        _row("Acme", 1_000_000_000, "acc2", "6.875% notes due 2034"),
    ]
    out = summarize_cross_filing_collapse(rows)
    assert out["collapsed_group_count"] == 0


def test_same_accession_is_not_this_passes_job() -> None:
    rows = [
        _row("Acme", 1_000_000_000, "acc1", "5.000% notes due 2030"),
        _row("Acme", 1_000_000_000, "acc1", "5.000% notes due 2030"),
    ]
    out = summarize_cross_filing_collapse(rows)
    assert out["collapsed_group_count"] == 0  # single accession -> within-filing pass handles it
