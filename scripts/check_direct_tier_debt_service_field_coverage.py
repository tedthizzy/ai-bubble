#!/usr/bin/env python
"""Summarize primary field coverage in direct-tier debt-service evidence cards.

This read-only checker turns the long-form verified collateral/recourse/covenant
fixture into one row per facility. It is deliberately a coverage surface, not a
metric adjustment: facility amounts and final-materiality totals are left
unchanged.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

CORE_FIELD_GROUPS = ("rate", "collateral", "recourse", "covenant")


@dataclass(frozen=True)
class DebtServiceFieldCoverage:
    entity: str
    facility: str
    row_count: int
    primary_edgar_rows: int
    partial_primary_rows: int
    derived_rows: int
    field_groups_verified: str
    missing_core_groups: str
    accessions: str
    status: str
    source_quote_snippets: str

    def to_row(self) -> dict[str, str]:
        row = asdict(self)
        return {key: str(value) for key, value in row.items()}


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def build_coverage_rows(rows: list[dict[str, str]]) -> list[DebtServiceFieldCoverage]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        entity = row.get("entity", "").strip()
        facility = row.get("facility", "").strip()
        if not entity or not facility:
            continue
        grouped.setdefault((entity, facility), []).append(row)

    coverage_rows = [
        _coverage_from_rows(entity, facility, card_rows)
        for (entity, facility), card_rows in grouped.items()
    ]
    return sorted(coverage_rows, key=lambda row: (row.entity.lower(), row.facility.lower()))


def _coverage_from_rows(
    entity: str,
    facility: str,
    rows: list[dict[str, str]],
) -> DebtServiceFieldCoverage:
    source_tiers = Counter(_source_tier(row) for row in rows)
    groups = sorted(
        {
            group
            for row in rows
            for group in _field_groups(row.get("field", ""), row.get("source_quote", ""))
        }
    )
    missing = (
        []
        if _is_context_only_group(rows)
        else [
            group
            for group in CORE_FIELD_GROUPS
            if group not in groups and not _group_is_not_applicable(group, rows)
        ]
    )
    return DebtServiceFieldCoverage(
        entity=entity,
        facility=facility,
        row_count=len(rows),
        primary_edgar_rows=source_tiers["primary_edgar"],
        partial_primary_rows=source_tiers["primary_edgar_partial"],
        derived_rows=source_tiers["derived"],
        field_groups_verified=";".join(groups),
        missing_core_groups=";".join(missing),
        accessions=";".join(
            sorted({row.get("filing_accession", "") for row in rows if row.get("filing_accession")})
        ),
        status=_status(groups, missing, rows),
        source_quote_snippets=" || ".join(_snippet(row) for row in rows[:4]),
    )


def _field_groups(field: str, quote: str) -> set[str]:
    normalized_field = field.strip().lower()
    text = f"{normalized_field} {quote}".lower()
    groups: set[str] = set()
    if normalized_field in {"coupon", "rate_floating", "commitment_fee", "rate_hedged"}:
        groups.add("rate")
    if normalized_field == "facility_size_usd":
        groups.add("size")
    if normalized_field == "aggregate_financing_usd":
        groups.add("context")
    if normalized_field in {"collateral", "credit_enhancement"}:
        groups.add("collateral")
    if normalized_field in {
        "recourse",
        "guarantor",
        "jv_ownership",
        "terawulf_effective_share_usd",
    }:
        groups.add("recourse")
    if normalized_field == "security":
        groups.add("recourse")
        if "secured" in text and "unsecured" not in text:
            groups.add("collateral")
    if normalized_field == "issuer":
        groups.add("structure")
    if normalized_field == "tranches":
        groups.add("rate")
        groups.add("maturity")
    if normalized_field in {"availability_until"}:
        groups.add("maturity")
    if normalized_field == "covenants":
        groups.add("covenant")
    return groups


def _group_is_not_applicable(group: str, rows: list[dict[str, str]]) -> bool:
    if group != "collateral":
        return False
    text = " ".join(f"{row.get('value', '')} {row.get('source_quote', '')}" for row in rows).lower()
    return "unsecured" in text or "not guaranteed by any" in text


def _is_context_only_group(rows: list[dict[str, str]]) -> bool:
    fields = {row.get("field", "").strip().lower() for row in rows}
    return fields <= {"aggregate_financing_usd"}


def _status(groups: list[str], missing: list[str], rows: list[dict[str, str]]) -> str:
    text = " ".join(f"{row.get('value', '')} {row.get('source_quote', '')}" for row in rows).lower()
    if _is_context_only_group(rows):
        return "aggregate_context_only"
    if not missing:
        return "core_structural_fields_verified"
    if "unsecured" in text and "recourse" in groups:
        return "parent_unsecured_recourse_verified"
    if "rate" in groups and "recourse" in groups and "collateral" in groups:
        return "collateral_recourse_rate_verified"
    return "partial_field_evidence"


def _source_tier(row: dict[str, str]) -> str:
    return row.get("source_tier", "").strip().lower()


def _snippet(row: dict[str, str], *, max_len: int = 180) -> str:
    quote = re.sub(r"\s+", " ", row.get("source_quote", "").strip())
    snippet = quote if len(quote) <= max_len else quote[: max_len - 3].rstrip() + "..."
    return f"{row.get('field', '')}: {snippet}"


def _write_rows(path: Path, rows: list[DebtServiceFieldCoverage]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(DebtServiceFieldCoverage.__annotations__))
        writer.writeheader()
        writer.writerows(row.to_row() for row in rows)


def summarize(rows: list[DebtServiceFieldCoverage]) -> dict[str, Any]:
    return {
        "facility_count": len(rows),
        "primary_edgar_rows": sum(row.primary_edgar_rows for row in rows),
        "partial_primary_rows": sum(row.partial_primary_rows for row in rows),
        "derived_rows": sum(row.derived_rows for row in rows),
        "by_status": dict(sorted(Counter(row.status for row in rows).items())),
        "facilities_with_missing_core_groups": sum(1 for row in rows if row.missing_core_groups),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("handoffs/fixtures/debt_service_verified_collateral_recourse_20260602.csv"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rows = build_coverage_rows(load_rows(args.input))
    if args.output:
        _write_rows(args.output, rows)
    print(json.dumps(summarize(rows), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
