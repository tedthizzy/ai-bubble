from __future__ import annotations

import csv
import json
from pathlib import Path

from bubble.analysis.review_queue import build_review_queue, write_review_queue


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_review_queue_prioritizes_source_backed_pending_items(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "edgar_acquisition" / "deals.csv",
        [
            {
                "deal_id": "deal-critical",
                "deal_type": "debt_facility",
                "primary_party": "CoreWeave",
                "parties": "CoreWeave|Apollo Credit",
                "counterparty_roles": json.dumps({"lender": ["Apollo Credit"]}),
                "notional_amount_usd": "30000000000",
                "source_uri": "https://www.sec.gov/credit.htm",
                "source_type": "sec_edgar",
                "source_confidence": "0.86",
                "human_review_status": "pending",
                "page_or_section": "8-K exhibit",
                "content_hash": "hash-credit",
                "key_terms": json.dumps(
                    {
                        "requires_human_review": True,
                        "notional_context_kind": "candidate_notional",
                        "extraction_method": "deterministic_edgar_agreement_v1",
                    }
                ),
            },
            {
                "deal_id": "deal-approved",
                "deal_type": "debt_facility",
                "primary_party": "Reviewed Borrower",
                "parties": "Reviewed Borrower|Reviewed Lender",
                "notional_amount_usd": "50000000000",
                "source_uri": "https://www.sec.gov/reviewed.htm",
                "source_confidence": "0.91",
                "human_review_status": "approved",
                "content_hash": "hash-reviewed",
                "key_terms": "{}",
            },
        ],
    )
    _write_csv(
        tmp_path / "reports" / "weak_link_candidates.csv",
        [
            {
                "weak_link_id": "weak-1",
                "category": "combined_capital_physical",
                "risk_score": "0.82",
                "risk_level": "critical",
                "entity": "CoreWeave",
                "counterparty": "Apollo Credit",
                "project_id": "project-1",
                "project_name": "CoreWeave Campus",
                "exposure_usd": "12000000000",
                "capacity_mw": "700",
                "queue_requested_mw": "700",
                "risk_drivers": json.dumps(["large exposure", "queue delay"]),
                "source_uris": json.dumps(["https://www.sec.gov/credit.htm"]),
                "content_hashes": json.dumps(["hash-credit"]),
                "human_review_statuses": json.dumps(["pending"]),
            }
        ],
    )
    _write_csv(
        tmp_path / "graph" / "capital_exposure_edges.csv",
        [
            {
                "source_deal_ids": json.dumps(["deal-critical"]),
                "source_uris": json.dumps(["https://www.sec.gov/credit.htm"]),
                "content_hashes": json.dumps(["hash-credit"]),
                "relevance_tags": json.dumps(["direct:compute", "watchlist:coreweave"]),
            }
        ],
    )
    _write_csv(
        tmp_path / "physical" / "queue_project_matches.csv",
        [
            {
                "match_id": "match-1",
                "match_status": "strong_match",
                "match_confidence": "0.95",
                "match_reasons": "name_overlap|state_match",
                "queue_customer": "CoreWeave",
                "queue_capacity_mw": "700",
                "matched_project_id": "project-1",
                "matched_project_name": "CoreWeave Campus",
                "matched_project_owner": "CoreWeave",
                "source_uri": "https://queue.example/export.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "hash-queue",
                "page_or_section": "queue row 10",
                "human_review_status": "pending",
            }
        ],
    )
    _write_csv(
        tmp_path / "compute" / "tam_claims.csv",
        [
            {
                "claim_id": "tam-1",
                "entity": "Cerebras",
                "claimed_market": "AI compute",
                "stated_tam_usd": "2400000000000",
                "source_uri": "https://www.sec.gov/s1.htm",
                "source_type": "sec_edgar",
                "retrieved_at": "2026-06-01T00:00:00+00:00",
                "source_confidence": "0.82",
                "human_review_status": "pending",
                "page_or_section": "S-1 TAM claim",
                "content_hash": "hash-tam",
            }
        ],
    )

    batch = build_review_queue([tmp_path])

    assert batch.summary.items == 4
    assert batch.summary.critical_items == 2
    assert batch.summary.high_items == 2
    assert batch.summary.categories == {
        "capital": 1,
        "compute": 1,
        "physical": 1,
        "weak_link": 1,
    }
    assert batch.summary.ecosystem_relevance == {
        "compute_economics": 1,
        "direct_ai_infra": 1,
        "physical_execution": 2,
    }
    assert batch.summary.ai_infra_relevant_items == 4
    assert batch.summary.pending_notional_amount_usd == 2_430_000_000_000
    assert batch.summary.pending_capital_notional_amount_usd == 30_000_000_000
    assert batch.summary.pending_capital_distinct_group_count == 1
    assert batch.summary.pending_capital_distinct_notional_amount_usd == 30_000_000_000
    assert batch.summary.pending_capital_duplicate_notional_amount_usd == 0
    assert (
        batch.summary.pending_ai_infra_relevant_capital_distinct_notional_amount_usd
        == 30_000_000_000
    )
    assert batch.summary.pending_compute_claim_amount_usd == 2_400_000_000_000
    assert batch.items[0].deal_id == "deal-critical"
    assert batch.items[0].ecosystem_relevance == "direct_ai_infra"
    assert batch.items[0].relevance_tags == ("direct:compute", "watchlist:coreweave")
    assert batch.items[0].source_uri == "https://www.sec.gov/credit.htm"
    assert batch.items[0].content_hash == "hash-credit"
    assert all(item.deal_id != "deal-approved" for item in batch.items)


