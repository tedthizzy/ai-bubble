"""EIA source resolvers for live public energy infrastructure artifacts."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from bubble.models.base import SourceType

EIA_860M_INDEX_URL = "https://www.eia.gov/electricity/data/eia860m/index.php"
DEFAULT_EIA_USER_AGENT = "bubble-forensic-source-acquisition/0.1"
_GENERATOR_XLSX_PATTERN = re.compile(r"/electricity/data/eia860m/.+generator\d{4}\.xlsx$")

TextFetcher = Callable[[str], str]
UrlAvailable = Callable[[str], bool]


@dataclass(frozen=True)
class Eia860mDocument:
    """Resolved EIA 860M workbook metadata."""

    label: str
    url: str
    release_date: str
    next_release_date: str

    @property
    def slug(self) -> str:
        return "-".join(self.label.lower().split())


def latest_eia_860m_catalog_row(
    *,
    fetch_text: TextFetcher | None = None,
    url_available: UrlAvailable | None = None,
) -> dict[str, str]:
    """Resolve the newest downloadable EIA 860M generator inventory workbook."""

    document = resolve_latest_eia_860m_document(
        fetch_text=fetch_text,
        url_available=url_available,
    )
    return {
        "source_id": f"eia-860m-generator-inventory-{document.slug}",
        "corpus": "equipment_records",
        "source_uri": document.url,
        "source_type": SourceType.EIA.value,
        "parser": "xlsx",
        "document_id": f"eia_860m_generator_inventory_{document.slug.replace('-', '_')}",
        "entity_id": "",
        "project_id": "",
        "filing_accession": "",
        "meta_publisher": "U.S. Energy Information Administration",
        "meta_title": f"EIA 860M {document.label} Generator Inventory",
        "meta_release_date": document.release_date,
        "meta_next_release_date": document.next_release_date,
        "meta_resolved_from_uri": EIA_860M_INDEX_URL,
        "meta_xlsx_required_value_columns": "Entity ID|Plant ID",
    }


def resolve_latest_eia_860m_document(
    *,
    fetch_text: TextFetcher | None = None,
    url_available: UrlAvailable | None = None,
) -> Eia860mDocument:
    """Return the first current EIA 860M workbook link that is actually downloadable."""

    html = (fetch_text or _fetch_text)(EIA_860M_INDEX_URL)
    soup = BeautifulSoup(html, "html.parser")
    release_date, next_release_date = _release_dates(soup)
    available = url_available or _url_available
    candidates = _candidate_links(soup)
    for label, url in candidates:
        if available(url):
            return Eia860mDocument(
                label=label,
                url=url,
                release_date=release_date,
                next_release_date=next_release_date,
            )
    raise ValueError("EIA 860M index did not contain a downloadable generator workbook")


def _fetch_text(url: str) -> str:
    headers = {"User-Agent": DEFAULT_EIA_USER_AGENT}
    with httpx.Client(timeout=45.0, follow_redirects=True) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        return response.text


def _url_available(url: str) -> bool:
    headers = {"User-Agent": DEFAULT_EIA_USER_AGENT}
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.head(url, headers=headers)
    content_type = response.headers.get("content-type", "").lower()
    return response.status_code == 200 and "spreadsheet" in content_type


def _candidate_links(soup: BeautifulSoup) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        absolute_url = urljoin(EIA_860M_INDEX_URL, href)
        if not _GENERATOR_XLSX_PATTERN.search(href):
            continue
        label = _link_label(anchor, absolute_url)
        if label:
            candidates.append((label, absolute_url))
    return candidates


def _link_label(anchor: Any, url: str) -> str:
    title = str(anchor.get("title") or "").strip()
    if title.startswith("EIA 860M "):
        return title.removeprefix("EIA 860M ").strip()
    match = re.search(r"/([a-z]+)_generator(\d{4})\.xlsx$", url)
    if not match:
        return ""
    month, year = match.groups()
    return f"{month.title()} {year}"


def _release_dates(soup: BeautifulSoup) -> tuple[str, str]:
    release_date = ""
    next_release_date = ""
    labels = soup.find_all(class_="label")
    for label in labels:
        text = " ".join(label.get_text(" ").split())
        date_node = label.find_next(class_="date")
        date_text = " ".join(date_node.get_text(" ").split()) if date_node else ""
        if text == "Release Date:":
            release_date = date_text
        elif text == "Next Release Date:":
            next_release_date = date_text
    return release_date, next_release_date
