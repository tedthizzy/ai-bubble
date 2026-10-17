#!/usr/bin/env python
"""Refresh viz/live.json -- the hourly market/filings overlay for the public viz.

Keyless public sources only (safe to run from GitHub Actions on a schedule):
- Stooq daily-history CSV for last/previous close per public ticker in the graph
  (Yahoo chart API as a per-ticker fallback)
- SEC EDGAR submissions API for new 8-K counts (trailing 7 days) per cluster issuer;
  CIKs are resolved at runtime from SEC's own company_tickers.json (nothing hardcoded)
- FRED CSV endpoint (keyless) for the credit dial: HY OAS, CCC OAS, 5y UST
- Listed-BDC closes vs hand-carded reported quarterly NAVs (the marginal-buyer
  discount series) and hand-carded cluster new-issue prints
  (analysis/issuance_cards.json) -> auto-evaluation of the pre-registered thesis
  signals defined in analysis/preregistered_signals.md

The adjudicated forensic numbers in viz/graph_data.json do NOT change here;
this overlay only adds freshness (prices, day moves, new filings) on top of the
evidence-gated verdicts. If every source fails, the existing live.json is left
untouched so the page never shows a falsely-advanced timestamp.
"""

from __future__ import annotations

import csv
import io
import json
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bubble.calendar_engine import calendar_payload  # noqa: E402
from bubble.market_signals import (  # noqa: E402
    BDC_CONTROL,
    BDC_EXPOSED,
    evaluate_signals,
)
from bubble.overlay_history import build_history_record, merge_history  # noqa: E402
from bubble.verdict_tree import realization_forecast  # noqa: E402

OUT = ROOT / "viz" / "live.json"
HISTORY = ROOT / "viz" / "history.jsonl"
CALENDAR = ROOT / "viz" / "calendar.json"
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

# Adjacency-extension tickers (analysis/spacex_adjacency.md) -- NOT cluster nodes; quoted
# into a separate live.json block so nothing conflates them with the adjudicated map.
ADJACENT_TICKERS: dict[str, tuple[str, str]] = {
    "SpaceX": ("spcx.us", "SPCX"),  # listed 2026-06-12 (xAI merged in 2026-02)
    "Alphabet": ("googl.us", "GOOGL"),  # ~5% SpaceX holder AND $920M/mo compute customer
}

# FRED daily series (keyless CSV endpoint) -- the systemic leg of the marginal-buyer dial
FRED_SERIES: dict[str, str] = {
    "hy_oas": "BAMLH0A0HYM2",  # ICE BofA US High Yield OAS, %
    "ccc_oas": "BAMLH0A3HYC",  # ICE BofA CCC & Lower OAS, %
    "bb_oas": "BAMLH0A1HYBB",  # ICE BofA BB OAS, % -- S2' quality-end control (amendment A2)
    "ust5y": "DGS5",  # 5-Year Treasury constant maturity, %
}

# Listed-BDC closes vs last REPORTED quarterly NAV. NAVs are hand-carded each quarter
# from the issuers' Q results (re-carding protocol: analysis/preregistered_signals.md).
# Discount = 1 - close/NAV. Set membership for the S3' differential (exposed vs non-AI
# control vs context-only) is carded evidence in analysis/bdc_exposure_cards.md and
# registered in src/bubble/market_signals.py -- thresholds change THERE, via the
# amendment log, never here.
BDC_TICKERS: dict[str, tuple[str, str]] = {
    "OBDC": ("obdc.us", "OBDC"),  # context: AI-DC lending sits at the manager, not this fund
    "ARCC": ("arcc.us", "ARCC"),  # exposed (weak): ~0.2% Vantage DC position
    "BXSL": ("bxsl.us", "BXSL"),  # exposed: Firmus GPU-cloud commitment
    "FSK": ("fsk.us", "FSK"),  # context: discount dominated by legacy book + class action
    "MAIN": ("main.us", "MAIN"),  # control (premium-regime outlier; median absorbs it)
    "GBDC": ("gbdc.us", "GBDC"),  # control: ~2% of portfolio AI-disruption-flagged, no DC lending
    "TSLX": ("tslx.us", "TSLX"),  # control: no AI/DC positions found
    "PSEC": ("psec.us", "PSEC"),  # control (idiosyncratic-discount outlier; median absorbs it)
}
BDC_NAV: dict[str, tuple[float, str]] = {
    "OBDC": (14.41, "2026-03-31"),
    "ARCC": (19.59, "2026-03-31"),
    "BXSL": (26.26, "2026-03-31"),
    "FSK": (18.83, "2026-03-31"),
    "MAIN": (33.46, "2026-03-31"),
    "GBDC": (14.35, "2026-03-31"),
    "TSLX": (16.24, "2026-03-31"),
    "PSEC": (6.05, "2026-03-31"),
}


