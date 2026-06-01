import pytest

from bubble.graph.client import BubbleGraphClient, InMemoryStore
from bubble.models.base import Provenance, SourceType
from bubble.models.entity import Entity, EntityType
from bubble.quality.source_invariants import SourceDataInvariantError


def test_in_memory_contagion_paths_use_named_edge_keys():
    store = InMemoryStore()
    store.add_node("Entity", "project-a", {"name": "Project A"})
    store.add_node("Entity", "lender-b", {"name": "Lender B"})
    store.add_relationship(
        "project-a",
        "lender-b",
        "DEBT_FACILITY",
        {"notional_amount_usd": 750_000_000, "type": "private credit facility"},
    )

    paths = store.contagion_paths("project-a", max_depth=2)

    assert paths[0]["estimated_exposure_usd"] == 750_000_000
    assert paths[0]["rel_types"] == ["DEBT_FACILITY"]


def test_in_memory_contagion_paths_do_not_invent_missing_exposure():
    store = InMemoryStore()
    store.add_node("Entity", "project-a", {"name": "Project A"})
    store.add_node("Entity", "lender-b", {"name": "Lender B"})
    store.add_relationship("project-a", "lender-b", "RELATED_TO", {})

    paths = store.contagion_paths("project-a", max_depth=2)

    assert paths[0]["estimated_exposure_usd"] == 0


def test_graph_client_exposes_query_nodes_in_memory_mode():
    client = BubbleGraphClient.__new__(BubbleGraphClient)
    client._mode = "memory"
    client._neo_driver = None
    client._memory = InMemoryStore()
    client._memory.add_node("Entity", "entity-1", {"name": "Entity 1"})
    client._memory.add_node("Deal", "deal-1", {"notional_amount_usd": 100})

    assert len(client.query_nodes()) == 2
    assert client.query_nodes("Entity") == [{"label": "Entity", "name": "Entity 1"}]


def test_graph_client_rejects_seed_entity_provenance_in_production_path():
    client = BubbleGraphClient.__new__(BubbleGraphClient)
    client._mode = "memory"
    client._neo_driver = None
    client._memory = InMemoryStore()
    entity = Entity(
        name="Manual Entity",
        entity_type=EntityType.HYPERSCALER,
        provenance=Provenance(
            source_uri="seed:manual",
            source_type=SourceType.MANUAL_CURATED,
            content_hash="a" * 64,
        ),
    )

    with pytest.raises(SourceDataInvariantError):
        client.merge_entity(entity)


def test_bootstrap_schema_does_not_insert_manual_entities_in_memory_mode():
    client = BubbleGraphClient.__new__(BubbleGraphClient)
    client._mode = "memory"
    client._neo_driver = None
    client._memory = InMemoryStore()

    client.bootstrap_schema()

    assert client.query_nodes("Entity") == []


def test_review_queue_returns_dict_rows_and_resolves_items():
    client = BubbleGraphClient.__new__(BubbleGraphClient)
    client._mode = "memory"
    client._neo_driver = None
    client._memory = InMemoryStore()

    client.add_to_review_queue("Risk", "risk-1", "needs review", 0.4, priority=10)
    pending = client.get_review_queue()

    assert pending
    assert pending[0]["node_id"] == "risk-1"

    client.resolve_review_item(str(pending[0]["id"]), "approved", "checked")

    assert client.get_review_queue() == []
    approved = client.get_review_queue("approved")
    assert approved[0]["notes"] == "checked"
