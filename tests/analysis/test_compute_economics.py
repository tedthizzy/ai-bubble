from __future__ import annotations

from datetime import date

from bubble.analysis.compute_economics import ComputeEconomicsBatch, analyze_compute_economics
from bubble.models.base import HumanReviewStatus, Provenance, SourceType
from bubble.models.compute import (
    CapexPaybackCase,
    ChipSupplyObservation,
    ComputeAsset,
    DepreciationPolicy,
    EpsDepreciationImpact,
    GpuPriceObservation,
    TamClaim,
)


def _prov(source_uri: str) -> Provenance:
    return Provenance(
        source_uri=source_uri,
        source_type=SourceType.SEC_EDGAR,
        confidence=0.9,
        human_review_status=HumanReviewStatus.APPROVED,
        content_hash=Provenance.compute_content_hash(source_uri),
    )


def test_compute_economics_flags_depreciation_tam_payback_eps_and_supply_risk() -> None:
    batch = ComputeEconomicsBatch(
        assets=[
            ComputeAsset(
                source_asset_id="asset-1",
                entity="xAI",
                gpu_generation="H100",
                capex_usd=30_000_000,
                accounting_useful_life_years=5,
                modeled_economic_life_years=2.5,
                provenance=_prov("https://www.sec.gov/asset"),
            )
        ],
        gpu_price_observations=[
            GpuPriceObservation(
                source_observation_id="h100-peak",
                gpu_generation="H100",
                observed_date=date(2024, 1, 1),
                observed_secondary_price_usd=40_000,
                observed_cloud_rental_rate_usd_per_hour=8,
                peak_price_usd=40_000,
                provenance=_prov("https://market.example/h100-peak"),
            ),
            GpuPriceObservation(
                source_observation_id="h100-latest",
                gpu_generation="H100",
                observed_date=date(2026, 5, 1),
                observed_secondary_price_usd=16_000,
                observed_cloud_rental_rate_usd_per_hour=3,
                peak_price_usd=40_000,
                provenance=_prov("https://market.example/h100-latest"),
            ),
        ],
        depreciation_policies=[
            DepreciationPolicy(
                source_policy_id="policy-1",
                entity="xAI",
                asset_class="GPU servers",
                accounting_useful_life_years=5,
                provenance=_prov("https://www.sec.gov/policy"),
            )
        ],
        tam_claims=[
            TamClaim(
                source_claim_id="tam-1",
                entity="xAI",
                claimed_market="AI compute",
                stated_tam_usd=2_400_000_000_000,
                realized_revenue_usd=100_000_000_000,
                provenance=_prov("https://issuer.example/tam"),
            )
        ],
        payback_cases=[
            CapexPaybackCase(
                source_case_id="case-1",
                entity="xAI",
                capex_usd=10_000_000_000,
                annual_revenue_run_rate_usd=1_000_000_000,
                gross_margin_pct=50,
                annual_power_cost_usd=100_000_000,
                annual_debt_service_usd=500_000_000,
                depreciation_life_years=3,
                provenance=_prov("https://issuer.example/payback"),
            )
        ],
        eps_impacts=[
            EpsDepreciationImpact(
                source_impact_id="eps-1",
                entity="xAI",
                fiscal_year=2027,
                gpu_capex_estimate_usd=10_000_000_000,
                accounting_useful_life_years=5,
                modeled_economic_life_years=2.5,
                tax_rate_pct=20,
                diluted_shares=1_000_000_000,
                provenance=_prov("https://issuer.example/eps"),
            )
        ],
        chip_supply_observations=[
            ChipSupplyObservation(
                source_observation_id="supply-1",
                entity="xAI",
                gpu_generation="H100",
                announced_gpu_count=10_000,
                delivered_gpu_count=4_000,
                announced_mw=100,
                provenance=_prov("https://issuer.example/supply"),
            )
        ],
    )

    metrics = analyze_compute_economics(batch)

    assert metrics.status == "measured"
    assert metrics.total_gpu_capex_usd == 30_000_000
    assert metrics.gpu_depreciation_red_flag_count == 1
    assert metrics.top_gpu_depreciation_risks[0].price_depreciation_pct == 60
    assert metrics.top_gpu_depreciation_risks[0].rental_rate_decline_pct == 62.5
    assert metrics.top_gpu_depreciation_risks[0].useful_life_gap_years == 2.5
    assert metrics.tam_red_flag_count == 1
    assert metrics.top_tam_reality_checks[0].tam_to_revenue_multiple == 24
    assert metrics.payback_red_flag_count == 1
    assert metrics.payback_blocked_case_count == 0
    assert metrics.payback_missing_debt_service_count == 0
    assert metrics.top_payback_stress_cases[0].annual_gross_cash_flow_usd == 400_000_000
    assert metrics.top_payback_stress_cases[0].payback_years == 25
    assert metrics.top_payback_stress_cases[0].debt_service_coverage_ratio == 0.8
    assert metrics.eps_red_flag_count == 1
    assert metrics.top_eps_impacts[0].incremental_depreciation_usd == 2_000_000_000
    assert metrics.top_eps_impacts[0].eps_drag == 1.6
    assert metrics.chip_supply_red_flag_count == 1
    assert metrics.top_chip_supply_gaps[0].delivery_gap_count == 6000
    assert metrics.top_chip_supply_gaps[0].implied_gpus_per_mw == 100


