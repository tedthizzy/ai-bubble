#!/usr/bin/env python3
"""Build the complete raw visualization field from an explicitly dated capital graph."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ALIASES = {
    "CoreWeave": ("coreweave",),
    "TeraWulf": ("terawulf",),
    "IREN": ("iren limited", "iren ltd"),
    "Applied Digital": ("applied digital",),
    "Hut 8": ("hut 8",),
    "MARA Holdings": ("mara holdings", "marathon digital"),
    "CleanSpark": ("cleanspark",),
    "Galaxy Digital": ("galaxy digital", "galaxy helios"),
    "Nebius": ("nebius",),
    "Core Scientific": ("core scientific",),
    "Cipher Mining": ("cipher mining", "cipher digital"),
    "Bit Digital": ("bit digital",),
    "Bitdeer": ("bitdeer",),
    "NVIDIA": ("nvidia",),
    "OpenAI": ("openai", "open ai"),
    "Microsoft": ("microsoft corp",),
    "Meta": ("meta platforms",),
    "Morgan Stanley": ("morgan stanley",),
    "Magnetar": ("magnetar",),
    "Blackstone": ("blackstone",),
    "Wilmington Trust": ("wilmington trust",),
    "Goldman Sachs": ("goldman sachs",),
    "Coatue": ("coatue",),
    "Apollo / Athene": (
        "apollo global",
        "athene",
    ),
    "Amazon Energy": ("amazon energy",),
    "Microsoft Energy": ("microsoft energy",),
    "Shell Energy": ("shell energy",),
    "SB Energy": ("sb energy",),
    "Deutsche Bank": ("deutsche bank",),
    "JPMorgan Chase": ("jpmorgan chase",),
    "Google": ("google llc", "google inc"),
    "Fluidstack": ("fluidstack",),
    "Anthropic": ("anthropic",),
    "AMD": ("advanced micro devices",),
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def position(identifier: str) -> list[float]:
    seed = hashlib.sha256(identifier.encode()).digest()
    values = [int.from_bytes(seed[i : i + 8]) / 2**64 for i in (0, 8, 16)]
    z = 2 * values[0] - 1
    angle = 2 * math.pi * values[1]
    radius = 200 + 350 * values[2] ** (1 / 3)
    radial = math.sqrt(1 - z * z)
    return [
        round(radius * radial * math.cos(angle), 4),
        round(radius * radial * math.sin(angle), 4),
        round(radius * z, 4),
    ]


def build_field(
    directory: Path, graph: dict[str, Any], as_of: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_path = directory / "input_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest["as_of"] != as_of or manifest["mode"] != "complete":
        raise ValueError("Expected the complete capital graph for this cutoff")
    inputs = {}
    for key in ("contract_nodes_csv", "contract_edges_csv"):
        record = manifest["outputs"][key]
        path = directory / Path(record["path"]).name
        if digest(path) != record["sha256"]:
            raise ValueError(f"Changed capital graph input: {path}")
        inputs[key] = path
    old_field = graph.get("field", {})
    old_positions = {
        row[0]: point
        for row, point in zip(
            old_field.get("nodes", []), graph.get("layout", {}).get("field", []), strict=False
        )
    }
    with sqlite3.connect("") as db:
        db.execute("PRAGMA cache_size=-4096")
        db.execute("PRAGMA temp_store=FILE")
        db.execute("CREATE TABLE entities(id TEXT PRIMARY KEY,name TEXT)")
        db.execute("CREATE TABLE deals(id TEXT PRIMARY KEY,usd REAL)")
        db.execute(
            "CREATE TABLE roles(deal TEXT,entity TEXT,side INTEGER,PRIMARY KEY(deal,entity,side))"
        )
        with inputs["contract_nodes_csv"].open(newline="") as stream:
            for row in csv.DictReader(stream):
                if row["node_type"] == "entity":
                    db.execute(
                        "INSERT OR IGNORE INTO entities VALUES (?,?)", (row["node_id"], row["name"])
                    )
                elif row["node_type"] == "deal":
                    db.execute(
                        "INSERT INTO deals VALUES (?,?) ON CONFLICT(id) DO UPDATE SET usd=MAX(usd,excluded.usd)",
                        (row["deal_id"], float(row["notional_usd"] or 0)),
                    )
        with inputs["contract_edges_csv"].open(newline="") as stream:
            for row in csv.DictReader(stream):
                relation = row["relationship_type"]
                if relation not in {"OBLIGATED_UNDER_DEAL", "DEAL_RISK_BEARER"}:
                    continue
                entity = (
                    row["source_id"] if relation == "OBLIGATED_UNDER_DEAL" else row["target_id"]
                )
                db.execute(
                    "INSERT OR IGNORE INTO roles VALUES (?,?,?)",
                    (row["deal_id"], entity, int(relation == "DEAL_RISK_BEARER")),
                )
        db.execute("CREATE INDEX roles_by_entity ON roles(entity,deal)")
        db.commit()
        rows = list(
            db.execute("""
            SELECT e.id,e.name,COALESCE(SUM(d.usd),0),COUNT(d.id) FROM entities e
            LEFT JOIN (SELECT DISTINCT deal,entity FROM roles) r ON r.entity=e.id
            LEFT JOIN deals d ON d.id=r.deal GROUP BY e.id ORDER BY e.id
        """)
        )
        ids = {row[0]: i for i, row in enumerate(rows)}
        core = {row["id"] for row in graph["nodes"]}
        matches = {}
        for name, aliases in ALIASES.items():
            hits = [
                row
                for row in rows
                if name in core and any(alias in row[1].casefold() for alias in aliases)
            ]
            if hits:
                matches[max(hits, key=lambda row: row[2])[0]] = name
        nodes = [
            [name, round(usd), count, matches.get(identifier, 0)]
            for identifier, name, usd, count in rows
        ]
        links = []
        for a, b, usd, count in db.execute("""
            SELECT a,b,SUM(usd),COUNT(*) FROM (
              SELECT CASE WHEN o.entity<r.entity THEN o.entity ELSE r.entity END a,
                     CASE WHEN o.entity<r.entity THEN r.entity ELSE o.entity END b,
                     d.id,MAX(d.usd) usd
              FROM roles o JOIN roles r ON r.deal=o.deal AND r.side=1
              JOIN deals d ON d.id=o.deal
              WHERE o.side=0 AND o.entity!=r.entity GROUP BY a,b,d.id
            ) GROUP BY a,b ORDER BY a,b
        """):
            if a not in ids or b not in ids:
                raise ValueError("Raw field connection references a missing entity")
            links.append([ids[a], ids[b], round(usd), count])
        field = {
            "entities": len(nodes),
            "deals": db.execute("SELECT COUNT(*) FROM deals").fetchone()[0],
            "matched_core": len(matches),
            "nodes": nodes,
            "links": links,
            "evidence_date": as_of,
            "input_manifest_sha256": digest(manifest_path),
            "note": "All named entities and all obligor-to-risk-bearer pairs from the dated extracted contract graph. No per-side party cap. A pair counts each extracted deal once. Raw amounts can repeat across filings and are unadjudicated; they are separate from reported issuer debt.",
        }
        layout = {
            **graph.get("layout", {}),
            "algorithm": "retained-positions-and-deterministic-entity-id-sphere-v1",
            "field": [
                old_positions.get(name) or position(identifier) for identifier, name, _, _ in rows
            ],
            "nodes": len(nodes),
            "input_sha256": digest(manifest_path),
        }
    return field, layout


def update(directory: Path, target: Path, as_of: str) -> dict[str, Any]:
    graph = json.loads(target.read_text())
    if graph["meta"].get("as_of") != as_of or not graph["meta"].get("current_review"):
        raise ValueError("The current financial review must be applied first")
    graph["field"], graph["layout"] = build_field(directory, graph, as_of)
    snapshot = ROOT / ".codex/refresh-2026-10-17" / f"before-field-update-{time.time_ns()}"
    snapshot.mkdir(parents=True)
    shutil.copy2(target, snapshot / target.name)
    target.write_text(json.dumps(graph, sort_keys=True, separators=(",", ":")) + "\n")
    result = {
        key: graph["field"][key] for key in ("entities", "deals", "matched_core", "evidence_date")
    }
    result.update(links=len(graph["field"]["links"]), output_sha256=digest(target))
    return result


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget(512)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capital-dir", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "viz/graph_data.json")
    args = parser.parse_args()
    print(json.dumps(update(args.capital_dir, args.output, args.as_of)))
