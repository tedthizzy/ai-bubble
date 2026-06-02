from __future__ import annotations

import csv
import json
from pathlib import Path

from bubble.analysis.timing_signals import (
    build_timing_signal_batch,
    write_timing_signal_batch,
)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_timing_signals_build_source_backed_crack_window_inputs(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "edgar_acquisition" / "deals.csv",
        [
            {
                "deal_id": "deal-coreweave-2027",
                "deal_type": "debt_facility",
                "title": "AI data center credit agreement",
                "primary_party": "CoreWeave",
                "parties": "CoreWeave|Apollo Credit",
                "counterparty_roles": json.dumps({"lender": ["Apollo Credit"]}),
                "notional_amount_usd": "12000000000",
                "maturity_date": "2027-06-30",
                "source_uri": "https://www.sec.gov/credit.htm",
                "source_type": "sec_edgar",
                "source_confidence": "0.87",
                "human_review_status": "pending",
                "page_or_section": "8-K exhibit",
                "content_hash": "hash-credit",
                "key_terms": json.dumps({"notional_context_kind": "candidate_notional"}),
            },
            {
                "deal_id": "deal-missing-source-hash",
                "deal_type": "debt_facility",
                "primary_party": "Skipped Borrower",
                "notional_amount_usd": "99000000000",
                "maturity_date": "2027-06-30",
                "source_uri": "https://www.sec.gov/missing-hash.htm",
                "content_hash": "",
            },
        ],
    )
    _write_csv(
        tmp_path / "physical" / "projects.csv",
        [
            {
                "project_id": "project-1",
                "name": "CoreWeave Data Center Campus",
                "asset_type": "data_center",
                "owner": "CoreWeave",
                "operator": "CoreWeave",
                "construction_status": "announced",
                "capacity_mw": "1200",
                "announced_in_service_date": "2028-08",
                "source_uri": "https://queue.example/project.xlsx",
                "source_confidence": "0.82",
                "human_review_status": "pending",
                "page_or_section": "project row 1",
                "content_hash": "hash-project",
            }
        ],
    )
    _write_csv(
        tmp_path / "compute" / "eps_depreciation_impacts.csv",
        [
            {
                "impact_id": "eps-1",
                "entity": "Meta Platforms",
                "fiscal_year": "2026",
                "disclosed_depreciation_usd": "2900000000",
                "source_uri": "https://www.sec.gov/meta-10k.htm",
                "source_confidence": "0.81",
                "human_review_status": "pending",
                "page_or_section": "10-K depreciation note",
                "content_hash": "hash-eps",
            }
        ],
    )
    _write_csv(
        tmp_path / "compute" / "chip_supply_observations.csv",
        [
            {
                "observation_id": "chip-1",
                "entity": "xAI",
                "project_or_cluster_id": "colossus",
                "gpu_generation": "GB200",
                "announced_gpu_count": "10000",
                "delivered_gpu_count": "4000",
                "announced_mw": "300",
                "delivery_window": "by end of calendar year 2027",
                "supplier": "NVIDIA",
                "source_uri": "https://www.sec.gov/xai-s1.htm",
                "source_confidence": "0.78",
                "human_review_status": "pending",
                "page_or_section": "S-1 compute supply note",
                "content_hash": "hash-chip",
            }
        ],
    )

    batch = build_timing_signal_batch([tmp_path])

    assert batch.summary.signals == 4
    assert batch.summary.source_backed_signals == 4
    assert batch.summary.critical_or_high_signals == 4
    assert batch.summary.ai_infra_relevant_signals == 4
    assert batch.summary.categories == {"capital": 1, "compute": 2, "physical": 1}
    assert batch.summary.signal_types == {
        "chip_supply_delivery_window": 1,
        "eps_depreciation_impact": 1,
        "project_cod_or_queue_in_service": 1,
        "refinancing_maturity": 1,
    }
    assert batch.summary.peak_stress_quarter == "2027-Q2"
    assert batch.summary.capital_refinancing_usd_2024_2030 == 12_000_000_000
    assert batch.summary.ai_infra_capital_refinancing_usd_2024_2030 == 12_000_000_000
    assert batch.summary.physical_capacity_mw_2024_2030 == 1200
    assert batch.summary.compute_amount_usd_2024_2030 == 2_900_000_000
    assert batch.summary.chip_supply_capacity_mw_2024_2030 == 300

    signals_by_type = {signal.signal_type: signal for signal in batch.signals}
    assert signals_by_type["refinancing_maturity"].quarter == "2027-Q2"
    assert signals_by_type["refinancing_maturity"].ecosystem_relevance == "direct_ai_infra"
    assert signals_by_type["refinancing_maturity"].content_hash == "hash-credit"
    assert signals_by_type["project_cod_or_queue_in_service"].quarter == "2028-Q3"
    assert signals_by_type["project_cod_or_queue_in_service"].severity == "critical"
    assert signals_by_type["eps_depreciation_impact"].quarter == "2026-Q4"
    assert signals_by_type["chip_supply_delivery_window"].quarter == "2027-Q4"
    assert all(signal.deal_id != "deal-missing-source-hash" for signal in batch.signals)


