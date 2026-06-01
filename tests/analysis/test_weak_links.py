from __future__ import annotations

import csv
import json
from pathlib import Path

from bubble.analysis.weak_links import build_weak_link_batch, write_weak_link_batch


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_weak_links_rank_capital_and_physical_candidates(tmp_path: Path) -> None:
    graph_dir = tmp_path / "graph"
    graph_dir.mkdir()
    _write_csv(
        graph_dir / "capital_exposure_edges.csv",
        [
            {
                "source_name": "CoreWeave SPV",
                "target_name": "Apollo Credit",
                "relationship_type": "OWES_OR_BORROWS_FROM",
                "deal_type": "debt_facility",
                "notional_usd": 12_000_000_000,
                "source_uris": json.dumps(["sec:credit"]),
                "content_hashes": json.dumps(["hash-1"]),
                "human_review_statuses": json.dumps(["pending"]),
                "relevance_tags": json.dumps(["direct:compute", "watchlist:coreweave"]),
            }
        ],
    )
    _write_csv(
        tmp_path / "edgar_acquisition" / "deals.csv",
        [
            {
                "deal_id": "credit-1",
                "deal_type": "debt_facility",
                "title": "AI data center credit agreement",
                "primary_party": "CoreWeave SPV",
                "parties": "CoreWeave SPV|Apollo Credit",
                "notional_amount_usd": "30000000000",
                "maturity_date": "2027-03-31",
                "source_uri": "https://www.sec.gov/coreweave-credit.htm",
                "source_type": "sec_edgar",
                "source_confidence": "0.87",
                "human_review_status": "pending",
                "page_or_section": "8-K exhibit",
                "content_hash": "hash-credit",
                "key_terms": json.dumps({"interest_rate": "10%"}),
            }
        ],
    )
    (graph_dir / "capital_exposure_graph_summary.json").write_text(
        json.dumps(
            {
                "ai_infra_relevant_edges": 1,
                "direct_ai_keyword_edges": 1,
                "ai_infra_relevant_notional_usd": 12_000_000_000,
            }
        )
    )

    physical_dir = tmp_path / "physical"
    physical_dir.mkdir()
    _write_csv(
        physical_dir / "projects.csv",
        [
            {
                "project_id": "project-1",
                "name": "CoreWeave Campus",
                "asset_type": "data_center_campus",
                "capacity_mw": "500",
                "owner": "CoreWeave SPV",
                "construction_status": "announced",
                "source_uri": "tracker:project",
                "source_type": "project_tracker",
                "content_hash": "project-hash",
            }
        ],
    )
    _write_csv(
        physical_dir / "queues.csv",
        [
            {
                "project_id": "project-1",
                "queue_id": "Q-1",
                "region": "PJM",
                "status": "study",
                "requested_mw": "500",
                "firm_service_mw": "0",
                "source_uri": "queue:project-1",
                "source_type": "grid_interconnection_queue",
                "content_hash": "queue-hash",
            }
        ],
    )

    batch = build_weak_link_batch([tmp_path], top_physical_limit=10)

    assert batch.summary.capital_candidates == 1
    assert batch.summary.physical_candidates == 1
    assert batch.summary.debt_service_candidates == 1
    assert batch.summary.combined_candidates == 1
    assert batch.summary.ai_infra_relevant_notional_usd == 12_000_000_000
    assert batch.summary.top_debt_service_weak_links[0]["entity"] == "CoreWeave SPV"
    assert batch.summary.top_debt_service_weak_links[0]["category"] == "debt_service_stress"
    assert batch.candidates[0].risk_level in {"critical", "high"}


def test_write_weak_links_outputs_summary_and_candidates(tmp_path: Path) -> None:
    graph_dir = tmp_path / "graph"
    graph_dir.mkdir()
    (graph_dir / "capital_exposure_edges.csv").write_text("")
    (graph_dir / "capital_exposure_graph_summary.json").write_text("{}")
    physical_dir = tmp_path / "physical"
    physical_dir.mkdir()
    _write_csv(
        physical_dir / "projects.csv",
        [
            {
                "project_id": "project-1",
                "name": "Example Data Center",
                "asset_type": "data_center_campus",
                "capacity_mw": "100",
                "source_uri": "tracker:project",
                "source_type": "project_tracker",
                "content_hash": "project-hash",
            }
        ],
    )

    batch = build_weak_link_batch([tmp_path], top_physical_limit=5)
    outputs = write_weak_link_batch(batch, tmp_path / "reports")

    assert Path(outputs["summary_json"]).exists()
    assert Path(outputs["candidates_csv"]).exists()
