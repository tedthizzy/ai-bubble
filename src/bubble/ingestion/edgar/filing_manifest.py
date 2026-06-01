"""
SEC filing manifest builder.

This is the first pass at a source-backed acquisition backlog: before the system
can claim ecosystem-scale coverage, it must know which filings and exhibits are
available for each CIK, which ones are Burry-relevant, and where each source came
from.
"""

from __future__ import annotations

import csv
import json
import os
import re
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, cast

import httpx

from bubble.ingestion.concurrency import (
    DomainFetchLimiter,
    FetchConcurrencyConfig,
    fetch_with_retries,
)
from bubble.models.base import Provenance, SourceType

SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_ARCHIVE_DOCUMENT_URL = (
    "https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_no_dash}/{primary_document}"
)
SEC_ARCHIVE_INDEX_URL = (
    "https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_no_dash}/index.json"
)

FetchJson = Callable[[str], Mapping[str, Any]]

FORM_BASE_SCORES: dict[str, int] = {
    "10-K": 100,
    "10-K/A": 95,
    "20-F": 95,
    "10-Q": 85,
    "10-Q/A": 80,
    "S-1": 95,
    "S-1/A": 85,
    "S-3": 85,
    "S-3ASR": 85,
    "424B2": 85,
    "424B3": 80,
    "424B5": 90,
    "8-K": 65,
    "8-K/A": 55,
    "6-K": 65,
}

ITEM_RELEVANCE: dict[str, tuple[int, str]] = {
    "1.01": (25, "material definitive agreement"),
    "1.02": (10, "agreement termination"),
    "2.03": (30, "direct financial obligation"),
    "2.04": (20, "triggering event or default"),
    "2.05": (10, "exit or disposal cost"),
    "2.06": (15, "material impairment"),
    "7.01": (10, "reg fd disclosure"),
    "8.01": (15, "other event disclosure"),
    "9.01": (20, "financial statements or exhibits"),
}

KEYWORD_RELEVANCE: dict[str, tuple[int, str]] = {
    "credit agreement": (25, "credit agreement"),
    "debt": (15, "debt disclosure"),
    "term loan": (25, "term loan"),
    "notes": (15, "debt securities"),
    "indenture": (25, "indenture"),
    "lease": (20, "lease obligation"),
    "guarantee": (20, "guarantee"),
    "collateral": (20, "collateral"),
    "securit": (20, "securitization"),
    "purchase agreement": (15, "purchase agreement"),
    "power purchase": (25, "power purchase agreement"),
    "ppa": (25, "power purchase agreement"),
    "data center": (30, "data center"),
    "datacenter": (30, "data center"),
    "artificial intelligence": (20, "AI infrastructure"),
    "ai infrastructure": (25, "AI infrastructure"),
    "gpu": (20, "GPU infrastructure"),
    "project finance": (25, "project finance"),
    "spv": (25, "SPV"),
    "special purpose": (20, "SPV"),
    "refinancing": (20, "refinancing"),
    "facility": (10, "facility"),
}

EXHIBIT_RELEVANCE: dict[str, tuple[int, str]] = {
    "2": (20, "material plan/acquisition agreement exhibit"),
    "4": (45, "indenture or security instrument exhibit"),
    "10": (65, "material contract exhibit"),
    "99": (10, "supplemental disclosure exhibit"),
}

EXHIBIT_TEXT_SUFFIXES = {".htm", ".html", ".txt"}
IGNORED_EXHIBIT_PREFIXES = (
    "xbrl",
    "schema",
    "cal_",
    "def_",
    "lab_",
    "pre_",
)


@dataclass(frozen=True)
class _FilingManifestResult:
    index: int
    cik: str
    records: list[FilingRecord]
    error: str | None


