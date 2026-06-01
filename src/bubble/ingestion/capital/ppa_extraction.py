"""Normalize source-backed PPA rows into deal evidence."""

from __future__ import annotations

import csv
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from bubble.models.base import Provenance
from bubble.quality.source_invariants import assert_source_row

PPA_DEAL_FIELDNAMES = [
    "deal_id",
    "deal_type",
    "title",
    "parties",
    "primary_party",
    "counterparty_roles",
    "announced_date",
    "effective_date",
    "maturity_date",
    "notional_amount_usd",
    "currency",
    "key_terms",
    "collateral",
    "guarantees",
    "linked_projects",
    "linked_assets",
    "is_related_party",
    "concentration_risk_flag",
    "source_uri",
    "source_type",
    "source_confidence",
    "human_review_status",
    "page_or_section",
    "content_hash",
]


@dataclass(frozen=True)
class PpaDealExtractionSummary:
    """Summary for a PPA-to-deal normalization run."""

    input_csv: str
    output_csv: str
    source_rows: int
    deals_written: int
    skipped_rows: int
    workers: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_csv": self.input_csv,
            "output_csv": self.output_csv,
            "source_rows": self.source_rows,
            "deals_written": self.deals_written,
            "skipped_rows": self.skipped_rows,
            "workers": self.workers,
        }


