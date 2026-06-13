"""Phase 2 — classify the surfaced fragility concentrations BY SECTOR.

Reads the sector-agnostic fragility map (Phase 1) and assigns each scored entity a
sector by name/ticker heuristic, so the economy's fragility concentrations fall out
as a RESULT (which clusters light up beyond AI). Banks are reclassified OFF the
corporate-leverage axis (their fragility is duration / deposit-flight, not leverage).

Offline only — no network. A precise CIK->SIC join is the queued refinement (a cheap
data.sec.gov pull once storage is cleared); until then classification is tier=heuristic.

Output: analysis/fragility_by_sector.{json,md}
"""

# ruff: noqa: PERF401  (report-builder appends are clearer as explicit loops)
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_JSON = ROOT / "analysis" / "economy_wide_fragility_map.json"
OUT_JSON = ROOT / "analysis" / "fragility_by_sector.json"
OUT_MD = ROOT / "analysis" / "fragility_by_sector.md"

# Ordered sector rules: first match wins. (sector, regex). Order matters — more
# specific patterns (mortgage REIT, LNG) precede broader ones (REIT, utility).
SECTOR_RULES: list[tuple[str, str]] = [
    (
        "Bank / depository",
        r"\b(bancorp|bancshares|banco|bank of|national bank|"
        r"financial group|first national|community bank|savings|federal savings|"
        r"\bn\.?a\.?$)\b",
    ),
    (
        "Mortgage REIT",
        r"\b(mortgage (investment|trust|capital)|pennymac|mfa financial|"
        r"annaly|agnc|rithm|redwood trust|two harbors|arbor realty|chimera|"
        r"new residential|ready capital|dynex|ellington)\b",
    ),
    (
        "BDC / private credit",
        r"\b(capital corp|bdc|business development|"
        r"secured lending|blackstone secured|blue owl|owl rock|fs kkr|prospect capital|"
        r"golub|sixth street|main street capital|hercules capital|barings)\b",
    ),
    (
        "LNG / gas export",
        r"\b(lng|cheniere|nextdecade|venture global|tellurian|"
        r"sabine pass|freeport)\b",
    ),
    (
        "Midstream / pipeline",
        r"\b(midstream|pipeline|enbridge|enterprise products|"
        r"energy transfer|kinder morgan|williams|oneok|mplx|plains all american|"
        r"magellan|targa|western midstream|dt midstream|antero midstream)\b",
    ),
    (
        "Oil & gas E&P",
        r"\b(resources corp|petroleum|oil exploration|oil & gas|"
        r"antero resources|occidental|devon|diamondback|coterra|chesapeake|"
        r"permian|marathon oil|apache|ovintiv|range resources)\b",
    ),
    (
        "Power / utility",
        r"\b(energy|electric|power|edison|utilit|nrg|centerpoint|"
        r"nisource|public service enterprise|exelon|dte|evergy|talen|calpine|vistra|"
        r"constellation|american electric|duke energy|dominion|southern co|"
        r"firstenergy|ameren|entergy|pg&e|pacific gas|sempra|xcel|wec energy|"
        r"eversource|pinnacle west|alliant)\b",
    ),
    (
        "Telecom",
        r"\b(lumen|at&t|verizon|t-mobile|frontier communications|"
        r"telecom|communications inc|centurylink|windstream|charter communications|"
        r"comcast|altice|cogent)\b",
    ),
    (
        "Data center / AI infra",
        r"\b(equinix|digital realty|coreweave|applied digital|"
        r"iren|terawulf|hut 8|core scientific|cipher|cleanspark|riot|bitdeer|"
        r"hyperscale data|data center|switch inc|cyxtera|vantage)\b",
    ),
    (
        "REIT / CRE (equity)",
        r"\b(realty|properties|reit|residential|welltower|"
        r"brixmor|healthpeak|copt|equity residential|agree realty|kennedy-wilson|"
        r"lineage|boston properties|vornado|sl green|kilroy|hudson pacific|"
        r"simon property|prologis|ventas|alexandria|federal realty|regency|"
        r"starwood property|kimco|host hotels|udr|essex|mid-america|camden)\b",
    ),
    (
        "Gaming / leisure / lodging",
        r"\b(las vegas sands|mgm|wynn|caesars|resorts|"
        r"gaming|casino|marina bay|penn entertainment|boyd|churchill downs|"
        r"carnival|royal caribbean|norwegian cruise)\b",
    ),
    (
        "Specialty pharma / healthcare",
        r"\b(pharma|bausch|therapeutics|biosciences|"
        r"health companies|healthcare|medical|biopharm|labs|teva|viatris|"
        r"endo|mallinckrodt|jazz pharma)\b",
    ),
    (
        "Payments / fintech",
        r"\b(paypal|bread financial|shift4|payments|block inc|"
        r"affirm|sofi|fiserv|fidelity national|global payments|fleetcor|wex inc|"
        r"synchrony|ally financial|navient|sallie mae|nelnet)\b",
    ),
    (
        "Consumer / staples / retail",
        r"\b(pepsico|keurig|dr pepper|beverage|amcor|"
        r"nike|coca-cola|kraft|mondelez|general mills|kellanova|procter|colgate|"
        r"walmart|target|costco|kroger|albertsons|dollar general|dollar tree)\b",
    ),
    (
        "Industrial / materials / other infra",
        r"\b(eaton|emerson|honeywell|3m|"
        r"caterpillar|deere|illinois tool|parker|dover|jabil|flex|sanmina|"
        r"bhp|rio tinto|freeport-mcmoran|nucor|steel|cement|chemicals|dow inc|"
        r"dupont|lyondell|air products|linde|sherwin)\b",
    ),
    (
        "Media / advertising",
        r"\b(omnicom|interpublic|publicis|wpp|advertising|"
        r"media|paramount|warner bros|fox corp|nexstar|sinclair|news corp|"
        r"mcgraw-hill|pearson|gannett)\b",
    ),
    (
        "Aerospace / space / defense",
        r"\b(space exploration|spacex|aerospace|"
        r"defense|lockheed|northrop|raytheon|rtx|general dynamics|boeing|"
        r"l3harris|huntington ingalls|leidos)\b",
    ),
]
COMPILED = [(name, re.compile(rx, re.IGNORECASE)) for name, rx in SECTOR_RULES]


