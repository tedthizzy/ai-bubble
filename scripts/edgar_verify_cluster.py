#!/usr/bin/env python
"""Filing-tier verification sweep over the whole financed-compute cluster + adjacents.

Reads the latest 10-K and 10-Q for each entity directly from SEC EDGAR (reachable from the
local research box; only the CI runner IP is blocked) and extracts the load-bearing facts at
FILING tier: customer concentration, RPO/backlog + take-or-pay structure, the debt stack
(notes/DDTLs with rates and maturities), going-concern / covenant / liquidity language, and
profitability. Writes analysis/cluster_filing_facts.json (full extracted snippets, auditable)
and prints a compact summary so the heavy filings never enter the synthesis context.

Polite: one SEC request at a time with a >=0.5s gap (well under the 10 req/s fair-access lane)
and a compliant User-Agent. No User-Agent spoofing. Re-running re-pulls the then-latest filings.
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from html import unescape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "analysis" / "cluster_filing_facts.json"
UA = {"User-Agent": "ai-bubble research ted1508@gmail.com"}

# Tickers grouped by role; CIKs resolved at runtime from SEC's own ticker table.
CLUSTER = ["CRWV", "WULF", "IREN", "APLD", "HUT", "MARA", "CLSK", "GLXY", "NBIS", "CORZ", "CIFR", "BTBT"]
BDC = ["BXSL", "ARCC"]
ROLES = {**{t: "cluster_issuer" for t in CLUSTER}, **{t: "bdc" for t in BDC}}

# Targeted extraction: label -> regex; we keep short windows around the first matches.
TARGETS = {
    "customer_concentration": r"(?:top customer|single customer|largest customer|% of (?:our )?(?:total )?revenue|customer concentration)",
    "rpo_backlog": r"(?:remaining performance obligation|\bRPO\b|committed contracts|contracted revenue|revenue backlog)",
    "take_or_pay": r"take-?or-?pay",
    "going_concern": r"(?:going concern|substantial doubt)",
    "covenant_liquidity": r"(?:financial covenant|covenant (?:compliance|default)|event of default|sufficient to fund|ability to continue|liquidity to)",
    "net_loss": r"net (?:loss|income) (?:of|attributable)",
    "debt_instrument": r"(?:\d{1,2}\.\d{2,3}\s*%\s*(?:senior|convertible|notes)|Senior Notes due 20\d\d|Delayed Draw Term Loan|\bDDTL\b|term loan)",
    "depreciation_life": r"(?:useful li(?:fe|ves)|depreciat\w+ over|estimated useful)",
}


def _get(url: str, timeout: float = 60.0) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _ciks() -> dict[str, str]:
    table = json.loads(_get("https://www.sec.gov/files/company_tickers.json"))
    by = {row["ticker"].upper(): int(row["cik_str"]) for row in table.values()}
    return {t: f"{by[t]:010d}" for t in ROLES if t in by}


def _latest(cik: str, forms: tuple[str, ...]) -> tuple[str, str, str] | None:
    rec = json.loads(_get(f"https://data.sec.gov/submissions/CIK{cik}.json"))["filings"]["recent"]
    for i in range(len(rec["form"])):
        if rec["form"][i] in forms:
            return rec["filingDate"][i], rec["accessionNumber"][i], rec["primaryDocument"][i]
    return None


def _text(cik: str, accession: str, doc: str) -> str:
    acc = accession.replace("-", "")
    raw = _get(
        f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}"
    ).decode("utf-8", "replace")
    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw)))


def _extract(txt: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for label, pat in TARGETS.items():
        hits: list[str] = []
        for m in re.finditer(pat, txt, re.I):
            s, e = max(0, m.start() - 180), min(len(txt), m.end() + 180)
            snip = txt[s:e].strip()
            if snip not in hits:
                hits.append(snip)
            if len(hits) >= 2:
                break
        if hits:
            out[label] = hits
    return out


def _verify_one(ticker: str, cik: str) -> dict[str, Any]:
    rec: dict[str, Any] = {"ticker": ticker, "cik": cik, "role": ROLES[ticker], "filings": {}}
    for form in (("10-K",), ("10-Q",)):
        try:
            latest = _latest(cik, form)
            time.sleep(0.5)
            if not latest:
                continue
            fdate, acc, doc = latest
            txt = _text(cik, acc, doc)
            time.sleep(0.5)
            rec["filings"][form[0]] = {
                "date": fdate,
                "accession": acc,
                "chars": len(txt),
                "facts": _extract(txt),
            }
        except Exception as e:  # noqa: BLE001 -- record failures, keep sweeping
            rec["filings"][form[0]] = {"error": f"{type(e).__name__}: {e}"}
    return rec


def main() -> int:
    ciks = _ciks()
    print(f"resolved {len(ciks)}/{len(ROLES)} CIKs; sweeping…\n")
    results = []
    for ticker in ROLES:
        cik = ciks.get(ticker)
        if not cik:
            print(f"  {ticker:5} NO CIK")
            continue
        rec = _verify_one(ticker, cik)
        results.append(rec)
        forms = rec["filings"]
        conc = forms.get("10-K", {}).get("facts", {}).get("customer_concentration", [])
        rpo = forms.get("10-K", {}).get("facts", {}).get("rpo_backlog", []) or forms.get(
            "10-Q", {}
        ).get("facts", {}).get("rpo_backlog", [])
        gc = "GOING-CONCERN" if any(
            "going_concern" in forms.get(f, {}).get("facts", {}) for f in ("10-K", "10-Q")
        ) else ""
        print(
            f"  {ticker:5} {rec['role']:13} "
            f"10-K {forms.get('10-K', {}).get('date', '—')} "
            f"10-Q {forms.get('10-Q', {}).get('date', '—')} "
            f"{'conc✓' if conc else 'conc—'} {'rpo✓' if rpo else 'rpo—'} {gc}"
        )
    OUT.write_text(json.dumps({"entities": results}, indent=1) + "\n")
    print(f"\nwrote {OUT.relative_to(ROOT)} ({len(results)} entities)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
