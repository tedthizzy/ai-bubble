from __future__ import annotations

from bubble.quality.relevance_linkage import (
    _collapse_economic_event_representatives,
    final_metric_representative_rows,
    summarize_relevance_linkage,
)


def _row(
    packet_id: str,
    *,
    entity: str,
    linkage: str,
    usd: float,
    group: str | None = None,
    policy: str = "max_amount_per_source_instrument",
    content_hash: str = "",
    quote: str = "",
    snapshot: str = "",
    rank: int = 1,
    counterparty: str = "",
    subcategory: str = "capital_exposure",
    source_uri: str = "",
    metric_dedupe_quote: str = "",
) -> dict[str, str]:
    return {
        "packet_id": packet_id,
        "rank": str(rank),
        "entity": entity,
        "counterparty": counterparty,
        "subcategory": subcategory,
        "metric_use_status": "approved_for_metric_use",
        "supported_amount_usd": str(usd),
        "metric_group_id": group or packet_id,
        "metric_aggregation_policy": policy,
        "metric_snapshot_date": snapshot,
        "content_hash": content_hash,
        "content_hashes": f'["{content_hash}"]' if content_hash else "[]",
        "evidence_quote": quote,
        "metric_dedupe_quote": metric_dedupe_quote,
        "source_uri": source_uri,
        "ai_data_center_linkage": linkage,
    }


def test_relevance_summary_splits_final_metric_representatives() -> None:
    rows = [
        _row("direct", entity="CoreWeave", linkage="direct", usd=30e9, content_hash="a" * 64),
        _row("watch", entity="Oracle", linkage="watchlist", usd=10e9, content_hash="b" * 64),
        _row(
            "off",
            entity="Navient",
            linkage="not_established",
            usd=300e9,
            content_hash="c" * 64,
        ),
    ]

    summary = summarize_relevance_linkage(rows)

    assert summary["final_metric_group_count"] == 3
    assert summary["total_usd"] == 340_000_000_000
    assert summary["direct_usd"] == 30_000_000_000
    assert summary["watchlist_usd"] == 10_000_000_000
    assert summary["established_usd"] == 40_000_000_000
    assert summary["not_established_usd"] == 300_000_000_000
    assert summary["top_not_established"][0] == {
        "entity": "Navient",
        "usd": 300_000_000_000,
    }


def test_relevance_summary_uses_same_representative_collapse_as_final_metric() -> None:
    long_quote = (
        "The issuer entered into a senior notes obligation with a stated principal amount "
        "and repayment terms under the indenture for the same financing transaction."
    )
    rows = [
        _row(
            "same-group-low",
            entity="CoreWeave",
            linkage="direct",
            usd=20e9,
            group="group-coreweave",
            content_hash="d" * 64,
        ),
        _row(
            "same-group-high",
            entity="CoreWeave",
            linkage="direct",
            usd=30e9,
            group="group-coreweave",
            content_hash="e" * 64,
        ),
        _row(
            "same-source-a",
            entity="Oracle",
            linkage="watchlist",
            usd=10e9,
            group="oracle-a",
            content_hash="f" * 64,
        ),
        _row(
            "same-source-b",
            entity="Oracle",
            linkage="watchlist",
            usd=10e9,
            group="oracle-b",
            content_hash="f" * 64,
        ),
        _row(
            "same-obligation-a",
            entity="Navient",
            linkage="not_established",
            usd=300e9,
            group="navient-a",
            quote=long_quote,
            counterparty="Trustee",
            subcategory="high_notional_debt_like_candidate",
        ),
        _row(
            "same-obligation-b",
            entity="Navient",
            linkage="not_established",
            usd=300e9,
            group="navient-b",
            quote=long_quote,
            counterparty="Trustee",
            subcategory="high_notional_debt_like_candidate",
        ),
        _row(
            "snapshot-old",
            entity="LeaseCo",
            linkage="not_established",
            usd=70e9,
            group="lease-snapshot",
            policy="latest_snapshot_per_metric_group",
            snapshot="2024-12-31",
            content_hash="g" * 64,
        ),
        _row(
            "snapshot-new",
            entity="LeaseCo",
            linkage="not_established",
            usd=75e9,
            group="lease-snapshot",
            policy="latest_snapshot_per_metric_group",
            snapshot="2025-12-31",
            content_hash="h" * 64,
        ),
    ]

    representatives = final_metric_representative_rows(rows)
    summary = summarize_relevance_linkage(rows)

    assert {row["packet_id"] for row in representatives} == {
        "same-group-high",
        "same-source-a",
        "same-obligation-a",
        "snapshot-new",
    }
    assert summary["final_metric_group_count"] == 4
    assert summary["total_usd"] == 415_000_000_000
    assert summary["direct_usd"] == 30_000_000_000
    assert summary["watchlist_usd"] == 10_000_000_000
    assert summary["not_established_usd"] == 375_000_000_000


