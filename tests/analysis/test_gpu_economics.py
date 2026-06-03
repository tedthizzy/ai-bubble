"""GPU depreciation-gap summary."""

from __future__ import annotations

from bubble.analysis.gpu_economics import summarize_gpu_depreciation_gap


def _gpu(name, rental_decline, *, secondary=None, book_anchor=False):
    obs = []
    if book_anchor:
        obs.append(
            {
                "metric": "depreciation_policy_book_life",
                "value": "Amazon revised useful life 6yr -> 5yr eff Jan 1 2025",
                "source_tier": "sec_filing",
            }
        )
    return {
        "gpu": name,
        "rental_rate_decline_pct": rental_decline,
        "secondary_price_depreciation_pct": secondary,
        "observations": obs,
    }


def test_blocks_without_evidence() -> None:
    assert summarize_gpu_depreciation_gap([])["status"].startswith("blocked")


def test_source_backed_gap_with_amazon_anchor() -> None:
    ev = [
        _gpu("NVIDIA H100 (SXM)", 75, secondary=35, book_anchor=True),
        _gpu("NVIDIA A100", 61, secondary=None),
        _gpu("NVIDIA H800", 70, secondary=83),
        _gpu("NVIDIA B200 / GB200", -15.6),  # appreciating, excluded from compression
    ]
    out = summarize_gpu_depreciation_gap(ev)

    assert out["status"] == "source_backed"
    assert out["deployed_gen_median_rental_yield_decline_pct"] == 70.0  # median of [75,61,70]
    assert "B200 / GB200" in out["appreciating_generations"] or "B200" in str(
        out["appreciating_generations"]
    )
    assert "amazon" in out["book_life_primary_anchor"].lower()
    assert out["book_life_years_range"] == [5, 7]
    assert "RENTAL" in out["gap_summary"] or "rental" in out["gap_summary"]
    # Honest counter-signals are surfaced, not buried.
    assert any("appreciating" in c.lower() for c in out["counter_signals"])


def test_blocks_when_only_appreciating() -> None:
    out = summarize_gpu_depreciation_gap([_gpu("NVIDIA B200", -15.6)])
    assert out["status"] == "blocked_no_rental_compression_signal"