def test_chip_supply_commitments_keep_latest_snapshot_per_purchase_book(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "compute" / "chip_supply_observations.csv",
        [
            {
                "observation_id": "nvidia-fy2026",
                "entity": "NVIDIA CORP",
                "project_or_cluster_id": "",
                "gpu_generation": "UNSPECIFIED",
                "disclosed_purchase_commitment_usd": "95200000000",
                "supplier": "NVIDIA CORP",
                "delivery_window": "fiscal year 2027",
                "observed_deployment_date": "2026-02-25",
                "source_uri": "https://www.sec.gov/nvda-20260125.htm",
                "source_confidence": "0.82",
                "human_review_status": "pending",
                "page_or_section": "10-K supply commitments",
                "content_hash": "hash-nvidia-10k",
            },
            {
                "observation_id": "nvidia-q1-fy2027",
                "entity": "NVIDIA CORP",
                "project_or_cluster_id": "",
                "gpu_generation": "UNSPECIFIED",
                "disclosed_purchase_commitment_usd": "119000000000",
                "supplier": "NVIDIA CORP",
                "delivery_window": "fiscal years 2027 through 2031",
                "observed_deployment_date": "2026-05-20",
                "source_uri": "https://www.sec.gov/nvda-20260426.htm",
                "source_confidence": "0.82",
                "human_review_status": "pending",
                "page_or_section": "10-Q supply commitments",
                "content_hash": "hash-nvidia-10q",
            },
            {
                "observation_id": "distinct-project",
                "entity": "Distinct AI Buyer",
                "project_or_cluster_id": "cluster-a",
                "gpu_generation": "MI300",
                "disclosed_purchase_commitment_usd": "10000000000",
                "supplier": "AMD",
                "delivery_window": "calendar year 2026",
                "observed_deployment_date": "2026-03-15",
                "source_uri": "https://www.sec.gov/distinct-project.htm",
                "source_confidence": "0.82",
                "human_review_status": "pending",
                "page_or_section": "8-K supply agreement",
                "content_hash": "hash-distinct-project",
            },
        ],
    )

    batch = build_timing_signal_batch([tmp_path])

    assert batch.summary.signals == 2
    assert batch.summary.compute_amount_usd_2024_2030 == 129_000_000_000
    signal_uris = {signal.source_uri for signal in batch.signals}
    assert "https://www.sec.gov/nvda-20260125.htm" not in signal_uris
    assert "https://www.sec.gov/nvda-20260426.htm" in signal_uris
    assert "https://www.sec.gov/distinct-project.htm" in signal_uris


def test_write_timing_signal_outputs_csv_and_summary(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "physical" / "queues.csv",
        [
            {
                "project_id": "queue-1",
                "status": "active",
                "requested_mw": "650",
                "expected_in_service_date": "2029-03-31",
                "source_uri": "https://queue.example/export.xlsx",
                "source_confidence": "0.8",
                "human_review_status": "pending",
                "page_or_section": "queue row 10",
                "content_hash": "hash-queue",
            }
        ],
    )

    batch = build_timing_signal_batch([tmp_path])
    outputs = write_timing_signal_batch(batch, tmp_path / "reports")

    assert Path(outputs["signals_csv"]).exists()
    assert Path(outputs["quarters_csv"]).exists()
    assert Path(outputs["summary_json"]).exists()
    summary = json.loads(Path(outputs["summary_json"]).read_text())
    assert summary["signals"] == 1
    assert summary["source_backed_signals"] == 1
    assert summary["physical_capacity_mw_2024_2030"] == 650