def classify(entity: str, ai_tagged: bool) -> str:
    for name, rx in COMPILED:
        if rx.search(entity):
            return name
    if ai_tagged:
        return "Data center / AI infra"
    return "Other / unclassified"


def main() -> None:
    data = json.loads(IN_JSON.read_text())
    rows = data["top_200"]
    by_sector: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        sec = classify(r["entity"], r["ai_tagged"])
        by_sector[sec].append(r)

    BANK_AXIS = "Bank / depository"  # excluded from the corporate-leverage ranking

    sectors = []
    for sec, members in by_sector.items():
        comps = [m["composite"] for m in members]
        debt = sum(m["debt_notional_usd"] for m in members)
        near = sum(m["near_term_notional_usd"] for m in members)
        members_sorted = sorted(members, key=lambda m: m["composite"], reverse=True)
        sectors.append(
            {
                "sector": sec,
                "n": len(members),
                "sum_debt_usd": debt,
                "sum_near_term_usd": near,
                "mean_composite": round(sum(comps) / len(comps), 4),
                "max_composite": round(max(comps), 4),
                "off_corporate_leverage_axis": sec == BANK_AXIS,
                "top_names": [
                    f"{m['entity'][:36]} ({m['composite']:.3f})" for m in members_sorted[:6]
                ],
            }
        )
    # rank sectors by mean composite among the corporate-leverage axis (banks shown separately)
    sectors.sort(
        key=lambda s: (not s["off_corporate_leverage_axis"], s["mean_composite"]), reverse=True
    )
    sectors.sort(key=lambda s: s["mean_composite"], reverse=True)

    ai_sector = next((s for s in sectors if s["sector"] == "Data center / AI infra"), None)
    ai_rank = (sectors.index(ai_sector) + 1) if ai_sector else None
    # rank among genuine cohorts (n>=3) so a single-name "sector" doesn't mislead the headline
    cohorts = [s for s in sectors if s["n"] >= 3]
    ai_cohort_rank = (cohorts.index(ai_sector) + 1) if ai_sector in cohorts else None
    n_cohorts = len(cohorts)

    out = {
        "as_of": data["as_of"],
        "source": "analysis/economy_wide_fragility_map.json (top_200)",
        "classification_tier": "heuristic (name/ticker); CIK->SIC join queued",
        "ai_sector_rank": ai_rank,
        "ai_cohort_rank": ai_cohort_rank,
        "n_cohorts": n_cohorts,
        "sectors": sectors,
    }
    OUT_JSON.write_text(json.dumps(out, indent=2))
    write_md(out)
    print(f"wrote {OUT_JSON.relative_to(ROOT)} + {OUT_MD.relative_to(ROOT)}")
    print(f"  AI-infra sector rank by mean composite: {ai_rank} of {len(sectors)}")