def test_write_review_queue_outputs_csv_and_summary(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "compute" / "eps_depreciation_impacts.csv",
        [
            {
                "impact_id": "eps-1",
                "entity": "Meta Platforms",
                "fiscal_year": "2025",
                "disclosed_depreciation_usd": "2920000000",
                "disclosed_eps_impact_usd": "1.0",
                "source_uri": "https://www.sec.gov/meta-10k.htm",
                "source_type": "sec_edgar",
                "retrieved_at": "2026-06-01T00:00:00+00:00",
                "source_confidence": "0.82",
                "human_review_status": "pending",
                "page_or_section": "10-K depreciation impact",
                "content_hash": "hash-eps",
            }
        ],
    )

    batch = build_review_queue([tmp_path])
    outputs = write_review_queue(batch, tmp_path / "reports")

    assert Path(outputs["queue_csv"]).exists()
    assert Path(outputs["summary_json"]).exists()
    summary = json.loads(Path(outputs["summary_json"]).read_text())
    assert summary["items"] == 1
    assert summary["high_items"] == 1


def test_review_queue_surfaces_high_impact_contract_tranches(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "edgar_acquisition" / "tranches.csv",
        [
            {
                "deal_id": "deal-coreweave-tranche",
                "tranche_id": "A",
                "name": "Senior secured term loan",
                "notional_usd": "7500000000",
                "interest_rate": "0.0725",
                "maturity": "2028-06-30",
                "collateral_description": "first-priority liens on GPU servers",
                "guarantors": "Example Parent LLC",
                "source_uri": "https://www.sec.gov/credit.htm#tranche-a",
                "source_type": "sec_edgar",
                "source_confidence": "0.86",
                "human_review_status": "pending",
                "page_or_section": "tranche A",
                "content_hash": "hash-tranche-a",
            }
        ],
    )
    _write_csv(
        tmp_path / "graph" / "capital_exposure_edges.csv",
        [
            {
                "source_deal_ids": json.dumps(["deal-coreweave-tranche"]),
                "source_uris": json.dumps(["https://www.sec.gov/credit.htm#tranche-a"]),
                "content_hashes": json.dumps(["hash-tranche-a"]),
                "relevance_tags": json.dumps(["direct:compute", "watchlist:coreweave"]),
            }
        ],
    )

    batch = build_review_queue([tmp_path])

    assert batch.summary.items == 1
    assert batch.summary.high_items == 1
    assert batch.summary.categories == {"contract": 1}
    assert batch.summary.subcategories == {"contract_tranche_terms": 1}
    assert batch.summary.pending_contract_tranche_items == 1
    assert batch.summary.pending_contract_tranche_notional_amount_usd == 7_500_000_000
    assert batch.summary.pending_capital_notional_amount_usd == 0
    assert batch.items[0].category == "contract"
    assert batch.items[0].ecosystem_relevance == "direct_ai_infra"
    assert batch.items[0].relevance_tags == ("direct:compute", "watchlist:coreweave")
    assert "collateral terms present" in batch.items[0].reason
    assert batch.items[0].source_uri.endswith("#tranche-a")


def test_review_queue_surfaces_contract_contagion_paths(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "reports" / "contract_contagion_paths.csv",
        [
            {
                "path_id": "contagion-1",
                "path_type": "ownership_expanded",
                "risk_level": "high",
                "risk_score": "0.72",
                "start_entity_name": "CoreWeave SPV LLC",
                "contract_counterparty_name": "Apollo Credit",
                "contract_relationship_type": "OBLIGOR_TO_TRANCHE",
                "deal_id": "deal-coreweave",
                "tranche_id": "A",
                "notional_usd": "7500000000",
                "ownership_path_node_ids": json.dumps(["LEI-CHILD", "LEI-PARENT"]),
                "reason": "ownership expanded contagion path; notional $7,500,000,000",
                "source_uris": json.dumps(
                    ["https://www.sec.gov/credit.htm", "https://lei.example/rr.zip"]
                ),
                "content_hashes": json.dumps(["hash-contract", "hash-rr"]),
                "human_review_statuses": json.dumps(["pending", "ownership_source_backed"]),
                "relevance_tags": json.dumps(["direct:compute", "watchlist:coreweave"]),
            }
        ],
    )

    batch = build_review_queue([tmp_path])

    assert batch.summary.items == 1
    assert batch.summary.high_items == 1
    assert batch.summary.categories == {"contagion": 1}
    assert batch.summary.pending_contagion_path_items == 1
    assert batch.summary.pending_contagion_path_exposure_usd == 7_500_000_000
    assert batch.summary.ai_infra_relevant_items == 1
    assert batch.items[0].subcategory == "ownership_expanded"
    assert batch.items[0].ecosystem_relevance == "direct_ai_infra"
    assert batch.items[0].source_uris == (
        "https://www.sec.gov/credit.htm",
        "https://lei.example/rr.zip",
    )


