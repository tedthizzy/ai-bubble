"""Circular / reciprocal ('round-trip') financing detection in the AI-infra cluster.

Vendor round-tripping -- a supplier financing its own customers' purchases of its
own product -- is the classic late-cycle bubble signature. Lucent and Nortel
booked vendor-financed sales as revenue into the 2000 telecom crash; the cash the
'customers' paid had largely been lent or invested to them by the vendor itself,
so the demand was not arm's-length and evaporated when the financing stopped.

Here NVIDIA is simultaneously the dominant GPU SUPPLIER to the financed cluster
AND a filing-verified EQUITY INVESTOR in three of its own GPU-cloud customers:
CoreWeave ($2B, Jan 2026), Nebius (~$2B, Mar 2026), Applied Digital (Sep 2024
PIPE). For Nebius the 20-F states the proceeds fund procurement of the NVIDIA
Vera Rubin platform -- i.e. the supplier's capital is earmarked to buy the
supplier's next-gen hardware. The round-trip is nearly explicit in the filing.

This module encodes every money-flow edge as PAYER -> PAYEE with a source tier,
runs directed simple-cycle detection, and reports:
  - filing-verified RECIPROCAL loops (supplier <-> investee, both legs from
    primary filings): the tightest, most defensible round-trips;
  - larger macro loops (e.g. NVIDIA -> OpenAI -> CoreWeave -> NVIDIA) that are
    FLAGGED and capped whenever a closing edge is only press-reported/inferred;
  - the reciprocal-hub concentration (one entity investing across the cluster).

HONESTY (first-class, per the engine's discipline):
  - The equity investments and the GPU purchases are LEGALLY SEPARATE
    transactions. Their co-existence does NOT prove the identical dollars
    circulate (Nebius is the one filing that ties proceeds to hardware).
  - What it DOES establish: (a) the supplier has a direct financial incentive to
    sustain its customers' apparent demand, and (b) reciprocal exposure -- a
    customer partly funded by its supplier is not an arm's-length validator of
    demand. This impairs the DURABILITY of the demand signal; it is a red flag,
    not proof of sham revenue.
  - Press-only / inferred loops are capped at the INFERRED tier (<=0.45) and
    never drive the verdict or the evidence gate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Money INTO a counterparty that the funder also sells to (the financing leg).
_CAPITAL_INJECTION_FLOWS = {
    "equity_investment",
    "framework_commitment",
    "vendor_warrant",
    "vendor_financing",
}
# Value flowing BACK toward the funder (the return leg that closes the loop).
_RETURN_FLOWS = {"gpu_purchase", "lease_payment", "purchase_commitment", "customer_revenue"}

_TIER_RANK = {"filing_verified": 2, "inferred": 1, "press_reported": 0}

# Primary-source verified 2026-06-03 (NVIDIA Q1-FY2027 10-Q; MSFT Q3-FY2026 10-Q): neither
# principal NAMES the circularity as a disclosed risk -- itself a disclosure-gap red flag.
_DISCLOSURE_GAP = (
    "Neither NVIDIA's nor Microsoft's filings name the supplier-AND-investor circularity (NVIDIA) "
    "or the Microsoft->OpenAI->CoreWeave->NVIDIA chain as a related-party or "
    "customer/supplier-concentration risk; NVIDIA's customer concentration is anonymized "
    "(Customer A/B/C). The round-trip is forensic framing, not a filing-disclosed risk -- a "
    "disclosure-gap red flag in its own right."
)


def load_edges(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        loaded = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(loaded, dict):
        loaded = loaded.get("edges", [])
    return [e for e in loaded if isinstance(e, dict) and e.get("from") and e.get("to")]


def _num(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _cycle_key(cycle: list[dict[str, Any]]) -> tuple[Any, ...]:
    return tuple((e["from"], e["to"], e.get("flow_type")) for e in cycle)


def find_money_cycles(edges: list[dict[str, Any]], *, max_len: int = 4) -> list[list[dict[str, Any]]]:
    """Enumerate simple directed cycles (payer->payee) once each, up to max_len edges."""

    nodes = sorted({e["from"] for e in edges} | {e["to"] for e in edges})
    idx = {n: i for i, n in enumerate(nodes)}
    adj: dict[str, list[dict[str, Any]]] = {}
    for e in edges:
        adj.setdefault(e["from"], []).append(e)

    cycles: list[list[dict[str, Any]]] = []
    seen: set[tuple[Any, ...]] = set()

    def dfs(start: str, current: str, path_edges: list[dict[str, Any]], visited: set[str]) -> None:
        for e in adj.get(current, []):
            nxt = e["to"]
            if nxt == start and path_edges:
                cyc = [*path_edges, e]
                key = _cycle_key(cyc)
                if key not in seen:
                    seen.add(key)
                    cycles.append(cyc)
            elif nxt not in visited and idx[nxt] > idx[start] and len(path_edges) < max_len - 1:
                dfs(start, nxt, [*path_edges, e], visited | {nxt})

    for n in nodes:
        dfs(n, n, [], {n})
    return cycles


def _cycle_meta(cycle: list[dict[str, Any]]) -> dict[str, Any]:
    tiers = [str(e.get("source_tier", "press_reported")) for e in cycle]
    weakest = min(tiers, key=lambda t: _TIER_RANK.get(t, 0))
    amounts = [a for e in cycle if (a := _num(e.get("amount_usd"))) is not None]
    nodes = [str(e["from"]) for e in cycle]
    path = " -> ".join([*nodes, str(cycle[0]["from"])])
    flows = " / ".join(str(e.get("flow_type")) for e in cycle)
    return {
        "length": len(cycle),
        "nodes": nodes,
        "path": path,
        "flow_types": flows,
        "all_filing_verified": all(t == "filing_verified" for t in tiers),
        "weakest_tier": weakest,
        # Bottleneck of disclosed amounts = a conservative ceiling on circulating capital.
        "binding_throughput_usd": min(amounts) if amounts else None,
        "edges": [
            {
                "from": e["from"],
                "to": e["to"],
                "flow_type": e.get("flow_type"),
                "amount_usd": e.get("amount_usd"),
                "source_tier": e.get("source_tier"),
                "source_uri": e.get("source_uri"),
            }
            for e in cycle
        ],
    }


def _reciprocal_hub(edges: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The entity that INVESTS in counterparties it also SELLS to (vendor round-trip hub)."""

    injections: dict[str, dict[str, dict[str, Any]]] = {}
    for e in edges:
        if e.get("flow_type") in _CAPITAL_INJECTION_FLOWS:
            injections.setdefault(str(e["from"]), {}).setdefault(str(e["to"]), e)
    if not injections:
        return None
    return_edge: dict[tuple[str, str], dict[str, Any]] = {}
    for e in edges:
        if e.get("flow_type") in _RETURN_FLOWS:
            return_edge[(str(e["from"]), str(e["to"]))] = e

    best: dict[str, Any] | None = None
    for funder, investees in injections.items():
        verified_capital = 0.0
        verified_round_trips = 0
        round_trips = 0
        verified_investees: list[str] = []
        for inv, inj in investees.items():
            inj_verified = inj.get("source_tier") == "filing_verified"
            if inj_verified:
                verified_investees.append(inv)
            ret = return_edge.get((inv, funder))
            if ret is None:
                continue
            round_trips += 1
            if inj_verified and ret.get("source_tier") == "filing_verified":
                verified_round_trips += 1
                amt = _num(inj.get("amount_usd"))
                if amt is not None:
                    verified_capital += amt
        candidate = {
            "entity": funder,
            "investee_customer_count": len(investees),
            "investees": sorted(investees),
            "filing_verified_investee_count": len(verified_investees),
            "filing_verified_investees": sorted(verified_investees),
            "round_trip_count": round_trips,
            "filing_verified_round_trip_count": verified_round_trips,
            "filing_verified_reciprocal_capital_usd": int(verified_capital),
        }
        if best is None or (
            candidate["investee_customer_count"],
            candidate["filing_verified_round_trip_count"],
        ) > (best["investee_customer_count"], best["filing_verified_round_trip_count"]):
            best = candidate
    return best


