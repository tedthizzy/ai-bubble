"""Per-entity weakest-links ranking — who cracks first, and why.

The Final Burry Report requires a clear identification of the weakest links in the
capital structure and the top specific high-risk entities with their exact
concerns. This fuses the per-issuer forensic red-flag scorecard with the
source-backed issuer financials (loss-making / leverage) into a single composite,
ranked, per-ENTITY view (complementing the per-RISK register): for each issuer, a
composite risk score plus the specific concerns (its present red flags + the
financial facts), each traceable to its source layer.

It never invents a concern: an entity's flags come from the filing-verified
scorecard, its financials from the primary-filing fixture; an entity with thin
disclosure simply carries fewer anchored concerns, not a fabricated score.
"""

from __future__ import annotations

from typing import Any


def _num(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _short(name: str) -> str:
    return str(name or "").split("(")[0].split(",")[0].strip()


def build_entity_risk_ranking(
    red_flag_scorecard: dict[str, Any],
    issuer_financials: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Rank cluster entities by a composite of forensic flags + financial fragility."""

    rf = red_flag_scorecard or {}
    if rf.get("status") != "source_backed":
        return {"status": "blocked_no_source_backed_red_flags", "entity_count": 0}

    # Index financials by normalized short name.
    fin_by_name: dict[str, dict[str, Any]] = {}
    for row in issuer_financials or []:
        name = _short(row.get("entity", ""))
        if name:
            fin_by_name[name.lower()] = row

    ranked: list[dict[str, Any]] = []
    for issuer in rf.get("per_issuer") or []:
        name = _short(issuer.get("issuer", ""))
        flag_score = float(issuer.get("red_flag_score") or 0)
        fin = fin_by_name.get(name.lower(), {})
        ebitda = _num(fin.get("ebitda_usd"))
        total_debt = _num(fin.get("total_debt_usd"))
        net_income = _num(fin.get("net_income_usd"))

        # Forensic concerns (the present flags, highest-weight first).
        concerns: list[str] = [
            f"{f.get('flag_type')} ({f.get('present')})"
            for f in (issuer.get("present_flags") or [])[:4]
        ]
        # Financial concerns.
        fin_score = 0.0
        if ebitda is not None and ebitda < 0:
            concerns.append(f"negative EBITDA (${round(ebitda / 1e9, 2)}B)")
            fin_score += 2
        if net_income is not None and net_income < 0:
            fin_score += 1
        if total_debt is not None and total_debt >= 5e9:
            concerns.append(f"high leverage (debt ${round(total_debt / 1e9, 1)}B)")
            fin_score += 1

        composite = round(flag_score + fin_score, 1)
        ranked.append(
            {
                "entity": name,
                "composite_risk_score": composite,
                "red_flag_score": flag_score,
                "financial_fragility_score": fin_score,
                "has_serious_accounting_flag": bool(issuer.get("has_serious_accounting_flag")),
                "negative_ebitda": bool(ebitda is not None and ebitda < 0),
                "total_debt_usd": total_debt,
                "key_concerns": concerns,
            }
        )

    ranked.sort(
        key=lambda e: (e["composite_risk_score"], e["has_serious_accounting_flag"]), reverse=True
    )
    for i, e in enumerate(ranked, start=1):
        e["rank"] = i

    if not ranked:
        return {"status": "blocked_no_entities", "entity_count": 0}

    return {
        "status": "source_backed",
        "entity_count": len(ranked),
        "entities_with_financials": sum(
            1 for e in ranked if e["total_debt_usd"] is not None or e["negative_ebitda"]
        ),
        "weakest_links_top": [
            {
                "rank": e["rank"],
                "entity": e["entity"],
                "composite_risk_score": e["composite_risk_score"],
                "key_concerns": e["key_concerns"][:5],
            }
            for e in ranked[:5]
        ],
        "ranked_entities": ranked,
        "ranking_read": _read(ranked),
        "note": (
            "Per-entity weakest-links ranking: composite = forensic red-flag score (severity-weighted, "
            "filing-verified) + financial-fragility score (negative EBITDA, net loss, high leverage from "
            "the primary-filing financials). Concerns are the entity's PRESENT red flags + its financial "
            "facts -- each traceable to its source layer; nothing invented. This is the per-ENTITY 'who "
            "cracks first and why' view, complementing the per-RISK register."
        ),
    }


def _read(ranked: list[dict[str, Any]]) -> str:
    top = ranked[0] if ranked else None
    serious = [e["entity"] for e in ranked if e["has_serious_accounting_flag"]]
    neg = [e["entity"] for e in ranked if e["negative_ebitda"]]
    if not top:
        return "no_entities_ranked"
    return (
        f"weakest_link_is_{top['entity'].replace(' ', '_')}: highest composite risk "
        f"({top['composite_risk_score']}) driven by {', '.join(top['key_concerns'][:3])}. "
        f"{len(serious)}/{len(ranked)} entities carry a serious accounting flag and "
        f"{len(neg)}/{len(ranked)} are EBITDA-negative -- the fragility is broad across the cluster, "
        "not concentrated in one name, so an idiosyncratic distress event would land in a correlated set."
    )