def test_blank_or_unknown_linkage_counts_as_not_established() -> None:
    rows = [
        _row("direct", entity="Tagged", linkage="direct", usd=10e9, content_hash="i" * 64),
        _row("blank", entity="Blank", linkage="", usd=5e9, content_hash="j" * 64),
        _row(
            "not-tagged",
            entity="NotTagged",
            linkage="not_tagged",
            usd=7e9,
            content_hash="k" * 64,
        ),
    ]

    summary = summarize_relevance_linkage(rows)

    assert summary["direct_usd"] == 10_000_000_000
    assert summary["not_established_usd"] == 12_000_000_000


def test_relevance_summary_collapses_same_accession_same_amount_rows() -> None:
    accession_uri = "https://www.sec.gov/Archives/edgar/data/1/000000000125000001/doc.htm"
    rows = [
        _row(
            "accession-a",
            entity="CoreWeave",
            linkage="direct",
            usd=40e9,
            group="coreweave-a",
            content_hash="l" * 64,
            source_uri=accession_uri,
        ),
        _row(
            "accession-b",
            entity="CoreWeave",
            linkage="direct",
            usd=40e9,
            group="coreweave-b",
            content_hash="m" * 64,
            source_uri=accession_uri,
        ),
    ]

    summary = summarize_relevance_linkage(rows)

    assert summary["final_metric_group_count"] == 1
    assert summary["direct_usd"] == 40_000_000_000
    assert summary["total_usd"] == 40_000_000_000


def test_relevance_summary_collapses_same_content_hash_and_quote_collision() -> None:
    quote = (
        "Example Issuer announced the final results of its exchange offer for senior secured "
        "notes and described the same instrument, trustee, indenture, guarantees, and principal "
        "amount in each extracted packet from the same source document."
    )
    rows = [
        _row(
            "collision-high",
            entity="Example Issuer",
            linkage="not_established",
            usd=8e9,
            group="collision-high",
            content_hash="n" * 64,
            quote=quote,
            metric_dedupe_quote=quote,
        ),
        _row(
            "collision-low",
            entity="Example Issuer",
            linkage="not_established",
            usd=3e9,
            group="collision-low",
            content_hash="n" * 64,
            quote=quote,
            metric_dedupe_quote=quote,
        ),
    ]

    representatives = final_metric_representative_rows(rows)
    summary = summarize_relevance_linkage(rows)

    assert {row["packet_id"] for row in representatives} == {"collision-high"}
    assert summary["final_metric_group_count"] == 1
    assert summary["total_usd"] == 8_000_000_000


def _econ_uri(accession: str) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/1/{accession}/doc.htm"


def test_relevance_summary_collapses_economic_event_repeats() -> None:
    # Same TeraWulf 7.750%/2030 notes counted across two filings: the partition
    # must apply the economic-event collapse so the direct bucket is not inflated.
    rows = [
        _row(
            "wulf-a",
            entity="TERAWULF INC.",
            linkage="direct",
            usd=3.2e9,
            group="wulf-a",
            content_hash="o" * 64,
            quote="TeraWulf priced 7.750% senior secured notes due 2030.",
            source_uri=_econ_uri("000110465925100142"),
        ),
        _row(
            "wulf-b",
            entity="TERAWULF INC.",
            linkage="direct",
            usd=3.2e9,
            group="wulf-b",
            content_hash="p" * 64,
            quote="Indenture for the 7.750% senior secured notes due 2030.",
            source_uri=_econ_uri("000110465925101866"),
        ),
    ]

    summary = summarize_relevance_linkage(rows)

    assert summary["final_metric_group_count"] == 1
    assert summary["direct_usd"] == 3_200_000_000
    assert summary["total_usd"] == 3_200_000_000