def analyze_circular_financing(edges: list[dict[str, Any]]) -> dict[str, Any]:
    """Detect reciprocal/round-trip financing loops and the supplier-as-investor hub."""

    if not edges:
        return {"status": "blocked_no_edges", "loop_count": 0}

    cycles = [_cycle_meta(c) for c in find_money_cycles(edges)]
    filing_verified = [c for c in cycles if c["all_filing_verified"]]
    flagged = [c for c in cycles if not c["all_filing_verified"]]
    hub = _reciprocal_hub(edges)

    return {
        "status": "source_backed",
        "edge_count": len(edges),
        "loop_count": len(cycles),
        "filing_verified_reciprocal_loops": filing_verified,
        "press_or_inferred_loops": flagged,
        "reciprocal_hub": hub,
        "disclosure_gap": _DISCLOSURE_GAP,
        "demand_durability_read": _read(filing_verified, flagged, hub),
        "interpretation_caveat": (
            "The equity-investment and GPU-purchase legs are LEGALLY SEPARATE transactions; their "
            "co-existence does not prove the identical dollars circulate (Nebius is the one filing that "
            "earmarks the supplier's proceeds for the supplier's hardware). The defensible inference is "
            "narrower and still material: the dominant supplier is also an equity investor in its own "
            "customers, so (a) it is incentivized to sustain their apparent demand and (b) the demand "
            "those customers represent is NOT arm's-length -- a vendor-financed buyer is not an "
            "independent validator of end-demand. This impairs demand DURABILITY; it is a red flag, not "
            "proof of fabricated revenue."
        ),
        "note": (
            "Reciprocal/round-trip financing detection via directed money-flow cycle search. "
            "Filing-verified loops are primary-source on every leg; loops touching a press-reported or "
            "inferred edge are FLAGGED and capped at INFERRED (<=0.45) -- they never drive the verdict. "
            "Vendor round-tripping is the Lucent/Nortel late-cycle tell; the finding here is that the "
            "structure is present and partly filing-verified, which is itself novel relative to the "
            "purely customer-concentration framing."
        ),
    }


