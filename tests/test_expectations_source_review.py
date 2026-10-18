from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest
from scripts import review_expectations_inputs as review

from bubble.expectations.names import AS_OF, INPUT_RECORD, NAMES

if TYPE_CHECKING:
    from pathlib import Path


def test_comparable_revenue_requires_the_same_period_accession_and_cutoff() -> None:
    card = {"namespace": "us-gaap", "tag": "Revenues", "accession": "current"}
    rows = [
        {
            "start": "2025-06-01",
            "end": "2025-08-31",
            "val": 80_934_000,
            "accn": "current",
            "filed": "2026-10-07",
        },
        {
            "start": "2025-06-01",
            "end": "2025-08-31",
            "val": 80_936_000,
            "accn": "older",
            "filed": "2025-10-07",
        },
        {
            "start": "2025-06-01",
            "end": "2025-08-31",
            "val": 90_000_000,
            "accn": "current",
            "filed": "2026-10-19",
        },
    ]
    facts = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": rows}}}}}
    assert review.fact_value(facts, card, "2025-06-01", "2025-08-31", AS_OF) == 80_934_000
    rows.append({**rows[0], "val": 99})
    with pytest.raises(ValueError, match="conflicting comparable"):
        review.fact_value(facts, card, "2025-06-01", "2025-08-31", AS_OF)
    with pytest.raises(ValueError, match="postdates"):
        review.fact_value(facts, card, "2027-06-01", "2027-08-31", AS_OF)


def test_statistics_use_the_close_before_after_hours_and_verify_source_bytes(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(review, "ROOT", tmp_path)
    raw = b"<p>61.39 -8.30 (-11.91%) At close: Oct 16, 2026, 4:00 PM EDT</p><p>60.97 After-hours</p><p>Enterprise Value 79.89B Net Cash -46.03B</p>"
    path = tmp_path / "market.html"
    path.write_bytes(raw)
    source = {"path": path.name, "sha256": hashlib.sha256(raw).hexdigest()}
    quote = {"date": "2026-10-16", "close": 61.38999938964844}
    result = review.market_card(source, quote)
    assert result["close_usd"] == 61.39
    assert result["ev_usd_b"] == 79.89
    assert result["net_debt_usd_b"] == 46.03
    with pytest.raises(ValueError, match="disagrees"):
        review.market_card(source, {**quote, "close": 60.97})
    path.write_bytes(raw + b"changed")
    with pytest.raises(ValueError, match="Changed valuation source"):
        review.market_card(source, quote)


def test_frozen_cards_keep_primary_rpo_distinct_from_broader_commitments() -> None:
    assert AS_OF == "2026-10-17"
    cards = {row.ticker: row for row in NAMES}
    assert cards["NBIS"].backlog_usd_b == 37.4906
    assert cards["NBIS"].backlog_usd_b != 40.0
    assert cards["IREN"].backlog_usd_b == 16.6
    assert cards["APLD"].backlog_usd_b == 36.0
    assert cards["APLD"].backlog_usd_b != 86.0
    for ticker, card in cards.items():
        evidence = INPUT_RECORD["evidence"][ticker]
        assert card.current_annualized_revenue_usd_b * 1e9 == pytest.approx(
            evidence["ttm_revenue_usd"]
        )
        assert evidence["ttm_revenue_usd"] == sum(
            row["sign"] * row["value_usd"] for row in evidence["revenue_components"]
        )
        assert evidence["revenue_period_end"] <= AS_OF
        assert evidence["market"]["market_date"] == "2026-10-16"
        assert evidence["contract_and_interim_statement"]["filing_date"] <= AS_OF
