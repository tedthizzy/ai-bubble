"""FracTracker source resolvers for public data-center tracker artifacts."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import urlencode

import httpx

from bubble.models.base import SourceType

FRACTRACKER_DATA_CENTERS_PAGE_URL = "https://www.fractracker.org/data-centers/"
FRACTRACKER_EXPERIENCE_ITEM_ID = "5a4d072ad01449bba5698a80103fb909"
FRACTRACKER_WEB_MAP_ITEM_ID = "abd7c231595e491c9d63513a195e21fc"
FRACTRACKER_FEATURE_ITEM_ID = "7036dcf75b6142a2809b4dca30200d80"
FRACTRACKER_FEATURE_LAYER_URL = (
    "https://services.arcgis.com/jDGuO8tYggdCCnUJ/arcgis/rest/services/"
    "data_centers_v4_agol_all/FeatureServer/0"
)
FRACTRACKER_QUERY_URL = f"{FRACTRACKER_FEATURE_LAYER_URL}/query"
DEFAULT_FRACTRACKER_USER_AGENT = "bubble-forensic-source-acquisition/0.1"

JsonFetcher = Callable[[str], Mapping[str, Any]]


def latest_fractracker_data_center_catalog_rows(
    *,
    fetch_json: JsonFetcher | None = None,
) -> list[dict[str, str]]:
    """Resolve FracTracker's ArcGIS feature layer into paged catalog rows."""

    fetch = fetch_json or _fetch_json
    layer_info = fetch(f"{FRACTRACKER_FEATURE_LAYER_URL}?f=json")
    count_payload = fetch(_query_url({"where": "1=1", "returnCountOnly": "true", "f": "json"}))
    total_count = _positive_int(count_payload.get("count"))
    if total_count <= 0:
        raise ValueError("FracTracker data-center layer did not report a positive row count")

    page_size = _positive_int(layer_info.get("maxRecordCount")) or 1000
    page_size = min(page_size, 1000)
    rows: list[dict[str, str]] = []
    for offset in range(0, total_count, page_size):
        end = min(offset + page_size, total_count)
        rows.append(
            {
                "source_id": f"fractracker-data-centers-{offset:06d}-{end:06d}",
                "corpus": "tracker_records",
                "source_uri": _query_url(
                    {
                        "where": "1=1",
                        "outFields": "*",
                        "returnGeometry": "true",
                        "resultOffset": str(offset),
                        "resultRecordCount": str(page_size),
                        "f": "json",
                    }
                ),
                "source_type": SourceType.PROJECT_TRACKER.value,
                "parser": "json",
                "document_id": f"fractracker_data_centers_{offset}_{end}",
                "entity_id": "",
                "project_id": "",
                "filing_accession": "",
                "meta_publisher": "FracTracker Alliance",
                "meta_title": "Open U.S. Data Centers Tracker - Data Center Summary",
                "meta_source_page": FRACTRACKER_DATA_CENTERS_PAGE_URL,
                "meta_arcgis_experience_item_id": FRACTRACKER_EXPERIENCE_ITEM_ID,
                "meta_arcgis_web_map_item_id": FRACTRACKER_WEB_MAP_ITEM_ID,
                "meta_arcgis_feature_item_id": FRACTRACKER_FEATURE_ITEM_ID,
                "meta_arcgis_feature_layer_url": FRACTRACKER_FEATURE_LAYER_URL,
                "meta_json_records_path": "features",
                "meta_json_flatten_records": "true",
                "meta_file_extension": "json",
                "meta_total_count": str(total_count),
                "meta_page_start": str(offset),
                "meta_page_end": str(end),
                "meta_page_size": str(page_size),
            }
        )
    return rows


def _query_url(params: Mapping[str, str]) -> str:
    return f"{FRACTRACKER_QUERY_URL}?{urlencode(params)}"


def _positive_int(value: Any) -> int:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return 0
    return max(0, parsed)


def _fetch_json(url: str) -> Mapping[str, Any]:
    headers = {"User-Agent": DEFAULT_FRACTRACKER_USER_AGENT}
    with httpx.Client(timeout=45.0, follow_redirects=True) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, Mapping):
        raise ValueError(
            f"FracTracker JSON endpoint returned {type(payload).__name__}, not an object"
        )
    return payload
