"""Inject the source-backed AI-direct cluster into the capital-exposure graph.

The production capital-exposure graph is built from the broad acquired deal
corpus, whose AI-infrastructure mass is small (~$5B Equinix of a ~$408B graph)
because the financed neocloud cluster's debt lives in per-issuer 10-K/10-Q
disclosures, not the bulk deal feed. This module turns the two
adversarially-verified cluster fixtures -- the debt census (per-issuer total
debt + facilities) and the contagion edges (per-issuer lenders/agents, GPU
suppliers, strategic investors, top customers) -- into source-backed ``Deal``
objects so the cluster, its lenders, its single GPU supplier (NVIDIA), and its
anchor customers (Microsoft, OpenAI) all become nodes/edges in the SAME graph as
the rest of the ecosystem. Multi-hop contagion and shared-counterparty hub
detection then run over the cluster, not just the Equinix mass.

Conservatism / honesty:
- Each issuer's total cluster debt is attributed to ONE notional-bearing debt
  edge (issuer -> lead arranger/lender); the remaining lenders, the GPU supplier,
  the strategic investor, and the customers are zero-notional TOPOLOGY edges, so
  the dollar exposure is counted once (no syndicate double-count). Per-lender
  syndicate allocations are not disclosed, so we do not invent them.
- Every Deal carries the fixture's real SEC ``source_uri`` as provenance.
- AI-infra keywords are placed in the title/key_terms so the graph's existing
  relevance tagger marks these edges ai_infra_relevant (they are, by definition).
"""

from __future__ import annotations

import re
from typing import Any

from bubble.analysis.contagion_hubs import _canonical_counterparty
from bubble.models.base import (
    DealType,
    HumanReviewStatus,
    Provenance,
    SourceType,
)
from bubble.models.deal import Deal


def _canon(name: str) -> str:
    """Canonicalize a counterparty name so name variants don't fragment hubs.

    Reuses the contagion-hub canonical map (NVIDIA / Goldman / Morgan Stanley /
    MUFG / Microsoft / ...) and falls back to the original name when unmapped, so
    "Goldman Sachs Bank USA" and "Goldman Sachs & Co. LLC" collapse to one node.
    """

    return _canonical_counterparty(name) or str(name or "").strip()

# Funding language => the named party is a risk-bearing lender (edge target),
# not merely an administrative agent (which alone produces no exposure edge).
_LENDER_ROLE = re.compile(r"lend|arrang|bookrun|financ|noteholder|purchaser|credit", re.I)
_PURE_AGENT_ROLE = re.compile(r"agent|trustee|custodian", re.I)


def _short_name(raw: str) -> str:
    """Normalize an issuer label to a stable short name for cross-fixture join."""

    text = str(raw or "")
    text = text.split("(", 1)[0]
    text = text.split("—", 1)[0]  # em-dash CIK suffix
    text = text.split(",", 1)[0]
    return text.strip()


def _provenance(source_uri: str, quote: str) -> Provenance:
    return Provenance(
        source_uri=source_uri or "sec:ai_direct_cluster",
        source_type=SourceType.SEC_EDGAR,
        confidence=0.85,
        human_review_status=HumanReviewStatus.PENDING,
        content_hash=Provenance.compute_content_hash(quote or source_uri or "ai_direct"),
    )


def _num(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _parse_amount_usd(text: str) -> float | None:
    """Best-effort '$2 billion' / '$6.5 billion' parse; None if not confident."""

    m = re.search(r"\$\s?([0-9]+(?:\.[0-9]+)?)\s*(billion|bn|million|mm|m)\b", str(text), re.I)
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2).lower()
    return value * (1e9 if unit in {"billion", "bn"} else 1e6)


