#!/usr/bin/env python3
"""Run the existing, applicable engine components on dated September 16 inputs.

The legacy final-report builder reads June handoffs and embeds June issuer facts.
This driver deliberately names each dated input, does no network I/O, and does
not turn an incomplete registered signal set into a new bubble probability.
Outputs are immutable: select a new --output-prefix for each later rerun.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from bubble.analysis.compute_economics import analyze_compute_economics
from bubble.analysis.physical_capacity import build_physical_capacity_summary
from bubble.ingestion.compute.loader import load_compute_economics
from bubble.market_signals import STALE_DAYS, evaluate_signals

AS_OF = "2026-09-16"
REGISTERED_IDS = (
    "S1_new_issue_spread",
    "S1b_failed_print",
    "S2_ccc_divergence",
    "S3_bdc_discount_differential",
    "S4_demand_trajectory",
)


def _json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def _file_record(path: Path, root: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {
        "path": str(path.relative_to(root)),
        "bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
    }


def _assert_date(payload: dict[str, Any], key: str, path: Path) -> None:
    if payload.get(key) != AS_OF:
        raise ValueError(f"{path}: expected {key}={AS_OF}, got {payload.get(key)!r}")


def evaluate_dated_market(
    market: dict[str, Any], issuance_cards: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Run the unchanged registered functions against the dated observations."""
    _assert_date(market, "as_of_pacific", Path("analysis/market_close_2026-09-16.json"))
    credit = market["credit"]
    bdc = market["bdc"]
    credit_input = {
        "ccc_oas": {
            "value": credit["ccc_oas_pct"],
            "ytd_chg": credit["ccc_ytd_change_pp"],
        },
        "hy_oas": {"value": credit["hy_oas_pct"], "ytd_chg": credit["hy_ytd_change_pp"]},
        "bb_oas": {"value": credit["bb_oas_pct"], "ytd_chg": credit["bb_ytd_change_pp"]},
    }
    bdc_input = {
        symbol: {"discount_pct": quote["discount_pct"]}
        for group in ("exposed", "controls")
        for symbol, quote in bdc[group].items()
    }
    # S1 reads completed prints only; S1b scans every card, including abandoned
    # attempts. Both remain selected observed transactions, not a complete tape.
    cards = issuance_cards or []
    if any(card.get("date", "") > AS_OF for card in cards):
        raise ValueError("Future issuance card in dated run")
    priced_cards = [card for card in cards if card.get("status", "priced") == "priced"]
    latest_card = max(priced_cards, key=lambda card: card.get("date", "")) if priced_cards else None
    treasury = credit.get("ust5y_pct")
    if treasury is not None and credit.get("ust5y_observation_date") != market["credit_observation_date"]:
        raise ValueError("Five-year Treasury observation does not match dated credit observation")
    if latest_card and treasury is not None and latest_card.get("coupon_pct") is not None:
        latest_card = {
            **latest_card,
            "spread_vs_5y_bp": round((latest_card["coupon_pct"] - treasury) * 100),
        }
    # The June S4 basket is deliberately not replayed as a new September YoY print.
    evaluated = evaluate_signals(
        credit_input, bdc_input, cards, latest_card, [], date.fromisoformat(AS_OF)
    )
    by_id = {signal["id"]: signal for signal in evaluated}
    expected = {"S2_ccc_divergence", "S3_bdc_discount_differential"}
    if cards:
        expected.add("S1b_failed_print")
    if latest_card and (
        latest_card.get("spread_vs_5y_bp") is not None
        or (date.fromisoformat(AS_OF) - date.fromisoformat(latest_card["date"])).days
        > STALE_DAYS
    ):
        expected.add("S1_new_issue_spread")
    if set(by_id) != expected:
        raise ValueError(f"Unexpected September registered signal coverage: {sorted(by_id)}")
    if by_id["S2_ccc_divergence"]["status"] != credit["registered_s2_status"]:
        raise ValueError("S2 disagrees with the dated market observation")
    if by_id["S3_bdc_discount_differential"]["status"] != bdc["registered_s3_status"]:
        raise ValueError("S3 disagrees with the dated market observation")
    return {
        "registered_components": [
            by_id.get(signal_id)
            or {
                "id": signal_id,
                "status": "unmeasured",
                "reason": {
                    "S1_new_issue_spread": "No carded completed print with a measurable coupon-versus-five-year-Treasury spread.",
                    "S1b_failed_print": "No carded failed-print observations.",
                    "S4_demand_trajectory": "No comparable roughly annual AI end-demand basket.",
                }[signal_id],
            }
            for signal_id in REGISTERED_IDS
        ],
        "compound_confirm_2": (
            by_id["S2_ccc_divergence"]["status"] == "confirming"
            and by_id["S3_bdc_discount_differential"]["status"] == "confirming"
        ),
        "credit_observation_date": market["credit_observation_date"],
        "bdc_close_date": market["bdc_close_date"],
        "latest_carded_issuance_date": (latest_card or {}).get("date"),
        "latest_carded_issuance_date_basis": (latest_card or {}).get("date_basis"),
        "latest_priced_issuer": (latest_card or {}).get("issuer"),
        "ust5y_pct": treasury,
        "ust5y_observation_date": credit.get("ust5y_observation_date"),
        "issuance_completeness": "Carded prints are not an exhaustive private-SPV issuance universe.",
        "limits": market["measurement_limits"],
    }


