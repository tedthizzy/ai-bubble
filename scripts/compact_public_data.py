#!/usr/bin/env python3
"""Apply reversible APFS compression to immutable public-source text files."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import stat
import subprocess
import sys
import uuid
import zlib
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

ROOT = Path(__file__).resolve().parents[1]
COMPRESSED = 0x20
EXTENSIONS = {".htm", ".html", ".txt", ".json", ".xml", ".csv"}


def xattrs(path: Path) -> dict[str, bytes]:
    library = ctypes.CDLL(None, use_errno=True)
    library.listxattr.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
    library.listxattr.restype = ctypes.c_ssize_t
    library.getxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p,
                               ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int]
    library.getxattr.restype = ctypes.c_ssize_t
    filename = os.fsencode(path)
    size = library.listxattr(filename, None, 0, 1)
    if size < 0:
        raise OSError(ctypes.get_errno(), "Cannot enumerate source metadata")
    names = ctypes.create_string_buffer(size)
    count = library.listxattr(filename, names, size, 1)
    if count < 0:
        raise OSError(ctypes.get_errno(), "Cannot read source metadata names")
    result = {}
    for name in names.raw[:count].split(b"\0"):
        if not name:
            continue
        length = library.getxattr(filename, name, None, 0, 0, 1)
        if length < 0:
            raise OSError(ctypes.get_errno(), "Cannot measure source metadata")
        value = ctypes.create_string_buffer(length)
        actual = library.getxattr(filename, name, value, length, 0, 1)
        if actual < 0:
            raise OSError(ctypes.get_errno(), "Cannot read source metadata")
        result[os.fsdecode(name)] = value.raw[:actual]
    return result


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def clone(source: Path, destination: Path) -> None:
    library = ctypes.CDLL(None, use_errno=True)
    library.clonefile.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint32]
    library.clonefile.restype = ctypes.c_int
    # Both paths must be resolved: macOS /var is itself a symlink.
    if library.clonefile(os.fsencode(source), os.fsencode(destination), 1 | 8):
        raise OSError(ctypes.get_errno(), "APFS snapshot clone failed")


def identity(info: os.stat_result) -> tuple[int, ...]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def metadata(path: Path) -> dict[str, Any]:
    info = path.stat(follow_symlinks=False)
    return {
        "mode": stat.S_IMODE(info.st_mode), "uid": info.st_uid, "gid": info.st_gid,
        "mtime_ns": info.st_mtime_ns, "atime_ns": info.st_atime_ns,
        "flags": info.st_flags, "size": info.st_size, "allocated": info.st_blocks * 512,
        "xattrs": {
            name: hashlib.sha256(value).hexdigest()
            for name, value in xattrs(path).items()
            if name not in {"com.apple.decmpfs", "com.apple.ResourceFork"}
        },
    }


def save(path: Path, data: Any) -> None:
    with path.open("x") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")


def eligible(path: Path) -> bool:
    info = path.lstat()
    return (
        stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and not (info.st_flags & ~0x40)
        and info.st_uid == os.getuid() and 65536 <= info.st_size <= 256 * 1024**2
        and info.st_blocks * 512 >= 65536
        and "com.apple.ResourceFork" not in xattrs(path)
    )


def compressible(path: Path) -> bool:
    size = path.stat().st_size
    sample = bytearray()
    with path.open("rb") as stream:
        for offset in (0, max(0, size // 2 - 16384), max(0, size - 32768)):
            stream.seek(offset)
            sample.extend(stream.read(32768))
    return len(zlib.compress(sample, 1)) < len(sample) * .75


def compact(path: Path, archive: Path) -> dict[str, Any]:
    if not eligible(path) or not compressible(path):
        return {"path": str(path), "status": "skipped"}
    original_stat = path.lstat()
    original = metadata(path)
    source_hash = digest(path)
    action = archive / uuid.uuid4().hex
    action.mkdir()
    record = {"path": str(path), "sha256": source_hash, "metadata": original}
    save(action / "original.json", record)
    compressed = action / "compressed"
    subprocess.run(
        ["/usr/bin/ditto", "--hfsCompression", "--nocache", str(path), str(compressed)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    copy = metadata(compressed)
    if digest(compressed) != source_hash:
        raise ValueError(f"Compression changed bytes: {path}")
    keys = ("size", "mode", "uid", "gid", "mtime_ns", "xattrs")
    if any(copy[key] != original[key] for key in keys):
        raise ValueError(f"Compression changed source metadata: {path}")
    if copy["flags"] & ~COMPRESSED != original["flags"]:
        raise ValueError(f"Compression changed unrelated source flags: {path}")
    if identity(path.lstat()) != identity(original_stat):
        raise ValueError(f"Source changed during compression; untouched: {path}")
    if copy["allocated"] >= original["allocated"]:
        save(action / "result.json", {**record, "status": "no_savings", "copy_preserved": True})
        return {"path": str(path), "status": "no_savings", "action": str(action)}
    # Snapshot the verified original bytes from their compressed representation.
    # APFS shares these compressed blocks with the replacement until either changes.
    clone(compressed, action / "snapshot")
    if digest(action / "snapshot") != source_hash:
        raise ValueError("Snapshot verification failed")
    if identity(path.lstat()) != identity(original_stat):
        raise ValueError(f"Source changed before replacement; untouched: {path}")
    os.replace(compressed, path)
    if digest(path) != source_hash:
        raise ValueError(f"Post-replacement verification failed: {path}")
    result = {**record, "status": "compressed", "allocated_after": path.stat().st_blocks * 512,
              "snapshot": str(action / "snapshot"), "action": str(action)}
    save(action / "result.json", result)
    return result


def restore(action: Path) -> dict[str, Any]:
    record = json.loads((action / "result.json").read_text())
    if record["status"] != "compressed":
        raise ValueError("Action did not replace its source")
    path = Path(record["path"])
    saved = Path(record["snapshot"])
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise ValueError("Restore target is no longer a regular file")
    if digest(path) != record["sha256"] or digest(saved) != record["sha256"]:
        raise ValueError("Restore would overwrite changed content")
    attempt = action / ("restore-" + uuid.uuid4().hex)
    attempt.mkdir()
    clone(path, attempt / "before")
    target = attempt / "uncompressed"
    subprocess.run(
        ["/usr/bin/ditto", "--nohfsCompression", "--nopreserveHFSCompression",
         "--nocache", str(saved), str(target)], check=True, capture_output=True,
    )
    if digest(target) != record["sha256"] or target.stat().st_flags & COMPRESSED:
        raise ValueError("Uncompressed restore verification failed")
    original = record["metadata"]
    current = metadata(path)
    if any(current[key] != original[key] for key in ("mode", "uid", "gid", "mtime_ns", "xattrs")):
        raise ValueError("Restore target metadata changed; untouched")
    if current["flags"] & ~COMPRESSED != original["flags"]:
        raise ValueError("Restore target flags changed; untouched")
    os.utime(target, ns=(original["atime_ns"], original["mtime_ns"]))
    if identity(path.lstat()) != identity(info):
        raise ValueError("Restore target changed; untouched")
    os.replace(target, path)
    result = {"status": "restored", "path": str(path), "sha256": digest(path)}
    save(attempt / "result.json", result)
    return result


def candidates(roots: list[Path]) -> Iterator[Path]:
    for root in roots:
        for directory, folders, files in os.walk(root, followlinks=False):
            folders[:] = [f for f in folders if not f.startswith(".") and not (Path(directory) / f).is_symlink()]
            for name in files:
                path = Path(directory) / name
                if not name.startswith(".") and path.suffix.lower() in EXTENSIONS and not path.is_symlink():
                    yield path


def main() -> None:
    if sys.platform != "darwin":
        raise RuntimeError("APFS compression requires macOS")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roots", nargs="+", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--restore-action", type=Path)
    args = parser.parse_args()
    if args.restore_action:
        action = args.restore_action.resolve()
        if not action.is_relative_to(ROOT / ".codex/storage-compaction"):
            raise ValueError("Restore action must be a retained snapshot in this checkout")
        record = json.loads((action / "result.json").read_text())
        if not Path(record["path"]).resolve().is_relative_to(ROOT / "data"):
            raise ValueError("Restore target must remain inside this checkout's data directory")
        print(json.dumps(restore(action)))
        return
    if not args.roots or not args.archive:
        parser.error("--roots and --archive are required for compression")
    roots = [path.resolve() for path in args.roots]
    for path in roots:
        if not path.is_relative_to(ROOT / "data") or path.name.startswith("refresh_"):
            raise ValueError("Scope must be historical public data under this checkout's data directory")
    archive = args.archive.resolve()
    if not archive.is_relative_to(ROOT / ".codex/storage-compaction"):
        raise ValueError("Snapshots must remain in .codex/storage-compaction")
    archive.mkdir(parents=True, exist_ok=False)
    free_before = os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize
    totals = {"compressed": 0, "skipped": 0, "no_savings": 0, "errors": 0, "allocated_reduction_bytes": 0}
    # Bound both in-flight files and worker memory; do not submit the whole tree.
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = set()
        def collect(future: Future[dict[str, Any]]) -> None:
            try:
                result = future.result()
                totals[result["status"]] += 1
                if result["status"] == "compressed":
                    totals["allocated_reduction_bytes"] += result["metadata"]["allocated"] - result["allocated_after"]
                    if totals["compressed"] % 100 == 0:
                        print(json.dumps({"progress": totals}), flush=True)
            except Exception as error:
                totals["errors"] += 1
                print(json.dumps({"error": str(error)}), flush=True)
        for path in candidates(roots):
            pending.add(pool.submit(compact, path, archive))
            if len(pending) >= 4:
                future = next(as_completed(pending))
                pending.remove(future)
                collect(future)
        for future in as_completed(pending):
            collect(future)
    result = {"roots": list(map(str, roots)), "archive": str(archive), **totals,
              "free_before": free_before, "free_after": os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize,
              "free_space_limit": "Concurrent acquisition and APFS snapshots affect volume free-space deltas."}
    save(archive / "summary.json", result)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget(512)
    main()
