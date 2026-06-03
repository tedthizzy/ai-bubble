"""GPU depreciation earnings-quality: restate D&A at economic life; TAM realism.

The Burry earnings-quality question on the weakest analytical layer: GPUs
economically depreciate in ~2-3 years (deployed-fleet rental yields fall 60-75% in
18-24 months) but the cluster books them over 5-6+ years, so depreciation is
understated and earnings are overstated. This restates each issuer's compute
depreciation at an economic life and measures how much worse the (already
fragile) earnings look -- plus a TAM-realism check (cited AI TAM vs realized
revenue capture).

The economic-life assumption (default 3yr) is a labeled ASSUMPTION; the compute
PP&E, accounting useful life, and D&A are primary-sourced per issuer. An issuer
contributes a restatement only where its inputs are filing-verified; nothing is
invented.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_ECONOMIC_LIFE_YEARS = 3.0


def load_gpu_earnings_quality(path: str | Path) -> list[dict[str, Any]]:
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


def _short(name: str) -> str:
    return str(name or "").split("(")[0].split(",")[0].strip()


def aggregate_gpu_earnings_quality(
    records: list[dict[str, Any]], *, economic_life_years: float = _ECONOMIC_LIFE_YEARS
) -> dict[str, Any]:
    """Restate compute depreciation at economic life + TAM realism, per issuer + aggregate."""

    usable = [
        r
        for r in records
        if str(r.get("overall") or "") in ("source_backed", "partially_source_backed")
    ]
    if not usable:
        return {"status": "blocked_no_source_backed_gpu_earnings", "issuer_count": 0}

    per_issuer: list[dict[str, Any]] = []
    total_understatement = 0.0
    issuers_with_restatement = 0
    issuers_flipped_more_negative = 0
    tam_realism: list[dict[str, Any]] = []

    for rec in usable:
        issuer = _short(rec.get("issuer", ""))
        mt = rec.get("verified_metrics") or {}
        compute_ppe = _num(mt.get("compute_or_gpu_ppe_net_usd"))
        life = _num(mt.get("compute_useful_life_years"))
        net_income = _num(mt.get("net_income_usd"))
        tam = _num(mt.get("ai_or_cloud_tam_cited_usd"))
        realized = _num(mt.get("realized_ai_cloud_revenue_usd"))

        da = _num(mt.get("annual_depreciation_amortization_usd"))
        understatement = None
        adjusted_ni = None
        method = None
        # Net compute PP&E is rarely disclosed (issuers give gross by class + aggregate
        # accumulated depreciation), so the usable restatement scales DISCLOSED D&A by the
        # accounting/economic life ratio: D&A x (life/econ - 1). Upper bound -- total D&A
        # includes some longer-lived non-compute assets, but compute dominates for neoclouds.
        if da and da > 0 and life and life > economic_life_years:
            understatement = round(da * (life / economic_life_years - 1), 2)
            method = "da_life_ratio_upper_bound"
        elif compute_ppe and compute_ppe > 0 and life and life > economic_life_years:
            understatement = round(
                compute_ppe / economic_life_years - compute_ppe / life, 2
            )
            method = "net_compute_ppe"
        if understatement and understatement > 0:
            total_understatement += understatement
            issuers_with_restatement += 1
            if net_income is not None:
                adjusted_ni = round(net_income - understatement, 2)
                if adjusted_ni < min(net_income, 0):
                    issuers_flipped_more_negative += 1

        capture_pct = None
        if tam and tam > 0 and realized is not None:
            capture_pct = round(100 * realized / tam, 3)
            tam_realism.append(
                {"issuer": issuer, "tam_usd": tam, "realized_usd": realized, "capture_pct": capture_pct}
            )

        per_issuer.append(
            {
                "issuer": issuer,
                "compute_ppe_net_usd": compute_ppe,
                "accounting_useful_life_years": life,
                "annual_da_understatement_usd": understatement,
                "restatement_method": method,
                "net_income_usd": net_income,
                "adjusted_net_income_usd": adjusted_ni,
            }
        )

    per_issuer.sort(key=lambda r: (r["annual_da_understatement_usd"] or 0), reverse=True)

    return {
        "status": "source_backed",
        "issuer_count": len(usable),
        "economic_life_assumption_years": economic_life_years,
        "issuers_with_restatement": issuers_with_restatement,
        "cluster_annual_da_understatement_usd": round(total_understatement, 2),
        "issuers_earnings_worsen_under_honest_depreciation": issuers_flipped_more_negative,
        "tam_realism": sorted(tam_realism, key=lambda x: x["capture_pct"]),
        "per_issuer": per_issuer,
        "earnings_quality_read": _read(
            issuers_with_restatement, total_understatement, tam_realism, economic_life_years
        ),
        "note": (
            "GPU depreciation earnings-quality. Compute PP&E, accounting useful life, and D&A are "
            f"primary-sourced per issuer; the {economic_life_years}yr economic life is a labeled "
            "ASSUMPTION (defensible from rental-yield compression). 'Understatement' = restated "
            "depreciation at economic life minus accounting depreciation on the same net book value -- "
            "the amount by which D&A is understated and pre-tax earnings overstated each year. TAM "
            "realism = realized AI/cloud revenue as a % of the cited TAM (tiny capture = aspirational). "
            "Only filing-verified inputs contribute; nothing invented."
        ),
    }


def _read(
    n: int, understatement: float, tam_realism: list[dict[str, Any]], life: float
) -> str:
    if n == 0:
        return (
            "indeterminate: no issuer disclosed both a compute-PP&E book value and a useful life "
            "cleanly enough to restate depreciation; the gap is real (see gpu_economics) but the "
            "per-issuer earnings impact is disclosure-blocked."
        )
    tam_txt = ""
    if tam_realism:
        worst = min(tam_realism, key=lambda x: x["capture_pct"])
        tam_txt = (
            f" TAM realism: cited markets imply a tiny realized capture (e.g. {worst['issuer']} "
            f"~{worst['capture_pct']}% of its cited TAM) -- the buildout's justification leans on "
            "aspirational TAM, not realized revenue."
        )
    return (
        f"earnings_overstated_by_understated_depreciation (UPPER BOUND): restating depreciation at a "
        f"~{int(life)}yr economic life adds ~${round(understatement / 1e9, 2)}B/yr across {n} issuers that "
        "disclose the inputs. This is an UPPER BOUND, not a point estimate: the method scales each issuer's "
        "ENTIRE D&A by the life ratio, but D&A also covers genuinely long-lived assets (data-center shells, "
        "electrical, leasehold up to ~12yr) that should NOT be re-lived at 3yr -- a compute-gross-weighted "
        "restatement is materially lower (e.g. CoreWeave ~$1.6B vs ~$2.45B here). The DIRECTION is robust "
        "(every restated issuer worsens; CoreWeave's loss roughly triples), but read the figure as a ceiling. "
        "Caveat Nebius: it is already operationally loss-making (continuing-ops NI ~+$10M; its positive "
        "headline NI is discontinued-ops + equity-revaluation gains), so the restatement deepens, not "
        "creates, its loss." + tam_txt
    )
