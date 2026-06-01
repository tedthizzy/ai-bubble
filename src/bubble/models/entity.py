"""
Entity model — companies, SPVs, projects, assets, etc.

This is the primary node type in the bubble graph.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import BubbleBaseModel, EntityRef, EntityType


class Entity(BubbleBaseModel):
    """
    A legal or economic actor in the ecosystem.

    Examples:
    - Microsoft Corporation (CIK 0000789019)
    - CoreWeave SPV-2027-17 (inferred or from exhibits)
    - Apollo/Athene co-investment vehicle for data center debt
    - A specific 150MW gas turbine array in Abilene, TX
    """

    name: str
    aliases: list[str] = Field(default_factory=list)
    entity_type: EntityType = EntityType.UNKNOWN

    # Public identifiers (where applicable)
    cik: str | None = None  # SEC Central Index Key
    lei: str | None = None  # Legal Entity Identifier
    ticker: str | None = None
    website: str | None = None
    jurisdiction: str | None = None  # Delaware, Texas, Ireland, etc.

    # Graph-friendly attributes
    parent_id: EntityRef | None = None
    subsidiaries: list[EntityRef] = Field(default_factory=list)
    related_entities: list[EntityRef] = Field(default_factory=list)  # non-ownership relationships

    # Key metrics extracted / inferred (always with provenance on the Entity itself + separate CashFlow/Risk nodes)
    market_cap_usd: float | None = None
    total_assets_usd: float | None = None
    data_center_capex_guidance_usd: float | None = None  # from latest 10-K/earnings

    # Free-form but structured attributes (e.g. "primary_power_source": "gas + nuclear PPA")
    attributes: dict[str, Any] = Field(default_factory=dict)

    def display_name(self) -> str:
        if self.ticker:
            return f"{self.name} ({self.ticker})"
        return self.name

    def __str__(self) -> str:
        return f"Entity({self.display_name()}, type={self.entity_type}, cik={self.cik})"