def test_timing_signals_use_tranche_maturities_when_available(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "edgar_acquisition" / "deals.csv",
        [
            {
                "deal_id": "deal-coreweave-tranched",
                "deal_type": "debt_facility",
                "title": "CoreWeave AI data center credit agreement",
                "primary_party": "CoreWeave",
                "counterparty_roles": json.dumps({"lender": ["Apollo Credit"]}),
                "source_uri": "https://www.sec.gov/credit.htm",
                "source_type": "sec_edgar",
                "source_confidence": "0.87",
                "human_review_status": "pending",
                "page_or_section": "8-K exhibit",
                "content_hash": "hash-credit",
                "key_terms": json.dumps({"notional_context_kind": "transaction_facility"}),
            }
        ],
    )
    _write_csv(
        tmp_path / "edgar_acquisition" / "tranches.csv",
        [
            {
                "deal_id": "deal-coreweave-tranched",
                "tranche_id": "A",
                "name": "Term Loan A",
                "notional_usd": "5000000000",
                "maturity": "2026-03-31",
                "source_uri": "https://www.sec.gov/credit.htm#tranche-a",
                "source_type": "sec_edgar",
                "source_confidence": "0.86",
                "human_review_status": "pending",
                "page_or_section": "tranche A",
                "content_hash": "hash-tranche-a",
            },
            {
                "deal_id": "deal-coreweave-tranched",
                "tranche_id": "B",
                "name": "Term Loan B",
                "notional_usd": "7000000000",
                "maturity": "2027-06-30",
                "source_uri": "https://www.sec.gov/credit.htm#tranche-b",
                "source_type": "sec_edgar",
                "source_confidence": "0.86",
                "human_review_status": "pending",
                "page_or_section": "tranche B",
                "content_hash": "hash-tranche-b",
            },
        ],
    )

    batch = build_timing_signal_batch([tmp_path])

    assert batch.summary.signals == 2
    assert batch.summary.signal_types == {"refinancing_maturity": 2}
    assert batch.summary.capital_refinancing_usd_2024_2030 == 12_000_000_000
    assert {signal.quarter for signal in batch.signals} == {"2026-Q1", "2027-Q2"}
    assert {signal.content_hash for signal in batch.signals} == {
        "hash-tranche-a",
        "hash-tranche-b",
    }
    assert all("tranche Term Loan" in signal.description for signal in batch.signals)


def test_timing_signals_dedupe_repeated_capital_obligation_disclosures(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "edgar_acquisition" / "deals.csv",
        [
            {
                "deal_id": "issuer-s1",
                "deal_type": "debt_facility",
                "title": "Issuer refinancing facility S-1",
                "primary_party": "Example Issuer Inc.",
                "counterparty_roles": json.dumps({"lender": ["Bank Group"]}),
                "notional_amount_usd": "10000000000",
                "maturity_date": "2026-03-31",
                "source_uri": "https://www.sec.gov/issuer-s1.htm",
                "source_confidence": "0.82",
                "human_review_status": "pending",
                "page_or_section": "S-1 facility description",
                "content_hash": "hash-s1",
                "key_terms": json.dumps({"notional_context_kind": "transaction_facility"}),
            },
            {
                "deal_id": "issuer-s1a",
                "deal_type": "lease",
                "title": "Issuer refinancing facility amended S-1",
                "primary_party": "Example Issuer Inc.",
                "counterparty_roles": json.dumps({"lessor": ["Bank Group"]}),
                "notional_amount_usd": "10000000000",
                "maturity_date": "2026-03-15",
                "source_uri": "https://www.sec.gov/issuer-s1a.htm",
                "source_confidence": "0.84",
                "human_review_status": "pending",
                "page_or_section": "S-1/A facility description",
                "content_hash": "hash-s1a",
                "key_terms": json.dumps({"notional_context_kind": "transaction_facility"}),
            },
            {
                "deal_id": "issuer-q2",
                "deal_type": "debt_facility",
                "title": "Issuer separate later maturity",
                "primary_party": "Example Issuer Inc.",
                "counterparty_roles": json.dumps({"lender": ["Bank Group"]}),
                "notional_amount_usd": "10000000000",
                "maturity_date": "2026-06-30",
                "source_uri": "https://www.sec.gov/issuer-q2.htm",
                "source_confidence": "0.82",
                "human_review_status": "pending",
                "page_or_section": "8-K separate facility",
                "content_hash": "hash-q2",
                "key_terms": json.dumps({"notional_context_kind": "transaction_facility"}),
            },
        ],
    )

    batch = build_timing_signal_batch([tmp_path])

    assert batch.summary.signals == 2
    assert batch.summary.capital_refinancing_usd_2024_2030 == 20_000_000_000
    q1_signal = next(signal for signal in batch.signals if signal.quarter == "2026-Q1")
    assert q1_signal.amount_usd == 10_000_000_000
    assert set(q1_signal.source_uris) == {
        "https://www.sec.gov/issuer-s1.htm",
        "https://www.sec.gov/issuer-s1a.htm",
    }
    assert set(q1_signal.content_hashes) == {"hash-s1", "hash-s1a"}
    assert {signal.quarter for signal in batch.signals} == {"2026-Q1", "2026-Q2"}


