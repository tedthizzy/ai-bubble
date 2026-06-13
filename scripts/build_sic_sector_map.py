"""Refinement — ground the fragility map's sectors in real SEC SIC codes.

Replaces the Phase-2 name heuristic (97/200 "unclassified") with authoritative SIC
classifications pulled from data.sec.gov. ORCHESTRATOR-side EDGAR access only (declared
UA, never spoofed); submissions JSON parsed IN MEMORY and discarded — only the tiny
CIK->SIC map + the grouped view are written, so near-zero disk.

Outputs:
  - data/entity_universe/cik_sic_map.json
  - analysis/fragility_by_sic.{json,md}
"""

# ruff: noqa: PERF401
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP_JSON = ROOT / "analysis" / "economy_wide_fragility_map.json"
SIC_MAP = ROOT / "data" / "entity_universe" / "cik_sic_map.json"
OUT_JSON = ROOT / "analysis" / "fragility_by_sic.json"
OUT_MD = ROOT / "analysis" / "fragility_by_sic.md"

UA = "ai-bubble research ted1508@gmail.com"
RATE_S = 0.15  # ~7 req/s, within SEC's 10/s etiquette ceiling

# SIC 2-digit major group -> readable division label (for grouping the output).
SIC_DIVISION = {
    "01": "Agriculture",
    "10": "Metal mining",
    "12": "Coal mining",
    "13": "Oil & gas extraction",
    "14": "Nonmetallic mining",
    "15": "Construction",
    "16": "Heavy construction",
    "20": "Food",
    "21": "Tobacco",
    "22": "Textiles",
    "23": "Apparel",
    "24": "Lumber/wood",
    "25": "Furniture",
    "26": "Paper",
    "27": "Printing/publishing",
    "28": "Chemicals/pharma",
    "29": "Petroleum refining",
    "30": "Rubber/plastics",
    "32": "Stone/clay/glass",
    "33": "Primary metals",
    "34": "Fabricated metals",
    "35": "Machinery/computers",
    "36": "Electronics",
    "37": "Transportation equipment",
    "38": "Instruments",
    "39": "Misc manufacturing",
    "40": "Railroads",
    "42": "Trucking",
    "44": "Water transport",
    "45": "Air transport",
    "46": "Pipelines (non-gas)",
    "47": "Transport services",
    "48": "Communications",
    "49": "Utilities (electric/gas/sanitary)",
    "50": "Wholesale durable",
    "51": "Wholesale nondurable",
    "52": "Building materials retail",
    "53": "General merchandise retail",
    "54": "Food stores",
    "55": "Auto dealers",
    "56": "Apparel retail",
    "57": "Furniture retail",
    "58": "Eating/drinking",
    "59": "Misc retail",
    "60": "Depository banks",
    "61": "Nondepository credit",
    "62": "Securities/brokers",
    "63": "Insurance carriers",
    "64": "Insurance agents",
    "65": "Real estate",
    "67": "Holding/investment (incl REITs/BDCs)",
    "70": "Hotels/lodging",
    "72": "Personal services",
    "73": "Business services/software",
    "75": "Auto repair",
    "78": "Motion pictures",
    "79": "Amusement/recreation",
    "80": "Health services",
    "87": "Engineering/accounting/research",
    "99": "Nonclassifiable",
}


def load_sic_cache() -> dict[str, dict]:
    if SIC_MAP.exists():
        return json.loads(SIC_MAP.read_text())
    return {}


