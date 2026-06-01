from __future__ import annotations

import csv
import json
from pathlib import Path

from bubble.analysis.contract_contagion_paths import (
    build_contract_contagion_paths,
    write_contract_contagion_paths,
)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_contract_contagion_paths_join_contract_edges_to_ownership(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "graph" / "capital_contract_edges.csv",
        [
            {
                "source_id": "entity:coreweave-spv",
                "source_name": "CoreWeave SPV LLC",
                "source_type": "entity",
                "target_id": "contract:tranche:1",
                "target_name": "GPU facility - Term loan",
                "target_type": "tranche",
                "relationship_type": "OBLIGOR_TO_TRANCHE",
                "deal_id": "deal-1",
                "deal_type": "debt_facility",
                "tranche_id": "A",
                "notional_usd": "7500000000",
                "source_uri": "https://www.sec.gov/credit.htm#tranche-a",
                "content_hash": "hash-contract",
                "human_review_status": "pending",
                "relevance_tags": json.dumps(["direct:compute", "watchlist:coreweave"]),
                "risk_flags": json.dumps(
                    ["spv_signal", "bankruptcy_remote_spv", "non_recourse", "priced_debt"]
                ),
            },
            {
                "source_id": "contract:tranche:1",
                "source_name": "GPU facility - Term loan",
                "source_type": "tranche",
                "target_id": "collateral:gpu",
                "target_name": "first-priority liens on GPU servers",
                "target_type": "collateral",
                "relationship_type": "SECURED_BY_COLLATERAL",
                "deal_id": "deal-1",
                "deal_type": "debt_facility",
                "tranche_id": "A",
                "notional_usd": "7500000000",
                "source_uri": "https://www.sec.gov/credit.htm#tranche-a",
                "content_hash": "hash-contract",
                "human_review_status": "pending",
                "relevance_tags": json.dumps(["direct:compute", "watchlist:coreweave"]),
                "risk_flags": json.dumps(["collateralized", "spv_signal"]),
            },
        ],
    )
    _write_csv(
        tmp_path / "graph" / "ownership_nodes.csv",
        [
            {
                "node_id": "LEI-CHILD",
                "legal_name": "CoreWeave SPV LLC",
                "source_uris": "https://lei.example/lei.zip",
                "content_hashes": "hash-lei-child",
            },
            {
                "node_id": "LEI-PARENT",
                "legal_name": "CoreWeave Parent Inc.",
                "source_uris": "https://lei.example/lei.zip",
                "content_hashes": "hash-lei-parent",
            },
        ],
    )
    _write_csv(
        tmp_path / "graph" / "ownership_edges.csv",
        [
            {
                "child_id": "LEI-CHILD",
                "parent_id": "LEI-PARENT",
                "relationship_type": "IS_DIRECTLY_CONSOLIDATED_BY",
                "relationship_status": "ACTIVE",
                "quantifier_amount": "100",
                "quantifier_units": "PERCENTAGE",
                "quantifier_method": "ACCOUNTING_CONSOLIDATION",
                "validation_sources": "FULLY_CORROBORATED",
                "source_uri": "https://lei.example/rr.zip",
                "content_hash": "hash-rr",
            }
        ],
    )

    batch = build_contract_contagion_paths([tmp_path], min_notional_usd=1_000_000)
    ownership_paths = [path for path in batch.paths if path.path_type == "ownership_expanded"]

    assert batch.summary.contract_edges_scanned == 2
    assert batch.summary.high_impact_contract_edges == 2
    assert batch.summary.ownership_nodes_indexed == 2
    assert batch.summary.ownership_edges_indexed == 1
    assert batch.summary.contract_entity_name_matches == 1
    assert batch.summary.paths == 2
    assert batch.summary.source_backed_paths == 2
    assert batch.summary.ownership_expanded_paths == 1
    assert batch.summary.contract_only_paths == 1
    assert batch.summary.ai_infra_relevant_paths == 2
    assert batch.summary.collateral_paths == 1
    assert batch.summary.non_recourse_paths == 1
    assert batch.summary.spv_paths == 2
    assert ownership_paths[0].ownership_path_node_ids == ("LEI-CHILD", "LEI-PARENT")
    assert ownership_paths[0].ownership_path_names == (
        "CoreWeave SPV LLC",
        "CoreWeave Parent Inc.",
    )
    assert ownership_paths[0].source_uris == (
        "https://www.sec.gov/credit.htm#tranche-a",
        "https://lei.example/rr.zip",
    )

    outputs = write_contract_contagion_paths(batch, tmp_path / "reports")
    assert Path(outputs["paths_csv"]).exists()
    assert Path(outputs["summary_json"]).exists()


def test_contract_contagion_paths_require_source_backed_high_impact_edges(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "graph" / "capital_contract_edges.csv",
        [
            {
                "source_id": "entity:small",
                "source_name": "Small Borrower LLC",
                "source_type": "entity",
                "target_id": "contract:deal:small",
                "target_name": "Small facility",
                "target_type": "deal",
                "relationship_type": "OBLIGATED_UNDER_DEAL",
                "deal_id": "small",
                "deal_type": "debt_facility",
                "notional_usd": "999",
                "source_uri": "https://www.sec.gov/small.htm",
                "content_hash": "hash-small",
                "human_review_status": "pending",
                "relevance_tags": "[]",
                "risk_flags": "[]",
            },
            {
                "source_id": "entity:missing-source",
                "source_name": "Missing Source LLC",
                "source_type": "entity",
                "target_id": "contract:deal:missing-source",
                "target_name": "Missing source facility",
                "target_type": "deal",
                "relationship_type": "OBLIGATED_UNDER_DEAL",
                "deal_id": "missing-source",
                "deal_type": "debt_facility",
                "notional_usd": "5000000000",
                "source_uri": "",
                "content_hash": "hash-missing",
                "human_review_status": "pending",
                "relevance_tags": "[]",
                "risk_flags": "[]",
            },
        ],
    )

    batch = build_contract_contagion_paths([tmp_path], min_notional_usd=1_000_000)

    assert batch.summary.high_impact_contract_edges == 0
    assert batch.summary.paths == 0
