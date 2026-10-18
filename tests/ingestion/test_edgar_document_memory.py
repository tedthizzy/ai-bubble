from __future__ import annotations

import ctypes
import errno
import gzip
import html
import re
import sys
import threading
from types import SimpleNamespace
from typing import TYPE_CHECKING

import httpx
import pytest
from scripts import run_with_memory_budget as memory
from scripts.refresh_public_sources import PublicClient

from bubble.ingestion.edgar.document_acquisition import (
    DocumentMemoryBudget,
    normalize_document_text,
)

if TYPE_CHECKING:
    from pathlib import Path


def legacy_normalize(raw: bytes) -> str:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="ignore")
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?i)<\s*br\s*/?\s*>|</\s*p\s*>|</\s*div\s*>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text.strip()


@pytest.mark.parametrize(
    "raw",
    [
        b"<html><script>ignored &amp;\nignored</script><style>body{}</style>"
        b"<p>Credit agreement &amp; $300 million.</p><BR/>Next\r\n<div>line</div></html>",
        b"<p>Malformed < unclosed\n<script>no end",
        b"<STYLE>ignore</style>\xff\r\n amount\t\t text",
        ("<p>\u6f22\u5b57 \U0001f34e \u05d0</p>" * 100_000).encode(),
        b"<x>123</x><br/>\n \t<p>$3</p>" * 200_000,
    ],
)
def test_normalization_preserves_legacy_text_across_buffer_boundaries(raw: bytes) -> None:
    assert normalize_document_text(raw) == legacy_normalize(raw)


def test_document_memory_reservation_blocks_and_releases_after_error() -> None:
    budget = DocumentMemoryBudget(capacity=8 * 1024**2)
    entered = threading.Event()
    ready = threading.Event()

    def waiting() -> None:
        ready.set()
        with budget.reserve(2 * 1024**2):
            entered.set()

    with pytest.raises(ValueError), budget.reserve(2 * 1024**2):
        thread = threading.Thread(target=waiting)
        thread.start()
        assert ready.wait(2)
        assert not entered.wait(0.05)
        raise ValueError("parser failed")
    assert entered.wait(2)
    thread.join(2)
    assert not thread.is_alive()
    assert budget.available == budget.capacity


class Chunks(httpx.SyncByteStream):
    def __init__(self, chunks: list[bytes], *, fail: bool = False) -> None:
        self.chunks = chunks
        self.fail = fail

    def __iter__(self):
        yield from self.chunks
        if self.fail:
            raise httpx.ReadError("interrupted response")


def test_streamed_download_preserves_decoded_bytes_and_failed_parts(tmp_path: Path) -> None:
    client = PublicClient(tmp_path, 8)
    client.client.close()

    payload = b"<html><p>Source evidence &amp; amount.</p></html>" * 50_000
    encoded = gzip.compress(payload)
    calls = 0

    def respond(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            headers={"Content-Encoding": "gzip"},
            stream=Chunks(
                [encoded[: len(encoded) // 2], encoded[len(encoded) // 2 :]], fail=calls == 1
            ),
        )

    client.client = httpx.Client(transport=httpx.MockTransport(respond))
    destination = tmp_path / "filing.htm.gz"
    with pytest.raises(httpx.ReadError):
        client.download("https://example.test/document", destination)
    assert not destination.exists()
    partials = {p: p.read_bytes() for p in tmp_path.glob("*.part")}
    assert len(partials) == 1
    client.download("https://example.test/document", destination)
    assert gzip.decompress(destination.read_bytes()) == payload
    assert {p: p.read_bytes() for p in tmp_path.glob("*.part")} == partials
    before = destination.read_bytes()
    with pytest.raises(FileExistsError):
        client.download("https://example.test/document", destination)
    assert destination.read_bytes() == before
    assert calls == 2
    client.client.close()


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS rusage exit transition")
@pytest.mark.parametrize("state,returncode,expected", [("Z", 0, 0), ("", 1, 0), ("R", 0, None)])
def test_guard_distinguishes_exit_transition_from_live_measurement_failure(
    monkeypatch: pytest.MonkeyPatch, state: str, returncode: int, expected: int | None
) -> None:
    def denied(*_args):
        ctypes.set_errno(errno.EPERM)
        return -1

    monkeypatch.setattr(
        memory.ctypes, "CDLL", lambda *_args, **_kwargs: SimpleNamespace(proc_pid_rusage=denied)
    )
    monkeypatch.setattr(
        memory.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=returncode, stdout=state),
    )
    if expected is None:
        with pytest.raises(PermissionError):
            memory.footprint(123)
    else:
        assert memory.footprint(123) == expected
