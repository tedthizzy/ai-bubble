#!/usr/bin/env python
"""Build source-backed capital exposure graph artifacts from acquired deal rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import TYPE_CHECKING

from bubble.analysis.ai_direct_graph_edges import build_ai_direct_deals
from bubble.analysis.capital_exposure_graph import (
    build_capital_exposure_graph,
    write_capital_exposure_graph,
)
from bubble.ingestion.capital import CapitalEvidenceBatch, load_capital_evidence

if TYPE_CHECKING:
    from bubble.models.deal import Deal


def load_ai_direct_cluster_deals() -> list[Deal]:
    """Source-backed AI-direct cluster deals from the verified census + contagion fixtures.

    Injects the financed neocloud cluster (its debt, lenders, GPU supplier, and
    anchor customers) into the production graph, whose bulk-feed AI-infra mass
    would otherwise be only ~$5B (Equinix). Missing fixtures are non-fatal.
    """

    census_path = Path("handoffs/ai_direct_debt_census_20260603.json")
    contagion_path = Path("handoffs/ai_direct_contagion_edges_20260603.json")
    if not (census_path.exists() and contagion_path.exists()):
        return []
    try:
        census = json.loads(census_path.read_text())
        contagion = json.loads(contagion_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    return build_ai_direct_deals(census, contagion)


def load_deals_from_data_dirs(data_dirs: list[Path]) -> CapitalEvidenceBatch:
    """Load and dedupe report-ready capital evidence from known data directories."""

    seen: set[tuple[str, str]] = set()
    deals = []
    for root in data_dirs:
        for directory in (root / "capital", root / "edgar_acquisition"):
            if not (directory / "deals.csv").exists():
                continue
            batch = load_capital_evidence(directory)
            for deal in batch.deals:
                key = (deal.source_deal_id or str(deal.id), deal.provenance.source_uri)
                if key in seen:
                    continue
                seen.add(key)
                deals.append(deal)
    return CapitalEvidenceBatch(deals=deals)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        action="append",
        type=Path,
        default=None,
        help="Data root to scan; may be supplied more than once.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/graph"))
    args = parser.parse_args()

    data_dirs = args.data_dir or [Path("data")]
    batch = load_deals_from_data_dirs(data_dirs)
    cluster_deals = load_ai_direct_cluster_deals()
    graph = build_capital_exposure_graph([*batch.deals, *cluster_deals])
    outputs = write_capital_exposure_graph(graph, args.output_dir)
    print(
        json.dumps(
            {
                **graph.summary.to_dict(),
                "outputs": outputs,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
