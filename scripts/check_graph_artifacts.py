"""CLI parity checker: contagion-graph artifact-edge count (track to 0 after rebuild).

Lists edges whose source/target node is a statute / role-phrase / clause-fragment
artifact (root cause 3). Run before/after wiring the stop-list into
``build_capital_exposure_graph.py`` to confirm the count goes to 0. See
``bubble.quality.risk_bearer_classification.summarize_graph_artifact_edges``.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from bubble.quality.risk_bearer_classification import (
    is_artifact_name,
    summarize_graph_artifact_edges,
)


def main() -> None:
    path = Path("data/graph/capital_exposure_edges.csv")
    with path.open(newline="") as handle:
        edges = list(csv.DictReader(handle))
    summary = summarize_graph_artifact_edges(edges)
    print(json.dumps(summary, indent=2))
    for edge in edges:
        target = str(edge.get("target_id") or "")
        source = str(edge.get("source_id") or "")
        if is_artifact_name(target) or is_artifact_name(source):
            print(f"  {source} -> {target}  ({edge.get('notional_usd')})")


if __name__ == "__main__":
    main()
