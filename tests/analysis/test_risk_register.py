"""Top actionable-risk register synthesis."""

from __future__ import annotations

from bubble.analysis.risk_register import build_risk_register


def test_blocks_when_no_layers() -> None:
    out = build_risk_register({})
    assert out["status"] == "blocked_no_source_backed_layers"


def test_builds_ranked_register_from_layers() -> None:
    m = {
        "cluster_interest_coverage": {
            "status": "source_backed",
            "cluster_ebitda_interest_coverage": 1.35,
            "loss_making_issuer_count": 7,
            "issuers_with_usable_inputs": 11,
        },
        "scenario_stress": {
            "scenarios": [{"scenario": "adverse", "issuers_breaching": 8}],
        },
        "red_flag_scorecard": {
            "status": "source_backed",
            "issuer_count": 8,
            "issuers_with_serious_accounting_flag": ["A", "B"],
            "most_common_flags": {
                "material_weakness_icfr": 8,
                "customer_concentration_over_35pct": 8,
                "auditor_change_or_resignation": 5,
                "related_party_or_circular_financing": 7,
            },
        },
        "equipment_bottlenecks": {
            "status": "source_backed",
            "gating_chokepoint_count": 8,
            "chokepoint_count": 8,
            "max_lead_time_months": 42,
            "single_source_or_duopoly_chokepoints": ["TSMC CoWoS advanced packaging"],
        },
        "private_credit_funding": {
            "status": "source_backed",
            "lenders_with_household_routed_funding": 8,
            "lender_count": 8,
            "median_insurance_funded_share_pct": 41.0,
        },
    }
    census = {
        "status": "source_backed",
        "cluster_total_debt_usd": 54_800_000_000,
        "near_term_2025_2027_pct_of_scheduled": 29,
        "wall_2030_2033_pct_of_scheduled": 40,
    }
    out = build_risk_register(m, debt_census=census)

    assert out["status"] == "source_backed"
    assert out["risk_count"] >= 6
    assert out["source_backed_risk_count"] == out["risk_count"]
    # Ranked severity-first, ranks assigned 1..n.
    assert out["risks"][0]["rank"] == 1
    severities = [r["severity"] for r in out["risks"]]
    assert severities == sorted(severities, reverse=True)
    # The top risk is a severity-5 cash-flow/refi risk.
    assert out["risks"][0]["severity"] == 5
    # Every risk carries an evidence anchor + backing layer.
    assert all(r["evidence"] and r["backing_layer"] for r in out["risks"])


def test_only_source_backed_layers_emit_risks() -> None:
    # A layer present but not source_backed must not produce a risk.
    out = build_risk_register(
        {
            "cluster_interest_coverage": {
                "status": "source_backed",
                "cluster_ebitda_interest_coverage": 1.2,
                "loss_making_issuer_count": 6,
                "issuers_with_usable_inputs": 11,
            },
            "equipment_bottlenecks": {"status": "blocked_no_source_backed_equipment_bottlenecks"},
        }
    )
    layers = {r["backing_layer"] for r in out["risks"]}
    assert not any("equipment" in s for s in layers)
