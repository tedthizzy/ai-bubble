"""Write source-backed physical execution terms from acquired source rows."""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from bubble.ingestion.physical.execution_terms import (
    PhysicalExecutionTerm,
    extract_physical_execution_terms,
)

PHYSICAL_EXECUTION_TERM_FIELDS = [field.name for field in fields(PhysicalExecutionTerm)]

_PROVENANCE_FIELDS = {
    "source_id",
    "source_uri",
    "source_type",
    "retrieved_at",
    "content_hash",
    "local_path",
    "record_index",
    "metadata",
    "document_id",
    "entity_id",
    "project_id",
    "filing_accession",
    "source_row_number",
    "zip_member",
    "sheet_name",
}
_TEXT_FIELD_CANDIDATES = (
    "projectName",
    "Project Name",
    "Name",
    "CommercialName",
    "facility_name",
    "FACILITY_NAME",
    "notes",
    "challenges",
    "sizeNotes",
    "sustainabilityNotes",
    "other_info",
    "advocacy_information",
    "Non-Confidential Summary",
    "Air Permit",
    "GHG Permit",
    "Water Availability",
    "Meets Planning",
    "Meets All Planning",
    "Generation/Fuel 1",
    "Generation/Fuel 2",
    "Generation/Fuel 3",
    "Fuel",
    "Fuel Type",
    "Type/ Fuel",
    "Generation Type",
    "ProjectType",
    "Technology",
    "NET MW 1",
    "NET MW 2",
    "NET MW 3",
    "NET MW POI",
    "Max Summer MW",
    "MAX Summer MW",
    "Capacity (MW)",
    "Capacity",
    "Nameplate Capacity",
    "Requested Maximum Injection Capability (MW)",
    "MW Range of Need",
    "powerCapacityMW",
    "itLoadMW",
    "mw",
    "mw_low",
    "mw_high",
    "power_source",
    "dedicated_power_plant",
    "number_of_generators",
    "community_pushback",
    "resistance_status",
    "PROGRAM_CODE",
    "PROGRAM_DESC",
    "AIR_OPERATING_STATUS_DESC",
    "CURRENT_HPV",
)


@dataclass(frozen=True)
class PhysicalExecutionExtractionSummary:
    """Summary for physical execution term extraction."""

    input_csvs: list[str]
    output_csv: str
    source_rows: int
    terms_written: int
    skipped_missing_source_uri: int
    by_term_type: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_physical_execution_terms_from_csvs(
    input_csvs: list[str | Path],
    output_csv: str | Path,
) -> PhysicalExecutionExtractionSummary:
    """Extract physical execution terms from acquired source-row CSVs."""

    paths = [Path(path) for path in input_csvs]
    terms: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    by_term_type: Counter[str] = Counter()
    source_rows = 0
    skipped_missing_source_uri = 0

    for path in paths:
        if not path.exists():
            continue
        for row in _read_csv(path):
            source_rows += 1
            normalized = _normalize_source_row(row)
            if not normalized.get("source_uri"):
                skipped_missing_source_uri += 1
                continue
            for term in extract_physical_execution_terms(normalized):
                key = (
                    term.term_type,
                    term.value,
                    term.source_uri,
                    term.document_id,
                    term.quote,
                )
                if key in seen:
                    continue
                seen.add(key)
                terms.append(term.to_row())
                by_term_type[term.term_type] += 1

    output = Path(output_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(output, terms)
    return PhysicalExecutionExtractionSummary(
        input_csvs=[str(path) for path in paths],
        output_csv=str(output),
        source_rows=source_rows,
        terms_written=len(terms),
        skipped_missing_source_uri=skipped_missing_source_uri,
        by_term_type=dict(sorted(by_term_type.items())),
    )


def write_physical_execution_extraction_summary(
    summary: PhysicalExecutionExtractionSummary,
    output_json: str | Path,
) -> Path:
    output = Path(output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    return output


def _normalize_source_row(row: dict[str, str]) -> dict[str, str]:
    metadata = _metadata(row)
    return {
        **row,
        "text": _source_text(row),
        "project_name": _first_value(
            row,
            metadata,
            "project_name",
            "projectName",
            "Project Name",
            "Name",
            "CommercialName",
            "facility_name",
            "FACILITY_NAME",
        ),
        "operator": _first_value(
            row,
            metadata,
            "operator",
            "operators",
            "operator_name",
            "Owner/Developer",
            "Developer/Interconnection Customer",
            "Interconnection Customer",
            "Interconnection Customer Name",
            "Owner/Developer",
            "Dev",
        ),
        "jurisdiction": _jurisdiction(row, metadata),
        "authority": _first_value(
            row,
            metadata,
            "authority",
            "regulator",
            "publisher",
            "source_id",
            "Transmission Owner",
            "Utility",
        ),
        "permit_or_docket": _first_value(
            row,
            metadata,
            "permit_or_docket",
            "PGM_SYS_ID",
            "PROGRAM_CODE",
            "Queue Number",
            "Project Number",
            "Generation Interconnection Number",
            "INR",
        ),
    }


def _source_text(row: dict[str, str]) -> str:
    parts: list[str] = []
    for field in _TEXT_FIELD_CANDIDATES:
        value = (row.get(field) or "").strip()
        if value:
            parts.append(f"{field}: {value}")
    metadata = _metadata(row)
    for field in ("title", "publisher", "source_page"):
        value = str(metadata.get(field) or "").strip()
        if value:
            parts.append(f"metadata.{field}: {value}")
    if not parts:
        parts = [
            f"{key}: {value.strip()}"
            for key, value in row.items()
            if key not in _PROVENANCE_FIELDS and value and value.strip()
        ]
    return ". ".join(parts)


def _jurisdiction(row: dict[str, str], metadata: dict[str, Any]) -> str:
    explicit = _first_value(row, metadata, "jurisdiction")
    if explicit:
        return explicit
    state = _first_value(row, metadata, "state", "State", "Project State", "STATE")
    county = _first_value(row, metadata, "county", "County", "PROJECT COUNTY", "COUNTY_NAME")
    city = _first_value(row, metadata, "city", "CITY")
    return ", ".join(part for part in (city, county, state) if part)


def _first_value(row: dict[str, str], metadata: dict[str, Any], *fields_: str) -> str:
    for field in fields_:
        value = (row.get(field) or "").strip()
        if value:
            return value
        metadata_value = metadata.get(field)
        if metadata_value:
            return str(metadata_value).strip()
    return ""


def _metadata(row: dict[str, str]) -> dict[str, Any]:
    raw = row.get("metadata")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return [
            {key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(f)
        ]


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PHYSICAL_EXECUTION_TERM_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
