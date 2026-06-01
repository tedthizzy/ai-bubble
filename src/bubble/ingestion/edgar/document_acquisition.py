"""
EDGAR document acquisition and deterministic agreement candidate extraction.

This module turns an EDGAR filing manifest into source documents and a first-pass
capital evidence CSV. The generated deals are deliberately pending-review:
they are useful extraction candidates, not final approved facts.
"""

from __future__ import annotations

import csv
import html
import json
import os
import re
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from bubble.ingestion.concurrency import (
    DomainFetchLimiter,
    FetchConcurrencyConfig,
    fetch_with_retries,
)
from bubble.models.base import DealType, HumanReviewStatus, Provenance, SourceType

FetchBytes = Callable[[str], bytes]
ManifestRow = dict[str, str]

AGREEMENT_RULES: tuple[tuple[DealType, tuple[str, ...], str], ...] = (
    (
        DealType.DEBT_FACILITY,
        (
            "credit agreement",
            "loan agreement",
            "term loan",
            "revolving credit",
            "credit facility",
            "financing agreement",
        ),
        "debt facility language",
    ),
    (
        DealType.BOND,
        (
            "indenture",
            "senior notes",
            "secured notes",
            "notes due",
            "aggregate principal amount",
        ),
        "bond or notes language",
    ),
    (
        DealType.LEASE,
        (
            "lease agreement",
            "master lease",
            "synthetic lease",
            "tenant lease",
            "lessor",
            "lessee",
        ),
        "lease language",
    ),
    (
        DealType.PPA,
        (
            "power purchase agreement",
            "energy purchase agreement",
            "ppa",
            "power supply agreement",
        ),
        "power purchase language",
    ),
    (
        DealType.GUARANTEE,
        (
            "guarantee agreement",
            "guaranty agreement",
            "guaranteed obligations",
            "parent guarantee",
        ),
        "guarantee language",
    ),
    (
        DealType.CONSTRUCTION_CONTRACT,
        (
            "construction agreement",
            "engineering procurement and construction",
            "epc agreement",
            "construction services agreement",
        ),
        "construction contract language",
    ),
    (
        DealType.LAND_ACQUISITION,
        (
            "purchase and sale agreement",
            "real property",
            "land purchase",
            "site acquisition",
        ),
        "land or site acquisition language",
    ),
)

MONTHS: dict[str, int] = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

