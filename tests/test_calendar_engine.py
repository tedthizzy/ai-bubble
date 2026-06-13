"""Unit tests for the forced-truth calendar (src/bubble/calendar_engine.py)."""

from __future__ import annotations

from datetime import date

from bubble.calendar_engine import (
    EVENTS,
    annotate,
    calendar_payload,
    next_event,
    next_quarterly_recard,
    upcoming,
)

# A fixed "today" so the registered calendar's relative positions are deterministic.
TODAY = date(2026, 6, 13)


def test_events_are_chronological_and_well_formed() -> None:
    dates = [e["date"] for e in EVENTS]
    assert dates == sorted(dates), "EVENTS should be declared in date order"
    for e in EVENTS:
        assert {"date", "kind", "label", "why"} <= e.keys()
        date.fromisoformat(e["date"])  # parses


def test_annotate_sets_status_bands() -> None:
    rows = annotate(EVENTS, TODAY)
    by_label = {r["label"]: r for r in rows}
    # FSK deadline 2026-07-06 is 23 days out -> approaching
    assert (
        by_label["FSK securities class-action lead-plaintiff deadline"]["status"] == "approaching"
    )
    # The Q4 adjudication is months out -> scheduled
    assert by_label["2026-Q4 TIMING-KILL adjudication"]["status"] == "scheduled"
    # The maturity wall is years out -> scheduled, large positive days_until
    assert by_label["Maturity wall 2030-2033 begins"]["days_until"] > 1000


def test_imminent_band() -> None:
    near = date(2026, 7, 1)  # 5 days before the FSK deadline
    rows = {r["label"]: r for r in annotate(EVENTS, near)}
    assert rows["FSK securities class-action lead-plaintiff deadline"]["status"] == "imminent"


def test_past_events_marked() -> None:
    later = date(2027, 1, 15)
    rows = {r["label"]: r for r in annotate(EVENTS, later)}
    assert rows["2026-Q4 TIMING-KILL adjudication"]["status"] == "past"
    assert rows["2026-Q4 TIMING-KILL adjudication"]["days_until"] < 0


def test_next_event_is_nearest_future() -> None:
    nxt = next_event(EVENTS, TODAY)
    assert nxt is not None
    assert nxt["label"] == "FSK securities class-action lead-plaintiff deadline"


def test_next_event_none_when_calendar_exhausted() -> None:
    assert next_event(EVENTS, date(2099, 1, 1)) is None


def test_upcoming_respects_horizon() -> None:
    within = upcoming(EVENTS, TODAY, horizon_days=120)
    labels = [e["label"] for e in within]
    assert "FSK securities class-action lead-plaintiff deadline" in labels
    assert "2026-Q4 TIMING-KILL adjudication" not in labels  # >120 days out
    assert all(0 <= e["days_until"] <= 120 for e in within)


def test_next_quarterly_recard() -> None:
    nxt = next_quarterly_recard(TODAY)
    assert nxt == date(2026, 8, 10)
    # after the last carded re-card, there is none left
    assert next_quarterly_recard(date(2027, 3, 1)) is None


def test_calendar_payload_shape() -> None:
    payload = calendar_payload(TODAY)
    assert payload["as_of"] == "2026-06-13"
    assert payload["next"]["label"] == "FSK securities class-action lead-plaintiff deadline"
    assert isinstance(payload["upcoming"], list)
    assert len(payload["all"]) == len(EVENTS)
