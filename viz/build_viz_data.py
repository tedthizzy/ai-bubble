#!/usr/bin/env python
"""Assemble the verified financed-core dataset that every Burry-viz variant renders.

Single source of truth: pulls the honest, red-team-hardened scalars live from the
latest evidence-gated report, and lays out the scoped financed-core graph (the
~4% cluster + its suppliers/investors/offtakers/lenders/end-holders + the energy
chokepoints) with primary-source-verified amounts, PLUS the full extracted contract
universe as a background "field" layer (raw, unadjudicated -- labeled as such).
Writes viz/graph_data.json.

The red-team fixes are first-class here so the visuals cannot paper over them:
coverage 1.35x is a masking artifact (negative ex-CoreWeave); the cascade $ is a
GROSS UPPER BOUND (CoreWeave's whole debt, not OpenAI-apportioned); fragility is 2
of the first-principles tipping conditions cleanly met; execution/satellite is
magnitude-only (confounded); the ecosystem gate is held at 0.25 by design.
"""

from __future__ import annotations

import glob
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _latest_report() -> dict[str, Any]:
    # data/reports/ is the local engine output (gitignored); data/published/ is the
    # committed copy so a public clone can regenerate the viz dataset.
    candidates = glob.glob(str(ROOT / "data/reports/BURRY_REPORT_EvidenceGated_*.json")) or glob.glob(
        str(ROOT / "data/published/BURRY_REPORT_EvidenceGated_*.json")
    )
    path = max(candidates, key=os.path.basename)  # filename timestamps sort; clone mtimes do not
    return json.loads(Path(path).read_text()), os.path.basename(path).replace(".json", "")


def _find(node: Any, pred) -> Any:
    if isinstance(node, dict):
        if pred(node):
            return node
        for v in node.values():
            r = _find(v, pred)
            if r is not None:
                return r
    elif isinstance(node, list):
        for v in node:
            r = _find(v, pred)
            if r is not None:
                return r
    return None


report, report_name = _latest_report()
v = report["burry_question_answers"]["is_this_a_bubble"]["ai_direct_core_verdict"]
how_large = report["burry_question_answers"]["how_large"]
adj = (how_large.get("adjudicated_ai_direct_committed_debt") or {})
dfd = v.get("demand_funding_durability", {})
cascade0 = (dfd.get("fragile_demand_failure_cascade", {}).get("cascades") or [{}])[0]
frag = _find(report, lambda o: "first_principles_conditions_met" in o and "dimensions" in o) or {}
gds = _find(report, lambda o: o.get("status") == "source_backed" and "ai_subgraph" in o) or {}
ct = v.get("crack_timing", {})

# ---- META / verdict chrome (honest, hardened scalars) ----------------------------------
meta = {
    "generated_from": report_name,
    "headline": "Is the AI / data-center / financing boom a bubble?",
    "answer": "Yes -- in the financed compute cluster. Bounded, not ecosystem-wide.",
    "core_verdict": v.get("core_verdict"),
    "core_confidence": v.get("core_verdict_confidence"),
    "ecosystem_verdict": v.get("ecosystem_verdict"),
    "ecosystem_confidence": report["burry_question_answers"]["is_this_a_bubble"].get(
        "ecosystem_confidence"
    ),
    "high_confidence_final": False,
    "fragility_conditions_met": frag.get("first_principles_conditions_met"),
    "fragility_met_dimensions": frag.get("tipping_conditions_met"),
    "committed_core_usd": adj.get("verified_distinct_committed_core_cluster_usd"),
    "committed_incl_infra_usd": adj.get("verified_distinct_committed_incl_infra_usd"),
    "original_inflated_basis_usd": adj.get("original_inflated_basis_usd"),
    "over_count_removed_pct": adj.get("over_count_removed_pct"),
    "cascade_debt_at_risk_usd": cascade0.get("debt_at_risk_usd"),
    "issuers_breaching_base": "7 of 11",
    "indicators_flashing": "4 of 7",
    "crack_window": ct.get("near_term_pressure_window"),
    "cluster_share_pct": 4.3,
    "ai_modularity": (gds.get("ai_subgraph") or {}).get("modularity"),
    "honest_caveats": [
        "Aggregate EBITDA/interest coverage ~1.35x is a CoreWeave/CleanSpark masking artifact -- NEGATIVE ex-CoreWeave; a majority (7/11) of issuers breach at the zero-shock base.",
        "The cascade $ is a GROSS UPPER BOUND: CoreWeave's ENTIRE debt, not apportioned to OpenAI's revenue share (Microsoft is the larger ~67% customer).",
        "2 of the first-principles tipping conditions are cleanly met (duration + concentration); execution/satellite is MAGNITUDE-ONLY (the 'un-built' proxy is confounded).",
        "Committed AI-cluster debt is ~$26-30B after stripping ~98% over-count -- NOT the trillion-dollar headline aggregate.",
        "The cluster stays ~4% of the universe even at the ~2x capture-recapture true size -- bounded, not ecosystem-wide.",
        "Ecosystem evidence gate held at 0.25 by design; high-confidence-final = False.",
    ],
}

