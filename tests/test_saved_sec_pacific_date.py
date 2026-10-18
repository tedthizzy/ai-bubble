import gzip
import json
from datetime import UTC, datetime
from pathlib import Path

from scripts import refresh_market_from_saved_sec as refresh


def test_saved_panel_date_uses_pacific_after_utc_midnight(tmp_path: Path, monkeypatch) -> None:
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            instant = datetime(2026, 10, 18, 0, 30, tzinfo=UTC)
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)

    monkeypatch.setattr(refresh, "datetime", Clock)
    monkeypatch.setattr(refresh.overlay, "EDGAR_TICKERS", {"node": "NVDA"})
    panel = tmp_path / "panel.json"
    panel.write_text(
        json.dumps({"as_of": "2026-10-17", "entities": [{"ticker": "NVDA", "cik": "1"}]})
    )
    with gzip.open(tmp_path / "CIK0000000001-submissions.json.gz", "wt") as stream:
        json.dump(
            {
                "filings": {
                    "recent": {
                        "form": ["8-K", "8-K/A", "8-K", "8-K"],
                        "filingDate": ["2026-10-17", "2026-10-10", "2026-10-09", "2026-10-18"],
                    }
                }
            },
            stream,
        )
    assert refresh.saved_counts(panel, tmp_path) == {"node": {"new_8k_7d": 2}}