@dataclass(frozen=True)
class FilingRecord:
    """One SEC filing candidate with provenance and relevance metadata."""

    cik: str
    company_name: str
    ticker: str | None
    form: str
    accession_number: str
    filing_date: date | None
    report_date: date | None
    acceptance_datetime: str | None
    items: list[str]
    primary_document: str | None
    primary_document_description: str | None
    size_bytes: int | None
    is_xbrl: bool
    is_inline_xbrl: bool
    source_uri: str
    filing_url: str | None
    relevance_score: int
    relevance_reasons: list[str]
    provenance: Provenance
    document_type: str = "primary"
    parent_primary_document: str | None = None
    filing_detail_url: str | None = None

    @property
    def is_burry_relevant(self) -> bool:
        return self.relevance_score >= 75

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["filing_date"] = self.filing_date.isoformat() if self.filing_date else None
        data["report_date"] = self.report_date.isoformat() if self.report_date else None
        data["items"] = "|".join(self.items)
        data["relevance_reasons"] = "|".join(self.relevance_reasons)
        data["provenance"] = self.provenance.model_dump(mode="json")
        return data

    def to_csv_row(self) -> dict[str, Any]:
        row = self.to_dict()
        row.pop("provenance")
        row["provenance_source_uri"] = self.provenance.source_uri
        row["provenance_confidence"] = self.provenance.confidence
        row["provenance_content_hash"] = self.provenance.content_hash
        return row


@dataclass(frozen=True)
class FilingManifestSummary:
    """Coverage rollup for a source acquisition run."""

    entities_requested: int
    entities_returned: int
    total_filings: int
    total_document_rows: int
    burry_relevant_filings: int
    workers: int
    sec_requests_per_second: float
    sec_domain_concurrency: int
    retry_attempts: int
    include_exhibits: bool
    exhibit_index_workers: int
    documents_by_type: dict[str, int]
    forms: dict[str, int]
    top_relevance_reasons: dict[str, int]
    earliest_filing_date: str | None
    latest_filing_date: str | None
    errors: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FilingManifest:
    """Filing records plus their coverage summary."""

    records: list[FilingRecord]
    summary: FilingManifestSummary

    def prioritized_records(self) -> list[FilingRecord]:
        return sorted(
            self.records,
            key=lambda record: (
                record.relevance_score,
                record.filing_date or date.min,
                record.accession_number,
            ),
            reverse=True,
        )

    def write_csv(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "cik",
            "company_name",
            "ticker",
            "form",
            "accession_number",
            "filing_date",
            "report_date",
            "acceptance_datetime",
            "items",
            "primary_document",
            "primary_document_description",
            "size_bytes",
            "is_xbrl",
            "is_inline_xbrl",
            "source_uri",
            "filing_url",
            "filing_detail_url",
            "document_type",
            "parent_primary_document",
            "relevance_score",
            "relevance_reasons",
            "provenance_source_uri",
            "provenance_confidence",
            "provenance_content_hash",
        ]
        with output.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(record.to_csv_row() for record in self.prioritized_records())
        return output

    def write_summary_json(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(self.summary.to_dict(), indent=2, sort_keys=True))
        return output


class SecSubmissionsClient:
    """Small official SEC submissions API client with injectable fetcher for tests."""

    def __init__(self, *, identity: str | None = None, timeout_seconds: float = 30.0) -> None:
        self.identity: str = identity or os.getenv("EDGAR_IDENTITY") or ""
        if not self.identity:
            raise ValueError(
                "Set EDGAR_IDENTITY before live SEC requests, e.g. "
                "'Your Name your.email@example.com'."
            )
        self.timeout_seconds = timeout_seconds

    def fetch_json(self, url: str) -> Mapping[str, Any]:
        headers = {"User-Agent": self.identity, "Accept-Encoding": "gzip, deflate"}
        with httpx.Client(
            headers=headers, timeout=self.timeout_seconds, follow_redirects=True
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            return cast("Mapping[str, Any]", response.json())


def build_edgar_filing_manifest(
    ciks: Iterable[str],
    *,
    fetch_json: FetchJson | None = None,
    since: date | None = None,
    until: date | None = None,
    max_filings_per_cik: int | None = None,
    include_exhibits: bool = False,
    max_exhibits_per_filing: int = 25,
    exhibit_index_workers: int = 4,
    max_workers: int = 32,
    sec_requests_per_second: float = 8.0,
    sec_domain_concurrency: int = 8,
    retry_attempts: int = 3,
    retry_backoff_seconds: float = 0.5,
) -> FilingManifest:
    """
    Build a source-backed SEC filing manifest for the requested CIKs.

    The manifest does not extract deal terms yet. It creates the auditable backlog
    of filings that should be parsed next, with exact SEC URLs and relevance scores.
    """

    fetcher = fetch_json or SecSubmissionsClient().fetch_json
    requested_ciks = [_normalize_cik(cik) for cik in ciks]
    limiter = DomainFetchLimiter(
        FetchConcurrencyConfig(
            max_workers=max_workers,
            sec_domain_concurrency=sec_domain_concurrency,
            sec_requests_per_second=sec_requests_per_second,
            retry_attempts=retry_attempts,
            retry_backoff_seconds=retry_backoff_seconds,
        )
    )
    worker_count = min(max(1, max_workers), max(1, len(requested_ciks)))
    results: list[_FilingManifestResult] = []
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(
                _build_manifest_for_cik,
                index,
                cik,
                fetcher,
                limiter,
                since,
                until,
                max_filings_per_cik,
                retry_attempts,
                retry_backoff_seconds,
            )
            for index, cik in enumerate(requested_ciks)
        ]
        results = [future.result() for future in as_completed(futures)]

    results.sort(key=lambda result: result.index)
    primary_records = [record for result in results for record in result.records]
    records = list(primary_records)
    if include_exhibits:
        records.extend(
            _exhibit_records_for_filings(
                primary_records,
                fetcher=fetcher,
                limiter=limiter,
                max_exhibits_per_filing=max_exhibits_per_filing,
                max_workers=exhibit_index_workers,
                retry_attempts=retry_attempts,
                retry_backoff_seconds=retry_backoff_seconds,
            )
        )
    returned_entities = sum(bool(result.records) for result in results)
    errors = {result.cik: result.error for result in results if result.error}

    return FilingManifest(
        records=records,
        summary=_summarize_manifest(
            requested_count=len(requested_ciks),
            returned_count=returned_entities,
            records=records,
            errors=errors,
            workers=worker_count,
            sec_requests_per_second=sec_requests_per_second,
            sec_domain_concurrency=sec_domain_concurrency,
            retry_attempts=retry_attempts,
            include_exhibits=include_exhibits,
            exhibit_index_workers=exhibit_index_workers,
        ),
    )


