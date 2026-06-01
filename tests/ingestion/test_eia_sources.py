from __future__ import annotations

from bubble.ingestion.sources.eia import (
    EIA_860M_INDEX_URL,
    latest_eia_860m_catalog_row,
    resolve_latest_eia_860m_document,
)


def test_resolve_latest_eia_860m_document_selects_first_downloadable_workbook():
    html = """
    <html>
      <span class="label">Release Date:</span> <span class="date">May 21, 2026</span>
      <span class="label">Next Release Date:</span> <span class="date">June 24, 2026</span>
      <a href="/electricity/data/eia860m/xls/december_generator2026.xlsx"
         title="EIA 860M December 2026">XLS</a>
      <a href="/electricity/data/eia860m/xls/april_generator2026.xlsx"
         title="EIA 860M April 2026">XLS</a>
    </html>
    """
    seen_urls: list[str] = []

    def fake_fetch_text(url: str) -> str:
        assert url == EIA_860M_INDEX_URL
        return html

    def fake_available(url: str) -> bool:
        seen_urls.append(url)
        return url.endswith("april_generator2026.xlsx")

    document = resolve_latest_eia_860m_document(
        fetch_text=fake_fetch_text,
        url_available=fake_available,
    )

    assert document.label == "April 2026"
    assert (
        document.url == "https://www.eia.gov/electricity/data/eia860m/xls/april_generator2026.xlsx"
    )
    assert document.release_date == "May 21, 2026"
    assert document.next_release_date == "June 24, 2026"
    assert seen_urls == [
        "https://www.eia.gov/electricity/data/eia860m/xls/december_generator2026.xlsx",
        "https://www.eia.gov/electricity/data/eia860m/xls/april_generator2026.xlsx",
    ]


def test_latest_eia_860m_catalog_row_preserves_resolver_provenance():
    html = """
    <html>
      <span class="label">Release Date:</span> <span class="date">May 21, 2026</span>
      <span class="label">Next Release Date:</span> <span class="date">June 24, 2026</span>
      <a href="/electricity/data/eia860m/xls/april_generator2026.xlsx"
         title="EIA 860M April 2026">XLS</a>
    </html>
    """

    row = latest_eia_860m_catalog_row(
        fetch_text=lambda _url: html,
        url_available=lambda _url: True,
    )

    assert row["source_id"] == "eia-860m-generator-inventory-april-2026"
    assert row["corpus"] == "equipment_records"
    assert row["source_type"] == "eia"
    assert row["parser"] == "xlsx"
    assert row["meta_release_date"] == "May 21, 2026"
    assert row["meta_next_release_date"] == "June 24, 2026"
    assert row["meta_resolved_from_uri"] == EIA_860M_INDEX_URL
    assert row["meta_xlsx_required_value_columns"] == "Entity ID|Plant ID"
