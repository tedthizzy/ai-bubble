"""Source-backed timing signals for crack-window analysis.

This module builds a quarter-by-quarter stress calendar from already acquired
filings, project evidence, queue records, and compute-economics rows. It is a
timing triage layer, not a final market-call engine.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
from datetime import date
from pathlib import Path
from typing import Any

from bubble.analysis.capital_exposure_graph import (
    DIRECT_AI_INFRA_PATTERNS,
    WATCHLIST_ENTITY_PATTERNS,
)

DEBT_LIKE_DEAL_TYPES = {
    "debt_facility",
    "bond",
    "lease",
    "preferred_equity",
    "guarantee",
}
MEGA_TIMING_OBLIGATION_REVIEW_THRESHOLD_USD = 50_000_000_000

START_YEAR = 2024
END_YEAR = 2030
FORWARD_REFINANCING_AS_OF_QUARTER = "2026-Q2"
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "watch": 3}
SEVERITY_WEIGHT = {"critical": 4.0, "high": 3.0, "medium": 2.0, "watch": 1.0}


@dataclass(frozen=True)
class TimingSignal:
    """One source-backed timing signal anchored to a calendar quarter."""

    signal_id: str
    quarter: str
    signal_date: str
    category: str
    signal_type: str
    severity: str
    ecosystem_relevance: str
    relevance_tags: tuple[str, ...]
    entity: str
    counterparty: str
    project_id: str
    project_name: str
    deal_id: str
    amount_usd: float
    capacity_mw: float
    risk_score: float
    description: str
    source_uri: str
    source_uris: tuple[str, ...]
    content_hash: str
    content_hashes: tuple[str, ...]
    page_or_section: str
    evidence_tier: str
    human_review_status: str
    source_confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TimingQuarter:
    """Aggregated stress metrics for one quarter."""

    quarter: str
    stress_score: float
    signal_count: int
    critical_or_high_signal_count: int
    ai_infra_relevant_signal_count: int
    capital_refinancing_usd: float
    ai_infra_capital_refinancing_usd: float
    physical_capacity_mw: float
    compute_amount_usd: float
    chip_supply_capacity_mw: float
    top_drivers: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TimingSignalSummary:
    """Serializable rollup for timing-signal artifacts."""

    signals: int
    source_backed_signals: int
    critical_or_high_signals: int
    ai_infra_relevant_signals: int
    categories: dict[str, int]
    signal_types: dict[str, int]
    ecosystem_relevance: dict[str, int]
    quarters: int
    peak_stress_quarter: str | None
    candidate_stress_window_start: str | None
    candidate_stress_window_end: str | None
    capital_refinancing_usd_2024_2030: float
    ai_infra_capital_refinancing_usd_2024_2030: float
    capital_refinancing_historical_to_as_of_usd: float
    ai_infra_capital_refinancing_historical_to_as_of_usd: float
    capital_refinancing_forward_from_as_of_usd: float
    ai_infra_capital_refinancing_forward_from_as_of_usd: float
    forward_refinancing_as_of_quarter: str
    forward_peak_refinancing_quarter: str | None
    forward_peak_ai_infra_refinancing_quarter: str | None
    forward_peak_refinancing_usd: float
    forward_peak_ai_infra_refinancing_usd: float
    physical_capacity_mw_2024_2030: float
    compute_amount_usd_2024_2030: float
    chip_supply_capacity_mw_2024_2030: float
    top_quarters: list[dict[str, Any]]
    top_signals: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TimingSignalBatch:
    """Built timing signal artifacts."""

    signals: list[TimingSignal]
    quarters: list[TimingQuarter]
    summary: TimingSignalSummary


def build_timing_signal_batch(data_dirs: list[str | Path] | None = None) -> TimingSignalBatch:
    """Build timing signals from source-backed production artifacts."""

    roots = [Path(root) for root in (data_dirs or ["data"])]
    signals: list[TimingSignal] = []
    signals.extend(_capital_refinancing_signals(roots))
    signals.extend(_physical_cod_signals(roots))
    signals.extend(_compute_timing_signals(roots))

    deduped = _dedupe_timing_economic_obligations(_dedupe_signals(signals))
    deduped.sort(key=_signal_sort_key)
    quarters = _quarter_rollups(deduped)
    summary = _summary(deduped, quarters)
    return TimingSignalBatch(signals=deduped, quarters=quarters, summary=summary)


def write_timing_signal_batch(
    batch: TimingSignalBatch,
    output_dir: str | Path,
) -> dict[str, str]:
    """Write timing signals, quarter rollups, and summary to disk."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    signals_path = out / "timing_signals.csv"
    quarters_path = out / "timing_signal_quarters.csv"
    summary_path = out / "timing_signal_summary.json"
    _write_csv(signals_path, [signal.to_dict() for signal in batch.signals])
    _write_csv(quarters_path, [quarter.to_dict() for quarter in batch.quarters])
    summary_path.write_text(json.dumps(batch.summary.to_dict(), indent=2))
    return {
        "signals_csv": str(signals_path),
        "quarters_csv": str(quarters_path),
        "summary_json": str(summary_path),
    }


