"""Convert SEC filing HTML without loading models or embedded images."""

from functools import lru_cache

from docling.datamodel.backend_options import HTMLBackendOptions
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, HTMLFormatOption


@lru_cache(maxsize=1)
def get_filing_converter() -> DocumentConverter:
    """Keep filing inputs out of model loaders affected by CVE-2026-69112."""
    return DocumentConverter(
        allowed_formats=[InputFormat.HTML],
        format_options={
            InputFormat.HTML: HTMLFormatOption(
                backend_options=HTMLBackendOptions.model_validate(
                    {
                        "fetch_images": False,
                        "enable_remote_fetch": False,
                        "enable_local_fetch": False,
                        "render_page": False,
                    }
                ),
            ),
        },
    )
