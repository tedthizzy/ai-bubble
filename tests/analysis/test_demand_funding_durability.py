"""Demand-funding durability decomposition."""

from __future__ import annotations

from bubble.analysis.demand_funding_durability import assess_demand_funding_durability


def _commit(offtaker, amount):
    return {"offtaker": offtaker, "counterparty": "CoreWeave", "amount_usd": amount}


PROFILE = {
    "OpenAI": {
        "funding_class": "capital_markets_dependent",
        "basis": "loss-making",
        "evidence_source_uri": "x",
    },
    "Meta": {
        "funding_class": "self_funding",
        "basis": "hyperscaler FCF",
        "evidence_source_uri": "y",
    },
    "Microsoft": {
        "funding_class": "self_funding",
        "basis": "hyperscaler FCF",
        "evidence_source_uri": "z",
    },
}


def test_blocks_empty() -> None:
    assert assess_demand_funding_durability([], PROFILE)["status"] == "blocked_no_commitments"


def test_decomposes_named_backlog_by_funding_class() -> None:
    commits = [_commit("OpenAI", 18_400_000_000), _commit("Meta", 14_200_000_000)]
    out = assess_demand_funding_durability(commits, PROFILE)
    assert out["status"] == "source_backed"
    assert out["total_named_commitment_usd"] == 32_600_000_000
    assert out["capital_markets_dependent_usd"] == 18_400_000_000
    # 18.4 / 32.6 = 56.4%
    assert 56.0 <= out["capital_markets_dependent_pct"] <= 57.0
    assert out["self_funding_usd"] == 14_200_000_000


def test_unknown_offtaker_is_segregated() -> None:
    commits = [_commit("OpenAI", 18_400_000_000), _commit("MysteryCo", 5_000_000_000)]
    out = assess_demand_funding_durability(commits, PROFILE)
    assert out["unknown_class_usd"] == 5_000_000_000
    # capital-markets-dependent pct is computed over the CLASSIFIED total only
    by = {o["offtaker"]: o for o in out["per_offtaker"]}
    assert by["MysteryCo"]["funding_class"] == "unknown"


def test_majority_flag_when_over_half_fragile() -> None:
    commits = [_commit("OpenAI", 18_400_000_000), _commit("Meta", 14_200_000_000)]
    out = assess_demand_funding_durability(commits, PROFILE)
    assert out["majority_of_named_backlog_capital_markets_dependent"] is True
