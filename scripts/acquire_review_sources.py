#!/usr/bin/env python3
"""Save explicit public review sources with hashes and observed retrieval times."""

from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from refresh_public_sources import IDENTITY

from bubble.ingestion.concurrency import DomainFetchLimiter, FetchConcurrencyConfig


def acquire(catalog: Path, output: Path) -> list[dict[str, Any]]:
    sources = json.loads(catalog.read_text())
    if not isinstance(sources, list) or any(
        not isinstance(row, dict)
        or not isinstance(row.get("id"), str)
        or not isinstance(row.get("url"), str)
        for row in sources
    ):
        raise ValueError("Review catalog must be a JSON array of objects with id and url strings")
    output.mkdir(parents=True, exist_ok=False)
    limiter = DomainFetchLimiter(
        FetchConcurrencyConfig(
            max_workers=16,
            sec_domain_concurrency=1,
            sec_requests_per_second=1,
            other_domain_concurrency=4,
            other_requests_per_second=2,
        )
    )

    def fetch(source: dict[str, Any]) -> dict[str, Any]:
        uri = source["url"]
        record = {**source, "retrieved_utc": datetime.now(UTC).isoformat()}
        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=45,
                headers={"User-Agent": IDENTITY},
            ) as client:

                def request() -> bytes:
                    with client.stream("GET", uri) as response:
                        response.raise_for_status()
                        raw = bytearray()
                        for block in response.iter_bytes():
                            raw.extend(block)
                            if len(raw) > 16 * 1024**2:
                                raise ValueError(
                                    "Review source exceeds 16 MiB; use streaming acquisition"
                                )
                        return bytes(raw)

                raw = limiter.run(uri, request)
            name = hashlib.sha256(uri.encode()).hexdigest() + ".raw"
            with (output / name).open("xb") as stream:
                stream.write(raw)
            return {
                **record,
                "status": "acquired",
                "path": str(output / name),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
            }
        except (httpx.HTTPError, ValueError) as error:
            return {
                **record,
                "status": "failed",
                "error_type": type(error).__name__,
                "http_status": error.response.status_code
                if isinstance(error, httpx.HTTPStatusError)
                else None,
            }

    with ThreadPoolExecutor(max_workers=16) as executor:
        results = list(executor.map(fetch, sources))
    with (output / "manifest.json").open("x") as stream:
        json.dump({"sources": results}, stream, indent=2)
        stream.write("\n")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", type=Path, help="JSON array of objects with id and url strings")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    results = acquire(args.catalog, args.output)
    print(
        json.dumps(
            {
                "acquired": sum(r["status"] == "acquired" for r in results),
                "failures": [r for r in results if r["status"] == "failed"],
            }
        )
    )


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget(512)
    main()
