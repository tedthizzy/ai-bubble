"""Cluster-boundary test — is the financed-AI cluster bounded, or does it balloon?

A bubble call hinges on scope. This consumes an adversarially-verified breadth
sweep of ADJACENT candidate names (crypto-miners / HPC pivots near the financed
neocloud cluster) and reports how many actually qualify as genuine FINANCED
AI-infra vs crypto-only-with-marginal-AI vs not-relevant. A low qualify-rate is a
SCOPING finding that reinforces the scoped (not ecosystem-wide) verdict: the
financed-AI buildout is a small, specific, leveraged set -- adding adjacent names
mostly fails the in-scope test rather than enlarging the cluster.

The in-scope judgement is the verifier's (a pure bitcoin miner with aspirational
AI is 'crypto_only_marginal_ai', not 'financed_ai_infra'); this aggregate only
tallies what survived verification.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_KEPT = ("source_backed", "partially_source_backed")


def load_cluster_boundary(path: str | Path) -> list[dict[str, Any]]:
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


def aggregate_cluster_boundary(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Tally how many adjacent candidate names qualify as financed AI-infra."""

    usable = [r for r in records if str(r.get("overall") or "") in _KEPT]
    if not usable:
        return {"status": "blocked_no_source_backed_boundary", "candidate_count": 0}

    by_scope: dict[str, list[str]] = {}
    for rec in usable:
        scope = str(rec.get("in_scope") or "unknown")
        by_scope.setdefault(scope, []).append(_short(rec.get("issuer", "")))

    financed = by_scope.get("financed_ai_infra", [])
    crypto = by_scope.get("crypto_only_marginal_ai", [])
    not_rel = by_scope.get("not_relevant", [])
    total = len(usable)
    qualify_pct = round(100 * len(financed) / total, 1) if total else None

    return {
        "status": "source_backed",
        "candidate_count": total,
        "qualified_financed_ai_infra": sorted(financed),
        "crypto_only_marginal_ai": sorted(crypto),
        "not_relevant": sorted(not_rel),
        "qualify_rate_pct": qualify_pct,
        "scope_counts": {k: len(v) for k, v in by_scope.items()},
        "boundary_read": _read(financed, crypto, not_rel, total),
        "note": (
            "Cluster-boundary test over adjacent candidate names (crypto-miners / HPC pivots near the "
            "financed neocloud cluster). Each is classified by the adversarial verifier as "
            "financed_ai_infra / crypto_only_marginal_ai / not_relevant. A low qualify-rate is a "
            "SCOPING finding: the financed-AI cluster is bounded and specific, which reinforces the "
            "scoped (not ecosystem-wide) verdict rather than enlarging the cluster."
        ),
    }


def _read(financed: list[str], crypto: list[str], not_rel: list[str], total: int) -> str:
    if total and len(financed) <= total / 2:
        return (
            f"cluster_is_bounded: only {len(financed)} of {total} adjacent candidate names qualify as "
            f"genuine financed AI-infra ({', '.join(financed) or 'none'}); {len(crypto)} are "
            f"crypto-only-with-marginal-AI and {len(not_rel)} not relevant. The financed-AI buildout "
            "does NOT balloon when you probe adjacent names -- it is a small, specific, leveraged set. "
            "This reinforces the scoped verdict: bubble dynamics in a bounded financed cluster, not an "
            "ecosystem-wide phenomenon."
        )
    return (
        f"cluster_extends: {len(financed)} of {total} adjacent candidates qualify as financed AI-infra "
        f"({', '.join(financed)}), so the financed cluster is broader than the initial core -- fold the "
        "qualified names into the per-issuer layers and re-test the aggregate findings at larger n."
    )