def fetch_sic(cik10: str) -> dict | None:
    url = f"https://data.sec.gov/submissions/CIK{cik10}.json"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.load(r)
        return {
            "sic": str(d.get("sic") or ""),
            "sicDescription": d.get("sicDescription") or "",
            "name": d.get("name") or "",
        }
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def main() -> None:
    data = json.loads(MAP_JSON.read_text())
    rows = data["top_200"] + data.get("top_canaries", [])
    # dedup entities, keep best (highest composite) per cik
    want: dict[str, dict] = {}
    for r in rows:
        cik = (r.get("cik") or "").strip()
        if not cik or not cik.isdigit():
            continue
        cik10 = cik.zfill(10)
        if cik10 not in want or r["composite"] > want[cik10]["composite"]:
            want[cik10] = r

    cache = load_sic_cache()
    to_pull = [c for c in want if c not in cache]
    print(f"{len(want)} CIK'd entities; {len(cache)} cached; pulling {len(to_pull)} ...")
    for i, cik10 in enumerate(to_pull, 1):
        rec = fetch_sic(cik10)
        cache[cik10] = rec or {"sic": "", "sicDescription": "", "name": ""}
        if i % 25 == 0:
            print(f"  pulled {i}/{len(to_pull)}")
            SIC_MAP.write_text(json.dumps(cache, indent=2))
        time.sleep(RATE_S)
    SIC_MAP.write_text(json.dumps(cache, indent=2))

    # group flagged entities by SIC major group (real classification)
    groups: dict[str, list] = defaultdict(list)
    resolved = 0
    for cik10, r in want.items():
        sic = cache.get(cik10, {}).get("sic", "")
        if not sic:
            groups["(no SIC)"].append(r)
            continue
        resolved += 1
        mg = sic[:2].zfill(2)
        label = f"{mg} {SIC_DIVISION.get(mg, 'Other')}"
        groups[label].append({**r, "sic": sic, "sicDescription": cache[cik10]["sicDescription"]})

    grouped = []
    for label, members in groups.items():
        comps = [m["composite"] for m in members]
        grouped.append(
            {
                "sic_division": label,
                "n": len(members),
                "mean_composite": round(sum(comps) / len(comps), 4),
                "max_composite": round(max(comps), 4),
                "sum_debt_usd": sum(m["debt_notional_usd"] for m in members),
                "top": [
                    f"{m['entity'][:34]} ({m['composite']:.3f})"
                    for m in sorted(members, key=lambda x: x["composite"], reverse=True)[:6]
                ],
            }
        )
    grouped.sort(key=lambda g: (g["sic_division"] != "(no SIC)", g["mean_composite"]), reverse=True)
    grouped.sort(key=lambda g: g["mean_composite"], reverse=True)

    out = {
        "as_of": data["as_of"],
        "entities_with_cik": len(want),
        "entities_sic_resolved": resolved,
        "groups": grouped,
    }
    OUT_JSON.write_text(json.dumps(out, indent=2))
    write_md(out)
    print(
        f"wrote {SIC_MAP.relative_to(ROOT)}, {OUT_JSON.relative_to(ROOT)}, {OUT_MD.relative_to(ROOT)}"
    )
    print(f"  SIC-resolved {resolved}/{len(want)} CIK'd entities")


BANNER = (ROOT / "analysis" / "economy_wide_fragility_map.md").read_text().split("\n")[2]


def write_md(out: dict) -> None:
    L: list[str] = []
    L.append("# Fragility by real SIC division (ground-truthed sectors)")
    L.append("")
    L.append(BANNER)
    L.append("")
    L.append(
        f"**As of {out['as_of']}.** The Phase-2 sector view, re-grounded in **real SEC SIC "
        f"codes** pulled from data.sec.gov ({out['entities_sic_resolved']}/"
        f"{out['entities_with_cik']} CIK'd entities resolved), replacing the name heuristic. "
        f"Machine-readable: [fragility_by_sic.json](fragility_by_sic.json)."
    )
    L.append("")
    L.append("| SIC division | n | mean comp | max comp | Σ debt $B |")
    L.append("|---|---:|---:|---:|---:|")
    for g in out["groups"]:
        L.append(
            f"| {g['sic_division']} | {g['n']} | {g['mean_composite']:.3f} | "
            f"{g['max_composite']:.3f} | {g['sum_debt_usd'] / 1e9:.0f} |"
        )
    L.append("")
    L.append("## Top names per SIC division")
    L.append("")
    for g in out["groups"]:
        L.append(f"- **{g['sic_division']}** ({g['n']}): " + ", ".join(g["top"]))
    L.append("")
    L.append(
        "*SIC is the issuer's primary classification; conglomerates and holding companies "
        "(SIC 67) may understate sub-sector detail. Pairs with the name-heuristic view in "
        "[fragility_by_sector.md](fragility_by_sector.md).*"
    )
    OUT_MD.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
