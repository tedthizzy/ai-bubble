from __future__ import annotations

import csv
from pathlib import Path

from bubble.analysis.ownership_graph import (
    build_ownership_graph,
    load_ownership_rows,
    write_ownership_graph,
)


def test_ownership_graph_builds_source_backed_consolidation_edges(tmp_path: Path) -> None:
    rows = [
        {
            "Relationship_StartNode_NodeID": "CHILDLEI1234567890",
            "Relationship_StartNode_NodeIDType": "LEI",
            "Relationship_EndNode_NodeID": "PARENTLEI123456789",
            "Relationship_EndNode_NodeIDType": "LEI",
            "Relationship_RelationshipType": "IS_DIRECTLY_CONSOLIDATED_BY",
            "Relationship_RelationshipStatus": "ACTIVE",
            "Relationship_RelationshipQuantifiers_RelationshipQuantifier_QuantifierAmount": "99.9",
            "Relationship_RelationshipQuantifiers_RelationshipQuantifier_QuantifierUnits": "PERCENTAGE",
            "Registration_ValidationSources": "FULLY_CORROBORATED",
            "source_uri": "https://leidata.gleif.org/api/v1/concatenated-files/rr/get/1/zip",
            "retrieved_at": "2026-06-01T00:00:00+00:00",
            "content_hash": "hash-1",
            "local_path": "raw.zip",
            "record_index": "0",
            "document_id": "gleif_rr",
        },
        {
            "Relationship_StartNode_NodeID": "CHILDLEI1234567890",
            "Relationship_StartNode_NodeIDType": "LEI",
            "Relationship_EndNode_NodeID": "ULTIMATELEI12345",
            "Relationship_EndNode_NodeIDType": "LEI",
            "Relationship_RelationshipType": "IS_ULTIMATELY_CONSOLIDATED_BY",
            "Relationship_RelationshipStatus": "ACTIVE",
            "Registration_ValidationSources": "PARTIALLY_CORROBORATED",
            "source_uri": "https://leidata.gleif.org/api/v1/concatenated-files/rr/get/1/zip",
            "retrieved_at": "2026-06-01T00:00:00+00:00",
            "content_hash": "hash-1",
            "local_path": "raw.zip",
            "record_index": "1",
            "document_id": "gleif_rr",
        },
    ]

    lei_rows = [
        {
            "LEI": "CHILDLEI1234567890",
            "Entity_LegalName": "Child Compute LLC",
            "Entity_EntityStatus": "ACTIVE",
            "Registration_RegistrationStatus": "ISSUED",
            "Entity_LegalJurisdiction": "US-DE",
            "source_uri": "https://leidata.gleif.org/api/v1/concatenated-files/lei2/get/1/zip",
            "content_hash": "hash-lei",
        }
    ]

    graph = build_ownership_graph(rows, lei_rows=lei_rows)

    assert graph.summary.rows_scanned == 2
    assert graph.summary.relationships == 2
    assert graph.summary.source_backed_relationships == 2
    assert graph.summary.active_relationships == 2
    assert graph.summary.direct_consolidation_edges == 1
    assert graph.summary.ultimate_consolidation_edges == 1
    assert graph.summary.fully_corroborated_relationships == 1
    assert graph.summary.quantified_relationships == 1
    assert graph.summary.nodes == 3
    assert graph.summary.lei_nodes == 3
    assert graph.summary.named_nodes == 1
    assert graph.summary.active_legal_entity_nodes == 1
    assert graph.edges[0].child_id == "CHILDLEI1234567890"
    assert graph.edges[0].quantifier_amount == 99.9
    assert graph.nodes[0].node_id == "CHILDLEI1234567890"
    assert graph.nodes[0].legal_name == "Child Compute LLC"
    assert graph.nodes[0].entity_status == "ACTIVE"
    assert graph.nodes[0].child_edge_count == 2
    assert graph.nodes[0].source_uri_count == 2
    assert (
        graph.nodes[0].source_uris
        == "https://leidata.gleif.org/api/v1/concatenated-files/lei2/get/1/zip|"
        "https://leidata.gleif.org/api/v1/concatenated-files/rr/get/1/zip"
    )
    assert graph.nodes[0].content_hashes == "hash-1|hash-lei"

    outputs = write_ownership_graph(graph, tmp_path)
    assert Path(outputs["nodes_csv"]).exists()
    assert Path(outputs["edges_csv"]).exists()
    assert Path(outputs["summary_json"]).exists()


def test_load_ownership_rows_reads_known_source_acquisition_path(tmp_path: Path) -> None:
    rows_path = tmp_path / "source_acquisition" / "source_rows" / "ownership_records.csv"
    rows_path.parent.mkdir(parents=True)
    with rows_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "Relationship_StartNode_NodeID",
                "Relationship_EndNode_NodeID",
                "source_uri",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "Relationship_StartNode_NodeID": "child",
                "Relationship_EndNode_NodeID": "parent",
                "source_uri": "https://example.com/ownership.csv",
            }
        )

    rows = load_ownership_rows([tmp_path])

    assert len(rows) == 1
    assert rows[0]["Relationship_StartNode_NodeID"] == "child"
