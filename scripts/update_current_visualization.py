#!/usr/bin/env python3
"""Apply a dated primary-source review while retaining the original graph evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ISSUERS = {
    "CRWV": "CoreWeave",
    "WULF": "TeraWulf",
    "IREN": "IREN",
    "APLD": "Applied Digital",
    "HUT": "Hut 8",
    "MARA": "MARA Holdings",
    "CLSK": "CleanSpark",
    "GLXY": "Galaxy Digital",
    "NBIS": "Nebius",
    "CORZ": "Core Scientific",
    "CIFR": "Cipher Mining",
    "BTBT": "Bit Digital",
    "BTDR": "Bitdeer",
}


def apply_review(  # noqa: PLR0912, PLR0915 - one reviewed reconciliation of the preserved graph
    graph: dict[str, Any],
    review: dict[str, Any],
    relationships: dict[str, Any],
    events: dict[str, Any] | None = None,
) -> None:
    if review["as_of"] != relationships["as_of"]:
        raise ValueError("Financial and relationship review cutoffs differ")
    as_of = review["as_of"]
    historical = graph.setdefault(
        "historical_core",
        copy.deepcopy(
            {
                key: value
                for key, value in graph.items()
                if key not in {"field", "layout", "historical_core"}
            }
        ),
    )
    history_date = historical["meta"]["generated_from"]
    historical_stamp = re.search(r"(20\d{2})(\d{2})(\d{2})", history_date)
    historical_as_of = "-".join(historical_stamp.groups()) if historical_stamp else None
    graph["meta"] = {
        "as_of": as_of,
        "generated_from": f"core_reassessment_{as_of}",
        "current_review": True,
        "headline": "Bubble",
        "answer": review["current_findings"]["bubble_classification"],
        "core_verdict": "financing_dependence_and_customer_concentration_observed",
        "core_verdict_label": "Financing dependence and customer concentration",
        "core_confidence": None,
        "ecosystem_confidence": None,
        "reported_issuer_debt_usd": review["reported_issuer_debt_usd"],
        "issuer_count": review["issuer_count"],
        "debt_measure": "Consolidated borrowing and note carrying amounts, reported in USD; latest reported period per issuer.",
        "cashflow_observations": review["cashflow_observations"],
        "negative_cash_after_capex": review["negative_cash_after_capex"],
        "historical_report": history_date,
        "historical_as_of": historical_as_of,
        "historical_core_confidence": historical["meta"].get("core_confidence"),
        "historical_ecosystem_confidence": historical["meta"].get("ecosystem_confidence"),
        "cascade_debt_at_risk_usd": next(
            row["reported_debt_usd"]
            for row in review["issuer_observations"]
            if row["ticker"] == "CRWV"
        ),
        "honest_caveats": review["limits"]
        + relationships["limits"]
        + [
            "Financial statements have their stated period ends, mostly June 30 and Applied Digital August 31. Subsequent financing events are separate from those balances.",
            "Node colors retain historical judgments. The current review does not produce calibrated risk scores.",
            "The cascade is a scenario. It does not establish a customer-specific debt loss or ultimate creditor holdings.",
        ],
    }
    by_id = {row["id"]: row for row in graph["nodes"]}
    for row in graph["nodes"]:
        row.update(
            usd=None,
            amount_label=None,
            note="Retained historical graph participant. Current exposure is not quantified in this review.",
            sources=[],
        )
    for item in review["issuer_observations"]:
        identifier = ISSUERS[item["ticker"]]
        node = by_id.get(identifier)
        if node is None:
            node = {"id": identifier, "label": identifier, "type": "issuer", "fragility": None}
            graph["nodes"].append(node)
            by_id[identifier] = node
        cash = item["cash_after_capex"]
        note = f"Reported consolidated borrowing and note balances at {item['period_end']}."
        if cash:
            note += f" Cash after capex: {'-' if cash['value_usd'] < 0 else ''}${abs(cash['value_usd']) / 1e9:.3f}B over {cash['start']} to {cash['end']}."
        node.update(
            usd=item["reported_debt_usd"],
            amount_label=f"reported debt / {item['period_end']}",
            note=note,
            ticker=item["ticker"],
            review_as_of=as_of,
            sources=[{"source_uri": item["source_uri"], "filing_date": item["filing_date"]}],
        )
        if item.get("excluded_components"):
            node["note"] += " " + " ".join(row["reason"] for row in item["excluded_components"])
    by_id["CoreWeave"]["note"] += (
        " Largest Q2 customer: 36%, anonymously disclosed. The old Microsoft 67% claim does not describe this quarter."
    )
    by_id["Core Scientific"]["note"] += (
        " The merger ended October 30, 2025. The old term loan was repaid in May 2026."
    )
    by_id["Cipher Mining"]["label"] = "Cipher Digital (CIFR)"
    if events:
        if events["as_of"] != as_of or any(
            row["date"] > as_of or row["filing_date"] > as_of for row in events["events"]
        ):
            raise ValueError("Financing event postdates the review cutoff")
        graph["financing_events"] = copy.deepcopy(events)
        for event in events["events"]:
            node = by_id[ISSUERS[event["ticker"]]]
            node["note"] += " " + event["date"] + ": " + event["note"]
            node["sources"].append(
                {"source_uri": event["source_uri"], "filing_date": event["filing_date"]}
            )
    notes = {
        "NVIDIA": "GPU supplier, customer equity investor and conditional guarantor. Each relationship carries its own measure and date.",
        "OpenAI": "Private AI company and compute customer. Announced funding, contract ceilings and funded installments are separate measures.",
        "Microsoft": "Cloud supplier, compute customer and OpenAI investor. Its June 30 filing reports $11.9B funded against $13B committed.",
        "Meta": "Compute customer. April 2026 CoreWeave agreement covers approximately $21B of capacity through December 2032.",
        "Coatue": "Hut 8's convertible note fully converted in May 2026. Current share ownership is not measured here.",
        "Morgan Stanley": "Named agent, arranger or initial purchaser on reviewed instruments. These roles do not identify ultimate note ownership.",
        "Wilmington Trust": "Named trustee and collateral agent. These roles do not establish beneficial creditor exposure.",
        "Goldman Sachs": "Named arranger on Hut 8's September 2026 revolving facility. Its retained funding share is not measured.",
        "Magnetar": "CoreWeave reports a remaining MagAI capacity-related debt obligation of $189M at June 30.",
    }
    for identifier, note in notes.items():
        by_id[identifier]["note"] = note
    for identifier, node_type, note in [
        (
            "SB Energy",
            "project_developer",
            "PORTS developer and lessor. NVIDIA's $105B guarantee cap is conditional and separate from funded issuer debt.",
        ),
        (
            "Deutsche Bank",
            "lender",
            "Named lender for Galaxy Helios I's construction facility. June 30 drawn principal: $1.3B.",
        ),
        (
            "JPMorgan Chase",
            "lender",
            "Named agent for Hut 8 and Core Scientific facilities. Expected Bitdeer/Volta credit support is conditional; beneficial lending allocations are not measured.",
        ),
        (
            "Google",
            "lease_guarantor",
            "Provider of specified lease-payment backstops. Conditions and scope differ by contract; these are separate from funded issuer debt.",
        ),
        (
            "Fluidstack",
            "tenant",
            "Tenant and joint-venture participant through named affiliates. Each subsidiary and contract has distinct obligations.",
        ),
        (
            "Anthropic",
            "compute_customer",
            "Private AI company and named customer under TeraWulf's July 2026 datacenter lease.",
        ),
        (
            "AMD",
            "supplier_offtaker",
            "Compute hardware supplier and named Core Scientific datacenter lease customer.",
        ),
        ("Coinbase Credit", "lender", "Named lender on MARA's August bitcoin-backed USD facility."),
        (
            "Two Prime Lending",
            "lender",
            "Named lender on MARA's August bitcoin-backed USD facility.",
        ),
        (
            "Royal Bank of Canada",
            "lender",
            "Named participant in Enovum/WhiteFiber's RBC syndicated financing. Individual lender allocation is not measured.",
        ),
        (
            "BIT Group",
            "lender",
            "Related-party lender named by Bitdeer. Its USD facilities and Bitcoin loan are separate obligations.",
        ),
        (
            "Volta Tydal",
            "tenant",
            "Named Bitdeer Tydal tenant. The 16-year base lease permits termination at year ten; anticipated credit support remains conditional.",
        ),
    ]:
        if identifier not in by_id:
            node = {
                "id": identifier,
                "label": identifier,
                "type": node_type,
                "fragility": None,
                "usd": None,
                "amount_label": None,
                "sources": [],
                "note": note,
            }
            graph["nodes"].append(node)
            by_id[identifier] = node
        by_id[identifier]["note"] = note
    for participant in relationships.get("participants", []):
        identifier = participant["id"]
        if identifier not in by_id:
            node = {
                "id": identifier,
                "label": identifier,
                "type": participant["type"],
                "fragility": None,
                "usd": None,
                "amount_label": None,
                "sources": [],
            }
            graph["nodes"].append(node)
            by_id[identifier] = node
        by_id[identifier].update(
            note=participant["note"],
            review_as_of=as_of,
        )
    updates = {(row["from"], row["to"]): row for row in relationships["relationships"]}
    seen = set()
    for index, edge in enumerate(graph["edges"]):
        key = edge["from"], edge["to"]
        if key in updates:
            graph["edges"][index] = copy.deepcopy(updates[key])
            seen.add(key)
        else:
            edge.update(
                usd=None,
                tier="unconfirmed",
                review_as_of=as_of,
                sources=[],
                note="Historical relationship or scenario retained for review. Current named counterparty exposure was not verified in the selected statements and event filings. "
                + relationships["unconfirmed_scope"],
            )
    graph["edges"].extend(copy.deepcopy(value) for key, value in updates.items() if key not in seen)
    for edge in relationships["relationships"]:
        for identifier in (edge["from"], edge["to"]):
            by_id[identifier]["sources"].extend(copy.deepcopy(edge.get("sources", [])))
    for node in graph["nodes"]:
        node["sources"] = list({row["source_uri"]: row for row in node.get("sources", [])}.values())
    graph["capital_rounds"] = copy.deepcopy(relationships.get("capital_rounds", []))
    graph["credit_facilities"] = copy.deepcopy(relationships.get("credit_facilities", []))
    graph["cascade"] = {
        "trigger": "OpenAI",
        "trigger_note": "Scenario: OpenAI demand withdraws.",
        "honest_label": "CoreWeave's entire reported debt is a gross scenario bound. Customer-specific losses, recoveries and creditor holdings are unmeasured.",
        "hops": [
            {
                "hop": 1,
                "nodes": ["CoreWeave"],
                "usd": graph["meta"]["cascade_debt_at_risk_usd"],
                "label": "CoreWeave total reported debt; gross scenario bound",
            },
            {
                "hop": 2,
                "nodes": [
                    "Core Scientific",
                    "Applied Digital",
                    "Galaxy Digital",
                    "Morgan Stanley",
                    "Magnetar",
                    "NVIDIA",
                ],
                "label": "Named contractual and financing connections; loss allocation unmeasured",
            },
            {
                "hop": 3,
                "nodes": ["Wilmington Trust", "Deutsche Bank"],
                "label": "Named financing roles; beneficial creditor holdings unmeasured",
            },
        ],
    }
    graph["fragility"] = {
        "as_of": as_of,
        "met": [
            "Core Scientific's single colocation customer represents about 83.2% of Q2 revenue."
        ],
        "unmeasured": [
            "GPU economic life",
            "Current cohort-wide maturity/asset-life mismatch",
            "Ultimate beneficial creditor exposure",
        ],
        "funding_requirement": f"{review['negative_cash_after_capex']} of {review['cashflow_observations']} reviewed issuers report negative cash after capex.",
    }
    graph["refi_wall"] = {
        **historical.get("refi_wall", {}),
        "evidence_date": history_date,
        "current_recomputed": False,
    }
    graph["chokepoints"] = {
        **historical.get("chokepoints", {}),
        "evidence_date": history_date,
        "current_recomputed": False,
    }
    graph["legend"]["node_types"].update(
        issuer="Issuer / consolidated statement balances",
        lender="Named financing participant; role shown on each connection",
        project_developer="Project developer / lessor",
        lease_guarantor="Lease-payment backstop provider",
        tenant="Tenant / named affiliates",
        compute_customer="Compute customer",
        supplier_offtaker="Hardware supplier / capacity customer",
        investor="Named round participant; individual allocation may be undisclosed",
    )
    graph["legend"]["edge_tiers"].update(
        issuer_announced="Issuer announcement; measure stated separately",
        historical="Historical relationship",
        unconfirmed="Unconfirmed current relationship / scenario",
    )
    graph["legend"]["fragility"] = (
        "Historical judgment colors. Node sizes use separately labeled measures; unknown amounts are unmeasured."
    )
    graph["review_sources"] = {
        "financial": f"analysis/core_reassessment_{as_of}.json",
        "relationships": f"analysis/core_relationship_review_{as_of}.json",
    }
    if graph.get("field") and (
        "evidence_date" not in graph["field"] or graph["field"].get("evidence_date") == history_date
    ):
        graph["field"].update(
            evidence_date=None,
            historical_report_context=history_date,
            cutoff_status="The retained field has no independently verified observation cutoff; its report context is separate.",
        )


def update(root: Path, as_of: str, graph: dict[str, Any] | None = None) -> None:
    graph_path = root / "viz/graph_data.json"
    if graph is None:
        graph = json.loads(graph_path.read_text())
    review_path = root / "analysis" / f"core_reassessment_{as_of}.json"
    relationships_path = root / "analysis" / f"core_relationship_review_{as_of}.json"
    events_path = root / "analysis" / f"core_financing_events_{as_of}.json"
    apply_review(
        graph,
        json.loads(review_path.read_text()),
        json.loads(relationships_path.read_text()),
        json.loads(events_path.read_text()),
    )
    graph["meta"]["review_sha256"] = hashlib.sha256(review_path.read_bytes()).hexdigest()
    graph["meta"]["relationship_review_sha256"] = hashlib.sha256(
        relationships_path.read_bytes()
    ).hexdigest()
    snapshot = root / ".codex/refresh-2026-10-17" / f"before-visualization-update-{time.time_ns()}"
    snapshot.mkdir(parents=True)
    for name in ("graph_data.json", "index.html"):
        shutil.copy2(root / "viz" / name, snapshot / name)
    graph_path.write_text(json.dumps(graph, sort_keys=True, separators=(",", ":")) + "\n")
    fallback = {
        key: value
        for key, value in graph.items()
        if key not in {"field", "layout", "historical_core"}
    }
    fallback["layout"] = {"core": graph.get("layout", {}).get("core", {})}
    index = root / "viz/index.html"
    lines = index.read_text().splitlines()
    matches = [i for i, line in enumerate(lines) if line.startswith("const EMBEDDED = ")]
    if len(matches) != 1:
        raise ValueError("Expected one embedded core fallback")
    lines[matches[0]] = (
        "const EMBEDDED = " + json.dumps(fallback, sort_keys=True, separators=(",", ":")) + ";"
    )
    index.write_text("\n".join(lines) + "\n")
    print(
        json.dumps(
            {
                "as_of": as_of,
                "nodes": len(graph["nodes"]),
                "edges": len(graph["edges"]),
                "reported_issuer_debt_usd": graph["meta"]["reported_issuer_debt_usd"],
                "field_evidence_date": graph.get("field", {}).get("evidence_date"),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True)
    update(ROOT, parser.parse_args().as_of)
