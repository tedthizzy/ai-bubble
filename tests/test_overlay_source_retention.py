from __future__ import annotations

import importlib.util
import json
import urllib.error
from datetime import date
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "overlay_retention", Path(__file__).resolve().parents[1] / "scripts/refresh_live_overlay.py"
)
assert SPEC and SPEC.loader
overlay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(overlay)


def test_sec_failure_records_cause_without_dropping_dated_observations(monkeypatch):
    def blocked():
        raise urllib.error.HTTPError(
            "https://www.sec.gov/files/company_tickers.json", 403, "denied", {}, None
        )

    monkeypatch.setattr(overlay, "_edgar_ciks", blocked)
    errors = []
    fresh = overlay._edgar_counts(today=date(2026, 10, 17), errors=errors)
    retained = overlay._last_observed_edgar(
        {"edgar": {"CoreWeave": {"new_8k_7d": 2, "observed_as_of": "2026-10-16"}}}, fresh
    )
    assert fresh == {}
    assert errors[0]["http_status"] == 403
    assert retained["CoreWeave"]["observed_as_of"] == "2026-10-16"
    assert retained["CoreWeave"]["new_8k_7d"] == 2


def test_sec_window_excludes_future_filings_and_validates_array_lengths(monkeypatch):
    monkeypatch.setattr(overlay, "EDGAR_TICKERS", {"CoreWeave": "CRWV"})
    monkeypatch.setattr(overlay, "_edgar_ciks", lambda: {"CRWV": "0001769628"})
    monkeypatch.setattr(overlay.time, "sleep", lambda _: None)
    recent = {
        "form": ["8-K", "8-K", "8-K", "10-Q"],
        "filingDate": ["2026-10-10", "2026-10-09", "2026-10-18", "2026-10-17"],
    }
    monkeypatch.setattr(
        overlay, "_get", lambda *a, **k: json.dumps({"filings": {"recent": recent}})
    )
    fresh = overlay._edgar_counts(today=date(2026, 10, 17))
    assert fresh["CoreWeave"] == {"new_8k_7d": 1, "observed_as_of": "2026-10-17"}
    recent["form"].append("8-K")
    errors = []
    assert overlay._edgar_counts(today=date(2026, 10, 17), errors=errors) == {}
    assert errors[0]["error_type"] == "ValueError"


def test_fresh_observation_replaces_only_its_own_retained_value():
    old = {
        "edgar_last_observed": {
            "A": {"new_8k_7d": 3, "observed_as_of": "2026-10-16"},
            "B": {"new_8k_7d": 4, "observed_as_of": "2026-10-15"},
        }
    }
    kept = overlay._last_observed_edgar(
        old, {"A": {"new_8k_7d": 0, "observed_as_of": "2026-10-17"}}
    )
    assert kept["A"]["new_8k_7d"] == 0
    assert kept["A"]["observed_as_of"] == "2026-10-17"
    assert kept["B"] == old["edgar_last_observed"]["B"]


def test_demand_review_does_not_relabel_june_basket_as_current(tmp_path, monkeypatch):
    monkeypatch.setattr(overlay, "ROOT", tmp_path)
    (tmp_path / "analysis").mkdir()
    path = tmp_path / "analysis/demand_trajectory.json"
    payload = {
        "baskets": [{"as_of": "2026-06-13"}],
        "current_review": {"as_of": "2026-10-17", "registered_growth_eligible": False},
    }
    path.write_text(json.dumps(payload))
    assert overlay._demand_baskets(date(2026, 6, 13)) == payload["baskets"]
    assert overlay._demand_baskets(date(2026, 10, 17)) == []
    payload["baskets"].append({"as_of": "2026-11-01"})
    path.write_text(json.dumps(payload))
    assert overlay._demand_baskets(date(2026, 11, 1)) == payload["baskets"]
    assert overlay._demand_baskets(date(2026, 10, 17)) == []