def test_timing_summary_splits_historical_and_forward_refinancing_wall(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "edgar_acquisition" / "deals.csv",
        [
            {
                "deal_id": "coreweave-past-q1",
                "deal_type": "debt_facility",
                "title": "CoreWeave AI data center credit agreement",
                "primary_party": "CoreWeave",
                "counterparty_roles": json.dumps({"lender": ["Bank Group"]}),
                "notional_amount_usd": "5000000000",
                "maturity_date": "2026-03-31",
                "source_uri": "https://www.sec.gov/coreweave-q1.htm",
                "source_confidence": "0.84",
                "human_review_status": "pending",
                "page_or_section": "8-K credit agreement",
                "content_hash": "hash-coreweave-q1",
                "key_terms": json.dumps({"notional_context_kind": "transaction_facility"}),
            },
            {
                "deal_id": "coreweave-forward-q2",
                "deal_type": "debt_facility",
                "title": "CoreWeave AI data center credit agreement",
                "primary_party": "CoreWeave",
                "counterparty_roles": json.dumps({"lender": ["Bank Group"]}),
                "notional_amount_usd": "7000000000",
                "maturity_date": "2026-06-30",
                "source_uri": "https://www.sec.gov/coreweave-q2.htm",
                "source_confidence": "0.84",
                "human_review_status": "pending",
                "page_or_section": "8-K credit agreement",
                "content_hash": "hash-coreweave-q2",
                "key_terms": json.dumps({"notional_context_kind": "transaction_facility"}),
            },
            {
                "deal_id": "utility-forward-q4",
                "deal_type": "bond",
                "title": "Utility first mortgage bonds",
                "primary_party": "Utility Issuer",
                "notional_amount_usd": "6000000000",
                "maturity_date": "2026-12-31",
                "source_uri": "https://www.sec.gov/utility-q4.htm",
                "source_confidence": "0.82",
                "human_review_status": "pending",
                "page_or_section": "8-K bond issuance",
                "content_hash": "hash-utility-q4",
                "key_terms": json.dumps({"notional_context_kind": "transaction_principal"}),
            },
        ],
    )

    batch = build_timing_signal_batch([tmp_path])

    assert batch.summary.forward_refinancing_as_of_quarter == "2026-Q2"
    assert batch.summary.capital_refinancing_usd_2024_2030 == 18_000_000_000
    assert batch.summary.capital_refinancing_historical_to_as_of_usd == 5_000_000_000
    assert batch.summary.capital_refinancing_forward_from_as_of_usd == 13_000_000_000
    assert (
        batch.summary.ai_infra_capital_refinancing_historical_to_as_of_usd
        == 5_000_000_000
    )
    assert batch.summary.ai_infra_capital_refinancing_forward_from_as_of_usd == 7_000_000_000
    assert batch.summary.forward_peak_refinancing_quarter == "2026-Q2"
    assert batch.summary.forward_peak_refinancing_usd == 7_000_000_000
    assert batch.summary.forward_peak_ai_infra_refinancing_quarter == "2026-Q2"
    assert batch.summary.forward_peak_ai_infra_refinancing_usd == 7_000_000_000


def test_timing_signals_block_mega_asset_and_capacity_rows(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "edgar_acquisition" / "deals.csv",
        [
            {
                "deal_id": "pennymac-upb",
                "deal_type": "bond",
                "title": "PennyMac investor presentation",
                "primary_party": "PennyMac Financial Services, Inc.",
                "notional_amount_usd": "471000000000",
                "maturity_date": "2026-03-31",
                "source_uri": "https://www.sec.gov/pennymac-upb.htm",
                "source_confidence": "0.78",
                "human_review_status": "pending",
                "page_or_section": "8-K exhibit",
                "content_hash": "hash-pennymac-upb",
                "key_terms": json.dumps(
                    {
                        "agreement_reasons": ["bond or notes language"],
                        "notional_context_excerpt": (
                            "Servicing portfolio UPB of $471.0 billion; notes payable "
                            "secured by mortgage servicing assets."
                        ),
                        "notional_context_kind": "candidate_notional",
                    }
                ),
            },
            {
                "deal_id": "blackstone-capacity",
                "deal_type": "debt_facility",
                "title": "Blackstone credit strategies disclosure",
                "primary_party": "Blackstone Secured Lending Fund",
                "notional_amount_usd": "266400000000",
                "maturity_date": "2024-09-30",
                "source_uri": "https://www.sec.gov/blackstone-capacity.htm",
                "source_confidence": "0.78",
                "human_review_status": "pending",
                "page_or_section": "424B2",
                "content_hash": "hash-blackstone-capacity",
                "key_terms": json.dumps(
                    {
                        "agreement_reasons": ["debt facility language"],
                        "collateral_descriptions": [
                            "net assets plus borrowings for investment purposes"
                        ],
                        "notional_context_excerpt": (
                            "$266.4 billion in credit-oriented strategies across "
                            "direct lending, leveraged loans, high yield bonds, "
                            "distressed and mezzanine debt."
                        ),
                        "notional_context_kind": "candidate_notional",
                    }
                ),
            },
        ],
    )

    batch = build_timing_signal_batch([tmp_path])

    assert batch.summary.signals == 0
    assert batch.summary.capital_refinancing_usd_2024_2030 == 0