def _capital_refinancing_signals(roots: list[Path]) -> list[TimingSignal]:
    signals: list[TimingSignal] = []
    seen_deals: set[str] = set()
    tranches_by_deal = _tranche_rows_by_deal(
        _read_rows(
            roots,
            [Path("edgar_acquisition") / "tranches.csv", Path("capital") / "tranches.csv"],
        )
    )
    rows = _read_rows(
        roots,
        [Path("edgar_acquisition") / "deals.csv", Path("capital") / "deals.csv"],
    )
    for row in rows:
        deal_id = _field(row, "deal_id")
        if deal_id and deal_id in seen_deals:
            continue
        if deal_id:
            seen_deals.add(deal_id)
        deal_type = _field(row, "deal_type")
        if deal_type not in DEBT_LIKE_DEAL_TYPES:
            continue
        tranche_rows = tranches_by_deal.get(deal_id, [])
        tranche_signals = [
            signal
            for tranche in tranche_rows
            if (
                signal := _capital_refinancing_signal(
                    row,
                    tranche,
                    use_tranche=True,
                )
            )
            is not None
        ]
        if tranche_signals:
            signals.extend(tranche_signals)
            continue

        if _float(row.get("notional_amount_usd")) <= 0:
            continue
        signal = _capital_refinancing_signal(row, row, use_tranche=False)
        if signal:
            signals.append(signal)
    return signals


def _capital_refinancing_signal(
    deal_row: dict[str, str],
    source_row: dict[str, str],
    *,
    use_tranche: bool,
) -> TimingSignal | None:
    deal_id = _field(deal_row, "deal_id")
    deal_type = _field(deal_row, "deal_type")
    notional = _float(
        source_row.get("notional_usd") if use_tranche else source_row.get("notional_amount_usd")
    )
    if notional <= 0:
        return None
    maturity = _parse_date(_field(source_row, "maturity" if use_tranche else "maturity_date"))
    if maturity is None or not _in_horizon(maturity):
        return None
    key_terms = _json_dict(deal_row.get("key_terms"))
    relevance_tags = _relevance_tags(
        " ".join(
            [
                _field(deal_row, "primary_party"),
                _counterparty_from_row(deal_row),
                _field(deal_row, "title"),
                _field(deal_row, "page_or_section"),
                deal_row.get("key_terms") or "",
                _field(source_row, "name"),
                _field(source_row, "collateral_description"),
                _field(source_row, "guarantors"),
            ]
        )
    )
    ecosystem_relevance = _ecosystem_relevance(relevance_tags)
    source_uri = _field(source_row, "source_uri") or _field(deal_row, "source_uri")
    content_hash = _field(source_row, "content_hash") or _field(deal_row, "content_hash")
    if not _has_source_provenance(source_uri, content_hash):
        return None
    context_kind = str(key_terms.get("notional_context_kind") or "").strip()
    if _looks_like_timing_asset_or_capacity_not_debt(deal_row, source_row):
        return None
    if _requires_mega_timing_obligation_confirmation(deal_row, source_row, notional):
        return None
    tranche_name = _field(source_row, "name") if use_tranche else ""
    description_parts = [
        f"{deal_type} {'tranche ' if use_tranche else ''}maturity",
        f"tranche {tranche_name}" if tranche_name else "",
        f"notional ${notional:,.0f}",
        f"context {context_kind}" if context_kind else "",
    ]
    return TimingSignal(
        signal_id=_signal_id(
            "capital_tranche" if use_tranche else "capital",
            deal_id,
            _field(source_row, "tranche_id") if use_tranche else "",
            source_uri,
            content_hash,
            maturity,
        ),
        quarter=_quarter(maturity),
        signal_date=maturity.isoformat(),
        category="capital",
        signal_type="refinancing_maturity",
        severity=_capital_severity(notional, ecosystem_relevance),
        ecosystem_relevance=ecosystem_relevance,
        relevance_tags=relevance_tags,
        entity=_field(deal_row, "primary_party"),
        counterparty=_counterparty_from_row(deal_row),
        project_id="",
        project_name="",
        deal_id=deal_id,
        amount_usd=round(notional, 2),
        capacity_mw=0.0,
        risk_score=0.0,
        description=_reason(description_parts),
        source_uri=source_uri,
        source_uris=(source_uri,) if source_uri else (),
        content_hash=content_hash,
        content_hashes=(content_hash,) if content_hash else (),
        page_or_section=_field(source_row, "page_or_section")
        or _field(deal_row, "page_or_section"),
        evidence_tier="source_backed_pending_review"
        if (_field(source_row, "human_review_status") or _field(deal_row, "human_review_status"))
        == "pending"
        else "source_backed_reviewed",
        human_review_status=(
            _field(source_row, "human_review_status")
            or _field(deal_row, "human_review_status")
            or "pending"
        ),
        source_confidence=_float(
            source_row.get("source_confidence")
            or deal_row.get("source_confidence")
            or source_row.get("confidence")
            or deal_row.get("confidence")
        ),
    )


