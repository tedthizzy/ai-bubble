from __future__ import annotations

from bubble.ingestion.sources.ercot import (
    ERCOT_DOCUMENT_DOWNLOAD_URL,
    ERCOT_GIS_REPORT_LIST_URL,
    latest_ercot_gis_catalog_row,
    resolve_latest_ercot_gis_document,
)


def test_resolve_latest_ercot_gis_document_ignores_battery_report():
    payload = {
        "ListDocsByRptTypeRes": {
            "DocumentList": [
                {
                    "Document": {
                        "DocID": "2",
                        "FriendlyName": "Co-located_Battery_Identification_Report_April_2026",
                        "Extension": "xlsx",
                        "ReportTypeID": "15933",
                        "PublishDate": "2026-05-05T14:31:25-05:00",
                    }
                },
                {
                    "Document": {
                        "DocID": "1",
                        "FriendlyName": "GIS_Report_March2026",
                        "Extension": "xlsx",
                        "ReportTypeID": "15933",
                        "PublishDate": "2026-04-01T10:00:00-05:00",
                    }
                },
                {
                    "Document": {
                        "DocID": "3",
                        "FriendlyName": "GIS_Report_April2026",
                        "Extension": "xlsx",
                        "ReportTypeID": "15933",
                        "ConstructedName": "RPT.00015933.GIS_Report_April2026.xlsx",
                        "ContentSize": "685461",
                        "PublishDate": "2026-05-01T13:53:52-05:00",
                    }
                },
            ]
        }
    }

    def fake_fetch_json(url: str):
        assert url == ERCOT_GIS_REPORT_LIST_URL
        return payload

    document = resolve_latest_ercot_gis_document(fetch_json=fake_fetch_json)

    assert document["DocID"] == "3"
    assert document["FriendlyName"] == "GIS_Report_April2026"


def test_latest_ercot_gis_catalog_row_preserves_resolver_provenance():
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
                        "ContentSize": "685461",
                        "PublishDate": "2026-05-01T13:53:52-05:00",
                    }
                }
            ]
        }
    }

    row = latest_ercot_gis_catalog_row(fetch_json=lambda _url: payload)

    assert row["source_id"] == "ercot-gis-report-1221842626"
    assert row["source_uri"] == ERCOT_DOCUMENT_DOWNLOAD_URL.format(doc_id="1221842626")
    assert row["parser"] == "xlsx"
    assert row["meta_doc_id"] == "1221842626"
    assert row["meta_resolved_from_uri"] == ERCOT_GIS_REPORT_LIST_URL
    assert row["meta_xlsx_sheet_name_prefix"] == "Project Details -"
    assert row["meta_xlsx_required_value_columns"] == "INR|Project Name"