# ---- NODES (curated financed-core graph; verified attributes) --------------------------
# type -> visual family; fragility 0-1 (higher=worse); usd = size weight.
N = lambda i, t, frg, usd, note, **kw: {  # noqa: E731
    "id": i, "label": kw.get("label", i), "type": t, "fragility": frg,
    "usd": usd, "note": note, **{k: v for k, v in kw.items() if k != "label"},
}
nodes = [
    # The fragile financing hub + the cluster
    N("CoreWeave", "issuer", 0.95, 3.10e9,
      "Financing chokepoint. 67% of revenue from Microsoft; loss-making; ~0.30x DSCR; $3.1B DDTL 5.0. "
      "All GPUs are NVIDIA; NVIDIA also holds $2B equity (circular).", redteam="financing chokepoint"),
    N("TeraWulf", "issuer", 0.85, 5.23e9, "$3.2B 7.75% senior secured notes (2030) + convertibles; loss-making."),
    N("IREN", "issuer", 0.70, 5.15e9, "Convertible-heavy ($3B 2033 + 2032/2031); NVIDIA equity investee."),
    N("Applied Digital", "issuer", 0.80, 4.50e9, "ComputeCo $2.35B + ComputeCo2 $2.15B senior secured notes; NVIDIA PIPE."),
    N("Hut 8", "issuer", 0.65, 3.25e9, "$3.25B 6.192% senior secured notes (2042); Google/Anthropic ties."),
    N("MARA Holdings", "issuer", 0.60, 1.95e9, "Convertibles 2030/2032; crypto-to-AI pivot."),
    N("CleanSpark", "issuer", 0.45, 1.15e9, "Only non-loss-making cluster issuer in the census (+$667M EBITDA)."),
    N("Galaxy Digital", "issuer", 0.55, 1.40e9, "Galaxy Helios I $1.4B Deutsche Bank term loan (AI data center)."),
    N("Nebius", "issuer", 0.70, 2.00e9, "NVIDIA equity investee (~$2B); 20-F earmarks proceeds for NVIDIA Vera Rubin."),
    N("Core Scientific", "issuer", 0.75, 1.00e9, "Being acquired by CoreWeave; $1B term loan."),
    N("Cipher Mining", "issuer", 0.60, 0.50e9, "SoftBank PIPE; Google warrants."),
    N("Bit Digital", "issuer", 0.50, 0.05e9, "Galaxy currency loan (initial $50M draw)."),
    # Supplier-AND-investor (the circular hub)
    N("NVIDIA", "supplier_investor", 0.30, 6.00e9,
      "Dominant GPU SUPPLIER and filing-verified EQUITY INVESTOR in its own customers "
      "(CoreWeave $2B, Nebius ~$2B, Applied Digital). Vendor round-trip / Lucent-Nortel tell."),
    # Offtakers (demand side)
    N("OpenAI", "fragile_offtaker", 0.90, 18.4e9,
      "FRAGILE demand leg: 56% of CoreWeave's named take-or-pay backlog; capital-markets-dependent "
      "(funded by Microsoft $13B + NVIDIA $100B LOI + SoftBank), not payable from operations."),
    N("Microsoft", "durable_offtaker", 0.10, 13.0e9, "Durable hyperscaler (huge FCF); 67% of CoreWeave revenue; $13B into OpenAI."),
    N("Meta", "durable_offtaker", 0.10, 14.2e9, "Durable hyperscaler; $14.2B take-or-pay to CoreWeave through 2031."),
    # Lenders / agents
    N("Morgan Stanley", "lender", 0.40, 4.0e9, "Initial purchaser / agent across cluster notes (Core Scientific TL etc.)."),
    N("Magnetar", "lender", 0.55, 3.0e9, "Private-credit lender to CoreWeave (DDTL structures)."),
    N("Blackstone", "lender", 0.50, 3.0e9, "Private-credit anchor to CoreWeave."),
    N("Wilmington Trust", "lender", 0.30, 2.0e9, "Trustee/collateral agent across the cluster's secured notes."),
    N("Goldman Sachs", "lender", 0.35, 2.0e9, "Agent / initial purchaser (SpaceX bridge, others)."),
    N("Coatue", "lender", 0.45, 1.0e9, "Convertible-note holder (Hut 8)."),
    # Private-credit -> end holders (who bears the downside)
    N("Apollo / Athene", "end_holder", 0.50, 4.0e9, "Insurer / private-credit funder -- routes loss to policyholders."),
    N("Pension funds", "end_holder", 0.40, 3.0e9, "Ultimate downside bearer via private-credit + index exposure."),
    N("Households / index", "end_holder", 0.30, 3.0e9, "Insurance policyholders + retirees + index investors."),
    # Energy chokepoints (the GDS topological finding)
    N("Amazon Energy", "energy_chokepoint", 0.20, 5.0e9, "Top betweenness chokepoint in the AI subgraph -- power is the binding constraint."),
    N("Microsoft Energy", "energy_chokepoint", 0.20, 4.0e9, "2nd betweenness chokepoint -- hyperscaler power procurement."),
    N("Shell Energy", "energy_chokepoint", 0.25, 3.0e9, "Power-market intermediary; structural chokepoint across the full graph."),
]

