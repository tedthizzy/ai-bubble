from __future__ import annotations

import csv
import json
import zipfile
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
    assert batch.summary.packets_with_local_evidence_snippets == 2
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


def test_materiality_packets_extract_xlsx_artifact_snippets(tmp_path: Path) -> None:
    xlsx_path = (
        tmp_path / "data" / "source_acquisition" / "raw" / "queue_records" / "queue-sample.xlsx"
    )
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(xlsx_path, "w") as archive:
        archive.writestr(
            "xl/sharedStrings.xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                "<si><t>Project Name</t></si>"
                "<si><t>Customer</t></si>"
                "<si><t>Requested MW</t></si>"
                "<si><t>ZeroC Data Centers LLC</t></si>"
                "<si><t>3000</t></si>"
                "</sst>"
            ),
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                "<sheetData>"
                '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c>'
                '<c r="C1" t="s"><v>2</v></c></row>'
                '<row r="2"><c r="A2" t="s"><v>3</v></c><c r="B2" t="s"><v>3</v></c>'
                '<c r="C2" t="s"><v>4</v></c></row>'
                "</sheetData></worksheet>"
            ),
        )

    _write_csv(
        tmp_path / "data" / "source_acquisition" / "source_artifact_inventory.csv",
        [
            {
                "source_uri": "https://www.nyiso.com/documents/20142/1407078/NYISO-Interconnection-Queue.xlsx",
                "local_path": str(xlsx_path),
                "content_hash": "9" * 64,
                "document_id": "nyiso_queue_sample",
            }
        ],
    )
    _write_csv(
        tmp_path / "data" / "reports" / "review_queue.csv",
        [
            {
                "review_id": "review-xlsx",
                "review_group_id": "group-xlsx",
                "priority": "high",
                "category": "physical",
                "subcategory": "queue_project_match",
                "ecosystem_relevance": "physical_execution",
                "entity": "ZeroC",
                "counterparty": "ZeroC Data Centers LLC",
                "project_id": "project-xlsx",
                "project_name": "ZeroC Campus",
                "source_row_id": "queue-row-1",
                "capacity_mw": "3000",
                "reason": "pending queue-to-project match; match status: strong_match",
                "recommended_action": "Confirm queue linkage",
                "source_uri": "https://www.nyiso.com/documents/20142/1407078/NYISO-Interconnection-Queue.xlsx",
                "source_uris": json.dumps(
                    ["https://www.nyiso.com/documents/20142/1407078/NYISO-Interconnection-Queue.xlsx"]
                ),
                "content_hash": "9" * 64,
                "content_hashes": json.dumps(["9" * 64]),
                "human_review_status": "pending",
            }
        ],
    )

    batch = build_materiality_adjudication_packets([tmp_path / "data"], limit=1)

    assert batch.packets[0].evidence_snippets
    snippet = batch.packets[0].evidence_snippets[0].snippet
    assert "ZeroC Data Centers LLC" in snippet
    assert "3000" in snippet


def test_materiality_packets_skip_binary_artifact_snippets(tmp_path: Path) -> None:
    binary_path = tmp_path / "data" / "source_acquisition" / "raw" / "ownership_records" / "rr.bin"
    binary_path.parent.mkdir(parents=True, exist_ok=True)
    binary_path.write_bytes(b"\x00\x01\x02\x03\xff\xfe\xfd\xfc")
    _write_csv(
        tmp_path / "data" / "source_acquisition" / "source_artifact_inventory.csv",
        [
            {
                "source_uri": "https://leidata.gleif.org/api/v1/concatenated-files/rr/get/41258/zip",
                "local_path": str(binary_path),
                "content_hash": "7" * 64,
                "document_id": "rr_bin_sample",
            }
        ],
    )
    _write_csv(
        tmp_path / "data" / "reports" / "review_queue.csv",
        [
            {
                "review_id": "review-binary",
                "review_group_id": "group-binary",
                "priority": "high",
                "category": "contagion",
                "subcategory": "ownership_expanded",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Example Parent",
                "counterparty": "Example Child",
                "source_uri": "https://leidata.gleif.org/api/v1/concatenated-files/rr/get/41258/zip",
                "source_uris": json.dumps(
                    ["https://leidata.gleif.org/api/v1/concatenated-files/rr/get/41258/zip"]
                ),
                "content_hash": "7" * 64,
                "content_hashes": json.dumps(["7" * 64]),
                "reason": "ownership expanded contagion path",
                "human_review_status": "pending",
            }
        ],
    )

    batch = build_materiality_adjudication_packets([tmp_path / "data"], limit=1)

    assert len(batch.packets) == 1
    assert batch.packets[0].evidence_snippets == ()


def test_materiality_packets_use_row_context_fallback_for_physical_rows(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "data" / "reports" / "review_queue.csv",
        [
            {
                "review_id": "review-physical-fallback",
                "review_group_id": "group-physical-fallback",
                "priority": "high",
                "category": "physical",
                "subcategory": "permit_project_match",
                "ecosystem_relevance": "physical_execution",
                "entity": "Amazon",
                "counterparty": "AMAZON DATA SERVICES INC IAD-210/211",
                "project_id": "project-physical-fallback",
                "project_name": "AMAZON DATA SERVICES INC",
                "source_row_id": "permit-match:test",
                "reason": (
                    "pending permit-to-project match; match status: strong_match; "
                    "match confidence: 0.99; county_match|state_match"
                ),
                "recommended_action": "Confirm permit linkage to project record.",
                "source_uri": "https://echo.epa.gov/files/echodownloads/ICIS-AIR_downloads.zip",
                "source_uris": json.dumps(
                    ["https://echo.epa.gov/files/echodownloads/ICIS-AIR_downloads.zip"]
                ),
                "content_hash": "f" * 64,
                "content_hashes": json.dumps(["f" * 64]),
                "page_or_section": (
                    "data/source_acquisition/raw/permit_records/"
                    "epa-icis-air-facilities-programs.zip#record_index=266038"
                ),
                "human_review_status": "pending",
            }
        ],
    )

    batch = build_materiality_adjudication_packets([tmp_path / "data"], limit=1)

    assert len(batch.packets) == 1
    assert batch.packets[0].evidence_snippets
    snippet = batch.packets[0].evidence_snippets[0]
    assert snippet.document_id == "review_queue_row_context"
    assert "match status: strong_match" in snippet.snippet
    assert "ICIS-AIR_downloads.zip" in snippet.snippet


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


def test_materiality_packet_prioritizes_contract_clause_snippet_for_non_specific_candidate(
    tmp_path: Path,
) -> None:
    generic_path = tmp_path / "data" / "edgar_acquisition" / "documents" / "generic.htm"
    agreement_path = tmp_path / "data" / "edgar_acquisition" / "documents" / "agreement.htm"
    generic_path.parent.mkdir(parents=True, exist_ok=True)
    generic_path.write_text(
        """
        EX-99.1 Exhibit 99.1
        Forward-looking statements. About Example Issuer, Inc.
        This press release includes selected operating metrics and outlook commentary.
        """
    )
    agreement_path.write_text(
        """
        On March 2, 2026, Example Issuer, Inc. entered into a Credit Agreement
        with Bank of Example, N.A., as administrative agent.
        The revolving credit facility is senior secured and includes a maturity
        schedule through 2030.
        """
    )
    _write_csv(
        tmp_path / "data" / "edgar_acquisition" / "edgar_document_inventory.csv",
        [
            {
                "filing_url": "https://www.sec.gov/example-generic.htm",
                "local_path": str(generic_path),
                "content_hash": "1" * 64,
                "primary_document": "generic.htm",
                "accession_number": "0001-26-000010",
            },
            {
                "filing_url": "https://www.sec.gov/example-agreement.htm",
                "local_path": str(agreement_path),
                "content_hash": "2" * 64,
                "primary_document": "agreement.htm",
                "accession_number": "0001-26-000011",
            },
        ],
    )
    _write_csv(
        tmp_path / "data" / "reports" / "review_queue.csv",
        [
            {
                "review_id": "review-non-specific",
                "review_group_id": "group-non-specific",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Example Issuer, Inc.",
                "counterparty": "",
                "deal_id": "deal-non-specific",
                "source_row_id": "row-non-specific",
                "notional_amount_usd": "25000000000",
                "exposure_usd": "0",
                "capacity_mw": "0",
                "risk_score": "0.2",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: bond; "
                    "notional $25,000,000,000; notional context: candidate_notional; "
                    "commitment scope: candidate_requires_adjudication; "
                    "source extraction marked requires LLM adjudication"
                ),
                "recommended_action": "Acquire agreement-level clauses for commitment terms",
                "source_uri": "https://www.sec.gov/example-generic.htm",
                "source_uris": json.dumps(
                    [
                        "https://www.sec.gov/example-generic.htm",
                        "https://www.sec.gov/example-agreement.htm",
                    ]
                ),
                "content_hash": "1" * 64,
                "content_hashes": json.dumps(["1" * 64, "2" * 64]),
                "human_review_status": "pending",
            }
        ],
    )

    batch = build_materiality_adjudication_packets(
        [tmp_path / "data"],
        limit=1,
        snippets_per_packet=1,
    )

    assert batch.packets[0].evidence_snippets
    snippet = batch.packets[0].evidence_snippets[0].snippet.lower()
    assert "credit agreement" in snippet
    assert "administrative agent" in snippet
    assert "forward-looking statements" not in snippet


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