def test_empty_compute_economics_batch_blocks_compute_conclusions() -> None:
    batch = ComputeEconomicsBatch(
        assets=[],
        gpu_price_observations=[],
        depreciation_policies=[],
        tam_claims=[],
        payback_cases=[],
        eps_impacts=[],
        chip_supply_observations=[],
    )

    metrics = analyze_compute_economics(batch)

    assert metrics.status == "blocked_missing_compute_economics_evidence"
    assert metrics.gpu_price_observation_count == 0
    assert metrics.evidence_summary["summary"]["unsupported_claims"] == 6


def test_compute_payback_missing_inputs_are_counted_as_blocked_not_clean() -> None:
    batch = ComputeEconomicsBatch(
        assets=[],
        gpu_price_observations=[],
        depreciation_policies=[],
        tam_claims=[],
        payback_cases=[
            CapexPaybackCase(
                source_case_id="missing-margin",
                entity="WhiteFiber, Inc.",
                capex_usd=30_000_000,
                annual_revenue_run_rate_usd=12_000_000,
                gross_margin_pct=None,
                annual_debt_service_usd=None,
                provenance=_prov("https://www.sec.gov/whitefiber-10q"),
            ),
            CapexPaybackCase(
                source_case_id="missing-debt-service",
                entity="WhiteFiber, Inc.",
                capex_usd=42_000,
                annual_revenue_run_rate_usd=30_000,
                gross_margin_pct=50,
                annual_debt_service_usd=None,
                provenance=_prov("https://www.sec.gov/whitefiber-s1"),
            ),
        ],
        eps_impacts=[],
        chip_supply_observations=[],
    )

    metrics = analyze_compute_economics(batch)

    assert metrics.payback_case_count == 2
    assert metrics.payback_red_flag_count == 0
    assert metrics.payback_blocked_case_count == 1
    assert metrics.payback_missing_debt_service_count == 2
    blocked = metrics.top_payback_stress_cases[1]
    assert blocked.payback_years is None
    assert blocked.blocking_issues == ["Missing gross margin."]


def test_gpu_rental_decline_requires_comparable_time_series() -> None:
    batch = ComputeEconomicsBatch(
        assets=[],
        gpu_price_observations=[
            GpuPriceObservation(
                source_observation_id="h100-provider-a",
                gpu_generation="H100",
                observed_date=date(2026, 6, 1),
                observed_cloud_rental_rate_usd_per_hour=6.0,
                provider_or_marketplace="Provider A",
                contract_term="on_demand;8x",
                provenance=_prov("https://provider-a.example/h100"),
            ),
            GpuPriceObservation(
                source_observation_id="h100-provider-b",
                gpu_generation="H100",
                observed_date=date(2026, 6, 1),
                observed_cloud_rental_rate_usd_per_hour=3.0,
                provider_or_marketplace="Provider B",
                contract_term="reserved;1x",
                provenance=_prov("https://provider-b.example/h100"),
            ),
        ],
        depreciation_policies=[],
        tam_claims=[],
        payback_cases=[],
        eps_impacts=[],
        chip_supply_observations=[],
    )

    metrics = analyze_compute_economics(batch)

    assert metrics.gpu_depreciation_red_flag_count == 0
    risk = metrics.top_gpu_depreciation_risks[0]
    assert risk.peak_rental_rate_usd_per_hour is None
    assert risk.latest_rental_rate_usd_per_hour == 3.0
    assert risk.rental_rate_decline_pct is None
    assert not risk.red_flag