# ---- EDGES (typed money/value flows; verified amounts) ---------------------------------
E = lambda f, t, ty, usd=None, tier="filing_verified", note="": {  # noqa: E731
    "from": f, "to": t, "type": ty, "usd": usd, "tier": tier, "note": note,
}
edges = [
    # Circular / vendor financing (the round-trip)
    E("NVIDIA", "CoreWeave", "equity_investment", 2.0e9, note="$2B Class A, Jan 2026 (CRWV 10-K)"),
    E("CoreWeave", "NVIDIA", "gpu_purchase", None, note="all GPUs are NVIDIA (CRWV 10-K)"),
    E("NVIDIA", "Nebius", "equity_investment", 2.0e9, note="~$2B Mar 2026; proceeds fund NVIDIA Vera Rubin (NBIS 20-F)"),
    E("Nebius", "NVIDIA", "gpu_purchase", None, note="proceeds earmarked for NVIDIA hardware"),
    E("NVIDIA", "Applied Digital", "equity_investment", None, note="Sep 2024 PIPE (APLD 10-K)"),
    E("NVIDIA", "OpenAI", "framework_commitment", 100.0e9, tier="press_reported",
      note="~$100B LOI, NON-BINDING, $0 funded; absent from NVIDIA 10-Q"),
    # Demand side (take-or-pay backlog)
    E("OpenAI", "CoreWeave", "purchase_commitment", 18.4e9, note="$6.5B + $11.9B take-or-pay (CRWV 10-K)"),
    E("Meta", "CoreWeave", "purchase_commitment", 14.2e9, note="$14.2B through 2031 (CRWV 10-K)"),
    E("Microsoft", "CoreWeave", "customer_revenue", None, note="67% of CoreWeave revenue (CRWV 10-K)"),
    E("Microsoft", "OpenAI", "equity_investment", 13.0e9, note="$13B funding commitment, $11.8B funded (MSFT 10-Q)"),
    # Financing (issuer -> lenders)
    E("CoreWeave", "Morgan Stanley", "lender", None, note="agent/initial purchaser"),
    E("CoreWeave", "Magnetar", "lender", None, note="DDTL private credit"),
    E("CoreWeave", "Blackstone", "lender", None, note="private-credit anchor"),
    E("CoreWeave", "Wilmington Trust", "lender", None, note="trustee/collateral agent"),
    E("TeraWulf", "Morgan Stanley", "lender", None), E("TeraWulf", "Wilmington Trust", "lender", None),
    E("Applied Digital", "Wilmington Trust", "lender", None),
    E("Hut 8", "Coatue", "lender", None), E("Hut 8", "Goldman Sachs", "lender", None),
    E("Galaxy Digital", "Goldman Sachs", "lender", None),
    E("Core Scientific", "Morgan Stanley", "lender", None),
    # Private-credit -> end holders (downside routing)
    E("Magnetar", "Apollo / Athene", "private_credit_funding", None, tier="source_backed",
      note="private-credit funded materially by insurance/pension"),
    E("Blackstone", "Apollo / Athene", "private_credit_funding", None, tier="source_backed"),
    E("Apollo / Athene", "Households / index", "policyholder_exposure", None, tier="source_backed",
      note="loss routes to policyholders/retirees"),
    E("Apollo / Athene", "Pension funds", "policyholder_exposure", None, tier="source_backed"),
    E("Morgan Stanley", "Pension funds", "syndication", None, tier="source_backed"),
    # Energy chokepoints (power is the binding constraint)
    E("Amazon Energy", "CoreWeave", "power_procurement", None, tier="source_backed", note="GDS chokepoint"),
    E("Microsoft Energy", "CoreWeave", "power_procurement", None, tier="source_backed"),
    E("Shell Energy", "TeraWulf", "power_procurement", None, tier="source_backed"),
    E("Amazon Energy", "Applied Digital", "power_procurement", None, tier="source_backed"),
]

