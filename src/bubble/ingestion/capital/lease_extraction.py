"""Materialize source-backed lease agreement rows from acquired deal evidence."""

from __future__ import annotations

import csv
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bubble.quality.source_invariants import SourceDataInvariantError, assert_source_row

LEASE_AGREEMENT_FIELDNAMES = [
    "agreement_id",
    "deal_id",
    "deal_type",
    "title",
    "parties",
    "primary_party",
    "lessee",
    "lessor",
    "guarantor",
    "counterparty_roles",
    "notional_amount_usd",
    "currency",
    "maturity_date",
    "key_terms",
    "source_uri",
    "source_type",
    "source_confidence",
    "human_review_status",
    "page_or_section",
    "content_hash",
    "retrieved_at",
    "filing_cik",
    "filing_company_name",
    "filing_form",
    "filing_date",
    "filing_accession",
    "primary_document",
    "document_type",
    "source_document_kind",
    "is_agreement_exhibit",
    "parent_primary_document",
    "document_id",
    "local_path",
    "byte_count",
    "text_char_count",
    "relevance_score",
    "relevance_reasons",
]


@dataclass(frozen=True)
class LeaseAgreementExtractionSummary:
    """Summary for lease agreement corpus materialization."""

    input_deals_csv: str
    inventory_csv: str
    output_csv: str
    source_rows: int
    lease_candidates: int
    agreements_written: int
    skipped_rows: int
    inventory_matches: int
    workers: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_deals_csv": self.input_deals_csv,
            "inventory_csv": self.inventory_csv,
            "output_csv": self.output_csv,
            "source_rows": self.source_rows,
            "lease_candidates": self.lease_candidates,
            "agreements_written": self.agreements_written,
            "skipped_rows": self.skipped_rows,
            "inventory_matches": self.inventory_matches,
            "workers": self.workers,
        }


