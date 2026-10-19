#!/usr/bin/env python3
"""Find linked credit agreements and indentures in the reviewed issuer statements."""

from __future__ import annotations

import argparse
import gzip
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from build_facility_cashflows import verify_source


def discover(inputs: Path, root: Path) -> list[dict[str, str]]:
    data = json.loads(inputs.read_text())
    found: dict[str, dict[str, str]] = {}
    for issuer in data["issuer_coverage"]:
        source = data["sources"][issuer["periodic_source_id"]]
        verify_source(source, root)
        path = root / source["source_path"]
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rb") as stream:
            soup = BeautifulSoup(stream.read(), "lxml")
        for anchor in soup.find_all("a", href=True):
            parent = anchor.find_parent("tr")
            if parent is None:
                continue
            label = " ".join(parent.get_text(" ", strip=True).split())
            if len(label) > 2000 or not re.search(
                r"indenture|credit agreement|note purchase agreement|common terms agreement",
                label,
                re.I,
            ):
                continue
            uri = urljoin(source["url"], str(anchor["href"]))
            parsed = urlparse(uri)
            if (
                parsed.hostname != "www.sec.gov"
                or "/Archives/edgar/" not in parsed.path
                or parsed.fragment
            ):
                continue
            found[uri] = {
                "id": issuer["ticker"] + "-" + str(len(found)),
                "url": uri,
                "ticker": issuer["ticker"],
                "label": label,
                "referenced_by": source["url"],
                "available_by": source["filing_date"],
            }
    return sorted(found.values(), key=lambda row: (row["ticker"], row["url"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = discover(args.input, Path(__file__).resolve().parents[1])
    with args.output.open("x") as stream:
        json.dump(rows, stream, indent=2)
    print(
        json.dumps(
            {
                "contract_links": len(rows),
                "by_ticker": {
                    ticker: sum(row["ticker"] == ticker for row in rows)
                    for ticker in sorted({row["ticker"] for row in rows})
                },
            }
        )
    )


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget(512)
    main()
