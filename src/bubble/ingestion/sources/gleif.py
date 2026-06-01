"""GLEIF source resolvers for public legal-entity ownership relationship records."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

import httpx

from bubble.models.base import SourceType

GLEIF_RR_LIST_URL = "https://leidata.gleif.org/api/v1/concatenated-files/rr"
GLEIF_RR_DOWNLOAD_URL = "https://leidata.gleif.org/api/v1/concatenated-files/rr/get/{file_id}/zip"
GLEIF_CONCATENATED_FILES_PAGE = (
    "https://www.gleif.org/en/lei-data/gleif-concatenated-file/download-the-concatenated-file"
)
DEFAULT_GLEIF_USER_AGENT = "bubble-forensic-source-acquisition/0.1"

JsonFetcher = Callable[[str], Mapping[str, Any]]


def latest_gleif_rr_catalog_row(*, fetch_json: JsonFetcher | None = None) -> dict[str, str]:
    """Resolve GLEIF's latest relationship-record CDF zip into a catalog row."""

    document = resolve_latest_gleif_rr_document(fetch_json=fetch_json)
    file_id = str(document["id"])
    content_date = str(document.get("content_date", ""))
    record_count = str(document.get("record_count", ""))
    cdf_version = str(document.get("cdf_version", ""))
    return {
        "source_id": f"gleif-rr-cdf-{file_id}",
        "corpus": "ownership_records",
        "source_uri": GLEIF_RR_DOWNLOAD_URL.format(file_id=file_id),
        "source_type": SourceType.GLEIF.value,
        "parser": "zip",
        "document_id": f"gleif_rr_cdf_{file_id}",
        "entity_id": "",
        "project_id": "",
        "filing_accession": "",
        "meta_publisher": "Global Legal Entity Identifier Foundation",
        "meta_title": "GLEIF Level 2 Relationship Record CDF Concatenated File",
        "meta_content_date": content_date,
        "meta_record_count": record_count,
        "meta_cdf_version": cdf_version,
        "meta_resolved_from_uri": GLEIF_RR_LIST_URL,
        "meta_source_page": GLEIF_CONCATENATED_FILES_PAGE,
        "meta_zip_member_name_prefix": content_date[:10].replace("-", ""),
        "meta_zip_xml_record_tag": "RelationshipRecord",
    }


def resolve_latest_gleif_rr_document(*, fetch_json: JsonFetcher | None = None) -> dict[str, Any]:
    """Return the latest GLEIF relationship-record concatenated file metadata."""

    payload = (fetch_json or _fetch_json)(GLEIF_RR_LIST_URL)
    documents = payload.get("data")
    if not isinstance(documents, Sequence) or isinstance(documents, str | bytes):
        raise ValueError("GLEIF RR list did not return a data array")
    candidates = [document for document in documents if isinstance(document, Mapping)]
    if not candidates:
        raise ValueError("GLEIF RR list did not contain any documents")
    selected = max(candidates, key=lambda document: str(document.get("content_date", "")))
    return dict(selected)


def _fetch_json(url: str) -> Mapping[str, Any]:
    headers = {"User-Agent": DEFAULT_GLEIF_USER_AGENT}
    with httpx.Client(timeout=45.0, follow_redirects=True) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, Mapping):
        raise ValueError(f"GLEIF JSON endpoint returned {type(payload).__name__}, not an object")
    return payload
