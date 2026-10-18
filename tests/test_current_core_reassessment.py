from __future__ import annotations

import copy
import gzip
import hashlib
from typing import TYPE_CHECKING

import pytest
from scripts import reassess_current_core as review

if TYPE_CHECKING:
    from pathlib import Path


def test_convertible_notes_are_included_beside_other_borrowing() -> None:
    card = {
        "ticker": "BTBT",
        "filing_date": "2026-08-13",
        "units_usd": 1000,
        "components": [
            {"label": "Short-term debt", "reported_value": "78,436", "sign": 1},
            {"label": "Long-term debt, net", "reported_value": "25,464", "sign": 1},
            {"label": "Convertible notes payable, net", "reported_value": "336,155", "sign": 1},
        ],
    }
    text = "Short-term debt 78,436 0 Long-term debt, net 25,464 0 Convertible notes payable, net 336,155 110,291"
    result = review.verify_debt_card(
        card, {"filing_date": "2026-08-13", "source_sha256": "fixture"}, text
    )
    assert result["reported_debt_usd"] == 440_055_000
    assert result["reported_debt_usd"] != 103_900_000


def test_current_column_can_follow_the_prior_year_without_selecting_it() -> None:
    card = {
        "ticker": "NBIS",
        "filing_date": "2026-08-12",
        "units_usd": 1_000_000,
        "period_end": "2026-06-30",
        "column_periods": ["2025-12-31", "2026-06-30"],
        "components": [
            {
                "label": "Debt, current",
                "reported_value": "46.7",
                "sign": 1,
                "reported_columns": ["24.5", "46.7"],
                "selected_column": 1,
            }
        ],
    }
    source = {"filing_date": "2026-08-12", "source_sha256": "fixture"}
    assert (
        review.verify_debt_card(card, source, "Debt, current 24.5 46.7")["reported_debt_usd"]
        == 46_700_000
    )
    wrong = copy.deepcopy(card)
    wrong["components"][0].update(reported_value="24.5", selected_column=0)
    with pytest.raises(ValueError, match="current period"):
        review.verify_debt_card(wrong, source, "Debt, current 24.5 46.7")


def test_changed_or_unverifiable_row_stops_the_financial_total() -> None:
    card = {
        "ticker": "issuer",
        "filing_date": "2026-08-12",
        "units_usd": 1000,
        "components": [{"label": "Debt", "reported_value": "100", "sign": 1}],
    }
    with pytest.raises(ValueError, match="Unverified debt row"):
        review.verify_debt_card(card, {"filing_date": "2026-08-12"}, "Debt 1000")
    with pytest.raises(ValueError, match="filing date mismatch"):
        review.verify_debt_card(card, {"filing_date": "2025-08-12"}, "Debt 100")


def test_primary_and_normalized_bytes_must_both_match(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(review, "ROOT", tmp_path)
    raw = b"<p>Primary statement</p>"
    normalized = b"Primary statement"
    (tmp_path / "source.gz").write_bytes(gzip.compress(raw))
    (tmp_path / "text.txt").write_bytes(normalized)
    record = {
        "source_path": "source.gz",
        "normalized_path": "text.txt",
        "url": "https://example.invalid/statement",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "normalized_sha256": hashlib.sha256(normalized).hexdigest(),
    }
    assert review.source_text(record) == "Primary statement"
    (tmp_path / "text.txt").write_text("Changed normalized statement")
    with pytest.raises(ValueError, match="Changed normalized"):
        review.source_text(record)
    (tmp_path / "source.gz").write_bytes(gzip.compress(b"Changed primary statement"))
    with pytest.raises(ValueError, match="Changed primary"):
        review.source_text(record)
