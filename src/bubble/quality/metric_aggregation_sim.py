"""Read-only metric-aggregation simulator (branch-local, proposed for Codex review).

Compares how the final approved-metric total changes under different grouping
keys (metric_group_id, content_hash+amount, source_uri+amount, accession+amount,
instrument-key). Each group contributes ``max(supported_amount)`` —
matching the report's ``max_amount_per_source_instrument`` policy. Reads only.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class AggregationResult:
    strategy: str
    total_usd: float
    group_count: int
    delta_vs_baseline_usd: float = 0.0


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def aggregate_by(
    rows: Iterable[Mapping[str, Any]],
    key_fields: Sequence[str],
    *,
    amount_field: str = "supported_amount_usd",
    strategy: str | None = None,
) -> AggregationResult:
    """Group rows by ``key_fields`` and total ``max(amount)`` per group."""

    groups: dict[tuple[str, ...], float] = defaultdict(float)
    for row in rows:
        key = tuple(str(row.get(field, "")) for field in key_fields)
        groups[key] = max(groups[key], _to_float(row.get(amount_field)))
    return AggregationResult(
        strategy=strategy or "+".join(key_fields),
        total_usd=round(sum(groups.values()), 2),
        group_count=len(groups),
    )


def simulate(
    rows: Iterable[Mapping[str, Any]],
    strategies: Sequence[tuple[str, Sequence[str]]],
    *,
    amount_field: str = "supported_amount_usd",
) -> list[AggregationResult]:
    """Run several grouping strategies; the first is the baseline for deltas."""

    materialized = list(rows)
    results: list[AggregationResult] = []
    baseline: float | None = None
    for name, key_fields in strategies:
        result = aggregate_by(materialized, key_fields, amount_field=amount_field, strategy=name)
        if baseline is None:
            baseline = result.total_usd
        results.append(
            AggregationResult(
                strategy=result.strategy,
                total_usd=result.total_usd,
                group_count=result.group_count,
                delta_vs_baseline_usd=round(result.total_usd - baseline, 2),
            )
        )
    return results
