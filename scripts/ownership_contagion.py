"""Ownership-graph contagion over the confirmed-fragility set (local, no agents/credits).

Extends contagion_over_confirmed.py from the deal-corpus capital/contract graphs to the
425k-node / 643k-edge LEI ownership graph. Attacks "resolve every alias into a single
unified graph": matches confirmed-fragile names to LEI legal entities, traverses
child→parent to the ULTIMATE parent, and groups confirmed names by shared ultimate owner —
the common-owner contagion channel (e.g. two fragile names under the same PE sponsor).

Output: analysis/ownership_contagion.{json,md}
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
NODES = ROOT / "data" / "graph" / "ownership_nodes.csv"
EDGES = ROOT / "data" / "graph" / "ownership_edges.csv"
OUT_JSON = ROOT / "analysis" / "ownership_contagion.json"
OUT_MD = ROOT / "analysis" / "ownership_contagion.md"


def norm(n: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", re.split(r"\s*[(\[]", n, maxsplit=1)[0].lower()).strip()


def main() -> None:
    conf = [
        x for x in json.loads(FINDINGS.read_text())["findings"] if x["is_real_fragility"] is True
    ]
    cset = {norm(x["entity"]) for x in conf if len(norm(x["entity"])) >= 5}

    # Pass 1: node_id -> legal_name (all), and matched confirmed -> node_id
    id_name: dict[str, str] = {}
    conf_node: dict[str, str] = {}  # node_id -> confirmed norm-name
    with NODES.open(newline="") as f:
        for row in csv.DictReader(f):
            nid, nm = row.get("node_id", ""), row.get("legal_name", "")
            if not nid:
                continue
            id_name[nid] = nm
            if norm(nm) in cset:
                conf_node[nid] = norm(nm)
    print(
        f"ownership nodes: {len(id_name):,} | confirmed matched to LEI: {len(set(conf_node.values()))}"
    )

    # Pass 2: child_id -> parent_id (ultimate-consolidation / direct edges)
    child_parent: dict[str, str] = {}
    with EDGES.open(newline="") as f:
        for row in csv.DictReader(f):
            c, p = row.get("child_id", ""), row.get("parent_id", "")
            rel = (row.get("relationship_type") or "").lower()
            if c and p and c != p:
                # prefer consolidation/ownership edges; keep first (don't overwrite a set parent)
                if c not in child_parent or "consolidat" in rel or "ultimate" in rel:
                    child_parent[c] = p

    def ultimate(nid: str) -> str:
        seen, cur = set(), nid
        while cur in child_parent and cur not in seen:
            seen.add(cur)
            cur = child_parent[cur]
        return cur

    # Group confirmed nodes by ultimate parent
    by_root: dict[str, set] = defaultdict(set)
    chained = 0
    for nid, cname in conf_node.items():
        root = ultimate(nid)
        if root != nid:
            chained += 1
        by_root[root].add(cname)
    shared = {id_name.get(r, r): sorted(names) for r, names in by_root.items() if len(names) >= 2}

    out = {
        "confirmed_total": len(conf),
        "confirmed_matched_to_lei": len(set(conf_node.values())),
        "confirmed_with_parent_chain": chained,
        "shared_ultimate_owner_clusters": [
            {"ultimate_owner": k, "confirmed_names": v, "n": len(v)}
            for k, v in sorted(shared.items(), key=lambda kv: -len(kv[1]))
        ],
        "interpretation": (
            "Shared ultimate owners among confirmed-fragile names = common-owner contagion "
            "(one sponsor's stress hits several). Few/none = the distress is independently held, "
            "reinforcing the idiosyncratic-scatter reading."
        ),
    }
    OUT_JSON.write_text(json.dumps(out, indent=2))
    write_md(out)
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")
    print(
        f"  matched {out['confirmed_matched_to_lei']}/{len(conf)} | chained {chained} | "
        f"shared-owner clusters {len(shared)}"
    )


BANNER = (ROOT / "analysis" / "economy_wide_fragility_map.md").read_text().split("\n")[2]


def write_md(out: dict) -> None:
    L = []
    L.append("# Ownership-graph contagion over the confirmed-fragility set")
    L.append("")
    L.append(BANNER)
    L.append("")
    L.append(
        f"Confirmed-fragile names matched into the **425k-node LEI ownership graph** and "
        f"traversed to ultimate parent. **{out['confirmed_matched_to_lei']} of "
        f"{out['confirmed_total']}** confirmed names resolve to an LEI entity; "
        f"**{out['confirmed_with_parent_chain']}** sit under a parent chain. "
        f"Machine-readable: [ownership_contagion.json](ownership_contagion.json)."
    )
    L.append("")
    L.append("## Shared ultimate-owner clusters (common-owner contagion)")
    L.append("")
    if out["shared_ultimate_owner_clusters"]:
        L.append("| ultimate owner | # confirmed | confirmed names |")
        L.append("|---|---:|---|")
        for c in out["shared_ultimate_owner_clusters"]:
            L.append(
                f"| {c['ultimate_owner'][:34]} | {c['n']} | {', '.join(c['confirmed_names'][:6])} |"
            )
    else:
        L.append("_No two confirmed-fragile names share an ultimate owner in the LEI graph._")
    L.append("")
    L.append(f"**Reading:** {out['interpretation']}")
    L.append("")
    L.append(
        "*Coverage caveat: LEI legal-name matching is exact-normalized, so small-cap / "
        "non-LEI issuers under-match; a low match rate is a coverage gap, not proof of no "
        "common ownership. Pairs with [contagion_over_confirmed.md](contagion_over_confirmed.md) "
        "(capital/contract graph) for the unified-graph view.*"
    )
    OUT_MD.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
