"""Multi-year leverage/coverage TRAJECTORIES for the confirmed-fragility set (HTTP+local).

Attacks the goal's "reconstruct multi-decade histories": for each confirmed-fragile name,
pull the FULL XBRL time series (data.sec.gov, all available fiscal years) and compute the
year-by-year net-debt/EBITDA and EBITDA/interest path. Classifies each as
deteriorating / stable / improving — turning a point-in-time flag into a direction, which
is the actual forward signal. No LLM agents.

Output: analysis/multidecade_trends.{json,md}
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from xbrl_net_leverage import (  # noqa: E402
    CASH_TAGS,
    DA_TAGS,
    DEBT_TAGS,
    INT_TAGS,
    OPINC_TAGS,
    fetch_json,
)

FINDINGS = ROOT / "analysis" / "phase3_findings.json"
XBRL_CACHE = ROOT / "data" / "entity_universe" / "xbrl_economy_cache.json"
OUT_JSON = ROOT / "analysis" / "multidecade_trends.json"
OUT_MD = ROOT / "analysis" / "multidecade_trends.md"
RATE_S = 0.12


def norm(n: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", re.split(r"\s*[(\[]", n, maxsplit=1)[0].lower()).strip()


def series(facts: dict, tags: list[str], instant: bool) -> dict[int, float]:
    """fiscal-year -> value, latest filing per year wins."""
    for tag in tags:
        node = facts.get("facts", {}).get("us-gaap", {}).get(tag)
        if not node:
            continue
        rows = node.get("units", {}).get("USD", [])
        out: dict[int, float] = {}
        for u in rows:
            fy, fp, form = u.get("fy"), u.get("fp"), u.get("form", "")
            if fy is None or fp != "FY" or not form.startswith("10-K"):
                continue
            if instant and "start" in u:
                continue
            out[int(fy)] = float(u["val"])
        if out:
            return out
    return {}


def trajectory(years: list[int], cov: dict[int, float]) -> str:
    pts = [cov[y] for y in years if y in cov and cov[y] is not None]
    if len(pts) < 3:
        return "insufficient_history"
    recent, early = pts[-3:], pts[:3]
    r, e = sum(recent) / len(recent), sum(early) / len(early)
    if r < e * 0.8:
        return "deteriorating"
    if r > e * 1.25:
        return "improving"
    return "stable"


def main() -> None:
    conf = [
        x for x in json.loads(FINDINGS.read_text())["findings"] if x["is_real_fragility"] is True
    ]
    cache = json.loads(XBRL_CACHE.read_text())
    name_cik = {norm(v.get("name", "")): v.get("cik") for v in cache.values() if v.get("cik")}
    # also scrape CIK out of confirmed entity strings
    targets = {}
    for x in conf:
        nm = norm(x["entity"])
        cik = name_cik.get(nm)
        if not cik:
            m = re.search(r"CIK[:\s]*0*([0-9]{4,10})", x["entity"])
            cik = m.group(1).zfill(10) if m else None
        if cik:
            targets[cik] = x["entity"]
    print(f"confirmed with CIK: {len(targets)}")

    results = []
    for i, (cik, name) in enumerate(targets.items(), 1):
        facts = fetch_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")
        time.sleep(RATE_S)
        if not facts:
            continue
        debt = series(facts, DEBT_TAGS, True)
        cash = series(facts, CASH_TAGS, True)
        op = series(facts, OPINC_TAGS, False)
        da = series(facts, DA_TAGS, False)
        inte = series(facts, INT_TAGS, False)
        years = sorted(set(op) & set(inte))
        cov = {}
        ndl = {}
        for y in years:
            eb = (op.get(y, 0) or 0) + (da.get(y, 0) or 0)
            if inte.get(y):
                cov[y] = round(eb / inte[y], 2)
            nd = (debt.get(y, 0) or 0) - (cash.get(y, 0) or 0)
            if eb > 0:
                ndl[y] = round(nd / eb, 1)
        if len(cov) < 3:
            continue
        traj = trajectory(years, cov)
        results.append(
            {
                "entity": name[:46],
                "cik": cik,
                "years": [y for y in years if y in cov],
                "coverage_path": {str(y): cov[y] for y in years if y in cov},
                "nd_ebitda_path": {str(y): ndl[y] for y in years if y in ndl},
                "trajectory": traj,
            }
        )
        if i % 40 == 0:
            print(f"  {i}/{len(targets)}")

    from collections import Counter

    dist = Counter(r["trajectory"] for r in results)
    results.sort(
        key=lambda r: {"deteriorating": 0, "stable": 1, "improving": 2}.get(r["trajectory"], 3)
    )
    out = {
        "confirmed_with_history": len(results),
        "trajectory_distribution": dict(dist),
        "trends": results,
    }
    OUT_JSON.write_text(json.dumps(out, indent=2))
    write_md(out)
    print(f"wrote {OUT_JSON.relative_to(ROOT)} | {dict(dist)}")


BANNER = (ROOT / "analysis" / "economy_wide_fragility_map.md").read_text().split("\n")[2]


def write_md(out: dict) -> None:
    L = []
    L.append("# Multi-year fragility trajectories of the confirmed set")
    L.append("")
    L.append(BANNER)
    L.append("")
    L.append(
        f"Year-by-year XBRL leverage/coverage paths for **{out['confirmed_with_history']} "
        f"confirmed-fragile names with ≥3y of history** (data.sec.gov). The *direction* is the "
        f"forward signal. Distribution: {out['trajectory_distribution']}. "
        f"Machine-readable: [multidecade_trends.json](multidecade_trends.json)."
    )
    L.append("")
    L.append("## Deteriorating (coverage falling toward distress — the forward-risk names)")
    L.append("")
    L.append("| entity | coverage path (EBITDA/interest by FY) |")
    L.append("|---|---|")
    for r in out["trends"]:
        if r["trajectory"] != "deteriorating":
            continue
        path = " → ".join(f"{y}:{v}" for y, v in list(r["coverage_path"].items())[-6:])
        L.append(f"| {r['entity']} | {path} |")
    L.append("")
    L.append(
        "*`deteriorating` = mean coverage of the last 3 FYs < 0.8× the first 3 FYs. "
        "Single-line ratios; financials/REITs read differently. The trajectory turns a "
        "point-in-time flag into a trend — names already deteriorating are the forward-risk set.*"
    )
    OUT_MD.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
