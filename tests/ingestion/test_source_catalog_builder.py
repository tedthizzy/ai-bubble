from __future__ import annotations

import csv
import json
from typing import TYPE_CHECKING

from bubble.ingestion.sources import build_seed_source_catalog
from bubble.ingestion.sources.catalog import load_source_catalog

if TYPE_CHECKING:
    from pathlib import Path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_build_seed_source_catalog_writes_sec_submission_targets(tmp_path: Path):
    output = tmp_path / "source_catalog.csv"

    summary = build_seed_source_catalog(
        output, ciks=["789019", "0001018724"], limit=2, include_public_sources=False
    )

    rows = _read_csv(output)
    assert summary.catalog_rows == 2
    assert summary.edgar_submission_sources == 2
    assert summary.public_sources == 0
    assert summary.corpora == {"filings": 2}
    assert rows[0]["source_id"] == "sec-submissions-0000789019"
    assert rows[0]["source_uri"] == "https://data.sec.gov/submissions/CIK0000789019.json"
    assert rows[0]["source_type"] == "sec_edgar"
    assert rows[0]["parser"] == "json"
    assert rows[0]["meta_company_name"] == "Microsoft"
    assert len(load_source_catalog(output)) == 2


def test_build_seed_source_catalog_appends_validated_curated_catalog(tmp_path: Path):
    curated = tmp_path / "curated.csv"
    _write_csv(
        curated,
        [
            {
                "source_id": "pjm-queue",
                "corpus": "queue_records",
                "source_uri": "https://example.com/pjm-queue.csv",
                "source_type": "grid_interconnection_queue",
                "parser": "csv",
                "meta_region": "PJM",
            }
        ],
    )

    output = tmp_path / "source_catalog.csv"
    summary = build_seed_source_catalog(
        output,
        ciks=["0000789019"],
        include_public_sources=False,
        curated_catalogs=[curated],
    )

    rows = _read_csv(output)
    assert summary.catalog_rows == 2
    assert summary.curated_sources == 1
    assert summary.corpora == {"filings": 1, "queue_records": 1}
    assert rows[1]["source_id"] == "pjm-queue"
    assert rows[1]["meta_region"] == "PJM"
    assert len(load_source_catalog(output)) == 2


def test_build_seed_source_catalog_includes_public_queue_target(tmp_path: Path):
    output = tmp_path / "source_catalog.csv"

    summary = build_seed_source_catalog(output, ciks=["0000789019"])

    rows = _read_csv(output)
    assert summary.catalog_rows == 9
    assert summary.public_sources == 8
    assert summary.corpora == {
        "equipment_records": 1,
        "filings": 1,
        "permit_records": 1,
        "queue_records": 5,
        "tracker_records": 1,
    }
    assert rows[1]["source_id"] == "caiso-cluster-15-queue-report"
    assert rows[1]["parser"] == "xlsx"
    assert rows[2]["source_id"] == "nyiso-interconnection-queue"
    assert rows[3]["source_id"] == "miso-eras-interconnection-requests"
    assert rows[4]["source_id"] == "spp-active-generation-interconnection-queue"
    assert rows[5]["source_id"] == "pjm-planning-queues-xml"
    assert rows[5]["parser"] == "xml"
    assert rows[6]["source_id"] == "epa-egrid2023-data-rev2"
    assert rows[7]["source_id"] == "epa-icis-air-facilities-programs"
    assert rows[7]["parser"] == "zip"
    assert rows[8]["source_id"] == "server-country-all-projects"
    assert rows[8]["corpus"] == "tracker_records"


