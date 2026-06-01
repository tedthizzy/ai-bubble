from __future__ import annotations

import csv
import json
from pathlib import Path

from bubble.analysis.materiality_adjudication import (
    build_materiality_adjudication_packets,
    write_materiality_adjudication_packets,
)
from bubble.analysis.materiality_adjudication_results import (
    build_materiality_adjudication_decisions,
    write_materiality_adjudication_decisions,
)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_materiality_adjudication_packets_dedupe_and_attach_snippets(tmp_path: Path) -> None:
    source_path = tmp_path / "data" / "edgar_acquisition" / "documents" / "coreweave.htm"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(
        """
        <html><body>
        CoreWeave entered into a committed senior secured term loan with Apollo Credit.
        The facility is collateralized by GPU servers and requires evaluation of
        borrower, lender, maturity, recourse, and collateral terms.
        </body></html>
        """
    )
    _write_csv(
        tmp_path / "data" / "edgar_acquisition" / "edgar_document_inventory.csv",
        [
            {
                "filing_url": "https://www.sec.gov/coreweave-credit.htm",
                "local_path": str(source_path),
                "content_hash": "a" * 64,
                "primary_document": "coreweave-credit.htm",
                "accession_number": "0001-26-000001",
            }
        ],
    )
    _write_csv(
        tmp_path / "data" / "reports" / "review_queue.csv",
        [
            {
                "review_id": "review-1",
                "review_group_id": "group-1",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "direct_ai_infra",
                "relevance_tags": json.dumps(["direct:compute"]),
                "entity": "CoreWeave",
                "counterparty": "Apollo Credit",
                "project_id": "",
                "project_name": "",
                "deal_id": "deal-1",
                "source_row_id": "row-1",
                "notional_amount_usd": "30000000000",
                "exposure_usd": "0",
                "capacity_mw": "0",
                "risk_score": "0.8",
                "reason": "pending adjudication status: pending",
                "recommended_action": "Confirm terms",
                "source_uri": "https://www.sec.gov/coreweave-credit.htm",
                "source_uris": json.dumps(["https://www.sec.gov/coreweave-credit.htm"]),
                "content_hash": "a" * 64,
                "content_hashes": json.dumps(["a" * 64]),
                "page_or_section": "8-K exhibit",
                "human_review_status": "pending",
                "source_confidence": "0.86",
            },
            {
                "review_id": "review-duplicate",
                "review_group_id": "group-1",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "CoreWeave",
                "counterparty": "Apollo Credit",
                "deal_id": "deal-duplicate",
                "source_row_id": "row-duplicate",
                "notional_amount_usd": "20000000000",
                "exposure_usd": "0",
                "capacity_mw": "0",
                "risk_score": "0.4",
                "reason": "lower materiality duplicate",
                "recommended_action": "Confirm terms",
                "source_uri": "https://www.sec.gov/coreweave-credit.htm",
                "source_uris": json.dumps(["https://www.sec.gov/coreweave-credit.htm"]),
                "content_hash": "a" * 64,
                "content_hashes": json.dumps(["a" * 64]),
                "page_or_section": "8-K exhibit",
                "human_review_status": "pending",
            },
            {
                "review_id": "review-physical",
                "review_group_id": "group-2",
                "priority": "high",
                "category": "physical",
                "subcategory": "queue_project_match",
                "ecosystem_relevance": "physical_execution",
                "entity": "ProjectCo",
                "counterparty": "",
                "project_id": "project-1",
                "project_name": "ProjectCo Campus",
                "deal_id": "",
                "source_row_id": "match-1",
                "notional_amount_usd": "0",
                "exposure_usd": "0",
                "capacity_mw": "700",
                "risk_score": "0.5",
                "reason": "large capacity match",
                "recommended_action": "Confirm physical match",
                "source_uri": "https://queue.example/export.xlsx",
                "source_uris": json.dumps(["https://queue.example/export.xlsx"]),
                "content_hash": "b" * 64,
                "content_hashes": json.dumps(["b" * 64]),
                "page_or_section": "queue row 7",
                "human_review_status": "pending",
            },
            {
                "review_id": "review-approved",
                "review_group_id": "group-3",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "ApprovedCo",
                "notional_amount_usd": "90000000000",
                "source_uri": "https://www.sec.gov/approved.htm",
                "content_hash": "c" * 64,
                "human_review_status": "approved",
            },
        ],
    )

    batch = build_materiality_adjudication_packets([tmp_path / "data"], limit=10)

    assert batch.summary.packets == 2
    assert batch.summary.source_backed_packets == 2
    assert batch.summary.packets_with_local_evidence_snippets == 1
    assert batch.summary.categories == {"capital": 1, "physical": 1}
    assert batch.packets[0].review_id == "review-1"
    assert batch.packets[0].rank == 1
    assert batch.packets[0].adjudication_status == "pending_llm_adjudication"
    assert "committed financing" in batch.packets[0].adjudication_questions[0]
    assert "CoreWeave entered into a committed senior secured term loan" in (
        batch.packets[0].evidence_snippets[0].snippet
    )
    assert batch.packets[0].source_uri == "https://www.sec.gov/coreweave-credit.htm"
    assert batch.packets[0].content_hash == "a" * 64
    assert all(packet.review_id != "review-duplicate" for packet in batch.packets)
    assert all(packet.review_id != "review-approved" for packet in batch.packets)


