"""
Seed the graph with high-priority entities from the approved plan.

Run via: `just seed` or `uv run python scripts/seed_graph.py`
"""

from __future__ import annotations

from bubble.graph.client import BubbleGraphClient
from bubble.ingestion.edgar.seeds import PRIVATE_SEEDS, PUBLIC_SEEDS
from bubble.models.base import EntityType, Provenance, SourceType
from bubble.models.entity import Entity


def main() -> None:
    client = BubbleGraphClient()

    print("Seeding high-priority entities...")

    for cik, meta in PUBLIC_SEEDS.items():
        prov = Provenance(
            source_uri=f"https://sec.gov/cgi-bin/browse-edgar?CIK={cik}",
            source_type=SourceType.SEC_EDGAR,
            confidence=0.99,
            content_hash=Provenance.compute_content_hash(f"SEED:{cik}"),
        )
        ent = Entity(
            name=meta["name"],
            cik=cik,
            entity_type=EntityType(meta.get("type", "hyperscaler")),
            ticker=meta.get("ticker"),
            provenance=prov,
            confidence=0.99,
        )
        client.merge_entity(ent)
        print(f"  ✓ {ent.name} (CIK {cik})")

    for meta in PRIVATE_SEEDS:
        prov = Provenance(
            source_uri="seed:private-priority-list",
            source_type=SourceType.MANUAL_CURATED,
            confidence=0.75,
            content_hash=Provenance.compute_content_hash(meta["name"]),
        )
        ent = Entity(
            name=meta["name"],
            entity_type=EntityType(meta.get("type", "ai_infra_pureplay")),
            provenance=prov,
            confidence=0.75,
        )
        client.merge_entity(ent)
        print(f"  ✓ {ent.name} (private seed)")

    print(
        "\nSeed complete. Run `just bootstrap-neo4j` if you haven't already, then start ingesting real filings."
    )


if __name__ == "__main__":
    main()
