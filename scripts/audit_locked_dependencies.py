#!/usr/bin/env python3
"""Check every locked registry version against retained PyPI advisory records."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import tomllib
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packaging.utils import canonicalize_name
from packaging.version import Version


def audit(lock: Path, output: Path) -> dict[str, Any]:
    raw_lock = lock.read_bytes()
    packages = [
        row
        for row in tomllib.loads(raw_lock.decode())["package"]
        if row.get("source", {}).get("registry") == "https://pypi.org/simple"
    ]
    output.mkdir(parents=True, exist_ok=False)

    def fetch(package: dict[str, Any]) -> dict[str, Any]:
        name, version = package["name"], package["version"]
        url = f"https://pypi.org/pypi/{name}/{version}/json"
        record = {"name": name, "version": version, "source_uri": url}
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                raw = response.read()
            payload = json.loads(raw)
            if (
                canonicalize_name(payload["info"]["name"]) != canonicalize_name(name)
                or Version(payload["info"]["version"]) != Version(version)
            ):
                raise ValueError("PyPI returned another package or version")
            path = output / f"{name}-{version}.json.gz"
            with path.open("xb") as stream:
                stream.write(gzip.compress(raw, mtime=0))
            return {
                **record,
                "status": "acquired",
                "path": str(path),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "retrieved_utc": datetime.now(UTC).isoformat(),
                "vulnerabilities": payload.get("vulnerabilities", []),
            }
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            return {**record, "status": "failed", "error": str(error)}

    with ThreadPoolExecutor(max_workers=16) as pool:
        pending = [pool.submit(fetch, row) for row in packages]
        records = [future.result() for future in as_completed(pending)]
    records.sort(key=lambda row: (row["name"], row["version"]))
    failures = [row for row in records if row["status"] != "acquired"]
    affected = [
        row
        for row in records
        if any(not item.get("withdrawn") for item in row.get("vulnerabilities", []))
    ]
    result = {
        "lock": str(lock),
        "lock_sha256": hashlib.sha256(raw_lock).hexdigest(),
        "registry_versions": len(packages),
        "records": records,
        "failures": failures,
        "affected_versions": affected,
        "complete": not failures,
        "limits": "Known advisories reported by PyPI for the exact locked versions. This does not establish absence of vulnerabilities. Compare separately with GitHub alerts and upstream source.",
    }
    with (output / "audit.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=Path("uv.lock"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.lock, args.output)
    print(
        json.dumps(
            {
                "registry_versions": result["registry_versions"],
                "failures": len(result["failures"]),
                "affected": [
                    {
                        "name": row["name"],
                        "version": row["version"],
                        "ids": [item["id"] for item in row["vulnerabilities"]],
                    }
                    for row in result["affected_versions"]
                ],
            }
        )
    )
    if result["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget(512)
    main()