# ---- CASCADE (ordered hops with $ accumulation; honest gross-upper-bound label) --------
cascade = {
    "trigger": "OpenAI",
    "trigger_note": "Fragile demand leg withdraws: OpenAI is 56% of CoreWeave's named backlog and is "
    "capital-markets-dependent (not payable from operations).",
    "honest_label": "GROSS UPPER BOUND -- this is CoreWeave's ENTIRE debt, NOT apportioned to OpenAI's "
    "revenue share. Microsoft (~67%) is the larger customer. Read as contagion SURFACE, not expected loss.",
    "hops": [
        {"hop": 1, "nodes": ["CoreWeave"], "usd": cascade0.get("debt_at_risk_usd"),
         "label": "Directly hit: CoreWeave's full debt at risk"},
        {"hop": 2, "nodes": ["Morgan Stanley", "Magnetar", "Blackstone", "Wilmington Trust", "NVIDIA"],
         "label": "Lenders + NVIDIA's $2B equity stake exposed"},
        {"hop": 3, "nodes": ["Apollo / Athene", "Pension funds", "Households / index"],
         "label": "Private-credit funding routes the loss to policyholders / retirees"},
    ],
}

# ---- FRAGILITY (what's cleanly met vs magnitude-only) ----------------------------------
fragility = {
    "met": ["duration: debt to 2030 outlives ~24mo GPU economic life",
            "concentration: a single customer is >50% of revenue (CoreWeave 67%)"],
    "magnitude_only": ["execution/satellite: 'no-change' conflates un-built with already-built (confounded)"],
    "no_binary": ["recourse: mostly parent-equity, not SPV fire-sale",
                  "leveraged-tail size: small share of the universe"],
    "dimensions": frag.get("dimensions", []),
}

