"""Refinement — XBRL net-debt / coverage join for the large-levered layer.

The scan flags on GROSS notional, which conflates "big balance sheet" with "fragile".
This pulls each name's XBRL financial facts (data.sec.gov, orchestrator, declared UA) and
computes the ratios that actually separate real distress from refi-risk-that-may-not-
crystallize: net-debt / EBITDA (leverage) and EBITDA / interest (coverage). In-memory
fetch; only the ratio table is written.

Classification (pre-registered):
  distressed   — interest coverage < 1.5x  (can't comfortably service current interest)
  refi_risk    — coverage >= 1.5x but net-debt/EBITDA >= 5x (services it, but levered into the wall)
  manageable   — coverage >= 1.5x and net-debt/EBITDA < 5x
  scan_oversized — XBRL net debt is < 1/3 of the scan's gross-notional flag (the flag was a size/extraction artifact)

Output: analysis/large_levered_net_leverage.{json,md}
"""

from __future__ import annotations

# ruff: noqa: PERF401
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP_JSON = ROOT / "analysis" / "economy_wide_fragility_map.json"
TARGETS = ROOT / "analysis" / "phase3_targets.json"
OUT_JSON = ROOT / "analysis" / "large_levered_net_leverage.json"
OUT_MD = ROOT / "analysis" / "large_levered_net_leverage.md"

UA = "ai-bubble research ted1508@gmail.com"
RATE_S = 0.2
MIN_DEBT_FLAG = 5e9  # focus on the large-levered layer (scan gross debt >= $5B)

DEBT_TAGS = [
    "DebtLongtermAndShorttermCombinedAmount",
    "LongTermDebtAndCapitalLeaseObligations",
    "LongTermDebt",
]
DEBT_SPLIT = ("LongTermDebtNoncurrent", "LongTermDebtCurrent")
CASH_TAGS = [
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
]
OPINC_TAGS = ["OperatingIncomeLoss"]
DA_TAGS = [
    "DepreciationDepletionAndAmortization",
    "DepreciationAmortizationAndAccretionNet",
    "DepreciationAndAmortization",
]
INT_TAGS = ["InterestExpense", "InterestExpenseDebt", "InterestAndDebtExpense"]
NI_TAGS = ["NetIncomeLoss"]
TAX_TAGS = ["IncomeTaxExpenseBenefit"]


def fetch_json(url: str) -> dict | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.load(r)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def _units(facts: dict, tag: str) -> list[dict]:
    node = facts.get("facts", {}).get("us-gaap", {}).get(tag)
    if not node:
        return []
    units = node.get("units", {})
    return units.get("USD", [])


def latest_instant(facts: dict, tags: list[str]) -> float | None:
    for tag in tags:
        rows = [u for u in _units(facts, tag) if u.get("end") and "start" not in u]
        if rows:
            rows.sort(key=lambda u: u["end"])
            return float(rows[-1]["val"])
    return None


def latest_annual(facts: dict, tags: list[str]) -> float | None:
    """Most recent FY (≈365-day) value."""
    for tag in tags:
        rows = []
        for u in _units(facts, tag):
            s, e = u.get("start"), u.get("end")
            if not s or not e:
                continue
            # crude ~annual filter via fiscal-period tag or 10-K form
            if u.get("fp") == "FY" or u.get("form", "").startswith("10-K"):
                rows.append(u)
        if rows:
            rows.sort(key=lambda u: u["end"])
            return float(rows[-1]["val"])
    return None


def total_debt(facts: dict) -> float | None:
    d = latest_instant(facts, DEBT_TAGS)
    if d is not None:
        return d
    nc = latest_instant(facts, [DEBT_SPLIT[0]])
    c = latest_instant(facts, [DEBT_SPLIT[1]])
    if nc is not None or c is not None:
        return (nc or 0) + (c or 0)
    return None


def ebitda(facts: dict) -> tuple[float | None, str]:
    op = latest_annual(facts, OPINC_TAGS)
    da = latest_annual(facts, DA_TAGS)
    if op is not None and da is not None:
        return op + da, "opinc+da"
    # bottom-up fallback
    ni = latest_annual(facts, NI_TAGS)
    inte = latest_annual(facts, INT_TAGS)
    tax = latest_annual(facts, TAX_TAGS)
    if ni is not None and inte is not None and da is not None:
        return ni + inte + (tax or 0) + da, "ni+int+tax+da"
    return None, "unavailable"


def classify(net_debt: float | None, eb: float | None, cov: float | None,
             gross_flag: float) -> str:
    if net_debt is not None and net_debt < gross_flag / 3:
        return "scan_oversized"
    if cov is None or eb is None or eb <= 0:
        return "unknown_or_negative_ebitda" if eb is not None and eb <= 0 else "unknown"
    if cov < 1.5:
        return "distressed"
    if net_debt is not None and eb > 0 and (net_debt / eb) >= 5:
        return "refi_risk"
    return "manageable"


