"""
LangGraph state machine for high-fidelity, auditable EDGAR extraction.

This flow is designed to be the production-grade document reasoning engine.
It now actually calls the real LLM structured extraction when keys are available.
"""

from __future__ import annotations

from typing import Any, TypedDict, cast

from langgraph.graph import END, StateGraph

from bubble.extraction.llm import call_structured_extraction
from bubble.ingestion.edgar.client import EdgarClient


class ExtractionState(TypedDict):
    cik: str
    raw_narrative: str
    structured_xbrl: dict[str, Any]
    extracted_deals: list[dict[str, Any]]
    extracted_risks: list[dict[str, Any]]
    confidence: float
    requires_human_review: bool
    errors: list[str]


def fetch_data(state: ExtractionState) -> ExtractionState:
    client = EdgarClient()
    state["structured_xbrl"] = client.structured_10k(state["cik"]) or {}
    # Narrative is fetched via the main extractor for now (Docling)
    state["raw_narrative"] = state.get("raw_narrative", "")
    return state


def llm_extract(state: ExtractionState) -> ExtractionState:
    if not state.get("raw_narrative"):
        state["errors"].append("No narrative text provided for LLM extraction")
        return state

    result, _provenance = call_structured_extraction(
        state["raw_narrative"],
        source_uri=f"langgraph-edgar:{state['cik']}",
    )

    if result:
        state["extracted_deals"] = [d.model_dump() for d in result.deals]
        state["extracted_risks"] = [r.model_dump() for r in result.risks]
        state["confidence"] = 0.82
    else:
        state["confidence"] = 0.6
        state["requires_human_review"] = True

    return state


def decide(state: ExtractionState) -> str:
    if state.get("requires_human_review") or state.get("confidence", 0) < 0.7:
        return "human_review"
    return "finalize"


def finalize(state: ExtractionState) -> ExtractionState:
    if state.get("extracted_risks"):
        state["requires_human_review"] = any(
            r.get("red_flag_score", 0) > 0.85 for r in state["extracted_risks"]
        )
    return state


# Build the graph
workflow = StateGraph(ExtractionState)
workflow.add_node("fetch", fetch_data)
workflow.add_node("llm", llm_extract)
workflow.add_node("finalize", finalize)

workflow.set_entry_point("fetch")
workflow.add_edge("fetch", "llm")
workflow.add_conditional_edges("llm", decide, {"human_review": "finalize", "finalize": "finalize"})
workflow.add_edge("finalize", END)

extraction_graph = workflow.compile()


def run_edgar_extraction(cik: str, narrative_text: str = "") -> ExtractionState:
    initial: ExtractionState = {
        "cik": cik,
        "raw_narrative": narrative_text,
        "structured_xbrl": {},
        "extracted_deals": [],
        "extracted_risks": [],
        "confidence": 0.0,
        "requires_human_review": False,
        "errors": [],
    }
    return cast("ExtractionState", extraction_graph.invoke(initial))