def test_materiality_adjudication_decisions_treat_row_context_as_non_quote_backed(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-row-context",
                "rank": 1,
                "review_id": "review-row-context",
                "review_group_id": "group-row-context",
                "priority": "high",
                "category": "physical",
                "subcategory": "permit_project_match",
                "ecosystem_relevance": "physical_execution",
                "entity": "Amazon",
                "counterparty": "AMAZON DATA SERVICES INC IAD-210/211",
                "exposure_basis_usd": "5000000000",
                "reason": "pending permit-to-project match; match status: strong_match",
                "recommended_action": "Confirm permit linkage to project record.",
                "source_uri": "https://echo.epa.gov/files/echodownloads/ICIS-AIR_downloads.zip",
                "source_uris": json.dumps(
                    ["https://echo.epa.gov/files/echodownloads/ICIS-AIR_downloads.zip"]
                ),
                "content_hash": "f" * 64,
                "content_hashes": json.dumps(["f" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://echo.epa.gov/files/echodownloads/ICIS-AIR_downloads.zip",
                            "content_hash": "f" * 64,
                            "document_id": "review_queue_row_context",
                            "snippet": (
                                "Category: physical Subcategory: permit_project_match "
                                "Reason: pending permit-to-project match; match status: strong_match "
                                "Source section: permit_records.zip#record_index=12"
                            ),
                        }
                    ]
                ),
            }
        ],
    )

    batch = build_materiality_adjudication_decisions(
        [tmp_path],
        adjudicated_at="2026-06-02T00:00:00+00:00",
    )

    assert batch.summary.decisions == 1
    assert batch.decisions[0].source_support == "row_context_backed"
    assert batch.decisions[0].decision != "needs_source_retrieval"
    assert batch.decisions[0].confidence <= 0.4


