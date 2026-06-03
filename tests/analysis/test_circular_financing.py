"""Circular / reciprocal financing cycle detection."""

from __future__ import annotations

from bubble.analysis.circular_financing import analyze_circular_financing, find_money_cycles


def _edge(frm, to, flow, tier="filing_verified", amount=None, binding=True):
    return {
        "from": frm,
        "to": to,
        "flow_type": flow,
        "source_tier": tier,
        "amount_usd": amount,
        "binding": binding,
    }


def test_blocks_empty() -> None:
    assert analyze_circular_financing([])["status"] == "blocked_no_edges"


def test_detects_filing_verified_reciprocal_2_cycle() -> None:
    edges = [
        _edge("NVIDIA", "CoreWeave", "equity_investment", amount=2_000_000_000),
        _edge("CoreWeave", "NVIDIA", "gpu_purchase"),
    ]
    out = analyze_circular_financing(edges)
    assert out["status"] == "source_backed"
    recip = out["filing_verified_reciprocal_loops"]
    assert len(recip) == 1
    assert recip[0]["length"] == 2
    assert {"NVIDIA", "CoreWeave"} == set(recip[0]["nodes"])
    assert recip[0]["all_filing_verified"] is True


def test_press_only_edge_keeps_loop_out_of_filing_verified_bucket() -> None:
    # Macro 3-loop NVIDIA -> OpenAI -> CoreWeave -> NVIDIA, NVIDIA->OpenAI is press only.
    edges = [
        _edge("NVIDIA", "OpenAI", "framework_commitment", tier="press_reported", amount=100_000_000_000, binding=False),
        _edge("OpenAI", "CoreWeave", "purchase_commitment", amount=18_400_000_000),
        _edge("CoreWeave", "NVIDIA", "gpu_purchase"),
    ]
    out = analyze_circular_financing(edges)
    # The 3-loop exists but is NOT filing-verified (one edge press only).
    assert out["filing_verified_reciprocal_loops"] == []
    flagged = out["press_or_inferred_loops"]
    assert len(flagged) == 1
    assert flagged[0]["weakest_tier"] == "press_reported"
    assert flagged[0]["length"] == 3


def test_reciprocal_hub_counts_supplier_as_investor() -> None:
    edges = [
        _edge("NVIDIA", "CoreWeave", "equity_investment", amount=2_000_000_000),
        _edge("CoreWeave", "NVIDIA", "gpu_purchase"),
        _edge("NVIDIA", "Nebius", "equity_investment", amount=2_000_000_000),
        _edge("Nebius", "NVIDIA", "gpu_purchase"),
        _edge("NVIDIA", "Applied Digital", "equity_investment"),
        _edge("Applied Digital", "NVIDIA", "gpu_purchase", tier="inferred"),
    ]
    out = analyze_circular_financing(edges)
    hub = out["reciprocal_hub"]
    assert hub["entity"] == "NVIDIA"
    # invests in 3 of its own GPU customers
    assert hub["investee_customer_count"] == 3
    assert "CoreWeave" in hub["investees"]
    # filing-verified return leg only for CoreWeave + Nebius (Applied Digital return is inferred)
    assert hub["filing_verified_round_trip_count"] == 2
    # total filing-verified injected capital with a verified return leg = $4B
    assert hub["filing_verified_reciprocal_capital_usd"] == 4_000_000_000


def test_find_money_cycles_dedups_rotations() -> None:
    edges = [
        _edge("A", "B", "x"),
        _edge("B", "A", "y"),
    ]
    cycles = find_money_cycles(edges, max_len=4)
    assert len(cycles) == 1
    assert len(cycles[0]) == 2
