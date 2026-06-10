"""Verified extension of the financed cluster with newly-surfaced material members.

The exhaustive universe map surfaced financed-leveraged names the original deep-8
missed; this folds in their adversarially-verified deep-models -- crucially with
RECOURSE debt disentangled from non-recourse JV/project debt. The headline example:
Crusoe's ~$10.75B of associated debt is only ~$1.15B RECOURSE to Crusoe Inc.; the
~$9.6B Abilene construction loans sit at a Blue Owl / Oracle-lease JV/SPV and do
NOT reach the parent -- so the cluster's recourse leverage rises far less than the
headline numbers suggest. Capturing only the recourse portion keeps the
who-bears-downside math honest.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_cluster_extension(path: str | Path) -> list[dict[str, Any]]:
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


def aggregate_cluster_extension(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate the verified new cluster members + their recourse debt."""

    confirmed = [
        r
        for r in records
        if r.get("in_financed_cluster")
        and str(r.get("overall") or "") in ("source_backed", "partially_source_backed")
    ]
    if not confirmed:
        return {"status": "blocked_no_confirmed_new_members", "member_count": 0}

    total_recourse = 0.0
    total_associated = 0.0
    members: list[dict[str, Any]] = []
    for r in confirmed:
        recourse = _num(r.get("verified_recourse_debt_usd"))
        total = _num(r.get("verified_total_debt_usd"))
        if recourse:
            total_recourse += recourse
        if total:
            total_associated += total
        members.append(
            {
                "name": str(r.get("name") or "").split("(")[0].split("—")[0].strip()[:50],
                "public_filer": r.get("public_filer"),
                "recourse_debt_usd": recourse,
                "total_associated_debt_usd": total,
                "revenue_usd": _num(r.get("verified_revenue_usd")),
            }
        )

    members.sort(key=lambda m: m["recourse_debt_usd"] or 0, reverse=True)
    return {
        "status": "source_backed",
        "member_count": len(confirmed),
        "new_recourse_debt_usd": round(total_recourse, 2),
        "new_associated_debt_usd": round(total_associated, 2),
        "members": members,
        "extension_read": _read(len(confirmed), total_recourse, total_associated, members),
        "note": (
            "Verified new financed-cluster members beyond the deep-8 (from the universe-map sweep), "
            "each adversarially deep-modeled. RECOURSE debt is disentangled from non-recourse JV / "
            "project-SPV debt (e.g. Crusoe ~$1.15B recourse vs ~$9.6B Oracle-lease-collateralized JV "
            "debt that does NOT reach the parent), so the cluster's recourse leverage rises only by the "
            "recourse portion. Private names disclose no audited financials -- debt is from ABS "
            "prospectuses / facility announcements, marked accordingly."
        ),
    }


def _read(n: int, recourse: float, associated: float, members: list[dict[str, Any]]) -> str:
    top = ", ".join(
        f"{m['name']} (${round((m['recourse_debt_usd'] or 0) / 1e9, 2)}B recourse)"
        for m in members[:4]
    )
    return (
        f"cluster_extends_by_{n}_verified_members: adds ~${round(recourse / 1e9, 1)}B of RECOURSE debt "
        f"(of ~${round(associated / 1e9, 1)}B associated) -- {top}. The recourse/associated gap is the "
        "honest correction: much of the headline AI-infra debt sits in non-recourse JV/project SPVs "
        "(Oracle-lease-collateralized) that do not reach the operator's equity, so the financed-distress "
        "exposure grows by the recourse slice, not the headline."
    )