def test_write_materiality_adjudication_packets(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "reports" / "review_queue.csv",
        [
            {
                "review_id": "review-1",
                "review_group_id": "group-1",
                "priority": "high",
                "category": "compute",
                "subcategory": "gpu_depreciation_policy",
                "ecosystem_relevance": "compute_economics",
                "entity": "Hyperscaler",
                "notional_amount_usd": "1000000000",
                "source_uri": "https://www.sec.gov/10k.htm",
                "source_uris": json.dumps(["https://www.sec.gov/10k.htm"]),
                "content_hash": "d" * 64,
                "content_hashes": json.dumps(["d" * 64]),
                "human_review_status": "pending",
            }
        ],
    )

    batch = build_materiality_adjudication_packets([tmp_path], limit=1)
    outputs = write_materiality_adjudication_packets(batch, tmp_path / "reports")

    assert Path(outputs["packets_csv"]).exists()
    assert Path(outputs["summary_json"]).exists()
    summary = json.loads(Path(outputs["summary_json"]).read_text())
    assert summary["packets"] == 1
    assert summary["categories"] == {"compute": 1}


def test_materiality_packet_snippet_targets_source_backed_aggregate_lease_amount(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "data" / "edgar_acquisition" / "documents" / "alphabet.htm"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(
        """
        The summary below describes the principal terms of the notes. The notes
        are unsecured general obligations of Alphabet Inc.

        As of March 31, 2026, Google and certain other subsidiaries had
        approximately $2.2 billion in finance lease obligations and no long-term
        debt outstanding. Additionally, as of March 31, 2026, we have entered
        into leases primarily related to data centers that have not yet commenced
        with future lease payments of $75.6 billion, that are not yet recorded
        on our consolidated balance sheets, a portion of which will represent
        finance lease obligations.
        """
    )
    _write_csv(
        tmp_path / "data" / "edgar_acquisition" / "edgar_document_inventory.csv",
        [
            {
                "filing_url": "https://www.sec.gov/alphabet-424b5.htm",
                "local_path": str(source_path),
                "content_hash": "e" * 64,
                "primary_document": "alphabet.htm",
                "accession_number": "0001-26-000002",
            }
        ],
    )
    _write_csv(
        tmp_path / "data" / "reports" / "review_queue.csv",
        [
            {
                "review_id": "review-aggregate",
                "review_group_id": "group-aggregate",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Alphabet Inc.",
                "counterparty": "",
                "deal_id": "alphabet-lease-snapshot",
                "source_row_id": "alphabet-lease-snapshot",
                "notional_amount_usd": "75600000000",
                "exposure_usd": "0",
                "capacity_mw": "0",
                "risk_score": "0",
                "reason": (
                    "notional $75,600,000,000; notional context: aggregate_lease_obligation"
                ),
                "recommended_action": "Confirm whether row is duplicate or aggregate obligation",
                "source_uri": "https://www.sec.gov/alphabet-424b5.htm",
                "source_uris": json.dumps(["https://www.sec.gov/alphabet-424b5.htm"]),
                "content_hash": "e" * 64,
                "content_hashes": json.dumps(["e" * 64]),
                "human_review_status": "pending",
            }
        ],
    )

    batch = build_materiality_adjudication_packets([tmp_path / "data"], limit=1)

    assert batch.packets[0].evidence_snippets
    snippet = batch.packets[0].evidence_snippets[0].snippet
    assert "future lease payments of $75.6 billion" in snippet
    assert "not yet recorded on our consolidated balance sheets" in snippet


def test_materiality_adjudication_decisions_are_conservative(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-1",
                "rank": 1,
                "review_id": "review-1",
                "review_group_id": "group-1",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "CoreWeave",
                "counterparty": "Apollo Credit",
                "exposure_basis_usd": "30000000000",
                "reason": "source-backed committed financing candidate",
                "recommended_action": "Confirm maturity, recourse, and collateral",
                "source_uri": "https://www.sec.gov/coreweave-credit.htm",
                "source_uris": json.dumps(["https://www.sec.gov/coreweave-credit.htm"]),
                "content_hash": "a" * 64,
                "content_hashes": json.dumps(["a" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/coreweave-credit.htm",
                            "content_hash": "a" * 64,
                            "document_id": "coreweave-credit.htm",
                            "snippet": (
                                "CoreWeave entered into a committed senior secured "
                                "credit agreement with Apollo Credit. The facility "
                                "is secured by collateral and contains guarantor terms."
                            ),
                        }
                    ]
                ),
            },
            {
                "packet_id": "packet-2",
                "rank": 2,
                "review_id": "review-2",
                "review_group_id": "group-2",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Alphabet Inc.",
                "counterparty": "",
                "exposure_basis_usd": "75600000000",
                "reason": (
                    "notional context: aggregate_lease_obligation; source extraction "
                    "marked requires LLM adjudication"
                ),
                "recommended_action": "Confirm whether row is duplicate or aggregate obligation",
                "source_uri": "https://www.sec.gov/alphabet-prospectus.htm",
                "source_uris": json.dumps(["https://www.sec.gov/alphabet-prospectus.htm"]),
                "content_hash": "b" * 64,
                "content_hashes": json.dumps(["b" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/alphabet-prospectus.htm",
                            "content_hash": "b" * 64,
                            "document_id": "alphabet-prospectus.htm",
                            "snippet": (
                                "This preliminary prospectus supplement is not complete "
                                "and may be changed before the notes are offered."
                            ),
                        }
                    ]
                ),
            },
        ],
    )

    batch = build_materiality_adjudication_decisions(
        [tmp_path],
        adjudicated_at="2026-06-01T00:00:00+00:00",
    )

    assert batch.summary.decisions == 2
    assert batch.summary.source_quote_backed_decisions == 2
    assert batch.summary.supported_as_material_blocker == 1
    assert batch.summary.needs_deeper_extraction == 1
    assert batch.summary.approved_for_metric_use == 1
    assert batch.decisions[0].decision == "supported_as_material_blocker"
    assert batch.decisions[0].metric_use_status == "approved_for_metric_use"
    assert batch.decisions[0].supported_amount_usd == 30_000_000_000
    assert batch.decisions[1].decision == "needs_deeper_extraction"
    assert batch.decisions[1].metric_use_status == "blocked_pending_extraction"
    assert "split aggregate disclosure" in batch.decisions[1].remaining_gap


