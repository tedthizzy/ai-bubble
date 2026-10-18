"""Build the complete ownership graph with file-backed aggregation."""

from __future__ import annotations

import csv
import json
import sqlite3
from collections import Counter
from dataclasses import asdict, fields
from pathlib import Path
from typing import TYPE_CHECKING

from bubble.analysis.ownership_graph import (
    OwnershipEdge,
    OwnershipGraphSummary,
    OwnershipNode,
    _edge_from_row,
    _first,
    _lei_reference,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


def write_ownership_graph_from_rows(
    rows: Iterable[Mapping[str, str]],
    *,
    lei_rows: Iterable[Mapping[str, str]],
    output_dir: str | Path,
) -> tuple[OwnershipGraphSummary, dict[str, str]]:
    """Preserve the production graph's fields, ordering, and summary semantics."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=False)
    database = _database(out / "aggregation.sqlite3")
    totals: Counter[str] = Counter()
    edges_path = out / "ownership_edges.csv"
    try:
        with edges_path.open("x", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=[f.name for f in fields(OwnershipEdge)])
            for row in rows:
                totals["rows_scanned"] += 1
                edge = _edge_from_row(row)
                if edge is None:
                    continue
                number = totals["relationships"]
                if number == 0:
                    writer.writeheader()
                writer.writerow(asdict(edge))
                totals["relationships"] += 1
                totals["source_backed_relationships"] += bool(edge.source_uri)
                totals["active_relationships"] += edge.relationship_status == "ACTIVE"
                totals["inactive_relationships"] += edge.relationship_status != "ACTIVE"
                direct = edge.relationship_type == "IS_DIRECTLY_CONSOLIDATED_BY"
                ultimate = edge.relationship_type == "IS_ULTIMATELY_CONSOLIDATED_BY"
                totals["direct_consolidation_edges"] += direct
                totals["ultimate_consolidation_edges"] += ultimate
                totals["other_relationship_edges"] += not (direct or ultimate)
                totals["fully_corroborated_relationships"] += (
                    edge.validation_sources == "FULLY_CORROBORATED"
                )
                totals["quantified_relationships"] += edge.quantifier_amount is not None
                # Insert child first, matching the original first-observed node type.
                database.executemany(
                    """
                    INSERT INTO nodes VALUES (?,?,?,?,?,?)
                    ON CONFLICT(node_id) DO UPDATE SET
                      parent_count=parent_count+excluded.parent_count,
                      child_count=child_count+excluded.child_count,
                      first_parent=COALESCE(first_parent,excluded.first_parent),
                      first_child=COALESCE(first_child,excluded.first_child)
                """,
                    [
                        (edge.child_id, edge.child_id_type, 0, 1, None, number),
                        (edge.parent_id, edge.parent_id_type, 1, 0, number, None),
                    ],
                )
                database.executemany(
                    "INSERT OR IGNORE INTO provenance VALUES (?,?,?)",
                    [
                        (node, edge.source_uri, edge.content_hash)
                        for node in (edge.child_id, edge.parent_id)
                    ],
                )
                if number % 1000 == 0:
                    database.commit()
        database.commit()
        _add_references(database, lei_rows)
        nodes_path = out / "ownership_nodes.csv"
        query = """
            SELECT n.node_id,n.node_id_type,
              COALESCE(r.legal_name,'') legal_name,
              COALESCE(r.entity_status,'') entity_status,
              COALESCE(r.registration_status,'') registration_status,
              COALESCE(r.legal_jurisdiction,'') legal_jurisdiction,
              n.parent_count+n.child_count relationship_count,
              n.parent_count parent_edge_count,n.child_count child_edge_count,
              (SELECT COUNT(DISTINCT source_uri) FROM provenance p
                WHERE p.node_id=n.node_id AND source_uri!='') source_uri_count,
              COALESCE((SELECT group_concat(source_uri,'|') FROM
                (SELECT DISTINCT source_uri FROM provenance p
                 WHERE p.node_id=n.node_id AND source_uri!='' ORDER BY source_uri)), '') source_uris,
              COALESCE((SELECT group_concat(content_hash,'|') FROM
                (SELECT DISTINCT content_hash FROM provenance p
                 WHERE p.node_id=n.node_id AND content_hash!='' ORDER BY content_hash)), '') content_hashes
            FROM nodes n LEFT JOIN reference r USING(node_id)
            ORDER BY relationship_count DESC,parent_edge_count DESC,child_edge_count DESC,n.node_id DESC
        """
        with nodes_path.open("x", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=[f.name for f in fields(OwnershipNode)])
            for number, row in enumerate(database.execute(query)):
                if number == 0:
                    writer.writeheader()
                writer.writerow(dict(row))

        def scalar(query: str) -> int:
            return int(database.execute(query).fetchone()[0])

        def top(role: str) -> list[dict[str, str | int]]:
            return [
                {"node_id": row[0], "relationship_count": row[1]}
                for row in database.execute(
                    f"SELECT node_id,{role}_count FROM nodes WHERE {role}_count>0 "
                    f"ORDER BY {role}_count DESC,first_{role} ASC LIMIT 25"
                )
            ]

        summary = OwnershipGraphSummary(
            rows_scanned=totals["rows_scanned"],
            relationships=totals["relationships"],
            source_backed_relationships=totals["source_backed_relationships"],
            active_relationships=totals["active_relationships"],
            inactive_relationships=totals["inactive_relationships"],
            direct_consolidation_edges=totals["direct_consolidation_edges"],
            ultimate_consolidation_edges=totals["ultimate_consolidation_edges"],
            other_relationship_edges=totals["other_relationship_edges"],
            fully_corroborated_relationships=totals["fully_corroborated_relationships"],
            quantified_relationships=totals["quantified_relationships"],
            nodes=scalar("SELECT COUNT(*) FROM nodes"),
            lei_nodes=scalar("SELECT COUNT(*) FROM nodes WHERE node_id_type='LEI'"),
            named_nodes=scalar("SELECT COUNT(*) FROM reference WHERE legal_name!=''"),
            active_legal_entity_nodes=scalar(
                "SELECT COUNT(*) FROM reference WHERE entity_status='ACTIVE'"
            ),
            source_uri_count=scalar(
                "SELECT COUNT(DISTINCT source_uri) FROM provenance WHERE source_uri!=''"
            ),
            content_hash_count=scalar(
                "SELECT COUNT(DISTINCT content_hash) FROM provenance WHERE content_hash!=''"
            ),
            top_parents_by_child_count=top("parent"),
            top_children_by_parent_count=top("child"),
        )
        summary_path = out / "ownership_graph_summary.json"
        with summary_path.open("x") as stream:
            json.dump(summary.to_dict(), stream, indent=2, sort_keys=True)
        return summary, {
            "nodes_csv": str(nodes_path),
            "edges_csv": str(edges_path),
            "summary_json": str(summary_path),
        }
    finally:
        database.close()


def _add_references(database: sqlite3.Connection, lei_rows: Iterable[Mapping[str, str]]) -> None:
    allowed = {row[0] for row in database.execute("SELECT node_id FROM nodes")}
    for number, row in enumerate(lei_rows):
        lei = _first(row, "LEI", "lei")
        if lei not in allowed:
            continue
        record = _lei_reference([row])[lei]
        database.execute(
            """
            INSERT OR REPLACE INTO reference VALUES (?,?,?,?,?,?,?)
        """,
            (
                lei,
                record["legal_name"],
                record["entity_status"],
                record["registration_status"],
                record["legal_jurisdiction"],
                record["source_uri"],
                record["content_hash"],
            ),
        )
        if number % 1000 == 0:
            database.commit()
    del allowed
    database.execute("""
        INSERT OR IGNORE INTO provenance
        SELECT node_id,source_uri,content_hash FROM reference
    """)
    database.commit()


def _database(path: Path) -> sqlite3.Connection:
    database = sqlite3.connect(path)
    database.row_factory = sqlite3.Row
    database.executescript("""
        PRAGMA cache_size=-8192;
        PRAGMA temp_store=FILE;
        PRAGMA mmap_size=0;
        CREATE TABLE nodes (
            node_id TEXT PRIMARY KEY, node_id_type TEXT,
            parent_count INTEGER, child_count INTEGER,
            first_parent INTEGER, first_child INTEGER);
        CREATE TABLE provenance (
            node_id TEXT, source_uri TEXT, content_hash TEXT,
            PRIMARY KEY(node_id,source_uri,content_hash)) WITHOUT ROWID;
        CREATE TABLE reference (
            node_id TEXT PRIMARY KEY, legal_name TEXT, entity_status TEXT,
            registration_status TEXT, legal_jurisdiction TEXT,
            source_uri TEXT, content_hash TEXT) WITHOUT ROWID;
    """)
    return database
