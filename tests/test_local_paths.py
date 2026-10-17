from __future__ import annotations

from pathlib import Path

import pytest

from bubble import paths
from bubble.ingestion.sources.catalog import SourceCatalogClient, SourceCatalogRow
from bubble.models.base import SourceType


@pytest.fixture
def checkouts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    archived = tmp_path / "archived"
    current = tmp_path / "current"
    current.mkdir()
    monkeypatch.setattr(paths, "_ARCHIVED_CHECKOUT_ROOT", archived)
    monkeypatch.setattr(paths, "_CHECKOUT_ROOT", current)
    return archived, current


def _catalog_row(source_uri: str) -> SourceCatalogRow:
    return SourceCatalogRow(
        source_id="cached-source",
        corpus="filings",
        source_uri=source_uri,
        source_type=SourceType.COMPANY_IR,
        parser="raw",
        document_id=None,
        entity_id=None,
        project_id=None,
        filing_accession=None,
        metadata={},
    )


@pytest.mark.parametrize("catalog_row", [False, True])
@pytest.mark.parametrize("file_uri", [False, True])
def test_cached_source_survives_checkout_move(
    checkouts: tuple[Path, Path], *, catalog_row: bool, file_uri: bool
) -> None:
    archived, current = checkouts
    relative = Path("data") / "filing with space \u03bb.json"
    actual = current / relative
    actual.parent.mkdir()
    payload = b'{"cached": true}\n'
    actual.write_bytes(payload)
    inode = actual.stat().st_ino
    recorded = archived / relative
    source_uri = recorded.as_uri() if file_uri else str(recorded)
    client = SourceCatalogClient()

    result = (
        client.fetch_catalog_row(_catalog_row(source_uri))
        if catalog_row
        else client.fetch_bytes(source_uri)
    )

    assert result == payload
    assert actual.stat().st_ino == inode
    assert not archived.exists()


def test_relative_source_keeps_its_working_directory(
    checkouts: tuple[Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, current = checkouts
    (current / "source.txt").write_bytes(b"checkout")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "source.txt").write_bytes(b"working directory")
    monkeypatch.chdir(elsewhere)

    assert SourceCatalogClient().fetch_bytes("source.txt") == b"working directory"


def test_external_source_keeps_its_absolute_location(
    checkouts: tuple[Path, Path], tmp_path: Path
) -> None:
    outside = tmp_path / "external.txt"
    outside.write_bytes(b"external source")

    assert (
        SourceCatalogClient().fetch_catalog_row(_catalog_row(outside.as_uri()))
        == b"external source"
    )


def test_dated_input_can_use_an_explicit_checkout_root(
    checkouts: tuple[Path, Path], tmp_path: Path
) -> None:
    archived, _ = checkouts
    supplied_root = tmp_path / "supplied"
    supplied_root.mkdir()
    (supplied_root / "input.txt").write_bytes(b"dated input")

    assert (
        paths.resolve_local_path(archived / "input.txt", root=supplied_root).read_bytes()
        == b"dated input"
    )


def test_archived_path_cannot_escape_into_the_new_parent(
    checkouts: tuple[Path, Path], tmp_path: Path
) -> None:
    archived, _ = checkouts
    (tmp_path / "outside.txt").write_bytes(b"outside checkout")

    with pytest.raises(FileNotFoundError):
        SourceCatalogClient().fetch_bytes(str(archived / ".." / "outside.txt"))