def _index_contagion(contagion_records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {_short_name(r.get("entity", "")): r for r in contagion_records if r.get("entity")}


def build_ai_direct_deals(
    census_records: list[dict[str, Any]],
    contagion_records: list[dict[str, Any]],
) -> list[Deal]:
    """Build source-backed cluster Deals from the census + contagion fixtures."""

    contagion_by_name = _index_contagion(contagion_records)
    deals: list[Deal] = []

    for census in census_records:
        stack = census.get("stack") or census
        issuer = _short_name(stack.get("entity", ""))
        if not issuer:
            continue
        total_debt = _num(stack.get("total_debt_usd")) or 0.0
        contagion = contagion_by_name.get(issuer, {})

        deals.extend(_debt_deals(issuer, total_debt, contagion))
        deals.extend(_supplier_deals(issuer, contagion))
        deals.extend(_investor_deals(issuer, contagion))
        deals.extend(_customer_deals(issuer, contagion))

    return deals


def _debt_deals(issuer: str, total_debt: float, contagion: dict[str, Any]) -> list[Deal]:
    lenders_or_agents = list(contagion.get("lenders_or_agents") or [])
    # Lead funding party (risk-bearer) carries the issuer's total cluster debt.
    funders = [
        la
        for la in lenders_or_agents
        if _LENDER_ROLE.search(str(la.get("role") or "")) or not _PURE_AGENT_ROLE.search(
            str(la.get("role") or "")
        )
    ]
    if not funders and lenders_or_agents:
        funders = lenders_or_agents[:1]  # fall back to the named agent as lead

    out: list[Deal] = []
    title = f"{issuer} AI/GPU data-center compute debt (cluster census)"
    for idx, la in enumerate(funders):
        name = _canon(str(la.get("name") or "").strip())
        if not name:
            continue
        is_lead = idx == 0
        out.append(
            Deal(
                source_deal_id=f"ai-direct-debt:{issuer}:{idx}",
                deal_type=DealType.DEBT_FACILITY,
                title=title,
                parties=[issuer, name],
                counterparty_roles={"borrower": [issuer], "lender": [name]},
                notional_amount_usd=total_debt if is_lead else 0.0,
                key_terms={
                    "cluster": "ai_direct_financed_core",
                    "role_in_source": str(la.get("role") or "lender"),
                    "notional_attribution": (
                        "lead_arranger_carries_issuer_total_cluster_debt"
                        if is_lead
                        else "topology_edge_zero_notional_syndicate_allocation_undisclosed"
                    ),
                },
                provenance=_provenance(str(la.get("source_uri") or ""), str(la.get("quote") or "")),
                confidence=0.85,
            )
        )
    return out


def _supplier_deals(issuer: str, contagion: dict[str, Any]) -> list[Deal]:
    out: list[Deal] = []
    for idx, sup in enumerate(contagion.get("gpu_suppliers") or []):
        raw = str(sup.get("name") or "").strip()
        # Skip undisclosed/placeholder supplier names (no fabricated nodes).
        if not raw or "unnamed" in raw.lower() or "not disclosed" in raw.lower():
            continue
        name = _canon(raw)
        out.append(
            Deal(
                source_deal_id=f"ai-direct-supplier:{issuer}:{idx}",
                deal_type=DealType.OTHER,
                title=f"{issuer} GPU/compute supply dependency (AI data-center)",
                parties=[issuer, name],
                key_terms={"cluster": "ai_direct_financed_core", "edge": "gpu_supplier_dependency"},
                provenance=_provenance(str(sup.get("source_uri") or ""), str(sup.get("quote") or "")),
                confidence=0.85,
            )
        )
    return out


def _investor_deals(issuer: str, contagion: dict[str, Any]) -> list[Deal]:
    out: list[Deal] = []
    for idx, inv in enumerate(contagion.get("strategic_investors") or []):
        name = _canon(str(inv.get("name") or "").strip())
        if not name:
            continue
        amount = _parse_amount_usd(str(inv.get("stake_or_amount") or ""))
        out.append(
            Deal(
                source_deal_id=f"ai-direct-investor:{issuer}:{idx}",
                deal_type=DealType.PREFERRED_EQUITY,
                title=f"{issuer} strategic equity investment (AI compute, related-party)",
                parties=[issuer, name],
                counterparty_roles={"company": [issuer], "financier": [name]},
                notional_amount_usd=amount,
                is_related_party=True,
                key_terms={
                    "cluster": "ai_direct_financed_core",
                    "edge": "strategic_investor",
                    "stake_or_amount": str(inv.get("stake_or_amount") or "")[:200],
                },
                provenance=_provenance(str(inv.get("source_uri") or ""), str(inv.get("quote") or "")),
                confidence=0.85,
            )
        )
    return out


def _customer_deals(issuer: str, contagion: dict[str, Any]) -> list[Deal]:
    out: list[Deal] = []
    for idx, cust in enumerate(contagion.get("top_customers") or []):
        name = _canon(str(cust.get("name") or "").strip())
        if not name:
            continue
        conc = _num(cust.get("revenue_concentration_pct"))
        out.append(
            Deal(
                source_deal_id=f"ai-direct-customer:{issuer}:{idx}",
                deal_type=DealType.OTHER,
                title=f"{issuer} anchor AI compute customer (revenue concentration)",
                parties=[issuer, name],
                concentration_risk_flag=bool(conc is not None and conc >= 35),
                key_terms={
                    "cluster": "ai_direct_financed_core",
                    "edge": "anchor_customer",
                    "revenue_concentration_pct": conc,
                },
                provenance=_provenance(
                    str(cust.get("source_uri") or ""), str(cust.get("quote") or "")
                ),
                confidence=0.85,
            )
        )
    return out