def test_build_seed_source_catalog_resolves_dynamic_public_queue_target(tmp_path: Path):
    output = tmp_path / "source_catalog.csv"
    eia_html = """
    <html>
      <span class="label">Release Date:</span> <span class="date">May 21, 2026</span>
      <span class="label">Next Release Date:</span> <span class="date">June 24, 2026</span>
      <a href="/electricity/data/eia860m/xls/april_generator2026.xlsx"
         title="EIA 860M April 2026">XLS</a>
    </html>
    """
    payload = {
        "ListDocsByRptTypeRes": {
            "DocumentList": [
                {
                    "Document": {
                        "DocID": "1221842626",
                        "FriendlyName": "GIS_Report_April2026",
                        "Extension": "xlsx",
                        "ReportTypeID": "15933",
                        "ConstructedName": "RPT.00015933.GIS_Report_April2026.xlsx",
                        "PublishDate": "2026-05-01T13:53:52-05:00",
                    }
                }
            ]
        }
    }
    iso_ne_html = """
    <html>
      <div>As of: 6/1/2026</div>
      <script>
        location.href = url + '?ReportDate=' + 639158688000000000 + '&Status=';
      </script>
    </html>
    """
    gleif_payloads = {
        "lei": {
            "data": [
                {
                    "id": 41255,
                    "type": "lei2",
                    "content_date": "2026-06-01 09:00:02",
                    "record_count": 3326141,
                    "cdf_version": "LEI_3.1",
                }
            ]
        },
        "rr": {
            "data": [
                {
                    "id": 41249,
                    "type": "rr",
                    "content_date": "2026-05-31 09:00:01",
                    "record_count": 650357,
                    "cdf_version": "RR_2.1",
                }
            ]
        },
    }
    ferc_next_data = {
        "props": {
            "pageProps": {
                "datasetId": 17,
                "metadata": {
                    "dataset_title": "Entities to PPAs",
                    "description": "Long-term firm agreements.",
                    "data_last_updated": "2026-06-01T04:08:45.815Z",
                },
                "format": [{"column_name": "ID"}, {"column_name": "Reporting_Entity_Name"}],
            }
        }
    }
    ferc_html = (
        '<html><script id="__NEXT_DATA__" type="application/json">'
        f"{json.dumps(ferc_next_data)}"
        "</script></html>"
    )
    fractracker_payloads = {
        "layer": {"maxRecordCount": 2},
        "count": {"count": 3},
    }

    def fractracker_fetch_json(url: str) -> dict[str, int]:
        if "returnCountOnly=true" in url:
            return fractracker_payloads["count"]
        return fractracker_payloads["layer"]

    def gleif_fetch_json(url: str) -> dict[str, object]:
        return gleif_payloads["lei"] if url.endswith("/lei2") else gleif_payloads["rr"]

    summary = build_seed_source_catalog(
        output,
        ciks=["0000789019"],
        include_dynamic_public_sources=True,
        eia_fetch_text=lambda _url: eia_html,
        eia_url_available=lambda _url: True,
        ercot_fetch_json=lambda _url: payload,
        ferc_fetch_text=lambda _url: ferc_html,
        ferc_fetch_json=lambda _url, _body: {"rowData": [], "totalCount": 3},
        fractracker_fetch_json=fractracker_fetch_json,
        gleif_fetch_json=gleif_fetch_json,
        iso_ne_fetch_text=lambda _url: iso_ne_html,
    )

    rows = _read_csv(output)
    assert summary.catalog_rows == 17
    assert summary.public_sources == 16
    assert summary.corpora == {
        "equipment_records": 2,
        "filings": 1,
        "lei_records": 1,
        "ownership_records": 1,
        "permit_records": 1,
        "ppas": 1,
        "queue_records": 7,
        "tracker_records": 3,
    }
    assert rows[9]["source_id"] == "eia-860m-generator-inventory-april-2026"
    assert rows[10]["source_id"] == "ercot-gis-report-1221842626"
    assert rows[10]["meta_resolved_from_uri"].startswith("https://www.ercot.com/")
    assert rows[11]["source_id"] == "ferc-mbr-entities-to-ppas-17-000000-000003"
    assert rows[11]["corpus"] == "ppas"
    assert rows[11]["meta_http_method"] == "POST"
    assert rows[12]["source_id"] == "fractracker-data-centers-000000-000002"
    assert rows[12]["meta_json_records_path"] == "features"
    assert rows[12]["meta_json_flatten_records"] == "true"
    assert rows[13]["source_id"] == "fractracker-data-centers-000002-000003"
    assert rows[14]["source_id"] == "gleif-lei-cdf-41255"
    assert rows[14]["source_type"] == "gleif"
    assert rows[14]["meta_zip_xml_record_tag"] == "LEIRecord"
    assert rows[15]["source_id"] == "gleif-rr-cdf-41249"
    assert rows[15]["source_type"] == "gleif"
    assert rows[15]["meta_zip_xml_record_tag"] == "RelationshipRecord"
    assert rows[16]["source_id"] == "iso-ne-public-queue-639158688000000000"
    assert rows[16]["meta_http_header_cookie"] == "AspxAutoDetectCookieSupport=1"
