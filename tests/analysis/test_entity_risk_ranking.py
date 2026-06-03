"""Per-entity weakest-links ranking."""

from __future__ import annotations

from bubble.analysis.entity_risk_ranking import build_entity_risk_ranking


def _scorecard(per_issuer):
    return {"status": "source_backed", "per_issuer": per_issuer}


def _issuer(name, score, *, serious=False, flags=None):
    return {
        "issuer": name,
        "red_flag_score": score,
        "has_serious_accounting_flag": serious,
        "present_flags": flags or [],
    }


def test_blocks_without_source_backed_scorecard() -> None:
    out = build_entity_risk_ranking({"status": "blocked"})
    assert out["status"] == "blocked_no_source_backed_red_flags"


def test_fuses_flags_and_financials_and_ranks() -> None:
    scorecard = _scorecard(
        [
            _issuer(
                "Weakco",
                10.0,
                serious=True,
                flags=[{"flag_type": "material_weakness_icfr", "present": "present"}],
            ),
            _issuer("Midco", 6.0),
        ]
    )
    financials = [
        {"entity": "Weakco, Inc.", "ebitda_usd": -500_000_000, "total_debt_usd": 6_000_000_000,
         "net_income_usd": -800_000_000},
        {"entity": "Midco", "ebitda_usd": 200_000_000, "total_debt_usd": 1_000_000_000},
    ]
    out = build_entity_risk_ranking(scorecard, financials)
    assert out["status"] == "source_backed"
    # Weakco: 10 + neg-ebitda(2) + net-loss(1) + high-debt(1) = 14; Midco: 6.
    weakco = out["ranked_entities"][0]
    assert weakco["entity"] == "Weakco"
    assert weakco["composite_risk_score"] == 14.0
    assert weakco["rank"] == 1
    assert any("negative EBITDA" in c for c in weakco["key_concerns"])
    assert any("material_weakness" in c for c in weakco["key_concerns"])
    assert "weakest_link_is_Weakco" in out["ranking_read"]


def test_entity_without_financials_still_ranks_on_flags() -> None:
    out = build_entity_risk_ranking(_scorecard([_issuer("Orphan", 8.0)]), [])
    e = out["ranked_entities"][0]
    assert e["entity"] == "Orphan"
    assert e["composite_risk_score"] == 8.0
    assert e["financial_fragility_score"] == 0.0
    assert e["total_debt_usd"] is None
