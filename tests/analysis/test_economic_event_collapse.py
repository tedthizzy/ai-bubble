"""Economic-event (same-instrument) metric collapse.

One offering counted across proposed -> priced -> closed -> indenture filings
inflates the direct-tier metric: different docs/quotes make the repeats invisible
to content-hash and exact-quote dedupe. This collapse removes the conservative
``probable_same_instrument_review`` class (same curated direct-tier issuer, same
amount, a consistent single coupon/maturity-year fingerprint, multiple
accessions) while preserving distinct facilities and out-of-scope issuers.
"""

from __future__ import annotations

from bubble.analysis.materiality_adjudication_results import (
    MaterialityAdjudicationDecision,
    _collapse_economic_event_representatives,
    canonical_direct_tier_entity,
    classify_economic_event_cluster,
)


def _decision(
    *,
    packet_id: str,
    entity: str,
    amount: float,
    accession: str,
    quote: str,
) -> MaterialityAdjudicationDecision:
    return MaterialityAdjudicationDecision(
        packet_id=packet_id,
        rank=1,
        review_id="r",
        review_group_id="rg",
        priority="P1",
        category="capital",
        subcategory="senior_secured_notes",
        ecosystem_relevance="ai_data_center",
        entity=entity,
        counterparty="noteholders",
        exposure_basis_usd=amount,
        decision="supported_as_material",
        metric_use_status="approved_for_metric_use",
        source_support="source_quote_backed",
        confidence=0.9,
        supported_amount_usd=amount,
        metric_group_id="",
        metric_snapshot_date="2026-01-01",
        metric_aggregation_policy="max_amount_per_source_instrument",
        duplicate_or_aggregate="",
        ai_data_center_linkage="established_direct",
        risk_bearer=entity,
        remaining_gap="",
        required_next_extraction="",
        metric_dedupe_quote=quote,
        evidence_quote=quote,
        evidence_quote_refs=(),
        rationale="",
        adjudicator_id="auto",
        adjudicated_at="2026-01-01",
        source_uri=f"https://www.sec.gov/Archives/edgar/data/1/{accession}/doc.htm",
        source_uris=(),
        content_hash=accession,
        content_hashes=(accession,),
        packet_reason="",
    )


def _amounts(rows: list[MaterialityAdjudicationDecision]) -> float:
    return sum(row.supported_amount_usd for row in rows)


def test_canonical_direct_tier_entity_scopes_to_curated_names() -> None:
    assert canonical_direct_tier_entity("TeraWulf Inc.") == "TeraWulf"
    assert canonical_direct_tier_entity("IREN LIMITED") == "IREN"
    # Out-of-scope issuers (negative controls) are never canonicalized.
    assert canonical_direct_tier_entity("EATON CORP PLC") == ""
    assert canonical_direct_tier_entity("GEORGIA POWER CO") == ""
    assert canonical_direct_tier_entity("MARATHON PETROLEUM CORP") == ""


def test_same_instrument_across_filings_collapses_to_one_representative() -> None:
    rows = [
        _decision(
            packet_id="a",
            entity="TERAWULF INC.",
            amount=3_200_000_000,
            accession="000110465925100142",
            quote="TeraWulf priced 7.750% senior secured notes due 2030.",
        ),
        _decision(
            packet_id="b",
            entity="TERAWULF INC.",
            amount=3_200_000_000,
            accession="000110465925101866",
            quote="Indenture for the 7.750% senior secured notes due 2030.",
        ),
    ]
    assert classify_economic_event_cluster(rows) == "probable_same_instrument_review"
    collapsed = _collapse_economic_event_representatives(rows)
    assert len(collapsed) == 1
    assert _amounts(collapsed) == 3_200_000_000


def test_year_only_note_pattern_across_filings_collapses() -> None:
    # Applied Digital $2.35B repeated with only a "2030 notes" year descriptor.
    rows = [
        _decision(
            packet_id="a",
            entity="APPLIED DIGITAL CORP",
            amount=2_350_000_000,
            accession="000149315225021400",
            quote="Applied Digital announced $2.35 billion 2030 notes.",
        ),
        _decision(
            packet_id="b",
            entity="APPLIED DIGITAL CORP",
            amount=2_350_000_000,
            accession="000149315225022506",
            quote="Closing of the $2.35 billion 2030 notes offering.",
        ),
    ]
    collapsed = _collapse_economic_event_representatives(rows)
    assert len(collapsed) == 1


def test_distinct_facilities_with_conflicting_descriptors_are_preserved() -> None:
    # IREN $1.0B convertible tranches: different maturity years AND coupons.
    rows = [
        _decision(
            packet_id="a",
            entity="IREN LIMITED",
            amount=1_000_000_000,
            accession="000114036125037488",
            quote="0.25% convertible senior notes due 2031.",
        ),
        _decision(
            packet_id="b",
            entity="IREN LIMITED",
            amount=1_000_000_000,
            accession="000114036125043803",
            quote="1.00% convertible senior notes due 2033.",
        ),
    ]
    assert classify_economic_event_cluster(rows) == "distinct_facility_negative_control"
    collapsed = _collapse_economic_event_representatives(rows)
    assert len(collapsed) == 2
    assert _amounts(collapsed) == 2_000_000_000


def test_amount_only_repeats_without_descriptors_are_preserved() -> None:
    rows = [
        _decision(
            packet_id="a",
            entity="TERAWULF INC.",
            amount=1_000_000_000,
            accession="000110465925100142",
            quote="Entered into a financing arrangement.",
        ),
        _decision(
            packet_id="b",
            entity="TERAWULF INC.",
            amount=1_000_000_000,
            accession="000110465925101866",
            quote="Borrower drew on the facility.",
        ),
    ]
    assert classify_economic_event_cluster(rows) == "amount_only_review"
    collapsed = _collapse_economic_event_representatives(rows)
    assert len(collapsed) == 2


def test_out_of_scope_issuer_same_instrument_is_not_collapsed() -> None:
    # Same-instrument signal, but the issuer is outside the curated direct-tier
    # alias map -> the collapse must never touch it.
    rows = [
        _decision(
            packet_id="a",
            entity="EATON CORP PLC",
            amount=3_200_000_000,
            accession="000110465925100142",
            quote="7.750% senior notes due 2030.",
        ),
        _decision(
            packet_id="b",
            entity="EATON CORP PLC",
            amount=3_200_000_000,
            accession="000110465925101866",
            quote="Indenture for the 7.750% senior notes due 2030.",
        ),
    ]
    collapsed = _collapse_economic_event_representatives(rows)
    assert len(collapsed) == 2
    assert _amounts(collapsed) == 6_400_000_000
