#!/usr/bin/env python3
"""Compare a dated SEC filing census with the CIKs selected for acquisition.

This parser reads saved official quarterly master.idx files. It never fetches SEC data.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from bubble.ingestion.entities.universe import normalize_entity_name

AI_NAME_RE = re.compile(
    r"\b(data cent(?:er|re)s?|compute|cloud|artificial intelligence|AI|GPU|"
    r"semiconductor|photonics|hyperscale|colocation)\b", re.IGNORECASE
)
FINANCING_NAME_RE = re.compile(
    r"\b(funding|finance|financing|securitization|asset backed|SPV)\b",
    re.IGNORECASE,
)


def _open_text(path: Path):
    return gzip.open(path, "rt", errors="replace") if path.suffix == ".gz" else path.open(errors="replace")


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_master(path: Path, *, start: date, end: date):
    """Yield official SEC master-index rows inside the specified filing-date window."""
    with _open_text(path) as stream:
        in_rows = False
        for raw_line in stream:
            line = raw_line.rstrip("\r\n")
            if not in_rows:
                if line.startswith("CIK|Company Name|Form Type|Date Filed|Filename"):
                    in_rows = True
                continue
            if not line or line.startswith("-"):
                continue
            parts = line.split("|", 4)
            if len(parts) != 5:
                continue
            cik, company, form, filed, filename = parts
            try:
                filing_day = date.fromisoformat(filed)
            except ValueError:
                continue
            if start <= filing_day <= end:
                yield {
                    "cik": cik.strip().zfill(10),
                    "company_name": company.strip(),
                    "form": form.strip(),
                    "filing_date": filed,
                    "filing_url": "https://www.sec.gov/Archives/" + filename.strip().lstrip("/"),
                }
        if not in_rows:
            raise ValueError(f"SEC master index header not found: {path}")


def _ciks(paths: list[Path]) -> set[str]:
    result: set[str] = set()
    for path in paths:
        with path.open(newline="") as stream:
            reader = csv.DictReader(stream)
            if "cik" not in (reader.fieldnames or []):
                raise ValueError(f"Missing cik column: {path}")
            result.update((row.get("cik") or "").strip().zfill(10) for row in reader)
    result.discard("0000000000")
    return result


def _dated_entity_matches(path: Path | None, names: set[str]) -> dict[str, dict]:
    if path is None:
        return {}
    matches: dict[str, dict] = {}
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            normalized = row.get("normalized_name") or ""
            if normalized not in names:
                continue
            tables = json.loads(row.get("source_tables") or "{}")
            matches[normalized] = {
                "mention_count": int(row.get("mention_count") or 0),
                "source_tables": tables,
                "source_count": int(row.get("source_count") or 0),
            }
    return matches


def audit(
    *,
    index_paths: list[Path],
    selected_cik_paths: list[Path],
    manifest_paths: list[Path],
    entities_csv: Path | None = None,
    start: date,
    end: date,
) -> dict:
    selected = _ciks(selected_cik_paths)
    manifested = _ciks(manifest_paths)
    unique_filings: set[str] = set()
    unique_accessions: set[str] = set()
    raw_index_rows = 0
    raw_form_counts: Counter[str] = Counter()
    first_form_by_url: dict[str, str] = {}
    multi_form_pairs: list[dict[str, str]] = []
    ci: dict[str, dict] = {}
    form_counts: Counter[str] = Counter()
    daily_counts: Counter[str] = Counter()
    cik_forms: dict[str, set[str]] = defaultdict(set)
    for path in index_paths:
        for row in read_master(path, start=start, end=end):
            raw_index_rows += 1
            raw_form_counts[row["form"]] += 1
            url = row["filing_url"]
            if url in unique_filings:
                if row["form"] != first_form_by_url[url]:
                    multi_form_pairs.append(
                        {
                            "filing_url": url,
                            "first_form": first_form_by_url[url],
                            "additional_form": row["form"],
                        }
                    )
                continue
            unique_filings.add(url)
            first_form_by_url[url] = row["form"]
            unique_accessions.add(Path(url).stem)
            cik = row["cik"]
            ci.setdefault(cik, {"company_name": row["company_name"], "example_filing_url": url})
            form_counts[row["form"]] += 1
            daily_counts[row["filing_date"]] += 1
            cik_forms[cik].add(row["form"])
    index_ciks = set(ci)
    missing_selected = index_ciks - selected
    missing_manifested = index_ciks - manifested
    matched_names = _dated_entity_matches(
        entities_csv, {normalize_entity_name(ci[cik]["company_name"]) for cik in missing_selected}
    )
    exact_entity_matches = [
        {
            "cik": cik,
            "company_name": ci[cik]["company_name"],
            "example_filing_url": ci[cik]["example_filing_url"],
            "dated_entity_match": matched_names[normalize_entity_name(ci[cik]["company_name"])],
        }
        for cik in sorted(missing_selected)
        if normalize_entity_name(ci[cik]["company_name"]) in matched_names
    ]
    candidate_rows = []
    for cik in sorted(missing_selected):
        name = ci[cik]["company_name"]
        match = matched_names.get(normalize_entity_name(name))
        reasons = []
        if match and any(
            table in match["source_tables"]
            for table in ("tracker_records", "queue_records", "ppas", "edgar_deals", "capital_deals")
        ):
            reasons.append("exact_name_in_dated_project_power_or_deal_source")
        if AI_NAME_RE.search(name):
            reasons.append("ai_infrastructure_name_keyword")
        if FINANCING_NAME_RE.search(name):
            reasons.append("financing_vehicle_name_keyword")
        if any(form == "FWP" or form.startswith("424B") for form in cik_forms[cik]):
            reasons.append("offering_document_form_lead")
        if reasons:
            candidate_rows.append(
                {
                    "cik": cik,
                    "company_name": name,
                    "example_filing_url": ci[cik]["example_filing_url"],
                    "forms": sorted(cik_forms[cik]),
                    "lead_reasons": reasons,
                    "dated_entity_match": match,
                }
            )
    candidate_rows.sort(
        key=lambda row: (
            "exact_name_in_dated_project_power_or_deal_source" not in row["lead_reasons"],
            "ai_infrastructure_name_keyword" not in row["lead_reasons"],
            "financing_vehicle_name_keyword" not in row["lead_reasons"],
            row["company_name"],
        )
    )
    return {
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "index_files": [{"path": str(p), "bytes": p.stat().st_size, "sha256": _hash(p)} for p in index_paths],
        "selected_cik_files": [{"path": str(p), "sha256": _hash(p)} for p in selected_cik_paths],
        "manifest_files": [{"path": str(p), "sha256": _hash(p)} for p in manifest_paths],
        "dated_entities_file": (
            {"path": str(entities_csv), "sha256": _hash(entities_csv)} if entities_csv else None
        ),
        "raw_index_rows": raw_index_rows,
        "unique_index_filings": len(unique_filings),
        "unique_index_cik_accession_pairs": len(unique_filings),
        "unique_index_accessions": len(unique_accessions),
        "repeat_cik_accession_rows": raw_index_rows - len(unique_filings),
        "multi_form_cik_accession_pairs": multi_form_pairs,
        "observed_filing_date_min": min(daily_counts, default=None),
        "observed_filing_date_max": max(daily_counts, default=None),
        "requested_end_date_observed": end.isoformat() in daily_counts,
        "filings_by_day": dict(sorted(daily_counts.items())),
        "unique_index_ciks": len(index_ciks),
        "unique_selected_ciks": len(selected),
        "unique_manifested_ciks": len(manifested),
        "index_ciks_absent_from_selection": len(missing_selected),
        "index_ciks_absent_from_manifest": len(missing_manifested),
        "selected_ciks_with_index_filing": len(selected & index_ciks),
        "manifested_ciks_with_index_filing": len(manifested & index_ciks),
        "form_counts": dict(sorted(form_counts.items())),
        "raw_form_counts": dict(sorted(raw_form_counts.items())),
        "absent_from_selection": [
            {"cik": cik, **ci[cik], "forms": sorted(cik_forms[cik])}
            for cik in sorted(missing_selected)
        ],
        "unselected_exact_dated_entity_matches": exact_entity_matches,
        "unselected_exact_dated_entity_match_count": len(exact_entity_matches),
        "unselected_ai_debt_leads": candidate_rows,
        "unselected_ai_debt_lead_count": len(candidate_rows),
        "interpretation": (
            "The SEC master index is an independent public filing denominator for the "
            "specified window. A complete-submission accession can appear under multiple "
            "cofiling CIKs, so CIK-accession pairs and unique accessions differ. Some "
            "CIK-accession pairs have multiple indexed form labels; raw_form_counts retains "
            "both, while form_counts attributes each pair to its first index label. Its CIKs "
            "include funds and issuers unrelated to AI. "
            "Name and form leads require filing-level verification; index inclusion "
            "does not establish a debt or AI exposure. All unselected CIKs are preserved."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, action="append", required=True)
    parser.add_argument("--selected-ciks", type=Path, action="append", required=True)
    parser.add_argument("--manifest", type=Path, action="append", required=True)
    parser.add_argument("--entities", type=Path)
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"output already exists: {args.output}")
    result = audit(
        index_paths=args.index,
        selected_cik_paths=args.selected_ciks,
        manifest_paths=args.manifest,
        entities_csv=args.entities,
        start=args.start,
        end=args.end,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps({key: result[key] for key in (
        "unique_index_filings", "unique_index_ciks", "unique_selected_ciks",
        "index_ciks_absent_from_selection", "index_ciks_absent_from_manifest",
    )}, indent=2))


if __name__ == "__main__":
    main()
