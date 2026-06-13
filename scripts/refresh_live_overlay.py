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
import sys
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bubble.market_signals import (  # noqa: E402
    BDC_CONTROL,
    BDC_EXPOSED,
    evaluate_signals,
)
from bubble.calendar_engine import calendar_payload  # noqa: E402
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
    for sym, (stooq_sym, yahoo_sym) in BDC_TICKERS.items():
        quote = _fetch_quote(stooq_sym, yahoo_sym)
        nav, nav_asof = BDC_NAV[sym]
        if quote and quote.get("close"):
            role = (
                "exposed" if sym in BDC_EXPOSED else "control" if sym in BDC_CONTROL else "context"
            )
            out[sym] = {
                "close": quote["close"],
                "date": quote.get("date", ""),
                "nav": nav,
                "nav_asof": nav_asof,
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
    """Most recent carded cluster print, + spread vs 5y UST if available."""
    if not deals:
        return None
    latest = max(deals, key=lambda d: d.get("date", ""))
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
    """Self-rendering status banner, embedded in the GitHub profile README via Pages."""
    meta: dict[str, Any] = {}
    field: dict[str, Any] = {}
    try:
        graph = json.loads((ROOT / "viz" / "graph_data.json").read_text())
        meta = graph.get("meta") or {}
        field = graph.get("field") or {}
    except Exception:
        pass
    core_b = (meta.get("committed_core_usd") or 0) / 1e9
    headline_t = (meta.get("original_inflated_basis_usd") or 0) / 1e12
    cut = meta.get("over_count_removed_pct") or 0
    ents = field.get("entities") or 0
    deals = field.get("deals") or 0
    stamp = datetime.now(UTC).strftime("%H:%M UTC · %d %b %Y")
    movers = sorted(
        ((nid, q) for nid, q in quotes.items() if isinstance(q.get("chg_pct"), int | float)),
        key=lambda kv: -abs(kv[1]["chg_pct"]),
    )[:4]
    tspans = "".join(
        f'<tspan fill="{"#3fb950" if q["chg_pct"] >= 0 else "#f85149"}">'
        f"{q['sym']} {'+' if q['chg_pct'] >= 0 else ''}{q['chg_pct']:.1f}%</tspan>"
        f'<tspan fill="#39414c">&#160;&#160;&#160;</tspan>'
        for _nid, q in movers
    )
    font = "ui-sans-serif,system-ui,sans-serif"
    dial_bits: list[str] = []
    hy = ((credit or {}).get("hy_oas") or {}).get("value")
    ccc = (credit or {}).get("ccc_oas") or {}
    if hy is not None:
        dial_bits.append(f"HY {hy:.2f}%")
    if ccc.get("value") is not None:
        ytd = ccc.get("ytd_chg")
        suffix = f" ({'+' if ytd >= 0 else ''}{round(ytd * 100)}bp YTD)" if ytd is not None else ""
        dial_bits.append(f"CCC {ccc['value']:.2f}%{suffix}")
    s3 = next((s for s in (signals or []) if s.get("id") == "S3_bdc_discount_differential"), None)
    if s3 and s3.get("differential_pp") is not None:
        dial_bits.append(f"AI-BDC {s3['differential_pp']:+.1f}pp vs ctl")
    if latest_deal and latest_deal.get("spread_vs_5y_bp") is not None:
        dial_bits.append(f"latest print +{latest_deal['spread_vs_5y_bp']}bp")
    dial = (
        f' <text x="24" y="106" font-family="{font}" font-size="12" fill="#9aa7b4">'
        f'<tspan fill="#5d6a77">credit dial</tspan>  {" · ".join(dial_bits)}</text>\n'
        if dial_bits
        else ""
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="860" height="126" viewBox="0 0 860 126">\n'
        ' <rect x="1" y="1" width="858" height="124" rx="12" fill="#0c1420" stroke="#223344"/>\n'
        f' <text x="24" y="32" font-family="{font}" font-size="15" font-weight="700" fill="#e6edf3">'
        f'AI BUBBLE<tspan fill="#5d6a77" font-weight="400"> · evidence-gated map · '
        f"{ents:,} entities · {deals:,} deals</tspan></text>\n"
        f' <text x="24" y="58" font-family="{font}" font-size="12.5" fill="#9aa7b4">'
        f'verified core <tspan fill="#ffd166" font-weight="600">${core_b:.1f}B</tspan> '
        f'vs headline claimed <tspan fill="#ffd166" font-weight="600">${headline_t:.2f}T</tspan> '
        f'(~{cut:.0f}% over-count) · bubble <tspan fill="#ffd166">{meta.get("core_confidence")}</tspan> '
        f'· ecosystem <tspan fill="#f0883e">{meta.get("ecosystem_confidence")}</tspan> · not final</text>\n'
        f' <text x="24" y="84" font-family="{font}" font-size="13" font-weight="600">{tspans}</text>\n'
        f"{dial}"
        f' <text x="836" y="106" text-anchor="end" font-family="{font}" font-size="11" fill="#6b7785">'
        f"live · {stamp}</text>\n"
        "</svg>\n"
    )


def main() -> int:
    quotes = _quotes()
    edgar = _edgar_counts()
    credit = _credit()
    bdc = _bdc()
    adjacent = _quotes_for(ADJACENT_TICKERS)
    deals = _issuance_cards()
    latest_deal = _issuance_latest(deals, credit)
    if not quotes and not edgar and not credit and not bdc:
        print("live overlay: every source failed; leaving existing live.json untouched")
        return 0
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
    }
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
        for line in HISTORY.read_text().splitlines():
            line = line.strip()
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