def test_materiality_adjudication_requires_quote_level_contagion_evidence(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-contagion",
                "rank": 1,
                "review_id": "review-contagion",
                "review_group_id": "group-contagion",
                "priority": "high",
                "category": "contagion",
                "subcategory": "contract_only",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Alphabet Inc. - 424B5",
                "counterparty": "noteholders",
                "exposure_basis_usd": "75600000000",
                "reason": (
                    "contract only contagion path; contract relationship: "
                    "SECURED_BY_COLLATERAL; notional $75,600,000,000"
                ),
                "recommended_action": "Validate legal-entity path and risk transfer mechanism",
                "source_uri": "https://www.sec.gov/alphabet-prospectus.htm",
                "source_uris": json.dumps(["https://www.sec.gov/alphabet-prospectus.htm"]),
                "content_hash": "c" * 64,
                "content_hashes": json.dumps(["c" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/alphabet-prospectus.htm",
                            "content_hash": "c" * 64,
                            "document_id": "alphabet-prospectus.htm",
                            "snippet": (
                                "As a result, investors may not be able to liquidate "
                                "their investment readily, and lenders may not readily "
                                "accept the notes as collateral for loans."
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

    assert batch.summary.supported_as_material_blocker == 0
    assert batch.summary.needs_deeper_extraction == 1
    assert batch.decisions[0].decision == "needs_deeper_extraction"
    assert "validate legal-entity path" in batch.decisions[0].remaining_gap


def test_materiality_adjudication_accepts_source_backed_ownership_expanded_contagion_path(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-contagion-ownership-expanded",
                "rank": 1,
                "review_id": "review-contagion-ownership-expanded",
                "review_group_id": "group-contagion-ownership-expanded",
                "priority": "high",
                "category": "contagion",
                "subcategory": "ownership_expanded",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Example Financing Bank",
                "counterparty": "Example Borrower",
                "exposure_basis_usd": "20000000000",
                "reason": (
                    "ownership expanded contagion path; contract relationship: TRANCHE_RISK_BEARER; "
                    "notional $20,000,000,000; ownership/control path depth 1; "
                    "risk flags: collateralized, non_recourse, maturity_wall"
                ),
                "recommended_action": "Validate legal-entity path and risk transfer mechanism",
                "source_uri": "https://www.sec.gov/example-bridge-loan.htm",
                "source_uris": json.dumps(
                    [
                        "https://www.sec.gov/example-bridge-loan.htm",
                        "https://leidata.gleif.org/api/v1/concatenated-files/rr/get/41258/zip",
                    ]
                ),
                "content_hash": "5" * 64,
                "content_hashes": json.dumps(["5" * 64, "6" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-bridge-loan.htm",
                            "content_hash": "5" * 64,
                            "document_id": "example-bridge-loan.htm",
                            "snippet": (
                                "Bridge Loan Credit Agreement dated March 2, 2026 among Example Borrower, "
                                "the guarantors party thereto, and the lenders from time to time party thereto."
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
    decision = batch.decisions[0]
    assert "validate legal-entity path" not in decision.remaining_gap


def test_materiality_adjudication_routes_contagion_boilerplate_to_term_evidence_gap(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-contagion-boilerplate",
                "rank": 1,
                "review_id": "review-contagion-boilerplate",
                "review_group_id": "group-contagion-boilerplate",
                "priority": "high",
                "category": "contagion",
                "subcategory": "contract_only",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Issuer",
                "counterparty": "Example Notes",
                "exposure_basis_usd": "25000000000",
                "reason": (
                    "contract only contagion path; contract relationship: SECURED_BY_COLLATERAL; "
                    "notional $25,000,000,000; risk flags: collateralized, spv_signal, tranched"
                ),
                "recommended_action": "Validate legal-entity path and risk transfer mechanism",
                "source_uri": "https://www.sec.gov/example-prospectus.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-prospectus.htm"]),
                "content_hash": "8" * 64,
                "content_hashes": json.dumps(["8" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-prospectus.htm",
                            "content_hash": "8" * 64,
                            "document_id": "example-prospectus.htm",
                            "snippet": (
                                "PROSPECTUS SUPPLEMENT. DTC facilitates post-trade settlement "
                                "through electronic book-entry transfers and pledges."
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
    decision = batch.decisions[0]
    assert (
        "acquire underlying agreement or debt schedule clause for term-level extraction"
        in decision.remaining_gap
    )
    assert "validate legal-entity path" not in decision.remaining_gap


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
                                "As of March 31, 2026, we have entered into leases "
                                "primarily related to data centers that have not yet "
                                "commenced with future lease payments of $75.6 billion, "
                                "that are not yet recorded on our consolidated balance sheets."
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
    assert batch.summary.approved_row_supported_amount_usd == 75_600_000_000
    assert batch.summary.final_metric_supported_amount_usd == 75_600_000_000
    assert batch.summary.final_metric_group_count == 1
    assert batch.decisions[0].decision == "supported_as_material_blocker"
    assert batch.decisions[0].metric_use_status == "approved_for_metric_use"
    assert batch.decisions[0].supported_amount_usd == 75_600_000_000
    assert (
        batch.decisions[0].metric_group_id
        == "aggregate-obligation-snapshot:alphabet-inc:high-notional-debt-like-candidate"
    )
    assert batch.decisions[0].metric_snapshot_date == "2026-03-31"
    assert batch.decisions[0].metric_aggregation_policy == "latest_snapshot_per_metric_group"
    assert batch.decisions[0].duplicate_or_aggregate == "yes"
    assert batch.decisions[0].remaining_gap == ""
    assert "do not treat as an individual contract" in batch.decisions[0].required_next_extraction
    assert "not treated as an individual contract" in batch.decisions[0].rationale


def test_materiality_adjudication_blocks_aggregate_lease_context_when_quote_is_debt_prospectus(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-lease-context-debt-prospectus",
                "rank": 1,
                "review_id": "review-lease-context-debt-prospectus",
                "review_group_id": "group-lease-context-debt-prospectus",
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
                "source_uri": "https://www.sec.gov/alphabet-debt-prospectus.htm",
                "source_uris": json.dumps(
                    ["https://www.sec.gov/alphabet-debt-prospectus.htm"]
                ),
                "content_hash": "c" * 64,
                "content_hashes": json.dumps(["c" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/alphabet-debt-prospectus.htm",
                            "content_hash": "c" * 64,
                            "document_id": "alphabet-debt-prospectus.htm",
                            "snippet": (
                                "DESCRIPTION OF DEBT SECURITIES We may offer secured "
                                "or unsecured debt securities in one or more series. "
                                "The following is a summary of certain general terms "
                                "of the debt securities and the indenture, dated as "
                                "of February 12, 2016, with the trustee."
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

    decision = batch.decisions[0]
    assert batch.summary.approved_for_metric_use == 0
    assert decision.metric_use_status == "blocked_pending_extraction"
    assert "confirm lease obligation source" in decision.remaining_gap
    assert "split aggregate disclosure" in decision.remaining_gap
    assert decision.supported_amount_usd == 0


def test_materiality_adjudication_dedupes_aggregate_snapshots_to_latest_metric(
    tmp_path: Path,
) -> None:
    rows = []
    for rank, amount, snapshot_date, uri in [
        (1, "75600000000", "March 31, 2026", "https://www.sec.gov/alphabet-2026q1.htm"),
        (2, "42600000000", "September 30, 2025", "https://www.sec.gov/alphabet-2025q3.htm"),
    ]:
        rows.append(
            {
                "packet_id": f"packet-aggregate-{rank}",
                "rank": rank,
                "review_id": f"review-aggregate-{rank}",
                "review_group_id": f"group-aggregate-{rank}",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Alphabet Inc.",
                "counterparty": "",
                "exposure_basis_usd": amount,
                "reason": "notional context: aggregate_lease_obligation",
                "recommended_action": "Confirm whether row is duplicate or aggregate obligation",
                "source_uri": uri,
                "source_uris": json.dumps([uri]),
                "content_hash": f"{rank}" * 64,
                "content_hashes": json.dumps([f"{rank}" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": uri,
                            "content_hash": f"{rank}" * 64,
                            "document_id": f"alphabet-{rank}.htm",
                            "snippet": (
                                f"Additionally, as of {snapshot_date}, we have entered into "
                                "leases primarily related to data centers that have not yet "
                                f"commenced with future lease payments of ${float(amount) / 1_000_000_000:g} "
                                "billion, that are not yet recorded on our consolidated balance sheets."
                            ),
                        }
                    ]
                ),
            }
        )
    _write_csv(tmp_path / "reports" / "materiality_adjudication_packets.csv", rows)

    batch = build_materiality_adjudication_decisions(
        [tmp_path],
        adjudicated_at="2026-06-01T00:00:00+00:00",
    )

    assert batch.summary.approved_for_metric_use == 2
    assert batch.summary.approved_row_supported_amount_usd == 118_200_000_000
    assert batch.summary.final_metric_supported_amount_usd == 75_600_000_000
    assert batch.summary.final_metric_group_count == 1
    assert [decision.metric_snapshot_date for decision in batch.decisions] == [
        "2026-03-31",
        "2025-09-30",
    ]


def test_materiality_adjudication_dedupes_same_source_instrument_metric_rows(
    tmp_path: Path,
) -> None:
    rows = []
    for rank, entity in [(1, "Example Parent Corp."), (2, "Example Finance LLC")]:
        rows.append(
            {
                "packet_id": f"packet-affiliate-{rank}",
                "rank": rank,
                "review_id": f"review-affiliate-{rank}",
                "review_group_id": f"group-affiliate-{rank}",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": entity,
                "counterparty": "Example Bank, N.A.",
                "exposure_basis_usd": "3500000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: debt_facility; "
                    "notional $3,500,000,000; notional context: transaction_principal; "
                    "commitment scope: specific_transaction_commitment; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm duplicate group",
                "source_uri": "https://www.sec.gov/example-shared-facility.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-shared-facility.htm"]),
                "content_hash": "d" * 64,
                "content_hashes": json.dumps(["d" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-shared-facility.htm",
                            "content_hash": "d" * 64,
                            "document_id": "example-shared-facility.htm",
                            "snippet": (
                                "Example Parent Corp. entered into a credit agreement "
                                "with Example Bank, N.A., as administrative agent, "
                                "providing a $3.5 billion senior unsecured revolving "
                                "credit facility. The facility is guaranteed by "
                                "Example Finance LLC."
                            ),
                        }
                    ]
                ),
            }
        )
    _write_csv(tmp_path / "reports" / "materiality_adjudication_packets.csv", rows)

    batch = build_materiality_adjudication_decisions(
        [tmp_path],
        adjudicated_at="2026-06-01T00:00:00+00:00",
    )

    assert batch.summary.approved_for_metric_use == 2
    assert batch.summary.approved_row_supported_amount_usd == 7_000_000_000
    assert batch.summary.final_metric_supported_amount_usd == 3_500_000_000
    assert batch.summary.final_metric_group_count == 1
    assert {decision.metric_group_id for decision in batch.decisions} == {
        f"source-instrument:hashes:{'d' * 64}:amount:3500000000"
    }
    assert {
        decision.metric_aggregation_policy for decision in batch.decisions
    } == {"max_amount_per_source_instrument"}


def test_materiality_adjudication_approves_aggregate_commitment_snapshot(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-commitments",
                "rank": 1,
                "review_id": "review-commitments",
                "review_group_id": "group-commitments",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "compute_economics",
                "entity": "Example Compute Corp.",
                "counterparty": "",
                "exposure_basis_usd": "119000000000",
                "reason": "notional context: aggregate_commitment_snapshot",
                "recommended_action": "Separate aggregate disclosure from specific contracts",
                "source_uri": "https://www.sec.gov/example-commitments.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-commitments.htm"]),
                "content_hash": "d" * 64,
                "content_hashes": json.dumps(["d" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-commitments.htm",
                            "content_hash": "d" * 64,
                            "document_id": "example-commitments.htm",
                            "snippet": (
                                "As of April 26, 2026, purchase commitments were "
                                "$119 billion under long-term infrastructure and "
                                "supply commitments."
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
    assert batch.decisions[0].metric_use_status == "approved_for_metric_use"
    assert batch.decisions[0].remaining_gap == ""


def test_materiality_adjudication_approves_committed_lease_contract_value_snapshot(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-hpc-lease-contract-value",
                "rank": 1,
                "review_id": "review-hpc-lease-contract-value",
                "review_group_id": "group-hpc-lease-contract-value",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Example Compute Lessor Inc.",
                "counterparty": "",
                "exposure_basis_usd": "12800000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: lease; "
                    "notional $12,800,000,000; notional context: candidate_notional; "
                    "source extraction marked requires LLM adjudication"
                ),
                "recommended_action": "Separate aggregate disclosure from specific contracts",
                "source_uri": "https://www.sec.gov/example-hpc-lease.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-hpc-lease.htm"]),
                "content_hash": "f" * 64,
                "content_hashes": json.dumps(["f" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-hpc-lease.htm",
                            "content_hash": "f" * 64,
                            "document_id": "example-hpc-lease.htm",
                            "snippet": (
                                "Execution of HPC lease agreements - Entered into "
                                "long-term HPC lease agreements representing aggregate "
                                "contractual value in excess of $12.8 billion, including "
                                "a lease with Fluidstack supported by Google's credit."
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

    decision = batch.decisions[0]
    assert decision.metric_use_status == "approved_for_metric_use"
    assert decision.remaining_gap == ""
    assert decision.metric_aggregation_policy == "latest_snapshot_per_metric_group"
    assert decision.duplicate_or_aggregate == "yes"
    assert "aggregate obligation snapshot" in decision.risk_bearer


def test_materiality_adjudication_keeps_portfolio_upb_plus_issued_notes_blocked(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-portfolio-upb-issued-notes",
                "rank": 1,
                "review_id": "review-portfolio-upb-issued-notes",
                "review_group_id": "group-portfolio-upb-issued-notes",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "not_tagged",
                "entity": "Example Mortgage Servicer Inc.",
                "counterparty": "noteholders",
                "exposure_basis_usd": "734000000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: bond; "
                    "notional $734,000,000,000; notional context: candidate_notional; "
                    "commitment scope: candidate_requires_adjudication"
                ),
                "recommended_action": "Split portfolio UPB from issued debt",
                "source_uri": "https://www.sec.gov/example-upb-issued-notes.htm",
                "source_uris": json.dumps(
                    ["https://www.sec.gov/example-upb-issued-notes.htm"]
                ),
                "content_hash": "1" * 64,
                "content_hashes": json.dumps(["1" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": (
                                "https://www.sec.gov/example-upb-issued-notes.htm"
                            ),
                            "content_hash": "1" * 64,
                            "document_id": "example-upb-issued-notes.htm",
                            "snippet": (
                                "Servicing portfolio UPB of $733.6 billion at year end. "
                                "Issued $2.35 billion of unsecured senior notes with "
                                "maturities ranging from 2032 to 2034."
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

    decision = batch.decisions[0]
    assert decision.metric_use_status == "blocked_pending_extraction"
    assert "split aggregate disclosure" in decision.remaining_gap


def test_materiality_adjudication_keeps_shelf_capacity_blocked(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-shelf",
                "rank": 1,
                "review_id": "review-shelf",
                "review_group_id": "group-shelf",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Example Issuer Inc.",
                "counterparty": "",
                "exposure_basis_usd": "25000000000",
                "reason": "notional context: aggregate_shelf_capacity",
                "recommended_action": "Distinguish shelf capacity from committed financing",
                "source_uri": "https://www.sec.gov/example-shelf.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-shelf.htm"]),
                "content_hash": "e" * 64,
                "content_hashes": json.dumps(["e" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-shelf.htm",
                            "content_hash": "e" * 64,
                            "document_id": "example-shelf.htm",
                            "snippet": (
                                "This prospectus supplement forms part of the registration "
                                "statement. From time to time, we may offer up to "
                                "$25 billion of debt securities."
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

    decision = batch.decisions[0]
    assert batch.summary.approved_for_metric_use == 0
    assert decision.metric_use_status == "blocked_pending_extraction"
    assert "split aggregate disclosure" in decision.remaining_gap
    assert "extract named counterparty and role" not in decision.remaining_gap
    assert "determine recourse and guarantee scope" not in decision.remaining_gap
    assert "determine collateral scope" not in decision.remaining_gap


def test_materiality_adjudication_does_not_flag_split_for_specific_transaction_principal(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-transaction-principal",
                "rank": 1,
                "review_id": "review-transaction-principal",
                "review_group_id": "group-transaction-principal",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Example Borrower, Inc.",
                "counterparty": "Example Lender Bank",
                "exposure_basis_usd": "25000000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: debt_facility; "
                    "notional $25,000,000,000; notional context: transaction_principal; "
                    "commitment scope: specific_transaction_commitment"
                ),
                "recommended_action": "Confirm maturity, collateral, and recourse",
                "source_uri": "https://www.sec.gov/example-transaction.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-transaction.htm"]),
                "content_hash": "f" * 64,
                "content_hashes": json.dumps(["f" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-transaction.htm",
                            "content_hash": "f" * 64,
                            "document_id": "example-transaction.htm",
                            "snippet": (
                                "The aggregate principal amount of notes sold in the "
                                "offering was $25 billion."
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

    assert "split aggregate disclosure" not in batch.decisions[0].remaining_gap


def test_materiality_adjudication_routes_non_specific_candidate_to_term_acquisition_gap(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-candidate-non-specific",
                "rank": 1,
                "review_id": "review-candidate-non-specific",
                "review_group_id": "group-candidate-non-specific",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Example Issuer, Inc.",
                "counterparty": "",
                "exposure_basis_usd": "471000000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: bond; "
                    "notional $471,000,000,000; notional context: candidate_notional; "
                    "commitment scope: candidate_requires_adjudication; "
                    "source extraction marked requires LLM adjudication"
                ),
                "recommended_action": "Confirm whether this is a specific committed obligation",
                "source_uri": "https://www.sec.gov/example-candidate.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-candidate.htm"]),
                "content_hash": "a" * 64,
                "content_hashes": json.dumps(["a" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-candidate.htm",
                            "content_hash": "a" * 64,
                            "document_id": "example-candidate.htm",
                            "snippet": (
                                "This presentation contains forward-looking statements and "
                                "selected operating metrics."
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

    decision = batch.decisions[0]
    assert "split aggregate disclosure" in decision.remaining_gap
    assert (
        "acquire underlying agreement or debt schedule clause for term-level extraction"
        in decision.remaining_gap
    )
    assert "extract named counterparty and role" not in decision.remaining_gap
    assert "determine recourse and guarantee scope" not in decision.remaining_gap
    assert "determine collateral scope" not in decision.remaining_gap


def test_materiality_adjudication_routes_aggregate_debt_snapshot_to_split_gap(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-aggregate-debt-snapshot",
                "rank": 1,
                "review_id": "review-aggregate-debt-snapshot",
                "review_group_id": "group-aggregate-debt-snapshot",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "not_tagged",
                "entity": "Example Debt Issuer, Inc.",
                "counterparty": "",
                "exposure_basis_usd": "103994000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: debt_facility; "
                    "notional $103,994,000,000; notional context: transaction_principal; "
                    "source extraction marked requires LLM adjudication"
                ),
                "recommended_action": "Confirm debt terms",
                "source_uri": "https://www.sec.gov/example-debt-snapshot.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-debt-snapshot.htm"]),
                "content_hash": "9" * 64,
                "content_hashes": json.dumps(["9" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-debt-snapshot.htm",
                            "content_hash": "9" * 64,
                            "document_id": "example-debt-snapshot.htm",
                            "snippet": (
                                "As of March 31, 2025, the Corporation's total consolidated "
                                "long-term debt and debt due within one year was, in aggregate "
                                "principal amount, approximately $103,994 million outstanding."
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

    decision = batch.decisions[0]
    assert "split aggregate disclosure" in decision.remaining_gap
    assert "extract named counterparty and role" not in decision.remaining_gap
    assert "determine recourse and guarantee scope" not in decision.remaining_gap
    assert "determine collateral scope" not in decision.remaining_gap


def test_materiality_adjudication_uses_contract_reason_flags_for_scope_terms(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-contract-flags",
                "rank": 1,
                "review_id": "review-contract-flags",
                "review_group_id": "group-contract-flags",
                "priority": "high",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Example Borrower, Inc.",
                "counterparty": "Example Lender Bank",
                "exposure_basis_usd": "20000000000",
                "reason": (
                    "pending contract tranche review; tranche: Principal tranche; "
                    "notional $20,000,000,000; maturity 2027-09-02; "
                    "interest rate 0.02; collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Confirm contract edge and downside bearer",
                "source_uri": "https://www.sec.gov/example-contract.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-contract.htm"]),
                "content_hash": "1" * 64,
                "content_hashes": json.dumps(["1" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-contract.htm",
                            "content_hash": "1" * 64,
                            "document_id": "example-contract.htm",
                            "snippet": "Bridge Loan Credit Agreement dated as of March 2, 2026.",
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

    decision = batch.decisions[0]
    assert "determine recourse and guarantee scope" not in decision.remaining_gap
    assert "determine collateral scope" not in decision.remaining_gap
    assert decision.metric_use_status == "approved_for_metric_use"


def test_materiality_adjudication_treats_unsecured_notes_as_scope_resolved(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-unsecured-notes",
                "rank": 1,
                "review_id": "review-unsecured-notes",
                "review_group_id": "group-unsecured-notes",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "not_tagged",
                "entity": "Example Issuer Inc.",
                "counterparty": "noteholders",
                "exposure_basis_usd": "12000000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: bond; "
                    "notional $12,000,000,000; notional context: transaction_principal; "
                    "commitment scope: specific_transaction_commitment"
                ),
                "recommended_action": "Confirm maturity and pricing terms",
                "source_uri": "https://www.sec.gov/example-unsecured.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-unsecured.htm"]),
                "content_hash": "2" * 64,
                "content_hashes": json.dumps(["2" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-unsecured.htm",
                            "content_hash": "2" * 64,
                            "document_id": "example-unsecured.htm",
                            "snippet": (
                                "The notes are senior unsecured obligations of the issuer "
                                "and are issued under an indenture."
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

    decision = batch.decisions[0]
    assert "determine recourse and guarantee scope" not in decision.remaining_gap
    assert "determine collateral scope" not in decision.remaining_gap
    assert decision.metric_use_status == "approved_for_metric_use"


def test_materiality_adjudication_quote_selection_prefers_unsecured_scope(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-unsecured-facility-scope",
                "rank": 1,
                "review_id": "review-unsecured-facility-scope",
                "review_group_id": "group-unsecured-facility-scope",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Issuer Inc.",
                "counterparty": "lenders party thereto",
                "exposure_basis_usd": "4000000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: debt_facility; "
                    "notional $4,000,000,000; notional context: transaction_facility; "
                    "commitment scope: specific_transaction_commitment"
                ),
                "recommended_action": "Confirm collateral and recourse",
                "source_uri": "https://www.sec.gov/example-unsecured-facility.htm",
                "source_uris": json.dumps(
                    ["https://www.sec.gov/example-unsecured-facility.htm"]
                ),
                "content_hash": "8" * 64,
                "content_hashes": json.dumps(["8" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-unsecured-facility.htm",
                            "content_hash": "8" * 64,
                            "document_id": "example-unsecured-facility.htm",
                            "snippet": (
                                "The issuer had a $4.0 billion revolving credit facility "
                                "available for corporate liquidity. Such borrowings would "
                                "have been unsecured indebtedness ranking equally with other "
                                "unsecured obligations."
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

    decision = batch.decisions[0]
    assert "unsecured indebtedness" in decision.evidence_quote.lower(), decision
    assert "determine recourse and guarantee scope" not in decision.remaining_gap
    assert "determine collateral scope" not in decision.remaining_gap
    assert decision.metric_use_status == "approved_for_metric_use"


def test_materiality_adjudication_quote_selection_keeps_asset_backed_scope_window(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-gpu-backed-scope",
                "rank": 1,
                "review_id": "review-gpu-backed-scope",
                "review_group_id": "group-gpu-backed-scope",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Example Cloud Inc.",
                "counterparty": "institutional lenders",
                "exposure_basis_usd": "8500000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: debt_facility; "
                    "notional $8,500,000,000; notional context: transaction_facility; "
                    "commitment scope: specific_transaction_commitment"
                ),
                "recommended_action": "Confirm collateral and recourse",
                "source_uri": "https://www.sec.gov/example-gpu-backed.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-gpu-backed.htm"]),
                "content_hash": "9" * 64,
                "content_hashes": json.dumps(["9" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-gpu-backed.htm",
                            "content_hash": "9" * 64,
                            "document_id": "example-gpu-backed.htm",
                            "snippet": (
                                "The company closed an $8.5 billion GPU-backed financing "
                                "facility for AI infrastructure assets. The facility is "
                                "non-recourse to the parent borrower and funds contracted "
                                "cloud services."
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

    decision = batch.decisions[0]
    assert "gpu-backed financing" in decision.evidence_quote.lower(), decision
    assert "non-recourse" in decision.evidence_quote.lower(), decision
    assert "determine recourse and guarantee scope" not in decision.remaining_gap
    assert "determine collateral scope" not in decision.remaining_gap
    assert decision.metric_use_status == "approved_for_metric_use"


def test_materiality_adjudication_treats_security_documents_as_collateral_scope(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-security-documents",
                "rank": 1,
                "review_id": "review-security-documents",
                "review_group_id": "group-security-documents",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Example Cloud Borrower, Inc.",
                "counterparty": "lenders party thereto",
                "exposure_basis_usd": "4459200000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: debt_facility; "
                    "notional $4,459,200,000; notional context: transaction_principal; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm collateral package",
                "source_uri": "https://www.sec.gov/example-security-documents.htm",
                "source_uris": json.dumps(
                    ["https://www.sec.gov/example-security-documents.htm"]
                ),
                "content_hash": "d" * 64,
                "content_hashes": json.dumps(["d" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-security-documents.htm",
                            "content_hash": "d" * 64,
                            "document_id": "example-security-documents.htm",
                            "snippet": (
                                "\"Loan Documents\" means this Agreement, the Security "
                                "Documents, promissory notes, fee letters, and each "
                                "other document entered into in connection with the "
                                "Facilities."
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

    decision = batch.decisions[0]
    assert "security documents" in decision.evidence_quote.lower(), decision
    assert "determine collateral scope" not in decision.remaining_gap
    assert decision.metric_use_status == "approved_for_metric_use"


def test_materiality_adjudication_scope_quote_trim_keeps_late_secured_terms(
    tmp_path: Path,
) -> None:
    long_intro = (
        "The company described background liquidity and related offering details. "
        * 14
    )
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-late-secured-term",
                "rank": 1,
                "review_id": "review-late-secured-term",
                "review_group_id": "group-late-secured-term",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Borrower, Inc.",
                "counterparty": "Example Lender Bank",
                "exposure_basis_usd": "2350000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: debt_facility; "
                    "notional $2,350,000,000; notional context: transaction_facility; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm collateral package",
                "source_uri": "https://www.sec.gov/example-late-secured-term.htm",
                "source_uris": json.dumps(
                    ["https://www.sec.gov/example-late-secured-term.htm"]
                ),
                "content_hash": "e" * 64,
                "content_hashes": json.dumps(["e" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-late-secured-term.htm",
                            "content_hash": "e" * 64,
                            "document_id": "example-late-secured-term.htm",
                            "snippet": (
                                long_intro
                                + "The refinancing replaced prior loans with a term "
                                "loan facility and revolving credit facility, together "
                                "defined as the Senior Secured Credit Facilities."
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

    decision = batch.decisions[0]
    assert "senior secured credit facilities" in decision.evidence_quote.lower(), decision
    assert "determine collateral scope" not in decision.remaining_gap
    assert decision.metric_use_status == "approved_for_metric_use"


def test_materiality_adjudication_treats_first_mortgage_bond_as_scope_resolved(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-first-mortgage-bond",
                "rank": 1,
                "review_id": "review-first-mortgage-bond",
                "review_group_id": "group-first-mortgage-bond",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Utility Co.",
                "counterparty": "noteholders",
                "exposure_basis_usd": "2204000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: bond; "
                    "notional $2,204,000,000; notional context: transaction_tranche_sum; "
                    "commitment scope: specific_transaction_commitment"
                ),
                "recommended_action": "Confirm mortgage-bond scope",
                "source_uri": "https://www.sec.gov/example-first-mortgage-bond.htm",
                "source_uris": json.dumps(
                    ["https://www.sec.gov/example-first-mortgage-bond.htm"]
                ),
                "content_hash": "f" * 64,
                "content_hashes": json.dumps(["f" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": (
                                "https://www.sec.gov/example-first-mortgage-bond.htm"
                            ),
                            "content_hash": "f" * 64,
                            "document_id": "example-first-mortgage-bond.htm",
                            "snippet": (
                                "UNION ELECTRIC COMPANY 4.80% FIRST MORTGAGE BOND "
                                "DUE 2036 CUSIP 906548CM2."
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

    decision = batch.decisions[0]
    assert "first mortgage bond" in decision.evidence_quote.lower(), decision
    assert "determine collateral scope" not in decision.remaining_gap
    assert "determine recourse and guarantee scope" not in decision.remaining_gap
    assert decision.metric_use_status == "approved_for_metric_use"


def test_materiality_adjudication_keeps_mortgage_bond_outstanding_total_blocked(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-mortgage-bond-outstanding-total",
                "rank": 1,
                "review_id": "review-mortgage-bond-outstanding-total",
                "review_group_id": "group-mortgage-bond-outstanding-total",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Utility Co.",
                "counterparty": "",
                "exposure_basis_usd": "10221000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: bond; "
                    "notional $10,221,000,000; notional context: transaction_principal; "
                    "source extraction marked requires LLM adjudication"
                ),
                "recommended_action": "Split outstanding series from current issuance",
                "source_uri": "https://www.sec.gov/example-mortgage-bond-summary.htm",
                "source_uris": json.dumps(
                    ["https://www.sec.gov/example-mortgage-bond-summary.htm"]
                ),
                "content_hash": "1" * 64,
                "content_hashes": json.dumps(["1" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": (
                                "https://www.sec.gov/example-mortgage-bond-summary.htm"
                            ),
                            "content_hash": "1" * 64,
                            "document_id": "example-mortgage-bond-summary.htm",
                            "snippet": (
                                "At June 30, 2023, 40 series of first mortgage bonds "
                                "in an aggregate principal amount of approximately "
                                "$10.221 billion were outstanding under the indenture."
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

    decision = batch.decisions[0]
    assert (
        "split aggregate disclosure from specific committed obligation"
        in decision.remaining_gap
    )
    assert "determine collateral scope" not in decision.remaining_gap
    assert "determine recourse and guarantee scope" not in decision.remaining_gap
    assert decision.metric_use_status == "blocked_pending_extraction"


def test_materiality_adjudication_keeps_generic_mortgage_bond_shelf_blocked(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-generic-mortgage-bond-shelf",
                "rank": 1,
                "review_id": "review-generic-mortgage-bond-shelf",
                "review_group_id": "group-generic-mortgage-bond-shelf",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Utility Co.",
                "counterparty": "noteholders",
                "exposure_basis_usd": "2195000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: bond; "
                    "notional $2,195,000,000; notional context: transaction_principal; "
                    "source extraction marked requires LLM adjudication"
                ),
                "recommended_action": "Confirm specific mortgage-bond issuance",
                "source_uri": "https://www.sec.gov/example-mortgage-bond-shelf.htm",
                "source_uris": json.dumps(
                    ["https://www.sec.gov/example-mortgage-bond-shelf.htm"]
                ),
                "content_hash": "2" * 64,
                "content_hashes": json.dumps(["2" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": (
                                "https://www.sec.gov/example-mortgage-bond-shelf.htm"
                            ),
                            "content_hash": "2" * 64,
                            "document_id": "example-mortgage-bond-shelf.htm",
                            "snippet": (
                                "FIRST MORTGAGE BONDS Example Utility Co. may "
                                "periodically offer our first mortgage bonds in one "
                                "or more series."
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

    decision = batch.decisions[0]
    assert decision.remaining_gap
    assert decision.metric_use_status == "blocked_pending_extraction"


def test_materiality_adjudication_keeps_mortgage_bond_repayment_proceeds_blocked(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-mortgage-bond-repayment-proceeds",
                "rank": 1,
                "review_id": "review-mortgage-bond-repayment-proceeds",
                "review_group_id": "group-mortgage-bond-repayment-proceeds",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Utility Co.",
                "counterparty": "noteholders",
                "exposure_basis_usd": "6985000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: bond; "
                    "notional $6,985,000,000; notional context: transaction_principal; "
                    "commitment scope: specific_transaction_commitment"
                ),
                "recommended_action": "Split proceeds use from current issuance",
                "source_uri": "https://www.sec.gov/example-mortgage-bond-proceeds.htm",
                "source_uris": json.dumps(
                    ["https://www.sec.gov/example-mortgage-bond-proceeds.htm"]
                ),
                "content_hash": "3" * 64,
                "content_hashes": json.dumps(["3" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": (
                                "https://www.sec.gov/example-mortgage-bond-proceeds.htm"
                            ),
                            "content_hash": "3" * 64,
                            "document_id": "example-mortgage-bond-proceeds.htm",
                            "snippet": (
                                "We intend to use the net proceeds from the issuance "
                                "and sale of the bonds to repay or redeem the "
                                "outstanding $1 billion aggregate principal amount "
                                "of our Collateral Trust Mortgage Bonds, 0.95% "
                                "Series due 2024."
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

    decision = batch.decisions[0]
    assert (
        "split aggregate disclosure from specific committed obligation"
        in decision.remaining_gap
    )
    assert decision.metric_use_status == "blocked_pending_extraction"


def test_materiality_adjudication_treats_note_offering_counterparty_as_non_bilateral(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-note-offering",
                "rank": 1,
                "review_id": "review-note-offering",
                "review_group_id": "group-note-offering",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Issuer Inc.",
                "counterparty": "",
                "exposure_basis_usd": "30000000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: bond; "
                    "notional $30,000,000,000; notional context: transaction_principal; "
                    "commitment scope: specific_transaction_commitment"
                ),
                "recommended_action": "Confirm maturity and pricing terms",
                "source_uri": "https://www.sec.gov/example-note-offering.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-note-offering.htm"]),
                "content_hash": "4" * 64,
                "content_hashes": json.dumps(["4" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-note-offering.htm",
                            "content_hash": "4" * 64,
                            "document_id": "example-note-offering.htm",
                            "snippet": (
                                "PROSPECTUS SUPPLEMENT Example Issuer Inc. $30,000,000,000 "
                                "aggregate principal amount of senior notes due 2035. "
                                "The notes are issued under an indenture."
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

    decision = batch.decisions[0]
    assert "extract named counterparty and role" not in decision.remaining_gap
    assert "determine collateral scope" not in decision.remaining_gap
    assert "determine recourse and guarantee scope" not in decision.remaining_gap
    assert decision.metric_use_status == "approved_for_metric_use"


def test_materiality_adjudication_treats_mistagged_note_offering_as_non_bilateral(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-mistagged-note-offering",
                "rank": 1,
                "review_id": "review-mistagged-note-offering",
                "review_group_id": "group-mistagged-note-offering",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Issuer Inc.",
                "counterparty": "",
                "exposure_basis_usd": "18000000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: debt_facility; "
                    "notional $18,000,000,000; notional context: transaction_principal; "
                    "commitment scope: specific_transaction_commitment"
                ),
                "recommended_action": "Confirm maturity and pricing terms",
                "source_uri": "https://www.sec.gov/example-mistagged-note-offering.htm",
                "source_uris": json.dumps(
                    ["https://www.sec.gov/example-mistagged-note-offering.htm"]
                ),
                "content_hash": "5" * 64,
                "content_hashes": json.dumps(["5" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-mistagged-note-offering.htm",
                            "content_hash": "5" * 64,
                            "document_id": "example-mistagged-note-offering.htm",
                            "snippet": (
                                "PROSPECTUS SUPPLEMENT Example Issuer Inc. issued "
                                "$18,000,000,000 aggregate principal amount of senior "
                                "unsecured notes due 2036 under an indenture."
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

    decision = batch.decisions[0]
    assert "extract named counterparty and role" not in decision.remaining_gap
    assert "determine collateral scope" not in decision.remaining_gap
    assert "determine recourse and guarantee scope" not in decision.remaining_gap
    assert decision.metric_use_status == "approved_for_metric_use"


def test_materiality_adjudication_treats_note_offering_with_credit_facility_reference_as_non_bilateral(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-note-credit-facility-reference",
                "rank": 1,
                "review_id": "review-note-credit-facility-reference",
                "review_group_id": "group-note-credit-facility-reference",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Issuer Inc.",
                "counterparty": "",
                "exposure_basis_usd": "1730000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: debt_facility; "
                    "notional $1,730,000,000; notional context: transaction_principal; "
                    "commitment scope: specific_transaction_commitment; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm maturity and pricing terms",
                "source_uri": "https://www.sec.gov/example-note-credit-reference.htm",
                "source_uris": json.dumps(
                    ["https://www.sec.gov/example-note-credit-reference.htm"]
                ),
                "content_hash": "f" * 64,
                "content_hashes": json.dumps(["f" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-note-credit-reference.htm",
                            "content_hash": "f" * 64,
                            "document_id": "example-note-credit-reference.htm",
                            "snippet": (
                                "Muvico, LLC commenced an offering of $1,730 million "
                                "aggregate principal amount of first lien notes due 2031. "
                                "The Notes will be guaranteed by subsidiaries that guarantee "
                                "obligations under the Company's new $750 million term loan "
                                "facility."
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

    decision = batch.decisions[0]
    assert "extract named counterparty and role" not in decision.remaining_gap
    assert decision.metric_use_status == "approved_for_metric_use"


def test_materiality_adjudication_keeps_term_facility_with_note_reference_bilateral(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-term-facility-note-reference",
                "rank": 1,
                "review_id": "review-term-facility-note-reference",
                "review_group_id": "group-term-facility-note-reference",
                "priority": "high",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Issuer Inc.",
                "counterparty": "",
                "exposure_basis_usd": "750000000",
                "reason": (
                    "pending contract tranche review; tranche: Term loan facility; "
                    "notional $750,000,000; notional context: transaction_facility; "
                    "collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Extract lender parties",
                "source_uri": "https://www.sec.gov/example-term-note-reference.htm",
                "source_uris": json.dumps(
                    ["https://www.sec.gov/example-term-note-reference.htm"]
                ),
                "content_hash": "a" * 64,
                "content_hashes": json.dumps(["a" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-term-note-reference.htm",
                            "content_hash": "a" * 64,
                            "document_id": "example-term-note-reference.htm",
                            "snippet": (
                                "Muvico, LLC commenced an offering of $1,730 million "
                                "aggregate principal amount of first lien notes due 2031. "
                                "The Notes will be guaranteed by subsidiaries that guarantee "
                                "obligations under the Company's new $750 million term loan "
                                "facility."
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

    decision = batch.decisions[0]
    assert "extract named counterparty and role" in decision.remaining_gap
    assert decision.metric_use_status == "blocked_pending_extraction"


def test_materiality_adjudication_treats_unsecured_term_facility_as_scope_resolved(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-unsecured-term-facility",
                "rank": 1,
                "review_id": "review-unsecured-term-facility",
                "review_group_id": "group-unsecured-term-facility",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Example Borrower, Inc.",
                "counterparty": "Example Lender Bank",
                "exposure_basis_usd": "11200000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: debt_facility; "
                    "notional $11,200,000,000; notional context: transaction_facility; "
                    "commitment scope: specific_transaction_commitment"
                ),
                "recommended_action": "Confirm maturity and pricing terms",
                "source_uri": "https://www.sec.gov/example-unsecured-term-facility.htm",
                "source_uris": json.dumps(
                    ["https://www.sec.gov/example-unsecured-term-facility.htm"]
                ),
                "content_hash": "8" * 64,
                "content_hashes": json.dumps(["8" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": (
                                "https://www.sec.gov/example-unsecured-term-facility.htm"
                            ),
                            "content_hash": "8" * 64,
                            "document_id": "example-unsecured-term-facility.htm",
                            "snippet": (
                                "The company entered into an $11.2 billion unsecured "
                                "Term A-2 facility maturing in 2028."
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

    decision = batch.decisions[0]
    assert "determine collateral scope" not in decision.remaining_gap
    assert "determine recourse and guarantee scope" not in decision.remaining_gap
    assert decision.metric_use_status == "approved_for_metric_use"


def test_materiality_adjudication_treats_bank_counterparty_credit_facility_as_recourse_resolved(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-bank-counterparty-recourse",
                "rank": 1,
                "review_id": "review-bank-counterparty-recourse",
                "review_group_id": "group-bank-counterparty-recourse",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Example Borrower, Inc.",
                "counterparty": "Bank of America, N.A.",
                "exposure_basis_usd": "9500000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: debt_facility; "
                    "notional $9,500,000,000; notional context: transaction_facility; "
                    "commitment scope: specific_transaction_commitment"
                ),
                "recommended_action": "Confirm maturity and pricing terms",
                "source_uri": "https://www.sec.gov/example-bank-counterparty.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-bank-counterparty.htm"]),
                "content_hash": "9" * 64,
                "content_hashes": json.dumps(["9" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-bank-counterparty.htm",
                            "content_hash": "9" * 64,
                            "document_id": "example-bank-counterparty.htm",
                            "snippet": (
                                "The company entered into a secured revolving credit "
                                "facility with Bank of America, N.A."
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

    decision = batch.decisions[0]
    assert "determine recourse and guarantee scope" not in decision.remaining_gap
    assert "determine collateral scope" not in decision.remaining_gap
    assert decision.metric_use_status == "approved_for_metric_use"


def test_materiality_adjudication_supports_weak_link_physical_execution_without_gap(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-weak-link-physical",
                "rank": 1,
                "review_id": "review-weak-link-physical",
                "review_group_id": "group-weak-link-physical",
                "priority": "high",
                "category": "weak_link",
                "subcategory": "physical_execution",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Example Campus LLC",
                "counterparty": "",
                "exposure_basis_usd": "24000000000",
                "reason": (
                    "weak-link risk level: high; No source-backed grid interconnection "
                    "record attached.; Project is near target in-service date but not "
                    "visibly under construction."
                ),
                "recommended_action": (
                    "persist underlying source rows and move composite risk to "
                    "metric-specific decisions"
                ),
                "source_uri": "https://example.org/projects.csv",
                "source_uris": json.dumps(["https://example.org/projects.csv"]),
                "content_hash": "a" * 64,
                "content_hashes": json.dumps(["a" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://example.org/projects.csv",
                            "content_hash": "a" * 64,
                            "document_id": "projects.csv",
                            "snippet": (
                                "Planned AI campus with 2,400 MW capacity and no visible "
                                "construction progress."
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
    decision = batch.decisions[0]
    assert decision.decision == "supported_as_material_blocker"
    assert decision.remaining_gap == ""
    assert decision.metric_use_status == "triage_only"


def test_materiality_adjudication_adds_gap_for_not_offer_boilerplate(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-capital-not-offer",
                "rank": 1,
                "review_id": "review-capital-not-offer",
                "review_group_id": "group-capital-not-offer",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Issuer Inc.",
                "counterparty": "noteholders",
                "exposure_basis_usd": "1000000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: bond; "
                    "notional $1,000,000,000; notional context: transaction_principal"
                ),
                "recommended_action": "Confirm final offering terms",
                "source_uri": "https://www.sec.gov/example-not-offer.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-not-offer.htm"]),
                "content_hash": "b" * 64,
                "content_hashes": json.dumps(["b" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-not-offer.htm",
                            "content_hash": "b" * 64,
                            "document_id": "example-not-offer.htm",
                            "snippet": (
                                "This communication is not an offer to sell any securities."
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
    decision = batch.decisions[0]
    assert decision.decision == "needs_deeper_extraction"
    assert "confirm final prospectus or underlying agreement terms" in decision.remaining_gap


def test_materiality_adjudication_does_not_treat_registration_statement_reference_as_boilerplate(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-registration-statement-reference",
                "rank": 1,
                "review_id": "review-registration-statement-reference",
                "review_group_id": "group-registration-statement-reference",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Issuer Inc.",
                "counterparty": "",
                "exposure_basis_usd": "1000000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: bond; "
                    "notional $1,000,000,000; notional context: transaction_principal; "
                    "commitment scope: specific_transaction_commitment"
                ),
                "recommended_action": "Confirm maturity and pricing terms",
                "source_uri": "https://www.sec.gov/example-424b2.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-424b2.htm"]),
                "content_hash": "c" * 64,
                "content_hashes": json.dumps(["c" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-424b2.htm",
                            "content_hash": "c" * 64,
                            "document_id": "example-424b2.htm",
                            "snippet": (
                                "Filed pursuant to Rule 424(b)(2) Registration Statement "
                                "No. 333-275201. Prospectus Supplement. "
                                "$1,000,000,000 aggregate principal amount of senior "
                                "unsecured notes due 2035 issued under an indenture."
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
    decision = batch.decisions[0]
    assert "confirm final prospectus or underlying agreement terms" not in decision.remaining_gap
    assert decision.metric_use_status == "approved_for_metric_use"


def test_materiality_adjudication_routes_generic_contract_boilerplate_to_term_evidence_gap(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-generic-contract-boilerplate",
                "rank": 1,
                "review_id": "review-generic-contract-boilerplate",
                "review_group_id": "group-generic-contract-boilerplate",
                "priority": "critical",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "not_tagged",
                "entity": "Example Fund",
                "counterparty": "",
                "exposure_basis_usd": "100000000000",
                "reason": (
                    "pending contract tranche review; tranche: Primary tranche; "
                    "notional $100,000,000,000; collateral terms present"
                ),
                "recommended_action": "Confirm contract edge",
                "source_uri": "https://www.sec.gov/example-generic-contract.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-generic-contract.htm"]),
                "content_hash": "6" * 64,
                "content_hashes": json.dumps(["6" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-generic-contract.htm",
                            "content_hash": "6" * 64,
                            "document_id": "example-generic-contract.htm",
                            "snippet": (
                                "PROSPECTUS SUPPLEMENT Common Shares. "
                                "The securities may be offered by us or by selling "
                                "security holders. Those terms may include maturity and interest."
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

    decision = batch.decisions[0]
    assert (
        "acquire underlying agreement or debt schedule clause for term-level extraction"
        in decision.remaining_gap
    )
    assert "extract named counterparty and role" not in decision.remaining_gap
    assert "determine recourse and guarantee scope" not in decision.remaining_gap
    assert "determine collateral scope" not in decision.remaining_gap


def test_materiality_adjudication_routes_generic_capital_boilerplate_to_split_gap(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-generic-capital-boilerplate",
                "rank": 1,
                "review_id": "review-generic-capital-boilerplate",
                "review_group_id": "group-generic-capital-boilerplate",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "not_tagged",
                "entity": "Example Issuer",
                "counterparty": "",
                "exposure_basis_usd": "156000000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: debt_facility; "
                    "notional $156,000,000,000; notional context: transaction_principal; "
                    "source extraction marked requires LLM adjudication"
                ),
                "recommended_action": "Confirm debt terms",
                "source_uri": "https://www.sec.gov/example-generic-capital.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-generic-capital.htm"]),
                "content_hash": "7" * 64,
                "content_hashes": json.dumps(["7" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-generic-capital.htm",
                            "content_hash": "7" * 64,
                            "document_id": "example-generic-capital.htm",
                            "snippet": (
                                "The terms of the debt securities will include those set forth "
                                "in the indenture. The securities may be offered by us or by "
                                "selling security holders."
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

    decision = batch.decisions[0]
    assert "split aggregate disclosure" in decision.remaining_gap
    assert "extract named counterparty and role" not in decision.remaining_gap
    assert "determine recourse and guarantee scope" not in decision.remaining_gap
    assert "determine collateral scope" not in decision.remaining_gap


def test_materiality_adjudication_infers_counterparty_from_quote_role_clause(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-infer-counterparty",
                "rank": 1,
                "review_id": "review-infer-counterparty",
                "review_group_id": "group-infer-counterparty",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Example Borrower, Inc.",
                "counterparty": "",
                "exposure_basis_usd": "18000000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: debt_facility; "
                    "notional $18,000,000,000; notional context: transaction_principal; "
                    "commitment scope: specific_transaction_commitment; "
                    "collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Confirm maturity and pricing terms",
                "source_uri": "https://www.sec.gov/example-infer.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-infer.htm"]),
                "content_hash": "3" * 64,
                "content_hashes": json.dumps(["3" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-infer.htm",
                            "content_hash": "3" * 64,
                            "document_id": "example-infer.htm",
                            "snippet": (
                                "Among the Company, the lenders named therein, "
                                "Bank of America, N.A., as administrative agent."
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

    decision = batch.decisions[0]
    assert "extract named counterparty and role" not in decision.remaining_gap, decision
    assert decision.risk_bearer.startswith("inferred:"), decision
    assert decision.metric_use_status == "approved_for_metric_use", decision


def test_materiality_adjudication_infers_commitment_parties_from_financing_letter(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-commitment-parties",
                "rank": 1,
                "review_id": "review-commitment-parties",
                "review_group_id": "group-commitment-parties",
                "priority": "high",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Borrower, Inc.",
                "counterparty": "",
                "exposure_basis_usd": "15700000000",
                "reason": (
                    "pending contract tranche review; tranche: Bridge Facility; "
                    "notional $15,700,000,000; interest rate 0.045; "
                    "collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Confirm parties and financing roles",
                "source_uri": "https://www.sec.gov/example-commitment.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-commitment.htm"]),
                "content_hash": "4" * 64,
                "content_hashes": json.dumps(["4" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-commitment.htm",
                            "content_hash": "4" * 64,
                            "document_id": "example-commitment.htm",
                            "snippet": (
                                "Example Borrower entered into a commitment letter with "
                                "Citigroup Global Markets Inc., Goldman Sachs Bank USA "
                                "and Morgan Stanley Senior Funding, Inc. (the "
                                "Commitment Parties), pursuant to which the Commitment "
                                "Parties agreed to provide committed financing. The "
                                "Bridge Facility provides for a senior secured 364-day "
                                "bridge term loan credit facility in an aggregate "
                                "principal amount of up to $15.7 billion."
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

    decision = batch.decisions[0]
    assert "extract named counterparty and role" not in decision.remaining_gap, decision
    assert "Citigroup Global Markets Inc." in decision.risk_bearer, decision
    assert decision.metric_use_status == "approved_for_metric_use", decision


def test_materiality_adjudication_infers_named_borrower_from_defined_party_label(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-defined-borrower",
                "rank": 1,
                "review_id": "review-defined-borrower",
                "review_group_id": "group-defined-borrower",
                "priority": "high",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Example LNG Parent, Inc.",
                "counterparty": "",
                "exposure_basis_usd": "2250000000",
                "reason": (
                    "pending contract tranche review; tranche: Senior secured term loan B; "
                    "notional $2,250,000,000; collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Confirm parties and financing roles",
                "source_uri": "https://www.sec.gov/example-defined-borrower.htm",
                "source_uris": json.dumps(
                    ["https://www.sec.gov/example-defined-borrower.htm"]
                ),
                "content_hash": "6" * 64,
                "content_hashes": json.dumps(["6" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-defined-borrower.htm",
                            "content_hash": "6" * 64,
                            "document_id": "example-defined-borrower.htm",
                            "snippet": (
                                'Calcasieu Pass Funding, LLC ("Borrower"), an indirect '
                                "subsidiary of the Company, entered into a senior secured "
                                "term loan B facility. The obligations are guaranteed and "
                                "secured by collateral."
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

    decision = batch.decisions[0]
    assert "extract named counterparty and role" not in decision.remaining_gap, decision
    assert "Calcasieu Pass Funding, LLC" in decision.risk_bearer, decision
    assert decision.metric_use_status == "approved_for_metric_use", decision


def test_materiality_adjudication_infers_together_commitment_parties(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-together-commitment-parties",
                "rank": 1,
                "review_id": "review-together-commitment-parties",
                "review_group_id": "group-together-commitment-parties",
                "priority": "high",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Electronics Borrower, Inc.",
                "counterparty": "",
                "exposure_basis_usd": "3750000000",
                "reason": (
                    "pending contract tranche review; tranche: Bridge Facility; "
                    "notional $3,750,000,000; collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Confirm parties and financing roles",
                "source_uri": "https://www.sec.gov/example-together-commitment.htm",
                "source_uris": json.dumps(
                    ["https://www.sec.gov/example-together-commitment.htm"]
                ),
                "content_hash": "7" * 64,
                "content_hashes": json.dumps(["7" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-together-commitment.htm",
                            "content_hash": "7" * 64,
                            "document_id": "example-together-commitment.htm",
                            "snippet": (
                                "Example Borrower entered into a commitment letter "
                                "with Bank of America, N.A. and BofA Securities, Inc. "
                                '(together, the "Commitment Parties"), pursuant to '
                                "which the Commitment Parties committed to provide "
                                "a senior secured bridge facility."
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

    decision = batch.decisions[0]
    assert "extract named counterparty and role" not in decision.remaining_gap, decision
    assert "Bank of America, N.A." in decision.risk_bearer, decision
    assert decision.metric_use_status == "approved_for_metric_use", decision


def test_materiality_adjudication_does_not_infer_generic_bridge_lenders(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-generic-bridge-lenders",
                "rank": 1,
                "review_id": "review-generic-bridge-lenders",
                "review_group_id": "group-generic-bridge-lenders",
                "priority": "high",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Acquisition Borrower, Inc.",
                "counterparty": "",
                "exposure_basis_usd": "9400000000",
                "reason": (
                    "pending contract tranche review; tranche: Bridge Facility; "
                    "notional $9,400,000,000; collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Confirm parties and financing roles",
                "source_uri": "https://www.sec.gov/example-generic-bridge-lenders.htm",
                "source_uris": json.dumps(
                    ["https://www.sec.gov/example-generic-bridge-lenders.htm"]
                ),
                "content_hash": "8" * 64,
                "content_hashes": json.dumps(["8" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": (
                                "https://www.sec.gov/example-generic-bridge-lenders.htm"
                            ),
                            "content_hash": "8" * 64,
                            "document_id": "example-generic-bridge-lenders.htm",
                            "snippet": (
                                "The commitment letter provides for certain Bridge "
                                "Lenders to provide up to $9.4 billion of bridge "
                                "financing in connection with the acquisition."
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

    decision = batch.decisions[0]
    assert "extract named counterparty and role" in decision.remaining_gap, decision
    assert decision.metric_use_status == "blocked_pending_extraction", decision


def test_materiality_adjudication_quote_selection_prefers_named_arranger_evidence(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-arranger-quote-selection",
                "rank": 1,
                "review_id": "review-arranger-quote-selection",
                "review_group_id": "group-arranger-quote-selection",
                "priority": "high",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Example Cloud, Inc.",
                "counterparty": "",
                "exposure_basis_usd": "3100000000",
                "reason": (
                    "pending contract tranche review; tranche: Delayed draw term loan "
                    "facility; notional $3,100,000,000; interest rate 0.045; "
                    "collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Confirm parties and financing roles",
                "source_uri": "https://www.sec.gov/example-arranger.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-arranger.htm"]),
                "content_hash": "5" * 64,
                "content_hashes": json.dumps(["5" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-arranger.htm",
                            "content_hash": "5" * 64,
                            "document_id": "example-arranger.htm",
                            "snippet": (
                                "The DDTL 5.0 Facility has a maturity of approximately "
                                "5.5 years and is structured as a delayed draw term "
                                "loan facility supporting GPU infrastructure assets."
                            ),
                        },
                        {
                            "source_uri": "https://www.sec.gov/example-arranger.htm",
                            "content_hash": "5" * 64,
                            "document_id": "example-arranger.htm",
                            "snippet": (
                                "Morgan Stanley and Mitsubishi UFJ Financial Group "
                                "served as joint lead arrangers and bookrunners for "
                                "the transaction."
                            ),
                        },
                    ]
                ),
            }
        ],
    )

    batch = build_materiality_adjudication_decisions(
        [tmp_path],
        adjudicated_at="2026-06-01T00:00:00+00:00",
    )

    decision = batch.decisions[0]
    assert "extract named counterparty and role" not in decision.remaining_gap, decision
    assert "Morgan Stanley" in decision.risk_bearer, decision
    assert "joint lead arrangers" in decision.evidence_quote.lower(), decision
    assert decision.metric_use_status == "approved_for_metric_use", decision


def test_materiality_adjudication_infers_counterparty_from_financing_role_variants(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-na-serving-agent",
                "rank": 1,
                "review_id": "review-na-serving-agent",
                "review_group_id": "group-na-serving-agent",
                "priority": "high",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Borrower, Inc.",
                "counterparty": "",
                "exposure_basis_usd": "500000000",
                "reason": (
                    "pending contract tranche review; tranche: Revolving Credit Facility; "
                    "notional $500,000,000; collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Confirm parties and financing roles",
                "source_uri": "https://www.sec.gov/example-na-serving-agent.htm",
                "source_uris": json.dumps(
                    ["https://www.sec.gov/example-na-serving-agent.htm"]
                ),
                "content_hash": "a" * 64,
                "content_hashes": json.dumps(["a" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-na-serving-agent.htm",
                            "content_hash": "a" * 64,
                            "document_id": "example-na-serving-agent.htm",
                            "snippet": (
                                "The borrower entered into a senior secured revolving "
                                "credit facility with Citibank, N.A. serving as "
                                "administrative agent for a syndicate of lenders."
                            ),
                        }
                    ]
                ),
            },
            {
                "packet_id": "packet-underwriter-representatives",
                "rank": 2,
                "review_id": "review-underwriter-representatives",
                "review_group_id": "group-underwriter-representatives",
                "priority": "high",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Notes Issuer, Inc.",
                "counterparty": "",
                "exposure_basis_usd": "1500000000",
                "reason": (
                    "pending contract tranche review; tranche: Senior Notes; "
                    "notional $1,500,000,000; collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Confirm underwriter representatives",
                "source_uri": "https://www.sec.gov/example-underwriters.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-underwriters.htm"]),
                "content_hash": "b" * 64,
                "content_hashes": json.dumps(["b" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-underwriters.htm",
                            "content_hash": "b" * 64,
                            "document_id": "example-underwriters.htm",
                            "snippet": (
                                "The issuer entered into an Underwriting Agreement with "
                                "BofA Securities, Inc., Goldman Sachs & Co. LLC and "
                                "Morgan Stanley & Co. LLC, as representatives of the "
                                "several underwriters named therein."
                            ),
                        }
                    ]
                ),
            },
            {
                "packet_id": "packet-trustee-label",
                "rank": 3,
                "review_id": "review-trustee-label",
                "review_group_id": "group-trustee-label",
                "priority": "high",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Example Cloud Notes Issuer, Inc.",
                "counterparty": "",
                "exposure_basis_usd": "2500000000",
                "reason": (
                    "pending contract tranche review; tranche: Senior Notes; "
                    "notional $2,500,000,000; collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Confirm trustee and noteholder role",
                "source_uri": "https://www.sec.gov/example-trustee-label.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-trustee-label.htm"]),
                "content_hash": "c" * 64,
                "content_hashes": json.dumps(["c" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-trustee-label.htm",
                            "content_hash": "c" * 64,
                            "document_id": "example-trustee-label.htm",
                            "snippet": (
                                "The notes were issued under an indenture. Trustee "
                                "U.S. Bank Trust Company, National Association."
                            ),
                        }
                    ]
                ),
            },
            {
                "packet_id": "packet-borrower-agent",
                "rank": 4,
                "review_id": "review-borrower-agent",
                "review_group_id": "group-borrower-agent",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Power Borrower, Inc.",
                "counterparty": "",
                "exposure_basis_usd": "2900000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: debt_facility; "
                    "notional $2,900,000,000; notional context: transaction_principal; "
                    "collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Confirm administrative agent and lenders",
                "source_uri": "https://www.sec.gov/example-borrower-agent.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-borrower-agent.htm"]),
                "content_hash": "d" * 64,
                "content_hashes": json.dumps(["d" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-borrower-agent.htm",
                            "content_hash": "d" * 64,
                            "document_id": "example-borrower-agent.htm",
                            "snippet": (
                                "The Term Loan Credit Agreement was entered among "
                                "Example Energy Supply, as borrower, JPMorgan Chase "
                                "Bank, N.A., as administrative agent, and the lenders "
                                "party thereto."
                            ),
                        }
                    ]
                ),
            },
            {
                "packet_id": "packet-combined-agent-role",
                "rank": 5,
                "review_id": "review-combined-agent-role",
                "review_group_id": "group-combined-agent-role",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Utility HoldCo, Inc.",
                "counterparty": "",
                "exposure_basis_usd": "1200000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: debt_facility; "
                    "notional $1,200,000,000; notional context: transaction_principal; "
                    "collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Confirm combined agent role",
                "source_uri": "https://www.sec.gov/example-combined-agent.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-combined-agent.htm"]),
                "content_hash": "e" * 64,
                "content_hashes": json.dumps(["e" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-combined-agent.htm",
                            "content_hash": "e" * 64,
                            "document_id": "example-combined-agent.htm",
                            "snippet": (
                                "The amendment was entered among the borrower, the "
                                "guarantors party thereto, Credit Suisse AG, Cayman "
                                "Islands Branch, as administrative and collateral "
                                "agent, and the other lenders party thereto."
                            ),
                        }
                    ]
                ),
            },
            {
                "packet_id": "packet-no-with-underwriter-reps",
                "rank": 6,
                "review_id": "review-no-with-underwriter-reps",
                "review_group_id": "group-no-with-underwriter-reps",
                "priority": "high",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Notes Issuer II, Inc.",
                "counterparty": "",
                "exposure_basis_usd": "800000000",
                "reason": (
                    "pending contract tranche review; tranche: Senior Notes; "
                    "notional $800,000,000; collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Confirm underwriter representatives",
                "source_uri": "https://www.sec.gov/example-no-with-underwriters.htm",
                "source_uris": json.dumps(
                    ["https://www.sec.gov/example-no-with-underwriters.htm"]
                ),
                "content_hash": "f" * 64,
                "content_hashes": json.dumps(["f" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-no-with-underwriters.htm",
                            "content_hash": "f" * 64,
                            "document_id": "example-no-with-underwriters.htm",
                            "snippet": (
                                "PNC Capital Markets LLC, TD Securities (USA) LLC "
                                "and Wells Fargo Securities, LLC, as representatives "
                                "of the several underwriters listed in the agreement."
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

    decisions = {decision.packet_id: decision for decision in batch.decisions}
    assert "extract named counterparty and role" not in decisions[
        "packet-na-serving-agent"
    ].remaining_gap
    assert "Citibank, N.A" in decisions["packet-na-serving-agent"].risk_bearer
    assert "extract named counterparty and role" not in decisions[
        "packet-underwriter-representatives"
    ].remaining_gap
    assert "BofA Securities, Inc." in decisions[
        "packet-underwriter-representatives"
    ].risk_bearer
    assert "extract named counterparty and role" not in decisions[
        "packet-trustee-label"
    ].remaining_gap
    assert "U.S. Bank Trust Company" in decisions["packet-trustee-label"].risk_bearer
    assert "extract named counterparty and role" not in decisions[
        "packet-borrower-agent"
    ].remaining_gap
    assert "JPMorgan Chase Bank" in decisions["packet-borrower-agent"].risk_bearer
    assert "extract named counterparty and role" not in decisions[
        "packet-combined-agent-role"
    ].remaining_gap
    assert "Credit Suisse AG" in decisions["packet-combined-agent-role"].risk_bearer
    assert "extract named counterparty and role" not in decisions[
        "packet-no-with-underwriter-reps"
    ].remaining_gap
    assert "PNC Capital Markets LLC" in decisions[
        "packet-no-with-underwriter-reps"
    ].risk_bearer


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
