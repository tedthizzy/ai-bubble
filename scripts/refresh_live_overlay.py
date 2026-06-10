#!/usr/bin/env python
"""Refresh viz/live.json -- the hourly market/filings overlay for the public viz.

Keyless public sources only (safe to run from GitHub Actions on a schedule):
- Stooq daily-history CSV for last/previous close per public ticker in the graph
  (Yahoo chart API as a per-ticker fallback)
- SEC EDGAR submissions API for new 8-K counts (trailing 7 days) per cluster issuer;
  CIKs are resolved at runtime from SEC's own company_tickers.json (nothing hardcoded)

The adjudicated forensic numbers in viz/graph_data.json do NOT change here;
this overlay only adds freshness (prices, day moves, new filings) on top of the
evidence-gated verdicts. If every source fails, the existing live.json is left
untouched so the page never shows a falsely-advanced timestamp.
"""

from __future__ import annotations

import csv
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "viz" / "live.json"
UA = {"User-Agent": "ai-bubble-live-overlay/1.0 (+https://github.com/tedthizzy/ai-bubble)"}
# SEC fair-access policy wants a declared tool with a contact in the User-Agent.
SEC_UA = {"User-Agent": "ai-bubble tedthizzy@users.noreply.github.com"}

# node id (must match viz/graph_data.json core nodes) -> (stooq symbol, yahoo symbol)
TICKERS: dict[str, tuple[str, str]] = {
    "CoreWeave": ("crwv.us", "CRWV"),
    "TeraWulf": ("wulf.us", "WULF"),
    "IREN": ("iren.us", "IREN"),
    "Applied Digital": ("apld.us", "APLD"),
    "Hut 8": ("hut.us", "HUT"),
    "MARA Holdings": ("mara.us", "MARA"),
    "CleanSpark": ("clsk.us", "CLSK"),
    "Galaxy Digital": ("glxy.us", "GLXY"),
    "Nebius": ("nbis.us", "NBIS"),
    "Core Scientific": ("corz.us", "CORZ"),
    "Cipher Mining": ("cifr.us", "CIFR"),
    "Bit Digital": ("btbt.us", "BTBT"),
    "NVIDIA": ("nvda.us", "NVDA"),
    "Microsoft": ("msft.us", "MSFT"),
    "Meta": ("meta.us", "META"),
    "Morgan Stanley": ("ms.us", "MS"),
    "Blackstone": ("bx.us", "BX"),
    "Goldman Sachs": ("gs.us", "GS"),
    "Apollo / Athene": ("apo.us", "APO"),
}

# node id -> exchange ticker, for the cluster issuers we count new 8-Ks for
# (polite request volume: 1 ticker-table fetch + 1 submissions fetch per issuer)
EDGAR_TICKERS: dict[str, str] = {
    "CoreWeave": "CRWV",
    "TeraWulf": "WULF",
    "IREN": "IREN",
    "Applied Digital": "APLD",
    "Hut 8": "HUT",
    "MARA Holdings": "MARA",
    "CleanSpark": "CLSK",
    "Galaxy Digital": "GLXY",
    "Nebius": "NBIS",
    "Core Scientific": "CORZ",
    "Cipher Mining": "CIFR",
    "Bit Digital": "BTBT",
}


def _get(url: str, timeout: float = 20.0, headers: dict[str, str] | None = None) -> str:
    req = urllib.request.Request(url, headers=headers or UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _stooq(sym: str) -> dict[str, Any] | None:
    end = datetime.now(UTC).date()
    start = end - timedelta(days=14)
    url = (
        f"https://stooq.com/q/d/l/?s={sym}"
        f"&d1={start.strftime('%Y%m%d')}&d2={end.strftime('%Y%m%d')}&i=d"
    )
    rows = [r for r in csv.DictReader(io.StringIO(_get(url))) if r.get("Close")]
    if len(rows) < 2:
        return None
    last, prev = rows[-1], rows[-2]
    return {
        "close": float(last["Close"]),
        "prev_close": float(prev["Close"]),
        "date": last.get("Date", ""),
    }


def _yahoo(sym: str) -> dict[str, Any] | None:
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{urllib.parse.quote(sym)}?range=5d&interval=1d"
    )
    data = json.loads(_get(url))
    result = (data.get("chart", {}).get("result") or [None])[0]
    if not result:
        return None
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    closes = [c for c in quote.get("close", []) if c is not None]
    if len(closes) < 2:
        return None
    ts = result.get("timestamp") or []
    date = datetime.fromtimestamp(ts[-1], tz=UTC).date().isoformat() if ts else ""
    return {"close": float(closes[-1]), "prev_close": float(closes[-2]), "date": date}


def _quotes() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for node_id, (stooq_sym, yahoo_sym) in TICKERS.items():
        quote = None
        for fetch, sym in ((_stooq, stooq_sym), (_yahoo, yahoo_sym)):
            try:
                quote = fetch(sym)
            except Exception:
                quote = None
            if quote:
                break
        if quote and quote["prev_close"]:
            quote["sym"] = yahoo_sym
            chg = (quote["close"] - quote["prev_close"]) / quote["prev_close"] * 100.0
            quote["chg_pct"] = round(chg, 2)
            out[node_id] = quote
        time.sleep(0.25)
    return out


def _edgar_ciks() -> dict[str, str]:
    """Resolve ticker -> zero-padded CIK from SEC's own ticker table (nothing hardcoded)."""
    table = json.loads(_get("https://www.sec.gov/files/company_tickers.json", headers=SEC_UA))
    by_ticker = {row["ticker"].upper(): int(row["cik_str"]) for row in table.values()}
    return {t: f"{by_ticker[t]:010d}" for t in EDGAR_TICKERS.values() if t in by_ticker}


def _edgar_counts() -> dict[str, dict[str, int]]:
    cutoff = (datetime.now(UTC).date() - timedelta(days=7)).isoformat()
    out: dict[str, dict[str, int]] = {}
    try:
        ciks = _edgar_ciks()
    except Exception:
        return out  # SEC unreachable from this network; overlay degrades to quotes-only
    for node_id, ticker in EDGAR_TICKERS.items():
        cik = ciks.get(ticker)
        if not cik:
            continue
        try:
            recent = json.loads(
                _get(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=SEC_UA)
            )["filings"]["recent"]
            count = sum(
                1
                for form, fdate in zip(recent["form"], recent["filingDate"], strict=False)
                if form.startswith("8-K") and fdate >= cutoff
            )
            out[node_id] = {"new_8k_7d": count}
        except Exception:
            pass  # missing counts are simply omitted
        time.sleep(0.35)
    return out


def main() -> int:
    quotes = _quotes()
    edgar = _edgar_counts()
    if not quotes and not edgar:
        print("live overlay: every source failed; leaving existing live.json untouched")
        return 0
    payload = {
        "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "quotes": quotes,
        "edgar": edgar,
    }
    OUT.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(quotes)} quotes, {len(edgar)} filing counts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
