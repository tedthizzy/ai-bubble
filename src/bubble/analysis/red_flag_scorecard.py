"""Per-issuer FILING-VERIFIED forensic red-flag scorecard (the Burry checklist).

Complements the inferred-heuristic ``RedFlagEngine`` (red_flags.py, source_type
INFERRED) with a SOURCE-BACKED scorecard: each financed-cluster issuer is scored
on the classic forensic red-flag checklist from its SEC filings (adversarially
verified) -- going-concern doubt, material weakness in internal controls, auditor
change/resignation, restatement, related-party / circular financing, customer
concentration, insider net selling, negative operating cash flow, RPO quality,
aggressive useful-life/depreciation, covenant/liquidity headroom, and dilution.

Flags are severity-weighted so the serious accounting flags (going-concern,
material weakness, restatement, auditor exit) dominate the score, and only flags
that are PRESENT and tied to a source count -- an 'absent' or unverified flag
never inflates the risk score. Skepticism is asymmetric by design: the upstream
verifier rejects any 'present' serious flag lacking a filing cite, so a fabricated
going-concern cannot survive into the scorecard.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Severity weights: serious accounting/audit flags dominate.
_SEVERITY: dict[str, int] = {
    "going_concern_doubt": 5,
    "material_weakness_icfr": 4,
    "restatement": 4,
    "auditor_change_or_resignation": 3,
    "related_party_or_circular_financing": 3,
    "customer_concentration_over_35pct": 3,
    "negative_operating_cash_flow": 2,
    "aggressive_useful_life_or_depreciation": 2,
    "rpo_quality_or_concentration": 2,
    "covenant_or_liquidity_headroom": 2,
    "insider_net_selling": 1,
    "dilution_or_share_count_growth": 1,
    "other": 1,
}
_SERIOUS = {
    "going_concern_doubt",
    "material_weakness_icfr",
    "restatement",
    "auditor_change_or_resignation",
}
_KEPT_VERDICTS = {"filing_verified", "analyst_kept_flagged"}
_PRESENT = {"present", "partial"}


def load_red_flag_scorecard(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        loaded = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    return [r for r in loaded if isinstance(r, dict)] if isinstance(loaded, list) else []


def _short(name: str) -> str:
    return str(name or "").split("(")[0].split(",")[0].strip()


def aggregate_red_flag_scorecard(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Score each issuer on the forensic red-flag checklist and rank by risk."""

    usable = [
        r
        for r in records
        if str(r.get("overall") or "") in ("source_backed", "partially_source_backed")
    ]
    if not usable:
        return {"status": "blocked_no_source_backed_red_flags", "issuer_count": 0}

    per_issuer: list[dict[str, Any]] = []
    flag_frequency: dict[str, int] = {}
    serious_flag_issuers: list[str] = []
    total_present_flags = 0
    total_filing_verified = 0

    for rec in usable:
        issuer = _short(rec.get("issuer", ""))
        present_flags: list[dict[str, Any]] = []
        score = 0.0
        has_serious = False
        for f in rec.get("verified_flags") or []:
            verdict = str(f.get("verdict") or "")
            if verdict not in _KEPT_VERDICTS:
                continue
            if str(f.get("present") or "") not in _PRESENT:
                continue
            ftype = str(f.get("flag_type") or "other")
            weight = _SEVERITY.get(ftype, 1)
            partial_factor = 0.5 if str(f.get("present")) == "partial" else 1.0
            contribution = weight * partial_factor
            score += contribution
            total_present_flags += 1
            flag_frequency[ftype] = flag_frequency.get(ftype, 0) + 1
            if verdict == "filing_verified":
                total_filing_verified += 1
            if ftype in _SERIOUS:
                has_serious = True
            present_flags.append(
                {
                    "flag_type": ftype,
                    "present": f.get("present"),
                    "weight": weight,
                    "detail": str(f.get("detail") or "")[:200],
                    "verdict": verdict,
                }
            )
        if has_serious:
            serious_flag_issuers.append(issuer)
        present_flags.sort(key=lambda x: x["weight"], reverse=True)
        per_issuer.append(
            {
                "issuer": issuer,
                "red_flag_score": round(score, 1),
                "present_flag_count": len(present_flags),
                "filing_verified_present_count": sum(
                    1 for f in present_flags if f["verdict"] == "filing_verified"
                ),
                "has_serious_accounting_flag": has_serious,
                "present_flags": present_flags,
            }
        )

    per_issuer.sort(key=lambda r: (r["red_flag_score"], r["present_flag_count"]), reverse=True)

    return {
        "status": "source_backed",
        "issuer_count": len(usable),
        "issuers_with_serious_accounting_flag": sorted(set(serious_flag_issuers)),
        "highest_risk_issuers": [
            {"issuer": r["issuer"], "red_flag_score": r["red_flag_score"]} for r in per_issuer[:5]
        ],
        "most_common_flags": dict(sorted(flag_frequency.items(), key=lambda kv: -kv[1])),
        "total_present_flags": total_present_flags,
        "filing_verified_present_flags": total_filing_verified,
        "per_issuer": per_issuer,
        "red_flag_read": _read(serious_flag_issuers, flag_frequency, len(usable)),
        "note": (
            "Per-issuer forensic red-flag checklist from SEC filings (adversarially verified). Only "
            "PRESENT, source-tied flags score; severity-weighted so going-concern / material weakness "
            "/ restatement / auditor exit dominate. The verifier rejects any unsourced serious flag, "
            "so the score cannot be inflated by a fabricated accounting red flag. Absence of a serious "
            "flag is NOT a clean bill -- it means the filing did not disclose one in the window read."
        ),
    }


def _read(serious: list[str], freq: dict[str, int], total: int) -> str:
    pervasive = sorted(k for k, v in freq.items() if v >= max(2, total / 2))
    if serious:
        return (
            f"serious_accounting_flags_present: {len(set(serious))} of {total} issuers carry a "
            f"filing-tied SERIOUS flag (going-concern / material weakness / restatement / auditor "
            f"exit): {', '.join(sorted(set(serious)))}. These are the highest-conviction forensic "
            "tells and concentrate where a distress event is most likely to surface first."
        )
    base = (
        "no_serious_accounting_flag_in_window: no issuer shows a filing-tied going-concern, material "
        "weakness, restatement, or auditor exit in the period read -- the cluster's fragility is a "
        "cash-flow / leverage / concentration story, not (yet) an accounting-integrity one."
    )
    if pervasive:
        base += (
            f" But structural flags are PERVASIVE across the cluster (>=half the issuers): "
            f"{', '.join(pervasive)} -- a systemic, correlated risk rather than an idiosyncratic one."
        )
    return base
