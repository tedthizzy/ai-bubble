"""Match acquired data-center queue rows to tracker-backed physical projects."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from bubble.analysis.physical_capacity import (
    _queue_capacity_mw,
    _queue_data_center_relationship,
    _queue_project_example,
    _queue_record_in_scope,
    _queue_record_is_data_center_related,
    _queue_region,
)
from bubble.models.base import Provenance

MATCH_FIELDNAMES = [
    "match_id",
    "match_status",
    "match_confidence",
    "match_method",
    "match_reasons",
    "queue_id",
    "queue_project_name",
    "queue_region",
    "queue_relationship",
    "queue_capacity_mw",
    "queue_status",
    "requested_in_service_date",
    "queue_customer",
    "queue_county",
    "queue_state",
    "point_of_interconnection",
    "data_center_load_description",
    "matched_project_id",
    "matched_project_name",
    "matched_project_owner",
    "matched_project_operator",
    "matched_project_county",
    "matched_project_state",
    "matched_project_capacity_mw",
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

QUEUE_FIELDNAMES = [
    "project_id",
    "queue_id",
    "region",
    "status",
    "requested_mw",
    "firm_service_mw",
    "requested_in_service_date",
    "expected_in_service_date",
    "delay_months",
    "network_upgrade_cost_usd",
    "study_phase",
    "notes",
    "source_uri",
    "source_type",
    "source_confidence",
    "human_review_status",
    "page_or_section",
    "content_hash",
]

PROJECT_FIELDNAMES = [
    "project_id",
    "name",
    "asset_type",
    "city",
    "county",
    "state",
    "location_lat",
    "location_lon",
    "address",
    "jurisdiction",
    "capacity_mw",
    "capacity_mw_low",
    "capacity_mw_high",
    "capacity_basis",
    "it_load_mw",
    "investment_usd",
    "owner",
    "operator",
    "tenants",
    "permit_status",
    "construction_status",
    "announced_in_service_date",
    "actual_in_service_date",
    "major_equipment",
    "linked_deals",
    "source_uri",
    "source_type",
    "retrieved_at",
    "source_id",
    "document_id",
    "content_hash",
    "local_path",
    "record_index",
    "page_or_section",
    "source_confidence",
    "human_review_status",
    "tracker_status",
    "tracker_last_updated",
]

TOKEN_STOPWORDS = {
    "ai",
    "aka",
    "and",
    "center",
    "centers",
    "centre",
    "co",
    "company",
    "county",
    "data",
    "datacenter",
    "digital",
    "facility",
    "holdings",
    "inc",
    "interconnection",
    "llc",
    "ltd",
    "project",
    "proposed",
    "the",
}

TOKEN_ALIASES = {
    "onovan": {"donovan"},
    "terawulf": {"wulf"},
}

STATE_ALIASES = {
    "alabama": "AL",
    "al": "AL",
    "alaska": "AK",
    "ak": "AK",
    "arkansas": "AR",
    "ar": "AR",
    "arizona": "AZ",
    "az": "AZ",
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
    "mississippi": "MS",
    "ms": "MS",
    "minnesota": "MN",
    "mn": "MN",
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
class QueueProjectMatchSummary:
    """Summary for deterministic queue-to-project matching."""

    queue_rows_scanned: int
    data_center_queue_rows: int
    matched_rows: int
    strong_matches: int
    candidate_matches: int
    unmatched_rows: int
    loader_queue_rows: int
    queue_derived_projects: int
    queue_derived_queue_rows: int
    matched_capacity_mw: float
    loader_queue_capacity_mw: float
    matches_by_status: dict[str, int]
    matches_by_relationship: dict[str, int]
    output_matches_csv: str
    output_queues_csv: str
    output_queue_projects_csv: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def match_data_center_queues_to_projects(
    *,
    queue_rows_csv: str | Path,
    projects_csv: str | Path,
    matches_output: str | Path,
    queues_output: str | Path,
    queue_projects_output: str | Path | None = None,
    loader_min_confidence: float = 0.72,
) -> QueueProjectMatchSummary:
    """Match data-center-related interconnection rows to project tracker rows."""

    projects = [_ProjectCandidate.from_row(row) for row in _read_csv(Path(projects_csv))]
    queue_rows = _read_csv(Path(queue_rows_csv))
    match_rows: list[dict[str, Any]] = []
    loader_rows: list[dict[str, Any]] = []
    queue_project_rows: dict[str, dict[str, Any]] = {}
    data_center_rows = 0
    matched_capacity_mw = 0.0
    loader_capacity_mw = 0.0
    queue_derived_queue_rows = 0
    status_counts: Counter[str] = Counter()
    relationship_counts: Counter[str] = Counter()

    for row in queue_rows:
        if not _queue_record_in_scope(row):
            continue
        capacity = _queue_capacity_mw(row)
        if capacity is None:
            continue
        if not _queue_record_is_data_center_related(row):
            continue

        data_center_rows += 1
        region = _queue_region(row)
        relationship = _queue_data_center_relationship(row)
        example = _queue_project_example(
            row,
            capacity_mw=capacity,
            region=region,
            relationship=relationship,
        )
        match = _best_project_match(example, projects)
        match_row = _match_row(row, example, match)
        match_rows.append(match_row)
        status_counts[match_row["match_status"]] += 1
        relationship_counts[relationship] += 1

        if match is not None:
            matched_capacity_mw += capacity
        if match is not None and match.confidence >= loader_min_confidence:
            loader_rows.append(_loader_queue_row(row, example, match))
            loader_capacity_mw += capacity
        elif match is None and _should_create_queue_project(relationship) and queue_projects_output:
            project_id = _queue_derived_project_id(example)
            _upsert_queue_project_row(
                queue_project_rows,
                project_id=project_id,
                source_row=row,
                queue=example,
            )
            loader_rows.append(
                _loader_queue_row_for_project(
                    row,
                    example,
                    project_id=project_id,
                    source_confidence=0.72,
                )
            )
            loader_capacity_mw += capacity
            queue_derived_queue_rows += 1

    _write_csv(Path(matches_output), MATCH_FIELDNAMES, match_rows)
    _write_csv(Path(queues_output), QUEUE_FIELDNAMES, loader_rows)
    if queue_projects_output:
        _write_csv(
            Path(queue_projects_output),
            PROJECT_FIELDNAMES,
            list(queue_project_rows.values()),
        )
    return QueueProjectMatchSummary(
        queue_rows_scanned=len(queue_rows),
        data_center_queue_rows=data_center_rows,
        matched_rows=sum(1 for row in match_rows if row["match_status"] != "unmatched"),
        strong_matches=status_counts["strong_match"],
        candidate_matches=status_counts["candidate_match"],
        unmatched_rows=status_counts["unmatched"],
        loader_queue_rows=len(loader_rows),
        queue_derived_projects=len(queue_project_rows),
        queue_derived_queue_rows=queue_derived_queue_rows,
        matched_capacity_mw=round(matched_capacity_mw, 3),
        loader_queue_capacity_mw=round(loader_capacity_mw, 3),
        matches_by_status=dict(sorted(status_counts.items())),
        matches_by_relationship=dict(sorted(relationship_counts.items())),
        output_matches_csv=str(matches_output),
        output_queues_csv=str(queues_output),
        output_queue_projects_csv=str(queue_projects_output) if queue_projects_output else None,
    )


def write_queue_project_match_summary(
    summary: QueueProjectMatchSummary,
    path: str | Path,
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    return output


@dataclass(frozen=True)
class _ProjectCandidate:
    project_id: str
    name: str
    owner: str
    operator: str
    county: str
    state: str
    capacity_mw: float | None
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
            county=_normalize_county(row.get("county") or row.get("jurisdiction") or ""),
            state=_normalize_state(row.get("state") or row.get("jurisdiction") or ""),
            capacity_mw=_optional_float(row.get("capacity_mw_high") or row.get("capacity_mw")),
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


def _best_project_match(
    queue: dict[str, Any],
    projects: list[_ProjectCandidate],
) -> _Match | None:
    is_direct_load = queue["relationship"] == "direct_data_center_load"
    queue_name_tokens = _tokens(str(queue["project_name"]))
    queue_party_tokens = _tokens(str(queue["customer"]))
    queue_state = _normalize_state(str(queue["state"]))
    queue_county = _normalize_county(str(queue["county"]))
    queue_capacity = _optional_float(str(queue["capacity_mw"]))
    best: _Match | None = None

    for project in projects:
        if queue_state and project.state and queue_state != project.state:
            continue
        name_overlap = _overlap_ratio(queue_name_tokens, project.name_tokens)
        if not is_direct_load and name_overlap < 0.6:
            continue
        confidence, reasons = _score_project_match(
            queue_name_tokens=queue_name_tokens,
            queue_party_tokens=queue_party_tokens,
            queue_county=queue_county,
            queue_state=queue_state,
            queue_capacity=queue_capacity,
            project=project,
        )
        if not reasons or confidence < 0.48:
            continue
        if not is_direct_load:
            reasons.append("supporting_queue_project_name_overlap")
        confidence = min(round(confidence, 3), 0.99)
        status = "strong_match" if confidence >= 0.72 else "candidate_match"
        candidate = _Match(
            project=project,
            confidence=confidence,
            status=status,
            method="deterministic_name_party_location_capacity_v1",
            reasons=reasons,
        )
        if best is None or candidate.confidence > best.confidence:
            best = candidate

    return best


def _score_project_match(
    *,
    queue_name_tokens: set[str],
    queue_party_tokens: set[str],
    queue_county: str,
    queue_state: str,
    queue_capacity: float | None,
    project: _ProjectCandidate,
) -> tuple[float, list[str]]:
    confidence = 0.0
    reasons: list[str] = []

    name_score, name_reason = _overlap_score(
        _overlap_ratio(queue_name_tokens, project.name_tokens),
        strong_score=0.5,
        partial_score=0.28,
        strong_reason="strong_name_overlap",
        partial_reason="partial_name_overlap",
    )
    party_score, party_reason = (0.0, None)
    if queue_party_tokens and not queue_party_tokens.issubset(queue_name_tokens):
        party_score, party_reason = _overlap_score(
            _overlap_ratio(queue_party_tokens, project.party_tokens),
            strong_score=0.3,
            partial_score=0.18,
            strong_reason="strong_customer_owner_overlap",
            partial_reason="partial_customer_owner_overlap",
        )
    confidence += name_score + party_score
    reasons.extend(reason for reason in [name_reason, party_reason] if reason)

    if queue_county and project.county and queue_county == project.county:
        confidence += 0.22
        reasons.append("county_match")
    if queue_state and project.state and queue_state == project.state:
        confidence += 0.08
        reasons.append("state_match")

    capacity_score = _capacity_score(queue_capacity, project.capacity_mw)
    if capacity_score:
        confidence += capacity_score
        reasons.append("capacity_close")
    elif _capacity_mismatch(queue_capacity, project.capacity_mw):
        if _strong_identity_match_with_capacity_expansion(
            reasons,
            queue_county=queue_county,
            queue_state=queue_state,
            project=project,
        ):
            confidence -= 0.06
            reasons.append("capacity_mismatch_softened_by_name_location")
        else:
            confidence -= 0.12
        reasons.append("capacity_mismatch_penalty")
    return confidence, reasons


def _strong_identity_match_with_capacity_expansion(
    reasons: list[str],
    *,
    queue_county: str,
    queue_state: str,
    project: _ProjectCandidate,
) -> bool:
    return (
        "strong_name_overlap" in reasons
        and bool(queue_county)
        and bool(project.county)
        and queue_county == project.county
        and bool(queue_state)
        and bool(project.state)
        and queue_state == project.state
    )


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


def _match_row(
    source_row: dict[str, str],
    queue: dict[str, Any],
    match: _Match | None,
) -> dict[str, Any]:
    match_id = Provenance.compute_content_hash(
        json.dumps(
            {
                "source_id": source_row.get("source_id", ""),
                "record_index": source_row.get("record_index", ""),
                "queue_id": queue.get("queue_id", ""),
                "project_id": match.project.project_id if match else "",
            },
            sort_keys=True,
        )
    )[:16]
    project = match.project if match else None
    return {
        "match_id": f"queue-match:{match_id}",
        "match_status": match.status if match else "unmatched",
        "match_confidence": match.confidence if match else "",
        "match_method": match.method if match else "deterministic_name_party_location_capacity_v1",
        "match_reasons": "|".join(match.reasons) if match else "",
        "queue_id": queue["queue_id"],
        "queue_project_name": queue["project_name"],
        "queue_region": queue["region"],
        "queue_relationship": queue["relationship"],
        "queue_capacity_mw": queue["capacity_mw"],
        "queue_status": queue["status"],
        "requested_in_service_date": queue["requested_in_service_date"],
        "queue_customer": queue["customer"],
        "queue_county": queue["county"],
        "queue_state": queue["state"],
        "point_of_interconnection": queue["point_of_interconnection"],
        "data_center_load_description": queue["data_center_load_description"],
        "matched_project_id": project.project_id if project else "",
        "matched_project_name": project.name if project else "",
        "matched_project_owner": project.owner if project else "",
        "matched_project_operator": project.operator if project else "",
        "matched_project_county": project.county if project else "",
        "matched_project_state": project.state if project else "",
        "matched_project_capacity_mw": project.capacity_mw if project else "",
        "source_uri": source_row.get("source_uri", ""),
        "source_type": source_row.get("source_type", ""),
        "source_id": source_row.get("source_id", ""),
        "document_id": source_row.get("document_id", ""),
        "content_hash": source_row.get("content_hash", ""),
        "local_path": source_row.get("local_path", ""),
        "record_index": source_row.get("record_index", ""),
        "page_or_section": _page_or_section(source_row),
        "human_review_status": "pending",
    }


def _loader_queue_row(
    source_row: dict[str, str],
    queue: dict[str, Any],
    match: _Match,
) -> dict[str, Any]:
    return _loader_queue_row_for_project(
        source_row,
        queue,
        project_id=match.project.project_id,
        source_confidence=match.confidence,
    )


def _loader_queue_row_for_project(
    source_row: dict[str, str],
    queue: dict[str, Any],
    *,
    project_id: str,
    source_confidence: float,
) -> dict[str, Any]:
    status = _normalized_interconnection_status(str(queue["status"]))
    firm_service_mw = queue["capacity_mw"] if status == "agreement_executed" else ""
    return {
        "project_id": project_id,
        "queue_id": queue["queue_id"]
        or f"{source_row.get('source_id')}:{source_row.get('record_index')}",
        "region": str(queue["region"]).lower().replace("-", "_"),
        "status": status,
        "requested_mw": _format_number(queue["capacity_mw"]),
        "firm_service_mw": _format_number(firm_service_mw) if firm_service_mw else "",
        "requested_in_service_date": _date_only(str(queue["requested_in_service_date"])),
        "expected_in_service_date": _date_only(str(queue["requested_in_service_date"])),
        "delay_months": "",
        "network_upgrade_cost_usd": "",
        "study_phase": str(queue["status"]),
        "notes": queue["data_center_load_description"],
        "source_uri": source_row.get("source_uri", ""),
        "source_type": "grid_interconnection_queue",
        "source_confidence": source_confidence,
        "human_review_status": "pending",
        "page_or_section": _page_or_section(source_row),
        "content_hash": source_row.get("content_hash", ""),
    }


def _queue_derived_project_id(queue: dict[str, Any]) -> str:
    basis_parts = {
        "project_name": str(queue.get("project_name", "")).strip().lower(),
        "county": _normalize_county(str(queue.get("county", ""))),
        "state": _normalize_state(str(queue.get("state", ""))),
    }
    if queue.get("relationship") == "supporting_generation_for_data_center_load":
        basis_parts.update(
            {
                "customer": str(queue.get("customer", "")).strip().lower(),
                "point_of_interconnection": str(queue.get("point_of_interconnection", ""))
                .strip()
                .lower(),
                "relationship": str(queue.get("relationship", "")),
            }
        )
    basis = json.dumps(basis_parts, sort_keys=True)
    return f"queue-project:{Provenance.compute_content_hash(basis)[:16]}"


def _should_create_queue_project(relationship: str) -> bool:
    return relationship in {
        "direct_data_center_load",
        "supporting_generation_for_data_center_load",
    }


def _upsert_queue_project_row(
    rows: dict[str, dict[str, Any]],
    *,
    project_id: str,
    source_row: dict[str, str],
    queue: dict[str, Any],
) -> None:
    capacity = _optional_float(str(queue.get("capacity_mw")))
    customer = str(queue.get("customer") or "").strip()
    if project_id not in rows:
        rows[project_id] = _queue_project_row(
            source_row,
            queue,
            project_id=project_id,
            capacity=capacity,
        )
        return

    existing = rows[project_id]
    existing_capacity = _optional_float(str(existing.get("capacity_mw")))
    if capacity and (existing_capacity is None or capacity > existing_capacity):
        formatted_capacity = _format_number(capacity)
        existing["capacity_mw"] = formatted_capacity
        existing["capacity_mw_high"] = formatted_capacity
        existing["announced_in_service_date"] = _date_only(
            str(queue.get("requested_in_service_date", ""))
        )
    if customer:
        existing["owner"] = _merge_pipe_values(str(existing.get("owner", "")), customer)
        existing["operator"] = _merge_pipe_values(str(existing.get("operator", "")), customer)


def _queue_project_row(
    source_row: dict[str, str],
    queue: dict[str, Any],
    *,
    project_id: str,
    capacity: float | None,
) -> dict[str, Any]:
    customer = str(queue.get("customer") or "").strip()
    county = str(queue.get("county") or "").strip()
    state = _normalize_state(str(queue.get("state") or ""))
    capacity_value = _format_number(capacity) if capacity is not None else ""
    requested_date = _date_only(str(queue.get("requested_in_service_date", "")))
    relationship = str(queue.get("relationship") or "")
    return {
        "project_id": project_id,
        "name": str(queue.get("project_name") or project_id),
        "asset_type": _queue_project_asset_type(relationship),
        "city": "",
        "county": county,
        "state": state,
        "location_lat": "",
        "location_lon": "",
        "address": "",
        "jurisdiction": ", ".join(part for part in [county, state] if part),
        "capacity_mw": capacity_value,
        "capacity_mw_low": capacity_value,
        "capacity_mw_high": capacity_value,
        "capacity_basis": _queue_project_capacity_basis(relationship),
        "it_load_mw": "",
        "investment_usd": "",
        "owner": customer,
        "operator": customer,
        "tenants": "",
        "permit_status": "",
        "construction_status": "announced",
        "announced_in_service_date": requested_date,
        "actual_in_service_date": "",
        "major_equipment": json.dumps(
            {
                "queue_id": queue.get("queue_id", ""),
                "queue_relationship": relationship,
                "queue_status": queue.get("status", ""),
                "point_of_interconnection": queue.get("point_of_interconnection", ""),
                "data_center_load_description": queue.get("data_center_load_description", ""),
            },
            sort_keys=True,
        ),
        "linked_deals": "",
        "source_uri": source_row.get("source_uri", ""),
        "source_type": "grid_interconnection_queue",
        "retrieved_at": source_row.get("retrieved_at", ""),
        "source_id": source_row.get("source_id", ""),
        "document_id": source_row.get("document_id", ""),
        "content_hash": source_row.get("content_hash", ""),
        "local_path": source_row.get("local_path", ""),
        "record_index": source_row.get("record_index", ""),
        "page_or_section": _page_or_section(source_row),
        "source_confidence": 0.72,
        "human_review_status": "pending",
        "tracker_status": _queue_project_tracker_status(relationship),
        "tracker_last_updated": "",
    }


def _queue_project_asset_type(relationship: str) -> str:
    if relationship == "supporting_generation_for_data_center_load":
        return "power_generation"
    return "data_center_campus"


def _queue_project_capacity_basis(relationship: str) -> str:
    if relationship == "supporting_generation_for_data_center_load":
        return "generation_queue_requested_mw"
    return "grid_queue_requested_mw"


def _queue_project_tracker_status(relationship: str) -> str:
    if relationship == "supporting_generation_for_data_center_load":
        return "queue_derived_supporting_generation"
    return "queue_derived_direct_load"


def _merge_pipe_values(existing: str, value: str) -> str:
    values = [item.strip() for item in existing.split("|") if item.strip()]
    if value not in values:
        values.append(value)
    return "|".join(values)


def _normalized_interconnection_status(value: str) -> str:
    lower = value.lower()
    if "withdraw" in lower:
        return "withdrawn"
    if "in service" in lower or lower == "i/s":
        return "in_service"
    if "ia" in lower or "agreement" in lower:
        return "agreement_executed"
    if "facility" in lower or "fis" in lower:
        return "facility_study"
    if "study" in lower or lower.isdigit():
        return "study"
    return "unknown"


def _capacity_score(queue_capacity: float | None, project_capacity: float | None) -> float:
    if not queue_capacity or not project_capacity:
        return 0.0
    ratio = abs(queue_capacity - project_capacity) / max(queue_capacity, project_capacity)
    if ratio <= 0.1:
        return 0.16
    if ratio <= 0.25:
        return 0.1
    if ratio <= 0.5:
        return 0.05
    return 0.0


def _capacity_mismatch(queue_capacity: float | None, project_capacity: float | None) -> bool:
    if not queue_capacity or not project_capacity:
        return False
    return abs(queue_capacity - project_capacity) / max(queue_capacity, project_capacity) > 0.5


def _overlap_ratio(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / max(1, min(len(left), len(right)))


def _tokens(value: str) -> set[str]:
    tokens = {
        token
        for token in re.sub(r"[^a-z0-9]+", " ", value.lower()).split()
        if len(token) > 2 and token not in TOKEN_STOPWORDS
    }
    for token in list(tokens):
        tokens.update(TOKEN_ALIASES.get(token, set()))
    return tokens


def _normalize_county(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower())
    normalized = re.sub(r"\b(county|parish|borough)\b", "", normalized)
    return " ".join(normalized.split())


def _normalize_state(value: str) -> str:
    normalized = value.strip().lower()
    if "," in normalized:
        normalized = normalized.rsplit(",", maxsplit=1)[-1].strip()
    if normalized in STATE_ALIASES:
        return STATE_ALIASES[normalized]
    if len(normalized) == 2:
        return normalized.upper()
    return ""


def _optional_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def _date_only(value: str) -> str:
    if not value or value.upper() in {"N/A", "NA", "NONE"}:
        return ""
    normalized = value.strip()
    try:
        return date.fromisoformat(normalized[:10]).isoformat()
    except ValueError:
        pass
    for fmt in ("%m-%Y", "%Y-%m"):
        try:
            return datetime.strptime(normalized, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def _format_number(value: Any) -> str:
    number = _optional_float(str(value))
    if number is None:
        return ""
    if number.is_integer():
        return str(int(number))
    return str(number)


def _page_or_section(row: dict[str, str]) -> str:
    local_path = row.get("local_path", "")
    record_index = row.get("record_index", "")
    if local_path and record_index:
        return f"{local_path}#record_index={record_index}"
    return local_path or record_index


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return [
            {key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(f)
        ]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