def test_materiality_adjudication_approves_source_backed_aggregate_obligation_snapshot(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-aggregate",
                "rank": 1,
                "review_id": "review-aggregate",
                "review_group_id": "group-aggregate",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Alphabet Inc.",
                "counterparty": "",
                "exposure_basis_usd": "75600000000",
                "reason": (
                    "notional context: aggregate_lease_obligation; source extraction "
                    "marked requires LLM adjudication"
                ),
                "recommended_action": "Confirm whether row is duplicate or aggregate obligation",
                "source_uri": "https://www.sec.gov/alphabet-prospectus.htm",
                "source_uris": json.dumps(["https://www.sec.gov/alphabet-prospectus.htm"]),
                "content_hash": "b" * 64,
                "content_hashes": json.dumps(["b" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/alphabet-prospectus.htm",
                            "content_hash": "b" * 64,
                            "document_id": "alphabet-prospectus.htm",
                            "snippet": (
                                "We have entered into leases primarily related to data centers "
                                "that have not yet commenced with future lease payments "
                                "of $75.6 billion, that are not yet recorded on our "
                                "consolidated balance sheets."
                            ),
                        }
                    ]
                ),
            }
        ],
    )

    batch = build_materiality_adjudication_decisions(
        [tmp_path],
        adjudicated_at="2026-06-01T00:00:00+00:00",
    )

    assert batch.summary.approved_for_metric_use == 1
    assert batch.summary.final_metric_supported_amount_usd == 75_600_000_000
    assert batch.decisions[0].decision == "supported_as_material_blocker"
    assert batch.decisions[0].metric_use_status == "approved_for_metric_use"
    assert batch.decisions[0].supported_amount_usd == 75_600_000_000
    assert batch.decisions[0].duplicate_or_aggregate == "yes"
    assert batch.decisions[0].remaining_gap == ""
    assert "do not treat as an individual contract" in batch.decisions[0].required_next_extraction
    assert "not treated as an individual contract" in batch.decisions[0].rationale


def test_write_materiality_adjudication_decisions(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-1",
                "rank": 1,
                "review_id": "review-1",
                "review_group_id": "group-1",
                "priority": "high",
                "category": "compute",
                "subcategory": "gpu_depreciation_policy",
                "ecosystem_relevance": "compute_economics",
                "entity": "Hyperscaler",
                "exposure_basis_usd": "1000000000",
                "source_uri": "https://www.sec.gov/10k.htm",
                "content_hash": "d" * 64,
                "evidence_snippets": "[]",
            }
        ],
    )

    batch = build_materiality_adjudication_decisions([tmp_path])
    outputs = write_materiality_adjudication_decisions(batch, tmp_path / "reports")

    assert Path(outputs["decisions_csv"]).exists()
    assert Path(outputs["summary_json"]).exists()
    summary = json.loads(Path(outputs["summary_json"]).read_text())
    assert summary["decisions"] == 1
    assert summary["needs_source_retrieval"] == 1