def _tranche_rows_by_deal(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    by_deal: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        deal_id = _field(row, "deal_id")
        if deal_id:
            by_deal[deal_id].append(row)
    return by_deal


def _looks_like_timing_asset_or_capacity_not_debt(
    deal_row: dict[str, str],
    source_row: dict[str, str],
) -> bool:
    text = _capital_source_text(deal_row, source_row)
    return _contains_any(
        text,
        [
            "servicing portfolio upb",
            "total upb",
            "by upb",
            "unpaid principal balance",
            "mortgage servicing rights",
            "mortgage servicing assets",
            "msr fair value",
            "msr term notes",
            "financing capacity",
            "amounts available to draw",
            "available to draw with collateral pledged",
            "eligible for repurchase",
            "loans and leases held for investment",
            "loans held for investment",
            "loans held for sale",
            "total loans",
            "average credit card and other loans",
            "end-of-period credit card and other loans",
            "loans at fair value",
            "asset-backed financing of variable interest entities",
            "assets under management",
            "credit-oriented strategies",
            "total assets",
            "net assets plus borrowings for investment purposes",
            "interest income interest-bearing deposits",
            "debt securities - taxable",
            "debt securities - nontaxable",
        ],
    )


def _requires_mega_timing_obligation_confirmation(
    deal_row: dict[str, str],
    source_row: dict[str, str],
    notional: float,
) -> bool:
    if notional <= MEGA_TIMING_OBLIGATION_REVIEW_THRESHOLD_USD:
        return False
    return not _has_strong_mega_timing_debt_evidence(deal_row, source_row)


def _has_strong_mega_timing_debt_evidence(
    deal_row: dict[str, str],
    source_row: dict[str, str],
) -> bool:
    text = _capital_source_text(deal_row, source_row)
    if _contains_any(
        text,
        [
            "prospectus supplement",
            "registration statement",
            "from time to time",
            "may offer",
            "may issue",
        ],
    ):
        return False
    has_committed_action = _contains_any(
        text,
        [
            "entered into",
            "issued",
            "completed its offering",
            "completed the offering",
            "borrowed",
            "incurred",
            "increased the commitments",
            "aggregate commitments",
        ],
    )
    has_debt_instrument = _contains_any(
        text,
        [
            "credit agreement",
            "term loan",
            "revolving credit facility",
            "credit facility",
            "bridge loan",
            "indenture",
            "senior notes",
            "secured notes",
            "notes due",
            "lease agreement",
        ],
    )
    return has_committed_action and has_debt_instrument


def _capital_source_text(deal_row: dict[str, str], source_row: dict[str, str]) -> str:
    key_terms = _json_dict(deal_row.get("key_terms"))
    key_term_values = [
        str(value)
        for key, value in key_terms.items()
        if key
        in {
            "agreement_reasons",
            "collateral_descriptions",
            "notional_context_excerpt",
            "notional_context_kind",
            "notional_commitment_scope",
            "notional_positive_terms",
            "notional_rejected_terms",
            "notional_scope_reasons",
        }
    ]
    return " ".join(
        [
            _field(deal_row, "primary_party"),
            _field(deal_row, "title"),
            _field(deal_row, "page_or_section"),
            _field(deal_row, "description"),
            _field(deal_row, "source_quote"),
            _field(source_row, "name"),
            _field(source_row, "collateral_description"),
            _field(source_row, "guarantors"),
            _field(source_row, "page_or_section"),
            _field(source_row, "source_quote"),
            *key_term_values,
        ]
    ).lower()


def _physical_cod_signals(roots: list[Path]) -> list[TimingSignal]:
    signals: list[TimingSignal] = []
    for row in _read_rows(
        roots, [Path("physical") / "projects.csv", Path("physical") / "queue_projects.csv"]
    ):
        signal_date = _parse_date(
            _first_present(
                row,
                "announced_in_service_date",
                "expected_in_service_date",
                "requested_in_service_date",
            )
        )
        if signal_date is None or not _in_horizon(signal_date):
            continue
        status = _field(row, "construction_status").lower()
        if status in {"in_service", "cancelled"}:
            continue
        capacity = max(
            _float(row.get("capacity_mw")),
            _float(row.get("capacity_mw_high")),
            _float(row.get("it_load_mw")),
        )
        if capacity < 50:
            continue
        source_uri = _field(row, "source_uri")
        content_hash = _field(row, "content_hash")
        if not _has_source_provenance(source_uri, content_hash):
            continue
        asset_type = _field(row, "asset_type")
        tags = _relevance_tags(
            " ".join(
                [
                    _field(row, "name"),
                    asset_type,
                    _field(row, "owner"),
                    _field(row, "operator"),
                    _field(row, "major_equipment"),
                    _field(row, "source_uri"),
                ]
            )
        )
        tags = tuple(sorted({*tags, "direct:data_center"}))
        project_name = _field(row, "name")
        signals.append(
            TimingSignal(
                signal_id=_signal_id(
                    "physical", _field(row, "project_id"), source_uri, signal_date
                ),
                quarter=_quarter(signal_date),
                signal_date=signal_date.isoformat(),
                category="physical",
                signal_type="project_cod_or_queue_in_service",
                severity=_physical_severity(capacity, status),
                ecosystem_relevance="physical_execution",
                relevance_tags=tags,
                entity=_field(row, "owner") or _field(row, "operator"),
                counterparty="",
                project_id=_field(row, "project_id"),
                project_name=project_name,
                deal_id="",
                amount_usd=_float(row.get("investment_usd")),
                capacity_mw=round(capacity, 2),
                risk_score=0.0,
                description=_reason(
                    [
                        f"{asset_type or 'physical asset'} target in-service",
                        f"status {status}" if status else "",
                        f"capacity {capacity:,.0f} MW",
                    ]
                ),
                source_uri=source_uri,
                source_uris=(source_uri,) if source_uri else (),
                content_hash=content_hash,
                content_hashes=(content_hash,) if content_hash else (),
                page_or_section=_field(row, "page_or_section"),
                evidence_tier="source_backed_project_timing",
                human_review_status=_field(row, "human_review_status") or "pending",
                source_confidence=_float(row.get("source_confidence") or row.get("confidence")),
            )
        )

    for row in _read_rows(roots, [Path("physical") / "queues.csv"]):
        signal_date = _parse_date(
            _first_present(row, "expected_in_service_date", "requested_in_service_date")
        )
        if signal_date is None or not _in_horizon(signal_date):
            continue
        capacity = max(_float(row.get("requested_mw")), _float(row.get("firm_service_mw")))
        if capacity < 50:
            continue
        source_uri = _field(row, "source_uri")
        content_hash = _field(row, "content_hash")
        if not _has_source_provenance(source_uri, content_hash):
            continue
        signals.append(
            TimingSignal(
                signal_id=_signal_id("queue", _field(row, "project_id"), source_uri, signal_date),
                quarter=_quarter(signal_date),
                signal_date=signal_date.isoformat(),
                category="physical",
                signal_type="queue_expected_in_service",
                severity=_physical_severity(capacity, _field(row, "status")),
                ecosystem_relevance="physical_execution",
                relevance_tags=("direct:data_center",),
                entity="",
                counterparty="",
                project_id=_field(row, "project_id"),
                project_name="",
                deal_id="",
                amount_usd=0.0,
                capacity_mw=round(capacity, 2),
                risk_score=0.0,
                description=_reason(
                    [
                        "grid queue expected in-service",
                        f"status {_field(row, 'status')}" if _field(row, "status") else "",
                        f"requested {capacity:,.0f} MW",
                    ]
                ),
                source_uri=source_uri,
                source_uris=(source_uri,) if source_uri else (),
                content_hash=content_hash,
                content_hashes=(content_hash,) if content_hash else (),
                page_or_section=_field(row, "page_or_section"),
                evidence_tier="source_backed_queue_timing",
                human_review_status=_field(row, "human_review_status") or "pending",
                source_confidence=_float(row.get("source_confidence") or row.get("confidence")),
            )
        )
    return signals


def _compute_timing_signals(roots: list[Path]) -> list[TimingSignal]:
    signals: list[TimingSignal] = []
    for row in _read_rows(roots, [Path("compute") / "eps_depreciation_impacts.csv"]):
        fiscal_year = _int(row.get("fiscal_year"))
        if not START_YEAR <= fiscal_year <= END_YEAR:
            continue
        signal_date = date(fiscal_year, 12, 31)
        amount = max(
            _float(row.get("disclosed_depreciation_usd")),
            _float(row.get("gpu_capex_estimate_usd")),
            _float(row.get("disclosed_net_income_impact_usd")),
        )
        if amount <= 0:
            continue
        source_uri = _field(row, "source_uri")
        content_hash = _field(row, "content_hash")
        if not _has_source_provenance(source_uri, content_hash):
            continue
        signals.append(
            TimingSignal(
                signal_id=_signal_id("eps", _field(row, "impact_id"), source_uri, content_hash),
                quarter=_quarter(signal_date),
                signal_date=signal_date.isoformat(),
                category="compute",
                signal_type="eps_depreciation_impact",
                severity="high" if amount >= 1_000_000_000 else "medium",
                ecosystem_relevance="compute_economics",
                relevance_tags=("direct:compute",),
                entity=_field(row, "entity"),
                counterparty="",
                project_id="",
                project_name="",
                deal_id="",
                amount_usd=round(amount, 2),
                capacity_mw=0.0,
                risk_score=0.0,
                description=_reason(
                    [
                        "depreciation/EPS impact year",
                        f"fiscal year {fiscal_year}",
                        f"amount ${amount:,.0f}",
                    ]
                ),
                source_uri=source_uri,
                source_uris=(source_uri,) if source_uri else (),
                content_hash=content_hash,
                content_hashes=(content_hash,) if content_hash else (),
                page_or_section=_field(row, "page_or_section"),
                evidence_tier="source_backed_compute_timing",
                human_review_status=_field(row, "human_review_status") or "pending",
                source_confidence=_float(row.get("source_confidence") or row.get("confidence")),
            )
        )

    chip_rows = _latest_chip_supply_commitment_rows(
        _read_rows(roots, [Path("compute") / "chip_supply_observations.csv"])
    )
    for row in chip_rows:
        delivery_date = _delivery_window_date(row)
        if delivery_date is None or not _in_horizon(delivery_date):
            continue
        announced_gpus = _float(row.get("announced_gpu_count"))
        delivered_gpus = _float(row.get("delivered_gpu_count"))
        delivery_gap = announced_gpus - delivered_gpus if announced_gpus else 0.0
        announced_mw = _float(row.get("announced_mw"))
        amount = _float(row.get("disclosed_purchase_commitment_usd"))
        if not any((delivery_gap > 0, announced_mw > 0, amount > 0)):
            continue
        source_uri = _field(row, "source_uri")
        content_hash = _field(row, "content_hash")
        if not _has_source_provenance(source_uri, content_hash):
            continue
        signals.append(
            TimingSignal(
                signal_id=_signal_id(
                    "chip", _field(row, "observation_id"), source_uri, content_hash
                ),
                quarter=_quarter(delivery_date),
                signal_date=delivery_date.isoformat(),
                category="compute",
                signal_type="chip_supply_delivery_window",
                severity=_chip_supply_severity(delivery_gap, announced_mw, amount),
                ecosystem_relevance="compute_economics",
                relevance_tags=("direct:compute",),
                entity=_field(row, "entity"),
                counterparty=_field(row, "supplier"),
                project_id=_field(row, "project_or_cluster_id"),
                project_name=_field(row, "project_or_cluster_id"),
                deal_id="",
                amount_usd=round(amount, 2),
                capacity_mw=round(announced_mw, 2),
                risk_score=0.0,
                description=_reason(
                    [
                        "chip supply delivery window",
                        f"{_field(row, 'gpu_generation')} generation"
                        if _field(row, "gpu_generation")
                        else "",
                        f"delivery gap {delivery_gap:,.0f} GPUs" if delivery_gap > 0 else "",
                        f"announced {announced_mw:,.0f} MW" if announced_mw > 0 else "",
                    ]
                ),
                source_uri=source_uri,
                source_uris=(source_uri,) if source_uri else (),
                content_hash=content_hash,
                content_hashes=(content_hash,) if content_hash else (),
                page_or_section=_field(row, "page_or_section"),
                evidence_tier="source_backed_compute_timing",
                human_review_status=_field(row, "human_review_status") or "pending",
                source_confidence=_float(row.get("source_confidence") or row.get("confidence")),
            )
        )
    return signals


def _quarter_rollups(signals: list[TimingSignal]) -> list[TimingQuarter]:
    by_quarter: dict[str, list[TimingSignal]] = defaultdict(list)
    for signal in signals:
        by_quarter[signal.quarter].append(signal)

    quarters: list[TimingQuarter] = []
    for quarter, quarter_signals in by_quarter.items():
        capital_refinancing = sum(
            signal.amount_usd for signal in quarter_signals if signal.category == "capital"
        )
        ai_capital_refinancing = sum(
            signal.amount_usd
            for signal in quarter_signals
            if signal.category == "capital" and _is_ai_relevant(signal)
        )
        physical_capacity = sum(
            signal.capacity_mw for signal in quarter_signals if signal.category == "physical"
        )
        compute_amount = sum(
            signal.amount_usd for signal in quarter_signals if signal.category == "compute"
        )
        chip_supply_capacity = sum(
            signal.capacity_mw
            for signal in quarter_signals
            if signal.signal_type == "chip_supply_delivery_window"
        )
        high_count = sum(signal.severity in {"critical", "high"} for signal in quarter_signals)
        ai_count = sum(_is_ai_relevant(signal) for signal in quarter_signals)
        score = _stress_score(
            capital_refinancing=capital_refinancing,
            ai_capital_refinancing=ai_capital_refinancing,
            physical_capacity=physical_capacity,
            compute_amount=compute_amount,
            high_count=high_count,
            ai_count=ai_count,
        )
        top_drivers = [
            signal.description
            for signal in sorted(quarter_signals, key=_signal_sort_key)[:5]
            if signal.description
        ]
        quarters.append(
            TimingQuarter(
                quarter=quarter,
                stress_score=score,
                signal_count=len(quarter_signals),
                critical_or_high_signal_count=high_count,
                ai_infra_relevant_signal_count=ai_count,
                capital_refinancing_usd=round(capital_refinancing, 2),
                ai_infra_capital_refinancing_usd=round(ai_capital_refinancing, 2),
                physical_capacity_mw=round(physical_capacity, 2),
                compute_amount_usd=round(compute_amount, 2),
                chip_supply_capacity_mw=round(chip_supply_capacity, 2),
                top_drivers=top_drivers,
            )
        )
    quarters.sort(key=lambda quarter: quarter.stress_score, reverse=True)
    return quarters


def _summary(signals: list[TimingSignal], quarters: list[TimingQuarter]) -> TimingSignalSummary:
    categories = Counter(signal.category for signal in signals)
    signal_types = Counter(signal.signal_type for signal in signals)
    ecosystem_relevance = Counter(signal.ecosystem_relevance for signal in signals)
    top_quarters = [quarter.to_dict() for quarter in quarters[:12]]
    peak = quarters[0].quarter if quarters else None
    high_quarters = [quarter.quarter for quarter in quarters if quarter.stress_score >= 0.6]
    sorted_high_quarters = sorted(high_quarters, key=_quarter_sort_key)
    historical_capital_refinancing = _capital_refinancing_sum(
        signals,
        ai_infra_only=False,
        forward=False,
    )
    historical_ai_refinancing = _capital_refinancing_sum(
        signals,
        ai_infra_only=True,
        forward=False,
    )
    forward_capital_refinancing = _capital_refinancing_sum(
        signals,
        ai_infra_only=False,
        forward=True,
    )
    forward_ai_refinancing = _capital_refinancing_sum(
        signals,
        ai_infra_only=True,
        forward=True,
    )
    forward_peak = _forward_peak_quarter(quarters, ai_infra_only=False)
    forward_ai_peak = _forward_peak_quarter(quarters, ai_infra_only=True)
    return TimingSignalSummary(
        signals=len(signals),
        source_backed_signals=sum(1 for signal in signals if signal.source_uri),
        critical_or_high_signals=sum(signal.severity in {"critical", "high"} for signal in signals),
        ai_infra_relevant_signals=sum(_is_ai_relevant(signal) for signal in signals),
        categories=dict(sorted(categories.items())),
        signal_types=dict(sorted(signal_types.items())),
        ecosystem_relevance=dict(sorted(ecosystem_relevance.items())),
        quarters=len({signal.quarter for signal in signals}),
        peak_stress_quarter=peak,
        candidate_stress_window_start=sorted_high_quarters[0] if sorted_high_quarters else peak,
        candidate_stress_window_end=sorted_high_quarters[-1] if sorted_high_quarters else peak,
        capital_refinancing_usd_2024_2030=round(
            sum(signal.amount_usd for signal in signals if signal.category == "capital"),
            2,
        ),
        ai_infra_capital_refinancing_usd_2024_2030=round(
            sum(
                signal.amount_usd
                for signal in signals
                if signal.category == "capital" and _is_ai_relevant(signal)
            ),
            2,
        ),
        capital_refinancing_historical_to_as_of_usd=round(
            historical_capital_refinancing,
            2,
        ),
        ai_infra_capital_refinancing_historical_to_as_of_usd=round(
            historical_ai_refinancing,
            2,
        ),
        capital_refinancing_forward_from_as_of_usd=round(
            forward_capital_refinancing,
            2,
        ),
        ai_infra_capital_refinancing_forward_from_as_of_usd=round(
            forward_ai_refinancing,
            2,
        ),
        forward_refinancing_as_of_quarter=FORWARD_REFINANCING_AS_OF_QUARTER,
        forward_peak_refinancing_quarter=forward_peak.quarter if forward_peak else None,
        forward_peak_ai_infra_refinancing_quarter=(
            forward_ai_peak.quarter if forward_ai_peak else None
        ),
        forward_peak_refinancing_usd=(
            round(forward_peak.capital_refinancing_usd, 2) if forward_peak else 0.0
        ),
        forward_peak_ai_infra_refinancing_usd=(
            round(forward_ai_peak.ai_infra_capital_refinancing_usd, 2)
            if forward_ai_peak
            else 0.0
        ),
        physical_capacity_mw_2024_2030=round(
            sum(signal.capacity_mw for signal in signals if signal.category == "physical"),
            2,
        ),
        compute_amount_usd_2024_2030=round(
            sum(signal.amount_usd for signal in signals if signal.category == "compute"),
            2,
        ),
        chip_supply_capacity_mw_2024_2030=round(
            sum(
                signal.capacity_mw
                for signal in signals
                if signal.signal_type == "chip_supply_delivery_window"
            ),
            2,
        ),
        top_quarters=top_quarters,
        top_signals=[signal.to_dict() for signal in signals[:25]],
    )


def _capital_refinancing_sum(
    signals: list[TimingSignal],
    *,
    ai_infra_only: bool,
    forward: bool,
) -> float:
    return sum(
        signal.amount_usd
        for signal in signals
        if signal.category == "capital"
        and (not ai_infra_only or _is_ai_relevant(signal))
        and _is_forward_refinancing_quarter(signal.quarter) == forward
    )


def _forward_peak_quarter(
    quarters: list[TimingQuarter],
    *,
    ai_infra_only: bool,
) -> TimingQuarter | None:
    forward_quarters = [
        quarter
        for quarter in quarters
        if _is_forward_refinancing_quarter(quarter.quarter)
        and (
            quarter.ai_infra_capital_refinancing_usd
            if ai_infra_only
            else quarter.capital_refinancing_usd
        )
        > 0
    ]
    if not forward_quarters:
        return None
    return max(
        forward_quarters,
        key=lambda quarter: (
            quarter.ai_infra_capital_refinancing_usd
            if ai_infra_only
            else quarter.capital_refinancing_usd,
            -_quarter_sort_key(quarter.quarter)[0],
            -_quarter_sort_key(quarter.quarter)[1],
        ),
    )


def _is_forward_refinancing_quarter(quarter: str) -> bool:
    return _quarter_sort_key(quarter) >= _quarter_sort_key(FORWARD_REFINANCING_AS_OF_QUARTER)


def _dedupe_signals(signals: list[TimingSignal]) -> list[TimingSignal]:
    best_by_key: dict[str, TimingSignal] = {}
    for signal in signals:
        key = "|".join(
            [
                signal.category,
                signal.signal_type,
                signal.quarter,
                signal.deal_id,
                signal.project_id,
                signal.source_uri,
                signal.content_hash,
            ]
        )
        current = best_by_key.get(key)
        if current is None or _signal_sort_key(signal) < _signal_sort_key(current):
            best_by_key[key] = signal
    return list(best_by_key.values())


def _dedupe_timing_economic_obligations(signals: list[TimingSignal]) -> list[TimingSignal]:
    """Collapse repeated capital timing disclosures for the same economic obligation."""

    best_by_key: dict[tuple[str, str, int], TimingSignal] = {}
    duplicates_by_key: dict[tuple[str, str, int], list[TimingSignal]] = defaultdict(list)
    passthrough: list[TimingSignal] = []
    for signal in signals:
        key = _timing_economic_obligation_key(signal)
        if key is None:
            passthrough.append(signal)
            continue
        duplicates_by_key[key].append(signal)
        current = best_by_key.get(key)
        if current is None or _signal_sort_key(signal) < _signal_sort_key(current):
            best_by_key[key] = signal

    merged = [
        _merge_signal_provenance(best_by_key[key], duplicates)
        for key, duplicates in duplicates_by_key.items()
    ]
    return [*passthrough, *merged]


def _timing_economic_obligation_key(
    signal: TimingSignal,
) -> tuple[str, str, int] | None:
    if signal.category != "capital" or signal.signal_type != "refinancing_maturity":
        return None
    entity_key = _normalized_key_part(signal.entity)
    amount_key = round(signal.amount_usd)
    if not entity_key or amount_key <= 0:
        return None
    return (entity_key, signal.quarter, amount_key)


def _merge_signal_provenance(
    representative: TimingSignal,
    duplicates: list[TimingSignal],
) -> TimingSignal:
    source_uris = _ordered_unique(
        [representative.source_uri]
        + [uri for signal in duplicates for uri in signal.source_uris]
    )
    content_hashes = _ordered_unique(
        [representative.content_hash]
        + [content_hash for signal in duplicates for content_hash in signal.content_hashes]
    )
    return replace(
        representative,
        source_uris=tuple(source_uris),
        content_hashes=tuple(content_hashes),
    )


def _ordered_unique(values: list[str]) -> list[str]:
    return [*dict.fromkeys(value for value in values if value)]


def _stress_score(
    *,
    capital_refinancing: float,
    ai_capital_refinancing: float,
    physical_capacity: float,
    compute_amount: float,
    high_count: int,
    ai_count: int,
) -> float:
    score = 0.0
    score += min(ai_capital_refinancing / 25_000_000_000, 1.0) * 0.3
    score += min(capital_refinancing / 75_000_000_000, 1.0) * 0.15
    score += min(physical_capacity / 2_000, 1.0) * 0.25
    score += min(compute_amount / 25_000_000_000, 1.0) * 0.15
    score += min(high_count / 5, 1.0) * 0.1
    score += min(ai_count / 5, 1.0) * 0.05
    return round(min(score, 1.0), 4)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    fieldnames = list(rows[0])
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(value) for key, value in row.items()})


