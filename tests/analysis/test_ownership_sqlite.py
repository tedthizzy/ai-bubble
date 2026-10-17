from pathlib import Path

from bubble.analysis.ownership_graph import build_ownership_graph, write_ownership_graph
from bubble.analysis.ownership_sqlite import write_ownership_graph_from_rows


def test_disk_graph_matches_all_legacy_fields_counts_order_and_last_reference(tmp_path: Path):
    rows = [
        {"child_entity": "child-a", "parent_entity": "parent-a", "start_node_id_type": "LEI", "end_node_id_type": "LEI",
         "relationship_type": "IS_DIRECTLY_CONSOLIDATED_BY", "relationship_status": "ACTIVE", "source_uri": "https://one.test", "content_hash": "one",
         "validation_sources": "FULLY_CORROBORATED"},
        {"child_entity": "child-b", "parent_entity": "parent-b", "source_uri": "https://two.test", "content_hash": "two"},
        {"child_entity": "child-a", "parent_entity": "parent-b", "relationship_type": "IS_ULTIMATELY_CONSOLIDATED_BY", "relationship_status": "INACTIVE"},
        {"child_entity": "child-b", "parent_entity": "parent-a", "relationship_type": "OTHER", "relationship_status": "ACTIVE",
         "Relationship_RelationshipQuantifiers_RelationshipQuantifier_QuantifierAmount": "0.5"},
        {"child_entity": "self", "parent_entity": "self"}, {},
    ]
    references = [
        {"LEI": "parent-a", "legal_name": "Superseded name", "source_uri": "https://superseded.test", "content_hash": "old"},
        {"LEI": "parent-a", "legal_name": "Current 漢字", "entity_status": "ACTIVE", "source_uri": "https://lei.test", "content_hash": "lei"},
        {"LEI": "unconnected", "legal_name": "Outside graph", "source_uri": "https://excluded.test"},
        {"LEI": "child-b", "legal_name": "Name B", "entity_status": "INACTIVE"},
    ]
    legacy = build_ownership_graph(iter(rows), lei_rows=iter(references))
    expected = write_ownership_graph(legacy, tmp_path / "legacy")
    summary, actual = write_ownership_graph_from_rows(iter(rows), lei_rows=iter(references), output_dir=tmp_path / "sqlite")
    assert summary.to_dict() == legacy.summary.to_dict()
    for name in ("nodes_csv", "edges_csv"):
        assert Path(actual[name]).read_bytes() == Path(expected[name]).read_bytes()


def test_disk_graph_keeps_empty_output_semantics(tmp_path: Path):
    legacy = build_ownership_graph([], lei_rows=[])
    expected = write_ownership_graph(legacy, tmp_path / "legacy")
    summary, actual = write_ownership_graph_from_rows([], lei_rows=[], output_dir=tmp_path / "sqlite")
    assert summary.to_dict() == legacy.summary.to_dict()
    assert Path(actual["nodes_csv"]).read_bytes() == Path(expected["nodes_csv"]).read_bytes() == b""
    assert Path(actual["edges_csv"]).read_bytes() == Path(expected["edges_csv"]).read_bytes() == b""
