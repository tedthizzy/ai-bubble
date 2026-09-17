"""Exercise the real converter at the boundary between filings and model loaders."""

from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
import requests
from docling.datamodel.base_models import DocumentStream
from docling.exceptions import ConversionError
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from PIL import Image

from bubble.ingestion.edgar.documents import get_filing_converter
from bubble.ingestion.edgar.extractor import EdgarExtractor

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@pytest.fixture
def external_operations(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    calls: list[str] = []

    def reject(*args: Any, **kwargs: Any) -> Any:
        calls.append("external operation")
        raise AssertionError("Filing HTML must not fetch images or start a model pipeline")

    get_filing_converter.cache_clear()
    monkeypatch.setattr(requests.sessions.Session, "request", reject)
    monkeypatch.setattr(Image, "open", reject)
    monkeypatch.setattr(StandardPdfPipeline, "__init__", reject)
    yield calls
    get_filing_converter.cache_clear()


def test_filing_html_preserves_text_and_tables_without_fetching_images(
    external_operations: list[str],
) -> None:
    html = b"""<!doctype html><html><body>
    <h1>Annual filing</h1><p>Revenue grew during the year.</p>
    <table><tr><th>Metric</th><th>USD million</th></tr>
    <tr><td>Revenue</td><td>1,234</td></tr></table>
    <img src="https://example.invalid/attacker-image.png">
    <img src="file:///synthetic-untrusted-image.png">
    </body></html>"""
    result = get_filing_converter().convert(
        DocumentStream(name="filing.html", stream=BytesIO(html))
    )
    markdown = result.document.export_to_markdown()
    assert "Annual filing" in markdown
    assert "Revenue grew during the year." in markdown
    assert "1,234" in markdown
    assert len(result.document.tables) == 1
    assert external_operations == []


@pytest.mark.parametrize("filename", ["filing.pdf", "mislabelled.html"])
def test_pdf_filing_cannot_select_a_model_pipeline(
    filename: str, external_operations: list[str]
) -> None:
    payload = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
    with pytest.raises(ConversionError):
        get_filing_converter().convert(DocumentStream(name=filename, stream=BytesIO(payload)))
    assert external_operations == []


def test_checkpoint_json_cannot_select_a_model_pipeline(external_operations: list[str]) -> None:
    payload = b'{"weight_map": {"weight": "../../synthetic-outside.bin"}}'
    with pytest.raises(ConversionError):
        get_filing_converter().convert(
            DocumentStream(name="weights.index.json", stream=BytesIO(payload))
        )
    assert external_operations == []


@pytest.mark.parametrize(
    ("contents", "expected"),
    [
        (
            b"<!doctype html><html><body><p>Filing revenue text.</p></body></html>",
            "Filing revenue text.",
        ),
        (b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n", ""),
    ],
)
def test_extractor_uses_the_restricted_converter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    external_operations: list[str],
    contents: bytes,
    expected: str,
) -> None:
    filing = tmp_path / "filing.html"
    filing.write_bytes(contents)
    extractor = EdgarExtractor()
    monkeypatch.setattr(
        extractor.edgar,
        "latest_filing",
        lambda *_: SimpleNamespace(primary_html_url=str(filing)),
    )
    assert extractor.extract_narrative_sections("0000000001").strip() == expected
    assert external_operations == []
