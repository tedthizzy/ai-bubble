"""
Risk and Assumption models — where the Burry skepticism lives.

These capture the critical variables that, if wrong, blow up the economics.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import BubbleBaseModel, NodeRef, RiskCategory


class Assumption(BubbleBaseModel):
    """
    A single numeric or qualitative assumption that drives a model.

    Examples:
    - "Utilization in year 3 = 78%"
    - "GPU economic life = 5 years (straight-line)"
    - "Power cost escalator = 2.5% / yr"
    - "Refinancing at 6.25% in 2028"
    """

    category: RiskCategory
    name: str
    value: Any
    unit: str | None = None
    source_quote: str | None = None  # direct quote from 10-K or transcript
    linked_nodes: list[NodeRef] = Field(default_factory=list)

    # Scenario values (the heart of stress testing)
    base_case: Any | None = None
    adverse: Any | None = None
    severe: Any | None = None
    tail: Any | None = None


class Risk(BubbleBaseModel):
    """
    A materialized risk or red flag.

    The system tries to auto-generate these from filings + cross-checks.
    Human analysts add the ones the models miss.
    """

    category: RiskCategory
    title: str
    description: str
    severity: float = Field(default=0.5, ge=0.0, le=1.0)  # 0.9+ = material to thesis
    red_flag_score: float = Field(default=0.6, ge=0.0, le=1.0)

    affected_entities: list[NodeRef] = Field(default_factory=list)
    affected_deals: list[NodeRef] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)

    # Evidence
    evidence_quotes: list[str] = Field(default_factory=list)
    counter_evidence: list[str] = Field(default_factory=list)

    # What would have to be true for this risk to be benign?
    benign_conditions: list[str] = Field(default_factory=list)

    is_material_to_thesis: bool = False
    requires_human_review: bool = True

    def is_high_severity(self) -> bool:
        return self.severity >= 0.7 or self.red_flag_score >= 0.8