def test_review_queue_surfaces_debt_service_weak_links(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "reports" / "weak_link_candidates.csv",
        [
            {
                "weak_link_id": "weak-debt-1",
                "category": "debt_service_stress",
                "risk_score": "0.91",
                "risk_level": "critical",
                "entity": "CoreWeave SPV",
                "counterparty": "",
                "project_id": "",
                "project_name": "",
                "exposure_usd": "30000000000",
                "capacity_mw": "0",
                "queue_requested_mw": "0",
                "risk_drivers": json.dumps(
                    [
                        "Entity-level source-backed debt-service stress",
                        "2024-2030 maturity wall $30,000,000,000",
                        "Peak maturity quarter 2027-Q1",
                    ]
                ),
                "source_uris": json.dumps(["https://www.sec.gov/coreweave-credit.htm"]),
                "content_hashes": json.dumps(["hash-credit"]),
                "human_review_statuses": json.dumps(["pending"]),
                "relevance_tags": json.dumps(["direct:debt_service"]),
            }
        ],
    )

    batch = build_review_queue([tmp_path])

    assert batch.summary.items == 1
    assert batch.summary.critical_items == 1
    assert batch.summary.pending_exposure_usd == 30_000_000_000
    assert batch.summary.categories == {"weak_link": 1}
    assert batch.items[0].subcategory == "debt_service_stress"
    assert batch.items[0].ecosystem_relevance == "direct_ai_infra"
    assert batch.items[0].source_uri == "https://www.sec.gov/coreweave-credit.htm"


def test_review_queue_groups_repeated_aggregate_capital_candidates(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "edgar_acquisition" / "deals.csv",
        [
            {
                "deal_id": "lease-1",
                "deal_type": "lease",
                "primary_party": "Alphabet Inc.",
                "parties": "Alphabet Inc.",
                "notional_amount_usd": "75600000000",
                "source_uri": "https://www.sec.gov/alphabet-424b5-a.htm",
                "source_confidence": "0.82",
                "human_review_status": "pending",
                "content_hash": "hash-a",
                "key_terms": json.dumps(
                    {
                        "requires_human_review": True,
                        "notional_context_kind": "aggregate_lease_obligation",
                        "accession_number": "0001",
                    }
                ),
            },
            {
                "deal_id": "lease-2",
                "deal_type": "lease",
                "primary_party": "Alphabet Inc.",
                "parties": "Alphabet Inc.",
                "notional_amount_usd": "75600000000",
                "source_uri": "https://www.sec.gov/alphabet-424b5-b.htm",
                "source_confidence": "0.86",
                "human_review_status": "pending",
                "content_hash": "hash-b",
                "key_terms": json.dumps(
                    {
                        "requires_human_review": True,
                        "notional_context_kind": "aggregate_lease_obligation",
                        "accession_number": "0002",
                    }
                ),
            },
        ],
    )
    _write_csv(
        tmp_path / "graph" / "capital_exposure_edges.csv",
        [
            {
                "source_deal_ids": json.dumps(["lease-1", "lease-2"]),
                "source_uris": json.dumps(
                    [
                        "https://www.sec.gov/alphabet-424b5-a.htm",
                        "https://www.sec.gov/alphabet-424b5-b.htm",
                    ]
                ),
                "content_hashes": json.dumps(["hash-a", "hash-b"]),
                "relevance_tags": json.dumps(["watchlist:alphabet"]),
            }
        ],
    )

    batch = build_review_queue([tmp_path])

    assert batch.summary.items == 2
    assert batch.summary.pending_capital_notional_amount_usd == 151_200_000_000
    assert batch.summary.pending_capital_distinct_group_count == 1
    assert batch.summary.pending_capital_distinct_notional_amount_usd == 75_600_000_000
    assert batch.summary.pending_capital_duplicate_notional_amount_usd == 75_600_000_000
    assert (
        batch.summary.pending_ai_infra_relevant_capital_distinct_notional_amount_usd
        == 75_600_000_000
    )
    assert batch.summary.top_distinct_capital_items[0]["ecosystem_relevance"] == (
        "watchlist_entity"
    )