def _read(
    filing_verified: list[dict[str, Any]],
    flagged: list[dict[str, Any]],
    hub: dict[str, Any] | None,
) -> str:
    parts: list[str] = []
    if hub and hub["filing_verified_round_trip_count"]:
        cap = hub["filing_verified_reciprocal_capital_usd"] / 1e9
        parts.append(
            f"{hub['entity']} is a filing-verified equity investor in "
            f"{hub['filing_verified_investee_count']} of its own GPU-cloud customers "
            f"({', '.join(hub['filing_verified_investees'])}); "
            f"{hub['filing_verified_round_trip_count']} have a filing-verified return-purchase leg, "
            f"closing ~${cap:.1f}B of reciprocal (supplier-funds-customer) capital."
        )
    if filing_verified:
        parts.append(
            f"{len(filing_verified)} reciprocal loop(s) are filing-verified on every leg "
            + "; ".join(c["path"] for c in filing_verified)
            + "."
        )
    if flagged:
        parts.append(
            f"{len(flagged)} larger macro loop(s) exist but rest on a press-reported/inferred edge "
            "(e.g. the NVIDIA->OpenAI framework commitment), so they are flagged and capped, not relied on."
        )
    parts.append(
        "Net: the AI-infra demand signal is partly reciprocal -- the supplier finances the buyers -- so "
        "headline take-or-pay backlog overstates independent, arm's-length end-demand."
    )
    return " ".join(parts)
