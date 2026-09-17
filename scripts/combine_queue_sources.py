#!/usr/bin/env python3
"""Combine queue exports while replacing PJM serial projects moved to cycles."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _pjm_id(value: str) -> str:
    return re.sub(r"\s+-\s+moved to\b.*$", "", value.strip(), flags=re.IGNORECASE)


def combine(
    standard_path: Path,
    serial_path: Path,
    cycle_path: Path,
    output_path: Path,
    summary_path: Path,
) -> dict[str, object]:
    standard = _read(standard_path)
    serial = _read(serial_path)
    cycle = _read(cycle_path)
    if not cycle or any(not row.get("Project ID") for row in cycle):
        raise ValueError("PJM cycle export missing Project ID")
    if not serial or any(not _serial_id(row) for row in serial):
        raise ValueError("PJM serial export missing project ID")
    cycle_ids = {row["Project ID"].strip() for row in cycle}
    if len(cycle_ids) != len(cycle):
        raise ValueError("duplicate PJM cycle Project ID")
    serial_ids = [_pjm_id(_serial_id(row)) for row in serial]
    if len(serial_ids) != len(set(serial_ids)):
        raise ValueError("duplicate normalized PJM serial project ID")
    overlapping = [row for row in serial if _pjm_id(_serial_id(row)) in cycle_ids]
    retained_serial = [row for row in serial if _pjm_id(_serial_id(row)) not in cycle_ids]
    combined = standard + retained_serial + cycle
    fieldnames = list(dict.fromkeys(key for row in combined for key in row if key is not None))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(combined)

    summary: dict[str, object] = {
        "standard_rows": len(standard),
        "serial_rows": len(serial),
        "serial_rows_replaced_by_current_cycle": len(overlapping),
        "serial_rows_retained": len(retained_serial),
        "serial_is_partial": any(row.get("recovery_status") for row in serial),
        "current_cycle_rows": len(cycle),
        "combined_rows": len(combined),
        "current_cycle_source_id": cycle[0].get("source_id", ""),
        "serial_source_id": serial[0].get("source_id", ""),
        "overlap_example_ids": sorted({_pjm_id(_serial_id(row)) for row in overlapping})[:10],
        "standard_path": str(standard_path),
        "serial_path": str(serial_path),
        "cycle_path": str(cycle_path),
        "output_path": str(output_path),
    }
    if summary["serial_is_partial"]:
        summary["coverage_warning"] = (
            "serial PJM XML is a complete-prefix recovery with an unknown omitted tail"
        )
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def _serial_id(row: dict[str, str]) -> str:
    return (row.get("Project ID") or row.get("ProjectNumber") or "").strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--standard", type=Path, required=True)
    parser.add_argument("--serial", "--partial-serial", dest="serial", type=Path, required=True)
    parser.add_argument("--cycle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            combine(
                args.standard,
                args.serial,
                args.cycle,
                args.output,
                args.summary_output,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
