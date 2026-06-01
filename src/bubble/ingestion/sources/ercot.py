"""ERCOT source resolvers for live public report artifacts."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

import httpx

from bubble.models.base import SourceType

ERCOT_GIS_REPORT_TYPE_ID = "15933"
ERCOT_GIS_REPORT_LIST_URL = (
    "https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId="
    f"{ERCOT_GIS_REPORT_TYPE_ID}"
)
ERCOT_DOCUMENT_DOWNLOAD_URL = (
    "https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId={doc_id}"
)
DEFAULT_ERCOT_USER_AGENT = "bubble-forensic-source-acquisition/0.1"

JsonFetcher = Callable[[str], Mapping[str, Any]]


def latest_ercot_gis_catalog_row(*, fetch_json: JsonFetcher | None = None) -> dict[str, str]:
    """Resolve ERCOT's latest primary GIS workbook into a source catalog row."""

    document = resolve_latest_ercot_gis_document(fetch_json=fetch_json)
    doc_id = document["DocID"]
    friendly_name = document["FriendlyName"]
    constructed_name = document.get("ConstructedName", "")
    publish_date = document.get("PublishDate", "")
    return {
        "source_id": f"ercot-gis-report-{doc_id}",
        "corpus": "queue_records",
        "source_uri": ERCOT_DOCUMENT_DOWNLOAD_URL.format(doc_id=doc_id),
        "source_type": SourceType.GRID_QUEUE.value,
        "parser": "xlsx",
        "document_id": f"ercot_gis_report_{doc_id}",
        "entity_id": "",
        "project_id": "",
        "filing_accession": "",
        "meta_publisher": "ERCOT",
        "meta_title": friendly_name,
        "meta_publish_date": publish_date,
        "meta_report_type_id": document.get("ReportTypeID", ERCOT_GIS_REPORT_TYPE_ID),
        "meta_doc_id": doc_id,
        "meta_constructed_name": constructed_name,
        "meta_content_size": document.get("ContentSize", ""),
        "meta_resolved_from_uri": ERCOT_GIS_REPORT_LIST_URL,
        "meta_xlsx_sheet_name_prefix": "Project Details -",
        "meta_xlsx_required_value_columns": "INR|Project Name",
    }


def resolve_latest_ercot_gis_document(*, fetch_json: JsonFetcher | None = None) -> dict[str, str]:
    """Return the latest non-battery ERCOT GIS workbook document metadata."""

    payload = (fetch_json or _fetch_json)(ERCOT_GIS_REPORT_LIST_URL)
    candidates = [
        document for document in _iter_documents(payload) if _is_primary_gis_report(document)
    ]
    if not candidates:
        raise ValueError("ERCOT GIS report list did not contain a primary GIS workbook")
    selected = max(candidates, key=_publish_date)
    return {str(key): str(value) for key, value in selected.items() if value is not None}


def _fetch_json(url: str) -> Mapping[str, Any]:
    headers = {"User-Agent": DEFAULT_ERCOT_USER_AGENT}
    with httpx.Client(timeout=45.0, follow_redirects=True) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, Mapping):
        raise ValueError(f"ERCOT JSON endpoint returned {type(payload).__name__}, not an object")
    return payload


def _iter_documents(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    response = payload.get("ListDocsByRptTypeRes")
    if not isinstance(response, Mapping):
        return []
    document_list = response.get("DocumentList")
    if not isinstance(document_list, Sequence) or isinstance(document_list, str | bytes):
        return []

    documents: list[Mapping[str, Any]] = []
    for item in document_list:
        if not isinstance(item, Mapping):
            continue
        nested_document = item.get("Document")
        if isinstance(nested_document, Mapping):
            documents.append(nested_document)
        elif "DocID" in item:
            documents.append(item)
    return documents


def _is_primary_gis_report(document: Mapping[str, Any]) -> bool:
    friendly_name = str(document.get("FriendlyName", "")).strip()
    extension = str(document.get("Extension", "")).strip().lower()
    report_type_id = str(document.get("ReportTypeID", "")).strip()
    doc_id = str(document.get("DocID", "")).strip()
    return (
        bool(doc_id)
        and extension == "xlsx"
        and report_type_id == ERCOT_GIS_REPORT_TYPE_ID
        and friendly_name.startswith("GIS_Report_")
        and "Co-located_Battery" not in friendly_name
    )


def _publish_date(document: Mapping[str, Any]) -> datetime:
    value = str(document.get("PublishDate", "")).strip()
    if not value:
        return datetime.min.replace(tzinfo=UTC)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed
