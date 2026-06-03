"""Demand-funding durability: is the financed cluster's contracted demand payable from
operations, or does it depend on the offtaker continuing to raise external capital?

The bull case for the financed AI-cloud cluster is its contracted take-or-pay
backlog (OpenAI ~$18.4B and Meta ~$14.2B to CoreWeave, Microsoft ~67% of revenue).
But a take-or-pay is only as good as the offtaker's ability to PAY it. The
first-principles test -- not a borrowed label -- is funding self-sufficiency:

  - DURABLE (self_funding): the commitment is small relative to the offtaker's
    operating cash flow, so it is payable from operations through a downturn.
    The hyperscalers (Microsoft, Meta) generate tens of $B/yr of operating cash;
    a few-$B/yr commitment is trivially covered.
  - FRAGILE (capital_markets_dependent): the commitment exceeds what the offtaker
    can fund from operations, so honoring it depends on continued external
    fundraising. OpenAI is pre-profitability (Microsoft carries it under the
    equity method / HLBV as a funding commitment with revenue-sharing) and is
    capitalized by Microsoft ($13B), an NVIDIA letter of intent (non-binding),
    and SoftBank; its multi-year compute commitments far exceed its revenue.

The decomposition then asks: what SHARE of the cluster's named contracted backlog
rests on capital_markets_dependent offtakers? When that share is a majority, the
"contracted demand proves durability" argument is undercut -- the largest slice of
demand is itself a bet on open capital markets, and (via the circular-financing
loop) is partly funded by the cluster's own GPU supplier.

Honesty: the dollar commitments are filing-verified; the funding-class is a
first-principles JUDGMENT backed by the cited filing where one exists. The
hyperscaler slices ARE durable -- the finding is the BIFURCATION, not blanket
fragility. Capped as a corroborating decomposition; it never drives the gate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DURABLE = "self_funding"
_FRAGILE = "capital_markets_dependent"


def _num(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def load_offtaker_funding_profile(path: str | Path) -> dict[str, dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        loaded = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    return loaded.get("offtakers", {}) or {} if isinstance(loaded, dict) else {}


def assess_demand_funding_durability(
    commitments: list[dict[str, Any]],
    funding_profile: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Decompose named contracted backlog by offtaker funding self-sufficiency."""

    named = [c for c in commitments if _num(c.get("amount_usd")) is not None]
    if not named:
        return {"status": "blocked_no_commitments", "total_named_commitment_usd": 0}

    profile = funding_profile or {}
    per_offtaker: list[dict[str, Any]] = []
    by_class: dict[str, float] = {}
    for c in named:
        offtaker = str(c.get("offtaker") or "")
        amount = _num(c.get("amount_usd")) or 0.0
        prof = profile.get(offtaker) or {}
        cls = str(prof.get("funding_class") or "unknown")
        by_class[cls] = by_class.get(cls, 0.0) + amount
        per_offtaker.append(
            {
                "offtaker": offtaker,
                "counterparty": c.get("counterparty"),
                "amount_usd": amount,
                "funding_class": cls,
                "basis": prof.get("basis"),
                "evidence_source_uri": prof.get("evidence_source_uri"),
            }
        )

    total = sum(by_class.values())
    fragile = by_class.get(_FRAGILE, 0.0)
    durable = by_class.get(_DURABLE, 0.0)
    unknown = by_class.get("unknown", 0.0)
    classified = fragile + durable
    # Pct is over the CLASSIFIED total (durable + fragile), so 'unknown' does not dilute the signal.
    fragile_pct = round(100 * fragile / classified, 1) if classified else None

    return {
        "status": "source_backed",
        "total_named_commitment_usd": int(total),
        "by_class_usd": {k: int(v) for k, v in by_class.items()},
        "capital_markets_dependent_usd": int(fragile),
        "self_funding_usd": int(durable),
        "unknown_class_usd": int(unknown),
        "classified_named_commitment_usd": int(classified),
        "capital_markets_dependent_pct": fragile_pct,
        "majority_of_named_backlog_capital_markets_dependent": bool(
            fragile_pct is not None and fragile_pct > 50.0
        ),
        "per_offtaker": sorted(per_offtaker, key=lambda o: o["amount_usd"], reverse=True),
        "durability_read": _read(fragile, durable, fragile_pct, per_offtaker),
        "caveat": (
            "Dollar commitments are filing-verified; the funding-class is a FIRST-PRINCIPLES judgment "
            "(payable-from-operations vs requires-external-capital) backed by the cited filing where one "
            "exists. The hyperscaler slices (Microsoft, Meta) are genuinely durable -- the finding is the "
            "BIFURCATION of demand, not blanket fragility. SCOPE: the percentage is of the NAMED, "
            "classified backlog only (OpenAI + Meta dollar commitments); Microsoft's commitment is sized "
            "only as ~67% of CoreWeave revenue (no multi-year dollar figure disclosed) and is durable, so "
            "the fragile share of TOTAL contracted demand is LOWER than the named-slice figure -- the "
            "precise claim is 'a majority of the NAMED take-or-pay backlog', not of all demand. Capped as "
            "a corroborating decomposition; never drives the evidence gate."
        ),
    }


def _read(
    fragile: float,
    durable: float,
    fragile_pct: float | None,
    per_offtaker: list[dict[str, Any]],
) -> str:
    fragile_names = sorted({o["offtaker"] for o in per_offtaker if o["funding_class"] == _FRAGILE})
    if fragile_pct is None:
        return "No classified named commitments to decompose."
    lead = (
        f"{fragile_pct}% of the cluster's CLASSIFIED named take-or-pay backlog (~${fragile / 1e9:.1f}B of "
        f"${(fragile + durable) / 1e9:.1f}B) rests on capital_markets_dependent offtaker(s) "
        f"({', '.join(fragile_names)}) -- demand that is NOT payable from the offtaker's operations and "
        "depends on continued external fundraising."
    )
    if fragile_pct > 50.0:
        lead += (
            " A MAJORITY of the named contracted demand is therefore a bet on open capital markets, not on "
            "end-customer operating cash flow -- and (via the circular-financing loop) that offtaker is "
            "partly funded by the cluster's own GPU supplier and largest current customer. The hyperscaler "
            "slices remain durable; the contracted-backlog 'proof of demand' is bifurcated, and its larger "
            "half is the fragile, circular one."
        )
    return lead
