"""Extract source-backed construction observations from normalized project trackers."""

from __future__ import annotations

import csv
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from bubble.ingestion.physical.status_taxonomy import construction_status_from_text

OBSERVATION_FIELDS = [
    "project_id",
    "observed_on",
    "construction_status",
    "progress_pct",
    "visible_indicators",
    "notes",
    "source_uri",
    "source_type",
    "retrieved_at",
    "source_confidence",
    "human_review_status",
    "page_or_section",
    "content_hash",
    "source_id",
    "document_id",
    "local_path",
    "record_index",
]


@dataclass(frozen=True)
class ConstructionObservationExtractionSummary:
    """Summary for source-backed construction observations extracted from projects."""

    input_csv: str
    output_csv: str
    source_rows: int
    observations_written: int
    skipped_missing_project_id: int
    skipped_missing_observed_on: int
    by_status: dict[str, int]
    workers: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_construction_observations_from_projects(
    input_csv: str | Path,
    output_csv: str | Path,
    *,
    max_workers: int = 32,
) -> ConstructionObservationExtractionSummary:
    """Convert normalized project tracker rows into construction observations."""

    source = Path(input_csv)
    output = Path(output_csv)
    rows = _read_csv(source)
    workers = min(max(1, max_workers), max(1, len(rows)))

    observations: list[dict[str, Any]] = []
    skipped_missing_project_id = 0
    skipped_missing_observed_on = 0
    by_status: Counter[str] = Counter()
    seen: set[tuple[str, str, str, str]] = set()

    for observation in _observation_rows(rows, max_workers=workers):
        if observation is None:
            skipped_missing_project_id += 1
            continue
        if not observation.get("observed_on"):
            skipped_missing_observed_on += 1
            continue
        key = (
            str(observation["project_id"]),
            str(observation["observed_on"]),
            str(observation["construction_status"]),
            str(observation["source_uri"]),
        )
        if key in seen:
            continue
        seen.add(key)
        observations.append(observation)
        by_status[str(observation["construction_status"])] += 1

    output.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(output, observations)
    return ConstructionObservationExtractionSummary(
        input_csv=str(source),
        output_csv=str(output),
        source_rows=len(rows),
        observations_written=len(observations),
        skipped_missing_project_id=skipped_missing_project_id,
        skipped_missing_observed_on=skipped_missing_observed_on,
        by_status=dict(sorted(by_status.items())),
        workers=workers,
    )


def write_construction_observation_summary(
    summary: ConstructionObservationExtractionSummary,
    output_json: str | Path,
) -> Path:
    output = Path(output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    return output


def _observation_rows(
    rows: list[dict[str, str]],
    *,
    max_workers: int,
) -> list[dict[str, Any] | None]:
    if not rows:
        return []
    if max_workers <= 1:
        return [_observation_from_project_row(row) for row in rows]
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(_observation_from_project_row, rows))


def _observation_from_project_row(row: dict[str, str]) -> dict[str, Any] | None:
    project_id = row.get("project_id", "").strip()
    if not project_id:
        return None
    observed_on = _observed_on(row)
    status = row.get("construction_status", "").strip() or _status_from_tracker(row)
    indicators = _visible_indicators(row, status=status)
    return {
        "project_id": project_id,
        "observed_on": observed_on or "",
        "construction_status": status or "announced",
        "progress_pct": "",
        "visible_indicators": "|".join(indicators),
        "notes": _notes(row, status=status),
        "source_uri": row.get("source_uri", ""),
        "source_type": row.get("source_type", "project_tracker"),
        "retrieved_at": row.get("retrieved_at", ""),
        "source_confidence": row.get("source_confidence", ""),
        "human_review_status": row.get("human_review_status", "pending") or "pending",
        "page_or_section": _page_or_section(row),
        "content_hash": row.get("content_hash", ""),
        "source_id": row.get("source_id", ""),
        "document_id": row.get("document_id", ""),
        "local_path": row.get("local_path", ""),
        "record_index": row.get("record_index", ""),
    }


def _observed_on(row: dict[str, str]) -> str | None:
    for value in (
        row.get("tracker_last_updated", ""),
        row.get("retrieved_at", ""),
        row.get("actual_in_service_date", ""),
    ):
        parsed = _date_token(value)
        if parsed is not None:
            return parsed.isoformat()
    return None


def _date_token(value: str | None) -> date | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if "T" in normalized:
        normalized = normalized.split("T", maxsplit=1)[0]
    if len(normalized) == 7:
        normalized = f"{normalized}-01"
    if len(normalized) == 4 and normalized.isdigit():
        normalized = f"{normalized}-01-01"
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        return None


def _status_from_tracker(row: dict[str, str]) -> str:
    return construction_status_from_text(row.get("tracker_status"))


def _visible_indicators(row: dict[str, str], *, status: str) -> list[str]:
    indicators = [f"tracker_status:{row.get('tracker_status') or status}"]
    for field in ("permit_status", "announced_in_service_date", "actual_in_service_date"):
        value = row.get(field, "")
        if value:
            indicators.append(f"{field}:{value}")
    capacity = row.get("capacity_mw", "")
    if capacity:
        indicators.append(f"capacity_mw:{capacity}")
    return indicators


def _notes(row: dict[str, str], *, status: str) -> str:
    name = row.get("name", "").strip() or row.get("project_id", "").strip()
    tracker_status = row.get("tracker_status", "").strip()
    return (
        f"Tracker construction status observation for {name}: {status}. "
        f"Raw tracker status: {tracker_status or 'not provided'}."
    )


def _page_or_section(row: dict[str, str]) -> str:
    base = row.get("page_or_section", "").strip()
    if base:
        return f"{base} construction status"
    local_path = row.get("local_path", "").strip()
    record_index = row.get("record_index", "").strip()
    if local_path and record_index:
        return f"{local_path}#record_index={record_index} construction status"
    return "project tracker construction status"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return [
            {key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(f)
        ]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OBSERVATION_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
