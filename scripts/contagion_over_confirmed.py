"""Contagion linkage over the confirmed-fragility set (local, no agents, no pulls).

Attacks the goal's "resolve into a single unified graph, traverse every contagion path":
cross-references the 174 confirmed-fragility entities against the on-disk capital-exposure
and contract graphs to find (a) DIRECT links between two confirmed-fragile names, and
(b) SHARED counterparties two confirmed names both depend on (indirect contagion). Reports
the honest match rate — a LOW interconnection is itself a finding (idiosyncratic, broadly
distributed distress vs a single contagion cascade).

Output: analysis/contagion_over_confirmed.{json,md}
"""

from __future__ import annotations

# ruff: noqa: PERF401
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

csv.field_size_limit(10**9)
ROOT = Path(__file__).resolve().parent.parent
FINDINGS = ROOT / "analysis" / "phase3_findings.json"
CAP_EDGES = ROOT / "data" / "graph" / "capital_exposure_edges.csv"
CON_EDGES = ROOT / "data" / "graph" / "capital_contract_edges.csv"
OUT_JSON = ROOT / "analysis" / "contagion_over_confirmed.json"
OUT_MD = ROOT / "analysis" / "contagion_over_confirmed.md"

GENERIC = re.compile(
    r"\b(bank|agent|trustee|lender|llc|inc|corp|lp|trust|the|company|"
    r"holdings|group|n a|co|section|item|article|exhibit)\b|^\d+ |^section",
    re.I,
)


def norm(n: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", re.split(r"\s*[(\[]", n, maxsplit=1)[0].lower()).strip()


def main() -> None:
    conf = [
        x for x in json.loads(FINDINGS.read_text())["findings"] if x["is_real_fragility"] is True
    ]
    cset = {norm(x["entity"]) for x in conf}
    cset = {c for c in cset if len(c) >= 4}
    sev = {norm(x["entity"]): x["severity"] for x in conf}

    direct = []  # confirmed -> confirmed edges
    cp_to_conf = defaultdict(set)  # counterparty -> set of confirmed names linked to it
    matched = set()

    for path in (CAP_EDGES, CON_EDGES):
        if not path.exists():
            continue
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                s, t = norm(row.get("source_name", "")), norm(row.get("target_name", ""))
                s_c, t_c = s in cset, t in cset
                if s_c:
                    matched.add(s)
                if t_c:
                    matched.add(t)
                if s_c and t_c and s != t:
                    direct.append(
                        (s, t, row.get("relationship_type") or row.get("deal_type") or "")
                    )
                # shared-counterparty: confirmed endpoint linked to a non-generic counterparty
                if s_c and t and not t_c and not GENERIC.search(t):
                    cp_to_conf[t].add(s)
                if t_c and s and not s_c and not GENERIC.search(s):
                    cp_to_conf[s].add(t)

    shared = {cp: sorted(names) for cp, names in cp_to_conf.items() if len(names) >= 2}
    out = {
        "confirmed_total": len(conf),
        "confirmed_present_in_graph": len(matched),
        "match_rate": round(len(matched) / len(cset), 3) if cset else 0,
        "direct_confirmed_to_confirmed_edges": len(direct),
        "direct_pairs": [{"a": a, "b": b, "rel": r} for a, b, r in direct][:50],
        "shared_counterparty_hubs": sorted(
            (
                {"counterparty": cp, "confirmed_linked": names, "n": len(names)}
                for cp, names in shared.items()
            ),
            key=lambda x: -x["n"],
        )[:40],
        "interpretation": (
            "LOW interconnection among confirmed-fragile names supports the broadly-distributed / "
            "idiosyncratic reading (no single contagion cascade); HIGH shared-counterparty "
            "clustering would indicate systemic contagion channels."
        ),
    }
    OUT_JSON.write_text(json.dumps(out, indent=2))
    write_md(out, sev)
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")
    print(
        f"  confirmed {out['confirmed_total']} | in-graph {out['confirmed_present_in_graph']} "
        f"(match {out['match_rate']}) | direct C-C edges {out['direct_confirmed_to_confirmed_edges']} "
        f"| shared-cp hubs {len(shared)}"
    )


BANNER = (ROOT / "analysis" / "economy_wide_fragility_map.md").read_text().split("\n")[2]


def write_md(out: dict, sev: dict) -> None:
    L = []
    L.append("# Contagion linkage over the confirmed-fragility set")
    L.append("")
    L.append(BANNER)
    L.append("")
    L.append(
        f"Cross-references the **{out['confirmed_total']} confirmed-fragility entities** against "
        f"the on-disk capital-exposure + contract graphs. **{out['confirmed_present_in_graph']} "
        f"appear in the graph at all (match rate {out['match_rate']})** — most confirmed names "
        f"come from the XBRL breadth layer and are NOT in the deal-corpus graph, so absence here "
        f"is a coverage gap, not proof of no linkage. Machine-readable: "
        f"[contagion_over_confirmed.json](contagion_over_confirmed.json)."
    )
    L.append("")
    L.append(
        f"- **Direct confirmed→confirmed edges:** {out['direct_confirmed_to_confirmed_edges']}\n"
        f"- **Shared-counterparty hubs (≥2 confirmed names depend on the same node):** "
        f"{len(out['shared_counterparty_hubs'])}"
    )
    L.append("")
    L.append("## Shared-counterparty contagion hubs (confirmed names exposed to the same node)")
    L.append("")
    if out["shared_counterparty_hubs"]:
        L.append("| counterparty | # confirmed | confirmed names |")
        L.append("|---|---:|---|")
        for h in out["shared_counterparty_hubs"]:
            L.append(
                f"| {h['counterparty'][:30]} | {h['n']} | {', '.join(h['confirmed_linked'][:6])} |"
            )
    else:
        L.append("_None found in the matched subset._")
    L.append("")
    L.append(f"**Reading:** {out['interpretation']}")
    L.append("")
    L.append(
        "*Limit: this traverses only the deal-corpus capital + contract graphs (small, "
        "AI-seeded). The 425k-node LEI ownership graph and the full economy-wide contagion "
        "traversal are the next non-LLM extension. Match rate is the honest coverage number.*"
    )
    OUT_MD.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
