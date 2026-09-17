"""The dated runner must not reuse the June verdict or hide missing signals."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

import pytest
from scripts.refresh_live_overlay import _issuance_latest
from scripts.run_dated_engine_2026_09_16 import (
    evaluate_dated_market,
    run,
    summarize_financials,
    summarize_sec_inventory,
)

ROOT = Path(__file__).resolve().parent.parent


def test_registered_signal_recalculation_matches_dated_observations() -> None:
    market = json.loads((ROOT / "analysis/market_close_2026-09-16.json").read_text())
    cards = json.loads((ROOT / "analysis/issuance_cards.json").read_text())["deals"]
    result = evaluate_dated_market(market, cards)
    statuses = {item["id"]: item["status"] for item in result["registered_components"]}
    assert statuses == {
        "S1_new_issue_spread": "contra",
        "S1b_failed_print": "confirming",
        "S2_ccc_divergence": "confirming",
        "S3_bdc_discount_differential": "contra",
        "S4_demand_trajectory": "unmeasured",
    }
    assert result["compound_confirm_2"] is False
    assert result["latest_carded_issuance_date"] == "2026-08-27"
    assert result["ust5y_pct"] == 4.83
    assert (
        next(
            item for item in result["registered_components"] if item["id"] == "S1_new_issue_spread"
        )["value_bp"]
        == 180
    )
    assert next(
        item for item in result["registered_components"] if item["id"] == "S1b_failed_print"
    )["event"]["issuer"] in {
        "Prime Data Centers LLC",
        "Pure Data Centres Group Ltd",
    }
    market["credit"]["registered_s2_status"] = "contra"
    with pytest.raises(ValueError, match="S2 disagrees"):
        evaluate_dated_market(market, cards)


def test_latest_issuance_for_s1_excludes_later_withdrawn_deal() -> None:
    deals = [
        {"date": "2026-08-27", "issuer": "priced", "coupon_pct": 6.625, "status": "priced"},
        {"date": "2026-09-01", "issuer": "withdrawn", "status": "pulled"},
    ]
    latest = _issuance_latest(deals, {"ust5y": {"value": 4.83}})
    assert latest is not None
    assert latest["issuer"] == "priced"
    assert latest["spread_vs_5y_bp"] == 180


def test_financial_panel_uses_matched_report_periods_only() -> None:
    panel = json.loads((ROOT / "analysis/case_zero_financials_2026-09-16_v4.json").read_text())
    result = summarize_financials(panel)
    assert result["panel_entities"] == 22
    assert result["panel_issuer_entries"] == 13
    assert result["issuer_current_2026_matched_cashflow_capex"] == 11
    assert result["issuer_current_2026_negative_cash_after_capex"] == 11
    assert result["issuer_older_matched_cashflow_capex"] == 1
    assert {row["ticker"] for row in result["issuer_observations"]} != {"BTDR"}
    assert (
        next(row for row in result["issuer_observations"] if row["ticker"] == "NBIS")["end"]
        == "2025-12-31"
    )


def test_saved_dated_run_preserves_full_observation_counts() -> None:
    result = json.loads((ROOT / "analysis/dated_engine_2026-09-16_v6.json").read_text())
    assert result["physical_capacity"]["queue_records_scanned"] == 16_515
    assert result["physical_capacity"]["gross_generation_queue_requested_mw"] == pytest.approx(
        531_011.143
    )
    assert result["compute_economics"]["gpu_price_observations"] == 87
    assert result["compute_economics"]["payback_case_rows"] == 0
    assert result["bubble_probability"] is None
    assert result["capital_graph"]["ferc_only"]["pending_graph_deals"] == 46_483


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_full_dated_run_executes_physical_and_compute_without_new_probability(
    tmp_path: Path,
) -> None:
    """Execute real rollups without depending on the ignored acquisition cache."""
    analysis = tmp_path / "analysis"
    analysis.mkdir()
    for name in (
        "market_close_2026-09-16.json",
        "case_zero_financials_2026-09-16_v4.json",
        "source_refresh_2026-09-16.json",
        "gpu_pricing_delta_2026-09-16.json",
        "issuance_cards.json",
    ):
        shutil.copyfile(ROOT / "analysis" / name, analysis / name)

    # Synthetic rows test execution and filtering. The saved-report test above
    # retains the full acquisition's historical totals separately.
    provenance = {
        "source_uri": "https://example.com/test-data",
        "retrieved_at": "2026-09-16T12:00:00+00:00",
        "content_hash": "test-fixture",
    }
    acquisition = tmp_path / "data/source_acquisition_2026-09-16"
    queue_path = (
        acquisition / "derived/queue_combined_full_serial_2026-09-16/source_rows/queue_records.csv"
    )
    _write_csv(
        queue_path,
        [
            {
                **provenance,
                "source_id": "pjm-planning-queues-xml",
                "source_type": "grid_interconnection_queue",
                "ProjectNumber": f"TEST-{status}",
                "Status": status,
                "MaximumFacilityOutput": capacity,
            }
            for status, capacity in (("Active", "450"), ("Withdrawn", "999"))
        ],
    )
    _write_csv(
        acquisition / "derived/tracker_projects.csv",
        [
            {
                **provenance,
                "source_type": "project_tracker",
                "project_id": "test-project",
                "name": "Test data center",
                "capacity_mw": "25",
            }
        ],
    )
    _write_csv(
        acquisition / "non_gleif/source_rows/equipment_records.csv",
        [
            {
                **provenance,
                "source_type": "eia",
                "sheet_name": "Operating",
                "Nameplate Capacity (MW)": "10.5",
            }
        ],
    )
    _write_csv(
        tmp_path / "data/compute/2026-09-16-expanded/gpu_price_observations.csv",
        [
            {
                **provenance,
                "source_type": "company_ir",
                "observation_id": f"test-gpu-{index}",
                "gpu_generation": "H100",
                "observed_date": "2026-09-16",
                "observed_cloud_rental_rate_usd_per_hour": "3",
            }
            for index in range(87)
        ],
    )
    graph_path = tmp_path / "data/capital_graph_refresh_2026-09-16/ferc_only/input_manifest.json"
    graph_path.parent.mkdir(parents=True)
    graph_path.write_text(
        json.dumps(
            {
                "as_of": "2026-09-16",
                "inputs": {
                    "test_input": {
                        "path": str(queue_path.relative_to(tmp_path)),
                        "bytes": queue_path.stat().st_size,
                    }
                },
                "graph_summary": {"deals_scanned": 1},
                "selection": {"pending_graph_deals": 1},
            }
        )
    )

    result = run(tmp_path)
    physical = result["physical_capacity"]
    assert physical["queue_records_scanned"] == 2
    assert physical["gross_generation_queue_requested_mw"] == 450
    assert physical["skipped_rows"] == {"queue_out_of_scope_status": 1}
    assert physical["tracker_project_records_scanned"] == 1
    assert physical["equipment_records_scanned"] == 1
    assert result["compute_economics"]["gpu_price_observations"] == 87
    assert result["compute_economics"]["payback_case_rows"] == 0
    assert result["bubble_probability"] is None
    assert result["capital_graph"]["ferc_only"]["pending_graph_deals"] == 1
    assert result["capital_graph"]["ferc_only"]["status"] == "input_sizes_match_manifest"
    assert (
        result["input_records"]["physical"][0]["sha256"]
        == hashlib.sha256(queue_path.read_bytes()).hexdigest()
    )


def test_sec_coverage_audit_must_match_inventory(tmp_path: Path) -> None:
    inventory = tmp_path / "data/edgar_acquisition_final_2026-09-16/edgar_document_inventory.csv"
    inventory.parent.mkdir(parents=True)
    inventory.write_text("cik,form,filing_url\n0001,10-Q,https://example.com/one\n")
    audit_path = tmp_path / "data/reports/edgar_coverage.json"
    audit_path.parent.mkdir(parents=True)
    audit = {
        "inventory": str(inventory),
        "input_rows": {"inventory": 1},
        "total": {"requested": 1, "acquired": 1, "missing": 0, "errors": 0},
        "manifests": ["manifest.csv"],
        "manifest_discovery_errors": [],
        "coverage_definition": "Exact URL match only.",
    }
    audit_path.write_text(json.dumps(audit))
    result = summarize_sec_inventory(tmp_path, audit_path, inventory)
    assert result["status"] == "exact_url_coverage_audited"
    assert result["coverage_audit"]["total"]["missing"] == 0
    assert result["path"] == "data/edgar_acquisition_final_2026-09-16/edgar_document_inventory.csv"
    wrong_inventory = tmp_path / "data/edgar_acquisition_2026-09-16/edgar_document_inventory.csv"
    wrong_inventory.parent.mkdir(parents=True)
    wrong_inventory.write_text("cik,form,filing_url\n0002,10-K,https://example.com/two\n")
    with pytest.raises(ValueError, match="different inventory"):
        summarize_sec_inventory(tmp_path, audit_path, wrong_inventory)
    audit["input_rows"]["inventory"] = 2
    audit_path.write_text(json.dumps(audit))
    with pytest.raises(ValueError, match="changed after"):
        summarize_sec_inventory(tmp_path, audit_path, inventory)