def summarize_financials(panel: dict[str, Any]) -> dict[str, Any]:
    _assert_date(panel, "as_of", Path("analysis/case_zero_financials_2026-09-16_v4.json"))
    entities = panel["entities"]
    if len(entities) != panel["target_count"]:
        raise ValueError("SEC financial panel count disagrees with its entity rows")
    issuers = [entity for entity in entities if entity.get("role") == "issuer"]
    observations: list[dict[str, Any]] = []
    for issuer in issuers:
        value = (issuer.get("current_liquidity") or {}).get("cash_after_capex")
        filing = issuer.get("latest_periodic_filing") or {}
        if not value:
            continue
        if value["end"] != filing.get("report_date"):
            raise ValueError(f"Cash flow does not end at latest report: {issuer['ticker']}")
        if abs(value["operating_cash_flow_usd"] - value["cash_capex_usd"] - value["value_usd"]) > 1:
            raise ValueError(f"Cash-after-capex arithmetic failed: {issuer['ticker']}")
        observations.append(
            {
                "ticker": issuer["ticker"],
                "start": value["start"],
                "end": value["end"],
                "operating_cash_flow_usd": value["operating_cash_flow_usd"],
                "cash_capex_usd": value["cash_capex_usd"],
                "cash_after_capex_usd": value["value_usd"],
                "filing_url": filing["url"],
            }
        )
    current = [row for row in observations if row["end"].startswith("2026-")]
    return {
        "panel_entities": len(entities),
        "panel_issuer_entries": len(issuers),
        "issuer_current_2026_matched_cashflow_capex": len(current),
        "issuer_current_2026_negative_cash_after_capex": sum(
            row["cash_after_capex_usd"] < 0 for row in current
        ),
        "issuer_older_matched_cashflow_capex": len(observations) - len(current),
        "issuer_observations": observations,
        "interpretation": "Preselected capital-intensive issuer cohort; no sector prevalence or insolvency inference.",
    }