def extract_lease_agreements(
    deals_csv: str | Path,
    inventory_csv: str | Path,
    output_csv: str | Path,
    *,
    max_workers: int = 32,
) -> LeaseAgreementExtractionSummary:
    """Write a source-backed lease agreement corpus from acquired EDGAR deal candidates."""

    deals_path = Path(deals_csv)
    inventory_path = Path(inventory_csv)
    output_path = Path(output_csv)
    deal_rows = _read_rows(deals_path)
    inventory_rows = _read_rows(inventory_path) if inventory_path.exists() else []
    inventory = _InventoryIndex(inventory_rows)
    worker_count = _worker_count(max_workers=max_workers, row_count=len(deal_rows))
    agreements = _extract_agreement_rows(deal_rows, inventory=inventory, max_workers=worker_count)
    agreements.sort(key=lambda row: (row.get("filing_date", ""), row.get("deal_id", "")))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEASE_AGREEMENT_FIELDNAMES)
        writer.writeheader()
        writer.writerows(agreements)

    lease_candidates = sum(
        1 for row in deal_rows if (row.get("deal_type") or "").strip().lower() == "lease"
    )
    return LeaseAgreementExtractionSummary(
        input_deals_csv=str(deals_path),
        inventory_csv=str(inventory_path),
        output_csv=str(output_path),
        source_rows=len(deal_rows),
        lease_candidates=lease_candidates,
        agreements_written=len(agreements),
        skipped_rows=lease_candidates - len(agreements),
        inventory_matches=sum(1 for row in agreements if row.get("retrieved_at")),
        workers=worker_count,
    )


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return [
            {key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(f)
        ]


def _extract_agreement_rows(
    rows: list[dict[str, str]],
    *,
    inventory: _InventoryIndex,
    max_workers: int,
) -> list[dict[str, str]]:
    if not rows:
        return []
    if max_workers <= 1:
        return [
            agreement
            for row in rows
            if (agreement := _agreement_row_if_extractable(row, inventory=inventory)) is not None
        ]
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return [
            agreement
            for agreement in executor.map(
                lambda row: _agreement_row_if_extractable(row, inventory=inventory), rows
            )
            if agreement is not None
        ]


def _agreement_row_if_extractable(
    row: dict[str, str],
    *,
    inventory: _InventoryIndex,
) -> dict[str, str] | None:
    if (row.get("deal_type") or "").strip().lower() != "lease":
        return None
    try:
        assert_source_row(row, context=f"lease-agreement:{row.get('deal_id', 'unknown')}")
    except SourceDataInvariantError:
        return None
    return _agreement_row(row, inventory=inventory)


def _agreement_row(row: dict[str, str], *, inventory: _InventoryIndex) -> dict[str, str]:
    key_terms = _json_dict(row.get("key_terms"))
    roles = _json_dict(row.get("counterparty_roles")) or _json_dict(
        json.dumps(key_terms.get("counterparty_roles", {}))
    )
    inventory_row = inventory.match(row, key_terms=key_terms)
    cik = inventory_row.get("cik") or _cik_from_deal_id(row.get("deal_id", ""))
    accession = (
        inventory_row.get("accession_number")
        or _string_value(key_terms.get("accession_number"))
        or _accession_from_deal_id(row.get("deal_id", ""))
    )
    primary_document = inventory_row.get("primary_document") or _string_value(
        key_terms.get("primary_document")
    )
    document_id = _document_id(cik=cik, accession=accession, primary_document=primary_document)
    document_type = inventory_row.get("document_type") or _string_value(
        key_terms.get("document_type")
    )
    document_kind = _source_document_kind(document_type=document_type, key_terms=key_terms)

    return {
        "agreement_id": f"lease_agreement:{row.get('deal_id', '')}",
        "deal_id": row.get("deal_id", ""),
        "deal_type": "lease",
        "title": row.get("title", ""),
        "parties": row.get("parties", ""),
        "primary_party": row.get("primary_party", ""),
        "lessee": "|".join(_role_values(roles, "lessee")),
        "lessor": "|".join(_role_values(roles, "lessor")),
        "guarantor": "|".join(_role_values(roles, "guarantor")),
        "counterparty_roles": json.dumps(roles, sort_keys=True),
        "notional_amount_usd": row.get("notional_amount_usd", ""),
        "currency": row.get("currency") or "USD",
        "maturity_date": row.get("maturity_date", ""),
        "key_terms": json.dumps(key_terms, sort_keys=True),
        "source_uri": row.get("source_uri", ""),
        "source_type": row.get("source_type") or "sec_edgar",
        "source_confidence": row.get("source_confidence") or row.get("confidence") or "0.72",
        "human_review_status": row.get("human_review_status") or "pending",
        "page_or_section": row.get("page_or_section", ""),
        "content_hash": row.get("content_hash", ""),
        "retrieved_at": inventory_row.get("downloaded_at", ""),
        "filing_cik": cik,
        "filing_company_name": inventory_row.get("company_name", ""),
        "filing_form": inventory_row.get("form") or _string_value(key_terms.get("filing_form")),
        "filing_date": inventory_row.get("filing_date")
        or _string_value(key_terms.get("filing_date")),
        "filing_accession": accession,
        "primary_document": primary_document,
        "document_type": document_type,
        "source_document_kind": document_kind,
        "is_agreement_exhibit": "true" if document_kind == "sec_exhibit_agreement" else "false",
        "parent_primary_document": inventory_row.get("parent_primary_document")
        or _string_value(key_terms.get("parent_primary_document")),
        "document_id": document_id,
        "local_path": inventory_row.get("local_path")
        or _string_value(key_terms.get("document_local_path")),
        "byte_count": inventory_row.get("byte_count", ""),
        "text_char_count": inventory_row.get("text_char_count", ""),
        "relevance_score": inventory_row.get("relevance_score")
        or _string_value(key_terms.get("manifest_relevance_score")),
        "relevance_reasons": inventory_row.get("relevance_reasons")
        or "|".join(str(value) for value in key_terms.get("manifest_relevance_reasons", [])),
    }


class _InventoryIndex:
    def __init__(self, rows: list[dict[str, str]]) -> None:
        self._by_uri = {
            row.get("filing_url", "").strip().lower(): row
            for row in rows
            if row.get("filing_url", "").strip()
        }
        self._by_hash: dict[str, list[dict[str, str]]] = {}
        for row in rows:
            content_hash = row.get("content_hash", "").strip().lower()
            if content_hash:
                self._by_hash.setdefault(content_hash, []).append(row)

    def match(self, row: dict[str, str], *, key_terms: dict[str, Any]) -> dict[str, str]:
        source_uri = row.get("source_uri", "").strip().lower()
        if source_uri and source_uri in self._by_uri:
            return self._by_uri[source_uri]

        content_hash = row.get("content_hash", "").strip().lower()
        if not content_hash:
            return {}
        candidates = self._by_hash.get(content_hash, [])
        if not candidates:
            return {}

        accession = _string_value(key_terms.get("accession_number")).replace("-", "")
        primary_document = _string_value(key_terms.get("primary_document")).lower()
        for candidate in candidates:
            candidate_accession = candidate.get("accession_number", "").replace("-", "")
            candidate_document = candidate.get("primary_document", "").lower()
            if accession and candidate_accession and accession != candidate_accession:
                continue
            if primary_document and candidate_document and primary_document != candidate_document:
                continue
            return candidate
        return candidates[0]


def _json_dict(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _role_values(roles: dict[str, Any], role: str) -> list[str]:
    values = roles.get(role, [])
    if isinstance(values, str):
        candidates = values.replace(";", "|").split("|")
    elif isinstance(values, list):
        candidates = [str(value) for value in values]
    else:
        return []
    seen: set[str] = set()
    cleaned: list[str] = []
    for candidate in candidates:
        value = candidate.strip()
        key = value.lower()
        if value and key not in seen:
            cleaned.append(value)
            seen.add(key)
    return cleaned


def _string_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, int | float):
        return str(value)
    return ""


def _cik_from_deal_id(deal_id: str) -> str:
    parts = deal_id.split(":")
    return parts[1] if len(parts) >= 2 and parts[0] == "edgar" else ""


def _accession_from_deal_id(deal_id: str) -> str:
    parts = deal_id.split(":")
    if len(parts) >= 3 and parts[0] == "edgar":
        compact = parts[2]
        if len(compact) == 18:
            return f"{compact[:10]}-{compact[10:12]}-{compact[12:]}"
        return compact
    return ""


def _document_id(*, cik: str, accession: str, primary_document: str) -> str:
    parts = [part for part in [cik, accession.replace("-", ""), primary_document] if part]
    return f"sec-edgar:{':'.join(parts)}" if parts else ""


def _source_document_kind(*, document_type: str, key_terms: dict[str, Any]) -> str:
    if document_type.strip().lower() == "exhibit":
        return "sec_exhibit_agreement"
    reasons = " ".join(str(value) for value in key_terms.get("agreement_reasons", [])).lower()
    if "lease agreement" in reasons or "master lease" in reasons:
        return "sec_primary_lease_event_disclosure"
    return "sec_primary_lease_disclosure"


def _worker_count(*, max_workers: int, row_count: int) -> int:
    if row_count <= 0:
        return 0
    return max(1, min(max_workers, row_count))
