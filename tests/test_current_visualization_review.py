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
