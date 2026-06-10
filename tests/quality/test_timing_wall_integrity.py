"""Timing-wall contamination fixtures (root cause 1+2 in the timing dimension).

Fixtures mirror the real live capital timing signals: PennyMac/Blackstone
asset/capacity figures contaminate the whole-corpus wall, while the AI-infra
subset (NVIDIA chip supply etc.) is clean.
"""

from __future__ import annotations

from bubble.quality.timing_wall_integrity import (
    simulate_timing_wall_fix,
    summarize_timing_wall_integrity,
)


def _sig(entity: str, amount: float, **over: str) -> dict[str, str]:
    base = {
        "category": "capital",
        "entity": entity,
        "amount_usd": str(amount),
        "ecosystem_relevance": "not_tagged",
        "relevance_tags": "",
        "description": "",
        "evidence_quote": "",
        "signal_type": "",
    }
    base.update(over)
    return base


def test_summary_separates_contaminated_wall_from_clean_ai_subset() -> None:
    rows = [
        # RC1: a >$50B asset/capacity figure (PennyMac financing capacity).
        _sig("PennyMac Financial", 471e9, description="Financing capacity across multiple banks"),
        # RC2: same figure re-disclosed across two filings -> excess once.
        _sig("PennyMac Financial", 471e9, description="EX-99.2 1Q26 earnings report"),
        # A clean AI-infra capital signal (negative control) -> in the AI subset.
        _sig(
            "CoreWeave",
            8e9,
            ecosystem_relevance="direct",
            relevance_tags="ai,data_center",
            description="senior secured notes due 2030",
        ),
        # A non-capital signal is ignored.
        _sig("Meta", 2e9, category="compute"),
    ]

    s = summarize_timing_wall_integrity(rows, mega_threshold=50e9)

    assert s["capital_signals"] == 3  # the compute signal excluded
    assert s["capital_wall_usd"] == 471e9 + 471e9 + 8e9
    assert s["mega_count"] == 2  # the two $471B PennyMac signals
    assert s["mega_gross_usd"] == 942e9
    assert s["asset_marker_count"] == 2  # "financing capacity" + "earnings report"
    assert s["crossfiling_excess_usd"] == 471e9  # PennyMac $471B x2 -> one excess
    # The AI-infra subset is clean: only the CoreWeave $8B, no mega.
    assert s["ai_infra_wall_usd"] == 8e9
    assert s["ai_infra_mega_count"] == 0


def test_clean_ai_capital_wall_has_no_contamination() -> None:
    rows = [
        _sig("CoreWeave", 8e9, ecosystem_relevance="direct", relevance_tags="ai"),
        _sig("Crusoe", 3e9, ecosystem_relevance="watchlist", relevance_tags="data_center"),
    ]

    s = summarize_timing_wall_integrity(rows, mega_threshold=50e9)

    assert s["mega_count"] == 0
    assert s["asset_marker_count"] == 0
    assert s["crossfiling_excess_usd"] == 0
    assert s["ai_infra_wall_usd"] == 11e9
    assert s["capital_wall_usd"] == 11e9


def test_simulate_timing_wall_fix_applies_mega_guard_then_dedup() -> None:
    rows = [
        # mega asset/capacity -> dropped by the guard.
        _sig("PennyMac Financial", 471e9, quarter="2026-Q1"),
        _sig("PennyMac Financial", 471e9, quarter="2026-Q2"),
        # same obligation re-disclosed in two periods -> collapses to one.
        _sig("Equinix", 19.5e9, quarter="2026-Q1"),
        _sig("Equinix", 19.5e9, quarter="2026-Q1"),
        # a clean distinct AI obligation.
        _sig(
            "CoreWeave", 8e9, quarter="2026-Q3", ecosystem_relevance="direct", relevance_tags="ai"
        ),
    ]

    s = simulate_timing_wall_fix(rows, mega_threshold=50e9)

    assert s["raw_capital_wall_usd"] == 471e9 * 2 + 19.5e9 * 2 + 8e9
    # both PennyMac $471B mega signals removed.
    assert s["mega_removed_usd"] == 942e9
    assert s["after_mega_guard_usd"] == 19.5e9 * 2 + 8e9
    # Equinix $19.5B x2 same period collapses -> one.
    assert s["dedup_removed_usd"] == 19.5e9
    assert s["corrected_capital_wall_usd"] == 19.5e9 + 8e9
    assert s["ai_infra_wall_usd"] == 8e9


def test_simulate_reports_top_collapsed_clusters() -> None:
    rows = [
        _sig("Equinix", 19.5e9, quarter="2025-Q4"),
        _sig("Equinix", 19.5e9, quarter="2025-Q4"),
        _sig("Equinix", 19.5e9, quarter="2025-Q4"),
        _sig("CoreWeave", 8e9, quarter="2026-Q1"),
    ]
    s = simulate_timing_wall_fix(rows, mega_threshold=50e9)
    assert s["top_collapsed"][0]["entity"] == "Equinix"
    assert s["top_collapsed"][0]["signals"] == 3
    assert s["top_collapsed"][0]["amount_usd"] == 19.5e9
