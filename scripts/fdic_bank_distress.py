"""Bank-distress scan over ALL FDIC institutions (off-EDGAR acquisition, free API, no agents).

Closes the explicitly-punted financials gap: banks break the EBITDA/interest model, so this
uses the PROPER bank-distress metrics from the FDIC public API (free) — risk-based capital
ratio, return on assets, nonperforming-asset ratio, equity/assets. Covers the ~4,000+ US
banks the corporate-leverage scan structurally could not read. Real new public-record
ingestion (FDIC call-report data), pure HTTP + local.

Output: analysis/fdic_bank_distress.{json,md}
"""

from __future__ import annotations

# ruff: noqa: PERF401
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "analysis" / "fdic_bank_distress.json"
OUT_MD = ROOT / "analysis" / "fdic_bank_distress.md"
UA = "ai-bubble research ted1508@gmail.com"
BASE = "https://banks.data.fdic.gov/api/financials"
FIELDS = "CERT,NAME,STNAME,REPDTE,ASSET,EQ,NETINC,RBCRWAJ,NPERFV,ROA"

# Pre-registered bank-distress thresholds (bank-specific, NOT corporate EBITDA/interest):
WELL_CAP = 10.0  # total risk-based capital ratio % — below = not well-capitalized
UNDER_CAP = 8.0  # below = undercapitalized (PCA territory)
HIGH_NPA = 4.0  # nonperforming assets % of assets
THIN_EQ = 5.0  # equity / assets %


def fetch_page(repdte: str, offset: int, limit: int = 5000) -> list[dict]:
    qs = urllib.parse.urlencode(
        {
            "filters": f"REPDTE:{repdte}",
            "fields": FIELDS,
            "limit": limit,
            "offset": offset,
            "format": "json",
        }
    )
    req = urllib.request.Request(f"{BASE}?{qs}", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return [row["data"] for row in json.load(r).get("data", [])]
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return []


def distress(b: dict) -> tuple[bool, list[str]]:
    flags = []
    cap = b.get("RBCRWAJ")
    roa = b.get("ROA")
    npa = b.get("NPERFV")
    asset, eq = b.get("ASSET") or 0, b.get("EQ") or 0
    eq_ratio = (eq / asset * 100) if asset else None
    # exclude non-reporting foreign-bank BRANCHES (capital sits at the parent → all-zero metrics):
    if (cap in (0, None)) and (roa in (0, None)) and (eq_ratio is None or eq_ratio < 0.1):
        return False, []
    if cap is not None and 0 < cap < UNDER_CAP:
        flags.append(f"undercapitalized (RBC {cap:.1f}%)")
    elif cap is not None and 0 < cap < WELL_CAP:
        flags.append(f"not well-capitalized (RBC {cap:.1f}%)")
    if roa is not None and roa < 0:
        flags.append(f"losing money (ROA {roa:.2f}%)")
    if npa is not None and npa > HIGH_NPA:
        flags.append(f"high nonperforming ({npa:.1f}%)")
    if eq_ratio is not None and eq_ratio < THIN_EQ:
        flags.append(f"thin equity ({eq_ratio:.1f}% of assets)")
    return bool(flags), flags


def main() -> None:
    # find the latest available quarter (try recent quarter-ends, descending)
    repdte = ""
    for cand in ("20260331", "20251231", "20250930"):
        if fetch_page(cand, 0, 1):
            repdte = cand
            break
    if not repdte:
        print("no FDIC data reachable")
        return
    print(f"FDIC call-report quarter: {repdte}")

    banks, offset = [], 0
    while True:
        page = fetch_page(repdte, offset)
        if not page:
            break
        banks.extend(page)
        offset += len(page)
        time.sleep(0.15)
        if len(page) < 5000:
            break
        print(f"  pulled {len(banks)}")
    print(f"total banks: {len(banks)}")

    flagged = []
    for b in banks:
        d, flags = distress(b)
        if d:
            flagged.append(
                {
                    "name": b.get("NAME"),
                    "state": b.get("STNAME"),
                    "cert": b.get("CERT"),
                    "assets_b": round((b.get("ASSET") or 0) / 1e6, 2),
                    "rbc_ratio": b.get("RBCRWAJ"),
                    "roa": b.get("ROA"),
                    "npa_pct": b.get("NPERFV"),
                    "flags": flags,
                }
            )
    flagged.sort(
        key=lambda x: (x["rbc_ratio"] if x["rbc_ratio"] is not None else 99, -(x["assets_b"] or 0))
    )
    sev = Counter()
    for x in flagged:
        if any("undercapitalized" in f for f in x["flags"]):
            sev["undercapitalized"] += 1
        elif any("not well-cap" in f for f in x["flags"]):
            sev["not_well_capitalized"] += 1
        else:
            sev["other_distress"] += 1
    out = {
        "repdte": repdte,
        "banks_scanned": len(banks),
        "flagged": len(flagged),
        "severity": dict(sev),
        "top_flagged": flagged[:120],
    }
    OUT_JSON.write_text(json.dumps(out, indent=2))
    write_md(out)
    print(
        f"wrote {OUT_JSON.relative_to(ROOT)} | scanned {len(banks)} | flagged {len(flagged)} | {dict(sev)}"
    )


BANNER = (ROOT / "analysis" / "economy_wide_fragility_map.md").read_text().split("\n")[2]


def write_md(out: dict) -> None:
    L = []
    L.append("# Bank-distress scan — all FDIC institutions (off-EDGAR, proper bank model)")
    L.append("")
    L.append(BANNER)
    L.append("")
    L.append(
        f"Closes the financials gap the corporate-leverage scan couldn't read. **All "
        f"{out['banks_scanned']:,} FDIC banks** ({out['repdte'][:4]}-Q{int(out['repdte'][4:6]) // 3}) "
        f"scored on the *bank-specific* distress model — risk-based capital, ROA, "
        f"nonperforming, equity/assets. **{out['flagged']} flagged** ({out['severity']}). "
        f"Real new public-record ingestion via the free FDIC API. "
        f"Machine-readable: [fdic_bank_distress.json](fdic_bank_distress.json)."
    )
    L.append("")
    L.append("## Most distressed banks (by risk-based capital ratio)")
    L.append("")
    L.append("| bank | state | assets $B | RBC % | ROA % | NPA % | flags |")
    L.append("|---|---|---:|---:|---:|---:|---|")
    for x in out["top_flagged"][:50]:
        L.append(
            f"| {(x['name'] or '')[:28]} | {(x['state'] or '')[:10]} | {x['assets_b']} | "
            f"{x['rbc_ratio']} | {x['roa']} | {x['npa_pct']} | {'; '.join(x['flags'])[:60]} |"
        )
    L.append("")
    L.append(
        "*Bank distress ≠ corporate leverage: a bank is fragile via capital adequacy "
        "(risk-based capital < 10% = not well-capitalized; < 8% = PCA), losses (ROA < 0), "
        "and asset quality (nonperforming > 4%) — not EBITDA/interest. This is the breadth "
        "layer for the ~4,000-bank universe the corporate scan excluded.*"
    )
    OUT_MD.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