def _reported_bdc_nav() -> dict[str, tuple[float, str, str]]:
    """Use the latest source-carded quarterly NAV snapshot for every BDC mark."""
    snapshots = sorted((ROOT / "analysis").glob("bdc_nav_????-??-??.json"))
    if not snapshots:
        return {ticker: (nav, period, "") for ticker, (nav, period) in BDC_NAV.items()}
    payload = json.loads(snapshots[-1].read_text())
    rows = payload["bdc"]
    if set(rows) != set(BDC_TICKERS):
        raise ValueError(f"Incomplete BDC NAV snapshot: {snapshots[-1]}")
    navs: dict[str, tuple[float, str, str]] = {}
    for ticker, row in rows.items():
        nav = float(row["nav_usd_per_share"])
        period = str(row["nav_asof"])
        source = str(row["source_uri"])
        if nav <= 0 or not source.startswith("https://") or period > payload["as_of"]:
            raise ValueError(f"Invalid {ticker} NAV in {snapshots[-1]}")
        navs[ticker] = (nav, period, source)
    return navs


def _get(url: str, timeout: float = 20.0, headers: dict[str, str] | None = None) -> str:
    req = urllib.request.Request(url, headers=headers or UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return str(resp.read().decode("utf-8", errors="replace"))


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


def _fetch_quote(stooq_sym: str, yahoo_sym: str) -> dict[str, Any] | None:
    for fetch, sym in ((_stooq, stooq_sym), (_yahoo, yahoo_sym)):
        try:
            quote = fetch(sym)
        except Exception:
            quote = None
        if quote:
            return quote
    return None


def _quotes_for(tickers: dict[str, tuple[str, str]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for node_id, (stooq_sym, yahoo_sym) in tickers.items():
        quote = _fetch_quote(stooq_sym, yahoo_sym)
        if quote and quote["prev_close"]:
            quote["sym"] = yahoo_sym
            chg = (quote["close"] - quote["prev_close"]) / quote["prev_close"] * 100.0
            quote["chg_pct"] = round(chg, 2)
            out[node_id] = quote
        time.sleep(0.25)
    return out


def _quotes() -> dict[str, dict[str, Any]]:
    return _quotes_for(TICKERS)


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


def _fred(series_id: str) -> dict[str, Any] | None:
    """Latest + YTD change of a FRED daily series (keyless CSV endpoint).

    The request is bounded to the year-to-date window via `cosd` -- unbounded pulls of
    long series (e.g. DGS5, daily since 1962) time out server-side.
    """
    start = f"{datetime.now(UTC).year}-01-01"
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start}"
    rows = list(csv.reader(io.StringIO(_get(url))))
    vals = [(r[0], float(r[1])) for r in rows[1:] if len(r) >= 2 and r[1] not in (".", "")]
    if not vals:
        return None
    last_date, last = vals[-1]
    return {"value": last, "date": last_date, "ytd_chg": round(last - vals[0][1], 2)}


def _credit() -> dict[str, Any]:
    """HY/CCC OAS + 5y UST -- is the credit market pricing ANY of the measured fragility?"""
    out: dict[str, Any] = {}
    for key, sid in FRED_SERIES.items():
        try:
            point = _fred(sid)
        except Exception:
            point = None
        if point:
            out[key] = point
        time.sleep(0.2)
    if "hy_oas" in out and "ccc_oas" in out:
        out["ccc_minus_hy_pp"] = round(out["ccc_oas"]["value"] - out["hy_oas"]["value"], 2)
    return out


def _bdc() -> dict[str, dict[str, Any]]:
    """Listed BDC closes vs last reported quarterly NAV -> live discount series.

    role: 'exposed' (carded asset-side AI/DC lending), 'control' (non-AI basket for the
    S3' differential), 'context' (quoted for continuity; in neither signal set).
    """
    out: dict[str, dict[str, Any]] = {}
    reported_nav = _reported_bdc_nav()
    for sym, (stooq_sym, yahoo_sym) in BDC_TICKERS.items():
        quote = _fetch_quote(stooq_sym, yahoo_sym)
        nav, nav_asof, nav_source_uri = reported_nav[sym]
        if quote and quote.get("close"):
            role = (
                "exposed" if sym in BDC_EXPOSED else "control" if sym in BDC_CONTROL else "context"
            )
            out[sym] = {
                "close": quote["close"],
                "date": quote.get("date", ""),
                "nav": nav,
                "nav_asof": nav_asof,
                "nav_source_uri": nav_source_uri,
                "discount_pct": round((1.0 - quote["close"] / nav) * 100.0, 1),
                "role": role,
            }
        time.sleep(0.25)
    return out


def _issuance_cards() -> list[dict[str, Any]]:
    """All hand-carded cluster prints (S1b scans every card's status, not just the latest)."""
    path = ROOT / "analysis" / "issuance_cards.json"
    try:
        deals = json.loads(path.read_text())["deals"]
    except Exception:
        return []
    return deals if isinstance(deals, list) else []


def _issuance_latest(deals: list[dict[str, Any]], credit: dict[str, Any]) -> dict[str, Any] | None:
    """Most recent completed cluster print, + registered coupon spread if available."""
    priced = [deal for deal in deals if deal.get("status", "priced") == "priced"]
    if not priced:
        return None
    latest = max(priced, key=lambda d: d.get("date", ""))
    ust = (credit.get("ust5y") or {}).get("value")
    if ust is not None and latest.get("coupon_pct") is not None:
        latest = {**latest, "spread_vs_5y_bp": round((latest["coupon_pct"] - ust) * 100)}
    return latest


def _demand_baskets() -> list[dict[str, Any]]:
    """Carded S4 demand-trajectory baskets (analysis/demand_trajectory.json)."""
    path = ROOT / "analysis" / "demand_trajectory.json"
    try:
        baskets = json.loads(path.read_text())["baskets"]
    except Exception:
        return []
    return baskets if isinstance(baskets, list) else []


def _banner_svg(
    quotes: dict[str, dict[str, Any]],
    credit: dict[str, Any] | None = None,
    signals: list[dict[str, Any]] | None = None,
    latest_deal: dict[str, Any] | None = None,
) -> str:
    """Render the GitHub banner with the same font and dates as the explorer."""
    graph = json.loads((ROOT / "viz/graph_data.json").read_text())
    meta, field = graph.get("meta", {}), graph.get("field", {})
    report = str(meta.get("as_of") or meta.get("generated_from") or "Unavailable")
    match = re.search(r"(20\d{2})(\d{2})(\d{2})", report)
    if match:
        report = "-".join(match.groups())
    dates = sorted({q["date"] for q in quotes.values() if q.get("date")})
    market = dates[-1] if dates else "Unavailable"
    credit_bits = []
    for name, label in (("hy_oas", "HY"), ("ccc_oas", "CCC")):
        point = (credit or {}).get(name, {})
        if point.get("value") is not None:
            credit_bits.append(f"{label} {point['value']:.2f}% ({point.get('date', 'unknown date')})")
    movers = sorted(quotes.values(), key=lambda q: -abs(q.get("chg_pct", 0)))[:4]
    rows = [
        f"Report {report} / ${(meta.get('committed_core_usd', 0)/1e9):.1f}B core debt / {field.get('entities', 0):,} extracted entities",
        f"Market {market}" + (" / " + " / ".join(credit_bits) if credit_bits else ""),
        " / ".join(f"{q.get('sym', '')} {q.get('chg_pct', 0):+.1f}%" for q in movers),
        "Report judgments retain their evidence date. Market observations have separate dates.",
    ]
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="182" viewBox="0 0 1000 182">\n'
        '<rect x="1" y="1" width="998" height="180" rx="10" fill="#0c1420" stroke="#354252"/>\n'
        '<text x="24" y="32" font-family="Arial,sans-serif" font-size="18" font-weight="700" fill="#e6edf3">Bubble</text>\n'
        + "".join(
            f'<text x="24" y="{59+i*31}" font-family="Arial,sans-serif" font-size="14" fill="#adb8c8">{escape(row)}</text>\n'
            for i, row in enumerate(rows)
        ) + "</svg>\n"
    )


def main(*, saved_edgar: dict[str, dict[str, int]] | None = None) -> int:
    quotes = _quotes()
    edgar = _edgar_counts() if saved_edgar is None else saved_edgar
    credit = _credit()
    bdc = _bdc()
    adjacent = _quotes_for(ADJACENT_TICKERS)
    deals = _issuance_cards()
    latest_deal = _issuance_latest(deals, credit)
    if not quotes and not edgar and not credit and not bdc:
        print("live overlay: every source failed; leaving existing live.json untouched")
        return 1
    signals = evaluate_signals(
        credit, bdc, deals, latest_deal, _demand_baskets(), datetime.now(UTC).date()
    )
    signal_status = {s["id"]: s["status"] for s in signals if "id" in s and "status" in s}
    payload = {
        "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "quotes": quotes,
        "edgar": edgar,
        "credit": credit,
        "bdc": bdc,
        "adjacent": adjacent,
        "issuance_latest": latest_deal,
        "signals": signals,
        "verdict_shadow": realization_forecast(signal_status),
        "source_status": {
            name: {
                "received": len(set(observed) & set(expected)),
                "expected": len(expected),
                "missing": sorted(set(expected) - set(observed)),
            }
            for name, observed, expected in (
                ("quotes", quotes, TICKERS),
                ("edgar", edgar, EDGAR_TICKERS),
                ("credit", credit, FRED_SERIES),
                ("bdc", bdc, BDC_TICKERS),
                ("adjacent", adjacent, ADJACENT_TICKERS),
            )
        },
    }
    snapshot = ROOT / ".codex" / "overlay-snapshots" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    snapshot.mkdir(parents=True, exist_ok=False)
    for path in (OUT, ROOT / "viz/banner.svg", HISTORY, CALENDAR):
        if path.exists():
            shutil.copy2(path, snapshot / path.name)
    OUT.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    (ROOT / "viz" / "banner.svg").write_text(_banner_svg(quotes, credit, signals, latest_deal))
    _persist_history(payload)
    CALENDAR.write_text(
        json.dumps(calendar_payload(datetime.now(UTC).date()), indent=1, sort_keys=True) + "\n"
    )
    print(
        f"wrote {OUT.relative_to(ROOT)} + viz/banner.svg: {len(quotes)} quotes, "
        f"{len(edgar)} filing counts, {len(credit)} credit series, {len(bdc)} BDC marks, "
        f"{len(adjacent)} adjacent"
    )
    return 0


def _persist_history(payload: dict[str, Any]) -> None:
    """Append-or-replace today's compact record in viz/history.jsonl (one row per UTC day)."""
    existing: list[dict[str, Any]] = []
    if HISTORY.exists():
        for raw_line in HISTORY.read_text().splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                existing.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    merged = merge_history(existing, build_history_record(payload))
    HISTORY.write_text("\n".join(json.dumps(r, sort_keys=True) for r in merged) + "\n")


if __name__ == "__main__":
    sys.exit(main())
