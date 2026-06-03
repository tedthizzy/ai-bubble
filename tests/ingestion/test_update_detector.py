"""Continuous-update delta detector."""

from __future__ import annotations

from bubble.ingestion.update_detector import detect_filing_updates


def _sub(cik, acc, form, date):
    return {"cik": cik, "accession": acc, "form": form, "filing_date": date}


def test_no_new_filings_no_rerun() -> None:
    out = detect_filing_updates(
        {"acc-1", "acc-2"},
        [_sub("123", "acc-1", "10-K", "2026-01-01"), _sub("123", "acc-2", "8-K", "2026-02-01")],
    )
    assert out["new_filing_count"] == 0
    assert out["rerun_recommended"] is False


def test_new_high_signal_triggers_rerun_and_priority() -> None:
    out = detect_filing_updates(
        ["acc-old"],
        [
            _sub("123", "acc-old", "10-K", "2026-01-01"),  # already ingested
            _sub("123", "acc-8k", "8-K", "2026-05-01"),  # new, relevance 65 -> rerun
            _sub("999", "acc-form4", "4", "2026-05-02"),  # new, relevance 20 -> low signal
            _sub("123", "acc-10q", "10-Q", "2026-05-03"),  # new, relevance 85 -> top
        ],
    )
    assert out["new_filing_count"] == 3
    assert out["high_signal_count"] == 2  # 10-Q and 8-K
    assert out["rerun_recommended"] is True
    # 10-Q (85) sorts above 8-K (65) above Form 4 (20).
    assert out["top_new_filings"][0]["form"] == "10-Q"
    assert out["top_new_filings"][-1]["form"] == "4"
    assert out["new_filings_by_cik"]["123"] == 2


def test_only_low_signal_no_rerun() -> None:
    out = detect_filing_updates(
        set(),
        [_sub("999", "acc-4", "4", "2026-05-02"), _sub("999", "acc-13g", "SC 13G", "2026-05-03")],
    )
    assert out["new_filing_count"] == 2
    assert out["high_signal_count"] == 0
    assert out["rerun_recommended"] is False


def test_form_family_scoring() -> None:
    out = detect_filing_updates(set(), [_sub("1", "a", "8-K/A", "2026-01-01")])
    # 8-K/A inherits 8-K relevance (65) -> high signal.
    assert out["top_new_filings"][0]["relevance"] == 65
    assert out["rerun_recommended"] is True
