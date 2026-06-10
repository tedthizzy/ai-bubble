"""Adjudicated AI-direct committed-debt aggregation."""

from __future__ import annotations

from bubble.analysis.adjudicated_committed_debt import aggregate_adjudicated_committed_debt

_PAYLOAD = {
    "status": "source_backed",
    "original_inflated_basis_usd": 1_451_900_000_000,
    "summary": {
        "row_count": 76,
        "committed_count": 39,
        "by_decision": {
            "committed_ai_debt": 19,
            "partial_committed": 20,
            "exclude_aggregate_or_capacity": 17,
        },
    },
    "adversarial_verification": {
        "refuted_count": 0,
        "by_verdict": {"confirmed": 36, "corrected": 3},
    },
    "deduped_distinct_instruments": {
        "instrument_count": 19,
        "core_cluster_committed_usd": 25_775_000_000,
        "datacenter_infra_committed_usd": 3_950_000_000,
        "questionable_linkage_committed_usd": 20_000_000_000,
        "distinct_committed_ex_questionable_usd": 29_725_000_000,
        "distinct_committed_all_usd": 49_725_000_000,
        "instruments": [
            {
                "instrument": "SpaceX bridge",
                "issuer": "SpaceX",
                "committed_usd": 20_000_000_000,
                "ai_class": "questionable_linkage",
            },
            {
                "instrument": "CoreWeave DDTL",
                "issuer": "CoreWeave",
                "committed_usd": 3_100_000_000,
                "ai_class": "core_cluster",
            },
        ],
        "caveat": "IREN residual uncertainty; SpaceX excluded from headline.",
    },
}


def test_blocks_empty() -> None:
    assert aggregate_adjudicated_committed_debt({})["status"] == "blocked_no_adjudication"


def test_aggregates_overcount_and_distinct() -> None:
    out = aggregate_adjudicated_committed_debt(_PAYLOAD)
    assert out["status"] == "source_backed"
    assert out["blocked_rows_adjudicated"] == 76
    assert out["refuted_in_adversarial_pass"] == 0
    assert out["verified_distinct_committed_core_cluster_usd"] == 25_775_000_000
    assert out["verified_distinct_committed_incl_infra_usd"] == 29_725_000_000
    # over-count removed vs the ex-questionable distinct figure
    assert out["over_count_removed_usd"] == 1_451_900_000_000 - 29_725_000_000
    assert out["over_count_removed_pct"] == 98.0


def test_top_instruments_sorted() -> None:
    out = aggregate_adjudicated_committed_debt(_PAYLOAD)
    assert out["top_instruments"][0]["issuer"] == "SpaceX"
