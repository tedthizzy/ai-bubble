"""AI-direct contagion hubs from shared counterparties.

A shock to a counterparty SHARED across many issuers (the GPU supplier, an anchor
customer, a common lender) propagates to all of them -- that is the contagion
path. This aggregates the per-issuer counterparty extraction into shared hubs
ranked by how many distinct issuers they touch, with the source-backed quotes
kept so each edge is auditable.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_CATEGORIES = {
    "customer": "top_customers",
    "gpu_supplier": "gpu_suppliers",
    "lender_or_agent": "lenders_or_agents",
    "strategic_investor": "strategic_investors",
}

# Canonical names for the high-frequency hubs (substring match on the lowered name).
_CANONICAL = {
    "nvidia": "NVIDIA",
    "microsoft": "Microsoft",
    "openai": "OpenAI",
    "google": "Google/Alphabet",
    "alphabet": "Google/Alphabet",
    "amazon": "Amazon/AWS",
    "meta": "Meta",
    "oracle": "Oracle",
    "dell": "Dell",
    "supermicro": "Supermicro",
    "super micro": "Supermicro",
    "fluidstack": "Fluidstack",
    "jpmorgan": "JPMorgan",
    "j.p. morgan": "JPMorgan",
    "morgan stanley": "Morgan Stanley",
    "goldman": "Goldman Sachs",
    "wilmington trust": "Wilmington Trust",
    "u.s. bank": "U.S. Bank",
    "us bank": "U.S. Bank",
    "u. s. bank": "U.S. Bank",
    "mufg": "MUFG",
    "cantor": "Cantor Fitzgerald",
    "coinbase": "Coinbase",
    "bnp paribas": "BNP Paribas",
    "coatue": "Coatue",
    "blackstone": "Blackstone",
    "magnetar": "Magnetar",
    "coreweave": "CoreWeave",
}

_SUFFIX_RE = re.compile(
    r"\b(corporation|incorporated|inc|corp|company|co|llc|l\.?p\.?|ltd|plc|n\.?a\.?|"
    r"national association|holdings|group|securities|capital|bank|trust)\b",
    re.I,
)


def load_contagion_edges(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        loaded = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    return [e for e in loaded if isinstance(e, dict)] if isinstance(loaded, list) else []


def _canonical_counterparty(name: str) -> str:
    lowered = (name or "").strip().lower()
    if not lowered:
        return ""
    for marker, canonical in _CANONICAL.items():
        if marker in lowered:
            return canonical
    stripped = _SUFFIX_RE.sub("", lowered)
    stripped = re.sub(r"[^a-z0-9 ]+", " ", stripped).strip()
    return " ".join(w.capitalize() for w in stripped.split()) if stripped else ""


def compute_contagion_hubs(edges: list[dict[str, Any]], *, min_issuers: int = 2) -> dict[str, Any]:
    """Rank counterparties by the number of distinct AI-direct issuers they touch."""

    if not edges:
        return {"status": "blocked_no_contagion_edges", "issuer_count": 0}

    # (category, canonical) -> {issuers: set, example_quote, concentration}
    nodes: dict[tuple[str, str], dict[str, Any]] = {}
    issuers_seen: set[str] = set()
    for edge in edges:
        issuer = str(edge.get("entity") or "")
        if not issuer:
            continue
        issuers_seen.add(issuer)
        for category, key in _CATEGORIES.items():
            for cp in edge.get(key) or []:
                if not isinstance(cp, dict):
                    continue
                canonical = _canonical_counterparty(str(cp.get("name") or ""))
                if not canonical:
                    continue
                node = nodes.setdefault(
                    (category, canonical),
                    {"issuers": set(), "example_quote": "", "max_concentration_pct": None},
                )
                node["issuers"].add(issuer)
                if not node["example_quote"] and cp.get("quote"):
                    node["example_quote"] = str(cp.get("quote"))[:200]
                pct = cp.get("revenue_concentration_pct")
                if isinstance(pct, (int, float)) and not isinstance(pct, bool):
                    prev = node["max_concentration_pct"]
                    node["max_concentration_pct"] = max(prev, pct) if prev is not None else pct

    hubs = [
        {
            "category": category,
            "counterparty": canonical,
            "issuer_count": len(data["issuers"]),
            "issuers": sorted(s.split(",")[0].split("(")[0].strip() for s in data["issuers"]),
            "max_revenue_concentration_pct": data["max_concentration_pct"],
            "example_quote": data["example_quote"],
        }
        for (category, canonical), data in nodes.items()
        if len(data["issuers"]) >= min_issuers
    ]
    hubs.sort(key=lambda h: (h["issuer_count"], h["counterparty"]), reverse=True)

    by_category: dict[str, list[dict[str, Any]]] = {}
    for hub in hubs:
        by_category.setdefault(hub["category"], []).append(hub)

    return {
        "status": "source_backed",
        "issuer_count": len(issuers_seen),
        "shared_hub_count": len(hubs),
        "top_contagion_hubs": hubs[:15],
        "hubs_by_category": by_category,
        "note": (
            "Contagion hubs = counterparties shared across >=2 AI-direct issuers. A shock to a "
            "high-issuer-count hub (e.g. the common GPU supplier, an anchor customer, a shared "
            "lender) propagates across the cluster simultaneously -- the single-points-of-failure "
            "that make idiosyncratic issuer risk systemic for the financed AI-direct core."
        ),
    }
