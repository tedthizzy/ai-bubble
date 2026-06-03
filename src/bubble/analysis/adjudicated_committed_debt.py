"""Adjudicated AI-direct committed-debt: the over-count guard, run to completion.

The materiality review queue left 76 AI-DIRECT high-impact rows blocked as
"needs_deeper_extraction", carrying ~$1.45 TRILLION of inflated exposure bases
(e.g. Alphabet $75.6B/$58.5B/$42.6B of UN-COMMENCED off-balance-sheet leases,
TeraWulf's $73.27B basis that "appears nowhere in the filing", Equinix's $141.5B
synthetic aggregate). A fan-out of one skeptical agent per local primary filing
adjudicated each against the source; an adversarial second pass re-verified every
"committed" decision and assigned a normalized instrument key; then the confirmed
instruments were de-duplicated (the same TeraWulf 2030 notes appeared across 6
filings, the CoreWeave DDTL across 3, the Galaxy facility across 9).

The result is a clean, primary-source, de-duplicated bottom-up figure for the
financed cluster's committed debt -- and a quantified demonstration of the
engine's anti-over-count discipline: ~98% of the headline "exposure" in these
rows was aggregate / capacity / resale-registration / future-lease noise, NOT
committed debt. This aggregator surfaces that for the "how large" answer; it does
NOT change the evidence gate (the ecosystem verdict stays scoped/honest).
"""

from __future__ import annotations

from typing import Any


def _num(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def aggregate_adjudicated_committed_debt(payload: dict[str, Any]) -> dict[str, Any]:
    """Aggregate the adjudicated + adversarially-verified + de-duplicated committed-debt fixture."""

    if not payload or payload.get("status") != "source_backed":
        return {"status": "blocked_no_adjudication"}

    summ = payload.get("summary") or {}
    adv = payload.get("adversarial_verification") or {}
    dd = payload.get("deduped_distinct_instruments") or {}
    basis = _num(payload.get("original_inflated_basis_usd"))
    core = _num(dd.get("core_cluster_committed_usd"))
    infra = _num(dd.get("datacenter_infra_committed_usd"))
    ex_q = _num(dd.get("distinct_committed_ex_questionable_usd"))
    over = (basis - ex_q) if (basis is not None and ex_q is not None) else None
    over_pct = round(100 * over / basis, 1) if (over is not None and basis) else None
    instruments = sorted(
        dd.get("instruments") or [], key=lambda x: x.get("committed_usd", 0), reverse=True
    )

    return {
        "status": "source_backed",
        "blocked_rows_adjudicated": summ.get("row_count"),
        "committed_rows": summ.get("committed_count"),
        "refuted_in_adversarial_pass": adv.get("refuted_count"),
        "adversarial_verdicts": adv.get("by_verdict"),
        "by_decision": summ.get("by_decision"),
        "original_inflated_basis_usd": int(basis) if basis is not None else None,
        "verified_distinct_committed_core_cluster_usd": int(core) if core is not None else None,
        "datacenter_infra_committed_usd": int(infra) if infra is not None else None,
        "verified_distinct_committed_incl_infra_usd": int(ex_q) if ex_q is not None else None,
        "questionable_linkage_usd": dd.get("questionable_linkage_committed_usd"),
        "distinct_instrument_count": dd.get("instrument_count"),
        "over_count_removed_usd": int(over) if over is not None else None,
        "over_count_removed_pct": over_pct,
        "top_instruments": instruments[:12],
        "size_read": _read(summ, adv, basis, core, ex_q, over_pct),
        "caveat": dd.get("caveat"),
        "note": (
            "Primary-source adjudication of the 76 AI-direct blocked materiality rows (one skeptical agent "
            "per local SEC filing), an adversarial re-verification pass (0 of 39 committed decisions "
            "refuted), and instrument-level de-duplication. Bottom-up, committed-only, de-duplicated -- a "
            "cross-check on the per-issuer debt census, and a quantified over-count guard. Does not change "
            "the evidence gate or the scoped verdict."
        ),
    }


def _read(
    summ: dict[str, Any],
    adv: dict[str, Any],
    basis: float | None,
    core: float | None,
    ex_q: float | None,
    over_pct: float | None,
) -> str:
    if basis is None or ex_q is None or core is None:
        return "Adjudication present but distinct-committed totals are incomplete."
    return (
        f"Of {summ.get('row_count')} AI-direct blocked rows carrying ~${basis / 1e9:.0f}B of INFLATED "
        f"exposure bases, primary-source adjudication + adversarial verification "
        f"({adv.get('refuted_count', 0)} of {summ.get('committed_count')} committed decisions refuted) + "
        f"instrument-level de-duplication yield ~${core / 1e9:.1f}B of distinct committed debt for the "
        f"financed AI-COMPUTE cluster (~${ex_q / 1e9:.1f}B including data-center-infra issuers). That is a "
        f"~{over_pct}% over-count stripped: almost all the headline 'exposure' was aggregate / capacity / "
        "resale-registration / un-commenced-lease noise, NOT committed debt. This is the anti-over-count "
        "discipline run to completion on the highest-impact blocked tail, and it cross-checks the "
        "primary-sourced cluster debt census from the bottom up."
    )
