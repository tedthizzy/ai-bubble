#!/usr/bin/env python3
"""Cache a deterministic 3D layout so the browser does no background simulation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import time
from pathlib import Path
from typing import Any

import networkx as nx


def layout_input(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "algorithm": "spring-energy-3d-v1",
        "nodes": [node["id"] for node in data["nodes"]],
        "edges": [(edge["from"], edge["to"]) for edge in data["edges"]],
        "field_nodes": [row[0:1] + row[3:4] for row in data.get("field", {}).get("nodes", [])],
        "field_links": [row[:2] for row in data.get("field", {}).get("links", [])],
    }


def build_layout(data: dict[str, Any]) -> dict[str, Any]:
    source = layout_input(data)
    fingerprint = hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()
    current = data.get("layout", {})
    if current.get("input_sha256") == fingerprint:
        return current
    graph = nx.Graph()
    core = {node["id"] for node in data["nodes"]}
    graph.add_nodes_from(sorted(core))
    field = data.get("field", {})
    field_ids = [
        row[3] if len(row) > 3 and row[3] in core else f"f{i}"
        for i, row in enumerate(field.get("nodes", []))
    ]
    graph.add_nodes_from(field_ids)
    for row in field.get("links", []):
        if 0 <= row[0] < len(field_ids) and 0 <= row[1] < len(field_ids):
            graph.add_edge(field_ids[row[0]], field_ids[row[1]], weight=1)
    for edge in data["edges"]:
        if edge["from"] in core and edge["to"] in core:
            graph.add_edge(edge["from"], edge["to"], weight=12)
    started = time.monotonic()
    points = nx.spring_layout(graph, dim=3, seed=14, iterations=80, method="energy", scale=650)
    center = [
        sum(float(points[node][axis]) for node in core) / max(1, len(core)) for axis in range(3)
    ]
    positions = {
        node: [round(float(value) - center[axis], 2) for axis, value in enumerate(point)]
        for node, point in points.items()
    }
    assert all(math.isfinite(value) for position in positions.values() for value in position)
    return {
        "algorithm": source["algorithm"],
        "input_sha256": fingerprint,
        "field": [positions[node] for node in field_ids],
        "core": {node: positions[node] for node in sorted(core)},
        "nodes": len(graph),
        "seconds": round(time.monotonic() - started, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("viz/graph_data.json"))
    parser.add_argument("--output", type=Path, default=Path("viz/graph_data.json"))
    args = parser.parse_args()
    data = json.loads(args.input.read_text())
    layout = build_layout(data)
    data["layout"] = layout
    if args.output.exists():
        backup = Path(__file__).resolve().parents[1] / ".codex/refresh-2026-10-17/layout-originals"
        backup.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
        path = backup / (digest + ".json")
        if not path.exists():
            shutil.copy2(args.output, path)
    args.output.write_text(json.dumps(data, separators=(",", ":")) + "\n")
    print(
        json.dumps(
            {
                "nodes": layout["nodes"],
                "seconds": layout["seconds"],
                "output": str(args.output),
                "input_sha256": layout["input_sha256"],
            }
        )
    )


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget()
    main()
