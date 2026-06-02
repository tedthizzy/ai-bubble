"""Match acquired permit and equipment rows to tracker-backed projects."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from bubble.models.base import Provenance

PERMIT_MATCH_FIELDNAMES = [
    "match_id",
    "match_status",
    "match_confidence",
    "match_method",
    "match_reasons",
    "permit_id",
    "facility_name",
    "facility_city",
    "facility_county",
    "facility_state",
    "permit_status",
    "matched_project_id",
    "matched_project_name",
    "matched_project_owner",
    "matched_project_operator",
    "matched_project_city",
    "matched_project_county",
    "matched_project_state",
    "source_uri",
    "source_type",
    "source_id",
    "document_id",
    "content_hash",
    "local_path",
    "record_index",
    "page_or_section",
    "human_review_status",
]

EQUIPMENT_MATCH_FIELDNAMES = [
    "match_id",
    "match_status",
    "match_confidence",
    "match_method",
    "match_reasons",
    "equipment_source_id",
    "plant_name",
    "plant_state",
    "plant_county",
    "equipment_type",
    "equipment_status",
    "capacity_mw",
    "matched_project_id",
    "matched_project_name",
    "matched_project_owner",
    "matched_project_operator",
    "matched_project_city",
    "matched_project_county",
    "matched_project_state",
    "source_uri",
    "source_type",
    "source_id",
    "document_id",
    "content_hash",
    "local_path",
    "record_index",
    "page_or_section",
    "human_review_status",
]

PERMIT_FIELDNAMES = [
    "project_id",
    "permit_id",
    "authority",
    "permit_type",
    "status",
    "application_date",
    "issued_date",
    "capacity_mw",
    "related_generation",
    "public_opposition",
    "notes",
    "source_uri",
    "source_type",
    "source_confidence",
    "human_review_status",
    "page_or_section",
    "content_hash",
]

EQUIPMENT_FIELDNAMES = [
    "project_id",
    "equipment_type",
    "status",
    "vendor",
    "capacity_mw",
    "ordered_date",
    "expected_delivery_date",
    "actual_delivery_date",
    "lead_time_months",
    "notes",
    "source_uri",
    "source_type",
    "source_confidence",
    "human_review_status",
    "page_or_section",
    "content_hash",
]

DATA_CENTER_TERMS = (
    "data center",
    "datacenter",
    "data centre",
    "datacenters",
)

FACILITY_SIGNAL_TERMS = (
    "aligned data",
    "amazon data",
    "compass datacenter",
    "compass datacenters",
    "crusoe",
    "digital realty",
    "equinix",
    "google data",
    "meta platforms",
    "microsoft corp",
    "qts",
    "vantage data",
)

TOKEN_STOPWORDS = {
    "ai",
    "and",
    "center",
    "centers",
    "centre",
    "corp",
    "corporation",
    "data",
    "datacenter",
    "datacenters",
    "digital",
    "energy",
    "facility",
    "fuel",
    "inc",
    "llc",
    "project",
    "solar",
    "the",
}

STATE_ALIASES = {
    "alabama": "AL",
    "al": "AL",
    "alaska": "AK",
    "ak": "AK",
    "arizona": "AZ",
    "az": "AZ",
    "arkansas": "AR",
    "ar": "AR",
    "california": "CA",
    "ca": "CA",
    "colorado": "CO",
    "co": "CO",
    "connecticut": "CT",
    "ct": "CT",
    "delaware": "DE",
    "de": "DE",
    "district of columbia": "DC",
    "dc": "DC",
    "florida": "FL",
    "fl": "FL",
    "georgia": "GA",
    "ga": "GA",
    "hawaii": "HI",
    "hi": "HI",
    "idaho": "ID",
    "id": "ID",
    "illinois": "IL",
    "il": "IL",
    "indiana": "IN",
    "in": "IN",
    "iowa": "IA",
    "ia": "IA",
    "kansas": "KS",
    "ks": "KS",
    "kentucky": "KY",
    "ky": "KY",
    "louisiana": "LA",
    "la": "LA",
    "maine": "ME",
    "me": "ME",
    "maryland": "MD",
    "md": "MD",
    "massachusetts": "MA",
    "ma": "MA",
    "michigan": "MI",
    "mi": "MI",
    "minnesota": "MN",
    "mn": "MN",
    "mississippi": "MS",
    "ms": "MS",
    "missouri": "MO",
    "mo": "MO",
    "montana": "MT",
    "mt": "MT",
    "nebraska": "NE",
    "ne": "NE",
    "nevada": "NV",
    "nv": "NV",
    "new hampshire": "NH",
    "nh": "NH",
    "new jersey": "NJ",
    "nj": "NJ",
    "new mexico": "NM",
    "nm": "NM",
    "new york": "NY",
    "ny": "NY",
    "north carolina": "NC",
    "nc": "NC",
    "north dakota": "ND",
    "nd": "ND",
    "ohio": "OH",
    "oh": "OH",
    "oklahoma": "OK",
    "ok": "OK",
    "oregon": "OR",
    "or": "OR",
    "pennsylvania": "PA",
    "pa": "PA",
    "rhode island": "RI",
    "ri": "RI",
    "south carolina": "SC",
    "sc": "SC",
    "south dakota": "SD",
    "sd": "SD",
    "tennessee": "TN",
    "tn": "TN",
    "texas": "TX",
    "tx": "TX",
    "utah": "UT",
    "ut": "UT",
    "vermont": "VT",
    "vt": "VT",
    "virginia": "VA",
    "va": "VA",
    "washington": "WA",
    "wa": "WA",
    "west virginia": "WV",
    "wv": "WV",
    "wisconsin": "WI",
    "wi": "WI",
    "wyoming": "WY",
    "wy": "WY",
}


@dataclass(frozen=True)
class PhysicalRecordMatchSummary:
    """Summary for deterministic permit/equipment matching."""

    permit_rows_scanned: int
    permit_candidate_rows: int
    permit_matched_rows: int
    permit_loader_rows: int
    equipment_rows_scanned: int
    equipment_candidate_rows: int
    equipment_matched_rows: int
    equipment_loader_rows: int
    equipment_loader_capacity_mw: float
    permit_matches_by_status: dict[str, int]
    equipment_matches_by_status: dict[str, int]
    output_permit_matches_csv: str
    output_equipment_matches_csv: str
    output_permits_csv: str
    output_equipment_csv: str
    workers: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _ProjectCandidate:
    project_id: str
    name: str
    owner: str
    operator: str
    city: str
    county: str
    state: str
    name_tokens: set[str]
    party_tokens: set[str]

    @classmethod
    def from_row(cls, row: dict[str, str]) -> _ProjectCandidate:
        name = row.get("name", "")
        owner = row.get("owner", "")
        operator = row.get("operator", "")
        party_text = " ".join([owner, operator]).strip() or name
        return cls(
            project_id=row.get("project_id", ""),
            name=name,
            owner=owner,
            operator=operator,
            city=_normalize_place(row.get("city", "")),
            county=_normalize_county(row.get("county") or row.get("jurisdiction") or ""),
            state=_normalize_state(row.get("state") or row.get("jurisdiction") or ""),
            name_tokens=_tokens(name),
            party_tokens=_tokens(party_text),
        )


@dataclass(frozen=True)
class _Match:
    project: _ProjectCandidate
    confidence: float
    status: str
    method: str
    reasons: list[str]


def match_physical_records_to_projects(
    *,
    permit_rows_csv: str | Path,
    equipment_rows_csv: str | Path,
    projects_csv: str | Path,
    permit_matches_output: str | Path,
    equipment_matches_output: str | Path,
    permits_output: str | Path,
    equipment_output: str | Path,
    loader_min_confidence: float = 0.72,
    max_workers: int | None = None,
) -> PhysicalRecordMatchSummary:
    """Match source permit/equipment rows to physical project rows."""

    projects = [_ProjectCandidate.from_row(row) for row in _read_csv(Path(projects_csv))]
    projects_by_state: dict[str, list[_ProjectCandidate]] = {}
    for project in projects:
        projects_by_state.setdefault(project.state, []).append(project)

    permit_rows = _read_csv(Path(permit_rows_csv))
    equipment_rows = _read_csv(Path(equipment_rows_csv))
    workers = _resolved_workers(max_workers)

    permit_match_rows: list[dict[str, Any]] = []
    permit_loader_rows: list[dict[str, Any]] = []
    equipment_match_rows: list[dict[str, Any]] = []
    equipment_loader_rows: list[dict[str, Any]] = []

    permit_candidates = [row for row in permit_rows if _permit_row_is_relevant(row)]
    equipment_candidates = [row for row in equipment_rows if _equipment_row_is_relevant(row)]

    with ThreadPoolExecutor(max_workers=workers) as executor:
        for match_row, loader_row in executor.map(
            lambda row: _process_permit_row(row, projects_by_state, loader_min_confidence),
            permit_candidates,
        ):
            permit_match_rows.append(match_row)
            if loader_row is not None:
                permit_loader_rows.append(loader_row)

        for match_row, loader_row in executor.map(
            lambda row: _process_equipment_row(row, projects_by_state, loader_min_confidence),
            equipment_candidates,
        ):
            equipment_match_rows.append(match_row)
            if loader_row is not None:
                equipment_loader_rows.append(loader_row)

    _write_csv(Path(permit_matches_output), PERMIT_MATCH_FIELDNAMES, permit_match_rows)
    _write_csv(Path(equipment_matches_output), EQUIPMENT_MATCH_FIELDNAMES, equipment_match_rows)
    _write_csv(Path(permits_output), PERMIT_FIELDNAMES, permit_loader_rows)
    _write_csv(Path(equipment_output), EQUIPMENT_FIELDNAMES, equipment_loader_rows)

    permit_status_counts = Counter(row["match_status"] for row in permit_match_rows)
    equipment_status_counts = Counter(row["match_status"] for row in equipment_match_rows)
    return PhysicalRecordMatchSummary(
        permit_rows_scanned=len(permit_rows),
        permit_candidate_rows=len(permit_candidates),
        permit_matched_rows=sum(
            1 for row in permit_match_rows if row["match_status"] != "unmatched"
        ),
        permit_loader_rows=len(permit_loader_rows),
        equipment_rows_scanned=len(equipment_rows),
        equipment_candidate_rows=len(equipment_candidates),
        equipment_matched_rows=sum(
            1 for row in equipment_match_rows if row["match_status"] != "unmatched"
        ),
        equipment_loader_rows=len(equipment_loader_rows),
        equipment_loader_capacity_mw=round(
            sum(_optional_float(str(row["capacity_mw"])) or 0.0 for row in equipment_loader_rows),
            3,
        ),
        permit_matches_by_status=dict(sorted(permit_status_counts.items())),
        equipment_matches_by_status=dict(sorted(equipment_status_counts.items())),
        output_permit_matches_csv=str(permit_matches_output),
        output_equipment_matches_csv=str(equipment_matches_output),
        output_permits_csv=str(permits_output),
        output_equipment_csv=str(equipment_output),
        workers=workers,
    )


def write_physical_record_match_summary(
    summary: PhysicalRecordMatchSummary,
    path: str | Path,
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    return output


def _process_permit_row(
    row: dict[str, str],
    projects_by_state: dict[str, list[_ProjectCandidate]],
    loader_min_confidence: float,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    match = _best_project_match(
        name=row.get("FACILITY_NAME", ""),
        city=row.get("CITY", ""),
        county=row.get("COUNTY_NAME", ""),
        state=row.get("STATE", ""),
        projects_by_state=projects_by_state,
    )
    match_row = _permit_match_row(row, match)
    loader_row = (
        _permit_loader_row(row, match)
        if match is not None and match.confidence >= loader_min_confidence
        else None
    )
    return match_row, loader_row


def _process_equipment_row(
    row: dict[str, str],
    projects_by_state: dict[str, list[_ProjectCandidate]],
    loader_min_confidence: float,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    plant = _equipment_plant_name(row)
    match = _best_project_match(
        name=plant,
        city="",
        county=_equipment_county(row),
        state=_equipment_state(row),
        projects_by_state=projects_by_state,
    )
    match_row = _equipment_match_row(row, match)
    loader_row = (
        _equipment_loader_row(row, match)
        if match is not None and match.confidence >= loader_min_confidence
        else None
    )
    return match_row, loader_row


def _best_project_match(
    *,
    name: str,
    city: str,
    county: str,
    state: str,
    projects_by_state: dict[str, list[_ProjectCandidate]],
) -> _Match | None:
    row_name_tokens = _tokens(name)
    row_state = _normalize_state(state)
    row_city = _normalize_place(city)
    row_county = _normalize_county(county)
    candidates = projects_by_state.get(row_state, []) if row_state else []
    best: _Match | None = None
    for project in candidates:
        confidence, reasons = _score_project_match(
            row_name_tokens=row_name_tokens,
            row_city=row_city,
            row_county=row_county,
            project=project,
        )
        if not reasons or confidence < 0.52:
            continue
        confidence = min(round(confidence, 3), 0.99)
        candidate = _Match(
            project=project,
            confidence=confidence,
            status="strong_match" if confidence >= 0.72 else "candidate_match",
            method="deterministic_facility_location_name_v1",
            reasons=reasons,
        )
        if best is None or candidate.confidence > best.confidence:
            best = candidate
    return best


def _score_project_match(
    *,
    row_name_tokens: set[str],
    row_city: str,
    row_county: str,
    project: _ProjectCandidate,
) -> tuple[float, list[str]]:
    confidence = 0.0
    reasons: list[str] = []
    name_score, name_reason = _overlap_score(
        _overlap_ratio(row_name_tokens, project.name_tokens),
        strong_score=0.48,
        partial_score=0.26,
        strong_reason="strong_facility_project_name_overlap",
        partial_reason="partial_facility_project_name_overlap",
    )
    # Owner overlap must use owner tokens that are *distinct* from the project
    # name; otherwise a facility name that matches the project name is credited a
    # second time (party_tokens falls back to the name when owner/operator are
    # absent), double-counting the same signal. Mirrors the queue matcher's
    # name/party separation.
    party_only_tokens = project.party_tokens - project.name_tokens
    party_score, party_reason = _overlap_score(
        _overlap_ratio(row_name_tokens, party_only_tokens),
        strong_score=0.28,
        partial_score=0.16,
        strong_reason="strong_facility_owner_overlap",
        partial_reason="partial_facility_owner_overlap",
    )
    confidence += name_score + party_score
    reasons.extend(reason for reason in [name_reason, party_reason] if reason)
    if row_city and project.city and row_city == project.city:
        confidence += 0.16
        reasons.append("city_match")
    if row_county and project.county and row_county == project.county:
        confidence += 0.18
        reasons.append("county_match")
    if project.state:
        confidence += 0.06
        reasons.append("state_match")
    return confidence, reasons


def _permit_row_is_relevant(row: dict[str, str]) -> bool:
    name = row.get("FACILITY_NAME", "").lower()
    if any(term in name for term in DATA_CENTER_TERMS):
        return True
    return any(term in name for term in FACILITY_SIGNAL_TERMS)


def _equipment_row_is_relevant(row: dict[str, str]) -> bool:
    name = _equipment_plant_name(row).lower()
    if not name or name in {"pname", "plant name"}:
        return False
    if any(term in name for term in DATA_CENTER_TERMS):
        return True
    return any(term in name for term in FACILITY_SIGNAL_TERMS)


def _permit_match_row(row: dict[str, str], match: _Match | None) -> dict[str, Any]:
    match_id = _match_id(row, match.project.project_id if match else "")
    project = match.project if match else None
    return {
        "match_id": f"permit-match:{match_id}",
        "match_status": match.status if match else "unmatched",
        "match_confidence": match.confidence if match else "",
        "match_method": match.method if match else "deterministic_facility_location_name_v1",
        "match_reasons": "|".join(match.reasons) if match else "",
        "permit_id": _permit_id(row),
        "facility_name": row.get("FACILITY_NAME", ""),
        "facility_city": row.get("CITY", ""),
        "facility_county": row.get("COUNTY_NAME", ""),
        "facility_state": row.get("STATE", ""),
        "permit_status": _permit_status(row),
        "matched_project_id": project.project_id if project else "",
        "matched_project_name": project.name if project else "",
        "matched_project_owner": project.owner if project else "",
        "matched_project_operator": project.operator if project else "",
        "matched_project_city": project.city if project else "",
        "matched_project_county": project.county if project else "",
        "matched_project_state": project.state if project else "",
        **_source_fields(row),
        "human_review_status": "pending",
    }


def _equipment_match_row(row: dict[str, str], match: _Match | None) -> dict[str, Any]:
    match_id = _match_id(row, match.project.project_id if match else "")
    project = match.project if match else None
    return {
        "match_id": f"equipment-match:{match_id}",
        "match_status": match.status if match else "unmatched",
        "match_confidence": match.confidence if match else "",
        "match_method": match.method if match else "deterministic_facility_location_name_v1",
        "match_reasons": "|".join(match.reasons) if match else "",
        "equipment_source_id": _equipment_id(row),
        "plant_name": _equipment_plant_name(row),
        "plant_state": _equipment_state(row),
        "plant_county": _equipment_county(row),
        "equipment_type": _equipment_type(row),
        "equipment_status": _equipment_status(row),
        "capacity_mw": _format_number(_equipment_capacity_mw(row)),
        "matched_project_id": project.project_id if project else "",
        "matched_project_name": project.name if project else "",
        "matched_project_owner": project.owner if project else "",
        "matched_project_operator": project.operator if project else "",
        "matched_project_city": project.city if project else "",
        "matched_project_county": project.county if project else "",
        "matched_project_state": project.state if project else "",
        **_source_fields(row),
        "human_review_status": "pending",
    }


def _permit_loader_row(row: dict[str, str], match: _Match) -> dict[str, Any]:
    return {
        "project_id": match.project.project_id,
        "permit_id": _permit_id(row),
        "authority": "EPA ICIS-Air",
        "permit_type": "air_operating_program",
        "status": _permit_status(row),
        "application_date": _date_only(row.get("BEGIN_DATE", "")),
        "issued_date": "",
        "capacity_mw": "",
        "related_generation": "true",
        "public_opposition": "false",
        "notes": _permit_notes(row),
        "source_uri": row.get("source_uri", ""),
        "source_type": row.get("source_type", "epa") or "epa",
        "source_confidence": match.confidence,
        "human_review_status": "pending",
        "page_or_section": _page_or_section(row),
        "content_hash": row.get("content_hash", ""),
    }


def _equipment_loader_row(row: dict[str, str], match: _Match) -> dict[str, Any]:
    return {
        "project_id": match.project.project_id,
        "equipment_type": _equipment_type(row),
        "status": _equipment_status(row),
        "vendor": row.get("Utility name") or row.get("Entity Name") or "",
        "capacity_mw": _format_number(_equipment_capacity_mw(row)),
        "ordered_date": "",
        "expected_delivery_date": _equipment_expected_date(row),
        "actual_delivery_date": _equipment_actual_date(row),
        "lead_time_months": "",
        "notes": _equipment_notes(row),
        "source_uri": row.get("source_uri", ""),
        "source_type": row.get("source_type", "") or "eia",
        "source_confidence": match.confidence,
        "human_review_status": "pending",
        "page_or_section": _page_or_section(row),
        "content_hash": row.get("content_hash", ""),
    }


def _permit_id(row: dict[str, str]) -> str:
    return row.get("PGM_SYS_ID") or row.get("REGISTRY_ID") or _source_row_identity(row)


def _permit_status(row: dict[str, str]) -> str:
    status = " ".join(
        [
            row.get("AIR_OPERATING_STATUS_DESC", ""),
            row.get("AIR_OPERATING_STATUS_CODE", ""),
            row.get("PROGRAM_DESC", ""),
        ]
    ).lower()
    if "withdraw" in status:
        return "withdrawn"
    if "denied" in status:
        return "denied"
    if "draft" in status:
        return "draft"
    if "operating" in status or "issued" in status or "opr" in status:
        return "issued"
    if "pending" in status or "application" in status:
        return "applied"
    return "unknown"


def _permit_notes(row: dict[str, str]) -> str:
    parts = [
        f"facility={row.get('FACILITY_NAME', '')}",
        f"air_class={row.get('AIR_POLLUTANT_CLASS_DESC', '')}",
        f"operating_status={row.get('AIR_OPERATING_STATUS_DESC', '')}",
        f"current_hpv={row.get('CURRENT_HPV', '')}",
    ]
    return "; ".join(part for part in parts if part.split("=", maxsplit=1)[1])


def _equipment_id(row: dict[str, str]) -> str:
    return ":".join(
        part
        for part in [
            row.get("Plant ID") or row.get("DOE/EIA ORIS plant or facility code"),
            row.get("Generator ID") or row.get("Unit ID") or row.get("Unit Code"),
            row.get("record_index"),
        ]
        if part
    ) or _source_row_identity(row)


def _equipment_plant_name(row: dict[str, str]) -> str:
    return row.get("Plant Name") or row.get("Plant name") or row.get("PNAME") or ""


def _equipment_state(row: dict[str, str]) -> str:
    return (
        row.get("Plant State") or row.get("Plant state abbreviation") or row.get("PSTATABB") or ""
    )


def _equipment_county(row: dict[str, str]) -> str:
    return row.get("County") or row.get("Plant county name") or ""


def _equipment_type(row: dict[str, str]) -> str:
    prime_mover = (
        row.get("Prime Mover Code")
        or row.get("Generator prime mover type")
        or row.get("Prime Mover")
        or ""
    ).upper()
    technology = row.get("Technology", "").lower()
    if prime_mover in {"CT", "GT"} or "gas turbine" in technology:
        return "gas_turbine"
    return "generator"


def _equipment_status(row: dict[str, str]) -> str:
    status = (
        row.get("Status") or row.get("Generator status") or row.get("Unit Operational Status") or ""
    ).lower()
    if status in {"op", "operating", "sb", "standby"}:
        return "installed"
    if status in {"ts", "u", "under construction", "planned", "proposed"}:
        return "ordered"
    if "retir" in status:
        return "unknown"
    return "unknown"


def _equipment_capacity_mw(row: dict[str, str]) -> float | None:
    for key in [
        "Nameplate Capacity (MW)",
        "Generator nameplate capacity (MW)",
        "Plant nameplate capacity (MW)",
        "Net Summer Capacity (MW)",
    ]:
        value = _optional_float(row.get(key, ""))
        if value is not None:
            return value
    return None


def _equipment_expected_date(row: dict[str, str]) -> str:
    year = row.get("Planned Operation Year", "")
    month = row.get("Planned Operation Month", "")
    return _year_month_date(year, month)


def _equipment_actual_date(row: dict[str, str]) -> str:
    year = row.get("Operating Year") or row.get("Generator year on-line", "")
    month = row.get("Operating Month", "")
    return _year_month_date(year, month)


def _equipment_notes(row: dict[str, str]) -> str:
    parts = [
        f"plant={_equipment_plant_name(row)}",
        f"prime_mover={row.get('Prime Mover Code') or row.get('Prime Mover') or ''}",
        f"fuel={row.get('Energy Source Code') or row.get('Unit primary fuel') or ''}",
        f"source_equipment_id={_equipment_id(row)}",
    ]
    return "; ".join(part for part in parts if part.split("=", maxsplit=1)[1])


def _source_fields(row: dict[str, str]) -> dict[str, str]:
    return {
        "source_uri": row.get("source_uri", ""),
        "source_type": row.get("source_type", ""),
        "source_id": row.get("source_id", ""),
        "document_id": row.get("document_id", ""),
        "content_hash": row.get("content_hash", ""),
        "local_path": row.get("local_path", ""),
        "record_index": row.get("record_index", ""),
        "page_or_section": _page_or_section(row),
    }


def _match_id(row: dict[str, str], project_id: str) -> str:
    return Provenance.compute_content_hash(
        json.dumps(
            {
                "source_id": row.get("source_id", ""),
                "record_index": row.get("record_index", ""),
                "project_id": project_id,
            },
            sort_keys=True,
        )
    )[:16]


def _source_row_identity(row: dict[str, str]) -> str:
    return f"{row.get('source_id', '')}:{row.get('record_index', '')}"


def _page_or_section(row: dict[str, str]) -> str:
    existing = row.get("page_or_section", "")
    if existing:
        return existing
    local_path = row.get("local_path", "")
    record_index = row.get("record_index", "")
    if local_path and record_index:
        return f"{local_path}#record_index={record_index}"
    return local_path


def _overlap_score(
    overlap: float,
    *,
    strong_score: float,
    partial_score: float,
    strong_reason: str,
    partial_reason: str,
) -> tuple[float, str | None]:
    if overlap >= 0.6:
        return strong_score, strong_reason
    if overlap >= 0.35:
        return partial_score, partial_reason
    return 0.0, None


def _overlap_ratio(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / max(1, min(len(left), len(right)))


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.sub(r"[^a-z0-9]+", " ", value.lower()).split()
        if len(token) > 2 and token not in TOKEN_STOPWORDS
    }


def _normalize_place(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return " ".join(normalized.split())


def _normalize_county(value: str) -> str:
    normalized = _normalize_place(value)
    normalized = re.sub(r"\b(county|parish|borough|city)\b", "", normalized)
    return " ".join(normalized.split())


def _normalize_state(value: str) -> str:
    normalized = value.strip().lower()
    if "," in normalized:
        normalized = normalized.rsplit(",", maxsplit=1)[-1].strip()
    return STATE_ALIASES.get(normalized, normalized.upper() if len(normalized) == 2 else "")


def _optional_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def _format_number(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:g}"


def _date_only(value: str) -> str:
    if not value:
        return ""
    return value[:10]


def _year_month_date(year: str, month: str) -> str:
    if not year or not str(year).isdigit():
        return ""
    month_value = int(month) if str(month).isdigit() else 1
    return f"{int(year):04d}-{month_value:02d}-01"


def _resolved_workers(max_workers: int | None) -> int:
    if max_workers is not None:
        return max(1, max_workers)
    return 32


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return [
            {key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(f)
        ]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
