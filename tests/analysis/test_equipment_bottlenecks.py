"""AI equipment-bottleneck constraint aggregation."""

from __future__ import annotations

from bubble.analysis.equipment_bottlenecks import aggregate_equipment_bottlenecks


def _supplier(name, *, verdict="filing_verified", share="leader"):
    return {
        "name": name,
        "approx_share_or_role": share,
        "source_filing": "20-F",
        "verdict": verdict,
    }


def _rec(
    chokepoint,
    *,
    suppliers,
    severity="material",
    gates="yes_primary_gate",
    lead_months=None,
    conc=None,
    overall="source_backed",
):
    return {
        "chokepoint": chokepoint,
        "verified_suppliers": suppliers,
        "constraint_severity": severity,
        "gates_ai_buildout": gates,
        "lead_time_months_estimate": lead_months,
        "concentration_note": conc,
        "overall": overall,
    }


def test_blocks_without_source_backed() -> None:
    out = aggregate_equipment_bottlenecks(
        [_rec("x", suppliers=[_supplier("A")], overall="unreliable")]
    )
    assert out["status"] == "blocked_no_source_backed_equipment_bottlenecks"


def test_rejected_suppliers_excluded() -> None:
    out = aggregate_equipment_bottlenecks(
        [
            _rec(
                "HBM",
                suppliers=[
                    _supplier("SK Hynix"),
                    _supplier("Ghost", verdict="rejected_unsourced"),
                ],
            )
        ]
    )
    assert out["total_kept_suppliers"] == 1
    assert out["filing_verified_suppliers"] == 1


def test_single_source_binding_gate_read() -> None:
    out = aggregate_equipment_bottlenecks(
        [
            _rec(
                "CoWoS advanced packaging",
                suppliers=[_supplier("TSMC", share="~near sole-source")],
                severity="binding_hard_constraint",
                gates="yes_primary_gate",
                lead_months=18,
                conc="effectively single-source for leading-edge CoWoS",
            ),
            _rec(
                "Liquid cooling",
                suppliers=[_supplier("Vertiv"), _supplier("Boyd")],
                severity="easing",
                gates="partial",
                lead_months=4,
            ),
        ]
    )
    assert out["status"] == "source_backed"
    assert out["gating_chokepoint_count"] == 1
    # Chokepoint labels are normalized to compact, stable tags.
    assert "TSMC CoWoS advanced packaging" in out["gating_chokepoints"]
    assert "TSMC CoWoS advanced packaging" in out["single_source_or_duopoly_chokepoints"]
    assert out["max_lead_time_months"] == 18
    assert "binding_equipment_chokepoints" in out["constraint_read"]
    assert "SINGLE-SOURCE" in out["constraint_read"]
    # The binding hard constraint sorts to the top.
    assert out["per_chokepoint"][0]["chokepoint"] == "TSMC CoWoS advanced packaging"


def test_no_binding_gate_read() -> None:
    out = aggregate_equipment_bottlenecks(
        [
            _rec(
                "Gensets",
                suppliers=[_supplier("Caterpillar"), _supplier("Cummins")],
                severity="easing",
                gates="no",
                lead_months=6,
            )
        ]
    )
    assert out["gating_chokepoint_count"] == 0
    assert "no_binding_equipment_gate_evidenced" in out["constraint_read"]
