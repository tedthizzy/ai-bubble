"""
Prefect flow: Daily delta EDGAR ingest + re-analysis for watchlist.

This is the foundation for the "continuous monitoring, updating & alerting" requirement.
"""

from __future__ import annotations

from prefect import flow, task

from bubble.graph.client import get_graph_client
from bubble.ingestion.edgar.extractor import EdgarExtractor
from bubble.ingestion.edgar.seeds import WATCHLIST_CIKS


@task
def ingest_and_analyze_cik(cik: str) -> dict[str, int | str]:
    extractor = EdgarExtractor()
    result = extractor.extract_from_cik(cik)
    ent = result["entity"]

    graph = get_graph_client()
    graph.merge_entity(ent)
    for d in result.get("deals", []):
        graph.merge_deal(d)

    # Auto-queue high severity items
    for r in result.get("risks", []):
        if r.severity >= 0.85:
            graph.add_to_review_queue("Risk", str(r.id), r.title, r.severity, priority=150)

    return {"entity": ent.name, "risks": len(result.get("risks", []))}


@flow(name="bubble-daily-edgar-delta")
def daily_edgar_delta(watchlist: list[str] | None = None) -> list[dict[str, int | str]]:
    watchlist = watchlist or WATCHLIST_CIKS
    results: list[dict[str, int | str]] = []
    for cik in watchlist:
        res = ingest_and_analyze_cik(cik)
        results.append(res)
    return results


if __name__ == "__main__":
    daily_edgar_delta()
