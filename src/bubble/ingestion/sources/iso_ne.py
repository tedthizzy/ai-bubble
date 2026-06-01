"""ISO New England source resolvers for public interconnection queue artifacts."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from bubble.models.base import SourceType

ISO_NE_PUBLIC_QUEUE_URL = "https://irtt.iso-ne.com/reports/external"
ISO_NE_PUBLIC_QUEUE_EXPORT_URL = "https://irtt.iso-ne.com/reports/exportpublicqueue"
DEFAULT_ISO_NE_USER_AGENT = "bubble-forensic-source-acquisition/0.1"
_REPORT_DATE_PATTERN = re.compile(r"ReportDate='\s*\+\s*(\d+)")
_AS_OF_PATTERN = re.compile(r"As of:\s*([^<]+)")

TextFetcher = Callable[[str], str]


@dataclass(frozen=True)
class IsoNePublicQueueDocument:
    """Resolved ISO-NE public queue export metadata."""

    report_date_ticks: str
    as_of: str

    @property
    def url(self) -> str:
        return (
            f"{ISO_NE_PUBLIC_QUEUE_EXPORT_URL}?ReportDate={self.report_date_ticks}"
            "&Status=&Jurisdiction="
        )


def latest_iso_ne_public_queue_catalog_row(
    *,
    fetch_text: TextFetcher | None = None,
) -> dict[str, str]:
    """Resolve ISO-NE's current public queue export into a source catalog row."""

    document = resolve_latest_iso_ne_public_queue_document(fetch_text=fetch_text)
    return {
        "source_id": f"iso-ne-public-queue-{document.report_date_ticks}",
        "corpus": "queue_records",
        "source_uri": document.url,
        "source_type": SourceType.GRID_QUEUE.value,
        "parser": "xlsx",
        "document_id": f"iso_ne_public_queue_{document.report_date_ticks}",
        "entity_id": "",
        "project_id": "",
        "filing_accession": "",
        "meta_publisher": "ISO New England",
        "meta_title": "ISO-NE Public Interconnection Request Queue",
        "meta_as_of": document.as_of,
        "meta_resolved_from_uri": ISO_NE_PUBLIC_QUEUE_URL,
        "meta_file_extension": "xlsx",
        "meta_http_header_cookie": "AspxAutoDetectCookieSupport=1",
        "meta_xlsx_required_value_columns": "Position|Alternative Name",
    }


def resolve_latest_iso_ne_public_queue_document(
    *,
    fetch_text: TextFetcher | None = None,
) -> IsoNePublicQueueDocument:
    """Return the current ISO-NE export token and visible as-of date."""

    html = (fetch_text or _fetch_text)(ISO_NE_PUBLIC_QUEUE_URL)
    report_date_match = _REPORT_DATE_PATTERN.search(html)
    if not report_date_match:
        raise ValueError("ISO-NE public queue page did not include an export ReportDate")
    as_of_match = _AS_OF_PATTERN.search(html)
    as_of = " ".join(as_of_match.group(1).split()) if as_of_match else ""
    return IsoNePublicQueueDocument(report_date_ticks=report_date_match.group(1), as_of=as_of)


def _fetch_text(url: str) -> str:
    headers = {
        "User-Agent": DEFAULT_ISO_NE_USER_AGENT,
        "Cookie": "AspxAutoDetectCookieSupport=1",
    }
    with httpx.Client(timeout=45.0, follow_redirects=True) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        return response.text
