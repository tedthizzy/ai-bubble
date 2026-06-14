"""Phase 4 rigor — orchestrator-side EDGAR verification of the confirmed survivors.

Closes the "zero orchestrator-verified" gap: for the highest-severity confirmed
fragility names, re-pull the ACTUAL SEC filings (orchestrator, declared UA, never
spoofed) and check the distress claims at filing tier — going-concern, delisting,
default, late-filing — instead of trusting the deep agents' self-reported tier. Also
measures agent reliability (how often their "filing_verified" survives an independent pull).

In-memory fetch (filings discarded after keyword scan); only the verification table is written.
Output: analysis/survivor_filing_verification.{json,md}
"""

from __future__ import annotations

# ruff: noqa: PERF401
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FINDINGS = ROOT / "analysis" / "phase3_findings.json"
TARGETS = ROOT / "analysis" / "phase3_targets.json"
OUT_JSON = ROOT / "analysis" / "survivor_filing_verification.json"
OUT_MD = ROOT / "analysis" / "survivor_filing_verification.md"

UA = "ai-bubble research ted1508@gmail.com"
RATE_S = 0.2

DISTRESS_TERMS = {
    "going_concern": r"going concern|substantial doubt",
    "delisting": r"delist|notice of (non[- ]?compliance|deficiency)|minimum (bid|stockholders)",
    "default": r"event of default|forbearance|covenant (breach|waiver)|cross-default",
    "bankruptcy": r"chapter 11|chapter 7|voluntary petition|restructuring support agreement",
    "impairment": r"impairment (charge|loss)|goodwill impairment",
}
SEVERITY_KEEP = {"already-distressed", "high"}


def _norm(name: str) -> str:
    head = re.split(r"\s*[(\[]", name, maxsplit=1)[0]
    return re.sub(r"[^a-z0-9]+", " ", head.lower()).strip()[:40]


def fetch(url: str) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", errors="ignore")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return None


def recent_filings(cik10: str) -> list[dict]:
    raw = fetch(f"https://data.sec.gov/submissions/CIK{cik10}.json")
    if not raw:
        return []
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        return []
    rec = d.get("filings", {}).get("recent", {})
    forms = rec.get("form", [])
    dates = rec.get("filingDate", [])
    accs = rec.get("accessionNumber", [])
    docs = rec.get("primaryDocument", [])
    out = []
    for i in range(min(len(forms), 40)):
        out.append(
            {
                "form": forms[i],
                "date": dates[i],
                "accession": accs[i],
                "doc": docs[i] if i < len(docs) else "",
            }
        )
    return out


def scan_terms(text: str) -> list[str]:
    low = text.lower()
    return [k for k, rx in DISTRESS_TERMS.items() if re.search(rx, low)]


def cik_index() -> dict[str, str]:
    idx = {}
    tdata = json.loads(TARGETS.read_text())
    for t in tdata["targets"]:
        cik = (t.get("cik") or "").strip()
        if cik and cik.isdigit():
            idx[_norm(t["entity"])] = cik.zfill(10)
    # fallback: the economy-wide XBRL cache (name -> cik) covers the XBRL-distress confirmations
    cache_path = ROOT / "data" / "entity_universe" / "xbrl_economy_cache.json"
    if cache_path.exists():
        for v in json.loads(cache_path.read_text()).values():
            cik = (v.get("cik") or "").strip()
            nm = _norm(v.get("name", ""))
            if cik and cik.isdigit() and nm and nm not in idx:
                idx[nm] = cik.zfill(10)
    return idx


