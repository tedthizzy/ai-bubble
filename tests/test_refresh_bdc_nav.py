import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("refresh_bdc_nav", Path(__file__).parents[1] / "scripts/refresh_bdc_nav.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fact(end, filed, val, form="10-Q", **extra):
    return dict(end=end, filed=filed, val=val, form=form, **extra)


def payload(rows):
    return {"facts": {"us-gaap": {"NetAssetValuePerShare": {"units": {"USD/shares": rows}}}}}


def test_nav_excludes_proxy_estimates_future_periods_and_duration_changes():
    actual = fact("2026-06-30", "2026-08-04", 16.24)
    rows = [actual, fact("2026-09-30", "2026-04-09", 17.14, "DEF 14A"),
            fact("2026-09-30", "2026-11-04", 18),
            fact("2026-09-30", "2026-10-15", 1.2, start="2026-07-01")]
    assert module.reported_nav(payload(rows), "2026-10-17") == actual


def test_nav_uses_latest_restated_observation_and_rejects_conflict():
    rows = [fact("2026-06-30", "2026-08-04", 16.24),
            fact("2026-06-30", "2026-08-05", 16.25, "10-Q/A")]
    assert module.reported_nav(payload(rows), "2026-10-17")["val"] == 16.25
    rows.append(fact("2026-06-30", "2026-08-05", 16.26, "10-Q/A"))
    with pytest.raises(ValueError, match="Conflicting"):
        module.reported_nav(payload(rows), "2026-10-17")