def _read_rows(roots: list[Path], relative_paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for root in roots:
        for relative_path in relative_paths:
            path = root / relative_path
            if not path.exists() or path.stat().st_size == 0:
                continue
            with path.open(newline="") as f:
                reader = csv.DictReader(f)
                rows.extend(
                    {
                        str(key): (value or "").strip()
                        for key, value in row.items()
                        if key is not None
                    }
                    for row in reader
                )
    return rows


def _csv_value(value: Any) -> str | int | float:
    if isinstance(value, tuple | list | dict):
        return json.dumps(value)
    if value is None:
        return ""
    if isinstance(value, bool | int | float | str):
        return value
    return str(value)


def _signal_sort_key(signal: TimingSignal) -> tuple[int, int, float, float, float, str]:
    return (
        SEVERITY_ORDER.get(signal.severity, 9),
        -_relevance_rank(signal.ecosystem_relevance),
        -signal.amount_usd,
        -signal.capacity_mw,
        -signal.risk_score,
        signal.signal_id,
    )


def _quarter_sort_key(quarter: str) -> tuple[int, int]:
    year, quarter_part = quarter.split("-Q", maxsplit=1)
    return int(year), int(quarter_part)


def _capital_severity(notional: float, relevance: str) -> str:
    if notional >= 25_000_000_000 and relevance != "not_tagged":
        return "critical"
    if notional >= 10_000_000_000:
        return "high"
    if notional >= 1_000_000_000:
        return "medium"
    return "watch"


def _physical_severity(capacity_mw: float, status: str) -> str:
    normalized_status = status.lower()
    if capacity_mw >= 1_000 and normalized_status != "in_service":
        return "critical"
    if capacity_mw >= 500:
        return "high"
    if capacity_mw >= 100:
        return "medium"
    return "watch"


def _chip_supply_severity(delivery_gap: float, announced_mw: float, amount: float) -> str:
    if delivery_gap >= 10_000 or announced_mw >= 500 or amount >= 10_000_000_000:
        return "critical"
    if delivery_gap > 0 or announced_mw >= 250 or amount >= 1_000_000_000:
        return "high"
    return "medium"


def _ecosystem_relevance(relevance_tags: tuple[str, ...]) -> str:
    if any(tag.startswith("direct:") for tag in relevance_tags):
        return "direct_ai_infra"
    if any(tag.startswith("watchlist:") for tag in relevance_tags):
        return "watchlist_entity"
    return "not_tagged"


def _is_ai_relevant(signal: TimingSignal) -> bool:
    return signal.ecosystem_relevance in {
        "direct_ai_infra",
        "watchlist_entity",
        "physical_execution",
        "compute_economics",
    }


def _relevance_tags(text: str) -> tuple[str, ...]:
    tags = {
        f"direct:{name}"
        for name, pattern in DIRECT_AI_INFRA_PATTERNS.items()
        if pattern.search(text)
    }
    tags.update(
        f"watchlist:{name}"
        for name, pattern in WATCHLIST_ENTITY_PATTERNS.items()
        if pattern.search(text)
    )
    return tuple(sorted(tags))


def _relevance_rank(relevance: str) -> int:
    return {
        "direct_ai_infra": 4,
        "watchlist_entity": 3,
        "physical_execution": 3,
        "compute_economics": 3,
        "not_tagged": 0,
    }.get(relevance, 0)


def _delivery_window_date(row: dict[str, str]) -> date | None:
    observed = _parse_date(_field(row, "observed_deployment_date"))
    if observed:
        return observed
    raw = _field(row, "delivery_window")
    if not raw:
        return None
    year_match = re.search(r"(20[2-3][0-9])", raw)
    if not year_match:
        return None
    year = int(year_match.group(1))
    month = 12
    if re.search(r"\b(q1|first quarter)\b", raw, re.I):
        month = 3
    elif re.search(r"\b(q2|second quarter)\b", raw, re.I):
        month = 6
    elif re.search(r"\b(q3|third quarter)\b", raw, re.I):
        month = 9
    return date(year, month, 30 if month in {6, 9} else 31)


def _latest_chip_supply_commitment_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep the latest disclosed purchase-commitment snapshot for each chip book."""

    passthrough: list[dict[str, str]] = []
    latest_by_book: dict[
        tuple[str, str, str, str],
        tuple[tuple[date, str, str, str], dict[str, str]],
    ] = {}
    for row in rows:
        if _float(row.get("disclosed_purchase_commitment_usd")) <= 0:
            passthrough.append(row)
            continue
        source_uri = _field(row, "source_uri")
        content_hash = _field(row, "content_hash")
        delivery_date = _delivery_window_date(row)
        if (
            delivery_date is None
            or not _in_horizon(delivery_date)
            or not _has_source_provenance(source_uri, content_hash)
        ):
            passthrough.append(row)
            continue
        key = _chip_supply_commitment_book_key(row)
        rank = (
            _chip_supply_snapshot_date(row),
            _field(row, "filing_accession"),
            _field(row, "document_id"),
            _field(row, "observation_id"),
        )
        previous = latest_by_book.get(key)
        if previous is None or rank > previous[0]:
            latest_by_book[key] = (rank, row)
    return [*passthrough, *(row for _, row in latest_by_book.values())]


def _chip_supply_commitment_book_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        _normalized_key_part(_field(row, "entity")),
        _normalized_key_part(_field(row, "supplier")),
        _normalized_key_part(_field(row, "gpu_generation") or "unspecified"),
        _normalized_key_part(_field(row, "project_or_cluster_id")),
    )


def _chip_supply_snapshot_date(row: dict[str, str]) -> date:
    return (
        _parse_date(_field(row, "observed_deployment_date"))
        or _delivery_window_date(row)
        or date.min
    )


def _normalized_key_part(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    text = value.strip()
    if "T" in text:
        text = text.split("T", maxsplit=1)[0]
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            parsed = date.fromisoformat(
                {
                    "%Y-%m-%d": text,
                    "%Y-%m": f"{text}-01",
                    "%Y": f"{text}-12-31",
                }[fmt]
            )
        except ValueError:
            continue
        return parsed
    return None


def _in_horizon(value: date) -> bool:
    return START_YEAR <= value.year <= END_YEAR


def _quarter(value: date) -> str:
    quarter = ((value.month - 1) // 3) + 1
    return f"{value.year}-Q{quarter}"


def _first_present(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = _field(row, key)
        if value:
            return value
    return ""


def _counterparty_from_row(row: dict[str, str]) -> str:
    roles = _json_dict(row.get("counterparty_roles"))
    for preferred_role in ("lender", "financier", "lessor", "guarantor", "buyer", "offtaker"):
        entities = roles.get(preferred_role)
        if isinstance(entities, list) and entities:
            return str(entities[0])
    parties = [part.strip() for part in _field(row, "parties").split("|") if part.strip()]
    primary = _field(row, "primary_party")
    for party in parties:
        if party != primary:
            return party
    return ""


def _reason(parts: list[str]) -> str:
    return "; ".join(part for part in parts if part)


def _contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _field(row: dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()


def _has_source_provenance(source_uri: str, content_hash: str) -> bool:
    return bool(source_uri and content_hash)


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value or not isinstance(value, str):
        return {}
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(str(value).replace(",", "").replace("$", ""))
    except ValueError:
        return 0.0


def _int(value: Any) -> int:
    return int(_float(value))


def _signal_id(*parts: Any) -> str:
    raw = "|".join(str(part) for part in parts)
    return "timing:" + hashlib.sha256(raw.encode()).hexdigest()[:16]
