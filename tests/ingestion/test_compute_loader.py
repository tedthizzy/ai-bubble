from __future__ import annotations

import csv
from typing import TYPE_CHECKING

import pytest

from bubble.ingestion.compute import load_compute_economics

if TYPE_CHECKING:
    from pathlib import Path


HASH = "a" * 64
RETRIEVED_AT = "2026-06-01T00:00:00+00:00"


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    assert rows
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _source_fields() -> dict[str, str]:
    return {
        "source_uri": "https://www.sec.gov/Archives/edgar/data/1/filing.htm",
        "source_type": "sec_edgar",
        "retrieved_at": RETRIEVED_AT,
        "content_hash": HASH,
        "human_review_status": "approved",
    }


def test_load_compute_economics_parses_all_source_backed_csvs(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "compute_assets.csv",
        [
            {
                "asset_id": "asset-1",
                "entity": "xAI",
                "gpu_generation": "H100",
                "gpu_count": 1000,
                "capex_usd": 30_000_000,
                "accounting_useful_life_years": 5,
                "modeled_economic_life_years": 2.5,
                **_source_fields(),
            }
        ],
    )
    _write_csv(
        tmp_path / "gpu_price_observations.csv",
        [
            {
                "observation_id": "price-1",
                "gpu_generation": "H100",
                "observed_date": "2026-05-01",
                "observed_secondary_price_usd": 16000,
                "peak_price_usd": 40000,
                **_source_fields(),
            }
        ],
    )
    _write_csv(
        tmp_path / "depreciation_policies.csv",
        [
            {
                "policy_id": "policy-1",
                "entity": "xAI",
                "asset_class": "GPU servers",
                "accounting_useful_life_years": 5,
                **_source_fields(),
            }
        ],
    )
    _write_csv(
        tmp_path / "tam_claims.csv",
        [
            {
                "claim_id": "tam-1",
                "entity": "xAI",
                "claimed_market": "AI compute",
                "stated_tam_usd": 2_400_000_000_000,
                "realized_revenue_usd": 100_000_000_000,
                **_source_fields(),
            }
        ],
    )
    _write_csv(
        tmp_path / "capex_payback_cases.csv",
        [
            {
                "case_id": "case-1",
                "entity": "xAI",
                "capex_usd": 10_000_000_000,
                "annual_revenue_run_rate_usd": 1_000_000_000,
                "gross_margin_pct": 50,
                "annual_power_cost_usd": 100_000_000,
                "annual_debt_service_usd": 500_000_000,
                "depreciation_life_years": 3,
                **_source_fields(),
            }
        ],
    )
    _write_csv(
        tmp_path / "eps_depreciation_impacts.csv",
        [
            {
                "impact_id": "eps-1",
                "entity": "xAI",
                "fiscal_year": 2027,
                "gpu_capex_estimate_usd": 10_000_000_000,
                "disclosed_depreciation_usd": 2_000_000_000,
                "disclosed_net_income_impact_usd": 1_600_000_000,
                "disclosed_eps_impact_usd": 1.6,
                "accounting_useful_life_years": 5,
                "modeled_economic_life_years": 2.5,
                "tax_rate_pct": 20,
                "diluted_shares": 1_000_000_000,
                "impact_direction": "modeled_shorter_economic_life",
                "source_quote": "The source disclosed an EPS impact from depreciation.",
                **_source_fields(),
            }
        ],
    )
    _write_csv(
        tmp_path / "chip_supply_observations.csv",
        [
            {
                "observation_id": "supply-1",
                "entity": "xAI",
                "gpu_generation": "H100",
                "announced_gpu_count": 10000,
                "delivered_gpu_count": 4000,
                "announced_mw": 100,
                **_source_fields(),
            }
        ],
    )

    batch = load_compute_economics(tmp_path)

    assert batch.row_count == 7
    assert batch.assets[0].entity == "xAI"
    assert batch.gpu_price_observations[0].provenance.content_hash == HASH
    assert batch.eps_impacts[0].fiscal_year == 2027
    assert batch.eps_impacts[0].disclosed_eps_impact_usd == 1.6
    assert batch.eps_impacts[0].source_quote == (
        "The source disclosed an EPS impact from depreciation."
    )


def test_compute_loader_requires_retrieval_timestamp_and_hash(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "compute_assets.csv",
        [
            {
                "asset_id": "asset-1",
                "entity": "xAI",
                "gpu_generation": "H100",
                "source_uri": "https://www.sec.gov/Archives/edgar/data/1/filing.htm",
                "source_type": "sec_edgar",
            }
        ],
    )

    with pytest.raises(ValueError, match=r"retrieved_at|content_hash"):
        load_compute_economics(tmp_path)