def _build_manifest_for_cik(
    index: int,
    cik: str,
    fetcher: FetchJson,
    limiter: DomainFetchLimiter,
    since: date | None,
    until: date | None,
    max_filings_per_cik: int | None,
    retry_attempts: int,
    retry_backoff_seconds: float,
) -> _FilingManifestResult:
    source_uri = SEC_SUBMISSIONS_URL.format(cik=cik)
    try:
        payload = fetch_with_retries(
            lambda: limiter.run(
                source_uri,
                lambda: fetcher(source_uri),
            ),
            attempts=retry_attempts,
            backoff_seconds=retry_backoff_seconds,
        )
        records = _records_from_submission(
            payload,
            cik=cik,
            source_uri=source_uri,
            since=since,
            until=until,
            max_filings=max_filings_per_cik,
        )
        return _FilingManifestResult(
            index=index,
            cik=cik,
            records=records,
            error=None,
        )
    except Exception as exc:  # pragma: no cover - exact network failures vary
        return _FilingManifestResult(index=index, cik=cik, records=[], error=str(exc))


def _records_from_submission(
    payload: Mapping[str, Any],
    *,
    cik: str,
    source_uri: str,
    since: date | None,
    until: date | None,
    max_filings: int | None,
) -> list[FilingRecord]:
    company_name = str(payload.get("name") or f"CIK {cik}")
    ticker = _first_string(payload.get("tickers"))
    recent = _recent_filings(payload)
    forms = _string_list(recent.get("form"))
    records: list[FilingRecord] = []

    for index, form in enumerate(forms):
        filing_date = _optional_date(_value_at(recent, "filingDate", index))
        if since and filing_date and filing_date < since:
            continue
        if until and filing_date and filing_date > until:
            continue

        accession_number = _string_at(recent, "accessionNumber", index)
        primary_document = _optional_string(_value_at(recent, "primaryDocument", index))
        primary_description = _optional_string(_value_at(recent, "primaryDocDescription", index))
        items = _items(_optional_string(_value_at(recent, "items", index)))
        is_xbrl = _bool_at(recent, "isXBRL", index)
        is_inline_xbrl = _bool_at(recent, "isInlineXBRL", index)
        score, reasons = score_filing_relevance(
            form=form,
            items=items,
            primary_document=primary_document,
            primary_document_description=primary_description,
            is_xbrl=is_xbrl,
            is_inline_xbrl=is_inline_xbrl,
        )
        filing_url = _filing_url(cik, accession_number, primary_document)
        filing_detail_url = _filing_index_url(cik, accession_number)
        content_hash = Provenance.compute_content_hash(
            json.dumps(
                {
                    "cik": cik,
                    "source_uri": source_uri,
                    "accession_number": accession_number,
                    "form": form,
                    "filing_date": filing_date.isoformat() if filing_date else None,
                    "primary_document": primary_document,
                },
                sort_keys=True,
            )
        )
        provenance = Provenance(
            source_uri=source_uri,
            source_type=SourceType.SEC_EDGAR,
            page_or_section="SEC submissions recent filings",
            confidence=0.98,
            content_hash=content_hash,
        )
        records.append(
            FilingRecord(
                cik=cik,
                company_name=company_name,
                ticker=ticker,
                form=form,
                accession_number=accession_number,
                filing_date=filing_date,
                report_date=_optional_date(_value_at(recent, "reportDate", index)),
                acceptance_datetime=_optional_string(
                    _value_at(recent, "acceptanceDateTime", index)
                ),
                items=items,
                primary_document=primary_document,
                primary_document_description=primary_description,
                size_bytes=_optional_int(_value_at(recent, "size", index)),
                is_xbrl=is_xbrl,
                is_inline_xbrl=is_inline_xbrl,
                source_uri=source_uri,
                filing_url=filing_url,
                relevance_score=score,
                relevance_reasons=reasons,
                provenance=provenance,
                filing_detail_url=filing_detail_url,
            )
        )
        if max_filings is not None and len(records) >= max_filings:
            break

    return records


