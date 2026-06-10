"""Risk-bearer role taxonomy + classifier (root cause 3 fixture/checker).

The contagion graph and the ``who_bears_downside`` ranking credit an entity with
borne downside for appearing in *any* counterparty role. But only **principals**
(lender / guarantor / insurer / noteholder / bondholder / lessor) actually bear
credit downside; **intermediaries** (administrative / collateral / facility agents,
trustees, arrangers, underwriters) bear little or none, and **artifacts** (statute
names, clause fragments, bare role phrases) are not entities at all.

``classify_risk_bearer`` returns the taxonomy bucket for an entity given its
aggregate roles and name. ``summarize_risk_bearer_quality`` scans a list of ranked
bearers and quantifies how much exposure is mis-attributed to intermediaries /
artifacts. Pure functions; the production graph/attribution logic is Codex's.
"""

from __future__ import annotations

import re
from typing import Any

# Roles that genuinely bear credit/default downside.
RISK_PRINCIPAL_ROLES = frozenset(
    {"lender", "guarantor", "insurer", "noteholder", "bondholder", "lessor"}
)
# Roles that arrange/administer/hold-in-trust — little or no credit risk.
INTERMEDIARY_ROLES = frozenset(
    {
        "administrative_agent",
        "collateral_agent",
        "syndication_agent",
        "facility_agent",
        "paying_agent",
        "trustee",
        "indenture_trustee",
        "arranger",
        "bookrunner",
        "placement_agent",
        "underwriter",
    }
)
# Tags too generic to establish a principal on their own.
AMBIGUOUS_ROLES = frozenset({"financier"})

# Name signatures that are statutes / clause fragments / bare role phrases, never a
# real counterparty entity. Matched as lowercased substrings.
ARTIFACT_NAME_MARKERS = (
    "trust indenture act",
    "securities act",
    "securities exchange act",
    "investment company act",
    "internal revenue code",
    "dodd-frank",
    "sarbanes",
    "u.s.c",
    "et seq",
    "the lenders",
    "lenders party",
    "the borrower",
    "the guarantor",
    "the trustee",
    "the issuer",
    "the company",
    "party hereto",
    "party thereto",
    "whereas",
    "defined herein",
)


# Real institutional-entity patterns that must NOT be flagged as artifacts even though
# they contain a role word (e.g. "The Trustees of the University of …" is a real
# endowment, not the "trustee" role).
INSTITUTIONAL_ALLOW_MARKERS = (
    "trustees of the university",
    "trustees of the",
    "university of",
    "regents of",
    "board of trustees",
    "board of regents",
)


def _norm(name: str) -> str:
    return re.sub(r"[-_]+", " ", (name or "").lower()).strip()


def is_artifact_name(name: str) -> bool:
    n = _norm(name)
    if any(marker in n for marker in INSTITUTIONAL_ALLOW_MARKERS):
        return False
    if re.search(r"^on [a-z]+ \d{1,2}, \d{4},\s+the\b", n):
        return True
    return any(marker in n for marker in ARTIFACT_NAME_MARKERS)


def classify_risk_bearer(roles: list[str] | set[str], name: str = "") -> dict[str, Any]:
    """Classify an entity as ``risk_principal`` / ``intermediary`` / ``artifact`` / ``unknown``.

    ``is_risk_principal`` is True only for a real entity holding at least one
    risk-principal role. An entity that also holds intermediary roles is flagged
    ``needs_role_weighting`` (its full-notional attribution over-counts the deals
    where it is merely an agent).
    """

    rset = {str(r).strip().lower() for r in roles if str(r).strip()}
    if is_artifact_name(name):
        return {"bucket": "artifact", "is_risk_principal": False, "needs_role_weighting": False}
    principal_roles = rset & RISK_PRINCIPAL_ROLES
    if principal_roles:
        return {
            "bucket": "risk_principal",
            "is_risk_principal": True,
            "needs_role_weighting": bool(rset & INTERMEDIARY_ROLES),
        }
    if rset and rset <= (INTERMEDIARY_ROLES | AMBIGUOUS_ROLES):
        return {"bucket": "intermediary", "is_risk_principal": False, "needs_role_weighting": False}
    return {"bucket": "unknown", "is_risk_principal": False, "needs_role_weighting": False}


def summarize_graph_artifact_edges(edges: list[dict[str, Any]]) -> dict[str, Any]:
    """Count contagion-graph edges whose source/target node is a statute/role-phrase artifact.

    Each edge is a dict with ``source_id``/``target_id`` (+ optional ``notional_usd``).
    These are spurious counterparty nodes (root cause 3) that should be filtered or
    re-resolved to a real named entity before the graph is trusted.
    """

    def _edge_amount(edge: dict[str, Any]) -> float:
        value = edge.get("notional_usd")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    artifact_edges = [
        edge
        for edge in edges
        if is_artifact_name(str(edge.get("target_id") or ""))
        or is_artifact_name(str(edge.get("source_id") or ""))
    ]
    return {
        "total_edges": len(edges),
        "artifact_edges": len(artifact_edges),
        "artifact_edge_notional_usd": round(sum(_edge_amount(e) for e in artifact_edges), 2),
    }


def _amount(bearer: dict[str, Any]) -> float:
    for key in ("exposure_usd", "notional_usd", "amount_usd"):
        value = bearer.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return 0.0


def summarize_risk_bearer_quality(bearers: list[dict[str, Any]]) -> dict[str, Any]:
    """Quantify mis-attributed exposure in a ranked risk-bearer list.

    Each bearer is a dict with ``roles`` (list) + a name (``name``/``entity_ref``) +
    an amount (``exposure_usd``/``notional_usd``/``amount_usd``).
    """

    totals: dict[str, float] = {
        "risk_principal": 0.0,
        "intermediary": 0.0,
        "artifact": 0.0,
        "unknown": 0.0,
    }
    counts: dict[str, int] = {"risk_principal": 0, "intermediary": 0, "artifact": 0, "unknown": 0}
    needs_weighting_usd = 0.0
    for bearer in bearers:
        name = str(bearer.get("name") or bearer.get("entity_ref") or bearer.get("entity") or "")
        result = classify_risk_bearer(bearer.get("roles") or [], name)
        bucket = result["bucket"]
        amount = _amount(bearer)
        totals[bucket] += amount
        counts[bucket] += 1
        if result["needs_role_weighting"]:
            needs_weighting_usd += amount
    misattributed = totals["intermediary"] + totals["artifact"]
    return {
        "counts": counts,
        "exposure_by_bucket_usd": {k: round(v, 2) for k, v in totals.items()},
        "misattributed_exposure_usd": round(misattributed, 2),
        "risk_principal_needs_role_weighting_usd": round(needs_weighting_usd, 2),
    }
