#!/usr/bin/env python3
"""Extract NYISO's direct data-center load requests from its Load Projects sheet."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from bubble.analysis.physical_capacity import _queue_record_in_scope


END_USE_NAMES = {
    "DAT": "data_center",
    "DAT-AI": "ai_data_center",
    "DAT-CM": "cryptocurrency_mining_data_center",
}


def extract(input_path: Path, output_path: Path, summary_path: Path) -> dict[str, object]:
    with input_path.open(newline="") as handle:
        source_rows = list(csv.DictReader(handle))
    nyiso_load_rows = [
        row
        for row in source_rows
        if row.get("source_id", "").startswith("nyiso-")
        and row.get("sheet_name", "").strip() == "Load Projects"
    ]
    if not nyiso_load_rows:
        raise ValueError("NYISO Load Projects sheet is absent")

    output_rows: list[dict[str, str]] = []
    counts: Counter[str] = Counter()
    mw_by_end_use: defaultdict[str, Decimal] = defaultdict(Decimal)
    for row in nyiso_load_rows:
        end_use = row.get("End-Use", "").strip().upper()
        if end_use not in END_USE_NAMES:
            continue
        counts["data_center_rows_in_source"] += 1
        if not _queue_record_in_scope(row):
            counts["data_center_rows_out_of_scope"] += 1
            continue
        try:
            peak_mw = Decimal(row.get("Peak MW load", ""))
        except InvalidOperation as exc:
            raise ValueError(
                f"missing/invalid Peak MW load for queue {row['Queue Number']}"
            ) from exc
        if peak_mw <= 0:
            raise ValueError(f"nonpositive Peak MW load for queue {row['Queue Number']}")
        counts["data_center_rows_active"] += 1
        mw_by_end_use[end_use] += peak_mw
        output_rows.append(
            {
                "queue_number": row["Queue Number"],
                "project_name": row.get("Project: Project Name", ""),
                "developer": row.get("Developer Name", ""),
                "end_use_code": end_use,
                "end_use": END_USE_NAMES[end_use],
                "project_status_code": row.get("Project Status #", ""),
                "peak_mw_load": str(peak_mw),
                "county": row.get("County", ""),
                "state": row.get("State", ""),
                "nyiso_zone": row.get("NYISO Zone", ""),
                "last_updated_date": row.get("Last Updated Date", ""),
                "source_row_number": row.get("source_row_number", ""),
                "source_uri": row.get("source_uri", ""),
                "retrieved_at": row.get("retrieved_at", ""),
                "content_hash": row.get("content_hash", ""),
            }
        )
    queue_numbers = [row["queue_number"] for row in output_rows]
    if not output_rows:
        raise ValueError("NYISO Load Projects sheet has no active DAT-coded load rows")
    if len(queue_numbers) != len(set(queue_numbers)):
        raise ValueError("duplicate NYISO queue numbers in direct-load rows")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)

    summary: dict[str, object] = {
        "source": "NYISO Interconnection Queue, Load Projects sheet",
        "source_uri": nyiso_load_rows[0].get("source_uri", ""),
        "source_content_hash": nyiso_load_rows[0].get("content_hash", ""),
        "retrieved_at_utc": nyiso_load_rows[0].get("retrieved_at", ""),
        "source_load_sheet_rows": len(nyiso_load_rows),
        **dict(counts),
        "peak_mw_by_end_use": {key: float(mw_by_end_use[key]) for key in END_USE_NAMES},
        "peak_mw_data_center_non_crypto": float(mw_by_end_use["DAT"] + mw_by_end_use["DAT-AI"]),
        "peak_mw_crypto_mining": float(mw_by_end_use["DAT-CM"]),
        "peak_mw_all_data_center_types": float(sum(mw_by_end_use.values())),
        "status_basis": (
            "NYISO workbook legend: 0 withdrawn; 13 test service; 14 commercial service"
        ),
        "end_use_basis": (
            "NYISO workbook legend: DAT Data Center; AI AI Data center; "
            "CM Cryptocurrency mining data center"
        ),
        "measurement": "requested peak load, not energized load or generation capacity",
        "output_csv": str(output_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    args = parser.parse_args()
    summary = extract(args.input, args.output, args.summary_output)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
