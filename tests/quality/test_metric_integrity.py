"""Tests for the metric-integrity over-count checker."""

from __future__ import annotations

from bubble.quality.metric_integrity import summarize_metric_integrity


def _row(gid: str, amount: float, **over: str) -> dict[str, str]:
    base = {
        "metric_use_status": "approved_for_metric_use",
        "metric_group_id": gid,
        "supported_amount_usd": str(amount),
        "entity": "Example Corp",
        "evidence_quote": "q",
        "content_hash": "",
    }
    base.update(over)
    return base


def test_summary_quantifies_three_overcount_signals() -> None:
    rows = [
        # Root cause 1: a >$50B mega single-obligation group.
        _row("source-instrument:hashes:aaa:amount:60", 60e9, entity="PennyMac"),
        # Root cause 2a: same obligation (entity+amount+quote) across two filings -> excess once.
        _row("source-instrument:hashes:bbb:amount:5", 5e9, entity="TeraWulf", evidence_quote="same note"),
        _row("source-instrument:hashes:ccc:amount:5", 5e9, entity="TeraWulf", evidence_quote="same note"),
        # A distinct $5B obligation for TeraWulf (different quote) -> NOT excess.
        _row("source-instrument:hashes:ddd:amount:5", 5e9, entity="TeraWulf", evidence_quote="other note"),
        # Root cause 2b: aggregate snapshot sharing a content_hash with a source-instrument group.
        _row("source-instrument:hashes:eee:amount:4", 4e9, entity="Marathon", content_hash="H1"),
        _row("aggregate-obligation-snapshot:marathon:cap", 4e9, entity="Marathon", content_hash="H1"),
        # A non-approved row is ignored entirely.
        _row("source-instrument:hashes:zzz:amount:9", 9e9, metric_use_status="needs_deeper_extraction"),
    ]

    s = summarize_metric_integrity(rows, mega_threshold=50e9)

    assert s["approved_source_instrument_groups"] == 5  # aaa,bbb,ccc,ddd,eee (zzz excluded)
    assert s["aggregate_snapshot_groups"] == 1
    assert s["mega_misextraction_count"] == 1
    assert s["mega_gross_usd"] == 60e9
    # identical (TeraWulf, $5B, "same note") across 2 groups -> excess = $5B once; "other note" not counted.
    assert s["crossfiling_excess_usd"] == 5e9
    # Marathon snapshot shares content_hash H1 with a source-instrument group -> $4B dup.
    assert s["aggregate_snapshot_dup_usd"] == 4e9
    assert s["implied_overcount_usd"] == 60e9 + 5e9 + 4e9


def test_clean_metric_has_zero_overcount() -> None:
    rows = [
        _row("source-instrument:hashes:a:amount:5", 5e9, entity="A", evidence_quote="a"),
        _row("source-instrument:hashes:b:amount:7", 7e9, entity="B", evidence_quote="b"),
    ]

    s = summarize_metric_integrity(rows, mega_threshold=50e9)

    assert s["mega_gross_usd"] == 0
    assert s["crossfiling_excess_usd"] == 0
    assert s["aggregate_snapshot_dup_usd"] == 0
    assert s["implied_overcount_usd"] == 0
    assert s["base_metric_usd"] == 12e9
