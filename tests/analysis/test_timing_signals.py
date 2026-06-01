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
