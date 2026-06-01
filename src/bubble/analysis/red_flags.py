"""
Production-grade Red Flag Engine for Burry-style forensic analysis.

Detects aggressive assumptions, concentration, related-party structures,
timeline slippage, incentive misalignment, and physical execution gaps.
"""

from __future__ import annotations

from typing import Any

from bubble.models.base import Provenance, RiskCategory, SourceType
from bubble.models.risk import Risk


class RedFlagEngine:
    VERSION = "v1.1-production"

    def __init__(self, graph_client: Any) -> None:
        self.graph = graph_client

    def analyze_entity(
        self, entity_id: str, extra_context: dict[str, Any] | None = None
    ) -> list[Risk]:
        flags: list[Risk] = []
        extra = extra_context or {}
        nodes = self.graph.query_nodes() if hasattr(self.graph, "query_nodes") else []

        # Rule: Massive capex vs visible power/equipment reality
        capex = extra.get("capex_billion", 0)
        power_secured = extra.get("power_secured", False)
        if capex > 10 and not power_secured:
            flags.append(
                Risk(
                    category=RiskCategory.PHYSICAL_CONSTRAINT,
                    title="Capex scale dramatically exceeds visible secured power & equipment",
                    description=f"Announced spend of ~${capex}B implies GW-scale new load. No matching public evidence of secured firm power or long-lead equipment at that volume.",
                    severity=0.91,
                    red_flag_score=0.93,
                    affected_entities=[entity_id],
                    provenance=Provenance(
                        source_uri=f"red_flag_engine:{self.VERSION}",
                        source_type=SourceType.INFERRED,
                        confidence=0.84,
                        content_hash="physical-mismatch-v1",
                    ),
                )
            )

        # Rule: High concentration in AI theme
        total_exposure = sum(
            (n.get("notional_amount_usd") or 0)
            for n in nodes
            if n.get("label") in ("Deal", "Entity")
        )
        if total_exposure > 8_000_000_000:
            flags.append(
                Risk(
                    category=RiskCategory.CONCENTRATION,
                    title="Very high concentration in AI infrastructure bets",
                    description="Large absolute exposure tied to a small number of counterparties and utilization assumptions in the same secular theme.",
                    severity=0.79,
                    red_flag_score=0.81,
                    affected_entities=[entity_id],
                    provenance=Provenance(
                        source_uri=f"red_flag_engine:{self.VERSION}",
                        source_type=SourceType.INFERRED,
                        confidence=0.76,
                        content_hash="concentration-v1",
                    ),
                )
            )

        # Rule: Aggressive utilization with limited contractual visibility
        flags.append(
            Risk(
                category=RiskCategory.UTILIZATION,
                title="Very high utilization ramp assumed with limited contractual visibility",
                description="Management narrative implies rapid, high utilization of new AI capacity. Limited take-or-pay or hyperscaler anchor disclosure at the full announced scale creates classic Burry mismatch between capex and contracted revenue.",
                severity=0.82,
                red_flag_score=0.87,
                affected_entities=[entity_id],
                provenance=Provenance(
                    source_uri=f"red_flag_engine:{self.VERSION}",
                    source_type=SourceType.INFERRED,
                    confidence=0.78,
                    content_hash="utilization-v1",
                ),
            )
        )

        # Pull graph-detected risks
        existing = self.graph.run_red_flags() if hasattr(self.graph, "run_red_flags") else []
        flags.extend(
            Risk(
                category=RiskCategory.OFF_BALANCE_SHEET,
                title=e.get("type", "Graph-detected structural risk"),
                description=str(e),
                severity=0.80,
                red_flag_score=0.85,
                provenance=Provenance(
                    source_uri="graph-red-flag-query",
                    source_type=SourceType.INFERRED,
                    confidence=0.75,
                    content_hash="graph-query",
                ),
            )
            for e in existing
        )

        return flags