# ---- REFI WALL (maturities by year) ----------------------------------------------------
refi = {
    "by_year": (ct.get("maturity_schedule_usd_by_year") or {}),
    "peak_year": ct.get("peak_maturity_year"),
    "near_term_window": ct.get("near_term_pressure_window"),
}

# ---- FIELD: the full extracted contract universe (RAW, unadjudicated) ------------------
# Background layer: every extracted entity and deal from the source corpus, collapsed
# deal-by-deal from obligor -> risk-bearer. Notionals here are the RAW inflated basis
# (the same basis adjudication stripped ~98% from); the viz labels them as such.
CORE_ENTITY_PATTERNS: dict[str, list[str]] = {
    "CoreWeave": ["coreweave"],
    "TeraWulf": ["terawulf"],
    "IREN": ["iren l"],
    "Applied Digital": ["applied digital"],
    "Hut 8": ["hut 8"],
    "MARA Holdings": ["mara holdings", "marathon digital"],
    "CleanSpark": ["cleanspark"],
    "Galaxy Digital": ["galaxy digital", "galaxy helios"],
    "Nebius": ["nebius"],
    "Core Scientific": ["core scientific"],
    "Cipher Mining": ["cipher mining"],
    "Bit Digital": ["bit digital"],
    "NVIDIA": ["nvidia"],
    "OpenAI": ["openai", "open ai"],
    "Microsoft": ["microsoft corp"],
    "Microsoft Energy": ["microsoft energy"],
    "Amazon Energy": ["amazon energy"],
    "Shell Energy": ["shell energy"],
    "Meta": ["meta platforms"],
    "Morgan Stanley": ["morgan stanley"],
    "Magnetar": ["magnetar"],
    "Blackstone": ["blackstone"],
    "Wilmington Trust": ["wilmington trust"],
    "Goldman Sachs": ["goldman sachs"],
    "Coatue": ["coatue"],
    "Apollo / Athene": ["apollo global", "athene"],
}


def _build_field() -> dict[str, Any]:
    import csv
    from collections import defaultdict

    nodes_csv = ROOT / "data/reports/capital_contract_nodes.csv"
    edges_csv = ROOT / "data/reports/capital_contract_edges.csv"
    if not (nodes_csv.exists() and edges_csv.exists()):
        prev = ROOT / "viz" / "graph_data.json"
        if prev.exists():
            old = json.loads(prev.read_text()).get("field")
            if old:
                print("  field: source CSVs absent; preserved existing field layer")
                return old
        print("  field: source CSVs absent; emitting core-only dataset")
        return {}

    ent_name: dict[str, str] = {}
    with nodes_csv.open() as fh:
        for row in csv.DictReader(fh):
            if row["node_type"] == "entity":
                ent_name[row["node_id"]] = " ".join((row.get("name") or "").split())[:90]

    obligors: dict[str, list[tuple[str, float]]] = defaultdict(list)
    bearers: dict[str, list[tuple[str, float]]] = defaultdict(list)
    deal_usd: dict[str, float] = {}
    ent_deals: dict[str, set[str]] = defaultdict(set)
    with edges_csv.open() as fh:
        for row in csv.DictReader(fh):
            rel = row["relationship_type"]
            if rel not in ("OBLIGATED_UNDER_DEAL", "DEAL_RISK_BEARER"):
                continue
            deal = row["deal_id"]
            try:
                usd = float(row["notional_usd"] or 0)
            except ValueError:
                usd = 0.0
            deal_usd[deal] = max(deal_usd.get(deal, 0.0), usd)
            ent = row["source_id"] if rel == "OBLIGATED_UNDER_DEAL" else row["target_id"]
            (obligors if rel == "OBLIGATED_UNDER_DEAL" else bearers)[deal].append((ent, usd))
            if ent in ent_name:
                ent_deals[ent].add(deal)

    pair: dict[tuple[str, str], list[float]] = {}
    all_deals = set(obligors) | set(bearers)
    for deal in all_deals:
        du = deal_usd.get(deal, 0.0)
        obs = sorted(obligors.get(deal, ()), key=lambda x: -x[1])[:4]
        brs = sorted(bearers.get(deal, ()), key=lambda x: -x[1])[:4]
        for s, _su in obs:
            for t, _tu in brs:
                if s == t or s not in ent_name or t not in ent_name:
                    continue
                key = (s, t) if s < t else (t, s)
                acc = pair.setdefault(key, [0.0, 0])
                acc[0] += du
                acc[1] += 1

    lower_names = {eid: name.lower() for eid, name in ent_name.items()}
    ent_usd = {eid: sum(deal_usd.get(d, 0.0) for d in ds) for eid, ds in ent_deals.items()}
    core_of: dict[str, str] = {}
    for core_id, pats in CORE_ENTITY_PATTERNS.items():
        hits = [eid for eid, nm in lower_names.items() if any(p in nm for p in pats)]
        if hits:
            core_of[max(hits, key=lambda eid: ent_usd.get(eid, 0.0))] = core_id

    ids = sorted(ent_name)
    idx = {eid: i for i, eid in enumerate(ids)}
    f_nodes = [
        [ent_name[eid], round(ent_usd.get(eid, 0.0)), len(ent_deals.get(eid, ())),
         core_of.get(eid, 0)]
        for eid in ids
    ]
    f_links = [[idx[a], idx[b], round(v[0]), v[1]] for (a, b), v in pair.items()]
    return {
        "entities": len(ids),
        "deals": len(all_deals),
        "matched_core": len(core_of),
        "nodes": f_nodes,
        "links": f_links,
        "note": (
            "Background field = the FULL extracted contract graph from the source corpus: "
            f"{len(ids):,} entities, {len(all_deals):,} deals collapsed obligor->risk-bearer "
            "(top-4 parties per side). Field notionals are RAW and UNADJUDICATED -- the same "
            "inflated basis the adjudication stripped ~98% from. Read field sizes as claimed "
            "paper, not verified debt; the bright core is what survived evidence-gating."
        ),
    }


