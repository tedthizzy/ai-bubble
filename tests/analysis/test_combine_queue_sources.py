from __future__ import annotations

import csv
from pathlib import Path

from scripts.combine_queue_sources import combine


def _write(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_current_pjm_cycle_replaces_moved_serial_project_once(tmp_path: Path) -> None:
    standard = tmp_path / "standard.csv"
    serial = tmp_path / "serial.csv"
    cycle = tmp_path / "cycle.csv"
    output = tmp_path / "combined.csv"
    _write(standard, [{"source_id": "nyiso", "ProjectNumber": "NY1"}])
    _write(
        serial,
        [
            {"source_id": "pjm-serial", "ProjectNumber": "AE1-070 - moved to TC1"},
            {"source_id": "pjm-serial", "ProjectNumber": "AG1-060"},
        ],
    )
    _write(cycle, [{"source_id": "pjm-cycle", "Project ID": "AE1-070"}])

    summary = combine(standard, serial, cycle, output, tmp_path / "summary.json")

    assert summary["serial_rows_replaced_by_current_cycle"] == 1
    assert summary["combined_rows"] == 3
    with output.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["source_id"] for row in rows] == ["nyiso", "pjm-serial", "pjm-cycle"]
    assert [row["ProjectNumber"] or row["Project ID"] for row in rows] == [
        "NY1",
        "AG1-060",
        "AE1-070",
    ]


def test_full_pjm_serial_workbook_replaces_moved_ids_without_partial_warning(
    tmp_path: Path,
) -> None:
    standard = tmp_path / "standard.csv"
    serial = tmp_path / "serial.csv"
    cycle = tmp_path / "cycle.csv"
    output = tmp_path / "combined.csv"
    _write(standard, [{"source_id": "nyiso", "Project ID": "NY1"}])
    _write(
        serial,
        [
            {"source_id": "pjm-serial-full", "Project ID": "AE1-070 - moved to TC1"},
            {"source_id": "pjm-serial-full", "Project ID": "AG2-344 - moved to TC2"},
            {"source_id": "pjm-serial-full", "Project ID": "AG1-060"},
        ],
    )
    _write(
        cycle,
        [
            {"source_id": "pjm-cycle", "Project ID": "AE1-070"},
            {"source_id": "pjm-cycle", "Project ID": "AG2-344"},
        ],
    )

    summary = combine(standard, serial, cycle, output, tmp_path / "summary.json")

    assert summary["serial_rows"] == 3
    assert summary["serial_rows_replaced_by_current_cycle"] == 2
    assert summary["serial_rows_retained"] == 1
    assert summary["serial_is_partial"] is False
    assert "coverage_warning" not in summary
    assert summary["combined_rows"] == 4
