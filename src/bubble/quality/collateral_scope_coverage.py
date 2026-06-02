"""Residual collateral-scope gap coverage metric (read-only QA).

Quantifies, over the materiality decisions, how many packets remain blocked on
``determine collateral scope`` and *why*:

* ``no_scope_language_count``: the selected ``evidence_quote`` contains none of the
  ``_collateral_scope_terms`` markers, so the gap is a SNIPPET-SELECTION miss (the
  selector picked a non-scope excerpt), not missing evidence. Watch this number as
  snippet selection improves.
* ``first_lien_marker_miss_count``: the quote determinately states secured scope via
  first-/second-lien language but carries no other recognised marker — a detection-
  marker gap (``_collateral_scope_terms`` omits ``first lien``/``second lien``).

The marker list is imported from the adjudicator so this metric can never drift from
the real detection logic.
"""

from __future__ import annotations

from typing import Any

from bubble.analysis.materiality_adjudication_results import _collateral_scope_terms

COLLATERAL_GAP = "determine collateral scope"
# Multi-word lien markers only — bare "lien" over-matches "permitted liens" and
# negative-covenant "not subject to any lien".
LIEN_MARKERS = ("first lien", "second lien", "first-lien", "second-lien", "first priority lien")


def _exposure(row: dict[str, str]) -> float:
    try:
        return float(row.get("exposure_basis_usd") or 0.0)
    except ValueError:
        return 0.0


def summarize_collateral_scope_coverage(rows: list[dict[str, str]]) -> dict[str, Any]:
    """Summarise residual collateral-scope gaps and their root cause.

    A row is counted when it is ``needs_deeper_extraction`` and its ``remaining_gap``
    contains ``determine collateral scope``. ``sole_gap`` rows have collateral scope as
    the only remaining gap.
    """

    markers = tuple(_collateral_scope_terms())
    blocked = [
        row
        for row in rows
        if row.get("decision") == "needs_deeper_extraction"
        and COLLATERAL_GAP in (row.get("remaining_gap") or "")
    ]
    sole = [row for row in blocked if (row.get("remaining_gap") or "").strip() == COLLATERAL_GAP]

    no_scope_language = 0
    first_lien_miss: list[dict[str, Any]] = []
    for row in blocked:
        quote = (row.get("evidence_quote") or "").lower()
        if any(marker in quote for marker in markers):
            continue
        no_scope_language += 1
        if any(lien in quote for lien in LIEN_MARKERS):
            first_lien_miss.append(
                {
                    "packet_id": row.get("packet_id", ""),
                    "entity": row.get("entity", ""),
                    "exposure_basis_usd": _exposure(row),
                }
            )

    return {
        "blocked_collateral_gaps": len(blocked),
        "sole_gap_count": len(sole),
        "sole_gap_exposure_usd": round(sum(_exposure(row) for row in sole), 2),
        "no_scope_language_count": no_scope_language,
        "first_lien_marker_miss_count": len(first_lien_miss),
        "first_lien_marker_miss_packets": sorted(
            first_lien_miss, key=lambda item: item["exposure_basis_usd"], reverse=True
        ),
    }
