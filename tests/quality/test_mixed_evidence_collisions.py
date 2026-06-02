from __future__ import annotations

from bubble.quality.mixed_evidence_collisions import summarize_mixed_evidence_collisions


def _row(
    packet_id: str,
    *,
    entity: str,
    usd: float,
    content_hash: str,
    metric_quote: str,
    evidence_quote: str,
    linkage: str = "not_established",
) -> dict[str, str]:
    return {
        "packet_id": packet_id,
        "rank": "1",
        "entity": entity,
        "counterparty": "",
        "subcategory": "high_notional_debt_like_candidate",
        "metric_use_status": "approved_for_metric_use",
        "supported_amount_usd": str(usd),
        "metric_group_id": packet_id,
        "metric_aggregation_policy": "max_amount_per_source_instrument",
        "metric_snapshot_date": "",
        "content_hash": content_hash,
        "content_hashes": f'["{content_hash}"]',
        "evidence_quote": evidence_quote,
        "metric_dedupe_quote": metric_quote,
        "source_uri": f"https://www.sec.gov/{packet_id}.htm",
        "ai_data_center_linkage": linkage,
    }


def test_mixed_evidence_checker_flags_aggregate_component_candidate() -> None:
    metric_quote = (
        "Hilton Worldwide Holdings entered into a credit agreement describing the same "
        "aggregate financing package and its component facilities in the filed agreement."
    )
    rows = [
        _row(
            "hilton-total",
            entity="Hilton Worldwide Holdings Inc.",
            usd=8_850_000_000,
            content_hash="a" * 64,
            metric_quote=metric_quote,
            evidence_quote=(
                "The credit agreement provides aggregate commitments of approximately "
                "$8.85 billion across term loan and revolving credit facilities."
            ),
        ),
        _row(
            "hilton-term",
            entity="Hilton Worldwide Holdings Inc.",
            usd=7_600_000_000,
            content_hash="a" * 64,
            metric_quote=metric_quote,
            evidence_quote=(
                "The term loan component of the same credit agreement provides "
                "$7.60 billion of term loan commitments."
            ),
        ),
        _row(
            "hilton-revolver",
            entity="Hilton Worldwide Holdings Inc.",
            usd=1_000_000_000,
            content_hash="a" * 64,
            metric_quote=metric_quote,
            evidence_quote=(
                "The revolving credit component of the same credit agreement provides "
                "$1.00 billion of revolving commitments."
            ),
        ),
    ]

    summary = summarize_mixed_evidence_collisions(rows)

    assert summary["candidate_group_count"] == 1
    assert summary["aggregate_component_candidate_count"] == 1
    assert summary["aggregate_candidate_excess_usd"] == 8_600_000_000
    assert summary["candidates"][0]["classification"] == "aggregate_component_candidate"
    assert summary["candidates"][0]["packet_ids"] == "hilton-revolver;hilton-term;hilton-total"


def test_mixed_evidence_checker_keeps_distinct_facility_candidate() -> None:
    metric_quote = (
        "Applied Digital disclosed separate financing facilities from the same filed "
        "source document with different evidence quotes and different committed amounts."
    )
    rows = [
        _row(
            "apld-large",
            entity="Applied Digital Corp.",
            usd=4_300_000_000,
            content_hash="b" * 64,
            metric_quote=metric_quote,
            evidence_quote=(
                "Applied Digital entered into a $4.30 billion financing facility for "
                "one high-performance computing data-center development."
            ),
            linkage="direct",
        ),
        _row(
            "apld-small",
            entity="Applied Digital Corp.",
            usd=2_150_000_000,
            content_hash="b" * 64,
            metric_quote=metric_quote,
            evidence_quote=(
                "Applied Digital separately disclosed a $2.15 billion financing facility "
                "for another high-performance computing data-center project."
            ),
            linkage="direct",
        ),
    ]

    summary = summarize_mixed_evidence_collisions(rows)

    assert summary["candidate_group_count"] == 1
    assert summary["aggregate_component_candidate_count"] == 0
    assert summary["distinct_facility_candidate_count"] == 1
    assert summary["ai_linked_candidate_count"] == 1
    assert summary["ai_linked_aggregate_candidate_count"] == 0
    assert summary["candidates"][0]["classification"] == "distinct_facility_candidate"


def test_mixed_evidence_checker_ignores_identical_evidence_quotes() -> None:
    metric_quote = (
        "Example Issuer described the same financing obligation in a filed agreement "
        "with one selected metric quote for final metric dedupe."
    )
    evidence_quote = (
        "Example Issuer entered into a $3.0 billion senior unsecured credit facility "
        "with the same lenders and same maturity date."
    )
    rows = [
        _row(
            "same-a",
            entity="Example Issuer",
            usd=3_000_000_000,
            content_hash="c" * 64,
            metric_quote=metric_quote,
            evidence_quote=evidence_quote,
        ),
        _row(
            "same-b",
            entity="Example Issuer",
            usd=1_000_000_000,
            content_hash="c" * 64,
            metric_quote=metric_quote,
            evidence_quote=evidence_quote,
        ),
    ]

    summary = summarize_mixed_evidence_collisions(rows)

    assert summary["candidate_group_count"] == 0


def test_mixed_evidence_checker_ignores_short_metric_quotes() -> None:
    rows = [
        _row(
            "short-a",
            entity="Example Issuer",
            usd=2_000_000_000,
            content_hash="d" * 64,
            metric_quote="short quote",
            evidence_quote=(
                "Example Issuer entered into a $2.0 billion senior unsecured credit "
                "facility with documented terms and lender commitments."
            ),
        ),
        _row(
            "short-b",
            entity="Example Issuer",
            usd=1_000_000_000,
            content_hash="d" * 64,
            metric_quote="short quote",
            evidence_quote=(
                "Example Issuer entered into a separate $1.0 billion senior unsecured "
                "credit facility with documented terms and lender commitments."
            ),
        ),
    ]

    summary = summarize_mixed_evidence_collisions(rows)

    assert summary["candidate_group_count"] == 0