def score_filing_relevance(
    *,
    form: str,
    items: Sequence[str],
    primary_document: str | None,
    primary_document_description: str | None,
    is_xbrl: bool,
    is_inline_xbrl: bool,
) -> tuple[int, list[str]]:
    """Rank filings for Burry-style extraction priority."""

    normalized_form = form.upper()
    score = FORM_BASE_SCORES.get(normalized_form, 20)
    reasons = [f"form:{normalized_form}"] if normalized_form in FORM_BASE_SCORES else []

    for item in items:
        bonus = ITEM_RELEVANCE.get(item)
        if bonus:
            points, reason = bonus
            score += points
            reasons.append(f"item:{item}:{reason}")

    searchable_text = " ".join(
        part
        for part in [
            normalized_form,
            primary_document or "",
            primary_document_description or "",
            " ".join(items),
        ]
        if part
    ).lower()
    for keyword, (points, reason) in KEYWORD_RELEVANCE.items():
        if keyword in searchable_text:
            score += points
            reasons.append(f"keyword:{reason}")

    exhibit_number = _exhibit_number(primary_document)
    if exhibit_number:
        bonus = EXHIBIT_RELEVANCE.get(exhibit_number)
        if bonus:
            points, reason = bonus
            score += points
            reasons.append(f"exhibit:{exhibit_number}:{reason}")

    if normalized_form in {"10-K", "10-K/A", "10-Q", "10-Q/A", "20-F"} and (
        is_xbrl or is_inline_xbrl
    ):
        score += 10
        reasons.append("structured:xbrl")

    deduped_reasons = list(dict.fromkeys(reasons))
    return min(score, 200), deduped_reasons


def _exhibit_records_for_filings(
    filings: Sequence[FilingRecord],
    *,
    fetcher: FetchJson,
    limiter: DomainFetchLimiter,
    max_exhibits_per_filing: int,
    max_workers: int,
    retry_attempts: int,
    retry_backoff_seconds: float,
) -> list[FilingRecord]:
    if max_exhibits_per_filing <= 0:
        return []
    candidates = [filing for filing in filings if _should_fetch_exhibit_index(filing)]
    if not candidates:
        return []

    worker_count = min(max(1, max_workers), len(candidates))
    results: list[tuple[int, list[FilingRecord]]] = []
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(
                _fetch_exhibit_records_for_filing,
                index,
                filing,
                fetcher,
                limiter,
                max_exhibits_per_filing,
                retry_attempts,
                retry_backoff_seconds,
            )
            for index, filing in enumerate(candidates)
        ]
        results = [future.result() for future in as_completed(futures)]

    return [
        exhibit
        for _index, exhibits in sorted(results, key=lambda result: result[0])
        for exhibit in exhibits
    ]


