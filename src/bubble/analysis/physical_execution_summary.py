"""Roll up source-backed physical execution terms without project-level overclaiming."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

MW_TERM_TYPES = {
    "onsite_generation_mw",
    "physical_generation_capacity_mw",
    "utility_generation_capacity_mw",
}

RISK_TERM_TYPES = {
    "behind_the_meter_or_off_grid",
    "permit_litigation_or_enforcement_risk",
    "queue_bypass_or_no_queue",
    "ratepayer_stranded_asset_transfer",
}


@dataclass(frozen=True)
class PhysicalExecutionSummary:
    """Source-backed term-level physical execution rollup.

    MW fields are sums over distinct extracted terms, not deduped project
    capacities. A project may appear with multiple legitimate source-backed
    terms, so report wording must preserve that distinction.
    """

    term_rows: int
    distinct_terms: int
    duplicate_term_rows_collapsed: int
    source_uris: int
    source_documents: int
    projects: int
    operators: int
    by_term_type: dict[str, int]
    distinct_by_term_type: dict[str, int]
    term_level_mw_by_type: dict[str, float]
    onsite_generation_mw_term_sum: float
    physical_generation_capacity_mw_term_sum: float
    utility_generation_capacity_mw_term_sum: float
    risk_term_counts: dict[str, int]
    top_mw_terms: list[dict[str, Any]]
    top_risk_terms: list[dict[str, Any]]
    caveat: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_physical_execution_summary(
    data_dirs: Sequence[str | Path],
    *,
    top_limit: int = 15,
) -> PhysicalExecutionSummary:
    """Build conservative source-term rollups from physical_execution_terms.csv files."""

    rows = list(_iter_term_rows(data_dirs))
    distinct_rows = _distinct_rows(rows)
    by_term_type = Counter(_field(row, "term_type") for row in rows if _field(row, "term_type"))
    distinct_by_term_type = Counter(
        _field(row, "term_type") for row in distinct_rows if _field(row, "term_type")
    )
    mw_by_type: defaultdict[str, float] = defaultdict(float)
    for row in distinct_rows:
        term_type = _field(row, "term_type")
        if term_type in MW_TERM_TYPES:
            mw_by_type[term_type] += _float(row.get("value"))

    risk_counts = {
        term_type: distinct_by_term_type.get(term_type, 0)
        for term_type in sorted(RISK_TERM_TYPES)
        if distinct_by_term_type.get(term_type, 0)
    }
    source_uris = {_field(row, "source_uri") for row in distinct_rows if _field(row, "source_uri")}
    source_documents = {
        _field(row, "document_id") for row in distinct_rows if _field(row, "document_id")
    }
    projects = {_field(row, "project_name") for row in distinct_rows if _field(row, "project_name")}
    operators = {_field(row, "operator") for row in distinct_rows if _field(row, "operator")}

    return PhysicalExecutionSummary(
        term_rows=len(rows),
        distinct_terms=len(distinct_rows),
        duplicate_term_rows_collapsed=len(rows) - len(distinct_rows),
        source_uris=len(source_uris),
        source_documents=len(source_documents),
        projects=len(projects),
        operators=len(operators),
        by_term_type=dict(sorted(by_term_type.items())),
        distinct_by_term_type=dict(sorted(distinct_by_term_type.items())),
        term_level_mw_by_type={key: round(value, 3) for key, value in sorted(mw_by_type.items())},
        onsite_generation_mw_term_sum=round(mw_by_type["onsite_generation_mw"], 3),
        physical_generation_capacity_mw_term_sum=round(
            mw_by_type["physical_generation_capacity_mw"], 3
        ),
        utility_generation_capacity_mw_term_sum=round(
            mw_by_type["utility_generation_capacity_mw"], 3
        ),
        risk_term_counts=risk_counts,
        top_mw_terms=_top_terms(
            [row for row in distinct_rows if _field(row, "term_type") in MW_TERM_TYPES],
            top_limit=top_limit,
            sort_by_value=True,
        ),
        top_risk_terms=_top_terms(
            [row for row in distinct_rows if _field(row, "term_type") in RISK_TERM_TYPES],
            top_limit=top_limit,
            sort_by_value=False,
        ),
        caveat=(
            "MW totals are term-level sums over distinct extracted evidence rows, "
            "not project-deduped capacity forecasts. Use top terms and source URIs "
            "for diligence; do not add these totals to physical capacity metrics."
        ),
    )


def write_physical_execution_summary(
    summary: PhysicalExecutionSummary,
    path: str | Path,
) -> Path:
    """Write a physical execution summary JSON artifact."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    return output


def _iter_term_rows(data_dirs: Sequence[str | Path]) -> Iterable[dict[str, str]]:
    for root in data_dirs:
        path = Path(root) / "physical" / "physical_execution_terms.csv"
        if not path.exists():
            continue
        with path.open(newline="") as f:
            yield from csv.DictReader(f)


def _distinct_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, ...]] = set()
    distinct: list[dict[str, str]] = []
    for row in rows:
        key = (
            _field(row, "term_type"),
            _field(row, "value"),
            _field(row, "unit"),
            _field(row, "quote"),
            _field(row, "source_uri"),
            _field(row, "document_id"),
            _field(row, "project_name"),
            _field(row, "operator"),
            _field(row, "permit_or_docket"),
        )
        if key in seen:
            continue
        seen.add(key)
        distinct.append(row)
    return distinct


def _top_terms(
    rows: list[dict[str, str]],
    *,
    top_limit: int,
    sort_by_value: bool,
) -> list[dict[str, Any]]:
    if sort_by_value:
        rows = sorted(rows, key=lambda row: _float(row.get("value")), reverse=True)
    else:
        rows = sorted(
            rows,
            key=lambda row: (
                _field(row, "term_type"),
                _field(row, "project_name"),
                _field(row, "source_uri"),
            ),
        )
    return [_term_payload(row) for row in rows[:top_limit]]


def _term_payload(row: dict[str, str]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "term_type": _field(row, "term_type"),
        "value": _field(row, "value"),
        "unit": _field(row, "unit"),
        "project_name": _field(row, "project_name"),
        "operator": _field(row, "operator"),
        "jurisdiction": _field(row, "jurisdiction"),
        "authority": _field(row, "authority"),
        "permit_or_docket": _field(row, "permit_or_docket"),
        "source_uri": _field(row, "source_uri"),
        "quote": _field(row, "quote"),
    }
    numeric_value = _float(row.get("value"))
    if numeric_value:
        payload["numeric_value"] = numeric_value
    return payload


def _field(row: dict[str, Any], key: str) -> str:
    return str(row.get(key) or "").strip()


def _float(value: Any) -> float:
    try:
        return float(str(value or "").replace(",", "").strip())
    except ValueError:
        return 0.0
