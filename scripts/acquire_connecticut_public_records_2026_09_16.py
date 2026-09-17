"""Acquire complete Connecticut Secretary of the State public-record exports.

The three Socrata datasets are downloaded without an account or API key. Raw
records contain personal names and addresses and belong in gitignored data/.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


DATASETS = {
    "ucc": "xfev-8smz",
    "business_master": "n7gp-d28j",
    "business_filings": "ah3s-bes7",
}
USER_AGENT = "BubbleResearch/1.0 (public Connecticut data acquisition)"


def fetch_json(url: str) -> object:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def source_state(dataset_id: str) -> dict[str, object]:
    metadata = fetch_json(f"https://data.ct.gov/api/views/{dataset_id}.json")
    count_result = fetch_json(
        f"https://data.ct.gov/resource/{dataset_id}.json?$select=count(*)"
    )
    assert isinstance(metadata, dict)
    assert isinstance(count_result, list)
    return {
        "name": metadata["name"],
        "updated_at_utc": datetime.fromtimestamp(
            metadata["rowsUpdatedAt"], timezone.utc
        ).isoformat(),
        "source_row_count": int(count_result[0]["count"]),
        "schema": [column["fieldName"] for column in metadata["columns"]],
    }


def count_csv(path: Path) -> tuple[int, list[str]]:
    csv.field_size_limit(100_000_000)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        return sum(1 for _ in reader), header


def acquire_one(name: str, dataset_id: str, output_dir: Path) -> dict[str, object]:
    url = f"https://data.ct.gov/api/v3/views/{dataset_id}/export.csv?accessType=DOWNLOAD"
    before = source_state(dataset_id)
    final_path = output_dir / f"{name}_{dataset_id}.csv"
    part_path = output_dir / f"{name}_{dataset_id}.csv.part"
    if final_path.exists() or part_path.exists():
        raise FileExistsError(f"refusing to overwrite existing acquisition: {final_path}")

    digest = hashlib.sha256()
    size = 0
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        if response.status != 200 or "csv" not in response.headers.get("Content-Type", ""):
            raise RuntimeError(f"unexpected response for {dataset_id}: {response.status}")
        with part_path.open("xb") as handle:
            while block := response.read(1024 * 1024):
                handle.write(block)
                digest.update(block)
                size += len(block)

    parsed_rows, exported_header = count_csv(part_path)
    after = source_state(dataset_id)
    source_stable = before == after
    count_matches = parsed_rows == before["source_row_count"] == after["source_row_count"]
    if not source_stable or not count_matches:
        raise RuntimeError(
            f"{name}: source changed during acquisition or row count differs: "
            f"parsed={parsed_rows}; before={before}; after={after}; retained={part_path}"
        )
    part_path.rename(final_path)
    return {
        "dataset": name,
        "dataset_id": dataset_id,
        "source_url": f"https://data.ct.gov/d/{dataset_id}",
        "export_url": url,
        "acquired_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_before": before,
        "source_after": after,
        "parsed_rows": parsed_rows,
        "exported_header": exported_header,
        "bytes": size,
        "sha256": digest.hexdigest(),
        "count_matches_source": count_matches,
        "source_stable_during_acquisition": source_stable,
        "raw_file": str(final_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("data/off_edgar_expansion_2026-09-16/connecticut"),
    )
    parser.add_argument(
        "--datasets", nargs="+", choices=sorted(DATASETS), default=list(DATASETS)
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    with ThreadPoolExecutor(max_workers=min(3, len(args.datasets))) as executor:
        futures = {
            executor.submit(acquire_one, name, DATASETS[name], args.output_dir): name
            for name in args.datasets
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(
                f"{result['dataset']}: {result['parsed_rows']:,} rows, "
                f"{result['bytes']:,} bytes, verified source count",
                flush=True,
            )
    manifest = {
        "acquisition_date_pacific": "2026-09-16",
        "records": sorted(results, key=lambda row: row["dataset"]),
        "interpretation": (
            "UCC rows are filing/debtor/secured-party records, not unique loans or "
            "outstanding balances. Registry rows identify entities and filings, not "
            "current economic activity. Raw records may include personal data."
        ),
    }
    manifest_path = args.output_dir / "acquisition_manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"refusing to overwrite manifest: {manifest_path}")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"manifest: {manifest_path}", flush=True)


if __name__ == "__main__":
    main()