out = {
    "meta": meta,
    "nodes": nodes,
    "edges": edges,
    "cascade": cascade,
    "fragility": fragility,
    "refi_wall": refi,
    "field": _build_field(),
    "chokepoints": {
        "power": ["Amazon Energy", "Microsoft Energy", "Shell Energy"],
        "financing": ["CoreWeave"],
    },
    "legend": {
        "node_types": {
            "issuer": "financed AI-compute issuer (the cluster)",
            "supplier_investor": "NVIDIA -- supplier AND equity investor (circular)",
            "fragile_offtaker": "capital-markets-dependent demand (OpenAI)",
            "durable_offtaker": "hyperscaler demand (durable FCF)",
            "lender": "lender / agent / trustee",
            "end_holder": "ultimate downside bearer (insurer/pension/household)",
            "energy_chokepoint": "power-procurement intermediary (GDS structural chokepoint)",
        },
        "fragility": "node color: green(safe)->red(fragile); size: exposure/committed debt",
        "edge_tiers": {"filing_verified": "solid", "press_reported": "dashed (NOT binding)",
                       "source_backed": "solid (aggregate)"},
    },
}

(ROOT / "viz" / "graph_data.json").write_text(json.dumps(out, separators=(",", ":")))
print(f"wrote viz/graph_data.json from {report_name}")
fld = out["field"] or {}
print(f"  core nodes={len(nodes)} edges={len(edges)} | field entities={fld.get('entities', 0)} "
      f"deals={fld.get('deals', 0)} links={len(fld.get('links') or [])} "
      f"core-matched={fld.get('matched_core', 0)}")
print(f"  core_conf={meta['core_confidence']} eco_conf={meta['ecosystem_confidence']} "
      f"| cascade=${(meta['cascade_debt_at_risk_usd'] or 0)/1e9:.1f}B")
print(f"  committed core=${(meta['committed_core_usd'] or 0)/1e9:.1f}B incl=${(meta['committed_incl_infra_usd'] or 0)/1e9:.1f}B "
      f"over-count={meta['over_count_removed_pct']}% fragility_met={meta['fragility_conditions_met']}")