def test_economic_event_collapse_preserves_distinct_facility_negative_control() -> None:
    # IREN $1B convertibles with conflicting maturity years AND coupons are
    # distinct facilities; tested on the collapse layer in isolation so the
    # upstream economic-obligation layer does not mask the behavior.
    rows = [
        _row(
            "iren-2031",
            entity="IREN LIMITED",
            linkage="direct",
            usd=1e9,
            content_hash="q" * 64,
            quote="0.25% convertible senior notes due 2031.",
            source_uri=_econ_uri("000114036125037488"),
        ),
        _row(
            "iren-2033",
            entity="IREN LIMITED",
            linkage="direct",
            usd=1e9,
            content_hash="r" * 64,
            quote="1.00% convertible senior notes due 2033.",
            source_uri=_econ_uri("000114036125043803"),
        ),
    ]

    collapsed = _collapse_economic_event_representatives(rows)

    assert len(collapsed) == 2


def test_economic_event_collapse_leaves_out_of_scope_issuer_repeats() -> None:
    # Out-of-scope issuer (not in the curated direct-tier alias map) is never
    # touched by the economic-event collapse, even with a same-instrument signal.
    rows = [
        _row(
            "eaton-a",
            entity="EATON CORP PLC",
            linkage="not_established",
            usd=3.2e9,
            content_hash="s" * 64,
            quote="7.750% senior notes due 2030.",
            source_uri=_econ_uri("000110465925100142"),
        ),
        _row(
            "eaton-b",
            entity="EATON CORP PLC",
            linkage="not_established",
            usd=3.2e9,
            content_hash="t" * 64,
            quote="Indenture for the 7.750% senior notes due 2030.",
            source_uri=_econ_uri("000110465925101866"),
        ),
    ]

    collapsed = _collapse_economic_event_representatives(rows)

    assert len(collapsed) == 2


def test_economic_event_collapse_merges_same_instrument_across_filings() -> None:
    # Same TeraWulf 7.750%/2030 notes across two filings collapse to one,
    # even though the counterparty descriptor differs between the filings.
    rows = [
        _row(
            "wulf-press",
            entity="TERAWULF INC.",
            linkage="direct",
            usd=3.2e9,
            content_hash="u" * 64,
            counterparty="Morgan Stanley Senior Funding, Inc.",
            quote="TeraWulf priced 7.750% senior secured notes due 2030.",
            source_uri=_econ_uri("000110465925100142"),
        ),
        _row(
            "wulf-indenture",
            entity="TERAWULF INC.",
            linkage="direct",
            usd=3.2e9,
            content_hash="v" * 64,
            counterparty="WILMINGTON TRUST, NATIONAL ASSOCIATION",
            quote="Indenture for the 7.750% senior secured notes due 2030.",
            source_uri=_econ_uri("000110465925101866"),
        ),
    ]

    collapsed = _collapse_economic_event_representatives(rows)

    assert len(collapsed) == 1


def test_relevance_summary_keeps_same_content_hash_quote_with_distinct_evidence() -> None:
    metric_quote = (
        "Example Borrower entered into a credit agreement with lenders, issuing banks, and the "
        "administrative agent to finance the acquisition and related corporate transactions."
    )
    term_loan_quote = (
        "The borrower requested term loan commitments in an aggregate principal amount of "
        "$8.0 billion under the credit agreement for the acquisition financing."
    )
    revolver_quote = (
        "The borrower also requested revolving commitments in an aggregate principal amount of "
        "$3.0 billion under the same credit agreement for working capital and letters of credit."
    )
    rows = [
        _row(
            "term-loan",
            entity="Example Borrower",
            linkage="not_established",
            usd=8e9,
            group="term-loan",
            content_hash="o" * 64,
            quote=term_loan_quote,
            metric_dedupe_quote=metric_quote,
        ),
        _row(
            "revolver",
            entity="Example Borrower",
            linkage="not_established",
            usd=3e9,
            group="revolver",
            content_hash="o" * 64,
            quote=revolver_quote,
            metric_dedupe_quote=metric_quote,
        ),
    ]

    representatives = final_metric_representative_rows(rows)
    summary = summarize_relevance_linkage(rows)

    assert {row["packet_id"] for row in representatives} == {"term-loan", "revolver"}
    assert summary["final_metric_group_count"] == 2
    assert summary["total_usd"] == 11_000_000_000


