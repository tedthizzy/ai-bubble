#!/usr/bin/env python3
"""Refresh markets using the dated SEC panel without a second SEC request pool."""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import refresh_live_overlay as overlay


def saved_counts(panel_path: Path, raw: Path) -> dict[str, dict[str, int | str]]:
    panel = json.loads(panel_path.read_text())
    today = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    if date.fromisoformat(panel["as_of"]) != today:
        raise ValueError("Saved SEC panel must have today's acquisition date")
    cutoff = (today - timedelta(days=7)).isoformat()
    ciks = {row["ticker"]: str(row["cik"]).zfill(10) for row in panel["entities"]}
    result = {}
    for node, ticker in overlay.EDGAR_TICKERS.items():
        if ticker not in ciks:
            raise ValueError(f"Missing SEC panel ticker: {ticker}")
        with gzip.open(raw / f"CIK{ciks[ticker]}-submissions.json.gz", "rt") as stream:
            recent = json.load(stream)["filings"]["recent"]
        result[node] = {
            "observed_as_of": today.isoformat(),
            "new_8k_7d": sum(
                form.startswith("8-K") and cutoff <= filed <= today.isoformat()
                for form, filed in zip(recent["form"], recent["filingDate"], strict=True)
            ),
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    args = parser.parse_args()
    return overlay.main(saved_edgar=saved_counts(args.panel, args.raw_dir))


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget(512)
    raise SystemExit(main())
