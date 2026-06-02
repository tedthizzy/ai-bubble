"""Cross-filing duplication fixtures (residual RC2 the per-hash dedup misses).

The metric dedups by ``metric_group_id`` (source-instrument hashes), so the SAME aggregate
obligation extracted from N different filings of the same issuer (each a distinct hash) is
counted N times. Signature: same issuer + identical amount across >=3 distinct groups -- a
$18.4B figure repeated across a company's Series A-E note prospectuses, not 5 distinct deals.
"""

from __future__ import annotations

from bubble.quality.cross_filing_duplication import summarize_cross_filing_duplication


def _row(entity: str, amount: float, group: str) -> dict[str, str]:
    return {
        "metric_use_status": "approved_for_metric_use",
        "metric_group_id": f"source-instrument:hashes:{group}:amount:{int(amount)}",
        "entity": entity,
        "supported_amount_usd": str(amount),
    }


def test_same_entity_amount_across_many_groups_is_flagged() -> None:
    rows = [
        # one $18.4B figure repeated across 4 distinct filings -> 3x excess
        _row("GEORGIA POWER CO", 18.4e9, "h1"),
        _row("GEORGIA POWER CO", 18.4e9, "h2"),
        _row("GEORGIA POWER CO", 18.4e9, "h3"),
        _row("GEORGIA POWER CO", 18.4e9, "h4"),
        # a genuinely distinct obligation -> not flagged
        _row("Other Co", 5e9, "h9"),
    ]

    s = summarize_cross_filing_duplication(rows, min_groups=3)

    assert s["suspect_families"] == 1
    top = s["top_suspects"][0]
    assert top["amount_usd"] == 18.4e9
    assert top["distinct_groups"] == 4
    # removable excess = amount * (groups - 1)
    assert round(s["removable_excess_usd"]) == round(18.4e9 * 3)
    # an odd-precision amount repeated 4x -> high confidence
    assert top["confidence"] == "high"


def test_two_groups_or_distinct_amounts_not_flagged() -> None:
    rows = [
        _row("Pair Co", 4e9, "h1"),
        _row("Pair Co", 4e9, "h2"),  # only 2 groups -> below min_groups=3
        _row("Distinct Co", 3e9, "h1"),
        _row("Distinct Co", 7e9, "h2"),  # different amounts -> not a duplication signal
    ]

    s = summarize_cross_filing_duplication(rows, min_groups=3)

    assert s["suspect_families"] == 0
    assert s["removable_excess_usd"] == 0.0


def test_round_amount_is_medium_confidence() -> None:
    rows = [_row("Round Co", 10e9, f"h{i}") for i in range(3)]
    s = summarize_cross_filing_duplication(rows, min_groups=3)
    assert s["top_suspects"][0]["confidence"] == "medium"  # round $10B could be distinct facilities
