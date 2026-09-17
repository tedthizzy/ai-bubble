"""Discover SEC exhibit candidates from already acquired primary filing HTML.

This is a local discovery pass, not proof that every exhibit in an accession was
linked from its primary filing. SEC archive index.json remains the completeness
source for parents with no links, missing local HTML, or unlinked exhibits.
"""

from __future__ import annotations

import gzip
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast
from urllib.parse import unquote, urljoin, urlparse

from lxml import html as lxml_html

from bubble.ingestion.edgar.filing_manifest import (
    EXHIBIT_RELEVANCE,
    IGNORED_EXHIBIT_PREFIXES,
    FilingManifest,
    FilingManifestSummary,
    FilingRecord,
    _exhibit_number,
    _is_candidate_exhibit_document,
    read_filing_manifest_csv,
    score_filing_relevance,
)
from bubble.models.base import Provenance, SourceType

if TYPE_CHECKING:
    from collections.abc import Iterable

EXHIBIT_LABEL = re.compile(
    r"^\s*(?:exhibit\s*(?:no\.?|number)?\s*)?(10|21|22|99|2|4)"
    r"(?:\s*[.\-]\s*\d+)?(?=\s|[*†(]|$)",
    re.IGNORECASE,
)
TEXT_SUFFIXES = {".htm", ".html", ".txt"}


@dataclass(frozen=True)
class OfflineExhibitResult:
    manifest: FilingManifest
    coverage: dict[str, object]


def discover_offline_exhibits(
    manifest_csv: str | Path,
    documents_dir: str | Path,
    *,
    min_parent_relevance_score: int = 75,
    max_exhibits_per_filing: int | None = None,
) -> OfflineExhibitResult:
    """Create an exhibit manifest without making any SEC or other network calls."""
    if max_exhibits_per_filing is not None and max_exhibits_per_filing < 1:
        raise ValueError("max_exhibits_per_filing must be positive or None")

    parents = [
        record
        for record in read_filing_manifest_csv(manifest_csv)
        if record.document_type == "primary"
        and record.filing_url
        and record.primary_document
        and record.relevance_score >= min_parent_relevance_score
    ]
    base = Path(documents_dir)
    records: list[FilingRecord] = []
    missing: list[str] = []
    parse_errors: dict[str, str] = {}
    no_links: list[str] = []
    truncated: list[str] = []
    parsed = 0
    compressed = 0

    for parent in parents:
        key = f"{parent.cik}:{parent.accession_number}:{parent.primary_document}"
        local = _local_document_path(base, parent)
        if not local.is_file():
            compressed_path = local.with_name(local.name + ".gz")
            if not compressed_path.is_file():
                missing.append(key)
                continue
            local = compressed_path
        try:
            if local.suffix == ".gz":
                with gzip.open(local, "rb") as compressed_file:
                    raw = compressed_file.read()
            else:
                raw = local.read_bytes()
            # Parent selection above guarantees a filing URL.
            links = discover_exhibit_links(raw, cast("str", parent.filing_url))
        except (OSError, EOFError, ValueError, TypeError) as exc:
            parse_errors[key] = f"{type(exc).__name__}: {exc}"
            continue
        parsed += 1
        compressed += local.suffix == ".gz"
        if not links:
            no_links.append(key)
        if max_exhibits_per_filing is not None and len(links) > max_exhibits_per_filing:
            truncated.append(key)
            links = links[:max_exhibits_per_filing]
        records.extend(_record_for_link(parent, name, number) for name, number in links)

    dates = sorted(parent.filing_date for parent in parents if parent.filing_date)
    reasons = Counter(reason for record in records for reason in record.relevance_reasons)
    summary = FilingManifestSummary(
        entities_requested=len(parents),
        entities_returned=len(parents) - len(missing) - len(parse_errors),
        total_filings=len(parents),
        total_document_rows=len(records),
        burry_relevant_filings=sum(parent.is_burry_relevant for parent in parents),
        workers=1,
        sec_requests_per_second=0.0,
        sec_domain_concurrency=0,
        retry_attempts=0,
        include_exhibits=True,
        exhibit_index_workers=0,
        documents_by_type={"exhibit": len(records)},
        forms=dict(sorted(Counter(parent.form for parent in parents).items())),
        top_relevance_reasons=dict(reasons.most_common(15)),
        earliest_filing_date=dates[0].isoformat() if dates else None,
        latest_filing_date=dates[-1].isoformat() if dates else None,
        errors=parse_errors,
    )
    coverage: dict[str, object] = {
        "primary_manifest": str(manifest_csv),
        "documents_dir": str(base),
        "selected_parent_filings": len(parents),
        "parsed_parent_filings": parsed,
        "parsed_compressed_parent_filings": compressed,
        "parsed_plain_parent_filings": parsed - compressed,
        "missing_local_parent_filings": len(missing),
        "parse_error_parent_filings": len(parse_errors),
        "parents_with_no_exhibit_links": len(no_links),
        "parents_truncated_by_limit": len(truncated),
        "discovered_exhibit_rows": len(records),
        "missing_local_parent_keys": missing,
        "parse_errors": parse_errors,
        "no_exhibit_link_parent_keys": no_links,
        "truncated_parent_keys": truncated,
        "completeness_limit": (
            "Primary HTML can omit, incorporate by reference, or fail to link exhibits. "
            "Only the SEC filing directory index can establish the accession's full file list."
        ),
    }
    return OfflineExhibitResult(FilingManifest(records, summary), coverage)


