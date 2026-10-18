#!/usr/bin/env python3
"""Prepare hash-verified local filings for the dated core review, without fetching."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from bubble.ingestion.edgar.document_acquisition import normalize_document_text
from bubble.paths import resolve_local_path

ROOT = Path(__file__).resolve().parents[1]


def prepare(  # noqa: PLR0912, PLR0915 - preserve provenance checks across independent queues and receipts
    run: Path, output: Path, as_of: str
) -> dict[str, Any]:
    panel = json.loads((ROOT / f"analysis/case_zero_financials_{as_of}_v4.json").read_text())
    wanted: dict[str, dict[str, Any]] = {}
    for entity in panel["entities"]:
        latest = entity.get("latest_periodic_filing")
        candidates = ([latest] if latest else []) + [
            filing
            for filing in entity["new_filings_since_june_13"]
            if filing["form"] in {"8-K", "8-K/A", "6-K", "6-K/A"}
        ]
        for filing in candidates:
            if filing["filing_date"] <= as_of:
                wanted[filing["url"]] = {
                    "ticker": entity["ticker"],
                    "role": entity["role"],
                    **filing,
                }
    records = {}
    prefixes = {url.rsplit("/", 1)[0] + "/": row for url, row in wanted.items()}
    with (ROOT / "data/edgar_acquisition_2026-09-16/edgar_document_inventory.csv").open(
        newline=""
    ) as stream:
        for row in csv.DictReader(stream):
            url = row["filing_url"]
            parent = prefixes.get(url.rsplit("/", 1)[0] + "/")
            if parent:
                records[url] = row
                wanted.setdefault(url, {**parent, "url": url, "document_type": "exhibit"})
    databases = [run / "document_queue.sqlite3"]
    extra = run / "exhibit_completion/document_queue.sqlite3"
    if extra.is_file():
        databases.append(extra)
    for database in databases:
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as db:
            for prefix, parent in prefixes.items():
                for url, result in db.execute(
                    "SELECT url,result FROM documents WHERE url>=? AND url<? AND status='acquired'",
                    (prefix, prefix[:-1] + "0"),
                ):
                    if result:
                        doc = json.loads(result).get("document")
                        if doc:
                            records[url] = doc
                            wanted.setdefault(
                                url, {**parent, "url": url, "document_type": "exhibit"}
                            )
    for name in ("core_review_retry", "core_review_public", "core_review_mirrors"):
        receipt = run / name / "manifest.json"
        if receipt.is_file():
            for source in json.loads(receipt.read_text())["sources"]:
                if source.get("status") == "acquired" and source["url"] in wanted:
                    records.setdefault(
                        source["url"],
                        {"local_path": source["path"], "content_hash": source["sha256"]},
                    )
    output.mkdir(parents=True, exist_ok=False)
    manifest: list[dict[str, Any]] = []
    for url, filing in sorted(wanted.items()):
        record = records.get(url)
        if record is None:
            manifest.append({**filing, "status": "not_in_selected_saved_inventory"})
            continue
        source = resolve_local_path(record["local_path"], root=ROOT).resolve()
        opener = gzip.open if source.suffix == ".gz" else open
        with opener(source, "rb") as stream:
            raw = stream.read()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != record["content_hash"]:
            raise ValueError(f"Source hash mismatch: {url}")
        text = normalize_document_text(raw)
        name = (
            filing["ticker"]
            + "-"
            + filing["accession"].replace("-", "")
            + "-"
            + hashlib.sha256(url.encode()).hexdigest()[:12]
            + ".txt"
        )
        path = output / name
        with path.open("x") as stream:
            stream.write(text)
        manifest.append(
            {
                **filing,
                "status": "hash_verified",
                "source_path": str(source.relative_to(ROOT)),
                "source_sha256": digest,
                "normalized_path": str(path.relative_to(ROOT)),
                "normalized_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    result = {
        "as_of": as_of,
        "filings": manifest,
        "verified": sum(row["status"] == "hash_verified" for row in manifest),
        "missing": [row for row in manifest if row["status"] != "hash_verified"],
        "method": "Latest periodic filing and every listed 8-K/6-K since June 13, with their saved exhibits; saved sources only.",
    }
    with (output / "manifest.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    result = prepare(args.run.resolve(), args.output.resolve(), args.as_of)
    print(json.dumps({"verified": result["verified"], "missing": len(result["missing"])}))


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget(512)
    main()
