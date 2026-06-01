#!/usr/bin/env python
"""Build source-backed capital exposure graph artifacts from acquired deal rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.analysis.capital_exposure_graph import (
    build_capital_exposure_graph,
    write_capital_exposure_graph,
)
from bubble.ingestion.capital import CapitalEvidenceBatch, load_capital_evidence


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
    graph = build_capital_exposure_graph(batch.deals)
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
