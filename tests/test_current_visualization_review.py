from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts.update_current_visualization import apply_review

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    # The checked-in source review is the financial contract for this visualization.
    graph = json.loads((ROOT / "viz/graph_data.json").read_text())
    review = json.loads((ROOT / "analysis/core_reassessment_2026-10-17.json").read_text())
    relationships = json.loads(
        (ROOT / "analysis/core_relationship_review_2026-10-17.json").read_text()
    )
    events = json.loads((ROOT / "analysis/core_financing_events_2026-10-17.json").read_text())
    return graph, review, relationships, events


def test_reapplying_review_preserves_sources_field_and_history_without_growth():
    graph, review, relationships, events = inputs()
    history = copy.deepcopy(graph["historical_core"])
    field = copy.deepcopy(graph["field"])
    apply_review(graph, review, relationships, events)
    first = copy.deepcopy(graph)
    apply_review(graph, review, relationships, events)
    assert graph == first
    assert graph["field"] == field
    assert graph["historical_core"] == history


def test_different_financial_measures_and_terminated_relationships_stay_separate():
    graph, review, relationships, events = inputs()
    apply_review(graph, review, relationships, events)
    nodes = {n["id"]: n for n in graph["nodes"]}
    edges = {(e["from"], e["to"]): e for e in graph["edges"]}
    assert sum(n["usd"] for n in nodes.values() if n["type"] == "issuer") == 90_184_580_000
    assert edges["NVIDIA", "SB Energy"]["usd"] == 105_000_000_000
    assert nodes["SB Energy"]["usd"] is None
    assert edges["Hut 8", "Coatue"]["usd"] is None
    assert edges["Hut 8", "Coatue"]["type"] == "converted_note"
    assert edges["CoreWeave", "Wilmington Trust"]["tier"] == "unconfirmed"
    assert edges["TeraWulf", "Wilmington Trust"]["type"] == "trustee"
    assert graph["meta"]["core_confidence"] is None
    assert graph["cascade"]["hops"][0]["usd"] == nodes["CoreWeave"]["usd"]


def test_later_investment_disclosures_supersede_announcements_without_inflating_debt():
    graph, review, relationships, events = inputs()
    apply_review(graph, review, relationships, events)
    nodes = {node["id"]: node for node in graph["nodes"]}
    edges = {(edge["from"], edge["to"]): edge for edge in graph["edges"]}
    amazon = edges["Amazon", "OpenAI"]
    assert amazon["usd"] == amazon["funded_by_period_end_usd"] + amazon["funded_subsequently_usd"]
    assert amazon["usd"] == 50_000_000_000
    assert edges["SoftBank", "OpenAI"]["usd"] == 64_600_000_000
    assert edges["Amazon", "Anthropic"]["usd"] == 18_000_000_000
    assert edges["Amazon", "Anthropic"]["remaining_conditional_facility_usd"] == 15_000_000_000
    assert edges["Anthropic", "Amazon"]["amount_is_lower_bound"]
    assert graph["meta"]["reported_issuer_debt_usd"] == 90_184_580_000
    assert all(nodes[name]["usd"] is None for name in ("OpenAI", "Anthropic", "Amazon", "SoftBank"))
    assert all(nodes[name]["fragility"] is None for name in ("Amazon", "SoftBank", "Cerebras"))
    assert edges["Google", "Anthropic"]["usd"] is None
    assert nodes["Amazon Energy"]["id"] != nodes["Amazon"]["id"]
    assert all(edge[side] in nodes for edge in graph["edges"] for side in ("from", "to"))
    assert all(nodes[name]["sources"] for name in ("Amazon", "SoftBank", "Cerebras", "Anthropic"))


def test_shared_facility_and_round_participants_do_not_invent_individual_allocations():
    graph, review, relationships, events = inputs()
    apply_review(graph, review, relationships, events)
    facility = graph["credit_facilities"][0]
    assert facility["commitment_usd"] == 4_700_000_000
    assert facility["drawn_at_close_usd"] == 0
    assert facility["subsequent_draws_usd"] is None
    roles = [edge for edge in graph["edges"] if edge.get("shared_facility_id") == facility["id"]]
    assert {edge["to"] for edge in roles} == set(facility["participants"])
    assert len(roles) == 11
    assert all(edge["usd"] is None for edge in roles)
    participants = [edge for edge in graph["edges"] if edge["type"] == "funding_round_participant"]
    assert participants
    assert all(edge["usd"] is None for edge in participants)
    rounds = {row["id"]: row for row in graph["capital_rounds"]}
    assert rounds["openai-2026-march"]["basis"] == "committed capital"
    assert rounds["anthropic-2026-series-h"]["previously_committed_included_usd"] == 15_000_000_000
    assert any(edge["from"] == "Morgan Stanley Investment Management" for edge in participants)
