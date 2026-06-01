"""FERC public data source discovery."""

from __future__ import annotations

import html
import json
from collections.abc import Callable, Mapping
from html.parser import HTMLParser
from typing import Any

import httpx

from bubble.ingestion.sources.catalog import DEFAULT_USER_AGENT
from bubble.models.base import SourceType

FERC_ENTITIES_TO_PPAS_PAGE_URL = (
    "https://data.ferc.gov/market-based-rate-database/entities-to-ppas/"
)
FERC_DATASET_API_URL = "https://data.ferc.gov/api/v1/dataset/{dataset_id}/"
FERC_PPA_PAGE_SIZE = 100

FetchText = Callable[[str], str]
FetchDatasetPage = Callable[[str, Mapping[str, Any]], Mapping[str, Any]]


def latest_ferc_entities_to_ppas_catalog_rows(
    *,
    fetch_text: FetchText | None = None,
    fetch_json: FetchDatasetPage | None = None,
    page_size: int = FERC_PPA_PAGE_SIZE,
) -> list[dict[str, str]]:
    """Return paged catalog rows for FERC's Entities to PPAs data set."""

    resolved_page_size = _valid_page_size(page_size)
    page_html = (
        fetch_text(FERC_ENTITIES_TO_PPAS_PAGE_URL)
        if fetch_text
        else _fetch_text(FERC_ENTITIES_TO_PPAS_PAGE_URL)
    )
    page_props = _page_props_from_next_data(_extract_next_data(page_html))
    dataset_id = str(page_props["datasetId"])
    metadata = page_props["metadata"]
    columns = [
        str(column["column_name"])
        for column in page_props["format"]
        if str(column.get("column_name", "")).strip()
    ]
    api_url = FERC_DATASET_API_URL.format(dataset_id=dataset_id)
    fetch_page = fetch_json or _post_dataset_page
    probe_body = _request_body(
        start_row=0,
        end_row=resolved_page_size,
        columns=columns,
    )
    probe = fetch_page(api_url, probe_body)
    total_count = int(probe["totalCount"])

    rows: list[dict[str, str]] = []
    for start_row in range(0, total_count, resolved_page_size):
        end_row = min(start_row + resolved_page_size, total_count)
        body = _request_body(start_row=start_row, end_row=end_row, columns=columns)
        rows.append(
            {
                "source_id": (
                    f"ferc-mbr-entities-to-ppas-{dataset_id}-{start_row:06d}-{end_row:06d}"
                ),
                "corpus": "ppas",
                "source_uri": api_url,
                "source_type": SourceType.FERC.value,
                "parser": "json",
                "document_id": f"ferc_dataset_{dataset_id}_entities_to_ppas",
                "entity_id": "",
                "project_id": "",
                "filing_accession": "",
                "meta_publisher": "Federal Energy Regulatory Commission",
                "meta_title": str(metadata.get("dataset_title", "Entities to PPAs")),
                "meta_description": str(metadata.get("description", "")),
                "meta_source_page": FERC_ENTITIES_TO_PPAS_PAGE_URL,
                "meta_dataset_id": dataset_id,
                "meta_data_last_updated": str(metadata.get("data_last_updated", "")),
                "meta_total_count": str(total_count),
                "meta_page_start_row": str(start_row),
                "meta_page_end_row": str(end_row),
                "meta_page_size": str(resolved_page_size),
                "meta_http_method": "POST",
                "meta_http_body": json.dumps(body, separators=(",", ":")),
                "meta_http_header_Content_Type": "application/json",
                "meta_http_header_Origin": "https://data.ferc.gov",
                "meta_http_header_Referer": FERC_ENTITIES_TO_PPAS_PAGE_URL,
                "meta_file_extension": "json",
                "meta_json_records_path": "rowData",
            }
        )
    return rows


def _request_body(*, start_row: int, end_row: int, columns: list[str]) -> dict[str, Any]:
    return {
        "startRow": start_row,
        "endRow": end_row,
        "sortModel": [{"sort": "asc", "colId": "ID"}],
        "filterModel": {},
        "columns": columns,
        "castData": [],
    }


def _valid_page_size(page_size: int) -> int:
    if page_size <= 0:
        raise ValueError("FERC page_size must be positive")
    return min(page_size, FERC_PPA_PAGE_SIZE)


def _fetch_text(url: str) -> str:
    with httpx.Client(timeout=45.0, follow_redirects=True) as client:
        response = client.get(url, headers={"User-Agent": DEFAULT_USER_AGENT})
        response.raise_for_status()
        return response.text


def _post_dataset_page(url: str, body: Mapping[str, Any]) -> Mapping[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://data.ferc.gov",
        "Referer": FERC_ENTITIES_TO_PPAS_PAGE_URL,
        "User-Agent": DEFAULT_USER_AGENT,
    }
    with httpx.Client(timeout=45.0, follow_redirects=True) as client:
        response = client.post(url, headers=headers, json=body)
        response.raise_for_status()
        parsed = response.json()
    if not isinstance(parsed, Mapping):
        raise ValueError("FERC dataset API returned non-object JSON")
    return parsed


def _page_props_from_next_data(next_data: Mapping[str, Any]) -> Mapping[str, Any]:
    props = next_data.get("props")
    if isinstance(props, Mapping):
        page_props = props.get("pageProps")
        if isinstance(page_props, Mapping):
            return page_props
    page_props = next_data.get("pageProps")
    if isinstance(page_props, Mapping):
        return page_props
    raise ValueError("FERC page did not include Next.js pageProps")


def _extract_next_data(page_html: str) -> Mapping[str, Any]:
    parser = _NextDataParser()
    parser.feed(page_html)
    if not parser.next_data:
        raise ValueError("FERC page did not include __NEXT_DATA__")
    parsed = json.loads(html.unescape(parser.next_data))
    if not isinstance(parsed, Mapping):
        raise ValueError("FERC __NEXT_DATA__ was not an object")
    return parsed


class _NextDataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_next_data = False
        self._parts: list[str] = []

    @property
    def next_data(self) -> str:
        return "".join(self._parts).strip()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag == "script" and attr_map.get("id") == "__NEXT_DATA__":
            self._in_next_data = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._in_next_data:
            self._in_next_data = False

    def handle_data(self, data: str) -> None:
        if self._in_next_data:
            self._parts.append(data)
