"""Within-filing duplication fixtures (same entity + amount + SEC accession counted 2+ times).

Running Codex's real `_final_metric_representative_decisions` shows 112 (entity, amount, accession)
groups surviving the final-metric dedup 2+ times ($220B excess) -- e.g. Amazon $6B 2036 notes, CME
$10B 364-day facility, Ford $4B revolver x3, Hut 8 / TeraWulf / CoreWeave notes. They survive
because intra-filing drift (multiple content-hashes, subcategory reclassification, an empty
snapshot_date) defeats the (entity, amount, subcategory, month, counterparty) collapse key. An
(entity, amount, accession) key is invariant to all of it. Positives are same-filing repeats;
negatives are same amount in DIFFERENT filings (legitimately may be distinct instruments).
"""

from __future__ import annotations

from bubble.quality.within_filing_duplication import (
    accession_from_uri,
    collapse_within_filing,
    summarize_within_filing_duplication,
)


def test_same_entity_amount_accession_repeated_is_excess() -> None:
    rows = [
        {
            "entity": "AMAZON COM INC",
            "amount_usd": 6_000_000_000,
            "accession": "000110465926027729",
        },
        {
            "entity": "AMAZON COM INC",
            "amount_usd": 6_000_000_000,
            "accession": "000110465926027729",
        },
        {"entity": "FORD MOTOR CO", "amount_usd": 4_000_000_000, "accession": "000003799626000079"},
        {"entity": "FORD MOTOR CO", "amount_usd": 4_000_000_000, "accession": "000003799626000079"},
        {"entity": "FORD MOTOR CO", "amount_usd": 4_000_000_000, "accession": "000003799626000079"},
    ]
    out = summarize_within_filing_duplication(rows)
    assert out["duplicate_group_count"] == 2  # Amazon x2 and Ford x3
    # excess = (2-1)*6B + (3-1)*4B = 6B + 8B = 14B
    assert out["excess_usd"] == 14_000_000_000


def test_same_amount_in_different_filings_is_not_within_filing_dup() -> None:
    rows = [
        {"entity": "ACME", "amount_usd": 1_000_000_000, "accession": "000000000000000001"},
        {"entity": "ACME", "amount_usd": 1_000_000_000, "accession": "000000000000000002"},
    ]
    out = summarize_within_filing_duplication(rows)
    assert out["duplicate_group_count"] == 0
    assert out["excess_usd"] == 0


def test_different_amounts_same_filing_are_not_dups() -> None:
    rows = [
        {"entity": "ACME", "amount_usd": 1_000_000_000, "accession": "000000000000000001"},
        {"entity": "ACME", "amount_usd": 2_000_000_000, "accession": "000000000000000001"},
    ]
    out = summarize_within_filing_duplication(rows)
    assert out["duplicate_group_count"] == 0
    assert out["excess_usd"] == 0


def test_collapse_keeps_one_per_group_and_returns_corrected_total() -> None:
    rows = [
        {"entity": "AMAZON COM INC", "amount_usd": 6_000_000_000, "accession": "acc1"},
        {"entity": "AMAZON COM INC", "amount_usd": 6_000_000_000, "accession": "acc1"},  # dup
        {"entity": "FORD MOTOR CO", "amount_usd": 4_000_000_000, "accession": "acc2"},
        {"entity": "FORD MOTOR CO", "amount_usd": 4_000_000_000, "accession": "acc2"},  # dup
        {"entity": "FORD MOTOR CO", "amount_usd": 4_000_000_000, "accession": "acc2"},  # dup
        {"entity": "ACME", "amount_usd": 1_000_000_000, "accession": "acc3"},  # unique, kept
    ]
    out = collapse_within_filing(rows)
    # raw = 6+6 (Amazon) + 4+4+4 (Ford) + 1 (Acme) = 25B; corrected keeps one each = 6+4+1 = 11B
    assert out["raw_total_usd"] == 25_000_000_000
    assert out["collapsed_total_usd"] == 11_000_000_000
    assert out["removed_excess_usd"] == 14_000_000_000
    assert len(out["kept_rows"]) == 3


def test_collapse_no_duplicates_is_identity() -> None:
    rows = [
        {"entity": "A", "amount_usd": 1_000_000_000, "accession": "x"},
        {"entity": "B", "amount_usd": 2_000_000_000, "accession": "y"},
    ]
    out = collapse_within_filing(rows)
    assert out["collapsed_total_usd"] == 3_000_000_000
    assert out["removed_excess_usd"] == 0
    assert len(out["kept_rows"]) == 2


def test_accession_parsed_from_sec_uri() -> None:
    uri = "https://www.sec.gov/Archives/edgar/data/1018724/000110465926027729/foo.htm"
    assert accession_from_uri(uri) == "000110465926027729"
    assert accession_from_uri("") == ""
    assert accession_from_uri("https://example.com/no-accession") == ""