def run_physical(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Use the production physical rollup on the full, deduplicated PJM set."""
    inputs = {
        "queue_records.csv": root
        / f"data/source_acquisition_{AS_OF}/derived/queue_combined_full_serial_{AS_OF}/source_rows/queue_records.csv",
        "projects.csv": root / f"data/source_acquisition_{AS_OF}/derived/tracker_projects.csv",
        "equipment_records.csv": root
        / f"data/source_acquisition_{AS_OF}/non_gleif/source_rows/equipment_records.csv",
    }
    for path in inputs.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    with tempfile.TemporaryDirectory(prefix="bubble-dated-physical-") as temporary:
        for filename, path in inputs.items():
            (Path(temporary) / filename).symlink_to(path)
        summary = build_physical_capacity_summary([temporary]).to_dict()
    summary.pop("data_dirs", None)  # ephemeral symlink path is not a source.
    # These large raw sums are non-additive and cannot be described as delivered load.
    return summary, [_file_record(path, root) for path in inputs.values()]


def run_compute(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    path = root / f"data/compute/{AS_OF}-expanded/gpu_price_observations.csv"
    if not path.is_file():
        raise FileNotFoundError(path)
    metrics = analyze_compute_economics(load_compute_economics(path.parent)).to_dict()
    return metrics, _file_record(path, root)


def summarize_graph(root: Path) -> dict[str, Any]:
    graph_root = root / f"data/capital_graph_refresh_{AS_OF}"
    output: dict[str, Any] = {}
    for mode in ("complete", "ferc_only", "ownership_current"):
        path = graph_root / mode / "input_manifest.json"
        if not path.is_file():
            output[mode] = {"status": "not_run"}
            continue
        manifest = _json(path)
        _assert_date(manifest, "as_of", path)
        stale: list[str] = []
        for record in manifest["inputs"].values():
            source = Path(record["path"])
            if not source.is_absolute():
                source = root / source
            if not source.is_file() or source.stat().st_size != record["bytes"]:
                stale.append(str(record["path"]))
        summary = manifest["graph_summary"]
        output[mode] = {
            "status": "source_size_changed" if stale else "input_sizes_match_manifest",
            "input_manifest": str(path.relative_to(root)),
            "inputs_with_changed_size": stale,
            "freshness_check": "file existence and size only; source SHA-256 is in the saved manifest",
            "deals_scanned": summary.get("deals_scanned"),
            "nodes": summary.get("nodes"),
            "edges": summary.get("edges"),
            "relationships": summary.get("relationships"),
            "total_edge_notional_usd": summary.get("total_edge_notional_usd"),
            "pending_graph_deals": (manifest.get("selection") or {}).get("pending_graph_deals"),
        }
    return output


def summarize_sec_inventory(
    root: Path,
    coverage_audit: Path | None = None,
    sec_inventory: Path | None = None,
) -> dict[str, Any]:
    path = sec_inventory or root / f"data/edgar_acquisition_{AS_OF}/edgar_document_inventory.csv"
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    if not path.is_file():
        if sec_inventory is not None:
            raise FileNotFoundError(path)
        return {"status": "not_run", "inventory_rows": 0}
    companies: set[str] = set()
    forms: Counter[str] = Counter()
    rows = 0
    with path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            rows += 1
            companies.add(row["cik"])
            forms[row["form"]] += 1
    result = {
        "status": "interim_unless_coverage_audit_confirms_complete",
        "inventory_rows": rows,
        "unique_ciks": len(companies),
        "forms": dict(forms.most_common()),
        "path": str(path.relative_to(root)),
        "caveat": "An inventory row is an acquired document, not a unique obligation or a coverage proof.",
    }
    if coverage_audit is not None:
        audit = _json(coverage_audit)
        audited_path = Path(audit["inventory"])
        if not audited_path.is_absolute():
            audited_path = root / audited_path
        if audited_path.resolve() != path.resolve():
            raise ValueError("SEC coverage audit references a different inventory")
        if audit["input_rows"]["inventory"] != rows:
            raise ValueError("SEC inventory changed after the coverage audit")
        result["status"] = "exact_url_coverage_audited"
        result["coverage_audit"] = {
            "path": str(coverage_audit.relative_to(root)),
            "total": audit["total"],
            "manifests": audit["manifests"],
            "manifest_discovery_error_count": len(audit["manifest_discovery_errors"]),
            "coverage_definition": audit["coverage_definition"],
        }
    return result


def run(
    root: Path,
    coverage_audit: Path | None = None,
    sec_inventory: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    market_path = root / f"analysis/market_close_{AS_OF}.json"
    finance_path = root / f"analysis/case_zero_financials_{AS_OF}_v4.json"
    source_path = root / f"analysis/source_refresh_{AS_OF}.json"
    gpu_delta_path = root / f"analysis/gpu_pricing_delta_{AS_OF}.json"
    issuance_path = root / "analysis/issuance_cards.json"
    sources = _json(source_path)
    _assert_date(sources, "as_of_pacific_date", source_path)
    gpu_delta = _json(gpu_delta_path)
    _assert_date(gpu_delta, "as_of_pacific", gpu_delta_path)
    physical, physical_inputs = run_physical(root)
    compute, compute_input = run_compute(root)
    if compute["gpu_price_observation_count"] != 87:
        raise ValueError("Expanded GPU quote set is incomplete")
    inputs = {
        "market": _file_record(market_path, root),
        "financials": _file_record(finance_path, root),
        "source_refresh": _file_record(source_path, root),
        "gpu_delta": _file_record(gpu_delta_path, root),
        "issuance_cards": _file_record(issuance_path, root),
        "physical": physical_inputs,
        "compute": compute_input,
    }
    if coverage_audit is not None:
        inputs["sec_coverage_audit"] = _file_record(coverage_audit, root)
    selected_sec_inventory = sec_inventory or root / f"data/edgar_acquisition_{AS_OF}/edgar_document_inventory.csv"
    if not selected_sec_inventory.is_absolute():
        selected_sec_inventory = root / selected_sec_inventory
    if selected_sec_inventory.is_file():
        inputs["sec_inventory"] = _file_record(selected_sec_inventory.resolve(), root)
    return {
        "as_of_pacific": AS_OF,
        "method": "Existing registered signal, physical-capacity, and compute-economics functions on explicit dated inputs; no June handoffs.",
        "input_records": inputs,
        "registered_market": evaluate_dated_market(
            _json(market_path), _json(issuance_path)["deals"]
        ),
        "sec_financial_panel": summarize_financials(_json(finance_path)),
        "source_acquisition": sources["acquisition_totals_excluding_sec"],
        "physical_capacity": {
            "queue_records_scanned": physical["queue_records_scanned"],
            "gross_generation_queue_requested_mw": physical["queue_capacity_mw"],
            "data_center_classifier_queue_mw": physical["data_center_queue_capacity_mw"],
            "tracker_project_records_scanned": physical["tracker_project_records_scanned"],
            "equipment_records_scanned": physical["equipment_records_scanned"],
            "skipped_rows": physical["skipped_rows"],
            "interpretation": "Queue MW are gross generation requests; no inference of energized AI load.",
        },
        "compute_economics": {
            "status": compute["status"],
            "gpu_price_observations": compute["gpu_price_observation_count"],
            "asset_rows": compute["compute_asset_count"],
            "depreciation_policy_rows": compute["depreciation_policy_count"],
            "payback_case_rows": compute["payback_case_count"],
            "gpu_depreciation_red_flags": compute["gpu_depreciation_red_flag_count"],
            "price_delta_matched_rows": gpu_delta["matched_observations"],
            "price_delta_direction_counts": gpu_delta["direction_counts"],
            "interpretation": "Listed quotes do not establish transaction prices, utilization, or a 2027 glut.",
        },
        "capital_graph": summarize_graph(root),
        "sec_document_acquisition": summarize_sec_inventory(root, coverage_audit, sec_inventory),
        "bubble_probability": None,
        "conclusion": (
            "Customer demand is measurable and the issuer panel remains cash-investment-intensive. "
            "The selected QTS print makes registered S1 contra while one postponed and one abandoned bond attempt make S1b confirming. "
            "S2 confirms weaker tail credit while S3 is contra, so CONFIRM-2 is false. "
            "Current evidence does not resolve the timing or probability of a system-wide unwind."
        ),
        "engine_boundary": (
            "The legacy final report's June handoff-based verdict, contagion graph, "
            "and hardcoded customer concentration were not executed or relabeled as September results."
        ),
    }


def markdown(report: dict[str, Any]) -> str:
    signals = {s["id"]: s for s in report["registered_market"]["registered_components"]}
    finance = report["sec_financial_panel"]
    physical = report["physical_capacity"]
    compute = report["compute_economics"]
    acquisition = report["source_acquisition"]
    sec = report["sec_document_acquisition"]
    capital = report["capital_graph"]
    return "\n".join(
        [
            f"# Dated engine run: {AS_OF}",
            "",
            report["conclusion"],
            "",
            f"The unchanged registered functions return S1 `{signals['S1_new_issue_spread']['status']}` "
            f"at {signals['S1_new_issue_spread']['value_bp']} basis points, "
            f"S1b `{signals['S1b_failed_print']['status']}`, and S2 `{signals['S2_ccc_divergence']['status']}` "
            f"at {signals['S2_ccc_divergence']['ccc_minus_hy_ytd_pp']:+.2f} percentage points "
            f"and S3 `{signals['S3_bdc_discount_differential']['status']}` at "
            f"{signals['S3_bdc_discount_differential']['differential_pp']:+.1f} points. "
            f"CONFIRM-2 is `{report['registered_market']['compound_confirm_2']}`. "
            "S1 uses the registered coupon-minus-five-year-Treasury proxy: QTS's 6.625% coupon "
            f"minus the September 15 Treasury {report['registered_market']['ust5y_pct']:.2f}% gives "
            f"{signals['S1_new_issue_spread']['value_bp']} basis points. QTS closed August 27; "
            "its public issue price and yield were not verified, and the selected card universe is incomplete. "
            "Bloomberg-reported Prime and Pure bond withdrawals support S1b; Pure separately obtained "
            "bank financing. S4 lacks a new comparable company-stated basket. "
            "No September bubble probability was generated.",
            "",
            f"The SEC XBRL panel checked {finance['panel_entities']} entities. "
            f"Among {finance['panel_issuer_entries']} issuer-labeled panel entries, "
            f"{finance['issuer_current_2026_negative_cash_after_capex']} of "
            f"{finance['issuer_current_2026_matched_cashflow_capex']} with matched 2026 "
            "cash-flow/capex periods had negative cash after capex. "
            f"{finance['issuer_older_matched_cashflow_capex']} additional matched issuer "
            "observation ended before 2026. This preselected cohort is not a sector prevalence estimate.",
            "",
            f"The production physical-capacity function read {physical['queue_records_scanned']:,} "
            f"queue records, {physical['tracker_project_records_scanned']:,} tracker projects, "
            f"and {physical['equipment_records_scanned']:,} equipment rows. Its "
            f"{physical['gross_generation_queue_requested_mw']:,.3f} MW is gross generation "
            "interconnection requests, not energized AI load. "
            f"The data-center classifier covers {physical['data_center_classifier_queue_mw']:,.1f} "
            "MW of queue rows; it is not incremental to the gross queue total.",
            "",
            f"The production compute-economics function read {compute['gpu_price_observations']} "
            f"September listed GPU quotes. {compute['price_delta_matched_rows']} comparable June/September "
            f"quotes had {compute['price_delta_direction_counts']['increase']} increases, "
            f"{compute['price_delta_direction_counts']['decrease']} decrease, and "
            f"{compute['price_delta_direction_counts']['unchanged']} unchanged. "
            f"It has {compute['payback_case_rows']} dated project payback cases and "
            f"{compute['depreciation_policy_rows']} dated depreciation policies, "
            "so it cannot compute a current project payback or book-life gap.",
            "",
            f"The non-SEC catalog acquired {acquisition['acquired']} of "
            f"{acquisition['attempted']} attempted sources. The current SEC document inventory "
            f"contains {sec['inventory_rows']:,} rows. Its coverage status is "
            f"`{sec['status']}`; see the JSON for the exact URL-reconciliation totals. "
            f"The capital graph state is FERC `{capital['ferc_only']['status']}`, "
            f"EDGAR-joined `{capital['complete']['status']}`, "
            f"and GLEIF ownership `{capital['ownership_current']['status']}`. "
            "Pending contract rows and graph edges are not additive debt.",
            "",
            report["engine_boundary"],
            "",
            "Exact input paths and SHA-256 hashes, per-issuer values, signal statuses, and graph "
            "coverage are in the adjacent JSON. This run is an exact URL audit of the saved "
            "inventory; it does not claim complete SEC coverage. Use a new `--output-prefix` "
            "after additional SEC documents or Feed days are acquired.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--coverage-audit", type=Path, help="Exact URL coverage-audit JSON, if run")
    parser.add_argument("--sec-inventory", type=Path, help="Saved SEC inventory to summarize and audit")
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=Path(f"analysis/dated_engine_{AS_OF}_v1"),
        help="Immutable output stem, relative to the repository unless absolute.",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    prefix = args.output_prefix
    if not prefix.is_absolute():
        prefix = root / prefix
    outputs = [prefix.with_suffix(ext) for ext in (".json", ".md")]
    if any(path.exists() for path in outputs):
        raise FileExistsError(f"Refusing to replace dated output: {outputs}")
    coverage_audit = args.coverage_audit
    if coverage_audit is not None and not coverage_audit.is_absolute():
        coverage_audit = root / coverage_audit
    report = run(root, coverage_audit, args.sec_inventory)
    for path in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
    outputs[0].write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    outputs[1].write_text(markdown(report))
    print(
        json.dumps(
            {
                "json": str(outputs[0]),
                "markdown": str(outputs[1]),
                "signals": {
                    s["id"]: s["status"]
                    for s in report["registered_market"]["registered_components"]
                },
                "sec_inventory_rows": report["sec_document_acquisition"]["inventory_rows"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
