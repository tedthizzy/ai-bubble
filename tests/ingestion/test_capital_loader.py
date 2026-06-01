from __future__ import annotations

import csv
from datetime import date
from typing import TYPE_CHECKING

from bubble.graph.client import BubbleGraphClient, InMemoryStore
from bubble.ingestion.capital import (
    analyze_capital_evidence,
    ingest_capital_evidence,
    load_capital_evidence,
)

if TYPE_CHECKING:
    from pathlib import Path


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    assert rows
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_fixture(directory: Path) -> None:
    common_source = {
        "source_confidence": 0.91,
        "human_review_status": "approved",
    }
    _write_csv(
        directory / "deals.csv",
        [
            {
                "deal_id": "deal-1",
                "deal_type": "debt_facility",
                "title": "SPV GPU collateral facility",
                "parties": "coreweave-spv|apollo-credit",
                "counterparty_roles": '{"borrower":["coreweave-spv"],"lender":["apollo-credit"],"insurer":["athene-wrapper"]}',
                "bankruptcy_remote_spv": "true",
                "guarantees": "athene-wrapper",
                "source_uri": "sec:credit-agreement",
                "source_type": "sec_edgar",
                **common_source,
            },
            {
                "deal_id": "deal-2",
                "deal_type": "lease",
                "title": "Synthetic lease for AI campus",
                "parties": "developer-spv|hyperscaler-anchor",
                "counterparty_roles": '{"lessor":["developer-spv"],"lessee":["hyperscaler-anchor"]}',
                "notional_amount_usd": 800_000_000,
                "maturity_date": "2028-03-31",
                "is_non_recourse": "true",
                "key_terms": '{"synthetic_lease":true}',
                "source_uri": "sec:synthetic-lease",
                "source_type": "sec_edgar",
                **common_source,
            },
            {
                "deal_id": "deal-3",
                "deal_type": "ppa",
                "title": "Power purchase agreement",
                "parties": "developer-spv|utility",
                "notional_amount_usd": 600_000_000,
                "maturity_date": "2035-01-01",
                "source_uri": "state-puc:ppa",
                "source_type": "state_puc",
                **common_source,
            },
        ],
    )
    _write_csv(
        directory / "tranches.csv",
        [
            {
                "deal_id": "deal-1",
                "tranche_id": "A",
                "name": "Term Loan A",
                "seniority": 1,
                "notional_usd": 1_000_000_000,
                "maturity": "2026-12-15",
                "guarantors": "athene-wrapper",
                "source_uri": "sec:credit-agreement#tranche-a",
                "source_type": "sec_edgar",
                **common_source,
            },
            {
                "deal_id": "deal-1",
                "tranche_id": "B",
                "name": "Term Loan B",
                "seniority": 2,
                "notional_usd": 500_000_000,
                "maturity": "2027-06-30",
                "source_uri": "sec:credit-agreement#tranche-b",
                "source_type": "sec_edgar",
                **common_source,
            },
        ],
    )


def _memory_graph() -> BubbleGraphClient:
    client = BubbleGraphClient.__new__(BubbleGraphClient)
    client._mode = "memory"
    client._neo_driver = None
    client._memory = InMemoryStore()
    return client


def test_load_capital_evidence_parses_deals_tranches_and_provenance(tmp_path: Path) -> None:
    _write_fixture(tmp_path)

    batch = load_capital_evidence(tmp_path)

    assert len(batch.deals) == 3
    assert batch.deals[0].source_deal_id == "deal-1"
    assert len(batch.deals[0].debt_tranches) == 2
    assert batch.deals[0].counterparty_roles["lender"] == ["apollo-credit"]
    assert batch.deals[0].provenance.source_uri == "sec:credit-agreement"
    assert batch.deals[0].debt_tranches[0].provenance.source_uri.endswith("tranche-a")


def test_analyze_capital_evidence_computes_metrics(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    batch = load_capital_evidence(tmp_path)

    metrics = analyze_capital_evidence(batch, as_of=date(2026, 1, 1))

    assert metrics.deal_count == 3
    assert metrics.debt_like_notional_usd == 2_300_000_000
    assert metrics.distinct_debt_like_notional_usd == 2_300_000_000
    assert metrics.duplicate_candidate_notional_usd == 0
    assert metrics.aggregate_obligation_distinct_notional_usd == 0
    assert metrics.off_balance_sheet_usd == 2_300_000_000
    assert metrics.guarantee_linked_usd == 1_500_000_000
    assert metrics.spv_or_non_recourse_usd == 2_300_000_000
    assert metrics.reviewed_debt_like_notional_usd == 2_300_000_000
    assert metrics.pending_review_debt_like_notional_usd == 0
    assert metrics.notional_review_required_usd == 0
    assert metrics.refinancing_wall_by_quarter == {
        "2026-Q4": 1_000_000_000,
        "2027-Q2": 500_000_000,
        "2028-Q1": 800_000_000,
    }
    assert metrics.evidence_summary["high_confidence_eligible_claims"] == 14


def test_ingest_capital_evidence_merges_deals_and_returns_metrics(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    graph = _memory_graph()

    summary = ingest_capital_evidence(tmp_path, graph=graph, as_of=date(2026, 1, 1))
    labels = [node["label"] for node in graph.query_nodes()]

    assert summary["deals"] == 3
    assert summary["tranches"] == 2
    assert summary["debt_like_deals"] == 2
    assert summary["debt_like_notional_usd"] == 2_300_000_000
    assert summary["distinct_debt_like_notional_usd"] == 2_300_000_000
    assert summary["duplicate_candidate_notional_usd"] == 0
    assert summary["aggregate_obligation_distinct_notional_usd"] == 0
    assert summary["guarantee_linked_usd"] == 1_500_000_000
    assert summary["spv_or_non_recourse_usd"] == 2_300_000_000
    assert summary["reviewed_debt_like_notional_usd"] == 2_300_000_000
    assert summary["pending_review_debt_like_notional_usd"] == 0
    assert summary["notional_review_required_usd"] == 0
    assert summary["notional_review_required_deals"] == 0
    assert summary["high_confidence_claims"] == 14
    assert labels == ["Deal", "Deal", "Deal"]