def discover_exhibit_links(raw_html: bytes, filing_url: str) -> list[tuple[str, str]]:
    """Return same-accession text exhibit filenames and their 2/4/10/21/22/99 class."""
    document = lxml_html.fromstring(raw_html)
    filing_path = urlparse(filing_url).path
    filing_dir = filing_path.rsplit("/", 1)[0] + "/"
    primary_name = Path(filing_path).name.lower()
    candidates: dict[str, str] = {}

    for anchor in document.iter("a"):
        href = anchor.get("href")
        if not href:
            continue
        parsed = urlparse(urljoin(filing_url, href))
        if parsed.scheme != "https" or parsed.netloc.lower() not in {"www.sec.gov", "sec.gov"}:
            continue
        candidate_path = unquote(parsed.path)
        if not candidate_path.startswith(filing_dir) or "/" in candidate_path[len(filing_dir) :]:
            continue
        name = Path(candidate_path).name
        if (
            not name
            or name.lower() == primary_name
            or Path(name).suffix.lower() not in TEXT_SUFFIXES
        ):
            continue
        if any(name.lower().startswith(prefix) for prefix in IGNORED_EXHIBIT_PREFIXES):
            continue

        from_name = _exhibit_number(name)
        label_match = EXHIBIT_LABEL.match(
            " ".join(cast("Iterable[str]", anchor.itertext())).strip()
        )
        from_label = label_match.group(1) if label_match else None
        number = from_name or from_label
        if number not in EXHIBIT_RELEVANCE:
            continue
        if from_name and not _is_candidate_exhibit_document(name, primary_name):
            continue
        candidates.setdefault(name, number)

    return sorted(candidates.items(), key=lambda entry: entry[0].lower())


def _local_document_path(base: Path, parent: FilingRecord) -> Path:
    assert parent.filing_url and parent.primary_document
    suffix = Path(urlparse(parent.filing_url).path).name
    return base / parent.cik / parent.accession_number.replace("-", "") / suffix


def _record_for_link(parent: FilingRecord, name: str, number: str) -> FilingRecord:
    assert parent.filing_url and parent.primary_document
    parent_url = parent.filing_url
    score_name = name if _exhibit_number(name) else f"ex{number}-{name}"
    score, reasons = score_filing_relevance(
        form=parent.form,
        items=parent.items,
        primary_document=score_name,
        primary_document_description=f"SEC exhibit {name}",
        is_xbrl=False,
        is_inline_xbrl=False,
    )
    content_hash = Provenance.compute_content_hash(
        json.dumps(
            {
                "source_uri": parent_url,
                "accession_number": parent.accession_number,
                "parent_primary_document": parent.primary_document,
                "exhibit_name": name,
                "exhibit_number": number,
            },
            sort_keys=True,
        )
    )
    return FilingRecord(
        cik=parent.cik,
        company_name=parent.company_name,
        ticker=parent.ticker,
        form=parent.form,
        accession_number=parent.accession_number,
        filing_date=parent.filing_date,
        report_date=parent.report_date,
        acceptance_datetime=parent.acceptance_datetime,
        items=parent.items,
        primary_document=name,
        primary_document_description=f"SEC exhibit {name}",
        size_bytes=None,
        is_xbrl=False,
        is_inline_xbrl=False,
        source_uri=parent_url,
        filing_url=urljoin(parent_url, name),
        relevance_score=score,
        relevance_reasons=reasons,
        provenance=Provenance(
            source_uri=parent_url,
            source_type=SourceType.SEC_EDGAR,
            page_or_section="Primary filing HTML exhibit link",
            confidence=0.85,
            content_hash=content_hash,
        ),
        document_type="exhibit",
        parent_primary_document=parent.primary_document,
        filing_detail_url=parent.filing_detail_url,
    )