def _fetch_exhibit_records_for_filing(
    index: int,
    filing: FilingRecord,
    fetcher: FetchJson,
    limiter: DomainFetchLimiter,
    max_exhibits_per_filing: int,
    retry_attempts: int,
    retry_backoff_seconds: float,
) -> tuple[int, list[FilingRecord]]:
    index_url = filing.filing_detail_url or _filing_index_url(filing.cik, filing.accession_number)
    try:
        payload = fetch_with_retries(
            lambda: limiter.run(
                index_url,
                lambda: fetcher(index_url),
            ),
            attempts=retry_attempts,
            backoff_seconds=retry_backoff_seconds,
        )
    except Exception:  # pragma: no cover - exact SEC archive failures vary
        return index, []

    items = _candidate_exhibit_items(payload, primary_document=filing.primary_document)
    return index, [
        _exhibit_record(filing, item, index_url) for item in items[:max_exhibits_per_filing]
    ]


def _exhibit_record(
    filing: FilingRecord,
    item: Mapping[str, Any],
    index_url: str,
) -> FilingRecord:
    document_name = str(item["name"])
    document_description = f"SEC exhibit {document_name}"
    score, reasons = score_filing_relevance(
        form=filing.form,
        items=filing.items,
        primary_document=document_name,
        primary_document_description=document_description,
        is_xbrl=False,
        is_inline_xbrl=False,
    )
    content_hash = Provenance.compute_content_hash(
        json.dumps(
            {
                "cik": filing.cik,
                "source_uri": index_url,
                "accession_number": filing.accession_number,
                "parent_primary_document": filing.primary_document,
                "primary_document": document_name,
            },
            sort_keys=True,
        )
    )
    provenance = Provenance(
        source_uri=index_url,
        source_type=SourceType.SEC_EDGAR,
        page_or_section="SEC archive filing directory index",
        confidence=0.95,
        content_hash=content_hash,
    )
    return FilingRecord(
        cik=filing.cik,
        company_name=filing.company_name,
        ticker=filing.ticker,
        form=filing.form,
        accession_number=filing.accession_number,
        filing_date=filing.filing_date,
        report_date=filing.report_date,
        acceptance_datetime=filing.acceptance_datetime,
        items=filing.items,
        primary_document=document_name,
        primary_document_description=document_description,
        size_bytes=_optional_int(item.get("size")),
        is_xbrl=False,
        is_inline_xbrl=False,
        source_uri=index_url,
        filing_url=_filing_url(filing.cik, filing.accession_number, document_name),
        relevance_score=score,
        relevance_reasons=reasons,
        provenance=provenance,
        document_type="exhibit",
        parent_primary_document=filing.primary_document,
        filing_detail_url=index_url,
    )


def _should_fetch_exhibit_index(record: FilingRecord) -> bool:
    if not record.filing_detail_url or record.document_type != "primary":
        return False
    form = record.form.upper()
    exhibit_heavy_forms = {
        "8-K",
        "8-K/A",
        "10-K",
        "10-K/A",
        "10-Q",
        "10-Q/A",
        "20-F",
        "6-K",
        "S-1",
        "S-1/A",
        "S-3",
        "S-3ASR",
        "424B2",
        "424B3",
        "424B5",
    }
    return record.relevance_score >= 75 or form in exhibit_heavy_forms


def _candidate_exhibit_items(
    payload: Mapping[str, Any],
    *,
    primary_document: str | None,
) -> list[Mapping[str, Any]]:
    directory = payload.get("directory")
    if not isinstance(directory, Mapping):
        return []
    raw_items = directory.get("item")
    if isinstance(raw_items, Mapping):
        raw_sequence: Sequence[object] = [raw_items]
    elif isinstance(raw_items, Sequence) and not isinstance(raw_items, str):
        raw_sequence = raw_items
    else:
        return []

    items: list[Mapping[str, Any]] = []
    for raw_item in raw_sequence:
        if not isinstance(raw_item, Mapping):
            continue
        name = _optional_string(raw_item.get("name"))
        if name and _is_candidate_exhibit_document(name, primary_document):
            items.append(cast("Mapping[str, Any]", raw_item))
    return items


def _is_candidate_exhibit_document(
    document_name: str,
    primary_document: str | None,
) -> bool:
    normalized = document_name.strip().lower()
    if not normalized or normalized.endswith("/"):
        return False
    if primary_document and normalized == primary_document.strip().lower():
        return False
    if any(normalized.startswith(prefix) for prefix in IGNORED_EXHIBIT_PREFIXES):
        return False
    suffix = Path(normalized).suffix
    if suffix and suffix not in EXHIBIT_TEXT_SUFFIXES:
        return False
    return _exhibit_number(document_name) in EXHIBIT_RELEVANCE