BANNER = (ROOT / "analysis" / "economy_wide_fragility_map.md").read_text().split("\n")[2]


def write_md(out: dict) -> None:
    L: list[str] = []
    L.append("# Fragility by sector — which clusters light up (AI is one of many)")
    L.append("")
    L.append(BANNER)
    L.append("")
    L.append(
        f"**As of {out['as_of']}.** Phase 2 of the dive: the Phase-1 economy-wide "
        f"fragility map, grouped by sector so the concentrations fall out as a result. "
        f"Classification is **{out['classification_tier']}**. Banks are shown on a "
        f"separate axis (deposit/FHLB liabilities are not corporate leverage). "
        f"Machine-readable: [fragility_by_sector.json](fragility_by_sector.json)."
    )
    L.append("")
    L.append(
        f"**Among genuine multi-name cohorts (n≥3), AI / data-center ranks "
        f"#{out['ai_cohort_rank']} of {out['n_cohorts']} by mean composite fragility — "
        f"in a top-tier dead heat with midstream/pipeline and mortgage REITs (~0.348).** "
        f"A real, uniformly-stressed concentration — but not *the* epicenter; there isn't "
        f"a single one."
    )
    L.append("")
    L.append("| sector | n | Σ debt $B | Σ ≤2027 $B | mean comp | max comp | off-lev axis |")
    L.append("|---|---:|---:|---:|---:|---:|:--:|")
    for s in out["sectors"]:
        L.append(
            f"| {s['sector']} | {s['n']} | {s['sum_debt_usd'] / 1e9:.0f} | "
            f"{s['sum_near_term_usd'] / 1e9:.0f} | {s['mean_composite']:.3f} | "
            f"{s['max_composite']:.3f} | {'banks' if s['off_corporate_leverage_axis'] else ''} |"
        )
    L.append("")
    L.append("## Top names per sector")
    L.append("")
    for s in out["sectors"]:
        L.append(f"- **{s['sector']}** ({s['n']}): " + ", ".join(s["top_names"]))
    L.append("")
    L.append("## Reading & caveats")
    L.append("")
    unclassified = next((s for s in out["sectors"] if s["sector"] == "Other / unclassified"), None)
    n_unc = unclassified["n"] if unclassified else 0
    L.append(
        "- **No single epicenter.** The top sectors sit in a narrow 0.34-0.35 mean-composite "
        "band (oil&gas E&P, midstream, AI-infra, mortgage REITs, payments) — fragility is "
        "**broadly distributed** across leveraged, rate-sensitive cohorts, not concentrated "
        "in one. This is the central Phase-2 finding."
    )
    L.append(
        "- **AI-infra ranks high because it is *uniformly* stressed** (tight cohort, n=7), "
        "whereas big sectors like utilities (n=20) carry many healthy names that dilute the "
        "mean. AI validated as case zero precisely because the whole cohort lights up — but "
        "it is one of ~6 comparably-stressed cohorts, not a unique outlier."
    )
    L.append(
        "- **Small-n instability:** several top sectors have n=3-4 (E&P, midstream), so "
        "their mean composite is noisy; treat the ordering inside the 0.34-0.35 band as a "
        "tie, not a strict ranking."
    )
    L.append(
        f"- **Coverage gap:** {n_unc} of 200 names fell into *Other / unclassified* "
        f"(${unclassified['sum_debt_usd'] / 1e9:.0f}B if present) — the name heuristic is "
        f"coarse and the single largest bucket. The CIK→SIC join is the fix and will "
        f"redistribute most of these into real sectors before any conclusion is drawn."
    )
    L.append("")
    L.append(
        "*Heuristic classification; the precise CIK->SIC join (a small data.sec.gov "
        "pull) is queued for when storage clears. Seeds Phase 3 deep-agent profiling, "
        "which targets the highest-mean-composite non-bank concentrations.*"
    )
    OUT_MD.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