PERIODIC_REPORT_FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A", "20-F"}
MAX_EXTRACTED_INTEREST_RATE_DECIMAL = 0.20
ROLE_ENTITY_PATTERN = re.compile(
    r"(?P<entity>[A-Z][A-Za-z0-9&.,'()\\/\- ]{2,140}?)"
    r"\s*,?\s+(?:as|in its capacity as)\s+(?:the\s+)?"
    r"(?P<role>"
    r"(?i:administrative agent|collateral agent|trustee|lender|lessor|lessee|buyer|seller|"
    r"offtaker|guarantor|issuer|borrower)"
    r")\b",
)
ENTITY_SUFFIX_PATTERN = re.compile(
    r"\b(?:inc\.?|incorporated|corp\.?|corporation|llc|l\.l\.c\.|ltd\.?|limited|plc|"
    r"lp|l\.p\.|llp|l\.l\.p\.|company|co\.|holdings?|properties|securities|markets|"
    r"capital|bank|trust|national association|n\.a\.|association)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class EdgarDocumentRecord:
    """Downloaded EDGAR source document."""

    cik: str
    company_name: str
    form: str
    accession_number: str
    filing_date: str | None
    primary_document: str
    filing_url: str
    local_path: str
    content_hash: str
    byte_count: int
    text_char_count: int
    relevance_score: int
    relevance_reasons: list[str]
    downloaded_at: str
    document_type: str = "primary"
    parent_primary_document: str | None = None

    def to_csv_row(self) -> dict[str, Any]:
        data = asdict(self)
        data["relevance_reasons"] = "|".join(self.relevance_reasons)
        return data


@dataclass(frozen=True)
class DealCandidate:
    """Pending-review capital/deal evidence extracted from one EDGAR document."""

    deal_id: str
    deal_type: DealType
    title: str
    parties: list[str]
    counterparty_roles: dict[str, list[str]]
    notional_amount_usd: float | None
    maturity_date: date | None
    confidence: float
    source_uri: str
    source_confidence: float
    page_or_section: str
    content_hash: str
    key_terms: dict[str, Any]
    collateral: list[str]
    guarantees: list[str]
    is_non_recourse: bool | None
    bankruptcy_remote_spv: bool | None

    def to_capital_csv_row(self) -> dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "deal_type": self.deal_type.value,
            "title": self.title,
            "parties": "|".join(self.parties),
            "primary_party": self.parties[0] if self.parties else "",
            "counterparty_roles": json.dumps(self.counterparty_roles, sort_keys=True),
            "announced_date": "",
            "effective_date": "",
            "notional_amount_usd": self.notional_amount_usd or "",
            "maturity_date": self.maturity_date.isoformat() if self.maturity_date else "",
            "currency": "USD",
            "key_terms": json.dumps(self.key_terms, sort_keys=True),
            "collateral": "|".join(self.collateral),
            "guarantees": "|".join(self.guarantees),
            "linked_projects": "",
            "linked_assets": "",
            "is_related_party": "",
            "concentration_risk_flag": "",
            "is_non_recourse": _bool_csv(self.is_non_recourse),
            "bankruptcy_remote_spv": _bool_csv(self.bankruptcy_remote_spv),
            "source_uri": self.source_uri,
            "source_type": SourceType.SEC_EDGAR.value,
            "source_confidence": self.source_confidence,
            "human_review_status": HumanReviewStatus.PENDING.value,
            "page_or_section": self.page_or_section,
            "content_hash": self.content_hash,
            "confidence": self.confidence,
        }

    def to_tranche_csv_row(self) -> dict[str, Any] | None:
        if self.deal_type not in {DealType.DEBT_FACILITY, DealType.BOND}:
            return None
        if self.notional_amount_usd is None:
            return None

        return {
            "deal_id": self.deal_id,
            "tranche_id": "primary",
            "name": _tranche_name(self.deal_type, self.key_terms),
            "seniority": _tranche_seniority(self.key_terms),
            "notional_usd": self.notional_amount_usd,
            "interest_rate": self.key_terms.get("interest_rate") or "",
            "maturity": self.maturity_date.isoformat() if self.maturity_date else "",
            "recourse": "false" if self.is_non_recourse else "",
            "collateral_description": " | ".join(self.collateral),
            "guarantors": "|".join(self.guarantees),
            "source_uri": self.source_uri,
            "source_type": SourceType.SEC_EDGAR.value,
            "source_confidence": self.source_confidence,
            "human_review_status": HumanReviewStatus.PENDING.value,
            "page_or_section": self.page_or_section,
            "content_hash": self.content_hash,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class EdgarAcquisitionSummary:
    """Rollup for one document acquisition run."""

    manifest_rows: int
    documents_attempted: int
    documents_downloaded: int
    documents_resumed: int
    deal_candidates: int
    tranche_candidates: int
    total_bytes: int
    workers: int
    sec_requests_per_second: float
    sec_domain_concurrency: int
    retry_attempts: int
    resume_enabled: bool
    forms: dict[str, int]
    deal_types: dict[str, int]
    errors: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EdgarAcquisitionBatch:
    """Downloaded documents, deal candidates, and summary."""

    documents: list[EdgarDocumentRecord]
    deal_candidates: list[DealCandidate]
    summary: EdgarAcquisitionSummary

    def write_inventory_csv(self, path: str | Path, *, merge_existing: bool = False) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "cik",
            "company_name",
            "form",
            "accession_number",
            "filing_date",
            "primary_document",
            "document_type",
            "parent_primary_document",
            "filing_url",
            "local_path",
            "content_hash",
            "byte_count",
            "text_char_count",
            "relevance_score",
            "relevance_reasons",
            "downloaded_at",
        ]
        rows = [document.to_csv_row() for document in self.documents]
        if merge_existing:
            rows = _merge_existing_csv_rows(output, rows, key_fields=("filing_url",))
        with output.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows({key: row.get(key, "") for key in fieldnames} for row in rows)
        return output

    def write_deals_csv(self, path: str | Path, *, merge_existing: bool = False) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "deal_id",
            "deal_type",
            "title",
            "parties",
            "primary_party",
            "counterparty_roles",
            "announced_date",
            "effective_date",
            "notional_amount_usd",
            "maturity_date",
            "currency",
            "key_terms",
            "collateral",
            "guarantees",
            "linked_projects",
            "linked_assets",
            "is_related_party",
            "concentration_risk_flag",
            "is_non_recourse",
            "bankruptcy_remote_spv",
            "source_uri",
            "source_type",
            "source_confidence",
            "human_review_status",
            "page_or_section",
            "content_hash",
            "confidence",
        ]
        rows = [candidate.to_capital_csv_row() for candidate in self.deal_candidates]
        if merge_existing:
            rows = _merge_existing_csv_rows(output, rows, key_fields=("deal_id",))
        with output.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows({key: row.get(key, "") for key in fieldnames} for row in rows)
        return output

    def write_tranches_csv(self, path: str | Path, *, merge_existing: bool = False) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "deal_id",
            "tranche_id",
            "name",
            "seniority",
            "notional_usd",
            "interest_rate",
            "maturity",
            "recourse",
            "collateral_description",
            "guarantors",
            "source_uri",
            "source_type",
            "source_confidence",
            "human_review_status",
            "page_or_section",
            "content_hash",
            "confidence",
        ]
        rows = [
            row
            for candidate in self.deal_candidates
            if (row := candidate.to_tranche_csv_row()) is not None
        ]
        if merge_existing:
            rows = _merge_existing_csv_rows(
                output,
                rows,
                key_fields=("deal_id", "tranche_id", "source_uri", "content_hash"),
            )
        with output.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows({key: row.get(key, "") for key in fieldnames} for row in rows)
        return output

    def write_summary_json(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(self.summary.to_dict(), indent=2, sort_keys=True))
        return output

    def write_outputs(
        self,
        output_dir: str | Path,
        *,
        merge_existing: bool = False,
    ) -> dict[str, str]:
        base = Path(output_dir)
        inventory = self.write_inventory_csv(
            base / "edgar_document_inventory.csv",
            merge_existing=merge_existing,
        )
        deals = self.write_deals_csv(base / "deals.csv", merge_existing=merge_existing)
        tranches = self.write_tranches_csv(
            base / "tranches.csv",
            merge_existing=merge_existing,
        )
        summary = self.write_summary_json(base / "edgar_document_acquisition.summary.json")
        return {
            "inventory_csv": str(inventory),
            "deals_csv": str(deals),
            "tranches_csv": str(tranches),
            "summary_json": str(summary),
        }


