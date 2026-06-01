"""Source-backed physical capacity rollups from acquired public infrastructure rows."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

REGION_ALIASES = {
    "AECI": "AECI",
    "CAISO": "CAISO",
    "CISO": "CAISO",
    "ERCOT": "ERCOT",
    "ERCO": "ERCOT",
    "ISNE": "ISO-NE",
    "ISO-NE": "ISO-NE",
    "MISO": "MISO",
    "NYIS": "NYISO",
    "NYISO": "NYISO",
    "PJM": "PJM",
    "SPP": "SPP",
    "SWPP": "SPP",
}

STATE_ALIASES = {
    "ALABAMA": "AL",
    "ALASKA": "AK",
    "ARIZONA": "AZ",
    "ARKANSAS": "AR",
    "CALIFORNIA": "CA",
    "COLORADO": "CO",
    "CONNECTICUT": "CT",
    "DELAWARE": "DE",
    "DISTRICT OF COLUMBIA": "DC",
    "FLORIDA": "FL",
    "GEORGIA": "GA",
    "HAWAII": "HI",
    "IDAHO": "ID",
    "ILLINOIS": "IL",
    "INDIANA": "IN",
    "IOWA": "IA",
    "KANSAS": "KS",
    "KENTUCKY": "KY",
    "LOUISIANA": "LA",
    "MAINE": "ME",
    "MARYLAND": "MD",
    "MASSACHUSETTS": "MA",
    "MICHIGAN": "MI",
    "MINNESOTA": "MN",
    "MISSISSIPPI": "MS",
    "MISSOURI": "MO",
    "MONTANA": "MT",
    "NEBRASKA": "NE",
    "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH",
    "NEW JERSEY": "NJ",
    "NEW MEXICO": "NM",
    "NEW YORK": "NY",
    "NORTH CAROLINA": "NC",
    "NORTH DAKOTA": "ND",
    "OHIO": "OH",
    "OKLAHOMA": "OK",
    "OREGON": "OR",
    "PENNSYLVANIA": "PA",
    "RHODE ISLAND": "RI",
    "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD",
    "TENNESSEE": "TN",
    "TEXAS": "TX",
    "UTAH": "UT",
    "VERMONT": "VT",
    "VIRGINIA": "VA",
    "WASHINGTON": "WA",
    "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI",
    "WYOMING": "WY",
}
GENERIC_PROJECT_TERMS = {
    "ai",
    "campus",
    "center",
    "centre",
    "cloud",
    "co",
    "company",
    "corp",
    "corporation",
    "data",
    "datacenter",
    "digital",
    "hyperscale",
    "inc",
    "llc",
    "lp",
    "partners",
    "platforms",
    "project",
    "realty",
    "the",
}
DATA_CENTER_QUEUE_TERMS = (
    "data center",
    "datacenter",
    "hyperscale",
    "artificial intelligence",
    "ai data",
    "compute data",
)


@dataclass(frozen=True)
class PhysicalCapacitySummary:
    """Deterministic physical capacity metrics tied to acquired source rows."""

    generated_at: str
    data_dirs: list[str]
    queue_records_scanned: int
    queue_capacity_records: int
    queue_capacity_mw: float
    queue_capacity_by_source_mw: dict[str, float]
    queue_capacity_by_region_mw: dict[str, float]
    data_center_queue_records: int
    data_center_queue_capacity_mw: float
    data_center_queue_capacity_by_region_mw: dict[str, float]
    data_center_queue_capacity_by_relationship_mw: dict[str, float]
    top_data_center_queue_projects: list[dict[str, Any]]
    tracker_project_records_scanned: int
    tracker_capacity_records: int
    tracker_capacity_low_mw: float
    tracker_capacity_high_mw: float
    tracker_it_load_mw: float
    tracker_investment_usd: float
    tracker_capacity_by_source_mw: dict[str, float]
    tracker_capacity_by_status_mw: dict[str, float]
    tracker_investment_by_source_usd: dict[str, float]
    tracker_distinct_projects: int
    tracker_duplicate_groups: int
    tracker_duplicate_rows_collapsed: int
    tracker_distinct_capacity_records: int
    tracker_distinct_capacity_low_mw: float
    tracker_distinct_capacity_high_mw: float
    tracker_distinct_pipeline_capacity_high_mw: float
    tracker_distinct_operating_capacity_high_mw: float
    tracker_distinct_cancelled_capacity_high_mw: float
    tracker_distinct_investment_usd: float
    tracker_distinct_capacity_by_status_mw: dict[str, float]
    tracker_distinct_capacity_by_state_mw: dict[str, float]
    equipment_records_scanned: int
    equipment_capacity_records: int
    eia_operating_capacity_mw: float
    eia_planned_capacity_mw: float
    eia_retired_capacity_mw: float
    eia_canceled_or_postponed_capacity_mw: float
    egrid_generator_capacity_mw: float
    equipment_capacity_by_source_mw: dict[str, float]
    eia_operating_capacity_by_region_mw: dict[str, float]
    eia_planned_capacity_by_region_mw: dict[str, float]
    physical_stress_indicators: list[dict[str, Any]]
    source_documents: list[dict[str, str]]
    skipped_rows: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_physical_capacity_summary(  # noqa: PLR0912, PLR0915
    data_dirs: Sequence[str | Path],
) -> PhysicalCapacitySummary:
    """Compute conservative physical capacity rollups from acquired queue/equipment rows."""

    roots = [Path(data_dir) for data_dir in data_dirs]
    queue_records_scanned = 0
    queue_capacity_records = 0
    queue_capacity_mw = 0.0
    queue_capacity_by_source: defaultdict[str, float] = defaultdict(float)
    queue_capacity_by_region: defaultdict[str, float] = defaultdict(float)
    data_center_queue_records = 0
    data_center_queue_capacity_mw = 0.0
    data_center_queue_capacity_by_region: defaultdict[str, float] = defaultdict(float)
    data_center_queue_capacity_by_relationship: defaultdict[str, float] = defaultdict(float)
    data_center_queue_projects: list[dict[str, Any]] = []
    tracker_project_records_scanned = 0
    tracker_capacity_records = 0
    tracker_capacity_low_mw = 0.0
    tracker_capacity_high_mw = 0.0
    tracker_it_load_mw = 0.0
    tracker_investment_usd = 0.0
    tracker_capacity_by_source: defaultdict[str, float] = defaultdict(float)
    tracker_capacity_by_status: defaultdict[str, float] = defaultdict(float)
    tracker_investment_by_source: defaultdict[str, float] = defaultdict(float)
    canonical_tracker_projects: dict[str, dict[str, Any]] = {}
    equipment_records_scanned = 0
    equipment_capacity_records = 0
    equipment_capacity_by_source: defaultdict[str, float] = defaultdict(float)
    eia_by_status: defaultdict[str, float] = defaultdict(float)
    eia_operating_capacity_by_region: defaultdict[str, float] = defaultdict(float)
    eia_planned_capacity_by_region: defaultdict[str, float] = defaultdict(float)
    egrid_generator_capacity_mw = 0.0
    skipped_rows: Counter[str] = Counter()
    source_documents: dict[tuple[str, str, str], dict[str, str]] = {}

    for path in _source_row_csvs(roots, "queue_records.csv"):
        for row in _read_csv(path):
            queue_records_scanned += 1
            _track_source(source_documents, row)
            if not _queue_record_in_scope(row):
                skipped_rows["queue_out_of_scope_status"] += 1
                continue
            capacity = _queue_capacity_mw(row)
            if capacity is None:
                skipped_rows["queue_missing_capacity"] += 1
                continue
            queue_capacity_records += 1
            queue_capacity_mw += capacity
            source_id = _source_id(row)
            region = _queue_region(row)
            queue_capacity_by_source[source_id] += capacity
            queue_capacity_by_region[region] += capacity
            if _queue_record_is_data_center_related(row):
                relationship = _queue_data_center_relationship(row)
                data_center_queue_records += 1
                data_center_queue_capacity_mw += capacity
                data_center_queue_capacity_by_region[region] += capacity
                data_center_queue_capacity_by_relationship[relationship] += capacity
                data_center_queue_projects.append(
                    _queue_project_example(
                        row,
                        capacity_mw=capacity,
                        region=region,
                        relationship=relationship,
                    )
                )

    for path in _source_row_csvs(roots, "projects.csv"):
        for row in _read_csv(path):
            if (row.get("source_type") or "").strip().lower() != "project_tracker":
                continue
            tracker_project_records_scanned += 1
            _track_source(source_documents, row)
            source_id = _source_id(row)
            low_capacity, high_capacity = _project_capacity_range(row)
            if high_capacity is not None and high_capacity > 0:
                tracker_capacity_records += 1
                tracker_capacity_low_mw += low_capacity or high_capacity
                tracker_capacity_high_mw += high_capacity
                tracker_capacity_by_source[source_id] += high_capacity
                tracker_capacity_by_status[_project_status(row)] += high_capacity
            it_load = _float_cell(row.get("it_load_mw"))
            if it_load is not None:
                tracker_it_load_mw += it_load
            investment = _float_cell(row.get("investment_usd"))
            if investment is not None:
                tracker_investment_usd += investment
                tracker_investment_by_source[source_id] += investment
            _add_canonical_tracker_project(
                canonical_tracker_projects,
                row,
                low_capacity=low_capacity,
                high_capacity=high_capacity,
                investment=investment,
            )

    for path in _source_row_csvs(roots, "equipment_records.csv"):
        for row in _read_csv(path):
            equipment_records_scanned += 1
            _track_source(source_documents, row)
            source_id = _source_id(row)
            if source_id.startswith("eia-860m-"):
                capacity = _float_cell(row.get("Nameplate Capacity (MW)"))
                status = _eia_status(row)
                if capacity is None:
                    skipped_rows["eia_missing_capacity"] += 1
                    continue
                equipment_capacity_records += 1
                equipment_capacity_by_source[source_id] += capacity
                eia_by_status[status] += capacity
                region = _normalize_region(_equipment_region(row))
                if status == "operating":
                    eia_operating_capacity_by_region[region] += capacity
                elif status == "planned":
                    eia_planned_capacity_by_region[region] += capacity
            elif source_id.startswith("epa-egrid") and row.get("sheet_name") == "GEN23":
                capacity = _float_cell(row.get("Generator nameplate capacity (MW)"))
                if capacity is None:
                    skipped_rows["egrid_missing_capacity"] += 1
                    continue
                equipment_capacity_records += 1
                equipment_capacity_by_source[source_id] += capacity
                egrid_generator_capacity_mw += capacity

    return PhysicalCapacitySummary(
        generated_at=datetime.now(UTC).isoformat(),
        data_dirs=[str(root) for root in roots],
        queue_records_scanned=queue_records_scanned,
        queue_capacity_records=queue_capacity_records,
        queue_capacity_mw=_round_mw(queue_capacity_mw),
        queue_capacity_by_source_mw=_sorted_capacity_dict(queue_capacity_by_source),
        queue_capacity_by_region_mw=_sorted_capacity_dict(queue_capacity_by_region),
        data_center_queue_records=data_center_queue_records,
        data_center_queue_capacity_mw=_round_mw(data_center_queue_capacity_mw),
        data_center_queue_capacity_by_region_mw=_sorted_capacity_dict(
            data_center_queue_capacity_by_region
        ),
        data_center_queue_capacity_by_relationship_mw=_sorted_capacity_dict(
            data_center_queue_capacity_by_relationship
        ),
        top_data_center_queue_projects=_top_queue_project_examples(data_center_queue_projects),
        tracker_project_records_scanned=tracker_project_records_scanned,
        tracker_capacity_records=tracker_capacity_records,
        tracker_capacity_low_mw=_round_mw(tracker_capacity_low_mw),
        tracker_capacity_high_mw=_round_mw(tracker_capacity_high_mw),
        tracker_it_load_mw=_round_mw(tracker_it_load_mw),
        tracker_investment_usd=round(tracker_investment_usd, 2),
        tracker_capacity_by_source_mw=_sorted_capacity_dict(tracker_capacity_by_source),
        tracker_capacity_by_status_mw=_sorted_capacity_dict(tracker_capacity_by_status),
        tracker_investment_by_source_usd=_sorted_money_dict(tracker_investment_by_source),
        **_canonical_tracker_metrics(canonical_tracker_projects),
        equipment_records_scanned=equipment_records_scanned,
        equipment_capacity_records=equipment_capacity_records,
        eia_operating_capacity_mw=_round_mw(eia_by_status["operating"]),
        eia_planned_capacity_mw=_round_mw(eia_by_status["planned"]),
        eia_retired_capacity_mw=_round_mw(eia_by_status["retired"]),
        eia_canceled_or_postponed_capacity_mw=_round_mw(eia_by_status["canceled_or_postponed"]),
        egrid_generator_capacity_mw=_round_mw(egrid_generator_capacity_mw),
        equipment_capacity_by_source_mw=_sorted_capacity_dict(equipment_capacity_by_source),
        eia_operating_capacity_by_region_mw=_sorted_capacity_dict(eia_operating_capacity_by_region),
        eia_planned_capacity_by_region_mw=_sorted_capacity_dict(eia_planned_capacity_by_region),
        physical_stress_indicators=_physical_stress_indicators(
            queue_capacity_by_region=queue_capacity_by_region,
            eia_planned_capacity_by_region=eia_planned_capacity_by_region,
            eia_operating_capacity_by_region=eia_operating_capacity_by_region,
        ),
        source_documents=sorted(source_documents.values(), key=lambda row: row["source_id"]),
        skipped_rows=dict(sorted(skipped_rows.items())),
    )


def write_physical_capacity_summary(
    summary: PhysicalCapacitySummary,
    path: str | Path,
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    return output


def _source_row_csvs(roots: Sequence[Path], filename: str) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(path for path in root.rglob(filename) if path.is_file())
    return sorted(files)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return [
            {key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(f)
        ]


def _queue_capacity_mw(row: Mapping[str, str]) -> float | None:
    preferred = _first_positive_float(
        row,
        [
            "NET MW POI",
            "Capacity (MW)",
            "Net MW",
            "MFO",
            "MaximumFacilityOutput",
        ],
    )
    if preferred is not None:
        return preferred
    candidates = [
        _float_cell(row.get(key))
        for key in [
            "Max Summer MW",
            "Max Winter MW",
            "Summer MW",
            "Winter MW",
            "MAX Summer MW",
            "MAX Winter MW",
            "Capacity",
            "MW Capacity",
            "MWCapacity",
            "MW Energy",
            "MWEnergy",
            "MW In Service",
            "MWInService",
            "SP (MW)",
            "WP (MW)",
            "Requested ERIS MW",
            "Requested NRIS MW",
            "NET MW 1",
            "NET MW 2",
            "NET MW 3",
        ]
    ]
    numeric = [value for value in candidates if value is not None and value > 0]
    return max(numeric) if numeric else None


def _queue_region(row: Mapping[str, str]) -> str:
    source_id = _source_id(row)
    source_prefix_regions = {
        "caiso-": "CAISO",
        "nyiso-": "NYISO",
        "miso-": "MISO",
        "ercot-": "ERCOT",
        "spp-": "SPP",
        "pjm-": "PJM",
        "iso-ne-": "ISO-NE",
    }
    for prefix, mapped_region in source_prefix_regions.items():
        if source_id.startswith(prefix):
            return _normalize_region(mapped_region)
    row_region = _first_present(row, ["Balancing Authority Code", "State", "Project State"])
    return _normalize_region(row_region or "unknown")


def _queue_record_in_scope(row: Mapping[str, str]) -> bool:
    status = (_queue_status(row) or "").strip().lower()
    if status in {
        "annulled",
        "canceled",
        "cancelled",
        "deactivated",
        "in service",
        "i/s",
        "operational",
        "partially in service",
        "retracted",
        "terminated",
        "withdrawn",
    }:
        return False
    if status.startswith("partially in service") and "under construction" not in status:
        return False
    if _first_present(
        row,
        [
            "Withdrawal Date",
            "Withdrawn Date",
            "Date Withdrawn",
            "W/ D Date",
            "Cessation Date",
        ],
    ):
        return False
    if _source_id(row).startswith("iso-ne-") and not status:
        op_date = _first_present(row, ["Op Date"])
        if op_date and _date_is_on_or_before_today(op_date):
            return False
    return not _first_present(row, ["Actual In Service Date", "ActualCompletionDate"])


def _queue_record_is_data_center_related(row: Mapping[str, str]) -> bool:
    text = " ".join(
        value
        for key in [
            "Project Name",
            "Name",
            "CommercialName",
            "Alternative Name",
            "Generating Facility",
            "Non-Confidential Summary",
            "ProjectType",
            "Technology",
            "Fuel",
            "Interconnecting Entity",
            "Interconnection Customer Name",
            "Interconnection Customer",
            "Developer/Interconnection Customer",
            "Owner/Developer",
        ]
        if (value := row.get(key))
    ).lower()
    return any(term in text for term in DATA_CENTER_QUEUE_TERMS)


def _queue_data_center_relationship(row: Mapping[str, str]) -> str:
    project_text = " ".join(
        value
        for key in ["Project Name", "Name", "CommercialName", "Alternative Name"]
        if (value := row.get(key))
    ).lower()
    if any(term in project_text for term in DATA_CENTER_QUEUE_TERMS):
        return "direct_data_center_load"
    return "supporting_generation_for_data_center_load"


def _queue_project_example(
    row: Mapping[str, str],
    *,
    capacity_mw: float,
    region: str,
    relationship: str,
) -> dict[str, Any]:
    return {
        "project_name": _first_present(
            row,
            ["Project Name", "Name", "CommercialName", "Alternative Name", "Generating Facility"],
        )
        or "unknown",
        "queue_id": _first_present(
            row,
            [
                "Queue Number",
                "Project Number",
                "ProjectNumber",
                "INR",
                "Application ID",
                "Generation Interconnection Number",
                "IFS Queue Number",
                "Position",
            ],
        )
        or "",
        "relationship": relationship,
        "region": region,
        "status": _queue_status(row) or "",
        "capacity_mw": _round_mw(capacity_mw),
        "requested_in_service_date": _first_present(
            row,
            [
                "Requested COD",
                "Proposed COD",
                "Projected COD",
                "ProjectedInServiceDate",
                "Application In Service Date",
                "In-Service Date",
                "Commercial Operation Date",
                "CommercialOperationMilestone",
                "Op Date",
            ],
        )
        or "",
        "customer": _first_present(
            row,
            [
                "Interconnection Customer Name",
                "Interconnection Customer",
                "Interconnecting Entity",
                "Developer/Interconnection Customer",
                "Owner/Developer",
            ],
        )
        or "",
        "county": _first_present(
            row, ["PROJECT COUNTY", "County", " Nearest Town or County", "Location of Need"]
        )
        or "",
        "state": _first_present(row, ["Project State", "State"]) or "",
        "point_of_interconnection": _first_present(
            row,
            [
                "POI",
                "POI Name",
                "Interconnection Point",
                "Interconnection Location",
                "Substation or Line",
                "POI Location",
                "Points of Interconnection",
            ],
        )
        or "",
        "data_center_load_description": _truncate_text(
            _first_present(row, ["Non-Confidential Summary", "Cause of Delay"]) or "",
            max_chars=360,
        ),
        "source_id": _source_id(row),
        "source_uri": row.get("source_uri", ""),
        "content_hash": row.get("content_hash", ""),
        "record_index": row.get("record_index", ""),
    }


def _top_queue_project_examples(projects: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        dict(project)
        for project in sorted(
            projects,
            key=lambda item: (-float(item.get("capacity_mw") or 0), str(item["project_name"])),
        )[:25]
    ]


def _truncate_text(value: str, *, max_chars: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 3].rstrip()}..."


def _project_capacity_range(row: Mapping[str, str]) -> tuple[float | None, float | None]:
    high = _float_cell(row.get("capacity_mw_high"))
    low = _float_cell(row.get("capacity_mw_low"))
    exact = _float_cell(row.get("capacity_mw"))
    if high is not None:
        return low, high
    if exact is not None:
        return exact, exact
    return None, None


def _project_status(row: Mapping[str, str]) -> str:
    return (row.get("construction_status") or row.get("status") or "unknown").strip() or "unknown"


def _add_canonical_tracker_project(
    canonical_projects: dict[str, dict[str, Any]],
    row: Mapping[str, str],
    *,
    low_capacity: float | None,
    high_capacity: float | None,
    investment: float | None,
) -> None:
    key = _canonical_tracker_project_key(row)
    entry = canonical_projects.setdefault(
        key,
        {
            "rows": 0,
            "sources": set(),
            "project_ids": set(),
            "statuses": set(),
            "state": _project_state(row),
            "capacity_low_mw": 0.0,
            "capacity_high_mw": 0.0,
            "investment_usd": 0.0,
        },
    )
    entry["rows"] += 1
    entry["sources"].add(_source_id(row))
    if row.get("project_id"):
        entry["project_ids"].add(str(row["project_id"]))
    entry["statuses"].add(_project_status(row))
    if high_capacity is not None and high_capacity > float(entry["capacity_high_mw"]):
        entry["capacity_high_mw"] = high_capacity
        entry["capacity_low_mw"] = low_capacity or high_capacity
    elif low_capacity is not None and low_capacity > float(entry["capacity_low_mw"]):
        entry["capacity_low_mw"] = low_capacity
    if investment is not None and investment > float(entry["investment_usd"]):
        entry["investment_usd"] = investment


def _canonical_tracker_metrics(
    canonical_projects: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    capacity_by_status: defaultdict[str, float] = defaultdict(float)
    capacity_by_state: defaultdict[str, float] = defaultdict(float)
    distinct_capacity_records = 0
    capacity_low_mw = 0.0
    capacity_high_mw = 0.0
    investment_usd = 0.0
    pipeline_capacity_high_mw = 0.0
    operating_capacity_high_mw = 0.0
    cancelled_capacity_high_mw = 0.0
    duplicate_groups = 0
    duplicate_rows_collapsed = 0

    for project in canonical_projects.values():
        row_count = int(project["rows"])
        if row_count > 1:
            duplicate_groups += 1
            duplicate_rows_collapsed += row_count - 1
        status = _canonical_status(project["statuses"])
        high_capacity = float(project["capacity_high_mw"])
        low_capacity = float(project["capacity_low_mw"])
        if high_capacity > 0:
            distinct_capacity_records += 1
            capacity_low_mw += low_capacity or high_capacity
            capacity_high_mw += high_capacity
            capacity_by_status[status] += high_capacity
            state = str(project["state"] or "unknown")
            capacity_by_state[state] += high_capacity
            if status in {"announced", "permitted", "under_construction"}:
                pipeline_capacity_high_mw += high_capacity
            elif status == "in_service":
                operating_capacity_high_mw += high_capacity
            elif status == "cancelled":
                cancelled_capacity_high_mw += high_capacity
        investment_usd += float(project["investment_usd"])

    return {
        "tracker_distinct_projects": len(canonical_projects),
        "tracker_duplicate_groups": duplicate_groups,
        "tracker_duplicate_rows_collapsed": duplicate_rows_collapsed,
        "tracker_distinct_capacity_records": distinct_capacity_records,
        "tracker_distinct_capacity_low_mw": _round_mw(capacity_low_mw),
        "tracker_distinct_capacity_high_mw": _round_mw(capacity_high_mw),
        "tracker_distinct_pipeline_capacity_high_mw": _round_mw(pipeline_capacity_high_mw),
        "tracker_distinct_operating_capacity_high_mw": _round_mw(operating_capacity_high_mw),
        "tracker_distinct_cancelled_capacity_high_mw": _round_mw(cancelled_capacity_high_mw),
        "tracker_distinct_investment_usd": round(investment_usd, 2),
        "tracker_distinct_capacity_by_status_mw": _sorted_capacity_dict(capacity_by_status),
        "tracker_distinct_capacity_by_state_mw": _sorted_capacity_dict(capacity_by_state),
    }


def _canonical_tracker_project_key(row: Mapping[str, str]) -> str:
    state = _project_state(row)
    city = _slug_text(row.get("city") or "")
    address = _slug_text(row.get("address") or "")
    if state and city and address:
        return f"address:{state}:{city}:{address}"

    operator = _normalize_company(row.get("operator") or row.get("owner") or "")
    name_tokens = _name_tokens(row.get("name") or "")
    operator_tokens = set(operator.split("-")) if operator else set()
    residual_tokens = [
        token
        for token in name_tokens
        if token not in operator_tokens and token not in GENERIC_PROJECT_TERMS
    ]
    if (
        state
        and city
        and operator
        and (not residual_tokens or set(residual_tokens).issubset(set(city.split("-"))))
    ):
        return f"operator:{state}:{city}:{operator}"

    name_key = "-".join(name_tokens) or _slug_text(row.get("project_id") or "unknown")
    place = f"{state}:{city}" if state or city else _slug_text(row.get("jurisdiction") or "")
    return f"name:{place}:{name_key}"


def _canonical_status(statuses: Any) -> str:
    status_set = {str(status) for status in statuses if status}
    for status in ["under_construction", "permitted", "announced", "in_service", "cancelled"]:
        if status in status_set:
            return status
    return "unknown"


def _project_state(row: Mapping[str, str]) -> str:
    state = (row.get("state") or "").strip()
    if not state:
        jurisdiction = row.get("jurisdiction") or ""
        state = jurisdiction.rsplit(",", 1)[-1].strip() if "," in jurisdiction else ""
    normalized = state.upper()
    if len(normalized) == 2:
        return normalized
    return STATE_ALIASES.get(normalized, normalized or "unknown")


def _name_tokens(value: str) -> list[str]:
    return [token for token in _slug_text(value).split("-") if token]


def _normalize_company(value: str) -> str:
    first = value.replace(";", "|").split("|")[0].split(",")[0]
    tokens = [
        token
        for token in _slug_text(first).split("-")
        if token and token not in GENERIC_PROJECT_TERMS
    ]
    return "-".join(tokens[:3])


def _slug_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def _queue_status(row: Mapping[str, str]) -> str | None:
    return _first_present(
        row,
        [
            "Status",
            "Project Status",
            "Queue Status",
            "Request Status",
            "Post GIA Status",
            "GIM Study Phase",
            "S",
        ],
    )


def _eia_status(row: Mapping[str, str]) -> str:
    sheet = (row.get("sheet_name") or "").strip().lower()
    if sheet == "operating":
        return "operating"
    if sheet == "planned":
        return "planned"
    if sheet == "retired":
        return "retired"
    if sheet.startswith("canceled"):
        return "canceled_or_postponed"
    return sheet.replace(" ", "_") or "unknown"


def _equipment_region(row: Mapping[str, str]) -> str:
    return (
        _first_present(row, ["Balancing Authority Code", "Plant State", "Plant state abbreviation"])
        or "unknown"
    )


def _physical_stress_indicators(
    *,
    queue_capacity_by_region: Mapping[str, float],
    eia_planned_capacity_by_region: Mapping[str, float],
    eia_operating_capacity_by_region: Mapping[str, float],
) -> list[dict[str, Any]]:
    indicators: list[dict[str, Any]] = []
    regions = sorted(
        {
            _normalize_region(region)
            for region in [
                *queue_capacity_by_region,
                *eia_planned_capacity_by_region,
                *eia_operating_capacity_by_region,
            ]
        }
    )
    for region in regions:
        queue_mw = queue_capacity_by_region.get(region, 0.0)
        planned_mw = eia_planned_capacity_by_region.get(region, 0.0)
        operating_mw = eia_operating_capacity_by_region.get(region, 0.0)
        if queue_mw <= 0:
            continue
        queue_to_planned = _ratio(queue_mw, planned_mw)
        queue_to_operating = _ratio(queue_mw, operating_mw)
        indicators.append(
            {
                "region": region,
                "queue_capacity_mw": _round_mw(queue_mw),
                "eia_planned_capacity_mw": _round_mw(planned_mw),
                "eia_operating_capacity_mw": _round_mw(operating_mw),
                "queue_less_planned_mw": _round_mw(queue_mw - planned_mw),
                "queue_to_planned_ratio": queue_to_planned,
                "queue_to_operating_ratio": queue_to_operating,
                "stress_level": _stress_level(
                    queue_mw=queue_mw,
                    planned_mw=planned_mw,
                    queue_to_planned=queue_to_planned,
                    queue_to_operating=queue_to_operating,
                ),
            }
        )
    return sorted(
        indicators,
        key=lambda item: (
            {"high": 0, "medium": 1, "monitor": 2}.get(str(item["stress_level"]), 3),
            -float(item["queue_less_planned_mw"]),
        ),
    )


def _track_source(
    source_documents: dict[tuple[str, str, str], dict[str, str]],
    row: Mapping[str, str],
) -> None:
    source_id = _source_id(row)
    source_uri = row.get("source_uri", "")
    content_hash = row.get("content_hash", "")
    key = (source_id, source_uri, content_hash)
    if key not in source_documents:
        source_documents[key] = {
            "source_id": source_id,
            "source_uri": source_uri,
            "source_type": row.get("source_type", ""),
            "content_hash": content_hash,
            "document_id": row.get("document_id", ""),
        }


def _source_id(row: Mapping[str, str]) -> str:
    return row.get("source_id", "").strip() or "unknown"


def _normalize_region(value: str) -> str:
    normalized = value.strip().upper()
    if not normalized:
        return "unknown"
    return REGION_ALIASES.get(normalized, normalized)


def _first_float(row: Mapping[str, str], keys: Iterable[str]) -> float | None:
    for key in keys:
        value = _float_cell(row.get(key))
        if value is not None:
            return value
    return None


def _first_positive_float(row: Mapping[str, str], keys: Iterable[str]) -> float | None:
    for key in keys:
        value = _float_cell(row.get(key))
        if value is not None and value > 0:
            return value
    return None


def _float_cell(value: str | None) -> float | None:
    if not value:
        return None
    normalized = value.strip().replace(",", "")
    if normalized in {"", "N/A", "None", "NA"}:
        return None
    try:
        parsed = float(normalized)
    except ValueError:
        return None
    if parsed < 0:
        return None
    return parsed


def _date_is_on_or_before_today(value: str) -> bool:
    parsed = _parse_datetime(value)
    if parsed is None:
        return False
    return parsed.date() <= datetime.now(UTC).date()


def _parse_datetime(value: str) -> datetime | None:
    normalized = value.strip()
    if not normalized:
        return None
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _first_present(row: Mapping[str, str], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = row.get(key)
        if value and value.strip():
            return value.strip()
    return None


def _sorted_capacity_dict(values: Mapping[str, float]) -> dict[str, float]:
    return {
        key: _round_mw(value)
        for key, value in sorted(values.items(), key=lambda item: (-item[1], item[0]))
    }


def _sorted_money_dict(values: Mapping[str, float]) -> dict[str, float]:
    return {
        key: round(value, 2)
        for key, value in sorted(values.items(), key=lambda item: (-item[1], item[0]))
    }


def _round_mw(value: float) -> float:
    return round(value, 3)


def _ratio(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 3)


def _stress_level(
    *,
    queue_mw: float,
    planned_mw: float,
    queue_to_planned: float | None,
    queue_to_operating: float | None,
) -> str:
    if queue_mw > 0 and planned_mw <= 0:
        return "high"
    if (queue_to_planned is not None and queue_to_planned >= 5) or (
        queue_to_operating is not None and queue_to_operating >= 1
    ):
        return "high"
    if (queue_to_planned is not None and queue_to_planned >= 2) or (
        queue_to_operating is not None and queue_to_operating >= 0.5
    ):
        return "medium"
    return "monitor"
