#!/usr/bin/env python3
"""Run existing deterministic components on explicitly dated refreshed evidence."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from bubble.analysis.compute_economics import analyze_compute_economics
from bubble.ingestion.compute.loader import load_compute_economics
from bubble.market_signals import evaluate_signals

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_facility_cashflows import build as build_facilities
from build_refresh_status import build, dated_market
from derive_public_refresh import file_record
from refresh_live_overlay import _demand_baskets, _issuance_latest
from run_dated_engine_2026_09_16 import summarize_financials


def read(path: Path) -> Any:
    return json.loads(path.read_text())


def relationship_summary(root: Path, as_of: str) -> tuple[dict[str, Any], list[Path]]:
    path = root / "analysis" / f"core_relationship_review_{as_of}.json"
    review = read(path)
    if review["as_of"] != as_of:
        raise ValueError("Relationship review date differs from the report cutoff")
    manifest_path = root / review["private_capital_source_manifest"]
    if file_record(manifest_path)["sha256"] != review["private_capital_source_manifest_sha256"]:
        raise ValueError("Private capital source manifest changed after review")
    manifest = read(manifest_path)
    if manifest["as_of"] != as_of or any(
        source["published"] > as_of for source in manifest["sources"]
    ):
        raise ValueError("Private capital source postdates the report cutoff")
    return {
        "as_of": as_of,
        "reviewed_relationships": len(review["relationships"]),
        "private_capital_sources": len(manifest["sources"]),
        "capital_rounds": review.get("capital_rounds", []),
        "credit_facilities": review.get("credit_facilities", []),
        "limits": review["limits"],
    }, [path, manifest_path]


def report(run: Path, root: Path) -> dict[str, Any]:
    as_of = run.name.removeprefix("refresh_")
    status = build(run)
    live_path, live = dated_market(root, as_of)
    panel_path = root / "analysis" / f"case_zero_financials_{as_of}_v4.json"
    cards_path = root / "analysis" / f"issuance_cards_{as_of}.json"
    physical_path = run / "derived_public_current/physical_capacity_summary.json"
    derived_manifest = run / "derived_public_current/input_manifest.json"
    core_path = root / "analysis" / f"core_reassessment_{as_of}.json"
    events_path = root / "analysis" / f"core_financing_events_{as_of}.json"
    expectations_path = root / "viz/expectations.json"
    expectations = read(expectations_path)
    if expectations["as_of"] != as_of or expectations["market_close"] > as_of:
        raise ValueError("Valuation inputs disagree with the report cutoff")
    core = read(core_path)
    if core["as_of"] != as_of:
        raise ValueError("Current core review date differs from the report cutoff")
    relationships, relationship_inputs = relationship_summary(root, as_of)
    demand_path = root / "analysis/demand_trajectory.json"
    cards = read(cards_path)["deals"]
    if any(card.get("date", "") > as_of for card in cards):
        raise ValueError("Issuance card postdates this report")
    signals = evaluate_signals(
        live["credit"],
        live["bdc"],
        cards,
        _issuance_latest(cards, live["credit"]),
        _demand_baskets(date.fromisoformat(as_of)),
        date.fromisoformat(as_of),
    )
    coverage = {signal["id"] for signal in signals}
    gpu = run / "gpu_prices_reparsed"
    with (gpu / "gpu_price_observations.csv").open(newline="") as stream:
        quotes = list(csv.DictReader(stream))
    counts = Counter(row["provider_or_marketplace"] for row in quotes)
    expected = {"CoreWeave", "Lambda", "Modal", "RunPod"}
    if set(counts) != expected or read(gpu / "gpu_pricing_acquisition.summary.json")["errors"]:
        raise ValueError("Incomplete parsed GPU provider coverage")
    compute = analyze_compute_economics(load_compute_economics(gpu)).to_dict()
    facility_input = root / "analysis" / f"facility_inputs_{as_of}.json"
    facilities = build_facilities(facility_input, root) if facility_input.is_file() else None
    graphs: dict[str, Any] = {}
    inputs = [
        live_path,
        panel_path,
        cards_path,
        physical_path,
        derived_manifest,
        core_path,
        events_path,
        expectations_path,
        gpu / "gpu_price_observations.csv",
        demand_path,
        *relationship_inputs,
    ]
    replacements = run / "edgar_merged_current/source_document_replacements.json"
    if replacements.exists():
        inputs.append(replacements)
    if facilities is not None:
        inputs.append(facility_input)
    for mode in ("complete", "ferc_only", "ownership_current"):
        path = root / "data" / f"capital_graph_refresh_{as_of}" / mode / "input_manifest.json"
        if path.exists():
            manifest = read(path)
            if manifest["as_of"] != as_of:
                raise ValueError(f"Graph date mismatch: {path}")
            graphs[mode] = {
                "summary": manifest["graph_summary"],
                "selection": manifest.get("selection"),
                "input_manifest": file_record(path),
            }
            inputs.append(path)
        else:
            graphs[mode] = {"status": "not_run"}
    missing = sorted(
        {
            "S1_new_issue_spread",
            "S1b_failed_print",
            "S2_ccc_divergence",
            "S3_bdc_discount_differential",
            "S4_demand_trajectory",
        }
        - coverage
    )
    return {
        "as_of_pacific": as_of,
        "snapshot_at_pacific": status["snapshot_at_pacific"],
        "acquisition_complete": status["complete"],
        "input_records": [file_record(path) for path in inputs],
        "source_freshness": status,
        "registered_market": {
            "components": signals,
            "unmeasured": missing,
            "issuance_cards_latest_date": max(
                (card.get("date", "") for card in cards), default=None
            ),
            "limits": [
                "Registered components use the existing thresholds and basket memberships.",
                "Issuance cards include reviewed September prints; no exhaustive private issuance census is claimed.",
                "The October primary-source demand review does not establish a comparable annual basket; S4 remains unmeasured.",
                "Compound confirm/kill criteria require the registered adjudication; component output alone does not settle them.",
            ],
        },
        "sec_financial_panel": summarize_financials(read(panel_path), as_of=as_of),
        "source_document_replacements": status["sec_acquisition"].get(
            "source_document_replacements", []
        ),
        "current_core_review": core,
        "current_relationship_review": relationships,
        "subsequent_financing_events": read(events_path),
        "demand_review": read(demand_path).get("current_review"),
        "expectations": expectations,
        "physical_capacity": read(physical_path),
        "public_derivation": read(derived_manifest)["source_selection"],
        "compute_economics": compute,
        "facility_cashflows": facilities,
        "gpu_providers": dict(counts),
        "gpu_observation_dates": sorted({row["observed_date"] for row in quotes}),
        "capital_graph": graphs,
        "bubble_probability": None,
        "limits": [
            "Source retrieval dates and observation dates remain separate.",
            "The dated core review reconciles current issuer statement rows; June confidence judgments are historical and are not recalibrated probabilities.",
            "SEC extraction and FERC candidates remain pending review.",
            "Queue requests, generator capacity and tracker capacity are separate measures.",
            "Contract edge notional repeats across relationships and is not additive debt.",
            "Published GPU list prices do not establish transactions, availability or utilization.",
            "This report has no new bubble probability.",
        ],
    }


def markdown(value: dict[str, Any]) -> str:
    freshness = value["source_freshness"]
    sec = freshness["sec_acquisition"]["new_run_queue"]
    financials = value["sec_financial_panel"]
    derived = value["public_derivation"]
    core = value["current_core_review"]
    lines = [
        f"# Bubble dated engine: {value['as_of_pacific']}",
        "",
        "This snapshot uses refreshed public evidence and the existing deterministic components.",
        f"Selected SEC document acquisition complete: {value['acquisition_complete']}.",
        "",
        f"Market closes: {', '.join(freshness['market']['price_dates'])}. "
        f"Credit observations: {', '.join(freshness['market']['credit_dates'])}. "
        f"Reported BDC NAV periods: {', '.join(freshness['market']['nav_periods'])}.",
        f"Financial panel: {financials['panel_entities']} entities. "
        f"Issuer cash-flow/capex arithmetic is checked against each latest report.",
        f"Primary statement reconciliation: {core['issuer_count']} issuers; "
        f"${core['reported_issuer_debt_usd'] / 1e9:.3f}B of reported borrowing and note carrying amounts, presented in USD. "
        "These consolidated balances include non-AI activities and retain their original reporting periods.",
        f"Reviewed relationships: {value['current_relationship_review']['reviewed_relationships']}; "
        f"private-capital primary sources: {value['current_relationship_review']['private_capital_sources']}. "
        "Funded investments, round commitments and undrawn facility roles retain separate dates and measures.",
        f"Matched current cash-flow and capital-purchase observations: {core['cashflow_observations']}; "
        f"negative cash after capex: {core['negative_cash_after_capex']}. This does not establish insolvency.",
        f"Current FERC PPA records: {derived['ppas']['source_rows']}; "
        f"pending extraction candidates: {derived['ppas']['deals_written']}.",
        f"Deduplicated queue records: {derived['queue_combination']['combined_rows']}.",
        f"GPU list-price observations: {sum(value['gpu_providers'].values())} across "
        f"{len(value['gpu_providers'])} providers.",
        f"SEC new documents acquired: {sec.get('acquired', 0)}; queued/in-flight: "
        f"{sec.get('queued', 0) + sec.get('inflight', 0)}. "
        f"Unresolved source errors: {freshness['sec_acquisition']['unresolved_source_errors']}.",
        f"Verified official source replacements: {len(value.get('source_document_replacements', []))}. Original URL failures remain recorded; actual retrieval URLs and hashes are preserved.",
        "",
        "Registered component results:",
        "",
    ]
    lines += [
        f"- {item['id']}: {item['status']}." for item in value["registered_market"]["components"]
    ]
    lines += [f"- {name}: unmeasured." for name in value["registered_market"]["unmeasured"]]
    if value.get("facility_cashflows"):
        facilities = value["facility_cashflows"]["summary"]
        lines += [
            "",
            "Facility cash flows:",
            "",
            f"- {facilities['facility_cases']} cases across {facilities['issuers_with_cases']} issuers; all {facilities['issuer_count']} reviewed issuers have coverage entries.",
            f"- {facilities['cases_with_interest_run_rate']} dated interest run rates; {facilities['cases_with_contract_average']} base-contract averages.",
            f"- {facilities['cases_with_complete_original_debt_schedule']} original debt schedules contain {facilities['verified_principal_installments']} verified principal installments.",
            f"- {facilities['cases_with_dscr']} measured DSCRs. Matched cash available and complete facility debt perimeters remain unmeasured.",
        ]
    lines += ["", "Limits:", ""]
    lines += [f"- {text}" for text in value["registered_market"]["limits"] + value["limits"]]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    value = report(args.run.resolve(), root)
    for suffix in (".json", ".md"):
        if args.output_prefix.with_suffix(suffix).exists():
            raise FileExistsError(f"Report output exists: {args.output_prefix}{suffix}")
    with args.output_prefix.with_suffix(".json").open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
    with args.output_prefix.with_suffix(".md").open("x") as stream:
        stream.write(markdown(value))
    print(
        json.dumps(
            {
                "as_of": value["as_of_pacific"],
                "acquisition_complete": value["acquisition_complete"],
                "gpu_observations": sum(value["gpu_providers"].values()),
                "source_rows": value["public_derivation"]["ppas"]["source_rows"],
            }
        )
    )


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget(512)
    main()