def main() -> None:
    data = json.loads(MAP_JSON.read_text())
    tdata = json.loads(TARGETS.read_text())
    cik_by_entity = {t["entity"]: (t.get("cik") or "") for t in tdata["targets"]}
    # large-levered layer: scan gross debt >= $5B, US filer (has CIK)
    names = {}
    for r in data["top_200"]:
        if r["debt_notional_usd"] >= MIN_DEBT_FLAG and (r.get("cik") or "").isdigit():
            names[r["entity"]] = r
    print(f"large-levered names with CIK: {len(names)}")

    results = []
    for ent, r in names.items():
        cik10 = r["cik"].zfill(10)
        facts = fetch_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json")
        time.sleep(RATE_S)
        if not facts:
            results.append({"entity": ent, "cik": cik10, "status": "no_xbrl"})
            continue
        debt = total_debt(facts)
        cash = latest_instant(facts, CASH_TAGS)
        eb, eb_method = ebitda(facts)
        inte = latest_annual(facts, INT_TAGS)
        net_debt = (debt - (cash or 0)) if debt is not None else None
        nd_ebitda = (net_debt / eb) if (net_debt is not None and eb and eb > 0) else None
        coverage = (eb / inte) if (eb is not None and inte and inte > 0) else None
        cls = classify(net_debt, eb, coverage, r["debt_notional_usd"])
        results.append({
            "entity": ent,
            "cik": cik10,
            "sector": r.get("sector", ""),
            "scan_gross_debt_b": round(r["debt_notional_usd"] / 1e9, 1),
            "xbrl_total_debt_b": round(debt / 1e9, 1) if debt is not None else None,
            "xbrl_net_debt_b": round(net_debt / 1e9, 1) if net_debt is not None else None,
            "ebitda_b": round(eb / 1e9, 2) if eb is not None else None,
            "ebitda_method": eb_method,
            "interest_b": round(inte / 1e9, 2) if inte is not None else None,
            "net_debt_to_ebitda": round(nd_ebitda, 1) if nd_ebitda is not None else None,
            "interest_coverage": round(coverage, 2) if coverage is not None else None,
            "classification": cls,
        })

    order = {"distressed": 0, "refi_risk": 1, "unknown_or_negative_ebitda": 2,
             "manageable": 3, "scan_oversized": 4, "unknown": 5, "no_xbrl": 6}
    results.sort(key=lambda x: (order.get(x.get("classification", "no_xbrl"), 9),
                                -(x.get("net_debt_to_ebitda") or 0)))
    from collections import Counter
    dist = Counter(x.get("classification", "no_xbrl") for x in results)
    out = {"checked": len(results), "distribution": dict(dist), "results": results}
    OUT_JSON.write_text(json.dumps(out, indent=2))
    write_md(out)
    print(f"wrote {OUT_JSON.relative_to(ROOT)} + {OUT_MD.relative_to(ROOT)}")
    print(f"  {dict(dist)}")


BANNER = (ROOT / "analysis" / "economy_wide_fragility_map.md").read_text().split("\n")[2]


def write_md(out: dict) -> None:
    L = []
    L.append("# Large-levered layer — XBRL net-debt / coverage (real distress vs refi risk)")
    L.append("")
    L.append(BANNER)
    L.append("")
    L.append(
        f"Converts the scan's GROSS-notional flags into true leverage + coverage for the "
        f"large-levered layer (scan gross debt ≥ $5B), so 'lots of debt' is separated from "
        f"'can't service it'. {out['checked']} names, XBRL from data.sec.gov. "
        f"Distribution: {out['distribution']}. "
        f"Machine-readable: [large_levered_net_leverage.json](large_levered_net_leverage.json)."
    )
    L.append("")
    L.append("| entity | sector | scan gross $B | XBRL net debt $B | ND/EBITDA | int cov | call |")
    L.append("|---|---|---:|---:|---:|---:|---|")
    for r in out["results"]:
        if r.get("status") == "no_xbrl":
            L.append(f"| {r['entity'][:30]} | | | | | | no XBRL |")
            continue
        L.append(
            f"| {r['entity'][:30]} | {r.get('sector','')[:18]} | {r.get('scan_gross_debt_b','')} | "
            f"{r.get('xbrl_net_debt_b','—')} | {r.get('net_debt_to_ebitda','—')} | "
            f"{r.get('interest_coverage','—')} | {r['classification']} |"
        )
    L.append("")
    L.append(
        "*EBITDA is built from XBRL (operating income + D&A, or bottom-up); most-recent FY. "
        "`scan_oversized` = XBRL net debt < ⅓ of the scan's gross flag (size/extraction artifact). "
        "`distressed` = interest coverage < 1.5×. `refi_risk` = serviced but ND/EBITDA ≥ 5×. "
        "Single-period ratios; financials/REIT/BDC leverage is not comparable to corporate "
        "(deposits/portfolio debt) — read those by sector, not on this axis.*"
    )
    OUT_MD.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
