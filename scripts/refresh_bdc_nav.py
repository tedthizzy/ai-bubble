#!/usr/bin/env python3
"""Card reported BDC NAV from a dated, saved SEC Company Facts panel."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any


def reported_nav(facts: dict[str, Any], as_of: str) -> dict[str, Any]:
    records = facts.get("facts", {}).get("us-gaap", {}).get("NetAssetValuePerShare", {})
    rows = [
        row
        for row in records.get("units", {}).get("USD/shares", [])
        if row.get("form") in {"10-Q", "10-Q/A", "10-K", "10-K/A"}
        and not row.get("start")
        and "1900-01-01" <= row.get("end", "") <= row.get("filed", "") <= as_of
        and isinstance(row.get("val"), (int, float))
        and row["val"] > 0
    ]
    if not rows:
        raise ValueError("No reported quarterly NAV in saved SEC facts")
    latest = max(rows, key=lambda row: (row["end"], row["filed"]))
    same = [row for row in rows if (row["end"], row["filed"]) == (latest["end"], latest["filed"])]
    if len({row["val"] for row in same}) != 1:
        raise ValueError("Conflicting reported NAV facts at the latest period and filing date")
    return dict(latest)


def build(panel_path: Path, raw: Path, as_of: str) -> dict[str, Any]:
    panel = json.loads(panel_path.read_text())
    if panel["as_of"] != as_of:
        raise ValueError("Financial panel date differs from requested NAV date")
    result: dict[str, Any] = {}
    for entity in panel["entities"]:
        if entity["role"] != "bdc":
            continue
        cik = str(entity["cik"]).zfill(10)
        path = raw / f"CIK{cik}-companyfacts.json.gz"
        with gzip.open(path, "rt") as stream:
            fact = reported_nav(json.load(stream), as_of)
        accession = fact["accn"]
        with gzip.open(raw / f"CIK{cik}-submissions.json.gz", "rt") as stream:
            recent = json.load(stream)["filings"]["recent"]
        try:
            index = recent["accessionNumber"].index(accession)
        except ValueError as error:
            raise ValueError(f"NAV filing missing from saved submissions: {entity['ticker']}") from error
        base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/"
        result[entity["ticker"]] = {
            "nav_usd_per_share": fact["val"],
            "nav_asof": fact["end"],
            "filed": fact["filed"],
            "form": fact["form"],
            "source_uri": base + recent["primaryDocument"][index],
            "fact_tag": "us-gaap:NetAssetValuePerShare",
            "raw_path": str(path),
            "raw_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    return {
        "as_of": as_of,
        "definition": "Latest reported quarterly NAV per share in saved SEC periodic filings",
        "panel": str(panel_path),
        "bdc": result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.panel, args.raw_dir, str(args.as_of))
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"output": str(args.output), "bdcs": len(result["bdc"]),
                      "periods": sorted({row["nav_asof"] for row in result["bdc"].values()})}))


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget(512)
    main()
