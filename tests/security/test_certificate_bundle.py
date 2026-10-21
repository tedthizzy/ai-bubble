"""Verify the overlay's CA bootstrap and its HTTPS connection configuration."""

from __future__ import annotations

import hashlib
import io
import ssl
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import certifi
import pytest
from scripts import refresh_live_overlay as overlay

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def clear_certificate_context() -> Iterator[None]:
    overlay._https_context.cache_clear()
    yield
    overlay._https_context.cache_clear()


@pytest.mark.parametrize("tampered", [False, True])
def test_certificate_bootstrap_verifies_locked_wheel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tampered: bool
) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("certifi/cacert.pem", Path(certifi.where()).read_bytes())
    wheel = buffer.getvalue()
    digest = hashlib.sha256(wheel).hexdigest()
    (tmp_path / "uv.lock").write_text(
        '[[package]]\nname = "certifi"\nversion = "0.0.0"\n'
        'wheels = [{ url = "https://example.invalid/certifi.whl", '
        f'hash = "sha256:{digest}", size = {len(wheel)} }}]\n'
    )
    monkeypatch.setattr(overlay, "ROOT", tmp_path)
    monkeypatch.setenv("SSL_CERT_FILE", str(tmp_path / "must-not-be-loaded.pem"))
    monkeypatch.setenv("SSL_CERT_DIR", str(tmp_path / "must-not-be-loaded"))
    requests = []

    def download(url: str, **_kwargs: Any) -> io.BytesIO:
        requests.append(url)
        return io.BytesIO(wheel + b"modified" if tampered else wheel)

    monkeypatch.setattr(overlay.urllib.request, "urlopen", download)
    if tampered:
        with pytest.raises(ValueError, match=r"does not match uv\.lock"):
            overlay._https_context()
    else:
        context = overlay._https_context()
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname
        roots = {hashlib.sha256(der).hexdigest() for der in context.get_ca_certs(binary_form=True)}
        assert roots
        assert "86a1ecba089c4a8d3bbe2734c612ba341d813e043cf9e8a862cd5c57a36bbe6b" not in roots
        assert overlay._https_context() is context
    assert requests == ["https://example.invalid/certifi.whl"]


def test_overlay_download_uses_installed_locked_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    def download(request: Any, **kwargs: Any) -> io.BytesIO:
        # A wheel bootstrap would pass a URL string instead of this source request.
        assert request.full_url == "https://example.invalid/source"
        context = kwargs["context"]
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname
        assert kwargs["timeout"] == 20
        return io.BytesIO(b"verified source content")

    monkeypatch.setattr(overlay.urllib.request, "urlopen", download)
    assert overlay._get("https://example.invalid/source") == "verified source content"
