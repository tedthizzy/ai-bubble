#!/usr/bin/env python3
"""Build an isolated entity census from the September 2026 acquired source rows."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from bubble.ingestion.entities import build_entity_universe
from bubble.ingestion.entities.universe import SOURCE_SPECS

DATE = "2026-09-16"
ROOT = Path(__file__).resolve().parent.parent
ACQUIRED = ROOT / f"data/source_acquisition_{DATE}"
REFERENCE = ROOT / "data/entity_universe/raw/sec_company_tickers_exchange_2026-09-16.json"
SOURCE_MAP = {
    "source_acquisition/source_rows/lei_records.csv": ACQUIRED / "gleif/source_rows/lei_records.csv",
    "source_acquisition/source_rows/ownership_records.csv": ACQUIRED
    / "gleif/source_rows/ownership_records.csv",
    "source_acquisition/source_rows/ppas.csv": ACQUIRED / "non_gleif/source_rows/ppas.csv",
    "source_acquisition/source_rows/tracker_records.csv": ACQUIRED
    / "non_gleif/source_rows/tracker_records.csv",
    "source_acquisition/source_rows/queue_records.csv": ACQUIRED
    / "derived/queue_combined_full_serial_2026-09-16/source_rows/queue_records.csv",
    "source_acquisition/source_rows/permit_records.csv": ACQUIRED
    / "non_gleif/source_rows/permit_records.csv",
    "source_acquisition/source_rows/equipment_records.csv": ACQUIRED
    / "non_gleif/source_rows/equipment_records.csv",
}


def _fingerprint(path: Path) -> dict[str, str | int]:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def _write_filing_rows(manifest: Path, output: Path) -> int:
    """Convert SEC submission-list rows to the universe builder's filing schema."""
    stamp = datetime.fromtimestamp(manifest.stat().st_mtime, UTC).isoformat()
    fields = [
        "name", "source_uri", "source_type", "retrieved_at", "content_hash",
        "local_path", "record_index", "filing_accession",
    ]
    count = 0
    with manifest.open(newline="") as source, output.open("w", newline="") as target:
        reader = csv.DictReader(source)
        required = {"company_name", "source_uri", "accession_number"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"SEC manifest missing fields {required - set(reader.fieldnames or [])}")
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        seen: set[tuple[str, str]] = set()
        for row in reader:
            key = (row.get("cik") or "", row.get("accession_number") or "")
            if key in seen:
                continue
            seen.add(key)
            name = (row.get("company_name") or "").strip()
            uri = (row.get("source_uri") or "").strip()
            if not name or not uri:
                continue
            count += 1
            writer.writerow(
                {
                    "name": name,
                    "source_uri": uri,
                    "source_type": "sec_edgar",
                    "retrieved_at": stamp,
                    "content_hash": row.get("provenance_content_hash") or "",
                    "local_path": str(manifest.resolve()),
                    "record_index": count,
                    "filing_accession": row.get("accession_number") or "",
                }
            )
    return count


def run(
    *,
    label: str,
    filings_manifest: Path | None,
    edgar_deals: Path | None,
    capital_deals: Path | None,
    input_base: Path,
    output_base: Path,
) -> dict:
    if not re.fullmatch(r"[a-z0-9_]+", label):
        raise ValueError("label must contain only lowercase letters, numbers and underscore")
    input_dir = input_base / f"economy_input_{DATE}_{label}"
    output_dir = output_base / f"entity_universe_{DATE}_{label}"
    if input_dir.exists() or output_dir.exists():
        raise FileExistsError(f"dated run already exists: {input_dir} or {output_dir}")
    mapping = dict(SOURCE_MAP)
    if filings_manifest is not None and not filings_manifest.is_file():
        raise FileNotFoundError(filings_manifest)
    if edgar_deals is not None:
        mapping["edgar_acquisition/deals.csv"] = edgar_deals
    if capital_deals is not None:
        mapping["capital/deals.csv"] = capital_deals
    missing = [str(path) for path in [*mapping.values(), REFERENCE] if not path.is_file()]
    if missing:
        raise FileNotFoundError("dated source missing: " + "; ".join(missing))

    # New dated directories are immutable run records. June paths are never copied in.
    input_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    for relative, source in mapping.items():
        target = input_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source.resolve())
    filing_rows = 0
    if filings_manifest is not None:
        target = input_dir / "source_acquisition/source_rows/filings.csv"
        target.parent.mkdir(parents=True, exist_ok=True)
        filing_rows = _write_filing_rows(filings_manifest, target)
        mapping["source_acquisition/source_rows/filings.csv"] = target

    summary = build_entity_universe(
        input_dir,
        output_dir=output_dir,
        sec_reference_json=REFERENCE,
        fetch_sec_reference=False,
    )
    included_specs = {spec.relative_path for spec in SOURCE_SPECS if (input_dir / spec.relative_path).is_file()}
    result = {
        "as_of": DATE,
        "run_label": label,
        "summary": summary.to_dict(),
        "input_files": {key: _fingerprint(source) for key, source in mapping.items()},
        "sec_reference": _fingerprint(REFERENCE),
        "filing_rows_derived": filing_rows,
        "included_entity_source_specs": sorted(included_specs),
        "excluded_entity_source_specs": sorted(
            spec.relative_path for spec in SOURCE_SPECS if spec.relative_path not in included_specs
        ),
        "exclusions": {
            "physical_derived_tables": "Excluded to avoid counting the same acquired tracker, permit, and equipment rows twice.",
            "june_source_rows": "No source_acquisition or capital inputs from the June tree are linked.",
            "private_filers": "The SEC exchange-ticker reference cannot identify every private entity or SPV.",
        },
    }
    (output_dir / "dated_input_manifest.json").write_text(json.dumps(result, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    parser.add_argument("--filings-manifest", type=Path)
    parser.add_argument("--edgar-deals", type=Path)
    parser.add_argument("--capital-deals", type=Path)
    parser.add_argument("--input-base", type=Path, default=ROOT / "data")
    parser.add_argument("--output-base", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    result = run(
        label=args.label,
        filings_manifest=args.filings_manifest,
        edgar_deals=args.edgar_deals,
        capital_deals=args.capital_deals,
        input_base=args.input_base,
        output_base=args.output_base,
    )
    print(json.dumps({"summary": result["summary"], "excluded_specs": result["excluded_entity_source_specs"]}, indent=2))


if __name__ == "__main__":
    main()