def extract_ppa_deals(
    input_csv: str | Path,
    output_csv: str | Path,
    *,
    max_workers: int = 32,
) -> PpaDealExtractionSummary:
    """Extract normalized, source-backed PPA deals from acquired PPA rows."""

    input_path = Path(input_csv)
    output_path = Path(output_csv)
    rows = _read_rows(input_path)
    worker_count = _worker_count(max_workers=max_workers, row_count=len(rows))
    deals = _extract_deal_rows(rows, max_workers=worker_count)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PPA_DEAL_FIELDNAMES)
        writer.writeheader()
        writer.writerows(deals)

    return PpaDealExtractionSummary(
        input_csv=str(input_path),
        output_csv=str(output_path),
        source_rows=len(rows),
        deals_written=len(deals),
        skipped_rows=len(rows) - len(deals),
        workers=worker_count,
    )


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return [
            {key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(f)
        ]


def _is_extractable_ppa(row: dict[str, str]) -> bool:
    if not row.get("ID"):
        return False
    assert_source_row(row, context=f"ppa:{row.get('ID', 'unknown')}")
    return bool(_party_names(row)) and not _is_probable_test_record(row)


def _extract_deal_rows(rows: list[dict[str, str]], *, max_workers: int) -> list[dict[str, str]]:
    if not rows:
        return []
    if max_workers <= 1:
        return [deal for row in rows if (deal := _deal_row_if_extractable(row)) is not None]
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return [deal for deal in executor.map(_deal_row_if_extractable, rows) if deal is not None]


def _deal_row_if_extractable(row: dict[str, str]) -> dict[str, str] | None:
    if not _is_extractable_ppa(row):
        return None
    return _deal_row(row)


def _deal_row(row: dict[str, str]) -> dict[str, str]:
    ppa_id = row["ID"]
    amount_mw = _optional_float(row.get("Amount"))
    parties = _party_names(row)
    roles = _counterparty_roles(row)
    key_terms = _key_terms(row, amount_mw=amount_mw)
    content_hash = row.get("content_hash") or Provenance.compute_content_hash(
        json.dumps(row, sort_keys=True)
    )

    return {
        "deal_id": f"ppa:ferc:{ppa_id}",
        "deal_type": "ppa",
        "title": _title(row),
        "parties": "|".join(parties),
        "primary_party": parties[0],
        "counterparty_roles": json.dumps(roles, sort_keys=True),
        "announced_date": "",
        "effective_date": _date_only(row.get("Start_Date")),
        "maturity_date": _date_only(row.get("Actual_End_Date"))
        or _date_only(row.get("Scheduled_End_Date")),
        "notional_amount_usd": "",
        "currency": "USD",
        "key_terms": json.dumps(key_terms, sort_keys=True),
        "collateral": "",
        "guarantees": "",
        "linked_projects": "",
        "linked_assets": _linked_assets(row),
        "is_related_party": _bool_text(_is_related_party(row)),
        "concentration_risk_flag": "",
        "source_uri": row["source_uri"],
        "source_type": row.get("source_type") or "ferc",
        "source_confidence": "0.90",
        "human_review_status": "pending",
        "page_or_section": (
            f"FERC dataset 17 Entities to PPAs row ID {ppa_id}; "
            f"source_id={row.get('source_id', '')}; record_index={row.get('record_index', '')}"
        ),
        "content_hash": content_hash,
    }


def _party_names(row: dict[str, str]) -> list[str]:
    candidates = [
        row.get("Entity_Name"),
        row.get("Reporting_Entity_Name"),
        row.get("Counterparty_Name"),
    ]
    parties: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = (candidate or "").strip()
        key = normalized.lower()
        if normalized and key not in seen:
            parties.append(normalized)
            seen.add(key)
    return parties


def _counterparty_roles(row: dict[str, str]) -> dict[str, list[str]]:
    entity = row.get("Entity_Name") or row.get("Reporting_Entity_Name")
    reporting = row.get("Reporting_Entity_Name") or entity
    counterparty = row.get("Counterparty_Name")
    ppa_type = (row.get("PPA_Type") or "").strip().lower()

    roles: dict[str, list[str]] = {}
    if ppa_type == "sale":
        _add_role(roles, "seller", entity)
        _add_role(roles, "reporting_entity", reporting)
        _add_role(roles, "buyer", counterparty)
        _add_role(roles, "offtaker", counterparty)
    elif ppa_type == "purchase":
        _add_role(roles, "buyer", entity)
        _add_role(roles, "offtaker", entity)
        _add_role(roles, "reporting_entity", reporting)
        _add_role(roles, "seller", counterparty)
    else:
        _add_role(roles, "reporting_entity", reporting)
        _add_role(roles, "counterparty", counterparty)
    return roles


def _add_role(roles: dict[str, list[str]], role: str, entity: str | None) -> None:
    value = (entity or "").strip()
    if not value:
        return
    bucket = roles.setdefault(role, [])
    if value not in bucket:
        bucket.append(value)


def _key_terms(row: dict[str, str], *, amount_mw: float | None) -> dict[str, Any]:
    return {
        "extraction_method": "ferc_entities_to_ppas_v1",
        "ferc_dataset_id": "17",
        "ferc_entities_ppa_id": row.get("ID", ""),
        "reporting_entity_cid": row.get("Reporting_Entity_CID", ""),
        "submission_id": row.get("Submission_ID", ""),
        "ppa_agreement_id": row.get("PPA_Agreement_ID", ""),
        "ppa_type": row.get("PPA_Type", ""),
        "supply_type": row.get("Supply_Type", ""),
        "amount_mw": amount_mw,
        "amount_adjusted_mw": _optional_float(row.get("Amount_Adjusted")),
        "adjusted_rating_option": row.get("Adjusted_Rating_Option", ""),
        "source_balancing_authority": row.get("Source_Balancing_Authority", ""),
        "source_balancing_authority_hub": row.get("Source_Balancing_Authority_Hub", ""),
        "sink_balancing_authority": row.get("Sink_Balancing_Authority", ""),
        "sink_balancing_authority_hub": row.get("Sink_Balancing_Authority_Hub", ""),
        "record_status": row.get("Record_Status", ""),
        "record_type": row.get("Record_Type", ""),
        "active_date": _date_only(row.get("Active_Date")),
        "inactive_date": _date_only(row.get("Inactive_Date")),
        "entity_id": row.get("Entity_ID", ""),
        "entity_id_type": row.get("Entity_ID_Type_CD", ""),
        "counterparty_id": row.get("Counterparty_ID", ""),
        "counterparty_id_type": row.get("Counterparty_ID_Type_CD", ""),
        "eia_plant_code": row.get("EIA_Plant_Code", ""),
        "eia_generator_id": row.get("EIA_Generator_ID", ""),
        "eia_unit_code": row.get("EIA_Unit_Code", ""),
        "ferc_gen_asset_id": row.get("FERC_Gen_Asset_ID", ""),
        "generation_asset_type": row.get("Generation_Asset_Type", ""),
        "source_artifact_id": row.get("source_id", ""),
        "source_artifact_local_path": row.get("local_path", ""),
        "source_record_index": row.get("record_index", ""),
        "requires_human_review": True,
    }


def _title(row: dict[str, str]) -> str:
    entity = row.get("Entity_Name") or row.get("Reporting_Entity_Name") or "Unknown entity"
    counterparty = row.get("Counterparty_Name") or "Unknown counterparty"
    ppa_type = row.get("PPA_Type") or "PPA"
    amount = row.get("Amount")
    amount_text = f", {amount} MW" if amount else ""
    return f"FERC PPA {row.get('ID', '')}: {entity} {ppa_type} with {counterparty}{amount_text}"


def _linked_assets(row: dict[str, str]) -> str:
    refs = []
    if row.get("EIA_Plant_Code"):
        refs.append(f"eia_plant:{row['EIA_Plant_Code']}")
    if row.get("EIA_Generator_ID"):
        refs.append(f"eia_generator:{row['EIA_Generator_ID']}")
    if row.get("FERC_Gen_Asset_ID"):
        refs.append(f"ferc_gen_asset:{row['FERC_Gen_Asset_ID']}")
    return "|".join(refs)


def _is_related_party(row: dict[str, str]) -> bool:
    entity_id = (row.get("Entity_ID") or "").strip().lower()
    counterparty_id = (row.get("Counterparty_ID") or "").strip().lower()
    entity_name = (row.get("Entity_Name") or "").strip().lower()
    counterparty_name = (row.get("Counterparty_Name") or "").strip().lower()
    return bool(
        (entity_id and entity_id == counterparty_id)
        or (entity_name and entity_name == counterparty_name)
    )


def _is_probable_test_record(row: dict[str, str]) -> bool:
    values = [
        row.get("Reporting_Entity_Name", ""),
        row.get("Entity_Name", ""),
        row.get("Counterparty_Name", ""),
    ]
    normalized = " ".join(value.lower() for value in values if value)
    compact = normalized.replace(" ", "")
    return any(
        marker in normalized or marker in compact
        for marker in (
            "production test",
            "test company",
            "testcompany",
            "dummy company",
            "dummycompany",
        )
    )


def _optional_float(value: str | None) -> float | None:
    if not value:
        return None
    return float(value.replace(",", ""))


def _date_only(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.strip()
    if "T" in normalized:
        normalized = normalized.split("T", maxsplit=1)[0]
    try:
        return date.fromisoformat(normalized).isoformat()
    except ValueError:
        return ""


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _worker_count(*, max_workers: int, row_count: int) -> int:
    if row_count <= 0:
        return 0
    return min(max(1, max_workers), row_count)
