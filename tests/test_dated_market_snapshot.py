import json

import pytest
from scripts.build_refresh_status import dated_market


def test_overnight_report_uses_frozen_market_and_preserves_observation_dates(tmp_path):
    (tmp_path / "analysis").mkdir()
    (tmp_path / "viz").mkdir()
    snapshot = {
        "as_of_pacific": "2026-10-17",
        "live": {
            "credit": {"ust5y": {"date": "2026-10-15", "value": 4.91}},
            "quotes": {"issuer": {"date": "2026-10-16", "close": 10}},
        },
    }
    path = tmp_path / "analysis/market_snapshot_2026-10-17.json"
    path.write_text(json.dumps(snapshot))
    (tmp_path / "viz/live.json").write_text(
        json.dumps({"quotes": {"issuer": {"date": "2026-10-19", "close": 100}}})
    )
    actual_path, live = dated_market(tmp_path, "2026-10-17")
    assert actual_path == path
    assert live["quotes"]["issuer"]["close"] == 10
    assert live["credit"]["ust5y"]["date"] == "2026-10-15"


@pytest.mark.parametrize("group", ["quotes", "credit", "bdc", "adjacent"])
def test_future_observation_stops_a_dated_report(tmp_path, group):
    (tmp_path / "analysis").mkdir()
    (tmp_path / "analysis/market_snapshot_2026-10-17.json").write_text(
        json.dumps(
            {"as_of_pacific": "2026-10-17", "live": {group: {"value": {"date": "2026-10-19"}}}}
        )
    )
    with pytest.raises(ValueError, match="postdates"):
        dated_market(tmp_path, "2026-10-17")
