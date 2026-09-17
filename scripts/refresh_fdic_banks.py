#!/usr/bin/env python3
"""Capture the latest available FDIC bank quarter as a dated, complete snapshot."""

from __future__ import annotations

import argparse
import calendar
import json
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

from fdic_bank_distress import BASE, FIELDS, distress


def quarters(as_of: date) -> list[date]:
    candidates = []
    for year in (as_of.year, as_of.year - 1):
        for month in (3, 6, 9, 12):
            last = date(year, month, calendar.monthrange(year, month)[1])
            if last <= as_of:
                candidates.append(last)
    return sorted(candidates, reverse=True)


def fetch_page(quarter: date, offset: int, limit: int = 5000) -> tuple[list[dict], int]:
    params = {
        "filters": f"REPDTE:{quarter:%Y%m%d}",
        "fields": FIELDS,
        "limit": limit,
        "offset": offset,
        "format": "json",
    }
    url = BASE + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": "bubble public research"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    rows = payload.get("data")
    total = payload.get("meta", {}).get("total")
    if not isinstance(rows, list) or total is None:
        raise ValueError(f"Incomplete FDIC API response for {quarter}, offset {offset}")
    return [entry["data"] for entry in rows], int(total)


def fetch_quarter(quarter: date) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        page, total = fetch_page(quarter, offset)
        if not page and offset < total:
            raise ValueError(f"FDIC page missing at offset {offset} of {total}")
        rows.extend(page)
        offset += len(page)
        if offset >= total:
            if len(rows) != total:
                raise ValueError(f"FDIC count mismatch: {len(rows)} of {total}")
            return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    quarter = None
    rows: list[dict] = []
    for candidate in quarters(args.as_of):
        rows = fetch_quarter(candidate)
        if rows:
            quarter = candidate
            break
    if quarter is None:
        raise RuntimeError("FDIC returned no populated quarter by the requested as-of date")

    certificates = [str(row.get("CERT")) for row in rows]
    if any(cert in ("", "None") for cert in certificates):
        raise ValueError("FDIC result contains missing certificates")
    if len(certificates) != len(set(certificates)):
        raise ValueError("FDIC result contains duplicate certificates")
    expected_date = quarter.strftime("%Y%m%d")
    if any("".join(ch for ch in str(row.get("REPDTE")) if ch.isdigit()) != expected_date for row in rows):
        raise ValueError("FDIC result mixes report dates")

    flagged = []
    severity = Counter()
    for row in rows:
        has_flag, reasons = distress(row)
        if not has_flag:
            continue
        flagged.append({"cert": row["CERT"], "name": row.get("NAME"), "state": row.get("STNAME"), "assets_thousands_usd": row.get("ASSET"), "risk_based_capital_pct": row.get("RBCRWAJ"), "roa_pct": row.get("ROA"), "nonperforming_pct": row.get("NPERFV"), "flags": reasons})
        if any("undercapitalized" in flag for flag in reasons):
            severity["undercapitalized"] += 1
        elif any("not well-capitalized" in flag for flag in reasons):
            severity["not_well_capitalized"] += 1
        else:
            severity["other_distress"] += 1

    stamp = args.as_of.isoformat()
    data_path = root / "data/financials" / f"fdic_bank_financials_{stamp}.json"
    report_path = root / "analysis" / f"fdic_bank_distress_{stamp}.json"
    for path in (data_path, report_path):
        if path.exists():
            raise FileExistsError(f"Refusing to replace existing snapshot: {path}")
    source = BASE + "?" + urllib.parse.urlencode({"filters": f"REPDTE:{expected_date}", "fields": FIELDS, "format": "json"})
    data_path.write_text(json.dumps({"as_of": stamp, "quarter": quarter.isoformat(), "source": source, "rows": rows}, indent=2) + "\n")
    report_path.write_text(json.dumps({"as_of": stamp, "quarter": quarter.isoformat(), "institutions_returned": len(rows), "flagged_count": len(flagged), "severity": dict(severity), "flagged": flagged, "raw_snapshot": str(data_path.relative_to(root))}, indent=2) + "\n")
    print(json.dumps({"quarter": quarter.isoformat(), "institutions_returned": len(rows), "flagged_count": len(flagged), "severity": dict(severity), "raw_snapshot": str(data_path.relative_to(root)), "report": str(report_path.relative_to(root))}, indent=2))


if __name__ == "__main__":
    main()
