"""Graph notional-dedup fixtures (graph validity / size).

A capital/contract graph repeats each obligation's notional across many edges (a deal's
tranche appears on obligor, collateral, risk-bearer, and flag edges). Summing the
`notional_usd` column therefore massively over-counts. The dedup collapses to one notional
per distinct obligation (deal+tranche) so a real exposure figure can be read.
"""

from __future__ import annotations

from bubble.quality.graph_notional_dedup import summarize_graph_notional


def _edge(rel: str, deal: str, tranche: str, usd: float) -> dict[str, str]:
    return {
        "relationship_type": rel,
        "deal_id": deal,
        "tranche_id": tranche,
        "notional_usd": str(usd),
    }


def test_dedup_collapses_repeated_obligation_notional() -> None:
    edges = [
        # one $10B tranche repeated across 3 edge types -> counted once
        _edge("OBLIGATED_UNDER_DEAL", "D1", "T1", 10e9),
        _edge("SECURED_BY_COLLATERAL", "D1", "T1", 10e9),
        _edge("DEAL_RISK_BEARER", "D1", "T1", 10e9),
        # a distinct $4B tranche of the same deal -> counted once more
        _edge("OBLIGATED_UNDER_DEAL", "D1", "T2", 4e9),
        # a different deal's $6B tranche
        _edge("OBLIGATED_UNDER_DEAL", "D2", "T1", 6e9),
    ]

    s = summarize_graph_notional(edges)

    assert round(s["raw_notional_usd"]) == 40_000_000_000  # naive sum over 5 edges
    assert round(s["deduped_notional_usd"]) == 20_000_000_000  # 10 + 4 + 6 distinct tranches
    assert round(s["inflation_factor"], 2) == 2.0
    assert s["edges"] == 5
    assert s["distinct_obligations"] == 3


def test_per_relationship_breakdown_and_zero_safe() -> None:
    edges = [
        _edge("SECURED_BY_COLLATERAL", "D1", "T1", 10e9),
        _edge("SECURED_BY_COLLATERAL", "D1", "T1", 10e9),  # repeat -> dedups
    ]
    s = summarize_graph_notional(edges)
    assert round(s["deduped_notional_usd"]) == 10_000_000_000
    assert s["by_relationship"]["SECURED_BY_COLLATERAL"]["edges"] == 2
    assert round(s["by_relationship"]["SECURED_BY_COLLATERAL"]["deduped_notional_usd"]) == 10_000_000_000
    # empty input is safe
    empty = summarize_graph_notional([])
    assert empty["raw_notional_usd"] == 0
    assert empty["inflation_factor"] == 1.0
