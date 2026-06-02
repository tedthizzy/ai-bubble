"""Normalize acquired project tracker rows into physical project evidence."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from bubble.ingestion.physical.status_taxonomy import construction_status_from_text


@dataclass(frozen=True)
class TrackerProjectExtractionSummary:
    """Summary of tracker rows converted into source-backed project records."""

    input_csv: str
    output_csv: str
    source_rows: int
    projects_written: int
    skipped_missing_name: int
    capacity_records: int
    capacity_low_mw: float
    capacity_high_mw: float
    investment_records: int
    investment_usd: float
    by_source: dict[str, int]
    by_status: dict[str, int]
    workers: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_tracker_projects(
    input_csv: str | Path,
    output_csv: str | Path,
    *,
    max_workers: int = 32,
) -> TrackerProjectExtractionSummary:
    """Convert acquired tracker rows into physical `projects.csv` records."""

    source = Path(input_csv)
    output = Path(output_csv)
    rows = _read_csv(source)
    worker_count = _worker_count(max_workers=max_workers, row_count=len(rows))
    projects: list[dict[str, Any]] = []
    skipped_missing_name = 0
    capacity_records = 0
    capacity_low_mw = 0.0
    capacity_high_mw = 0.0
    investment_records = 0
    investment_usd = 0.0
    by_source: Counter[str] = Counter()
    by_status: Counter[str] = Counter()

    for project in _project_rows(rows, max_workers=worker_count):
        if project is None:
            skipped_missing_name += 1
            continue
        projects.append(project)
        source_id = str(project.get("source_id") or "unknown")
        by_source[source_id] += 1
        by_status[str(project.get("construction_status") or "unknown")] += 1
        capacity_high = _float_cell(project.get("capacity_mw_high"))
        if capacity_high is not None and capacity_high > 0:
            capacity_records += 1
            capacity_low_mw += _float_cell(project.get("capacity_mw_low")) or capacity_high
            capacity_high_mw += capacity_high
        investment = _float_cell(project.get("investment_usd"))
        if investment is not None and investment > 0:
            investment_records += 1
            investment_usd += investment

    output.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(output, projects)
    summary = TrackerProjectExtractionSummary(
        input_csv=str(source),
        output_csv=str(output),
        source_rows=len(rows),
        projects_written=len(projects),
        skipped_missing_name=skipped_missing_name,
        capacity_records=capacity_records,
        capacity_low_mw=round(capacity_low_mw, 3),
        capacity_high_mw=round(capacity_high_mw, 3),
        investment_records=investment_records,
        investment_usd=round(investment_usd, 2),
        by_source=dict(sorted(by_source.items())),
        by_status=dict(sorted(by_status.items())),
        workers=worker_count,
    )
    return summary


def write_tracker_project_summary(
    summary: TrackerProjectExtractionSummary,
    output_json: str | Path,
) -> Path:
    output = Path(output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    return output


def _project_from_tracker_row(row: dict[str, str]) -> dict[str, Any] | None:
    name = _first_present(row, ["projectName", "facility_name", "name", "Name"])
    if not name:
        return None

    source_id = row.get("source_id", "").strip()
    tracker_key = _first_present(row, ["facility_id", "GlobalID", "OBJECTID", "project_id"])
    project_id = _stable_project_id(source_id, tracker_key or name)
    capacity_low, capacity_high, capacity_basis = _capacity_range(row)
    investment = _investment_usd(row)
    construction_status = _construction_status(row.get("status", ""))
    major_equipment = _major_equipment(row, investment=investment)

    return {
        "project_id": project_id,
        "name": name,
        "asset_type": "data_center_campus",
        "city": row.get("city", ""),
        "county": row.get("county", ""),
        "state": row.get("state", ""),
        "location_lat": _first_present(row, ["lat", "location_lat"]) or "",
        "location_lon": _first_present(row, ["long", "lon", "location_lon"]) or "",
        "address": row.get("address", ""),
        "jurisdiction": _jurisdiction(row),
        "capacity_mw": _cell(capacity_high),
        "capacity_mw_low": _cell(capacity_low),
        "capacity_mw_high": _cell(capacity_high),
        "capacity_basis": capacity_basis,
        "it_load_mw": _first_present(row, ["itLoadMW", "it_load_mw"]) or "",
        "investment_usd": _cell(investment),
        "owner": _first_present(row, ["sponsors", "operator_name", "operators"]) or "",
        "operator": _first_present(row, ["operators", "operator_name"]) or "",
        "tenants": _first_present(row, ["tenants", "tenant"]) or "",
        "permit_status": _permit_status(row.get("status", "")),
        "construction_status": construction_status,
        "announced_in_service_date": _first_present(
            row,
            ["expectedCompletionDate", "expected_date_online"],
        )
        or "",
        "actual_in_service_date": row.get("actualCompletionDate", ""),
        "major_equipment": json.dumps(major_equipment, sort_keys=True),
        "linked_deals": "",
        "source_uri": row.get("source_uri", ""),
        "source_type": row.get("source_type", "project_tracker"),
        "retrieved_at": row.get("retrieved_at", ""),
        "source_id": source_id,
        "document_id": row.get("document_id", ""),
        "content_hash": row.get("content_hash", ""),
        "local_path": row.get("local_path", ""),
        "record_index": row.get("record_index", ""),
        "page_or_section": _page_or_section(row),
        "source_confidence": _source_confidence(row),
        "human_review_status": "pending",
        "tracker_status": row.get("status", ""),
        "tracker_last_updated": _first_present(row, ["lastUpdated", "date_updated"]) or "",
    }


def _project_rows(
    rows: list[dict[str, str]],
    *,
    max_workers: int,
) -> list[dict[str, Any] | None]:
    if not rows:
        return []
    if max_workers <= 1:
        return [_project_from_tracker_row(row) for row in rows]
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(_project_from_tracker_row, rows))


def _capacity_range(row: dict[str, str]) -> tuple[float | None, float | None, str]:
    server_capacity = _float_cell(row.get("powerCapacityMW"))
    if server_capacity is not None and server_capacity > 0:
        return server_capacity, server_capacity, "server_country_power_capacity_mw"

    it_load = _float_cell(row.get("itLoadMW"))
    if it_load is not None and it_load > 0:
        return it_load, it_load, "server_country_it_load_mw"

    low = _float_cell(row.get("mw_low"))
    high = _float_cell(row.get("mw_high"))
    if high is not None and high > 0:
        return low or high, high, "fractracker_mw_high"

    exact = _float_cell(row.get("mw"))
    if exact is not None and exact > 0:
        return exact, exact, "fractracker_mw"

    return None, None, ""


def _investment_usd(row: dict[str, str]) -> float | None:
    direct = _float_cell(row.get("investmentUSD"))
    if direct is not None and direct > 0:
        return direct
    return _money_cell(row.get("project_cost"))


def _major_equipment(row: dict[str, str], *, investment: float | None) -> dict[str, Any]:
    fields = [
        "power_source",
        "dedicated_power_plant",
        "number_of_generators",
        "number_of_buildings",
        "cooling_source",
        "cooling_type",
        "facility_size_sqft",
        "property_size_acres",
        "project_cost",
        "sizerank",
        "community_pushback",
        "resistance_status",
        "information_source",
        "notes",
        "other_info",
        "challenges",
    ]
    equipment: dict[str, Any] = {key: row[key] for key in fields if row.get(key)}
    info_sources = [
        row[key]
        for key in [
            "info_source_1",
            "info_source_2",
            "info_source_3",
            "info_source_4",
            "info_source_5",
            "info_source_6",
            "info_source_7",
            "info_source_8",
        ]
        if row.get(key)
    ]
    if info_sources:
        equipment["info_sources"] = info_sources
    if investment is not None:
        equipment["investment_usd"] = investment
    return equipment


def _construction_status(status: str) -> str:
    return construction_status_from_text(status)


def _permit_status(status: str) -> str:
    normalized = status.strip().lower()
    if "approved" in normalized or "permitted" in normalized:
        return "approved_or_permitted"
    if "proposed" in normalized or "planned" in normalized or "announced" in normalized:
        return "not_confirmed"
    if "operat" in normalized:
        return "in_service"
    return ""


def _source_confidence(row: dict[str, str]) -> str:
    confidence = (row.get("location_confidence") or "").strip().lower()
    if confidence == "high":
        return "0.85"
    if confidence == "medium":
        return "0.75"
    if confidence == "low":
        return "0.6"
    return "0.75"


def _jurisdiction(row: dict[str, str]) -> str:
    return ", ".join(
        value
        for value in [
            row.get("county", "").strip(),
            row.get("state", "").strip(),
        ]
        if value
    )


def _page_or_section(row: dict[str, str]) -> str:
    local_path = row.get("local_path", "")
    record_index = row.get("record_index", "")
    if local_path and record_index:
        return f"{local_path}#record_index={record_index}"
    return local_path or record_index


def _stable_project_id(source_id: str, value: str) -> str:
    return f"{_slug(source_id or 'tracker')}:{_slug(value)}"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return slug.strip("-") or "unknown"


def _money_cell(value: str | None) -> float | None:
    if not value:
        return None
    normalized = value.lower().replace(",", "").strip()
    match = re.search(
        r"\$?\s*([0-9]+(?:\.[0-9]+)?)\s*(trillion|billion|million|m|bn|b)?", normalized
    )
    if not match:
        return None
    amount = float(match.group(1))
    unit = match.group(2) or ""
    multiplier = 1.0
    if unit in {"trillion"}:
        multiplier = 1_000_000_000_000.0
    elif unit in {"billion", "bn", "b"}:
        multiplier = 1_000_000_000.0
    elif unit in {"million", "m"}:
        multiplier = 1_000_000.0
    return amount * multiplier


def _float_cell(value: object | None) -> float | None:
    if value is None:
        return None
    normalized = str(value).strip().replace(",", "")
    if normalized in {"", "N/A", "NA", "None", "null"}:
        return None
    try:
        parsed = float(normalized)
    except ValueError:
        return None
    if parsed < 0:
        return None
    return parsed


def _cell(value: object | None) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(round(value, 6)).rstrip("0").rstrip(".")
    return str(value)


def _first_present(row: dict[str, str], keys: list[str]) -> str | None:
    for key in keys:
        value = row.get(key)
        if value and value.strip():
            return value.strip()
    return None


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return [
            {key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(f)
        ]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _worker_count(*, max_workers: int, row_count: int) -> int:
    if row_count <= 0:
        return 0
    return min(max(1, max_workers), row_count)
