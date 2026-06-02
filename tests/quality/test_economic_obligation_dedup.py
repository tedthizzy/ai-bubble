"""Economic-obligation dedup fixtures (root cause 2).

Positive fixtures mirror the verified cross-filing clusters (same obligation across
filings must collapse to one); negative controls are genuinely distinct obligations
that must stay separate.
"""

from __future__ import annotations

from bubble.quality.economic_obligation_dedup import (
    economic_obligation_key,
    summarize_economic_dedup,
)


def _si(content_hash: str, entity: str, amount: float, **over: str) -> dict[str, str]:
    base = {
        "metric_use_status": "approved_for_metric_use",
        "metric_group_id": f"source-instrument:hashes:{content_hash}:amount:{int(amount)}",
        "supported_amount_usd": str(amount),
        "entity": entity,
        "content_hash": content_hash,
    }
    base.update(over)
    return base


def test_same_obligation_across_filings_shares_one_key() -> None:
    # TeraWulf $3.2B note in two filings (different content_hash) -> same economic key.
    a = _si("hash-aaa", "TeraWulf Inc.", 3.2e9)
    b = _si("hash-bbb", "TeraWulf Inc.", 3.2e9)
    assert economic_obligation_key(a) == economic_obligation_key(b)


def test_distinct_amounts_get_distinct_keys() -> None:
    a = _si("h1", "TeraWulf Inc.", 3.2e9)
    b = _si("h2", "TeraWulf Inc.", 1.3e9)
    assert economic_obligation_key(a) != economic_obligation_key(b)


def test_discriminators_split_same_amount_distinct_obligations() -> None:
    # Same entity + amount but different maturity/counterparty -> NOT merged (negative control).
    a = _si("h1", "MegaCorp", 5e9, metric_snapshot_date="2029-09", counterparty="JPMorgan")
    b = _si("h2", "MegaCorp", 5e9, metric_snapshot_date="2031-05", counterparty="Citibank")
    assert economic_obligation_key(a, use_discriminators=True) != economic_obligation_key(
        b, use_discriminators=True
    )


def test_summary_simulates_the_rc2_fix() -> None:
    rows = [
        # TeraWulf $3.2B across 3 filings -> collapses to 1 (excess $6.4B).
        _si("h-a", "TeraWulf Inc.", 3.2e9),
        _si("h-b", "TeraWulf Inc.", 3.2e9),
        _si("h-c", "TeraWulf Inc.", 3.2e9),
        # Equinix $19.5B across 2 filings -> collapses to 1 (excess $19.5B).
        _si("h-d", "Equinix Inc.", 19.5e9),
        _si("h-e", "Equinix Inc.", 19.5e9),
        # A distinct standalone obligation -> stays.
        _si("h-f", "CoreWeave", 8e9),
    ]

    s = summarize_economic_dedup(rows, use_discriminators=False)

    assert s["source_instrument_groups"] == 6
    assert s["economic_obligations"] == 3  # TeraWulf, Equinix, CoreWeave
    assert s["raw_sum_usd"] == 3.2e9 * 3 + 19.5e9 * 2 + 8e9
    assert s["deduped_sum_usd"] == 3.2e9 + 19.5e9 + 8e9
    assert s["dedup_excess_usd"] == 3.2e9 * 2 + 19.5e9  # 6.4B + 19.5B
    assert s["top_collapsed"][0]["filings"] == 2  # Equinix has the largest excess
