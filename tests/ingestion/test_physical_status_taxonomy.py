"""Physical construction-status taxonomy contract + verified gap scaffolds.

Codex "lane 2" (physical status population) — reframed after verification.

FRAMING CORRECTION (verified against data/physical/*.csv with csv.DictReader):
``construction_status`` is NOT empty. projects.csv (2125 rows) and
observations.csv (2125 rows) are both 0/2125 empty, carrying only four distinct
values: announced=974, in_service=793, under_construction=298, cancelled=60.
The real defect is taxonomy *starvation*, not emptiness:

* ``_construction_status`` (the projects writer) can never emit ``delayed`` or
  ``mechanical_completion`` and only emits ``permitted`` for a bare
  approved/permitted string — the live tracker string carries the
  ``under construction`` token too, which is checked first, so ``permitted`` is
  starved (0 rows on disk despite 143 ``approved_or_permitted`` permit_status).
* ``_status_from_tracker`` (the observations writer) *does* recognise
  ``delayed`` — so the two writers disagree on the same raw input.

The characterization tests below lock the verified-today contract. The
``xfail(strict=True)`` tests encode the verified gaps: they keep the gate green
today and FLIP to a failure the moment the gap is closed, prompting removal of
the marker. Proposed target mappings only — Codex owns the final taxonomy.
"""

from __future__ import annotations

import pytest

from bubble.ingestion.physical.construction_observations import _status_from_tracker
from bubble.ingestion.physical.tracker_extraction import _construction_status


# ---------------------------------------------------------------------------
# Characterization (GREEN): the projects writer's status mapper as it behaves
# today. Locks the contract so a refactor can't silently reclassify projects.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Operating", "in_service"),
        ("operational", "in_service"),
        ("in service", "in_service"),
        ("Cancelled", "cancelled"),
        ("canceled", "cancelled"),
        ("Under construction", "under_construction"),
        ("expansion", "under_construction"),
        # A bare permit signal IS reachable in isolation...
        ("Approved", "permitted"),
        ("Permitted", "permitted"),
        # ...but the live tracker string carries BOTH tokens, and the
        # under-construction branch is checked before the permit branch, so a
        # clean permitting signal is starved (0 'permitted' rows on disk).
        ("Approved/Permitted/Under construction", "under_construction"),
        ("Proposed", "announced"),
        ("planned", "announced"),
        ("", "announced"),
    ],
)
def test_construction_status_current_contract(raw: str, expected: str) -> None:
    assert _construction_status(raw) == expected


# ---------------------------------------------------------------------------
# Characterization (GREEN): the observations writer's mapper. Note it DOES map
# 'delayed' -> delayed, which the projects writer does not — the asymmetry the
# divergence scaffold below pins down.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("operational", "in_service"),
        ("under construction", "under_construction"),
        ("planned", "announced"),
        ("cancelled", "cancelled"),
        ("delayed", "delayed"),
    ],
)
def test_status_from_tracker_current_contract(raw: str, expected: str) -> None:
    assert _status_from_tracker({"tracker_status": raw}) == expected


# ---------------------------------------------------------------------------
# Verified taxonomy GAPS (xfail strict). Each maps to a ConstructionStatus enum
# member that is currently unreachable from the projects.csv pipeline.
# ---------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    reason="GAP: _construction_status has no delayed branch; 'delayed' -> announced",
)
def test_construction_status_should_map_delayed() -> None:
    assert _construction_status("delayed") == "delayed"


@pytest.mark.xfail(
    strict=True,
    reason="GAP: 'Suspended' is a delay signal but maps to announced today",
)
def test_construction_status_should_map_suspended_to_delayed() -> None:
    assert _construction_status("Suspended") == "delayed"


@pytest.mark.xfail(
    strict=True,
    reason="GAP: 'on hold' is a delay signal but maps to announced today",
)
def test_construction_status_should_map_on_hold_to_delayed() -> None:
    assert _construction_status("on hold") == "delayed"


@pytest.mark.xfail(
    strict=True,
    reason="GAP: ConstructionStatus.MECHANICAL_COMPLETION is unreachable from ingestion",
)
def test_construction_status_should_map_commissioning_to_mechanical_completion() -> None:
    assert _construction_status("commissioning") == "mechanical_completion"


@pytest.mark.xfail(
    strict=True,
    reason="DIVERGENCE: observations writer maps 'delayed'->delayed but projects "
    "writer maps it ->announced; the two writers must agree",
)
def test_status_mappers_agree_on_delayed() -> None:
    assert _construction_status("delayed") == _status_from_tracker(
        {"tracker_status": "delayed"}
    )
