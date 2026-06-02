"""Physical construction-status taxonomy contract.

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
* ``_status_from_tracker`` (the observations writer) now shares the same mapper,
  so project rows and observation rows cannot disagree on the same raw status.

The characterization tests below lock the intended shared taxonomy after the
ingestion mappers were unified. The mixed
``Approved/Permitted/Under construction`` case intentionally remains
``under_construction`` because the more advanced visible construction state is
more useful for deliverability analysis than downgrading it to a permit-only
state.
"""

from __future__ import annotations

import pytest

from bubble.ingestion.physical.construction_observations import _status_from_tracker
from bubble.ingestion.physical.tracker_extraction import _construction_status


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
        ("delayed", "delayed"),
        ("Suspended", "delayed"),
        ("on hold", "delayed"),
        ("commissioning", "mechanical_completion"),
        ("mechanical completion", "mechanical_completion"),
        ("Proposed", "announced"),
        ("planned", "announced"),
        ("", "announced"),
    ],
)
def test_construction_status_current_contract(raw: str, expected: str) -> None:
    assert _construction_status(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("operational", "in_service"),
        ("under construction", "under_construction"),
        ("planned", "announced"),
        ("cancelled", "cancelled"),
        ("delayed", "delayed"),
        ("Suspended", "delayed"),
        ("on hold", "delayed"),
        ("commissioning", "mechanical_completion"),
    ],
)
def test_status_from_tracker_current_contract(raw: str, expected: str) -> None:
    assert _status_from_tracker({"tracker_status": raw}) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "delayed",
        "Suspended",
        "on hold",
        "commissioning",
        "mechanical completion",
        "Approved/Permitted/Under construction",
    ],
)
def test_status_mappers_agree_on_shared_taxonomy(raw: str) -> None:
    assert _construction_status(raw) == _status_from_tracker({"tracker_status": raw})
