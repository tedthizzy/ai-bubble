"""AI data-center supply-chain equipment-bottleneck constraint layer.

The supply-side skeptic's question: can the buildout physically be built, and who
controls the chokepoints? Distinct from the POWER layer (delivered grid capacity)
and the FINANCING layer (can they pay), this maps the equipment chokepoints --
advanced packaging (TSMC CoWoS), HBM memory, GPUs, gas turbines, large power
transformers, gensets, liquid cooling, skilled electrical labor -- each with its
supplier concentration, lead time / backlog, and whether it GATES deployment, from
supplier filings (adversarially verified).

A hard, concentrated, multi-year-lead-time chokepoint is a Burry-style leading
indicator: it caps how fast the announced buildout can convert to revenue, and a
single-source gate (e.g. CoWoS) propagates a shock across every downstream issuer
at once. The aggregate is explicit about which figures are filing-verified vs
analyst-reported -- it never asserts a lead time it cannot source.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Severities that represent a real, binding gate on the buildout.
_GATING_SEVERITIES = {"binding_hard_constraint", "material"}
_PRIMARY_GATES = {"yes_primary_gate", "yes_secondary"}
_KEPT_VERDICTS = {"filing_verified", "analyst_kept_flagged"}

# The extractor sometimes returns a long descriptive chokepoint string; collapse
# it to a compact, stable label by keyword for display/aggregation.
_LABELS = (
    ("cowos", "TSMC CoWoS advanced packaging"),
    ("advanced 2.5d", "TSMC CoWoS advanced packaging"),
    ("high-bandwidth memory", "HBM memory"),
    ("hbm", "HBM memory"),
    ("gpu allocation", "NVIDIA GPU allocation"),
    ("data-center gpu", "NVIDIA GPU allocation"),
    ("gas turbine", "Gas turbines"),
    ("turbine", "Gas turbines"),
    ("transformer", "Large power transformers & switchgear"),
    ("switchgear", "Large power transformers & switchgear"),
    ("genset", "Backup gensets / reciprocating engines"),
    ("reciprocating engine", "Backup gensets / reciprocating engines"),
    ("liquid cooling", "Liquid cooling / thermal"),
    ("cooling", "Liquid cooling / thermal"),
    ("electrical labor", "Skilled electrical labor / EPC"),
    ("electrician", "Skilled electrical labor / EPC"),
    ("epc", "Skilled electrical labor / EPC"),
)


def _short_label(chokepoint: str) -> str:
    text = str(chokepoint or "").lower()
    for marker, label in _LABELS:
        if marker in text:
            return label
    # Fall back to the first clause of the raw string, truncated.
    head = str(chokepoint or "").split("—")[0].split("(")[0].split(".")[0].strip()
    return head[:60] or "unknown_chokepoint"


def load_equipment_bottlenecks(path: str | Path) -> list[dict[str, Any]]:
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


def aggregate_equipment_bottlenecks(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate chokepoint constraint severity, lead times, and supplier concentration."""

    usable = [
        r
        for r in records
        if str(r.get("overall") or "") in ("source_backed", "partially_source_backed")
    ]
    if not usable:
        return {"status": "blocked_no_source_backed_equipment_bottlenecks", "chokepoint_count": 0}

    per_chokepoint: list[dict[str, Any]] = []
    gating_chokepoints: list[str] = []
    primary_gates: list[str] = []
    lead_times: list[float] = []
    filing_verified_suppliers = 0
    total_kept_suppliers = 0
    single_source: list[str] = []

    for rec in usable:
        name = _short_label(rec.get("chokepoint") or "")
        suppliers = [
            s
            for s in (rec.get("verified_suppliers") or [])
            if str(s.get("verdict") or "") in _KEPT_VERDICTS
        ]
        fv = sum(1 for s in suppliers if str(s.get("verdict")) == "filing_verified")
        filing_verified_suppliers += fv
        total_kept_suppliers += len(suppliers)
        severity = str(rec.get("constraint_severity") or "unknown")
        gates = str(rec.get("gates_ai_buildout") or "no")
        lead_months = _num(rec.get("lead_time_months_estimate"))
        if lead_months is not None and lead_months > 0:
            lead_times.append(lead_months)
        if severity in _GATING_SEVERITIES and gates in _PRIMARY_GATES:
            gating_chokepoints.append(name)
        if gates == "yes_primary_gate":
            primary_gates.append(name)
        # Single-source / duopoly concentration flag from kept suppliers count + note.
        conc_note = str(rec.get("concentration_note") or "").lower()
        if len(suppliers) <= 1 or "single" in conc_note or "sole" in conc_note:
            single_source.append(name)

        per_chokepoint.append(
            {
                "chokepoint": name,
                "chokepoint_detail": str(rec.get("chokepoint") or "")[:200],
                "constraint_severity": severity,
                "gates_ai_buildout": gates,
                "lead_time_or_backlog": str(rec.get("lead_time_or_backlog") or "")[:200] or None,
                "lead_time_months_estimate": lead_months,
                "supplier_count": len(suppliers),
                "filing_verified_suppliers": fv,
                "top_suppliers": [
                    {
                        "name": str(s.get("name") or "")[:80],
                        "approx_share_or_role": str(s.get("approx_share_or_role") or "")[:120],
                        "verdict": s.get("verdict"),
                    }
                    for s in suppliers[:5]
                ],
                "concentration_note": str(rec.get("concentration_note") or "")[:240] or None,
            }
        )

    per_chokepoint.sort(
        key=lambda c: (
            c["constraint_severity"] == "binding_hard_constraint",
            c["gates_ai_buildout"] == "yes_primary_gate",
            c["lead_time_months_estimate"] or 0,
        ),
        reverse=True,
    )
    max_lead = max(lead_times) if lead_times else None

    return {
        "status": "source_backed",
        "chokepoint_count": len(usable),
        "gating_chokepoint_count": len(gating_chokepoints),
        "gating_chokepoints": gating_chokepoints,
        "primary_gate_chokepoints": primary_gates,
        "single_source_or_duopoly_chokepoints": sorted(set(single_source)),
        "max_lead_time_months": max_lead,
        "median_lead_time_months": _median(lead_times),
        "filing_verified_suppliers": filing_verified_suppliers,
        "total_kept_suppliers": total_kept_suppliers,
        "per_chokepoint": per_chokepoint,
        "constraint_read": _constraint_read(gating_chokepoints, single_source, max_lead),
        "note": (
            "Supply-side equipment-bottleneck layer: each chokepoint's supplier concentration, lead "
            "time / backlog, and whether it gates the AI buildout, from supplier filings "
            "(adversarially verified). A hard, single-source, multi-year-lead chokepoint caps how "
            "fast announced capacity converts to revenue and propagates a shock across all downstream "
            "issuers at once. Lead-time figures are only those tied to a source; unsourceable ones are "
            "left null, not invented."
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


def _constraint_read(gating: list[str], single_source: list[str], max_lead: float | None) -> str:
    if not gating:
        return (
            "no_binding_equipment_gate_evidenced: no chokepoint is both a hard/material constraint AND "
            "a primary gate in the verified set; supply may still tighten, but the evidence does not "
            "support a binding equipment bottleneck today."
        )
    overlap = sorted(set(gating) & set(single_source))
    lead_txt = f" with lead times up to ~{int(max_lead)} months" if max_lead else ""
    base = (
        f"binding_equipment_chokepoints: {len(gating)} chokepoint(s) are both hard/material AND gate "
        f"the buildout{lead_txt} -- a physical cap on how fast announced AI capacity can convert to "
        f"revenue, independent of demand or financing."
    )
    if overlap:
        return (
            base
            + f" Of these, {', '.join(overlap)} is/are SINGLE-SOURCE or duopoly -- a shock there "
            "propagates across every downstream issuer simultaneously (the supply-side analogue of the "
            "NVIDIA hub), and a leading indicator the market under-weights versus headline demand."
        )
    return base