def _merge_existing_csv_rows(
    output: Path,
    new_rows: list[dict[str, Any]],
    *,
    key_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    if not output.exists() or output.stat().st_size == 0:
        return new_rows

    merged: dict[str, dict[str, Any]] = {}
    with output.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = _row_key(row, key_fields)
            if key:
                merged[key] = dict(row)
    for row in new_rows:
        key = _row_key(row, key_fields)
        if key:
            merged[key] = row
    return list(merged.values())


def _row_key(row: Mapping[str, Any], key_fields: tuple[str, ...]) -> str:
    return "|".join(str(row.get(field) or "").strip() for field in key_fields)


@dataclass(frozen=True)
class NotionalCandidate:
    """A dollar amount with the local context used to decide whether it is deal notional."""

    value_usd: float
    score: int
    positive_terms: list[str]
    rejected_terms: list[str]
    context_kind: str
    context_excerpt: str


@dataclass(frozen=True)
class _EdgarDocumentResult:
    index: int
    document: EdgarDocumentRecord | None
    candidate: DealCandidate | None
    resumed: bool
    error_key: str | None
    error: str | None


class SecArchiveClient:
    """Official SEC archive document fetcher."""

    def __init__(self, *, identity: str | None = None, timeout_seconds: float = 30.0) -> None:
        self.identity = identity or os.getenv("EDGAR_IDENTITY") or ""
        if not self.identity:
            raise ValueError(
                "Set EDGAR_IDENTITY before live SEC requests, e.g. "
                "'Your Name your.email@example.com'."
            )
        self.timeout_seconds = timeout_seconds

    def fetch_bytes(self, url: str) -> bytes:
        headers = {"User-Agent": self.identity, "Accept-Encoding": "gzip, deflate"}
        with httpx.Client(
            headers=headers, timeout=self.timeout_seconds, follow_redirects=True
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            return bytes(response.content)


def acquire_edgar_documents_from_manifest(
    manifest_csv: str | Path,
    *,
    output_dir: str | Path,
    fetch_bytes: FetchBytes | None = None,
    min_relevance_score: int = 75,
    limit: int | None = None,
    max_workers: int = 32,
    sec_requests_per_second: float = 8.0,
    sec_domain_concurrency: int = 8,
    retry_attempts: int = 3,
    retry_backoff_seconds: float = 0.5,
    resume: bool = True,
    write_outputs: bool = True,
) -> EdgarAcquisitionBatch:
    """
    Download prioritized EDGAR documents and emit pending-review deal candidates.

    The output directory can be passed directly to `scripts/ingest_capital_evidence.py`
    because this function writes a compatible `deals.csv`.
    """

    rows = _read_manifest_csv(Path(manifest_csv))
    selected_rows = _select_manifest_rows(
        rows,
        min_relevance_score=min_relevance_score,
        limit=limit,
    )
    fetcher = fetch_bytes or SecArchiveClient().fetch_bytes
    base_dir = Path(output_dir)
    limiter = DomainFetchLimiter(
        FetchConcurrencyConfig(
            max_workers=max_workers,
            sec_domain_concurrency=sec_domain_concurrency,
            sec_requests_per_second=sec_requests_per_second,
            retry_attempts=retry_attempts,
            retry_backoff_seconds=retry_backoff_seconds,
        )
    )
    worker_count = min(max(1, max_workers), max(1, len(selected_rows)))
    results: list[_EdgarDocumentResult] = []
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(
                _acquire_edgar_manifest_row,
                index,
                row,
                base_dir,
                fetcher,
                limiter,
                retry_attempts,
                retry_backoff_seconds,
                resume,
            )
            for index, row in enumerate(selected_rows)
        ]
        results = [future.result() for future in as_completed(futures)]

    results.sort(key=lambda result: result.index)
    documents = [result.document for result in results if result.document is not None]
    candidates = [result.candidate for result in results if result.candidate is not None]
    errors = {
        str(result.error_key): str(result.error)
        for result in results
        if result.error_key and result.error
    }

    summary = EdgarAcquisitionSummary(
        manifest_rows=len(rows),
        documents_attempted=len(selected_rows),
        documents_downloaded=len(documents),
        documents_resumed=sum(result.resumed for result in results),
        deal_candidates=len(candidates),
        tranche_candidates=sum(1 for candidate in candidates if candidate.to_tranche_csv_row()),
        total_bytes=sum(document.byte_count for document in documents),
        workers=worker_count,
        sec_requests_per_second=sec_requests_per_second,
        sec_domain_concurrency=sec_domain_concurrency,
        retry_attempts=retry_attempts,
        resume_enabled=resume,
        forms=dict(sorted(Counter(document.form for document in documents).items())),
        deal_types=dict(
            sorted(Counter(candidate.deal_type.value for candidate in candidates).items())
        ),
        errors=errors,
    )
    batch = EdgarAcquisitionBatch(
        documents=documents,
        deal_candidates=candidates,
        summary=summary,
    )
    if write_outputs:
        batch.write_outputs(base_dir)
    return batch


def _acquire_edgar_manifest_row(
    index: int,
    row: ManifestRow,
    base_dir: Path,
    fetcher: FetchBytes,
    limiter: DomainFetchLimiter,
    retry_attempts: int,
    retry_backoff_seconds: float,
    resume: bool,
) -> _EdgarDocumentResult:
    filing_url = row.get("filing_url", "")
    record_key = _record_key(row)
    if not filing_url:
        return _EdgarDocumentResult(
            index=index,
            document=None,
            candidate=None,
            resumed=False,
            error_key=record_key,
            error="Manifest row has no filing_url.",
        )
    try:
        local_path = _document_path(base_dir, row)
        resumed = resume and local_path.exists()
        if resumed:
            raw = local_path.read_bytes()
            downloaded_at = datetime.fromtimestamp(local_path.stat().st_mtime, UTC).isoformat()
        else:
            raw = fetch_with_retries(
                lambda: limiter.run(
                    filing_url,
                    lambda: fetcher(filing_url),
                ),
                attempts=retry_attempts,
                backoff_seconds=retry_backoff_seconds,
            )
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(raw)
            downloaded_at = datetime.now(UTC).isoformat()

        content_hash = Provenance.compute_content_hash(raw)
        text = normalize_document_text(raw)
        document = EdgarDocumentRecord(
            cik=row.get("cik", ""),
            company_name=row.get("company_name", ""),
            form=row.get("form", ""),
            accession_number=row.get("accession_number", ""),
            filing_date=row.get("filing_date") or None,
            primary_document=row.get("primary_document", ""),
            document_type=row.get("document_type") or "primary",
            parent_primary_document=row.get("parent_primary_document") or None,
            filing_url=filing_url,
            local_path=str(local_path),
            content_hash=content_hash,
            byte_count=len(raw),
            text_char_count=len(text),
            relevance_score=_int(row.get("relevance_score"), default=0),
            relevance_reasons=_split(row.get("relevance_reasons")),
            downloaded_at=downloaded_at,
        )
        return _EdgarDocumentResult(
            index=index,
            document=document,
            candidate=extract_deal_candidate(row, text, content_hash, local_path),
            resumed=resumed,
            error_key=None,
            error=None,
        )
    except Exception as exc:  # pragma: no cover - exact network/filesystem failures vary
        return _EdgarDocumentResult(
            index=index,
            document=None,
            candidate=None,
            resumed=False,
            error_key=record_key,
            error=str(exc),
        )


def extract_deal_candidate(
    manifest_row: Mapping[str, str],
    text: str,
    content_hash: str,
    local_path: str | Path,
) -> DealCandidate | None:
    """Extract a deterministic pending-review deal candidate from source text."""

    if _is_periodic_primary_report(manifest_row):
        return None

    classification = classify_agreement(manifest_row, text)
    if classification is None:
        return None

    deal_type, classification_reasons, base_confidence = classification
    amount_candidate = extract_deal_notional_candidate(text, deal_type=deal_type)
    if amount_candidate and amount_candidate.context_kind == "aggregate_lease_obligation":
        if deal_type != DealType.LEASE:
            classification_reasons = [
                *classification_reasons,
                "notional_context:aggregate_lease_obligation",
            ]
        deal_type = DealType.LEASE
    amount = amount_candidate.value_usd if amount_candidate else None
    maturity = extract_maturity_date(text)
    interest_rate = extract_interest_rate(text)
    company_name = manifest_row.get("company_name") or manifest_row.get("cik") or "unknown-company"
    counterparty_roles = extract_counterparty_roles(
        deal_type=deal_type,
        manifest_row=manifest_row,
        text=text,
        company_name=company_name,
    )
    parties = _parties_from_roles(company_name, counterparty_roles)
    collateral = extract_collateral_descriptions(text)
    guarantees = _guarantees_from_roles(counterparty_roles)
    is_non_recourse = _detect_non_recourse(text)
    bankruptcy_remote_spv = _detect_bankruptcy_remote_spv(text)
    spv_signal = _detect_spv_signal(text, counterparty_roles=counterparty_roles)
    source_uri = manifest_row.get("filing_url", "")
    accession = manifest_row.get("accession_number", "unknown-accession")
    deal_id = (
        f"edgar:{manifest_row.get('cik', 'unknown')}:{accession.replace('-', '')}:"
        f"{deal_type.value}:{content_hash[:12]}"
    )
    confidence = _candidate_confidence(
        base_confidence=base_confidence,
        has_amount=amount is not None,
        has_maturity=maturity is not None,
        has_interest_rate=interest_rate is not None,
    )
    key_terms = {
        "extraction_method": "deterministic_edgar_agreement_v1",
        "agreement_reasons": classification_reasons,
        "manifest_relevance_score": _int(manifest_row.get("relevance_score"), default=0),
        "manifest_relevance_reasons": _split(manifest_row.get("relevance_reasons")),
        "filing_form": manifest_row.get("form", ""),
        "filing_date": manifest_row.get("filing_date", ""),
        "accession_number": accession,
        "primary_document": manifest_row.get("primary_document", ""),
        "document_type": manifest_row.get("document_type") or "primary",
        "parent_primary_document": manifest_row.get("parent_primary_document", ""),
        "document_local_path": str(local_path),
        "interest_rate": interest_rate,
        "collateral_descriptions": collateral,
        "guarantees": guarantees,
        "non_recourse": bool(is_non_recourse),
        "bankruptcy_remote_spv": bool(bankruptcy_remote_spv),
        "spv": bool(spv_signal),
        "off_balance_sheet": bool(is_non_recourse or bankruptcy_remote_spv or spv_signal),
        "notional_extraction_method": (
            "contextual_deal_notional_v1" if amount_candidate else "no_contextual_notional"
        ),
        "notional_positive_terms": amount_candidate.positive_terms if amount_candidate else [],
        "notional_rejected_terms": amount_candidate.rejected_terms if amount_candidate else [],
        "notional_context_kind": amount_candidate.context_kind if amount_candidate else "",
        "notional_context_excerpt": amount_candidate.context_excerpt if amount_candidate else "",
        "counterparty_extraction_status": (
            "role_extracted" if counterparty_roles else "not_extracted"
        ),
        "counterparty_roles": counterparty_roles,
        "requires_llm_adjudication": True,
    }
    title = _candidate_title(manifest_row, deal_type)

    return DealCandidate(
        deal_id=deal_id,
        deal_type=deal_type,
        title=title,
        parties=parties,
        counterparty_roles=counterparty_roles,
        notional_amount_usd=amount,
        maturity_date=maturity,
        confidence=confidence,
        source_uri=source_uri,
        source_confidence=confidence,
        page_or_section=f"{manifest_row.get('form', '')} {accession} {manifest_row.get('primary_document', '')}".strip(),
        content_hash=content_hash,
        key_terms=key_terms,
        collateral=collateral,
        guarantees=guarantees,
        is_non_recourse=is_non_recourse,
        bankruptcy_remote_spv=bankruptcy_remote_spv,
    )


def classify_agreement(
    manifest_row: Mapping[str, str],
    text: str,
) -> tuple[DealType, list[str], float] | None:
    """Classify the agreement type using explicit source text and manifest metadata."""

    searchable = " ".join(
        [
            manifest_row.get("form", ""),
            manifest_row.get("items", ""),
            manifest_row.get("primary_document", ""),
            manifest_row.get("primary_document_description", ""),
            text[:120_000],
        ]
    ).lower()
    reasons: list[str] = []
    for deal_type, keywords, rule_reason in AGREEMENT_RULES:
        matched = [keyword for keyword in keywords if keyword in searchable]
        if matched:
            reasons.append(rule_reason)
            reasons.extend(f"keyword:{keyword}" for keyword in matched[:4])
            return deal_type, list(dict.fromkeys(reasons)), 0.72

    if _int(manifest_row.get("relevance_score"), default=0) >= 120 and extract_largest_notional_usd(
        text
    ):
        return DealType.OTHER, ["high manifest relevance plus disclosed notional"], 0.58

    return None


def _is_periodic_primary_report(manifest_row: Mapping[str, str]) -> bool:
    form = (manifest_row.get("form") or "").strip().upper()
    document_type = (manifest_row.get("document_type") or "primary").strip().lower()
    return document_type == "primary" and form in PERIODIC_REPORT_FORMS


def extract_counterparty_roles(
    *,
    deal_type: DealType,
    manifest_row: Mapping[str, str],
    text: str,
    company_name: str,
) -> dict[str, list[str]]:
    """Extract conservative role labels from explicit SEC agreement language."""

    roles: dict[str, list[str]] = {}
    normalized_company = company_name.strip()
    if deal_type == DealType.DEBT_FACILITY:
        _add_role(roles, "borrower", normalized_company)
        if _mentions_lenders(text):
            _add_role(roles, "lender", "lenders party thereto")
    elif deal_type == DealType.BOND:
        _add_role(roles, "issuer", normalized_company)
        _add_role(roles, "noteholder", "noteholders")
    elif deal_type == DealType.LEASE:
        _add_role(roles, "lessee", normalized_company)
    elif deal_type == DealType.PPA:
        _add_role(roles, "offtaker", normalized_company)
    elif deal_type == DealType.GUARANTEE:
        _add_role(roles, "guarantor", normalized_company)

    allowed_roles = _allowed_explicit_roles(deal_type)
    role_matches = _explicit_role_entities(text)
    for role, entities in role_matches.items():
        if role not in allowed_roles:
            continue
        for entity in entities:
            _add_role(roles, role, entity)
            if deal_type == DealType.DEBT_FACILITY and role in {
                "administrative_agent",
                "collateral_agent",
                "lender",
            }:
                _add_role(roles, "financier", entity)
            if deal_type == DealType.BOND and role == "trustee":
                _add_role(roles, "indenture_trustee", entity)

    return {role: entities for role, entities in roles.items() if entities}


def _explicit_role_entities(text: str) -> dict[str, list[str]]:
    snippet = text[:300_000]
    roles: dict[str, list[str]] = {}
    for match in ROLE_ENTITY_PATTERN.finditer(snippet):
        role = _normalized_role(match.group("role"))
        entity = _clean_entity_name(match.group("entity"), role=role)
        if entity:
            _add_role(roles, role, entity)
    return _compact_role_entities(roles)


def _allowed_explicit_roles(deal_type: DealType) -> set[str]:
    if deal_type == DealType.DEBT_FACILITY:
        return {"administrative_agent", "collateral_agent", "lender", "borrower", "guarantor"}
    if deal_type == DealType.BOND:
        return {"issuer", "trustee", "guarantor"}
    if deal_type == DealType.LEASE:
        return {"lessor", "lessee", "guarantor"}
    if deal_type == DealType.PPA:
        return {"buyer", "seller", "offtaker", "guarantor"}
    if deal_type == DealType.GUARANTEE:
        return {"guarantor", "borrower", "lender", "administrative_agent", "trustee"}
    return {
        "administrative_agent",
        "collateral_agent",
        "trustee",
        "lender",
        "lessor",
        "lessee",
        "buyer",
        "seller",
        "offtaker",
        "guarantor",
        "issuer",
        "borrower",
    }


def _normalized_role(raw_role: str) -> str:
    return raw_role.strip().lower().replace(" ", "_")


def _clean_entity_name(value: str, *, role: str | None = None) -> str:
    cleaned = " ".join(value.replace("\n", " ").split())
    cleaned = re.sub(
        r"\s*\((?:or any|including|together with|together,? with).*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"^.*?\b(?:by and among|by and between|among|between|with)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"^(and|or|the|each of|together with)\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"^(?:this\s+)?(?:credit agreement|indenture|agreement)?\s*"
        r"(?:by and )?(?:among|between)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"^(by and among|among|between)\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"^(?:agreement|credit agreement|indenture),?\s+(?:and\s+)?",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"^(?:the\s+)?(?:borrower|issuer|company|holdco),\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"^.*?\blenders?\s+(?:from\s+time\s+to\s+time\s+)?party\s+"
        r"(?:thereto|thereunder)\s+and\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    if re.search(r"\blenders?\s+party\b", cleaned, flags=re.IGNORECASE) and ", and " in cleaned:
        cleaned = cleaned.rsplit(", and ", maxsplit=1)[-1]
    cleaned = cleaned.strip(" ,;:\"'()[]")
    lower = cleaned.lower()
    rejected_prefixes = (
        "means ",
        "such ",
        "each ",
        "any ",
        "all ",
        "as applied ",
        "in the heading ",
        "c) ",
        "d) ",
        "e) ",
    )
    if lower.startswith(rejected_prefixes):
        return ""
    rejected_phrases = (
        " such ",
        " shall ",
        " will ",
        " which ",
        " benchmark ",
        " loans ",
        " loan or commitment",
        " commitment ",
        " required lenders",
        " other lenders",
        " notes for redemption",
        " trustee will",
        " administrative agent shall",
        " borrower or ",
        " subsidiaries",
        " qualifies",
        " applicable",
        " denominated",
        " redemption",
        " certificates",
        " successors and assigns",
        " alternative currency",
        " percentage of the lenders",
        " purchase at par",
    )
    padded = f" {lower} "
    if any(phrase in padded for phrase in rejected_phrases):
        return ""
    if not cleaned or not any(char.isalpha() for char in cleaned):
        return ""
    reject_markers = {
        "agreement",
        "credit agreement",
        "indenture",
        "exhibit",
        "schedule",
        "section",
        "borrower",
        "issuer",
        "lender",
        "trustee",
        "lessor",
        "lessee",
        "seller",
        "buyer",
        "bank, n.a.",
        "bank, national association",
    }
    if lower in reject_markers or len(cleaned) > 120:
        return ""
    if not _looks_like_counterparty_entity(cleaned, role=role):
        return ""
    return cleaned


def _looks_like_counterparty_entity(value: str, *, role: str | None = None) -> bool:
    lower = value.lower()
    if ENTITY_SUFFIX_PATTERN.search(value):
        return True
    if re.fullmatch(r"[A-Z][A-Z0-9&.\-/ ]{1,15}", value):
        generic_tokens = {
            "ABR",
            "SOFR",
            "RFR",
            "YEN",
            "LOAN",
            "LOANS",
            "NOTES",
            "DEBT",
            "LENDER",
            "LENDERS",
            "BORROWER",
            "ISSUER",
            "TRUSTEE",
        }
        words = set(re.findall(r"[A-Z0-9]+", value))
        return not bool(words & generic_tokens)
    if role in {
        "issuer",
        "borrower",
        "guarantor",
        "lessee",
        "lessor",
        "buyer",
        "seller",
        "offtaker",
    }:
        return bool(re.search(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4}\b", value)) and not any(
            token in lower for token in ("agreement", "section", "schedule", "exhibit")
        )
    return False


def _compact_role_entities(roles: dict[str, list[str]]) -> dict[str, list[str]]:
    compacted: dict[str, list[str]] = {}
    for role, entities in roles.items():
        keys = [_entity_key(entity) for entity in entities]
        for index, entity in enumerate(entities):
            key = keys[index]
            if not key:
                continue
            if any(
                index != other_index
                and key != other_key
                and len(key) + 4 <= len(other_key)
                and key in other_key
                for other_index, other_key in enumerate(keys)
            ):
                continue
            bucket = compacted.setdefault(role, [])
            if not any(_entity_key(existing) == key for existing in bucket):
                bucket.append(entity)
    return compacted


def _entity_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _mentions_lenders(text: str) -> bool:
    return bool(
        re.search(
            r"\b(lenders?\s+(party|from time to time|thereto|thereunder)|revolving lenders?|term lenders?)\b",
            text[:120_000],
            re.IGNORECASE,
        )
    )


def _add_role(roles: dict[str, list[str]], role: str, entity: str | None) -> None:
    normalized = (entity or "").strip()
    if not normalized:
        return
    bucket = roles.setdefault(role, [])
    if normalized not in bucket:
        bucket.append(normalized)


def _parties_from_roles(
    company_name: str,
    roles: Mapping[str, Sequence[str]],
) -> list[str]:
    parties: list[str] = []
    for entity in [company_name, *(entity for entities in roles.values() for entity in entities)]:
        if entity and entity not in parties:
            parties.append(entity)
    return parties or [company_name]


def extract_largest_notional_usd(text: str) -> float | None:
    """Return the largest dollar amount in the document that is at least $1M."""

    candidates = [
        _amount_to_usd(match.group("num"), match.group("unit")) for match in _amount_matches(text)
    ]
    candidates = [value for value in candidates if 1_000_000 <= value <= 10_000_000_000_000]
    return max(candidates) if candidates else None


def extract_deal_notional_usd(text: str, *, deal_type: DealType) -> float | None:
    """Return the best context-supported deal notional, excluding corporate scale metrics."""

    candidate = extract_deal_notional_candidate(text, deal_type=deal_type)
    return candidate.value_usd if candidate else None


def extract_deal_notional_candidate(text: str, *, deal_type: DealType) -> NotionalCandidate | None:
    """Return the best amount whose surrounding text looks like contract notional."""

    candidates: list[NotionalCandidate] = []
    seen: set[tuple[int, float]] = set()
    snippet = text[:300_000]
    for match in _amount_matches(snippet):
        value = _amount_to_usd(match.group("num"), match.group("unit"))
        if not 1_000_000 <= value <= 10_000_000_000_000:
            continue
        key = (match.start(), value)
        if key in seen:
            continue
        seen.add(key)
        context = _amount_sentence_context(snippet, match.start(), match.end()).lower()
        positive_terms = _notional_positive_terms(context, deal_type=deal_type)
        rejected_terms = [
            *_notional_rejected_terms(context),
            *_amount_specific_rejected_terms(match, value, context),
        ]
        series_candidate = _series_component_sum_candidate(
            snippet,
            match,
            aggregate_value=value,
            deal_type=deal_type,
        )
        if series_candidate:
            candidates.append(series_candidate)
        if rejected_terms or not positive_terms:
            continue
        score = len(positive_terms)
        candidates.append(
            NotionalCandidate(
                value_usd=value,
                score=score,
                positive_terms=positive_terms,
                rejected_terms=rejected_terms,
                context_kind=_notional_context_kind(context, deal_type=deal_type),
                context_excerpt=_short_context_excerpt(context),
            )
        )
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: (candidate.score, candidate.value_usd))


def _series_component_sum_candidate(
    text: str,
    aggregate_match: re.Match[str],
    *,
    aggregate_value: float,
    deal_type: DealType,
) -> NotionalCandidate | None:
    """Recover series-level principal sum when an aggregate unit is internally inconsistent."""

    if deal_type != DealType.BOND:
        return None
    if not _looks_like_scaled_billion_mismatch(aggregate_match, aggregate_value):
        return None
    window = text[aggregate_match.start() : aggregate_match.end() + 4_000]
    window_lower = window.lower()
    if "in two series" not in window_lower and "in three series" not in window_lower:
        return None

    component_values: list[float] = []
    component_terms: list[str] = []
    for match in _amount_matches(window):
        if match.start() == 0:
            continue
        value = _amount_to_usd(match.group("num"), match.group("unit"))
        if not 100_000_000 <= value <= aggregate_value / 10:
            continue
        context = _amount_sentence_context(window, match.start(), match.end()).lower()
        positive_terms = _notional_positive_terms(context, deal_type=deal_type)
        if not positive_terms or _notional_rejected_terms(context):
            continue
        component_values.append(value)
        component_terms.extend(positive_terms)

    if len(component_values) < 2:
        return None
    component_sum = sum(component_values)
    scaled_aggregate = aggregate_value / 1_000
    if not scaled_aggregate * 0.95 <= component_sum <= scaled_aggregate * 1.05:
        return None
    terms = list(dict.fromkeys([*component_terms, "series component principal sum"]))
    context_excerpt = _short_context_excerpt(
        " ".join(window.split())
        + " [aggregate billion unit scale mismatch; using source series principal sum]"
    )
    return NotionalCandidate(
        value_usd=component_sum,
        score=len(terms) + 4,
        positive_terms=terms,
        rejected_terms=[],
        context_kind="transaction_principal_series_sum",
        context_excerpt=context_excerpt,
    )


def _amount_sentence_context(text: str, start: int, end: int) -> str:
    before = max(
        text.rfind(".", 0, start),
        text.rfind(";", 0, start),
        text.rfind("\n", 0, start),
    )
    after_candidates = [
        index
        for index in (text.find(".", end), text.find(";", end), text.find("\n", end))
        if index != -1
    ]
    after = min(after_candidates) if after_candidates else min(len(text), end + 240)
    context_start = max(0, before + 1 if before != -1 else start - 120)
    context_end = min(len(text), after + 1)
    return text[context_start:context_end]


def _short_context_excerpt(context: str, *, max_length: int = 500) -> str:
    normalized = " ".join(context.split())
    return normalized[:max_length]


def _amount_matches(text: str) -> list[re.Match[str]]:
    patterns = [
        re.compile(
            r"(?:\$|usd\s*)\s*(?P<num>\d+(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*"
            r"(?P<unit>billion|bn|million|mm|thousand|k)?",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?P<num>\d+(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*"
            r"(?P<unit>billion|bn|million|mm)\s+"
            r"(?:dollars|principal|facility|commitment|notes|loans)",
            re.IGNORECASE,
        ),
    ]
    return [match for pattern in patterns for match in pattern.finditer(text[:300_000])]


def _notional_positive_terms(context: str, *, deal_type: DealType) -> list[str]:
    common_terms = {
        "aggregate principal amount": 3,
        "principal amount": 2,
        "facility": 1,
        "credit facility": 2,
        "term loan": 2,
        "revolving credit": 2,
        "loan": 1,
        "loans": 1,
        "notes due": 2,
        "senior notes": 2,
        "secured notes": 2,
        "offering": 1,
        "purchase price": 1,
        "lease": 1,
        "power purchase": 2,
        "guaranteed obligations": 2,
    }
    deal_terms: dict[DealType, dict[str, int]] = {
        DealType.DEBT_FACILITY: {
            "credit agreement": 2,
            "credit facility": 3,
            "term loan": 3,
            "revolving credit": 3,
            "aggregate commitments": 3,
            "revolving commitments": 3,
            "loan commitments": 3,
            "facility amount": 2,
            "borrowings": 1,
        },
        DealType.BOND: {
            "aggregate principal amount": 4,
            "senior notes": 3,
            "secured notes": 3,
            "notes due": 3,
            "indenture": 2,
        },
        DealType.LEASE: {
            "lease agreement": 3,
            "master lease": 3,
            "rent": 1,
            "tenant": 1,
        },
        DealType.PPA: {
            "power purchase agreement": 4,
            "energy purchase agreement": 3,
            "power supply agreement": 3,
            "ppa": 2,
        },
        DealType.GUARANTEE: {
            "guarantee agreement": 3,
            "guaranty agreement": 3,
            "guaranteed obligations": 3,
        },
        DealType.LAND_ACQUISITION: {
            "purchase and sale agreement": 3,
            "real property": 2,
            "land purchase": 2,
            "site acquisition": 2,
        },
    }
    weighted_terms = common_terms | deal_terms.get(deal_type, {})
    matches: list[str] = []
    for term, weight in weighted_terms.items():
        if term in context:
            matches.extend([term] * weight)
    return list(dict.fromkeys(matches))


def _notional_context_kind(context: str, *, deal_type: DealType) -> str:
    phrase_kind_rules = [
        (
            "aggregate_lease_obligation",
            (
                "future lease payments",
                "lease payments",
                "operating lease obligations",
                "finance lease obligations",
                "not yet recorded on our consolidated balance sheets",
                "not yet commenced",
            ),
        ),
        (
            "transaction_principal",
            (
                "aggregate principal amount",
                "principal amount",
                "senior notes",
                "secured notes",
                "notes due",
            ),
        ),
        (
            "transaction_facility",
            (
                "credit facility",
                "credit agreement",
                "term loan",
                "revolving credit",
                "aggregate commitments",
                "revolving commitments",
                "loan commitments",
            ),
        ),
        ("transaction_purchase_price", ("purchase price",)),
        ("transaction_power_purchase", ("power purchase", "ppa")),
    ]
    for kind, phrases in phrase_kind_rules:
        if any(phrase in context for phrase in phrases):
            return kind
    return "transaction_guarantee" if deal_type == DealType.GUARANTEE else "candidate_notional"


def _notional_rejected_terms(context: str) -> list[str]:
    rejected = [
        "assets under management",
        "aum",
        "capital expenditures",
        "principal payments on finance leases",
        "market capitalization",
        "enterprise value",
        "total assets",
        "total liabilities",
        "total consolidated indebtedness",
        "total revenues",
        "revenue",
        "net income",
        "adjusted ebitda",
        "cash and cash equivalents",
        "share repurchase",
        "common stock",
        "market value",
        "remaining performance obligations",
        "rpo",
        "investment commitment",
        "commitments to our",
        "commitments to ace",
        "capital raised",
        "the increase of",
        "increase of $",
        "we had $",
        "outstanding",
    ]
    matches = [term for term in rejected if term in context]
    if _looks_like_balance_sheet_debt_snapshot(context):
        matches.append("balance sheet debt snapshot")
    return matches


def _amount_specific_rejected_terms(
    match: re.Match[str],
    value_usd: float,
    context: str,
) -> list[str]:
    if _looks_like_scaled_billion_mismatch(match, value_usd) and (
        "in two series" in context or "in three series" in context
    ):
        return ["suspicious billion unit scale mismatch"]
    return []


def _looks_like_scaled_billion_mismatch(match: re.Match[str], value_usd: float) -> bool:
    unit = (match.group("unit") or "").lower()
    if unit not in {"billion", "bn"}:
        return False
    try:
        numeric = float(match.group("num").replace(",", ""))
    except ValueError:
        return False
    return numeric >= 1_000 and value_usd >= 1_000_000_000_000


def _looks_like_balance_sheet_debt_snapshot(context: str) -> bool:
    if any(
        transaction_term in context
        for transaction_term in (
            "being issued",
            "being offered",
            "notes being offered",
            "notes offering",
            "offering of",
            "issuance of",
            "issued $",
            "had issued",
            "has issued",
            "have issued",
            "we issued",
            "will issue",
        )
    ):
        return False
    if "aggregate principal amount" in context and re.search(
        r"\b(?:issuer|company|we|our subsidiaries|subsidiaries)\s+"
        r"(?:had|has|have)\s+(?:approximately\s+)?",
        context,
    ):
        return True
    if "as of " not in context:
        return False
    return any(
        snapshot_term in context
        for snapshot_term in (
            "aggregate principal amount of indebtedness",
            "principal amount of indebtedness",
            "indebtedness for borrowed money",
            "long-term debt",
            "total consolidated indebtedness",
        )
    )


def extract_maturity_date(text: str) -> date | None:
    """Find a date close to maturity/due/expiration language."""

    snippet = text[:300_000]
    date_pattern = (
        r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(?P<day>\d{1,2}),\s+(?P<year>\d{4})"
    )
    keyword_pattern = re.compile(
        rf"(?:matur(?:e|es|ity|ing)|due|expires?|expiration).{{0,120}}{date_pattern}",
        re.IGNORECASE | re.DOTALL,
    )
    match = keyword_pattern.search(snippet)
    if not match:
        return None
    month = MONTHS[match.group("month").lower()]
    return date(int(match.group("year")), month, int(match.group("day")))


def extract_interest_rate(text: str) -> float | None:
    """Extract an interest-rate-like percentage from debt agreement text."""

    pattern = re.compile(
        r"(?:bear(?:s|ing)?\s+interest|interest\s+(?:at|rate)|coupon|"
        r"SOFR\s+(?:plus|\+)|notes?\s+(?:bear(?:s|ing)?\s+interest|due)).{0,120}?"
        r"(?P<rate>\d{1,2}(?:\.\d+)?)\s*%",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text[:250_000])
    if not match:
        return None
    rate = float(match.group("rate"))
    rate_decimal = round(rate / 100, 6)
    if rate_decimal <= 0 or rate_decimal > MAX_EXTRACTED_INTEREST_RATE_DECIMAL:
        return None
    return rate_decimal


def extract_collateral_descriptions(text: str, *, max_descriptions: int = 3) -> list[str]:
    """Extract short source-text snippets that indicate collateral/security terms."""

    snippet = text[:300_000]
    patterns = [
        re.compile(r"\bsenior secured\b", re.IGNORECASE),
        re.compile(r"\bsecured by\b", re.IGNORECASE),
        re.compile(r"\bcollateral\b", re.IGNORECASE),
        re.compile(r"\bsecurity interest\b", re.IGNORECASE),
        re.compile(r"\bfirst(?:-|\s+)priority lien\b", re.IGNORECASE),
        re.compile(r"\bfirst(?:-|\s+)lien\b", re.IGNORECASE),
        re.compile(r"\bsecond(?:-|\s+)lien\b", re.IGNORECASE),
        re.compile(r"\bpledge(?:d|s)?\b", re.IGNORECASE),
    ]
    descriptions: list[str] = []
    seen: set[str] = set()
    for pattern in patterns:
        for match in pattern.finditer(snippet):
            context = _short_context_excerpt(
                _amount_sentence_context(snippet, match.start(), match.end()),
                max_length=260,
            )
            key = context.lower()
            if not context or key in seen:
                continue
            seen.add(key)
            descriptions.append(context)
            if len(descriptions) >= max_descriptions:
                return descriptions
    return descriptions


def _guarantees_from_roles(counterparty_roles: Mapping[str, Sequence[str]]) -> list[str]:
    guarantees: list[str] = []
    for role, entities in counterparty_roles.items():
        normalized_role = role.lower().replace("_", " ")
        if "guarant" not in normalized_role and "guarantee" not in normalized_role:
            continue
        for entity in entities:
            cleaned = str(entity).strip()
            if cleaned and cleaned not in guarantees:
                guarantees.append(cleaned)
    return guarantees


def _detect_non_recourse(text: str) -> bool | None:
    snippet = text[:300_000]
    if re.search(r"\bnon[-\s]?recourse\b", snippet, flags=re.IGNORECASE):
        return True
    return None


def _detect_bankruptcy_remote_spv(text: str) -> bool | None:
    snippet = text[:300_000]
    if re.search(r"\bbankruptcy[-\s]?remote\b", snippet, flags=re.IGNORECASE):
        return True
    if re.search(
        r"\bspecial purpose (?:entity|company|vehicle|subsidiar(?:y|ies))\b",
        snippet,
        flags=re.IGNORECASE,
    ):
        return True
    return None


def _detect_spv_signal(
    text: str,
    *,
    counterparty_roles: Mapping[str, Sequence[str]],
) -> bool:
    snippet = text[:300_000]
    if re.search(
        r"\b(?:spv|special purpose (?:entity|company|vehicle|subsidiar(?:y|ies)))\b",
        snippet,
        flags=re.IGNORECASE,
    ):
        return True
    role_entities = [entity for entities in counterparty_roles.values() for entity in entities]
    return any(_looks_like_spv_entity(str(entity)) for entity in role_entities)


def _looks_like_spv_entity(entity: str) -> bool:
    lower = entity.lower()
    return any(
        term in lower
        for term in (
            " spv",
            "special purpose",
            "financing",
            "funding",
            "issuer",
            "trust ",
            "asset",
            "receivables",
        )
    )


def _bool_csv(value: bool | None) -> str:
    if value is None:
        return ""
    return "true" if value else "false"


def _tranche_name(deal_type: DealType, key_terms: Mapping[str, Any]) -> str:
    context_kind = str(key_terms.get("notional_context_kind") or "").strip()
    if deal_type == DealType.BOND:
        return "Notes"
    if context_kind == "transaction_facility":
        return "Debt facility"
    if context_kind == "transaction_principal":
        return "Principal tranche"
    return "Primary tranche"


def _tranche_seniority(key_terms: Mapping[str, Any]) -> int:
    search = " ".join(
        [
            str(key_terms.get("notional_context_excerpt") or ""),
            str(key_terms.get("title") or ""),
            " ".join(str(term) for term in key_terms.get("collateral_descriptions") or []),
        ]
    ).lower()
    if "subordinated" in search:
        return 3
    if "mezzanine" in search or "second lien" in search:
        return 2
    return 1


def normalize_document_text(raw: bytes) -> str:
    """Decode and lightly normalize an EDGAR HTML/text document."""

    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        decoded = raw.decode("latin-1", errors="ignore")
    decoded = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", decoded)
    decoded = re.sub(r"(?i)<\s*br\s*/?\s*>|</\s*p\s*>|</\s*div\s*>", "\n", decoded)
    decoded = re.sub(r"(?s)<[^>]+>", " ", decoded)
    decoded = html.unescape(decoded)
    decoded = re.sub(r"[ \t\r\f\v]+", " ", decoded)
    decoded = re.sub(r"\n\s+", "\n", decoded)
    return decoded.strip()


def _candidate_confidence(
    *,
    base_confidence: float,
    has_amount: bool,
    has_maturity: bool,
    has_interest_rate: bool,
) -> float:
    confidence = base_confidence
    if has_amount:
        confidence += 0.07
    if has_maturity:
        confidence += 0.04
    if has_interest_rate:
        confidence += 0.03
    return round(min(confidence, 0.86), 4)


def _candidate_title(row: Mapping[str, str], deal_type: DealType) -> str:
    description = row.get("primary_document_description") or row.get("primary_document") or ""
    company = row.get("company_name") or row.get("cik") or "Unknown filer"
    if description:
        return f"{company} - {description}"
    return f"{company} - EDGAR {deal_type.value.replace('_', ' ')} candidate"


def _read_manifest_csv(path: Path) -> list[ManifestRow]:
    with path.open(newline="") as f:
        return [
            {key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(f)
        ]


def _select_manifest_rows(
    rows: Sequence[ManifestRow],
    *,
    min_relevance_score: int,
    limit: int | None,
) -> list[ManifestRow]:
    selected = [
        row for row in rows if _int(row.get("relevance_score"), default=0) >= min_relevance_score
    ]
    selected.sort(
        key=lambda row: (
            _int(row.get("relevance_score"), default=0),
            row.get("filing_date", ""),
            row.get("accession_number", ""),
        ),
        reverse=True,
    )
    return selected[:limit] if limit is not None else selected


def _document_path(output_dir: Path, row: Mapping[str, str]) -> Path:
    parsed = urlparse(row.get("filing_url", ""))
    filename = Path(parsed.path).name or row.get("primary_document") or "document.html"
    accession = row.get("accession_number", "unknown").replace("-", "")
    cik = row.get("cik", "unknown")
    return output_dir / "documents" / cik / accession / filename


def _record_key(row: Mapping[str, str]) -> str:
    return ":".join(
        [
            row.get("cik", "unknown"),
            row.get("accession_number", "unknown"),
            row.get("primary_document", "unknown"),
        ]
    )


def _amount_to_usd(number: str, unit: str | None) -> float:
    value = float(number.replace(",", ""))
    normalized_unit = (unit or "").lower()
    if normalized_unit in {"billion", "bn"}:
        return value * 1_000_000_000
    if normalized_unit in {"million", "mm"}:
        return value * 1_000_000
    if normalized_unit in {"thousand", "k"}:
        return value * 1_000
    return value


def _split(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.replace(";", "|").split("|") if part.strip()]


def _int(value: str | None, *, default: int) -> int:
    if not value:
        return default
    return int(float(value))
