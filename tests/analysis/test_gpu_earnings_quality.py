"""GPU depreciation earnings-quality restatement."""

from __future__ import annotations

from bubble.analysis.gpu_earnings_quality import aggregate_gpu_earnings_quality


def _rec(issuer, metrics, overall="source_backed"):
    return {"issuer": issuer, "verified_metrics": metrics, "overall": overall}


def test_blocks_without_source_backed() -> None:
    out = aggregate_gpu_earnings_quality(
        [_rec("X", {"compute_or_gpu_ppe_net_usd": 1e9}, overall="unreliable")]
    )
    assert out["status"] == "blocked_no_source_backed_gpu_earnings"


def test_restates_depreciation_at_economic_life() -> None:
    # $6B compute PP&E at 6yr accounting life -> $1B/yr; at 3yr -> $2B/yr; understatement $1B.
    out = aggregate_gpu_earnings_quality(
        [
            _rec(
                "Bigfleet",
                {
                    "compute_or_gpu_ppe_net_usd": 6_000_000_000,
                    "compute_useful_life_years": 6,
                    "net_income_usd": 500_000_000,
                },
            )
        ],
        economic_life_years=3.0,
    )
    assert out["status"] == "source_backed"
    p = out["per_issuer"][0]
    assert p["annual_da_understatement_usd"] == 1_000_000_000
    # adjusted NI = 500M - 1000M = -500M -> flips negative.
    assert p["adjusted_net_income_usd"] == -500_000_000
    assert out["issuers_earnings_worsen_under_honest_depreciation"] == 1
    assert out["cluster_annual_da_understatement_usd"] == 1_000_000_000
    assert "earnings_overstated_by_understated_depreciation" in out["earnings_quality_read"]


def test_tam_realism_capture() -> None:
    out = aggregate_gpu_earnings_quality(
        [
            _rec(
                "TAMco",
                {
                    "ai_or_cloud_tam_cited_usd": 131_000_000_000,
                    "realized_ai_cloud_revenue_usd": 100_000_000,
                },
            )
        ]
    )
    tr = out["tam_realism"][0]
    assert tr["issuer"] == "TAMco"
    # 100M / 131B ~= 0.076%
    assert abs(tr["capture_pct"] - 0.076) < 0.01


def test_indeterminate_without_inputs() -> None:
    out = aggregate_gpu_earnings_quality([_rec("Empty", {"net_income_usd": -100})])
    assert out["issuers_with_restatement"] == 0
    assert "indeterminate" in out["earnings_quality_read"]
