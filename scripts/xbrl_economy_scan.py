"""Economy-wide financials-based fragility scan over ALL public filers (no LLM agents).

Breaks the deal-corpus dependency: instead of scoring only the ~2,007 entities that appear
in our EDGAR deal extraction, this pulls XBRL financial facts for EVERY SEC filer
(~10,365) and computes the ratios that actually matter — net-debt/EBITDA (leverage) and
EBITDA/interest (coverage). Being ratio-based, it is immune to the gross-notional size-bias
that polluted the deal-corpus scan. Pure HTTP to data.sec.gov + local compute — uses ZERO
LLM agents, so it runs fine under an LLM rate-limit cooldown.

In-memory fetch (companyfacts discarded after parse); writes only the ratio table.
Resumable: caches results every 200 filers.

Output: analysis/economy_xbrl_fragility.{json,md}
"""

from __future__ import annotations

# ruff: noqa: PERF401, RUF001
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from xbrl_net_leverage import (  # noqa: E402
    CASH_TAGS,
    INT_TAGS,
    ebitda,
    fetch_json,
    latest_annual,
    latest_instant,
    total_debt,
)

SEC_REF = ROOT / "data" / "entity_universe" / "raw" / "sec_company_tickers_exchange.json"
OUT_JSON = ROOT / "analysis" / "economy_xbrl_fragility.json"
OUT_MD = ROOT / "analysis" / "economy_xbrl_fragility.md"
CACHE = ROOT / "data" / "entity_universe" / "xbrl_economy_cache.json"
RATE_S = 0.12


def classify(net_debt, eb, cov):
    if eb is not None and eb <= 0:
        return "negative_ebitda"
    if cov is None or eb is None:
        return "insufficient_data"
    if cov < 1.5:
        return "distressed"
    nd_e = (net_debt / eb) if (net_debt is not None and eb > 0) else None
    if nd_e is not None and nd_e >= 5:
        return "refi_risk"
    return "manageable"


def load_universe() -> list[dict]:
    d = json.loads(SEC_REF.read_text())
    fields = d["fields"]
    ci, ti, ni = fields.index("cik"), fields.index("ticker"), fields.index("name")
    out = []
    seen = set()
    for row in d["data"]:
        cik = str(row[ci]).zfill(10)
        if cik in seen:
            continue
        seen.add(cik)
        out.append({"cik": cik, "ticker": row[ti], "name": row[ni]})
    return out


def main() -> None:
    universe = load_universe()
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    print(f"economy XBRL scan: {len(universe)} filers; {len(cache)} cached")
    for i, ent in enumerate(universe, 1):
        cik = ent["cik"]
        if cik in cache:
            continue
        facts = fetch_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")
        time.sleep(RATE_S)
        if not facts:
            cache[cik] = {**ent, "status": "no_xbrl"}
        else:
            debt = total_debt(facts)
            cash = latest_instant(facts, CASH_TAGS)
            eb, _ = ebitda(facts)
            inte = latest_annual(facts, INT_TAGS)
            nd = (debt - (cash or 0)) if debt is not None else None
            cov = (eb / inte) if (eb is not None and inte and inte > 0) else None
            cache[cik] = {
                **ent,
                "status": "ok",
                "debt_b": round(debt / 1e9, 2) if debt is not None else None,
                "net_debt_b": round(nd / 1e9, 2) if nd is not None else None,
                "ebitda_b": round(eb / 1e9, 2) if eb is not None else None,
                "interest_b": round(inte / 1e9, 3) if inte is not None else None,
                "nd_ebitda": round(nd / eb, 1) if (nd is not None and eb and eb > 0) else None,
                "coverage": round(cov, 2) if cov is not None else None,
                "classification": classify(nd, eb, cov),
            }
        if i % 200 == 0:
            CACHE.write_text(json.dumps(cache))
            print(f"  {i}/{len(universe)} pulled")
    CACHE.write_text(json.dumps(cache))

    rows = [v for v in cache.values() if v.get("status") == "ok"]
    dist = Counter(r["classification"] for r in rows)
    distressed = sorted(
        [r for r in rows if r["classification"] == "distressed"],
        key=lambda r: r.get("coverage") if r.get("coverage") is not None else 9,
    )
    out = {
        "filers_scanned": len(cache),
        "with_xbrl": len(rows),
        "distribution": dict(dist),
        "distressed_count": len(distressed),
        "distressed": distressed[:200],
    }
    OUT_JSON.write_text(json.dumps(out, indent=2))
    write_md(out)
    print(f"done: {len(rows)} with XBRL; distribution {dict(dist)}")


BANNER = (ROOT / "analysis" / "economy_wide_fragility_map.md").read_text().split("\n")[2]


def write_md(out: dict) -> None:
    L = []
    L.append("# Economy-wide XBRL fragility — all public filers, ratio-based (size-bias-free)")
    L.append("")
    L.append(BANNER)
    L.append("")
    L.append(
        f"Financials-based scan over **{out['filers_scanned']} SEC filers** "
        f"({out['with_xbrl']} with usable XBRL), independent of the deal corpus and immune "
        f"to gross-notional size-bias (ratio-based: net-debt/EBITDA + EBITDA/interest). "
        f"Distribution: {out['distribution']}. **{out['distressed_count']} filers show "
        f"interest coverage < 1.5×** (the real distress line). "
        f"Machine-readable: [economy_xbrl_fragility.json](economy_xbrl_fragility.json)."
    )
    L.append("")
    L.append("## Most distressed by interest coverage (top 60)")
    L.append("")
    L.append("| entity | ticker | net debt $B | ND/EBITDA | int cov | EBITDA $B |")
    L.append("|---|---|---:|---:|---:|---:|")
    for r in out["distressed"][:60]:
        L.append(
            f"| {r['name'][:34]} | {r.get('ticker', '')} | {r.get('net_debt_b', '—')} | "
            f"{r.get('nd_ebitda', '—')} | {r.get('coverage', '—')} | {r.get('ebitda_b', '—')} |"
        )
    L.append("")
    L.append(
        "*Single-period ratios from latest XBRL. Financials/REIT/BDC leverage is not "
        "comparable to corporate (deposits/portfolio debt) — read those by sector. "
        "`distressed` = EBITDA/interest < 1.5×; `negative_ebitda` is tracked separately. "
        "This is the breadth layer; the deal-corpus signature scan + deep agents are the depth layer.*"
    )
    OUT_MD.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