def _summarize_manifest(
    *,
    requested_count: int,
    returned_count: int,
    records: Sequence[FilingRecord],
    errors: dict[str, str],
    workers: int,
    sec_requests_per_second: float,
    sec_domain_concurrency: int,
    retry_attempts: int,
    include_exhibits: bool,
    exhibit_index_workers: int,
) -> FilingManifestSummary:
    primary_records = [record for record in records if record.document_type == "primary"]
    summary_filings = primary_records or list(records)
    form_counts = Counter(record.form for record in summary_filings)
    document_type_counts = Counter(record.document_type for record in records)
    reason_counts = Counter(reason for record in records for reason in record.relevance_reasons)
    filing_dates = sorted(record.filing_date for record in summary_filings if record.filing_date)
    return FilingManifestSummary(
        entities_requested=requested_count,
        entities_returned=returned_count,
        total_filings=len(summary_filings),
        total_document_rows=len(records),
        burry_relevant_filings=sum(record.is_burry_relevant for record in summary_filings),
        workers=workers,
        sec_requests_per_second=sec_requests_per_second,
        sec_domain_concurrency=sec_domain_concurrency,
        retry_attempts=retry_attempts,
        include_exhibits=include_exhibits,
        exhibit_index_workers=exhibit_index_workers,
        documents_by_type=dict(sorted(document_type_counts.items())),
        forms=dict(sorted(form_counts.items())),
        top_relevance_reasons=dict(reason_counts.most_common(15)),
        earliest_filing_date=filing_dates[0].isoformat() if filing_dates else None,
        latest_filing_date=filing_dates[-1].isoformat() if filing_dates else None,
        errors=errors,
    )


def _normalize_cik(cik: str) -> str:
    digits = "".join(ch for ch in str(cik) if ch.isdigit())
    if not digits:
        raise ValueError(f"Invalid CIK: {cik}")
    return digits.zfill(10)


def _recent_filings(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    filings = payload.get("filings")
    if not isinstance(filings, Mapping):
        return {}
    recent = filings.get("recent")
    if not isinstance(recent, Mapping):
        return {}
    return cast("Mapping[str, Any]", recent)


def _value_at(recent: Mapping[str, Any], key: str, index: int) -> object | None:
    values = recent.get(key)
    if not isinstance(values, Sequence) or isinstance(values, str):
        return None
    if index >= len(values):
        return None
    return cast("object", values[index])


def _string_at(recent: Mapping[str, Any], key: str, index: int) -> str:
    value = _optional_string(_value_at(recent, key, index))
    if not value:
        raise ValueError(f"SEC submissions row missing required field: {key}")
    return value


def _string_list(value: object | None) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    return [str(item) for item in value]


def _first_string(value: object | None) -> str | None:
    values = _string_list(value)
    return values[0] if values else None


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_date(value: object | None) -> date | None:
    text = _optional_string(value)
    if not text:
        return None
    return date.fromisoformat(text[:10])


def _optional_int(value: object | None) -> int | None:
    text = _optional_string(value)
    if not text:
        return None
    return int(float(text.replace(",", "")))


def _bool_at(recent: Mapping[str, Any], key: str, index: int) -> bool:
    value = _value_at(recent, key, index)
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def _items(raw_items: str | None) -> list[str]:
    if not raw_items:
        return []
    return [item.strip() for item in raw_items.replace(",", " ").split() if item.strip()]


def _filing_url(cik: str, accession_number: str, primary_document: str | None) -> str | None:
    if not primary_document:
        return None
    return SEC_ARCHIVE_DOCUMENT_URL.format(
        cik_int=str(int(cik)),
        accession_no_dash=accession_number.replace("-", ""),
        primary_document=primary_document,
    )


def _filing_index_url(cik: str, accession_number: str) -> str:
    return SEC_ARCHIVE_INDEX_URL.format(
        cik_int=str(int(cik)),
        accession_no_dash=accession_number.replace("-", ""),
    )


def _exhibit_number(document_name: str | None) -> str | None:
    if not document_name:
        return None
    normalized = Path(document_name.strip().lower()).name
    for match in re.finditer(r"ex(?:hibit)?[-_ ]?(?P<number>\d{1,3})", normalized):
        start = match.start()
        if start > 0 and normalized[start - 1].isalpha() and normalized[start - 1] != "d":
            continue
        raw_number = match.group("number")
        if raw_number.startswith("10"):
            return "10"
        if raw_number.startswith("99"):
            return "99"
        if raw_number in EXHIBIT_RELEVANCE:
            return raw_number
    return None