def test_relevance_summary_collapses_cross_filing_exact_quote_amount_repeats() -> None:
    quote = (
        "The borrower entered into a term loan credit agreement with Goldman Sachs Bank USA, "
        "as administrative agent, providing an $8.0 billion senior unsecured term loan facility "
        "in connection with the issuer solutions transaction."
    )
    rows = [
        _row(
            "exact-cross-a",
            entity="Example Payments Corp.",
            linkage="not_established",
            usd=8e9,
            group="exact-cross-a",
            content_hash="p" * 64,
            source_uri="https://www.sec.gov/Archives/edgar/data/1/000119312526096739/a.htm",
            quote=quote,
        ),
        _row(
            "exact-cross-b",
            entity="Example Payments Corp.",
            linkage="not_established",
            usd=8e9,
            group="exact-cross-b",
            content_hash="q" * 64,
            source_uri="https://www.sec.gov/Archives/edgar/data/1/000119312526073639/b.htm",
            quote=quote,
        ),
    ]

    representatives = final_metric_representative_rows(rows)
    summary = summarize_relevance_linkage(rows)

    assert {row["packet_id"] for row in representatives} == {"exact-cross-a"}
    assert summary["final_metric_group_count"] == 1
    assert summary["total_usd"] == 8_000_000_000


def test_relevance_summary_keeps_exact_quote_repeats_with_different_amount_or_entity() -> None:
    quote = (
        "The borrower entered into a credit agreement with lenders and administrative agent "
        "for acquisition financing under the same generic transaction description."
    )
    rows = [
        _row(
            "different-amount-a",
            entity="Example Payments Corp.",
            linkage="not_established",
            usd=8e9,
            group="different-amount-a",
            content_hash="r" * 64,
            source_uri="https://www.sec.gov/Archives/edgar/data/1/000119312526096739/a.htm",
            quote=quote,
        ),
        _row(
            "different-amount-b",
            entity="Example Payments Corp.",
            linkage="not_established",
            usd=7e9,
            group="different-amount-b",
            content_hash="s" * 64,
            source_uri="https://www.sec.gov/Archives/edgar/data/1/000119312526073639/b.htm",
            quote=quote,
        ),
        _row(
            "different-entity-a",
            entity="First Boilerplate Corp.",
            linkage="not_established",
            usd=5e9,
            group="different-entity-a",
            content_hash="t" * 64,
            source_uri="https://www.sec.gov/Archives/edgar/data/1/000119312526000001/c.htm",
            quote=quote,
        ),
        _row(
            "different-entity-b",
            entity="Second Boilerplate Corp.",
            linkage="not_established",
            usd=5e9,
            group="different-entity-b",
            content_hash="u" * 64,
            source_uri="https://www.sec.gov/Archives/edgar/data/2/000119312526000002/d.htm",
            quote=quote,
        ),
    ]

    representatives = final_metric_representative_rows(rows)
    summary = summarize_relevance_linkage(rows)

    assert {row["packet_id"] for row in representatives} == {
        "different-amount-a",
        "different-amount-b",
        "different-entity-a",
        "different-entity-b",
    }
    assert summary["final_metric_group_count"] == 4
    assert summary["total_usd"] == 25_000_000_000


def test_relevance_summary_collapses_strict_cross_filing_instrument_fingerprints() -> None:
    quote_a = "The notes bear interest at 9.25% and are due 2030 under the indenture."
    quote_b = "Senior secured notes will bear interest at 9.25% and mature due 2030."
    rows = [
        _row(
            "cross-a",
            entity="CoreWeave Inc.",
            linkage="direct",
            usd=30e9,
            group="cross-a",
            source_uri="https://www.sec.gov/Archives/edgar/data/1/000000000125000001/a.htm",
            quote=quote_a,
        ),
        _row(
            "cross-b",
            entity="CoreWeave Funding LLC",
            linkage="direct",
            usd=30e9,
            group="cross-b",
            source_uri="https://www.sec.gov/Archives/edgar/data/1/000000000225000002/b.htm",
            quote=quote_b,
        ),
        # Non-curated issuer: the strict layer still must not collapse a no-year
        # case, and the curated-scope economic-event layer leaves it untouched.
        _row(
            "negative-no-year",
            entity="Equinix Inc.",
            linkage="direct",
            usd=31e9,
            group="negative-no-year",
            counterparty="Agent A",
            source_uri="https://www.sec.gov/Archives/edgar/data/1/000000000325000003/c.htm",
            quote="The notes bear interest at 9.25% under the indenture.",
        ),
        _row(
            "negative-other",
            entity="Equinix Inc.",
            linkage="direct",
            usd=31e9,
            group="negative-other",
            counterparty="Agent B",
            source_uri="https://www.sec.gov/Archives/edgar/data/1/000000000425000004/d.htm",
            quote="The notes bear interest at 9.25% under the indenture.",
        ),
    ]

    summary = summarize_relevance_linkage(rows)

    assert summary["final_metric_group_count"] == 3
    assert summary["direct_usd"] == 92_000_000_000
    assert summary["total_usd"] == 92_000_000_000