def test_timing_signals_allow_strong_source_backed_mega_credit_agreement(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "edgar_acquisition" / "deals.csv",
        [
            {
                "deal_id": "mega-committed-credit",
                "deal_type": "debt_facility",
                "title": "AI infrastructure committed credit agreement",
                "primary_party": "Hyperscale AI Borrower",
                "counterparty_roles": json.dumps({"lender": ["Bank Group"]}),
                "notional_amount_usd": "60000000000",
                "maturity_date": "2029-06-30",
                "source_uri": "https://www.sec.gov/mega-committed-credit.htm",
                "source_confidence": "0.86",
                "human_review_status": "pending",
                "page_or_section": "8-K credit agreement",
                "content_hash": "hash-mega-credit",
                "key_terms": json.dumps(
                    {
                        "agreement_reasons": [
                            "debt facility language",
                            "keyword:credit agreement",
                        ],
                        "notional_context_excerpt": (
                            "The borrower entered into a senior secured credit "
                            "agreement providing aggregate commitments of "
                            "$60.0 billion under a revolving credit facility."
                        ),
                        "notional_context_kind": "transaction_facility",
                    }
                ),
            }
        ],
    )

    batch = build_timing_signal_batch([tmp_path])

    assert batch.summary.signals == 1
    assert batch.summary.capital_refinancing_usd_2024_2030 == 60_000_000_000
    assert batch.signals[0].entity == "Hyperscale AI Borrower"


def test_timing_signals_block_subthreshold_asset_rows_without_blocking_debt_boilerplate(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "edgar_acquisition" / "deals.csv",
        [
            {
                "deal_id": "community-bank-total-loans",
                "deal_type": "debt_facility",
                "title": "Community bank earnings release",
                "primary_party": "HBT Financial",
                "notional_amount_usd": "4700000000",
                "maturity_date": "2026-12-31",
                "source_uri": "https://www.sec.gov/hbt-total-loans.htm",
                "source_confidence": "0.78",
                "human_review_status": "pending",
                "page_or_section": "8-K exhibit",
                "content_hash": "hash-hbt-total-loans",
                "key_terms": json.dumps(
                    {
                        "notional_context_excerpt": (
                            "Total loans were $4.7 billion at quarter end."
                        ),
                        "notional_context_kind": "candidate_notional",
                    }
                ),
            },
            {
                "deal_id": "first-mortgage-bonds",
                "deal_type": "bond",
                "title": "Utility first mortgage bonds",
                "primary_party": "Utility Issuer",
                "notional_amount_usd": "12000000000",
                "maturity_date": "2030-12-31",
                "source_uri": "https://www.sec.gov/first-mortgage-bonds.htm",
                "source_confidence": "0.82",
                "human_review_status": "pending",
                "page_or_section": "8-K exhibit",
                "content_hash": "hash-first-mortgage-bonds",
                "key_terms": json.dumps(
                    {
                        "agreement_reasons": ["bond or notes language"],
                        "notional_context_excerpt": (
                            "The issuer completed the offering of $12.0 billion "
                            "principal amount of first mortgage bonds. "
                            "Forward-looking statements involve risks."
                        ),
                        "notional_context_kind": "transaction_principal",
                    }
                ),
            },
        ],
    )

    batch = build_timing_signal_batch([tmp_path])

    assert batch.summary.signals == 1
    assert batch.summary.capital_refinancing_usd_2024_2030 == 12_000_000_000
    assert batch.signals[0].deal_id == "first-mortgage-bonds"
