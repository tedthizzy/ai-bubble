"""Risk-bearer role-taxonomy fixtures (root cause 3).

Fixtures are the real misclassified entities from
``who_bears_downside.current_top_risk_bearers`` (report 20260602-0612), plus
negative controls that must remain risk principals.
"""

from __future__ import annotations

from bubble.quality.risk_bearer_classification import (
    classify_risk_bearer,
    is_artifact_name,
    summarize_graph_artifact_edges,
    summarize_risk_bearer_quality,
)


def test_pure_trustee_and_agent_are_not_risk_principals() -> None:
    # Wilmington Trust / U.S. Bank Trust: trustee+agent+financier, NO lender role.
    wilmington = classify_risk_bearer(
        ["administrative_agent", "collateral_agent", "financier", "indenture_trustee", "trustee"],
        "WILMINGTON TRUST, NATIONAL ASSOCIATION",
    )
    assert wilmington["bucket"] == "intermediary"
    assert wilmington["is_risk_principal"] is False


def test_statute_and_fragment_names_are_artifacts() -> None:
    statute = classify_risk_bearer(["indenture_trustee", "trustee"], "Trust Indenture Act of 1939 or res")
    assert statute["bucket"] == "artifact"
    assert statute["is_risk_principal"] is False
    fragment = classify_risk_bearer(["lender"], "the lenders party hereto and JPMorgan")
    assert fragment["bucket"] == "artifact"  # name stop-list wins even with a lender role
    assert fragment["is_risk_principal"] is False


def test_lender_that_is_also_an_agent_stays_principal_but_flags_weighting() -> None:
    # JPMorgan: lender AND admin/collateral agent -> principal, but its full-notional
    # attribution over-counts the deals where it is merely an agent.
    jpm = classify_risk_bearer(
        ["administrative_agent", "collateral_agent", "financier", "lender"],
        "JPMORGAN CHASE BANK, N.A.",
    )
    assert jpm["bucket"] == "risk_principal"
    assert jpm["is_risk_principal"] is True
    assert jpm["needs_role_weighting"] is True


def test_negative_controls_real_lender_and_guarantor_remain_principals() -> None:
    # A pure named lender (syndicate member) must remain a risk bearer, unflagged.
    apollo = classify_risk_bearer(["lender"], "Apollo Credit Management, LLC")
    assert apollo["bucket"] == "risk_principal"
    assert apollo["is_risk_principal"] is True
    assert apollo["needs_role_weighting"] is False
    # A pure guarantor (WML, $44.4B in the report) is a genuine downside bearer.
    wml = classify_risk_bearer(["guarantor"], "WML")
    assert wml["is_risk_principal"] is True
    # 'financier' alone is too generic to establish a principal.
    assert classify_risk_bearer(["financier"], "Some Bank")["bucket"] == "intermediary"


def test_summary_quantifies_misattributed_exposure() -> None:
    bearers = [
        {"name": "JPMORGAN CHASE BANK, N.A.", "roles": ["administrative_agent", "lender"], "exposure_usd": 592.9e9},
        {"name": "WILMINGTON TRUST, N.A.", "roles": ["indenture_trustee", "trustee"], "exposure_usd": 111.5e9},
        {"name": "Trust Indenture Act of 1939", "roles": ["trustee"], "exposure_usd": 52.2e9},
        {"name": "Apollo Credit", "roles": ["lender"], "exposure_usd": 10.0e9},
    ]

    s = summarize_risk_bearer_quality(bearers)

    assert s["counts"] == {"risk_principal": 2, "intermediary": 1, "artifact": 1, "unknown": 0}
    # intermediary (Wilmington 111.5) + artifact (statute 52.2) = 163.7B mis-attributed.
    assert s["misattributed_exposure_usd"] == round(111.5e9 + 52.2e9, 2)
    # JPMorgan ($592.9B) is a principal but flagged for role-weighting; Apollo is not.
    assert s["risk_principal_needs_role_weighting_usd"] == 592.9e9


def test_graph_artifact_edges_are_flagged() -> None:
    edges = [
        {"source_id": "entity:fulton-financial", "target_id": "entity:trust-indenture-act-of-1939", "notional_usd": 52.2e9},
        {"source_id": "entity:coreweave", "target_id": "entity:apollo-credit", "notional_usd": 8e9},
        {"source_id": "entity:at-t", "target_id": "entity:parent-company-the-lenders", "notional_usd": 12.75e9},
    ]
    s = summarize_graph_artifact_edges(edges)
    assert s["total_edges"] == 3
    assert s["artifact_edges"] == 2  # trust-indenture-act + the-lenders
    assert s["artifact_edge_notional_usd"] == round(52.2e9 + 12.75e9, 2)


def test_institutional_names_are_not_artifacts() -> None:
    # "The Trustees of the University of X" is a real endowment, not the trustee role.
    assert is_artifact_name("the-trustees-of-the-university-of-pennsylvania") is False
    assert is_artifact_name("regents-of-the-university-of-california") is False
    # The bare role phrase is still an artifact.
    assert is_artifact_name("entity:the-trustee") is True
    assert is_artifact_name("entity:trust-indenture-act-of-1939") is True
