from __future__ import annotations

import json
from typing import Any

from bubble.ingestion.sources.ferc import (
    FERC_DATASET_API_URL,
    FERC_ENTITIES_TO_PPAS_PAGE_URL,
    latest_ferc_entities_to_ppas_catalog_rows,
)


def test_latest_ferc_entities_to_ppas_catalog_rows_pages_dataset_api():
    next_data = {
        "props": {
            "pageProps": {
                "datasetId": 17,
                "metadata": {
                    "dataset_title": "Entities to PPAs",
                    "description": "Long-term firm agreements.",
                    "data_last_updated": "2026-06-01T04:08:45.815Z",
                },
                "format": [
                    {"column_name": "ID"},
                    {"column_name": "Reporting_Entity_Name"},
                    {"column_name": "Counterparty_Name"},
                ],
            }
        }
    }
    html = (
        '<html><script id="__NEXT_DATA__" type="application/json">'
        f"{json.dumps(next_data)}"
        "</script></html>"
    )
    posted_bodies: list[dict[str, Any]] = []

    def fetch_json(url: str, body: dict[str, Any]):
        assert url == FERC_DATASET_API_URL.format(dataset_id=17)
        posted_bodies.append(body)
        return {"rowData": [{"ID": "1"}], "totalCount": 3}

    rows = latest_ferc_entities_to_ppas_catalog_rows(
        fetch_text=lambda url: html if url == FERC_ENTITIES_TO_PPAS_PAGE_URL else "",
        fetch_json=fetch_json,
        page_size=2,
    )

    assert len(rows) == 2
    assert rows[0]["source_id"] == "ferc-mbr-entities-to-ppas-17-000000-000002"
    assert rows[0]["source_uri"] == FERC_DATASET_API_URL.format(dataset_id=17)
    assert rows[0]["source_type"] == "ferc"
    assert rows[0]["corpus"] == "ppas"
    assert rows[0]["parser"] == "json"
    assert rows[0]["meta_http_method"] == "POST"
    assert rows[0]["meta_http_header_Content_Type"] == "application/json"
    assert rows[0]["meta_file_extension"] == "json"
    assert rows[0]["meta_json_records_path"] == "rowData"
    assert rows[1]["source_id"] == "ferc-mbr-entities-to-ppas-17-000002-000003"
    assert posted_bodies == [
        {
            "startRow": 0,
            "endRow": 2,
            "sortModel": [{"sort": "asc", "colId": "ID"}],
            "filterModel": {},
            "columns": ["ID", "Reporting_Entity_Name", "Counterparty_Name"],
            "castData": [],
        }
    ]
    assert json.loads(rows[1]["meta_http_body"])["startRow"] == 2