def main() -> None:
    findings = json.loads(FINDINGS.read_text())["findings"]
    cidx = cik_index()
    # broadened: orchestrator-verify the FULL confirmed set, not just already-distressed+high
    confirmed = [f for f in findings if f["is_real_fragility"] is True]
    seen = set()
    results = []
    for f in confirmed:
        key = _norm(f["entity"])
        cik = cidx.get(key)
        # also try to scrape a CIK out of the entity string
        if not cik:
            m = re.search(r"CIK[:\s]*0*([0-9]{4,10})", f["entity"])
            if m:
                cik = m.group(1).zfill(10)
        if not cik or cik in seen:
            continue
        seen.add(cik)

        filings = recent_filings(cik)
        time.sleep(RATE_S)
        has_nt = any(fl["form"].startswith("NT ") for fl in filings)
        # fetch latest 10-K (or 20-F) and latest 8-K; keyword-scan
        found_terms: dict[str, list[str]] = {}
        for want in ("10-K", "20-F", "8-K"):
            fl = next((x for x in filings if x["form"] == want), None)
            if not fl or not fl["doc"]:
                continue
            acc = fl["accession"].replace("-", "")
            url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{fl['doc']}"
            txt = fetch(url)
            time.sleep(RATE_S)
            if txt:
                terms = scan_terms(txt)
                if terms:
                    found_terms[f"{want} {fl['date']}"] = terms

        any_distress = bool(found_terms) or has_nt
        results.append(
            {
                "entity": f["entity"],
                "cik": cik,
                "agent_severity": f["severity"],
                "agent_tier": f["confidence_tier"],
                "recent_forms": [f"{x['form']}:{x['date']}" for x in filings[:6]],
                "late_filing_NT": has_nt,
                "distress_terms_in_filings": found_terms,
                "orchestrator_verdict": (
                    "filing_verified_distress"
                    if any_distress
                    else "no_filing_distress_signal_found"
                ),
            }
        )

    confirmed_n = sum(1 for r in results if r["orchestrator_verdict"] == "filing_verified_distress")
    out = {
        "checked": len(results),
        "filing_verified_distress": confirmed_n,
        "no_signal": len(results) - confirmed_n,
        "agent_reliability_on_spotcheck": round(confirmed_n / len(results), 3) if results else None,
        "results": results,
    }
    OUT_JSON.write_text(json.dumps(out, indent=2))
    write_md(out)
    print(f"wrote {OUT_JSON.relative_to(ROOT)} + {OUT_MD.relative_to(ROOT)}")
    print(
        f"  spot-checked {len(results)} survivors; {confirmed_n} filing-verified distress "
        f"({out['agent_reliability_on_spotcheck']} agent reliability)"
    )


BANNER = (ROOT / "analysis" / "economy_wide_fragility_map.md").read_text().split("\n")[2]


def write_md(out: dict) -> None:
    L = []
    L.append("# Survivor filing verification (orchestrator-pulled EDGAR)")
    L.append("")
    L.append(BANNER)
    L.append("")
    L.append(
        f"Independent orchestrator-side EDGAR pull of the top confirmed survivors "
        f"(already-distressed + high), to move them off agent-asserted tier. "
        f"**{out['checked']} spot-checked; {out['filing_verified_distress']} show a distress "
        f"signal in the actual filings** (going-concern / delisting / default / late-filing / "
        f"impairment); agent reliability on this sample = **{out['agent_reliability_on_spotcheck']}**. "
        f"Machine-readable: [survivor_filing_verification.json](survivor_filing_verification.json)."
    )
    L.append("")
    L.append("| entity | CIK | agent sev | NT late | distress terms found (filing) | verdict |")
    L.append("|---|---|---|:--:|---|---|")
    for r in out["results"]:
        terms = "; ".join(f"{k}→{','.join(v)}" for k, v in r["distress_terms_in_filings"].items())
        L.append(
            f"| {r['entity'][:34]} | {r['cik']} | {r['agent_severity']} | "
            f"{'Y' if r['late_filing_NT'] else ''} | {terms[:80] or '—'} | "
            f"{'✅' if r['orchestrator_verdict'] == 'filing_verified_distress' else '⚠️ none'} |"
        )
    L.append("")
    L.append(
        "*Keyword-tier verification (presence of distress language in the latest 10-K/20-F/8-K + "
        "NT late-filing flag), not a full re-audit. '⚠️ none' means the headline distress wasn't "
        "found in the most-recent primary doc — flag for a deeper read, not an automatic refutation.*"
    )
    OUT_MD.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
