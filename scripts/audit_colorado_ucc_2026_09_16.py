#!/usr/bin/env python3
"""Audit Colorado public UCC bulk exports and identify entity-name leads."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

AS_OF = "2026-09-16"
DATASETS = {
    "debtor": ("8upq-58vz", 2015653),
    "filing": ("wffy-3uut", 2592624),
    "collateral": ("4am6-w6u4", 1704752),
}
NAME_PATTERNS = {
    "CoreWeave": re.compile(r"\bcoreweave\b", re.I),
    "Crusoe": re.compile(r"\bcrusoe\b", re.I),
    "Vantage Data Centers": re.compile(r"\bvantage\s+data\s+centers?\b", re.I),
    "EdgeCore": re.compile(r"\bedgecore\b", re.I),
    "Prime Data Centers": re.compile(r"\bprime\s+data\s+centers?\b", re.I),
    "QTS": re.compile(r"\bqts\b", re.I),
    "Flexential": re.compile(r"\bflexential\b", re.I),
    "CloudHQ": re.compile(r"\bcloudhq\b", re.I),
    "Nscale": re.compile(r"\bnscale\b", re.I),
    "Nebius": re.compile(r"\bnebius\b", re.I),
    "Cipher Mining": re.compile(r"\bcipher\s+mining\b", re.I),
    "Hut 8": re.compile(r"\bhut\s*8\b", re.I),
    "Applied Digital": re.compile(r"\bapplied\s+digital\b", re.I),
    "TeraWulf": re.compile(r"\bterawulf\b", re.I),
    "Galaxy Digital": re.compile(r"\bgalaxy\s+digital\b", re.I),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_dataset(
    path: Path, kind: str, candidate_fileids: set[str] | None = None
) -> tuple[dict, list[dict]]:
    action_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    matched: list[dict] = []
    count = 0
    missing_fileid = 0
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        columns = reader.fieldnames or []
        for row in reader:
            count += 1
            fileid = row.get("fileid", row.get("fileId", ""))
            if not fileid:
                missing_fileid += 1
            if kind == "debtor":
                action_counts[row.get("actiontype", "")] += 1
                status_counts[row.get("recordstatus", "")] += 1
                name = row.get("organizationname", "")
                hits = [label for label, pattern in NAME_PATTERNS.items() if pattern.search(name)]
                if hits:
                    matched.append(
                        {
                            "fileid": fileid,
                            "organizationname": name,
                            "matches": ";".join(hits),
                            "recordstatus": row.get("recordstatus", ""),
                            "source_row": count + 1,
                        }
                    )
            elif kind == "filing":
                type_counts[row.get("filingType", "")] += 1
                if candidate_fileids and fileid in candidate_fileids:
                    matched.append(
                        {
                            "fileid": fileid,
                            "filing_date": row.get("filingDate", ""),
                            "filing_type": row.get("filingType", ""),
                            "document_type": row.get("documentType", ""),
                            "termination_flag": row.get("terminationFlag", ""),
                            "source_row": count + 1,
                        }
                    )
            else:
                action_counts[row.get("actiontype", "")] += 1
                status_counts[row.get("recordstatus", "")] += 1
                if candidate_fileids and fileid in candidate_fileids:
                    matched.append(
                        {
                            "fileid": fileid,
                            "collateral_description": row.get("collateraldescription", ""),
                            "recordstatus": row.get("recordstatus", ""),
                            "source_row": count + 1,
                        }
                    )
    summary = {
        "raw_path": str(path),
        "raw_sha256": sha256(path),
        "row_count": count,
        "columns": columns,
        "missing_fileid_rows": missing_fileid,
        "action_type_counts": dict(action_counts),
        "record_status_counts": dict(status_counts),
        "filing_type_counts": dict(type_counts),
        "candidate_rows": len(matched),
    }
    return summary, matched


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    candidates = {}
    for kind in ("debtor", "filing", "collateral"):
        dataset_id, expected = DATASETS[kind]
        path = args.raw_dir / f"co_ucc_{dataset_id}_{AS_OF}.csv"
        if not path.is_file():
            raise FileNotFoundError(path)
        linked_fileids = {r["fileid"] for r in candidates.get("debtor", [])}
        summary, matched = scan_dataset(path, kind, linked_fileids)
        summary["api_row_count_before_download"] = expected
        summary["matches_api_row_count"] = summary["row_count"] == expected
        summary["source_uri"] = (
            f"https://data.colorado.gov/api/views/{dataset_id}/rows.csv?accessType=DOWNLOAD"
        )
        summary["source_dataset_page"] = f"https://data.colorado.gov/d/{dataset_id}"
        results[kind] = summary
        candidates[kind] = matched
    leads_path = args.output_dir / "ucc_named_entity_leads.json"
    leads_path.write_text(json.dumps(candidates, indent=2, sort_keys=True) + "\n")
    output = {
        "as_of_pacific_date": AS_OF,
        "datasets": results,
        "named_entity_leads_path": str(leads_path),
        "named_entity_pattern_counts": dict(
            Counter(label for row in candidates["debtor"] for label in row["matches"].split(";"))
        ),
        "distinct_candidate_fileids": len({r["fileid"] for r in candidates["debtor"]}),
        "caveats": [
            "Colorado is one jurisdiction, not a national UCC corpus.",
            "A UCC filing is notice of a security interest; it does not disclose debt outstanding or prove borrower distress.",
            "Name matches are unverified leads and may include different legal entities or historical/inactive records.",
            "The public raw debtor export includes individual names/addresses and IDs; keep raw files outside git and do not publish them.",
        ],
    }
    summary_path = args.output_dir / "ucc_summary.json"
    summary_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                **output,
                "datasets": {
                    k: {
                        "row_count": v["row_count"],
                        "matches_api_row_count": v["matches_api_row_count"],
                        "candidate_rows": v["candidate_rows"],
                    }
                    for k, v in results.items()
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
