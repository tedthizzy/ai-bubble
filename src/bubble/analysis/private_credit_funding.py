"""Debt-side routing of who-bears-downside: how the cluster's lenders are funded.

The end-holder layer (``end_holders``) maps the disclosed EQUITY holders of the
cluster but flags that the private-placement DDTL/SPV DEBT holders are not
13-F-visible. This module resolves that leg: it traces how the private-credit
lenders that hold the cluster's debt are themselves FUNDED -- the share of their
credit capital sourced from INSURANCE/ANNUITY balance sheets and PENSIONS, from
those lenders' own filings.

The Burry point: when Apollo lends to a neocloud off Athene's annuity book, or
Blackstone/Blue Owl/KKR off insurance perpetual capital, the ultimate credit loss
routes to POLICYHOLDERS and RETIREES -- households who never chose the AI bet.
This is the 2008 parallel (risk wrapped in "safe" insurance/pension liabilities)
and the debt-side complement to the equity end-holder distribution. Coverage is
partial and explicit: these are the lenders' aggregate funding mixes, not a
per-DDTL-facility attribution, which is not publicly disclosed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Funding sources whose losses route to households (policyholders / retirees).
_HOUSEHOLD_ROUTED = {"insurance_annuity_balance_sheet", "pension"}
_KEPT_VERDICTS = {"filing_verified", "analyst_kept_flagged"}


def load_private_credit_funding(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        loaded = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    return [r for r in loaded if isinstance(r, dict)] if isinstance(loaded, list) else []


def _num(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def aggregate_private_credit_funding(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate the insurance/pension funding share across the cluster's lenders."""

    usable = [
        r
        for r in records
        if str(r.get("overall") or "") in ("source_backed", "partially_source_backed")
    ]
    if not usable:
        return {"status": "blocked_no_source_backed_private_credit_funding", "lender_count": 0}

    per_lender: list[dict[str, Any]] = []
    insurance_shares: list[float] = []
    lenders_with_household_funding = 0
    filing_verified_sources = 0
    total_kept_sources = 0
    insurance_funded_lenders: list[str] = []

    for rec in usable:
        lender = str(rec.get("lender") or "").split("(")[0].split("/")[0].strip()
        sources = [
            s
            for s in (rec.get("verified_funding_sources") or [])
            if str(s.get("verdict") or "") in _KEPT_VERDICTS
        ]
        total_kept_sources += len(sources)
        filing_verified_sources += sum(
            1 for s in sources if str(s.get("verdict")) == "filing_verified"
        )
        ins_share = _num(rec.get("insurance_funded_share_pct"))
        household_types = {
            str(s.get("source_type"))
            for s in sources
            if str(s.get("source_type")) in _HOUSEHOLD_ROUTED
        }
        if ins_share is not None and ins_share > 0:
            insurance_shares.append(ins_share)
        if household_types:
            lenders_with_household_funding += 1
        if "insurance_annuity_balance_sheet" in household_types or (
            ins_share is not None and ins_share >= 20
        ):
            insurance_funded_lenders.append(lender)

        per_lender.append(
            {
                "lender": lender,
                "insurance_funded_share_pct": ins_share,
                "household_routed_funding_types": sorted(household_types),
                "total_credit_aum_usd": _num(rec.get("total_credit_aum_usd")),
                "kept_funding_sources": len(sources),
                "digital_infra_or_datacenter_credit_note": str(
                    rec.get("digital_infra_or_datacenter_credit_note") or ""
                )[:200]
                or None,
            }
        )

    per_lender.sort(key=lambda r: r["insurance_funded_share_pct"] or 0, reverse=True)
    median_ins = _median(insurance_shares)

    return {
        "status": "source_backed",
        "lender_count": len(usable),
        "lenders_with_household_routed_funding": lenders_with_household_funding,
        "insurance_funded_lenders": sorted(set(insurance_funded_lenders)),
        "median_insurance_funded_share_pct": median_ins,
        "lenders_reporting_insurance_share": len(insurance_shares),
        "filing_verified_sources": filing_verified_sources,
        "total_kept_sources": total_kept_sources,
        "per_lender": per_lender,
        "debt_side_downside_read": _read(lenders_with_household_funding, len(usable), median_ins),
        "note": (
            "Debt-side leg of who-bears-downside: how the private-credit lenders that hold the "
            "cluster's DDTL/SPV paper are themselves FUNDED (insurance/annuity + pension share of "
            "credit capital), from the lenders' own filings. Insurance-annuity / pension funding "
            "routes the ultimate credit loss to policyholders and retirees (households). COVERAGE IS "
            "PARTIAL: this is each lender's AGGREGATE funding mix, not a per-facility attribution to "
            "the cluster's specific debt (not publicly disclosed); shares are only those a filing "
            "supports, analyst-only figures are flagged. Complements the equity-side end_holders leg."
        ),
    }


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[mid], 1)
    return round((ordered[mid - 1] + ordered[mid]) / 2, 1)


def _read(household_lenders: int, total: int, median_ins: float | None) -> str:
    share_txt = (
        f" (median ~{median_ins}% of credit capital insurance-funded among lenders that disclose it)"
        if median_ins is not None
        else ""
    )
    if total > 0 and household_lenders >= total / 2:
        return (
            f"debt_side_routes_to_households: {household_lenders} of {total} cluster lenders draw a "
            f"material share of their credit capital from INSURANCE/ANNUITY balance sheets or "
            f"PENSIONS{share_txt}. So the cluster's private-placement DEBT loss -- invisible in 13-F "
            "equity data -- routes to policyholders and retirees, the same quiet, socialized channel "
            "as 2008. This is the resolved debt-side complement to the equity end-holder mix and a "
            "hidden, under-discussed downside concentration."
        )
    return (
        f"debt_side_mixed: {household_lenders} of {total} cluster lenders show material insurance/"
        f"pension funding{share_txt}; the rest draw on other institutional capital. The debt-side "
        "household routing is real but not dominant in the verified set; per-facility attribution to "
        "the cluster's specific paper remains undisclosed."
    )
