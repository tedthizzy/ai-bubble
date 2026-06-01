#!/usr/bin/env python
"""
Bulk Ingestion Script for Go Big Mode.

Processes EDGAR filers to build source-backed coverage.

Usage:
    uv run python scripts/bulk_ingest.py --limit 50
    uv run python scripts/bulk_ingest.py --all-public
    uv run python scripts/build_edgar_manifest.py --since 2024-01-01
"""

from __future__ import annotations

import argparse
import time
from typing import TYPE_CHECKING, Any

from bubble.graph.client import get_graph_client
from bubble.ingestion.edgar.extractor import EdgarExtractor
from bubble.ingestion.edgar.seeds import PUBLIC_SEEDS, WATCHLIST_CIKS

if TYPE_CHECKING:
    from collections.abc import Sequence


def bulk_ingest(
    ciks: Sequence[str],
    limit: int | None = None,
    sleep_seconds: float = 1.5,
) -> dict[str, Any]:
    """
    Ingest a list of CIKs with rate limiting.
    Returns summary stats.
    """
    extractor = EdgarExtractor()
    graph = get_graph_client()
    graph.bootstrap_schema()

    results: list[dict[str, Any]] = []
    processed = 0
    target = limit or len(ciks)

    for cik in ciks[:target]:
        try:
            print(f"Processing CIK {cik} ({PUBLIC_SEEDS.get(cik, {}).get('name', 'Unknown')})...")
            extraction = extractor.extract_from_cik(cik)
            entity = extraction["entity"]

            graph.merge_entity(entity)
            for deal in extraction.get("deals", []):
                graph.merge_deal(deal)

            # Auto-queue high severity risks
            for risk in extraction.get("risks", []):
                if risk.severity >= 0.85:
                    graph.add_to_review_queue(
                        "Risk",
                        str(risk.id),
                        risk.title,
                        risk.severity,
                        priority=150,
                    )

            results.append(
                {
                    "cik": cik,
                    "name": entity.name,
                    "deals": len(extraction.get("deals", [])),
                    "risks": len(extraction.get("risks", [])),
                    "llm_used": extraction.get("llm_used", False),
                }
            )
            processed += 1

        except Exception as e:
            print(f"  Error on {cik}: {e}")
            results.append({"cik": cik, "error": str(e)})

        time.sleep(sleep_seconds)  # Be polite to SEC

    return {
        "processed": processed,
        "results": results,
        "graph_nodes_after": len(graph.query_nodes()) if hasattr(graph, "query_nodes") else "N/A",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Max number of CIKs to process")
    parser.add_argument("--all-public", action="store_true", help="Process all known public CIKs")
    args = parser.parse_args()

    ciks = WATCHLIST_CIKS if args.all_public else list(PUBLIC_SEEDS.keys())

    print(
        f"Starting bulk ingest on {min(args.limit or len(ciks), len(ciks))} filers (Go Big mode)..."
    )
    summary = bulk_ingest(ciks, limit=args.limit)

    print("\n=== Bulk Ingest Summary ===")
    print(f"Processed: {summary['processed']}")
    print(f"Graph nodes after run: {summary.get('graph_nodes_after')}")
    print(f"Sample results: {summary['results'][:3]}")
    print(
        "\nNext: build/download the source corpus with `just edgar-manifest` and `just edgar-acquire`."
    )

    print("\nTip: Run `bubble ui` or `just ui` to explore the growing map.")
    print("High-volume mode: Use --all-public (respect rate limits).")


if __name__ == "__main__":
    main()
