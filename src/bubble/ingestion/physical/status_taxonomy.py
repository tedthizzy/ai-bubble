"""Shared construction-status taxonomy for physical ingestion."""

from __future__ import annotations


def construction_status_from_text(status: str | None) -> str:
    """Map tracker status text into the canonical ConstructionStatus values."""

    normalized = (status or "").strip().lower()
    if not normalized:
        return "announced"

    rules = [
        (("cancel",), "cancelled"),
        (("delay", "suspend", "on hold", "paused"), "delayed"),
        (
            ("operating", "operational", "online", "in service", "in-service"),
            "in_service",
        ),
        (
            (
                "mechanical completion",
                "mechanically complete",
                "commissioning",
                "substantial completion",
                "energized",
            ),
            "mechanical_completion",
        ),
        (
            (
                "under construction",
                "under-construction",
                "construction",
                "expansion",
                "site work",
            ),
            "under_construction",
        ),
        (("approved", "permitted"), "permitted"),
    ]
    for tokens, status_value in rules:
        if any(token in normalized for token in tokens):
            return status_value
    return "announced"
