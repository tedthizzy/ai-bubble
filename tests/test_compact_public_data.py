import sys
from pathlib import Path

import pytest
from scripts.compact_public_data import clone, compact, digest, metadata, restore

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="APFS compression requires macOS")


def test_compression_roundtrip_retains_bytes_metadata_and_independent_snapshot(tmp_path: Path):
    path = tmp_path / "public-source.html"
    path.write_bytes(b"<p>Public source evidence, retained in full.</p>\n" * 30000)
    archive = tmp_path / "snapshots"
    archive.mkdir()
    before = metadata(path)
    result = compact(path, archive)
    assert result["status"] == "compressed"
    snapshot = Path(result["snapshot"])
    derivative = tmp_path / "independent-derivative"
    clone(path, derivative)
    with derivative.open("r+b") as stream:
        stream.write(b"EDITED")
    assert digest(snapshot) == digest(path) == result["sha256"]
    assert digest(derivative) != result["sha256"]
    assert restore(Path(result["action"]))["status"] == "restored"
    after = metadata(path)
    for key in ("mode", "uid", "gid", "mtime_ns", "flags", "xattrs", "size"):
        assert before[key] == after[key]
    assert compact(path, archive)["status"] == "compressed"


def test_restore_refuses_changed_metadata(tmp_path: Path):
    path = tmp_path / "public-source.txt"
    path.write_bytes(b"Retained public record\n" * 10000)
    archive = tmp_path / "snapshots"
    archive.mkdir()
    result = compact(path, archive)
    path.chmod(0o600 if path.stat().st_mode & 0o777 != 0o600 else 0o640)
    with pytest.raises(ValueError, match="metadata changed"):
        restore(Path(result["action"]))
    assert digest(path) == result["sha256"]
