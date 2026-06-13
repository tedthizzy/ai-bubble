"""Forced-truth calendar as code (WS3.3).

The pre-registered calendar (analysis/preregistered_signals.md) is encoded here as data so
the overlay can surface the next dated moment that will confirm, kill, or re-card a claim --
and so quarterly re-cards become tickets the system fires, not things remembered. Pure
selection logic under mypy + tests; the script renders viz/calendar.json from it.

EVENTS is the canonical machine-readable form of the registered calendar. New dated events
are added here and, when they bear on a signal's semantics, also via the amendment log.
"""

from __future__ import annotations

from datetime import date
from typing import Any

# kind: adjudication | freeze | recard | contract | legal | wall | earnings
# date: ISO yyyy-mm-dd for a point event; for windows, the OPENING date with a note.
EVENTS: list[dict[str, Any]] = [
    {
        "date": "2026-07-06",
        "kind": "legal",
        "label": "FSK securities class-action lead-plaintiff deadline",
        "why": "Confirms the FSK discount is legacy/governance-driven, not AI -- the basis of "
        "the S3' control-set exclusion (amendment A1).",
    },
    {
        "date": "2026-08-10",
        "kind": "recard",
        "label": "Q2-2026 BDC NAV re-card",
        "why": "Re-card the eight BDC NAVs from Q2 results into BDC_NAV; S3' must compare close "
        "to REPORTED NAV, never estimated.",
        "recurs": "quarterly",
    },
    {
        "date": "2026-09-30",
        "kind": "freeze",
        "label": "Signal-semantics freeze",
        "why": "No semantic amendments to S1-S4 after this date, so the Q4 adjudication scores a "
        "spec fixed well before the data arrived (ROADMAP doctrine).",
    },
    {
        "date": "2026-10-01",
        "kind": "contract",
        "label": "Google -> SpaceX compute contract revenue start",
        "why": "~$920M/month begins; the first of the SpaceX adjacency contracts to go live.",
    },
    {
        "date": "2026-11-10",
        "kind": "recard",
        "label": "Q3-2026 BDC NAV re-card",
        "why": "Re-card BDC NAVs from Q3 results; last re-card before the Q4 adjudication.",
        "recurs": "quarterly",
    },
    {
        "date": "2026-12-18",
        "kind": "adjudication",
        "label": "2026-Q4 TIMING-KILL adjudication",
        "why": "The engine's registered predictions are scored -- the first calibration datum for "
        "whether the apparatus can be trusted. The one date that is not optional.",
    },
    {
        "date": "2027-01-01",
        "kind": "contract",
        "label": "SpaceX contract termination window opens (90-day notice)",
        "why": "First quarter in which the ~$26B/yr SpaceX compute run-rate is economically "
        "at-will; renewal/termination behaviour is the best single test of the headline backlog.",
    },
    {
        "date": "2027-02-10",
        "kind": "recard",
        "label": "Q4-2026 BDC NAV re-card",
        "why": "Re-card BDC NAVs from full-year results.",
        "recurs": "quarterly",
    },
    {
        "date": "2030-01-01",
        "kind": "wall",
        "label": "Maturity wall 2030-2033 begins",
        "why": "88% of carded maturities ($36.6B of $41.7B) stack 2030-33 on collateral at/past "
        "GPU economic life -- the refinancing-vs-collateral-age terminal test.",
    },
    {
        "date": "2030-10-01",
        "kind": "contract",
        "label": "CoreWeave-OpenAI commitment expiry",
        "why": "The contract servicing the maturity wall is itself up for renewal as the wall "
        "peaks -- backlog quality becomes terminal.",
    },
]


def _parse(d: str) -> date:
    return date.fromisoformat(d)


def annotate(events: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    """Attach days_until and a status to each event, sorted by date ascending."""
    out: list[dict[str, Any]] = []
    for ev in sorted(events, key=lambda e: e["date"]):
        days = (_parse(ev["date"]) - today).days
        if days < 0:
            status = "past"
        elif days <= 14:
            status = "imminent"
        elif days <= 90:
            status = "approaching"
        else:
            status = "scheduled"
        out.append({**ev, "days_until": days, "status": status})
    return out


def upcoming(
    events: list[dict[str, Any]], today: date, horizon_days: int = 120
) -> list[dict[str, Any]]:
    """Future events within the horizon (inclusive), nearest first."""
    return [e for e in annotate(events, today) if 0 <= e["days_until"] <= horizon_days]


def next_event(events: list[dict[str, Any]], today: date) -> dict[str, Any] | None:
    """The single nearest future (or same-day) event, or None if the calendar is exhausted."""
    future = [e for e in annotate(events, today) if e["days_until"] >= 0]
    return future[0] if future else None


def calendar_payload(today: date, horizon_days: int = 120) -> dict[str, Any]:
    """The viz/calendar.json shape: the next event plus the near-horizon list and full annotated set."""
    return {
        "as_of": today.isoformat(),
        "next": next_event(EVENTS, today),
        "upcoming": upcoming(EVENTS, today, horizon_days),
        "all": annotate(EVENTS, today),
    }


def next_quarterly_recard(today: date) -> date | None:
    """The next BDC NAV re-card date on/after today (drives the standing re-card ticket)."""
    dates = sorted(
        _parse(e["date"])
        for e in EVENTS
        if e.get("kind") == "recard" and _parse(e["date"]) >= today
    )
    return dates[0] if dates else None
