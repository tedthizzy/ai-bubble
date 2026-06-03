"""Contract-level structure: who bears the loss, from the actual credit agreements.

Upgrades the census-level recourse classification with CONTRACT-LEVEL structure
extracted from the issuers' actual credit-agreement / guaranty exhibits
(adversarially verified): per facility, the named borrower SPV, whether it is
bankruptcy-remote, recourse (full-to-parent / limited / non-recourse / unclear),
guarantors + guarantee scope (cap/trigger), and collateral (GPUs / equity pledge
/ all-assets). This is the load-bearing input to "who ultimately bears the
downside": a non-recourse, bankruptcy-remote SPV ring-fences the loss to that
facility's creditors and the pledged collateral; a full-recourse / parent-
guaranteed facility puts the loss on parent equity.

The recourse and guarantee fields are STRONG claims, so the upstream verifier
rejects any non-recourse / bankruptcy-remote assertion lacking explicit document
language (downgraded to 'unclear'); this aggregate only counts what survived.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_RECOURSE_CLASSES = (
    "full_recourse_to_parent",
    "limited_recourse",
    "non_recourse",
    "unclear",
)
_KEPT_VERDICTS = {"filing_verified", "analyst_kept_flagged"}


def _is_yes(value: Any) -> bool:
    """Verify agents may return a verbose 'yes -- SUPPORTED by ...' string; match the yes prefix."""

    return str(value or "").strip().lower().startswith("yes")


def _norm_recourse(value: Any) -> str:
    text = str(value or "").strip().lower()
    for rc in _RECOURSE_CLASSES:
        if text.startswith(rc) or rc in text:
            return rc
    return "unclear"


def load_contract_structure(path: str | Path) -> list[dict[str, Any]]:
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


def aggregate_contract_structure(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate contract-level recourse / guarantee / SPV / collateral structure."""

    usable = [
        r
        for r in records
        if str(r.get("overall") or "") in ("source_backed", "partially_source_backed")
    ]
    if not usable:
        return {"status": "blocked_no_source_backed_contract_structure", "issuer_count": 0}

    recourse_counts: dict[str, int] = dict.fromkeys(_RECOURSE_CLASSES, 0)
    recourse_principal: dict[str, float] = dict.fromkeys(_RECOURSE_CLASSES, 0.0)
    facilities_total = 0
    filing_verified_facilities = 0
    bankruptcy_remote = 0
    gpu_collateralized = 0
    parent_guaranteed = 0
    spv_named = 0
    per_issuer: list[dict[str, Any]] = []
    example_guarantees: list[str] = []

    for rec in usable:
        issuer = _short(rec.get("issuer", ""))
        facs = [
            f
            for f in (rec.get("verified_facilities") or [])
            if str(f.get("verdict") or "") in _KEPT_VERDICTS
        ]
        issuer_recourse: dict[str, int] = {}
        for f in facs:
            facilities_total += 1
            if str(f.get("verdict")) == "filing_verified":
                filing_verified_facilities += 1
            rc = _norm_recourse(f.get("recourse"))
            recourse_counts[rc] += 1
            issuer_recourse[rc] = issuer_recourse.get(rc, 0) + 1
            principal = _num(f.get("principal_usd"))
            if principal:
                recourse_principal[rc] += principal
            if _is_yes(f.get("bankruptcy_remote")):
                bankruptcy_remote += 1
            if _is_yes(f.get("gpu_collateral")):
                gpu_collateralized += 1
            if f.get("guarantors"):
                parent_guaranteed += 1
            if f.get("borrower_spv") and str(f.get("borrower_spv")).lower() not in ("parent", "none"):
                spv_named += 1
            scope = str(f.get("guarantee_scope") or "").strip()
            if scope and len(example_guarantees) < 6:
                example_guarantees.append(f"{issuer}: {scope[:120]}")
        per_issuer.append(
            {
                "issuer": issuer,
                "facility_count": len(facs),
                "recourse_breakdown": issuer_recourse,
                "spv_named": sum(
                    1
                    for f in facs
                    if f.get("borrower_spv")
                    and str(f.get("borrower_spv")).lower() not in ("parent", "none")
                ),
            }
        )

    if facilities_total == 0:
        return {"status": "blocked_no_kept_facilities", "issuer_count": len(usable)}

    return {
        "status": "source_backed",
        "issuer_count": len(usable),
        "facility_count": facilities_total,
        "filing_verified_facilities": filing_verified_facilities,
        "recourse_breakdown_counts": recourse_counts,
        "recourse_breakdown_principal_usd": {k: round(v, 2) for k, v in recourse_principal.items()},
        "bankruptcy_remote_facilities": bankruptcy_remote,
        "gpu_collateralized_facilities": gpu_collateralized,
        "parent_guaranteed_facilities": parent_guaranteed,
        "named_borrower_spv_facilities": spv_named,
        "example_guarantee_scopes": example_guarantees,
        "per_issuer": per_issuer,
        "who_bears_downside_read": _read(recourse_counts, bankruptcy_remote, parent_guaranteed),
        "note": (
            "Contract-level who-bears-downside, from the actual credit-agreement / guaranty exhibits "
            "(adversarially verified; non-recourse / bankruptcy-remote claims rejected unless the "
            "document states them, so those counts are conservative). full_recourse_to_parent / "
            "parent-guaranteed facilities put the loss on PARENT EQUITY; non_recourse + "
            "bankruptcy-remote SPVs ring-fence it to facility creditors + pledged collateral (often "
            "GPUs). This sharpens the census-level recourse split with document-level structure."
        ),
    }


def _read(counts: dict[str, int], bankruptcy_remote: int, parent_guaranteed: int) -> str:
    total = sum(counts.values())
    full = counts.get("full_recourse_to_parent", 0)
    non = counts.get("non_recourse", 0)
    if total == 0:
        return "indeterminate"
    if full + parent_guaranteed >= max(non, 1) and full >= non:
        return (
            f"loss_concentrates_on_parent_equity: of {total} contract-verified facilities, "
            f"{full} are full-recourse-to-parent and {parent_guaranteed} are parent-guaranteed vs "
            f"{non} non-recourse ({bankruptcy_remote} bankruptcy-remote). So at the contract level the "
            "downside lands on PARENT EQUITY, not ring-fenced into the SPVs -- a creditor of the "
            "facility can reach the parent, so equity holders (not just facility lenders) eat the loss. "
            "This corroborates the census-level recourse finding with document language."
        )
    return (
        f"loss_ring_fenced_to_spv_creditors: of {total} contract-verified facilities, {non} are "
        f"non-recourse ({bankruptcy_remote} bankruptcy-remote) vs {full} full-recourse -- a material "
        "share of the loss is ring-fenced to facility creditors and the pledged collateral (GPUs), "
        "limiting parent-equity contagion but concentrating GPU-collateral recovery risk."
    )
