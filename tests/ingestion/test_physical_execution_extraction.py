from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from bubble.ingestion.physical.execution_extraction import (
    extract_physical_execution_terms_from_csvs,
)

if TYPE_CHECKING:
    from pathlib import Path


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    assert rows
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def test_extract_physical_execution_terms_from_mixed_source_rows(tmp_path: Path) -> None:
    tracker = tmp_path / "source_rows" / "tracker_records.csv"
    queue = tmp_path / "source_rows" / "queue_records.csv"
    output = tmp_path / "physical" / "physical_execution_terms.csv"
    _write_csv(
        tracker,
        [
            {
                "projectName": "Stargate Abilene",
                "operators": "Crusoe / OpenAI / Oracle",
                "state": "TX",
                "notes": (
                    "Five (5) 38 MW Titan 350 and Five (5) 34.1 MW GE LM2500 "
                    "will generate power for onsite use only for data centers."
                ),
                "source_id": "tracker",
                "source_uri": "https://example.test/stargate",
                "document_id": "tracker-doc",
                "content_hash": "a" * 64,
            }
        ],
    )
    _write_csv(
        queue,
        [
            {
                "Project Name": "Grid-connected campus",
                "Interconnection Customer": "Utility Customer",
                "Non-Confidential Summary": (
                    "ERCOT GIS INR queue position and Large Load Interconnection Study "
                    "records show an interconnection agreement executed for in-service grid load."
                ),
                "source_id": "ercot",
                "source_uri": "https://example.test/queue",
                "document_id": "queue-doc",
                "content_hash": "b" * 64,
            }
        ],
    )

    summary = extract_physical_execution_terms_from_csvs([tracker, queue], output)
    rows = _read_csv(output)
    values = {(row["term_type"], row["value"], row["unit"]) for row in rows}

    assert summary.source_rows == 2
    assert summary.terms_written == 2
    assert summary.by_term_type == {
        "behind_the_meter_or_off_grid": 1,
        "onsite_generation_mw": 1,
    }
    assert ("onsite_generation_mw", "360.5", "MW") in values
    assert not any(row["term_type"] == "air_permit_id" for row in rows)
    assert all(row["source_uri"] == "https://example.test/stargate" for row in rows)
    assert all(row["project_name"] == "Stargate Abilene" for row in rows)


def test_extract_physical_execution_terms_writes_header_for_no_terms(tmp_path: Path) -> None:
    source = tmp_path / "source_rows" / "tracker_records.csv"
    output = tmp_path / "physical" / "physical_execution_terms.csv"
    _write_csv(
        source,
        [
            {
                "projectName": "Generic campus",
                "notes": "Ordinary financing disclosure with no physical execution evidence.",
                "source_uri": "https://example.test/generic",
            }
        ],
    )

    summary = extract_physical_execution_terms_from_csvs([source], output)

    assert summary.terms_written == 0
    assert _read_csv(output) == []
