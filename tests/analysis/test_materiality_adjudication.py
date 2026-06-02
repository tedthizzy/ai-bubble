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


def test_materiality_packet_snippet_prefers_late_collateral_scope_clause(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "data" / "edgar_acquisition" / "documents" / "secured.htm"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(
        """
        <html><body>
        Example Borrower, Inc. entered into a $2.35 billion term loan facility
        with Example Lender Bank. The opening summary discusses liquidity,
        proceeds, working capital, and general corporate purposes.
        Background liquidity and transaction overview. Background liquidity and
        transaction overview. Background liquidity and transaction overview.
        Definitions. Lien means any mortgage, pledge, charge, security interest
        or encumbrance of any kind, whether arising by contract or law.
        Collateral and Guarantee Support. The obligations under the facilities
        shall be secured by a first priority security interest in substantially
        all assets of the borrower and guaranteed by the subsidiary guarantors.
        </body></html>
        """
    )
    _write_csv(
        tmp_path / "data" / "edgar_acquisition" / "edgar_document_inventory.csv",
        [
            {
                "filing_url": "https://www.sec.gov/example-secured.htm",
                "local_path": str(source_path),
                "content_hash": "1" * 64,
                "primary_document": "secured.htm",
                "accession_number": "0001-26-000002",
            }
        ],
    )
    _write_csv(
        tmp_path / "data" / "reports" / "review_queue.csv",
        [
            {
                "review_id": "review-late-scope",
                "review_group_id": "group-late-scope",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Borrower, Inc.",
                "counterparty": "Example Lender Bank",
                "deal_id": "deal-late-scope",
                "source_row_id": "row-late-scope",
                "notional_amount_usd": "2350000000",
                "exposure_usd": "0",
                "capacity_mw": "0",
                "risk_score": "0.6",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: "
                    "debt_facility; notional $2,350,000,000; notional context: "
                    "transaction_facility"
                ),
                "recommended_action": "Confirm collateral package",
                "source_uri": "https://www.sec.gov/example-secured.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-secured.htm"]),
                "content_hash": "1" * 64,
                "content_hashes": json.dumps(["1" * 64]),
                "page_or_section": "credit agreement exhibit",
                "human_review_status": "pending",
            }
        ],
    )

    batch = build_materiality_adjudication_packets(
        [tmp_path / "data"],
        limit=1,
        snippet_chars=360,
    )

    snippet = batch.packets[0].evidence_snippets[0].snippet.lower()
    assert "shall be secured by a first priority security interest" in snippet
    assert "substantially all assets" in snippet
    assert "lien means" not in snippet


def test_materiality_packet_snippet_does_not_prefer_definition_only_scope(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "data" / "edgar_acquisition" / "documents" / "defs.htm"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(
        """
        <html><body>
        Example Finance Corp. entered into a $4.0 billion revolving credit
        facility with Example Administrative Agent to refinance existing debt.
        The facility matures in 2030 and bears interest at SOFR plus a margin.
        Boilerplate definitions follow. Lien means any mortgage, pledge,
        security interest, encumbrance or charge, including obligations secured
        by any lien on property. Permitted Liens include statutory liens and
        other customary exceptions.
        </body></html>
        """
    )
    _write_csv(
        tmp_path / "data" / "edgar_acquisition" / "edgar_document_inventory.csv",
        [
            {
                "filing_url": "https://www.sec.gov/example-defs.htm",
                "local_path": str(source_path),
                "content_hash": "2" * 64,
                "primary_document": "defs.htm",
                "accession_number": "0001-26-000003",
            }
        ],
    )
    _write_csv(
        tmp_path / "data" / "reports" / "review_queue.csv",
        [
            {
                "review_id": "review-definitions",
                "review_group_id": "group-definitions",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Finance Corp.",
                "counterparty": "Example Administrative Agent",
                "deal_id": "deal-definitions",
                "source_row_id": "row-definitions",
                "notional_amount_usd": "4000000000",
                "exposure_usd": "0",
                "capacity_mw": "0",
                "risk_score": "0.6",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: "
                    "debt_facility; notional $4,000,000,000; notional context: "
                    "transaction_facility"
                ),
                "recommended_action": "Confirm collateral package",
                "source_uri": "https://www.sec.gov/example-defs.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-defs.htm"]),
                "content_hash": "2" * 64,
                "content_hashes": json.dumps(["2" * 64]),
                "page_or_section": "credit agreement exhibit",
                "human_review_status": "pending",
            }
        ],
    )

    batch = build_materiality_adjudication_packets(
        [tmp_path / "data"],
        limit=1,
        snippet_chars=260,
    )

    snippet = batch.packets[0].evidence_snippets[0].snippet.lower()
    assert "entered into a $4.0 billion revolving credit facility" in snippet
    assert "permitted liens include statutory liens" not in snippet


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
                    [
                        "https://www.nyiso.com/documents/20142/1407078/NYISO-Interconnection-Queue.xlsx"
                    ]
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


def test_materiality_packet_keeps_role_and_scope_clauses_from_same_artifact(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "data" / "edgar_acquisition" / "documents" / "credit.htm"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(
        """
        <html><body>
        Credit Agreement, dated as of March 2, 2026, among Example Borrower LLC,
        the lenders party thereto, and Bank of Example, N.A., as administrative
        agent. Background transaction narrative and proceeds disclosure.
        Background transaction narrative and proceeds disclosure.
        Background transaction narrative and proceeds disclosure.
        The obligations under the Credit Agreement are secured by substantially
        all assets of the Borrower and guaranteed by each material subsidiary
        guarantor.
        </body></html>
        """
    )
    _write_csv(
        tmp_path / "data" / "edgar_acquisition" / "edgar_document_inventory.csv",
        [
            {
                "filing_url": "https://www.sec.gov/example-credit.htm",
                "local_path": str(source_path),
                "content_hash": "3" * 64,
                "primary_document": "credit.htm",
                "accession_number": "0001-26-000012",
            }
        ],
    )
    _write_csv(
        tmp_path / "data" / "reports" / "review_queue.csv",
        [
            {
                "review_id": "review-role-scope",
                "review_group_id": "group-role-scope",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "direct_ai_infra",
                "entity": "Example Borrower LLC",
                "counterparty": "",
                "deal_id": "deal-role-scope",
                "source_row_id": "row-role-scope",
                "notional_amount_usd": "25000000000",
                "exposure_usd": "0",
                "capacity_mw": "0",
                "risk_score": "0.4",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: "
                    "debt_facility; notional $25,000,000,000; notional context: "
                    "transaction_facility"
                ),
                "recommended_action": (
                    "Confirm named counterparty plus collateral and guarantee scope"
                ),
                "source_uri": "https://www.sec.gov/example-credit.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-credit.htm"]),
                "content_hash": "3" * 64,
                "content_hashes": json.dumps(["3" * 64]),
                "human_review_status": "pending",
            }
        ],
    )

    packet_batch = build_materiality_adjudication_packets(
        [tmp_path / "data"],
        limit=1,
        snippets_per_packet=2,
        snippet_chars=260,
    )
    write_materiality_adjudication_packets(packet_batch, tmp_path / "reports")
    decision_batch = build_materiality_adjudication_decisions(
        [tmp_path],
        adjudicated_at="2026-06-01T00:00:00+00:00",
    )

    packet_snippets = [
        snippet.snippet.lower() for snippet in packet_batch.packets[0].evidence_snippets
    ]
    assert any("bank of example" in snippet for snippet in packet_snippets)
    assert any("secured by substantially all assets" in snippet for snippet in packet_snippets)
    decision = decision_batch.decisions[0]
    assert "bank of example" in decision.evidence_quote.lower()
    assert "secured by substantially all assets" in decision.evidence_quote.lower()
    assert "guaranteed by each material subsidiary guarantor" in (decision.evidence_quote.lower())
    assert "extract named counterparty and role" not in decision.remaining_gap
    assert "determine collateral scope" not in decision.remaining_gap
    assert "determine recourse and guarantee scope" not in decision.remaining_gap
    assert decision.metric_use_status == "approved_for_metric_use"


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
                "source_uris": json.dumps(["https://www.sec.gov/alphabet-debt-prospectus.htm"]),
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


def test_materiality_adjudication_blocks_unconverted_hk_dollar_face_value(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-hkd-face-value",
                "rank": 1,
                "review_id": "review-hkd-face-value",
                "review_group_id": "group-hkd-face-value",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "market_contagion",
                "entity": "MGM Resorts International",
                "counterparty": "Bank of China Limited, Macau Branch",
                "exposure_basis_usd": "23400000000",
                "reason": (
                    "debt-like deal type: debt_facility; notional $23,400,000,000; "
                    "notional context: transaction_principal; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm metric currency conversion.",
                "source_uri": "https://www.sec.gov/mgm-hkd-facility.htm",
                "source_uris": json.dumps(["https://www.sec.gov/mgm-hkd-facility.htm"]),
                "content_hash": "d" * 64,
                "content_hashes": json.dumps(["d" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/mgm-hkd-facility.htm",
                            "content_hash": "d" * 64,
                            "document_id": "mgm-hkd-facility.htm",
                            "snippet": (
                                "MGM China entered into a HK$23.4 billion unsecured "
                                "revolving credit facility with Bank of China Limited, "
                                "Macau Branch as agent and certain lenders party thereto."
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
    assert decision.decision == "needs_deeper_extraction"
    assert decision.metric_use_status == "blocked_pending_extraction"
    assert "convert non-USD notional to USD before metric use" in decision.remaining_gap
    assert decision.supported_amount_usd == 0


def test_materiality_adjudication_allows_preconverted_hk_dollar_notional(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-hkd-converted",
                "rank": 1,
                "review_id": "review-hkd-converted",
                "review_group_id": "group-hkd-converted",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "market_contagion",
                "entity": "MGM Resorts International",
                "counterparty": "Bank of China Limited, Macau Branch",
                "exposure_basis_usd": "3000000000",
                "reason": (
                    "debt-like deal type: debt_facility; notional $3,000,000,000; "
                    "notional context: transaction_principal; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm metric currency conversion.",
                "source_uri": "https://www.sec.gov/mgm-hkd-facility.htm",
                "source_uris": json.dumps(["https://www.sec.gov/mgm-hkd-facility.htm"]),
                "content_hash": "d" * 64,
                "content_hashes": json.dumps(["d" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/mgm-hkd-facility.htm",
                            "content_hash": "d" * 64,
                            "document_id": "mgm-hkd-facility.htm",
                            "snippet": (
                                "MGM China entered into a HK$23.4 billion unsecured "
                                "revolving credit facility with Bank of China Limited, "
                                "Macau Branch as agent and certain lenders party thereto."
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
    assert batch.summary.approved_for_metric_use == 1
    assert decision.metric_use_status == "approved_for_metric_use"
    assert "convert non-USD notional" not in decision.remaining_gap
    assert decision.supported_amount_usd == 3_000_000_000


def test_materiality_adjudication_blocks_cad_face_value_recorded_as_usd(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-cad-face-value",
                "rank": 1,
                "review_id": "review-cad-face-value",
                "review_group_id": "group-cad-face-value",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Alphabet Inc.",
                "counterparty": "noteholders",
                "exposure_basis_usd": "9500000000",
                "reason": (
                    "debt-like deal type: bond; notional $9,500,000,000; "
                    "notional context: transaction_principal; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm metric currency conversion.",
                "source_uri": "https://www.sec.gov/alphabet-cad-notes.htm",
                "source_uris": json.dumps(["https://www.sec.gov/alphabet-cad-notes.htm"]),
                "content_hash": "e" * 64,
                "content_hashes": json.dumps(["e" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/alphabet-cad-notes.htm",
                            "content_hash": "e" * 64,
                            "document_id": "alphabet-cad-notes.htm",
                            "snippet": (
                                "Alphabet completed underwritten public offerings of "
                                "EUR9 billion aggregate principal amount of "
                                "euro-denominated senior notes and C$9.5 billion "
                                "aggregate principal amount of Canadian dollar-denominated "
                                "senior notes."
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
    assert "extract USD-equivalent or reselect source quote" in decision.remaining_gap
    assert decision.supported_amount_usd == 0


def test_materiality_adjudication_retags_clear_ai_operator_as_direct(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-iren-direct-operator",
                "rank": 1,
                "review_id": "review-iren-direct-operator",
                "review_group_id": "group-iren-direct-operator",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "not_tagged",
                "entity": "IREN Ltd",
                "counterparty": "noteholders",
                "exposure_basis_usd": "3000000000",
                "reason": (
                    "debt-like deal type: bond; notional $3,000,000,000; "
                    "notional context: transaction_principal; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm metric linkage.",
                "source_uri": "https://www.sec.gov/iren-notes.htm",
                "source_uris": json.dumps(["https://www.sec.gov/iren-notes.htm"]),
                "content_hash": "b" * 64,
                "content_hashes": json.dumps(["b" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/iren-notes.htm",
                            "content_hash": "b" * 64,
                            "document_id": "iren-notes.htm",
                            "snippet": (
                                "IREN issued $3.0 billion aggregate principal amount "
                                "of senior unsecured notes due 2030 under an indenture "
                                "with a trustee for the noteholders."
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
    assert decision.ai_data_center_linkage == "direct"


def test_materiality_adjudication_upgrades_stale_watchlist_ai_operator_to_direct(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-nebius-direct-operator",
                "rank": 1,
                "review_id": "review-nebius-direct-operator",
                "review_group_id": "group-nebius-direct-operator",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Nebius Group N.V.",
                "counterparty": "noteholders",
                "exposure_basis_usd": "3162500000",
                "reason": (
                    "debt-like deal type: bond; notional $3,162,500,000; "
                    "notional context: transaction_principal; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm metric linkage.",
                "source_uri": "https://www.sec.gov/nebius-notes.htm",
                "source_uris": json.dumps(["https://www.sec.gov/nebius-notes.htm"]),
                "content_hash": "n" * 64,
                "content_hashes": json.dumps(["n" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/nebius-notes.htm",
                            "content_hash": "n" * 64,
                            "document_id": "nebius-notes.htm",
                            "snippet": (
                                "Nebius Group issued $3,162,500,000 aggregate "
                                "principal amount of convertible notes due 2032 "
                                "under indentures with U.S. Bank Trust Company."
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
    assert decision.ai_data_center_linkage == "direct"


def test_materiality_adjudication_retags_cerebras_operator_as_direct(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-cerebras-direct-operator",
                "rank": 1,
                "review_id": "review-cerebras-direct-operator",
                "review_group_id": "group-cerebras-direct-operator",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "not_tagged",
                "entity": "Cerebras Systems Inc.",
                "counterparty": "lenders",
                "exposure_basis_usd": "5000000000",
                "reason": (
                    "debt-like deal type: credit_facility; notional $5,000,000,000; "
                    "notional context: transaction_principal; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm metric linkage.",
                "source_uri": "https://www.sec.gov/cerebras-credit.htm",
                "source_uris": json.dumps(["https://www.sec.gov/cerebras-credit.htm"]),
                "content_hash": "e" * 64,
                "content_hashes": json.dumps(["e" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/cerebras-credit.htm",
                            "content_hash": "e" * 64,
                            "document_id": "cerebras-credit.htm",
                            "snippet": (
                                "Cerebras Systems Inc., as borrower, entered into a "
                                "$5.0 billion credit agreement with the lenders and "
                                "Morgan Stanley Senior Funding as administrative agent."
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
    assert decision.ai_data_center_linkage == "direct"


def test_materiality_adjudication_retags_galaxy_helios_context_as_direct(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-galaxy-helios-direct",
                "rank": 1,
                "review_id": "review-galaxy-helios-direct",
                "review_group_id": "group-galaxy-helios-direct",
                "priority": "high",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "not_tagged",
                "entity": "Galaxy Digital Inc.",
                "counterparty": "Deutsche Bank AG",
                "exposure_basis_usd": "1400000000",
                "reason": (
                    "pending contract tranche review; tranche: Debt facility; "
                    "notional $1,400,000,000; maturity 2028-08-15; collateral terms present"
                ),
                "recommended_action": "Confirm metric linkage.",
                "source_uri": "https://www.sec.gov/galaxy-helios-credit.htm",
                "source_uris": json.dumps(["https://www.sec.gov/galaxy-helios-credit.htm"]),
                "content_hash": "g" * 64,
                "content_hashes": json.dumps(["g" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/galaxy-helios-credit.htm",
                            "content_hash": "g" * 64,
                            "document_id": "galaxy-helios-credit.htm",
                            "snippet": (
                                "Galaxy Helios I, as borrower, entered into a "
                                "$1.4 billion senior secured term loan facility "
                                "to finance development of the Helios data center campus."
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
    assert decision.ai_data_center_linkage == "direct"


def test_materiality_adjudication_keeps_generic_galaxy_debt_not_established(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-galaxy-generic-debt",
                "rank": 1,
                "review_id": "review-galaxy-generic-debt",
                "review_group_id": "group-galaxy-generic-debt",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "not_tagged",
                "entity": "Galaxy Digital Inc.",
                "counterparty": "noteholders",
                "exposure_basis_usd": "3427000000",
                "reason": (
                    "debt-like deal type: bond; notional $3,427,000,000; "
                    "notional context: transaction_principal; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm metric linkage.",
                "source_uri": "https://www.sec.gov/galaxy-notes.htm",
                "source_uris": json.dumps(["https://www.sec.gov/galaxy-notes.htm"]),
                "content_hash": "h" * 64,
                "content_hashes": json.dumps(["h" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/galaxy-notes.htm",
                            "content_hash": "h" * 64,
                            "document_id": "galaxy-notes.htm",
                            "snippet": (
                                "Galaxy Digital issued $3,427,000,000 aggregate "
                                "principal amount of exchangeable senior notes due "
                                "2031 for general corporate purposes."
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
    assert decision.ai_data_center_linkage == "not_established"


def test_materiality_adjudication_keeps_indirect_utility_not_established(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-georgia-power-indirect",
                "rank": 1,
                "review_id": "review-georgia-power-indirect",
                "review_group_id": "group-georgia-power-indirect",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "not_tagged",
                "entity": "Georgia Power Company",
                "counterparty": "lenders",
                "exposure_basis_usd": "3500000000",
                "reason": (
                    "debt-like deal type: credit_facility; notional $3,500,000,000; "
                    "notional context: transaction_principal; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm indirect scope rule.",
                "source_uri": "https://www.sec.gov/georgia-power-credit.htm",
                "source_uris": json.dumps(["https://www.sec.gov/georgia-power-credit.htm"]),
                "content_hash": "c" * 64,
                "content_hashes": json.dumps(["c" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/georgia-power-credit.htm",
                            "content_hash": "c" * 64,
                            "document_id": "georgia-power-credit.htm",
                            "snippet": (
                                "Georgia Power Company entered into a $3.5 billion "
                                "credit agreement with lenders party thereto and an "
                                "administrative agent; the facility is unsecured and "
                                "matures in 2030."
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
    assert decision.ai_data_center_linkage == "not_established"


def test_materiality_adjudication_reselects_stronger_same_filing_semantic_quote(
    tmp_path: Path,
) -> None:
    shared_hash = "d" * 64
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-peripheral-dtc",
                "rank": 1,
                "review_id": "review-peripheral-dtc",
                "review_group_id": "group-peripheral-dtc",
                "priority": "high",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "not_tagged",
                "entity": "United Community Banks Inc",
                "counterparty": "noteholders",
                "exposure_basis_usd": "19200000000",
                "reason": (
                    "debt-like deal type: bond; notional $19,200,000,000; "
                    "notional context: transaction_principal; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Reselect committed-debt clause.",
                "source_uri": "https://www.sec.gov/united-community-shelf.htm",
                "source_uris": json.dumps(["https://www.sec.gov/united-community-shelf.htm"]),
                "content_hash": shared_hash,
                "content_hashes": json.dumps([shared_hash]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/united-community-shelf.htm",
                            "content_hash": shared_hash,
                            "document_id": "united-community-shelf.htm",
                            "snippet": (
                                "DTC has no responsibility or liability for any aspect "
                                "of participant records relating to beneficial interests "
                                "in global security certificates."
                            ),
                        }
                    ]
                ),
            },
            {
                "packet_id": "packet-strong-sibling",
                "rank": 2,
                "review_id": "review-strong-sibling",
                "review_group_id": "group-strong-sibling",
                "priority": "high",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "not_tagged",
                "entity": "United Community Banks Inc",
                "counterparty": "trustee",
                "exposure_basis_usd": "19200000000",
                "reason": (
                    "debt-like deal type: bond; notional $19,200,000,000; "
                    "notional context: transaction_principal; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm committed-debt clause.",
                "source_uri": "https://www.sec.gov/united-community-shelf.htm",
                "source_uris": json.dumps(["https://www.sec.gov/united-community-shelf.htm"]),
                "content_hash": shared_hash,
                "content_hashes": json.dumps([shared_hash]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/united-community-shelf.htm",
                            "content_hash": shared_hash,
                            "document_id": "united-community-shelf.htm",
                            "snippet": (
                                "The company entered into an indenture with respect to "
                                "the notes with the trustee. The notes are senior "
                                "unsecured obligations issued pursuant to the indenture "
                                "and rank equally with other unsecured debt."
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

    peripheral = next(
        decision for decision in batch.decisions if decision.packet_id == "packet-peripheral-dtc"
    )
    assert peripheral.metric_use_status == "approved_for_metric_use"
    assert "DTC has no responsibility" not in peripheral.evidence_quote
    assert "entered into an indenture" in peripheral.evidence_quote
    assert "packet-strong-sibling" in peripheral.rationale


def test_materiality_adjudication_reselects_exact_amount_committed_snippet(
    tmp_path: Path,
) -> None:
    shared_hash = "x" * 64
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-amazon-peripheral-series-list",
                "rank": 1,
                "review_id": "review-amazon-peripheral-series-list",
                "review_group_id": "group-amazon-peripheral-series-list",
                "priority": "high",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "AMAZON COM INC",
                "counterparty": "underwriters",
                "exposure_basis_usd": "6000000000",
                "reason": (
                    "pending contract tranche review; tranche: Notes; "
                    "notional $6,000,000,000; interest rate 0.0385; "
                    "collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Reselect exact amount note clause.",
                "source_uri": "https://www.sec.gov/amazon-notes.htm",
                "source_uris": json.dumps(["https://www.sec.gov/amazon-notes.htm"]),
                "content_hash": shared_hash,
                "content_hashes": json.dumps([shared_hash]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/amazon-notes.htm",
                            "content_hash": shared_hash,
                            "document_id": "amazon-notes.htm",
                            "snippet": (
                                "2029 Floating Rate Notes, 2028 Notes, 2029 Notes, "
                                "2031 Notes, 2033 Notes, 2036 Notes, 2046 Notes, "
                                "2056 Notes, and 2066 Notes, the Notes, pursuant "
                                "to an Underwriting Agreement among the Company and "
                                "J.P. Morgan Securities LLC."
                            ),
                        }
                    ]
                ),
            },
            {
                "packet_id": "packet-amazon-exact-amount-sibling",
                "rank": 2,
                "review_id": "review-amazon-exact-amount-sibling",
                "review_group_id": "group-amazon-exact-amount-sibling",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "AMAZON COM INC",
                "counterparty": "noteholders",
                "exposure_basis_usd": "6000000000",
                "reason": (
                    "debt-like deal type: bond; notional $6,000,000,000; "
                    "notional context: transaction_principal; "
                    "collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Confirm exact amount note clause.",
                "source_uri": "https://www.sec.gov/amazon-notes.htm",
                "source_uris": json.dumps(["https://www.sec.gov/amazon-notes.htm"]),
                "content_hash": shared_hash,
                "content_hashes": json.dumps([shared_hash]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/amazon-notes.htm",
                            "content_hash": shared_hash,
                            "document_id": "amazon-notes.htm",
                            "snippet": (
                                "The Company issued $6,000,000,000 aggregate "
                                "principal amount of its 4.875% notes due 2036 "
                                "under the supplemental indenture."
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

    peripheral = next(
        decision
        for decision in batch.decisions
        if decision.packet_id == "packet-amazon-peripheral-series-list"
    )
    assert peripheral.metric_use_status == "approved_for_metric_use"
    assert "$6,000,000,000 aggregate principal amount" in peripheral.evidence_quote
    assert "4.875% notes due 2036" in peripheral.evidence_quote
    assert "packet-amazon-exact-amount-sibling" in peripheral.rationale


def test_materiality_adjudication_quote_reselection_preserves_metric_dedupe(
    tmp_path: Path,
) -> None:
    weak_quote = (
        "2029 Floating Rate Notes, 2028 Notes, 2029 Notes, 2031 Notes, "
        "2033 Notes, 2036 Notes, 2046 Notes, 2056 Notes, and 2066 Notes, "
        "the Notes, pursuant to an Underwriting Agreement among the Company "
        "and J.P. Morgan Securities LLC."
    )
    exact_quote = (
        "The Company issued $6,000,000,000 aggregate principal amount of "
        "its 4.875% notes due 2036 under the supplemental indenture."
    )
    hash_a = "a" * 64
    hash_b = "b" * 64
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-reselect-target",
                "rank": 1,
                "review_id": "review-reselect-target",
                "review_group_id": "group-reselect-target",
                "priority": "high",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Cloud Corp.",
                "counterparty": "underwriters",
                "exposure_basis_usd": "6000000000",
                "reason": (
                    "pending contract tranche review; tranche: Notes; "
                    "notional $6,000,000,000; interest rate 0.04875; "
                    "collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Reselect exact amount note clause.",
                "source_uri": "https://www.sec.gov/example-notes-a.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-notes-a.htm"]),
                "content_hash": hash_a,
                "content_hashes": json.dumps([hash_a]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-notes-a.htm",
                            "content_hash": hash_a,
                            "document_id": "example-notes-a.htm",
                            "snippet": weak_quote,
                        }
                    ]
                ),
            },
            {
                "packet_id": "packet-exact-amount-snippet",
                "rank": 2,
                "review_id": "review-exact-amount-snippet",
                "review_group_id": "group-exact-amount-snippet",
                "priority": "low",
                "category": "physical",
                "subcategory": "permitting_watch",
                "ecosystem_relevance": "not_tagged",
                "entity": "Example Cloud Corp.",
                "counterparty": "",
                "exposure_basis_usd": "0",
                "reason": "non-metric packet carrying a better same-filing snippet",
                "recommended_action": "Do not count as a metric row.",
                "source_uri": "https://www.sec.gov/example-notes-a.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-notes-a.htm"]),
                "content_hash": hash_a,
                "content_hashes": json.dumps([hash_a]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-notes-a.htm",
                            "content_hash": hash_a,
                            "document_id": "example-notes-a.htm",
                            "snippet": exact_quote,
                        }
                    ]
                ),
            },
            {
                "packet_id": "packet-repeat-disclosure",
                "rank": 3,
                "review_id": "review-repeat-disclosure",
                "review_group_id": "group-repeat-disclosure",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Cloud Corp.",
                "counterparty": "trustee",
                "exposure_basis_usd": "6000000000",
                "reason": (
                    "debt-like deal type: bond; notional $6,000,000,000; "
                    "notional context: transaction_principal; "
                    "collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Repeated disclosure of the same obligation.",
                "source_uri": "https://www.sec.gov/example-notes-b.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-notes-b.htm"]),
                "content_hash": hash_b,
                "content_hashes": json.dumps([hash_b]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-notes-b.htm",
                            "content_hash": hash_b,
                            "document_id": "example-notes-b.htm",
                            "snippet": weak_quote,
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

    target = next(
        decision for decision in batch.decisions if decision.packet_id == "packet-reselect-target"
    )
    assert target.metric_use_status == "approved_for_metric_use"
    assert "2029 Floating Rate Notes" in target.metric_dedupe_quote
    assert "$6,000,000,000 aggregate principal amount" not in target.metric_dedupe_quote
    assert "$6,000,000,000 aggregate principal amount" in target.evidence_quote
    assert batch.summary.approved_for_metric_use == 2
    assert batch.summary.approved_row_supported_amount_usd == 12_000_000_000
    assert batch.summary.final_metric_supported_amount_usd == 6_000_000_000
    assert batch.summary.final_metric_group_count == 1


def test_materiality_adjudication_does_not_reselect_exact_amount_boilerplate(
    tmp_path: Path,
) -> None:
    shared_hash = "y" * 64
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-fee-table-target",
                "rank": 1,
                "review_id": "review-fee-table-target",
                "review_group_id": "group-fee-table-target",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "not_tagged",
                "entity": "GE Vernova Inc.",
                "counterparty": "underwriters",
                "exposure_basis_usd": "2567180000",
                "reason": (
                    "debt-like deal type: bond; notional $2,567,180,000; "
                    "notional context: transaction_principal; "
                    "collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Do not promote filing fee table.",
                "source_uri": "https://www.sec.gov/ge-vernova-fee-table.htm",
                "source_uris": json.dumps(["https://www.sec.gov/ge-vernova-fee-table.htm"]),
                "content_hash": shared_hash,
                "content_hashes": json.dumps([shared_hash]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/ge-vernova-fee-table.htm",
                            "content_hash": shared_hash,
                            "document_id": "ge-vernova-fee-table.htm",
                            "snippet": (
                                "The notes were offered pursuant to a prospectus "
                                "supplement and an underwriting agreement."
                            ),
                        }
                    ]
                ),
            },
            {
                "packet_id": "packet-fee-table-sibling",
                "rank": 2,
                "review_id": "review-fee-table-sibling",
                "review_group_id": "group-fee-table-sibling",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "not_tagged",
                "entity": "GE Vernova Inc.",
                "counterparty": "registrant",
                "exposure_basis_usd": "2567180000",
                "reason": (
                    "debt-like deal type: bond; notional $2,567,180,000; "
                    "notional context: transaction_principal; "
                    "collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Reject fee-table amount as quote replacement.",
                "source_uri": "https://www.sec.gov/ge-vernova-fee-table.htm",
                "source_uris": json.dumps(["https://www.sec.gov/ge-vernova-fee-table.htm"]),
                "content_hash": shared_hash,
                "content_hashes": json.dumps([shared_hash]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/ge-vernova-fee-table.htm",
                            "content_hash": shared_hash,
                            "document_id": "ge-vernova-fee-table.htm",
                            "snippet": (
                                "CALCULATION OF FILING FEE TABLE. Maximum aggregate "
                                "offering amount $2,567,180,000. Total fees "
                                "previously paid were offset against the registration fee."
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

    target = next(
        decision for decision in batch.decisions if decision.packet_id == "packet-fee-table-target"
    )
    assert target.metric_use_status == "approved_for_metric_use"
    assert "FILING FEE TABLE" not in target.evidence_quote
    assert "packet-fee-table-sibling" not in target.rationale


def test_materiality_adjudication_does_not_reselect_capacity_quote_as_exact_amount(
    tmp_path: Path,
) -> None:
    shared_hash = "z" * 64
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-capacity-target",
                "rank": 1,
                "review_id": "review-capacity-target",
                "review_group_id": "group-capacity-target",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "not_tagged",
                "entity": "Oracle Example Corp.",
                "counterparty": "underwriters",
                "exposure_basis_usd": "9900000000",
                "reason": (
                    "debt-like deal type: bond; notional $9,900,000,000; "
                    "notional context: transaction_principal; "
                    "collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Do not promote capacity language.",
                "source_uri": "https://www.sec.gov/oracle-capacity.htm",
                "source_uris": json.dumps(["https://www.sec.gov/oracle-capacity.htm"]),
                "content_hash": shared_hash,
                "content_hashes": json.dumps([shared_hash]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/oracle-capacity.htm",
                            "content_hash": shared_hash,
                            "document_id": "oracle-capacity.htm",
                            "snippet": (
                                "The notes are senior unsecured obligations and "
                                "were offered under the underwriting agreement."
                            ),
                        }
                    ]
                ),
            },
            {
                "packet_id": "packet-capacity-sibling",
                "rank": 2,
                "review_id": "review-capacity-sibling",
                "review_group_id": "group-capacity-sibling",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "not_tagged",
                "entity": "Oracle Example Corp.",
                "counterparty": "lenders",
                "exposure_basis_usd": "9900000000",
                "reason": (
                    "debt-like deal type: debt_facility; notional $9,900,000,000; "
                    "notional context: financing_capacity; "
                    "collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Capacity quote is not committed debt.",
                "source_uri": "https://www.sec.gov/oracle-capacity.htm",
                "source_uris": json.dumps(["https://www.sec.gov/oracle-capacity.htm"]),
                "content_hash": shared_hash,
                "content_hashes": json.dumps([shared_hash]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/oracle-capacity.htm",
                            "content_hash": shared_hash,
                            "document_id": "oracle-capacity.htm",
                            "snippet": (
                                "The company had the ability to borrow up to an "
                                "additional $9.9 billion under its revolving "
                                "credit facility and commercial paper program."
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

    target = next(
        decision for decision in batch.decisions if decision.packet_id == "packet-capacity-target"
    )
    assert target.metric_use_status == "approved_for_metric_use"
    assert "ability to borrow" not in target.evidence_quote
    assert "packet-capacity-sibling" not in target.rationale


def test_materiality_adjudication_does_not_reselect_semantic_quote_across_entities(
    tmp_path: Path,
) -> None:
    shared_hash = "e" * 64
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-target-entity",
                "rank": 1,
                "review_id": "review-target-entity",
                "review_group_id": "group-target-entity",
                "priority": "high",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "not_tagged",
                "entity": "Target Bancorp",
                "counterparty": "noteholders",
                "exposure_basis_usd": "5000000000",
                "reason": (
                    "debt-like deal type: bond; notional $5,000,000,000; "
                    "notional context: transaction_principal; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Reselect committed-debt clause.",
                "source_uri": "https://www.sec.gov/shared-filing.htm",
                "source_uris": json.dumps(["https://www.sec.gov/shared-filing.htm"]),
                "content_hash": shared_hash,
                "content_hashes": json.dumps([shared_hash]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/shared-filing.htm",
                            "content_hash": shared_hash,
                            "document_id": "shared-filing.htm",
                            "snippet": (
                                "DTC has no responsibility or liability for participant "
                                "records relating to beneficial interests in global "
                                "security certificates."
                            ),
                        }
                    ]
                ),
            },
            {
                "packet_id": "packet-other-entity",
                "rank": 2,
                "review_id": "review-other-entity",
                "review_group_id": "group-other-entity",
                "priority": "high",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "not_tagged",
                "entity": "Other Bancorp",
                "counterparty": "trustee",
                "exposure_basis_usd": "5000000000",
                "reason": (
                    "debt-like deal type: bond; notional $5,000,000,000; "
                    "notional context: transaction_principal; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm committed-debt clause.",
                "source_uri": "https://www.sec.gov/shared-filing.htm",
                "source_uris": json.dumps(["https://www.sec.gov/shared-filing.htm"]),
                "content_hash": shared_hash,
                "content_hashes": json.dumps([shared_hash]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/shared-filing.htm",
                            "content_hash": shared_hash,
                            "document_id": "shared-filing.htm",
                            "snippet": (
                                "Other Bancorp entered into an indenture with respect "
                                "to the notes with the trustee. The notes are senior "
                                "unsecured obligations issued pursuant to the indenture."
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

    target = next(
        decision for decision in batch.decisions if decision.packet_id == "packet-target-entity"
    )
    assert target.metric_use_status == "approved_for_metric_use"
    assert "DTC has no responsibility" in target.evidence_quote
    assert "entered into an indenture" not in target.evidence_quote


def test_materiality_adjudication_blocks_mixed_currency_quote_without_recorded_usd(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-sterling-mixed-currency",
                "rank": 1,
                "review_id": "review-sterling-mixed-currency",
                "review_group_id": "group-sterling-mixed-currency",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Alphabet Inc.",
                "counterparty": "noteholders",
                "exposure_basis_usd": "20000000000",
                "reason": (
                    "debt-like deal type: bond; notional $20,000,000,000; "
                    "notional context: transaction_principal; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Reselect source quote with USD-equivalent schedule.",
                "source_uri": "https://www.sec.gov/alphabet-sterling-notes.htm",
                "source_uris": json.dumps(["https://www.sec.gov/alphabet-sterling-notes.htm"]),
                "content_hash": "f" * 64,
                "content_hashes": json.dumps(["f" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/alphabet-sterling-notes.htm",
                            "content_hash": "f" * 64,
                            "document_id": "alphabet-sterling-notes.htm",
                            "snippet": (
                                "The Sterling Notes consist of GBP750,000,000 "
                                "aggregate principal amount of 4.125% notes due 2029, "
                                "GBP1,250,000,000 aggregate principal amount of "
                                "4.625% notes due 2032, and GBP1,000,000,000 "
                                "aggregate principal amount of 6.125% notes due 2126."
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
    assert "extract USD-equivalent or reselect source quote" in decision.remaining_gap
    assert decision.supported_amount_usd == 0


def test_materiality_adjudication_allows_usd_confirmed_mixed_currency_quote(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-usd-confirmed-mixed-currency",
                "rank": 1,
                "review_id": "review-usd-confirmed-mixed-currency",
                "review_group_id": "group-usd-confirmed-mixed-currency",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "market_contagion",
                "entity": "Baker Hughes Co",
                "counterparty": "noteholders",
                "exposure_basis_usd": "6500000000",
                "reason": (
                    "debt-like deal type: bond; notional $6,500,000,000; "
                    "notional context: transaction_principal; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Approve USD-confirmed mixed-currency note offering.",
                "source_uri": "https://www.sec.gov/baker-hughes-mixed-notes.htm",
                "source_uris": json.dumps(["https://www.sec.gov/baker-hughes-mixed-notes.htm"]),
                "content_hash": "a" * 64,
                "content_hashes": json.dumps(["a" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/baker-hughes-mixed-notes.htm",
                            "content_hash": "a" * 64,
                            "document_id": "baker-hughes-mixed-notes.htm",
                            "snippet": (
                                "Baker Hughes successfully issued $6.5 billion in debt "
                                "consisting of five tranches of senior unsecured notes "
                                "and EUR3 billion in debt consisting of four tranches "
                                "of senior unsecured notes."
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
    assert batch.summary.approved_for_metric_use == 1
    assert decision.metric_use_status == "approved_for_metric_use"
    assert "extract USD-equivalent or reselect source quote" not in decision.remaining_gap
    assert decision.supported_amount_usd == 6_500_000_000


def test_materiality_adjudication_blocks_bank_financial_metric_snippet(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-bank-financial-metric",
                "rank": 1,
                "review_id": "review-bank-financial-metric",
                "review_group_id": "group-bank-financial-metric",
                "priority": "critical",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "market_contagion",
                "entity": "Example Bancorp",
                "counterparty": "noteholders",
                "exposure_basis_usd": "41594000000",
                "reason": (
                    "pending contract tranche review; tranche: Notes; notional $41,594,000,000"
                ),
                "recommended_action": "Confirm whether this is debt or bank metrics",
                "source_uri": "https://www.sec.gov/example-bank-results.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-bank-results.htm"]),
                "content_hash": "d" * 64,
                "content_hashes": json.dumps(["d" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-bank-results.htm",
                            "content_hash": "d" * 64,
                            "document_id": "example-bank-results.htm",
                            "snippet": (
                                "Net income of $109.8 million, return on average "
                                "assets of 1.65%, tangible book value growth, "
                                "market capitalization and efficiency ratio improved."
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
        "split asset, UPB, or financing-capacity disclosure from committed debt"
        in decision.remaining_gap
    )
    assert decision.metric_use_status == "blocked_pending_extraction"
    assert decision.supported_amount_usd == 0


def test_materiality_adjudication_blocks_enterprise_value_acquisition_snippet(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-enterprise-value",
                "rank": 1,
                "review_id": "review-enterprise-value",
                "review_group_id": "group-enterprise-value",
                "priority": "critical",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "market_contagion",
                "entity": "Example Payments Inc.",
                "counterparty": "noteholders",
                "exposure_basis_usd": "24250000000",
                "reason": (
                    "pending contract tranche review; tranche: Notes; notional $24,250,000,000"
                ),
                "recommended_action": "Confirm whether this is debt or acquisition value",
                "source_uri": "https://www.sec.gov/example-acquisition.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-acquisition.htm"]),
                "content_hash": "e" * 64,
                "content_hashes": json.dumps(["e" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-acquisition.htm",
                            "content_hash": "e" * 64,
                            "document_id": "example-acquisition.htm",
                            "snippet": (
                                "Completion of Acquisition or Disposition of Assets. "
                                "The aggregate purchase price was based on a $24.25 "
                                "billion enterprise valuation for the acquired "
                                "business."
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
        "split asset, UPB, or financing-capacity disclosure from committed debt"
        in decision.remaining_gap
    )
    assert decision.metric_use_status == "blocked_pending_extraction"
    assert decision.supported_amount_usd == 0


def test_materiality_adjudication_does_not_block_existing_notes_with_incidental_undrawn_clause(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-existing-notes-with-undrawn-facility",
                "rank": 1,
                "review_id": "review-existing-notes-with-undrawn-facility",
                "review_group_id": "group-existing-notes-with-undrawn-facility",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Keurig Dr Pepper Inc.",
                "counterparty": "noteholders",
                "exposure_basis_usd": "14100000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: bond; "
                    "notional $14,100,000,000; notional context: transaction_principal"
                ),
                "recommended_action": "Confirm amount binding",
                "source_uri": "https://www.sec.gov/kdp-guarantees.htm",
                "source_uris": json.dumps(["https://www.sec.gov/kdp-guarantees.htm"]),
                "content_hash": "k" * 64,
                "content_hashes": json.dumps(["k" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/kdp-guarantees.htm",
                            "content_hash": "k" * 64,
                            "document_id": "kdp-guarantees.htm",
                            "snippet": (
                                "As of March 6, 2026, the full amount of the "
                                "Delayed Draw Term Loan Agreement remains available "
                                "and undrawn. Maple Parent Holdings became a "
                                "guarantor of KDP's $14.1 billion of existing "
                                "senior unsecured notes, KDP's $4.3 billion "
                                "revolving credit agreement, and KDP's bridge "
                                "credit facility."
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
        "split asset, UPB, or financing-capacity disclosure from committed debt"
        not in decision.remaining_gap
    )
    assert decision.metric_use_status == "approved_for_metric_use"


def test_materiality_adjudication_blocks_amount_bound_undrawn_revolver_capacity(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-undrawn-revolver-capacity",
                "rank": 1,
                "review_id": "review-undrawn-revolver-capacity",
                "review_group_id": "group-undrawn-revolver-capacity",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Keurig Dr Pepper Inc.",
                "counterparty": "revolving lenders",
                "exposure_basis_usd": "4300000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: "
                    "debt_facility; notional $4,300,000,000; notional context: "
                    "transaction_facility"
                ),
                "recommended_action": "Confirm amount binding",
                "source_uri": "https://www.sec.gov/kdp-guarantees.htm",
                "source_uris": json.dumps(["https://www.sec.gov/kdp-guarantees.htm"]),
                "content_hash": "l" * 64,
                "content_hashes": json.dumps(["l" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/kdp-guarantees.htm",
                            "content_hash": "l" * 64,
                            "document_id": "kdp-guarantees.htm",
                            "snippet": (
                                "Maple Parent Holdings became a guarantor of "
                                "KDP's $14.1 billion of existing senior unsecured "
                                "notes, KDP's $4.3 billion revolving credit "
                                "agreement, and KDP's bridge credit facility. "
                                "There were no borrowings as of March 6, 2026, "
                                "under the revolving credit facility."
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
        "split asset, UPB, or financing-capacity disclosure from committed debt"
        in decision.remaining_gap
    )
    assert decision.metric_use_status == "blocked_pending_extraction"


def _single_capacity_decision(
    tmp_path: Path,
    *,
    packet_id: str,
    entity: str,
    amount: int,
    quote: str,
    reason: str | None = None,
    counterparty: str = "revolving lenders",
) -> object:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": packet_id,
                "rank": 1,
                "review_id": f"review-{packet_id}",
                "review_group_id": f"group-{packet_id}",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": entity,
                "counterparty": counterparty,
                "exposure_basis_usd": str(amount),
                "reason": reason
                or (
                    "pending adjudication status: pending; debt-like deal type: "
                    f"debt_facility; notional ${amount:,.0f}; notional context: "
                    "transaction_facility"
                ),
                "recommended_action": "Confirm amount binding",
                "source_uri": f"https://www.sec.gov/{packet_id}.htm",
                "source_uris": json.dumps([f"https://www.sec.gov/{packet_id}.htm"]),
                "content_hash": "q" * 64,
                "content_hashes": json.dumps(["q" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": f"https://www.sec.gov/{packet_id}.htm",
                            "content_hash": "q" * 64,
                            "document_id": f"{packet_id}.htm",
                            "snippet": quote,
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
    return batch.decisions[0]


def test_materiality_adjudication_blocks_consolidated_indebtedness_rollup(
    tmp_path: Path,
) -> None:
    decision = _single_capacity_decision(
        tmp_path,
        packet_id="packet-consolidated-indebtedness-rollup",
        entity="Equinix Inc.",
        amount=18_100_000_000,
        quote=(
            "As of March 31, 2025, Equinix, Inc. had approximately "
            "$18.1 billion of consolidated indebtedness, which included "
            "finance lease liabilities, mortgage and loans payable and senior "
            "notes. The company also had $3.9 billion available under its "
            "revolving credit facility."
        ),
    )

    assert (
        "split asset, UPB, or financing-capacity disclosure from committed debt"
        in decision.remaining_gap
    )
    assert decision.metric_use_status == "blocked_pending_extraction"


def test_materiality_adjudication_blocks_available_borrowing_capacity(
    tmp_path: Path,
) -> None:
    decision = _single_capacity_decision(
        tmp_path,
        packet_id="packet-available-borrowing-capacity",
        entity="General Motors Co.",
        amount=6_000_000_000,
        quote=(
            "The Facility is unsecured, provides available borrowing capacity "
            "of $6.0 billion, and matures on October 1, 2024."
        ),
    )

    assert (
        "split asset, UPB, or financing-capacity disclosure from committed debt"
        in decision.remaining_gap
    )
    assert decision.metric_use_status == "blocked_pending_extraction"


def test_materiality_adjudication_blocks_covenant_basket_amount(
    tmp_path: Path,
) -> None:
    decision = _single_capacity_decision(
        tmp_path,
        packet_id="packet-covenant-basket-amount",
        entity="Advanced Micro Devices Inc.",
        amount=1_250_000_000,
        quote=(
            "The notes are not at least equally and ratably secured would not "
            "exceed the greater of (a) $1.25 billion and (b) 25% of our "
            "Consolidated Net Tangible Assets."
        ),
    )

    assert (
        "split asset, UPB, or financing-capacity disclosure from committed debt"
        in decision.remaining_gap
    )
    assert decision.metric_use_status == "blocked_pending_extraction"


def test_materiality_adjudication_blocks_weak_quote_without_bound_amount(
    tmp_path: Path,
) -> None:
    decision = _single_capacity_decision(
        tmp_path,
        packet_id="packet-weak-rate-grid-quote",
        entity="General Motors Co.",
        amount=1_000_000_000,
        quote=(
            "If not available, then the rating most recently in effect prior "
            "to such change or cessation shall apply. Credit Agreement "
            "Schedule 1.1C lists Applicable Margin, Facility Fee Rate and "
            "Existing Liens."
        ),
    )

    assert (
        "split asset, UPB, or financing-capacity disclosure from committed debt"
        in decision.remaining_gap
    )
    assert decision.metric_use_status == "blocked_pending_extraction"


def test_materiality_adjudication_blocks_zero_draw_replacement_revolver(
    tmp_path: Path,
) -> None:
    decision = _single_capacity_decision(
        tmp_path,
        packet_id="packet-zero-draw-replacement-revolver",
        entity="Advanced Micro Devices Inc.",
        amount=5_000_000_000,
        quote=(
            "The Credit Agreement provides for a five-year, $5.0 billion "
            "unsecured revolving credit facility and replaces the Company's "
            "existing Credit Agreement. As of the Closing Date, there are no "
            "borrowings outstanding under the Revolving Facility."
        ),
    )

    assert (
        "split asset, UPB, or financing-capacity disclosure from committed debt"
        in decision.remaining_gap
    )
    assert decision.metric_use_status == "blocked_pending_extraction"


def test_materiality_adjudication_keeps_committed_bridge_and_revolver_controls(
    tmp_path: Path,
) -> None:
    rows = []
    for packet_id, entity, amount, quote in [
        (
            "packet-committed-bridge-control",
            "Public Storage",
            2_000_000_000,
            "The Parent Commitment Parties committed to provide, subject to "
            "the terms and conditions of the Parent Commitment Letter, up to "
            "$2.0 billion of senior unsecured bridge loans.",
        ),
        (
            "packet-committed-revolver-control",
            "Wynn Resorts Ltd.",
            2_500_000_000,
            "We increased the borrowing capacity under the WM Cayman II "
            "Revolver by an additional aggregate amount of $1.0 billion, "
            "bringing the total committed amount to $2.5 billion equivalent.",
        ),
    ]:
        rows.append(
            {
                "packet_id": packet_id,
                "rank": len(rows) + 1,
                "review_id": f"review-{packet_id}",
                "review_group_id": f"group-{packet_id}",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": entity,
                "counterparty": "commitment parties",
                "exposure_basis_usd": str(amount),
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: "
                    f"debt_facility; notional ${amount:,.0f}; notional context: "
                    "transaction_facility"
                ),
                "recommended_action": "Confirm amount binding",
                "source_uri": f"https://www.sec.gov/{packet_id}.htm",
                "source_uris": json.dumps([f"https://www.sec.gov/{packet_id}.htm"]),
                "content_hash": "r" * 64,
                "content_hashes": json.dumps(["r" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": f"https://www.sec.gov/{packet_id}.htm",
                            "content_hash": "r" * 64,
                            "document_id": f"{packet_id}.htm",
                            "snippet": quote,
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

    decisions = {decision.packet_id: decision for decision in batch.decisions}
    for decision in decisions.values():
        assert (
            "split asset, UPB, or financing-capacity disclosure from committed debt"
            not in decision.remaining_gap
        )
    assert decisions["packet-committed-bridge-control"].metric_use_status == (
        "approved_for_metric_use"
    )


def test_materiality_adjudication_blocks_pro_forma_combined_financing_total(
    tmp_path: Path,
) -> None:
    decision = _single_capacity_decision(
        tmp_path,
        packet_id="packet-pro-forma-combined-total",
        entity="Brown & Brown, Inc.",
        amount=11_960_000_000,
        quote=(
            "The Company funded the purchase price with a combination of "
            "net proceeds from a follow-on common stock offering, net proceeds "
            "from the issuance of certain series of unsecured senior notes and "
            "the Equity Consideration, described further in Note 3 to this "
            "unaudited pro forma condensed combined financial information."
        ),
        reason=(
            "pending adjudication status: pending; debt-like deal type: bond; "
            "notional $11,960,000,000; notional context: transaction_tranche_sum; "
            "commitment scope: specific_transaction_commitment"
        ),
    )

    assert "split aggregate disclosure from specific committed obligation" in (
        decision.remaining_gap
    )
    assert decision.metric_use_status == "blocked_pending_extraction"


def test_materiality_adjudication_blocks_loan_portfolio_asset_total(
    tmp_path: Path,
) -> None:
    decision = _single_capacity_decision(
        tmp_path,
        packet_id="packet-loan-portfolio-asset-total",
        entity="Navient Corp.",
        amount=15_963_000_000,
        quote=(
            "We expect to fund our ongoing liquidity needs, including the "
            "repayment of $1.2 billion of senior unsecured notes and the "
            "remaining $4.1 billion of senior unsecured notes, through sources "
            "including our cash on hand and Private Education Loan portfolios."
        ),
        reason=(
            "pending contract tranche review; tranche: Notes; notional "
            "$15,963,000,000; maturity 2025-03-31; collateral terms present"
        ),
    )

    assert "split aggregate disclosure from specific committed obligation" in (
        decision.remaining_gap
    )
    assert decision.metric_use_status == "blocked_pending_extraction"


def test_materiality_adjudication_blocks_debt_rollup_total(
    tmp_path: Path,
) -> None:
    decision = _single_capacity_decision(
        tmp_path,
        packet_id="packet-debt-rollup-total",
        entity="MidCap Financial Investment Corp.",
        amount=2_058_000_000,
        quote=(
            "Total debt totaled $2,058 million which was comprised of "
            "$125 million of Senior Unsecured Notes, $80 million of Senior "
            "Unsecured Notes, $232 million outstanding Class A-1 Notes, "
            "$399 million outstanding secured debt and $1,222 million "
            "outstanding under the Company's Senior Secured Facility."
        ),
    )

    assert "split aggregate disclosure from specific committed obligation" in (
        decision.remaining_gap
    )
    assert decision.metric_use_status == "blocked_pending_extraction"


def test_materiality_adjudication_blocks_total_capacity_bundle(
    tmp_path: Path,
) -> None:
    decision = _single_capacity_decision(
        tmp_path,
        packet_id="packet-total-capacity-bundle",
        entity="NRG Energy, Inc.",
        amount=8_000_000_000,
        quote=(
            "Total capacity of Revolving Credit Facility and collective "
            "collateral facilities was $8.0 billion as of September 30, 2025."
        ),
    )

    assert "split aggregate disclosure from specific committed obligation" in (
        decision.remaining_gap
    )
    assert decision.metric_use_status == "blocked_pending_extraction"


def test_materiality_adjudication_keeps_single_multi_tranche_offering(
    tmp_path: Path,
) -> None:
    decision = _single_capacity_decision(
        tmp_path,
        packet_id="packet-single-multi-tranche-offering",
        entity="Baker Hughes Company",
        amount=6_500_000_000,
        quote=(
            "Baker Hughes is offering $6.5 billion aggregate principal amount "
            "of senior notes consisting of five tranches under the indenture."
        ),
        reason=(
            "pending adjudication status: pending; debt-like deal type: bond; "
            "notional $6,500,000,000; notional context: transaction_principal"
        ),
        counterparty="underwriters",
    )

    assert "split aggregate disclosure from specific committed obligation" not in (
        decision.remaining_gap
    )
    assert decision.metric_use_status == "approved_for_metric_use"


def test_materiality_adjudication_blocks_indeterminate_shelf_capacity(
    tmp_path: Path,
) -> None:
    decision = _single_capacity_decision(
        tmp_path,
        packet_id="packet-indeterminate-shelf-capacity",
        entity="Ameris Bancorp",
        amount=22_380_000_000,
        quote=(
            "An indeterminate amount of securities are being registered under "
            "this registration statement and may be offered from time to time."
        ),
    )

    assert "confirm source quote contains specific committed obligation terms" in (
        decision.remaining_gap
    )
    assert decision.metric_use_status == "blocked_pending_extraction"


def test_materiality_adjudication_blocks_preferred_stock_purchase_agreement(
    tmp_path: Path,
) -> None:
    decision = _single_capacity_decision(
        tmp_path,
        packet_id="packet-preferred-stock-purchase",
        entity="Cerebras Systems Inc.",
        amount=5_000_000_000,
        quote=(
            "Series F-1 Preferred Stock Purchase Agreement by and among "
            "Cerebras Systems Inc. and the purchasers named therein."
        ),
    )

    assert "confirm source quote contains specific committed obligation terms" in (
        decision.remaining_gap
    )
    assert decision.metric_use_status == "blocked_pending_extraction"


def test_materiality_adjudication_blocks_no_leverage_fund_share_offering(
    tmp_path: Path,
) -> None:
    decision = _single_capacity_decision(
        tmp_path,
        packet_id="packet-no-leverage-fund",
        entity="Fidelity Solana Fund",
        amount=1_000_000_000,
        quote=(
            "The Trust will not utilize leverage, derivatives or similar "
            "instruments and will issue shares of beneficial interest."
        ),
    )

    assert "confirm source quote contains specific committed obligation terms" in (
        decision.remaining_gap
    )
    assert decision.metric_use_status == "blocked_pending_extraction"


def test_materiality_adjudication_blocks_acquisition_purchase_price(
    tmp_path: Path,
) -> None:
    decision = _single_capacity_decision(
        tmp_path,
        packet_id="packet-acquisition-purchase-price",
        entity="eBay Inc.",
        amount=1_200_000_000,
        quote=(
            "eBay agreed to acquire Depop, Inc. for approximately "
            "$1.2 billion in cash, subject to purchase price adjustments."
        ),
    )

    assert "confirm source quote contains specific committed obligation terms" in (
        decision.remaining_gap
    )
    assert decision.metric_use_status == "blocked_pending_extraction"


def test_materiality_adjudication_does_not_block_underwriter_commitment_boilerplate(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-underwriter-commitment-boilerplate",
                "rank": 1,
                "review_id": "review-underwriter-commitment-boilerplate",
                "review_group_id": "group-underwriter-commitment-boilerplate",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "BHP Group Ltd",
                "counterparty": "underwriters",
                "exposure_basis_usd": "2953000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: bond; "
                    "notional $2,953,000,000; notional context: transaction_principal"
                ),
                "recommended_action": "Confirm amount binding",
                "source_uri": "https://www.sec.gov/bhp-notes.htm",
                "source_uris": json.dumps(["https://www.sec.gov/bhp-notes.htm"]),
                "content_hash": "m" * 64,
                "content_hashes": json.dumps(["m" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/bhp-notes.htm",
                            "content_hash": "m" * 64,
                            "document_id": "bhp-notes.htm",
                            "snippet": (
                                "BHP Billiton Finance (USA) Limited is offering "
                                "and selling US$2.953 billion senior notes due "
                                "2035. The underwriting agreement provides that "
                                "the purchase commitments of the non-defaulting "
                                "underwriters may be increased or the underwriting "
                                "agreement may be terminated."
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
        "split asset, UPB, or financing-capacity disclosure from committed debt"
        not in decision.remaining_gap
    )
    assert decision.metric_use_status == "approved_for_metric_use"


def test_materiality_adjudication_blocks_amount_bound_terminated_bridge_capacity(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-terminated-bridge-capacity",
                "rank": 1,
                "review_id": "review-terminated-bridge-capacity",
                "review_group_id": "group-terminated-bridge-capacity",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Global Payments Inc.",
                "counterparty": "commitment parties",
                "exposure_basis_usd": "7700000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: "
                    "debt_facility; notional $7,700,000,000; notional context: "
                    "transaction_facility"
                ),
                "recommended_action": "Confirm amount binding",
                "source_uri": "https://www.sec.gov/global-payments-bridge.htm",
                "source_uris": json.dumps(["https://www.sec.gov/global-payments-bridge.htm"]),
                "content_hash": "p" * 64,
                "content_hashes": json.dumps(["p" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/global-payments-bridge.htm",
                            "content_hash": "p" * 64,
                            "document_id": "global-payments-bridge.htm",
                            "snippet": (
                                "The Commitment Parties committed to provide a "
                                "364-day senior unsecured bridge loan facility "
                                "in an initial aggregate principal amount of up "
                                "to $7.7 billion. Upon closing of the offering, "
                                "the company reduced the remaining commitments "
                                "related to the Bridge Facility to zero and "
                                "terminated the Bridge Facility in full."
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
        "split asset, UPB, or financing-capacity disclosure from committed debt"
        in decision.remaining_gap
    )
    assert decision.metric_use_status == "blocked_pending_extraction"


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
    assert {decision.metric_aggregation_policy for decision in batch.decisions} == {
        "max_amount_per_source_instrument"
    }


def test_materiality_adjudication_dedupes_same_accession_amount_metric_rows(
    tmp_path: Path,
) -> None:
    accession = "000000000000000001"
    rows = []
    for rank, subcategory, counterparty, hash_value, quote in [
        (
            1,
            "contract_tranche_terms",
            "underwriters",
            "a" * 64,
            "Example Cloud Corp. completed an offering of $6,000,000,000 "
            "aggregate principal amount of its senior unsecured notes due 2036.",
        ),
        (
            2,
            "high_notional_debt_like_candidate",
            "trustee",
            "b" * 64,
            "The notes are senior unsecured obligations issued pursuant to an "
            "indenture with the trustee and include $6.0 billion principal due 2036.",
        ),
    ]:
        uri = f"https://www.sec.gov/Archives/edgar/data/1234/{accession}/example-{rank}.htm"
        rows.append(
            {
                "packet_id": f"packet-same-accession-{rank}",
                "rank": rank,
                "review_id": f"review-same-accession-{rank}",
                "review_group_id": f"group-same-accession-{rank}",
                "priority": "high",
                "category": "capital",
                "subcategory": subcategory,
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Cloud Corp.",
                "counterparty": counterparty,
                "exposure_basis_usd": "6000000000",
                "reason": (
                    "debt-like deal type: bond; notional $6,000,000,000; "
                    "notional context: transaction_principal; "
                    "collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Confirm same-accession duplicate",
                "source_uri": uri,
                "source_uris": json.dumps([uri]),
                "content_hash": hash_value,
                "content_hashes": json.dumps([hash_value]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": uri,
                            "content_hash": hash_value,
                            "document_id": f"example-{rank}.htm",
                            "snippet": quote,
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
    assert batch.summary.approved_row_supported_amount_usd == 12_000_000_000
    assert batch.summary.final_metric_supported_amount_usd == 6_000_000_000
    assert batch.summary.final_metric_group_count == 1
    assert len({decision.metric_group_id for decision in batch.decisions}) == 2


def test_materiality_adjudication_dedupes_same_content_hash_quote_collision(
    tmp_path: Path,
) -> None:
    source_uri = "https://www.sec.gov/Archives/edgar/data/1234/000000000125000001/ex991.htm"
    quote = (
        "Example Issuer announced the final results of its exchange offer for senior secured "
        "notes and described the same indenture, trustee, guarantees, collateral terms, and "
        "outstanding notes in each extraction from the same filed source document."
    )
    rows = []
    for rank, amount in [(1, 8_000_000_000), (2, 3_000_000_000)]:
        rows.append(
            {
                "packet_id": f"packet-content-collision-{rank}",
                "rank": rank,
                "review_id": f"review-content-collision-{rank}",
                "review_group_id": f"group-content-collision-{rank}",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "not_established",
                "entity": "Example Issuer",
                "counterparty": "Example Trustee",
                "exposure_basis_usd": str(amount),
                "reason": (
                    f"debt-like deal type: bond; notional ${amount:,}; "
                    "notional context: transaction_principal; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm content-hash quote collision",
                "source_uri": source_uri,
                "source_uris": json.dumps([source_uri]),
                "content_hash": "n" * 64,
                "content_hashes": json.dumps(["n" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": source_uri,
                            "content_hash": "n" * 64,
                            "document_id": "ex991.htm",
                            "snippet": quote,
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
    assert batch.summary.approved_row_supported_amount_usd == 11_000_000_000
    assert batch.summary.final_metric_supported_amount_usd == 8_000_000_000
    assert batch.summary.final_metric_group_count == 1
    assert len({decision.metric_group_id for decision in batch.decisions}) == 2


def test_materiality_adjudication_keeps_same_amount_across_accessions(
    tmp_path: Path,
) -> None:
    rows = []
    for rank, accession, hash_value in [
        (1, "000000000000000001", "c" * 64),
        (2, "000000000000000002", "d" * 64),
    ]:
        uri = f"https://www.sec.gov/Archives/edgar/data/1234/{accession}/example-{rank}.htm"
        rows.append(
            {
                "packet_id": f"packet-different-accession-{rank}",
                "rank": rank,
                "review_id": f"review-different-accession-{rank}",
                "review_group_id": f"group-different-accession-{rank}",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Repeat Issuer Corp.",
                "counterparty": f"trustee-{rank}",
                "exposure_basis_usd": "4000000000",
                "reason": (
                    "debt-like deal type: bond; notional $4,000,000,000; "
                    "notional context: transaction_principal; "
                    "collateral terms present; guarantee scope present"
                ),
                "recommended_action": "Keep distinct accessions separate",
                "source_uri": uri,
                "source_uris": json.dumps([uri]),
                "content_hash": hash_value,
                "content_hashes": json.dumps([hash_value]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": uri,
                            "content_hash": hash_value,
                            "document_id": f"example-{rank}.htm",
                            "snippet": (
                                f"Example Repeat Issuer Corp. issued $4.0 billion "
                                f"aggregate principal amount of senior notes due 20{30 + rank}."
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
    assert batch.summary.approved_row_supported_amount_usd == 8_000_000_000
    assert batch.summary.final_metric_supported_amount_usd == 8_000_000_000
    assert batch.summary.final_metric_group_count == 2


def test_materiality_adjudication_dedupes_cross_filing_exact_quote_amount_repeat(
    tmp_path: Path,
) -> None:
    quote = (
        "On May 1, 2025, in connection with the Issuer Solutions transaction, "
        "Example Payments Corp. entered into a Term Loan Credit Agreement with "
        "Goldman Sachs Bank USA, as administrative agent, providing an $8.0 "
        "billion senior unsecured term loan facility."
    )
    rows = []
    for rank, accession in [(1, "000119312526096739"), (2, "000119312526073639")]:
        uri = f"https://www.sec.gov/Archives/edgar/data/1136893/{accession}/example.htm"
        rows.append(
            {
                "packet_id": f"packet-exact-cross-filing-{rank}",
                "rank": rank,
                "review_id": f"review-exact-cross-filing-{rank}",
                "review_group_id": f"group-exact-cross-filing-{rank}",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "not_established",
                "entity": "Example Payments Corp.",
                "counterparty": "Goldman Sachs Bank USA",
                "exposure_basis_usd": "8000000000",
                "reason": (
                    "debt-like deal type: debt_facility; notional $8,000,000,000; "
                    "notional context: transaction_principal; commitment scope: "
                    "specific_transaction_commitment; guarantee scope present"
                ),
                "recommended_action": "Confirm cross-filing exact quote repeat",
                "source_uri": uri,
                "source_uris": json.dumps([uri]),
                "content_hash": str(rank) * 64,
                "content_hashes": json.dumps([str(rank) * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": uri,
                            "content_hash": str(rank) * 64,
                            "document_id": f"example-{rank}.htm",
                            "snippet": quote,
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
    assert batch.summary.approved_row_supported_amount_usd == 16_000_000_000
    assert batch.summary.final_metric_supported_amount_usd == 8_000_000_000
    assert batch.summary.final_metric_group_count == 1
    assert len({decision.metric_group_id for decision in batch.decisions}) == 2


def test_materiality_adjudication_dedupes_same_obligation_across_filings(
    tmp_path: Path,
) -> None:
    quote = (
        "Example Parent Corp. entered into a credit agreement with Example Bank, "
        "N.A., as administrative agent, providing a $5.0 billion senior unsecured "
        "revolving credit facility. The facility is guaranteed by Example Finance LLC."
    )
    rows = []
    for rank, hash_value in [(1, "f" * 64), (2, "9" * 64)]:
        rows.append(
            {
                "packet_id": f"packet-repeat-filing-{rank}",
                "rank": rank,
                "review_id": f"review-repeat-filing-{rank}",
                "review_group_id": f"group-repeat-filing-{rank}",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Parent Corp.",
                "counterparty": "Example Bank, N.A.",
                "exposure_basis_usd": "5000000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: "
                    "debt_facility; notional $5,000,000,000; notional context: "
                    "transaction_principal; commitment scope: "
                    "specific_transaction_commitment"
                ),
                "recommended_action": "Confirm repeated filing disclosure",
                "source_uri": f"https://www.sec.gov/example-repeat-{rank}.htm",
                "source_uris": json.dumps([f"https://www.sec.gov/example-repeat-{rank}.htm"]),
                "content_hash": hash_value,
                "content_hashes": json.dumps([hash_value]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": f"https://www.sec.gov/example-repeat-{rank}.htm",
                            "content_hash": hash_value,
                            "document_id": f"example-repeat-{rank}.htm",
                            "snippet": quote,
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
    assert batch.summary.approved_row_supported_amount_usd == 10_000_000_000
    assert batch.summary.final_metric_supported_amount_usd == 5_000_000_000
    assert batch.summary.final_metric_group_count == 1
    assert len({decision.metric_group_id for decision in batch.decisions}) == 2
    assert {decision.metric_aggregation_policy for decision in batch.decisions} == {
        "max_amount_per_source_instrument"
    }


def test_materiality_adjudication_dedupes_same_obligation_with_varied_filing_wording(
    tmp_path: Path,
) -> None:
    rows = []
    for rank, quote in [
        (
            1,
            "Example Parent Corp. entered into a credit agreement with Example Bank, "
            "N.A. providing a $5.0 billion senior unsecured revolving credit facility. "
            "The facility is guaranteed by Example Finance LLC.",
        ),
        (
            2,
            "Example Parent Corp. reported that it entered into and maintains a "
            "$5.0 billion senior unsecured revolving credit facility under the "
            "credit agreement with Example Bank, N.A.; the facility remains "
            "guaranteed by Example Finance LLC.",
        ),
        (
            3,
            "Example Parent Corp. entered into a separate $5.0 billion senior "
            "unsecured credit agreement with Different Bank, N.A. guaranteed by "
            "Example Finance LLC.",
        ),
    ]:
        counterparty = "Different Bank, N.A." if rank == 3 else "Example Bank, N.A."
        rows.append(
            {
                "packet_id": f"packet-varied-repeat-{rank}",
                "rank": rank,
                "review_id": f"review-varied-repeat-{rank}",
                "review_group_id": f"group-varied-repeat-{rank}",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Parent Corp.",
                "counterparty": counterparty,
                "exposure_basis_usd": "5000000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: "
                    "debt_facility; notional $5,000,000,000; notional context: "
                    "transaction_principal; commitment scope: "
                    "specific_transaction_commitment; guarantee scope present"
                ),
                "recommended_action": "Confirm repeated filing disclosure",
                "source_uri": f"https://www.sec.gov/example-varied-repeat-{rank}.htm",
                "source_uris": json.dumps(
                    [f"https://www.sec.gov/example-varied-repeat-{rank}.htm"]
                ),
                "content_hash": str(rank) * 64,
                "content_hashes": json.dumps([str(rank) * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": (f"https://www.sec.gov/example-varied-repeat-{rank}.htm"),
                            "content_hash": str(rank) * 64,
                            "document_id": f"example-varied-repeat-{rank}.htm",
                            "snippet": quote,
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

    assert batch.summary.approved_for_metric_use == 3
    assert batch.summary.approved_row_supported_amount_usd == 15_000_000_000
    assert batch.summary.final_metric_supported_amount_usd == 10_000_000_000
    assert batch.summary.final_metric_group_count == 2
    assert len({decision.metric_group_id for decision in batch.decisions}) == 3


def test_materiality_adjudication_dedupes_strict_cross_filing_note_repeat(
    tmp_path: Path,
) -> None:
    rows = []
    for rank, accession, counterparty, quote in [
        (
            1,
            "000000000000000101",
            "underwriters",
            "Example Notes Corp. entered into an underwriting agreement for "
            "$1.25 billion aggregate principal amount of its 5.150% senior "
            "notes due 2034.",
        ),
        (
            2,
            "000000000000000102",
            "trustee",
            "The indenture governs Example Notes Corp.'s $1.25 billion "
            "aggregate principal amount of 5.150% senior notes due 2034.",
        ),
    ]:
        uri = f"https://www.sec.gov/Archives/edgar/data/1234/{accession}/notes-{rank}.htm"
        rows.append(
            {
                "packet_id": f"packet-strict-cross-filing-{rank}",
                "rank": rank,
                "review_id": f"review-strict-cross-filing-{rank}",
                "review_group_id": f"group-strict-cross-filing-{rank}",
                "priority": "high",
                "category": "capital",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Notes Corp.",
                "counterparty": counterparty,
                "exposure_basis_usd": "1250000000",
                "reason": (
                    "debt-like deal type: bond; notional $1,250,000,000; "
                    "notional context: transaction_principal; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm repeated cross-filing note disclosure",
                "source_uri": uri,
                "source_uris": json.dumps([uri]),
                "content_hash": str(rank) * 64,
                "content_hashes": json.dumps([str(rank) * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": uri,
                            "content_hash": str(rank) * 64,
                            "document_id": f"notes-{rank}.htm",
                            "snippet": quote,
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
    assert batch.summary.approved_row_supported_amount_usd == 2_500_000_000
    assert batch.summary.final_metric_supported_amount_usd == 1_250_000_000
    assert batch.summary.final_metric_group_count == 1
    assert len({decision.metric_group_id for decision in batch.decisions}) == 2


def test_materiality_adjudication_keeps_cross_filing_rows_without_coupon_and_year_match(
    tmp_path: Path,
) -> None:
    rows = []
    fixtures = [
        (
            1,
            "000000000000000201",
            "underwriters",
            "Example Split Corp. priced $1.8 billion aggregate principal amount "
            "of 7.000% senior notes due 2031.",
        ),
        (
            2,
            "000000000000000202",
            "trustee",
            "Example Split Corp. commenced an offer involving $1.8 billion "
            "aggregate principal amount of 5.000% senior notes due 2031.",
        ),
        (
            3,
            "000000000000000301",
            "administrative agent",
            "Example Coupon Corp. issued $2.0 billion aggregate principal amount "
            "of 6.000% senior notes due 2033.",
        ),
        (
            4,
            "000000000000000302",
            "noteholders",
            "Example Coupon Corp. issued another $2.0 billion aggregate principal "
            "amount of 6.000% senior notes due 2035.",
        ),
    ]
    for rank, accession, counterparty, quote in fixtures:
        amount = "1800000000" if rank <= 2 else "2000000000"
        entity = "Example Split Corp." if rank <= 2 else "Example Coupon Corp."
        uri = f"https://www.sec.gov/Archives/edgar/data/1234/{accession}/negative-{rank}.htm"
        rows.append(
            {
                "packet_id": f"packet-cross-filing-negative-{rank}",
                "rank": rank,
                "review_id": f"review-cross-filing-negative-{rank}",
                "review_group_id": f"group-cross-filing-negative-{rank}",
                "priority": "high",
                "category": "capital",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "watchlist_entity",
                "entity": entity,
                "counterparty": counterparty,
                "exposure_basis_usd": amount,
                "reason": (
                    f"debt-like deal type: bond; notional ${int(amount):,}; "
                    "notional context: transaction_principal; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Keep distinct cross-filing notes separate",
                "source_uri": uri,
                "source_uris": json.dumps([uri]),
                "content_hash": str(rank + 4) * 64,
                "content_hashes": json.dumps([str(rank + 4) * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": uri,
                            "content_hash": str(rank + 4) * 64,
                            "document_id": f"negative-{rank}.htm",
                            "snippet": quote,
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

    assert batch.summary.approved_for_metric_use == 4
    assert batch.summary.approved_row_supported_amount_usd == 7_600_000_000
    assert batch.summary.final_metric_supported_amount_usd == 7_600_000_000
    assert batch.summary.final_metric_group_count == 4


def test_materiality_adjudication_dedupes_source_instrument_and_snapshot_overlap(
    tmp_path: Path,
) -> None:
    shared_hash = "e" * 64
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-source-instrument",
                "rank": 1,
                "review_id": "review-source-instrument",
                "review_group_id": "group-source-instrument",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Parent Corp.",
                "counterparty": "Example Bank, N.A.",
                "exposure_basis_usd": "5000000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: "
                    "debt_facility; notional $5,000,000,000; notional context: "
                    "transaction_principal; commitment scope: "
                    "specific_transaction_commitment"
                ),
                "recommended_action": "Confirm source instrument",
                "source_uri": "https://www.sec.gov/example-overlap.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-overlap.htm"]),
                "content_hash": shared_hash,
                "content_hashes": json.dumps([shared_hash]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-overlap.htm",
                            "content_hash": shared_hash,
                            "document_id": "example-overlap.htm",
                            "snippet": (
                                "Example Parent Corp. entered into a credit agreement "
                                "with Example Bank, N.A., as administrative agent, "
                                "providing a $5.0 billion senior unsecured revolving "
                                "credit facility. The facility is guaranteed by "
                                "Example Finance LLC."
                            ),
                        }
                    ]
                ),
            },
            {
                "packet_id": "packet-aggregate-snapshot",
                "rank": 2,
                "review_id": "review-aggregate-snapshot",
                "review_group_id": "group-aggregate-snapshot",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Parent Corp.",
                "counterparty": "",
                "exposure_basis_usd": "5000000000",
                "reason": (
                    "notional $5,000,000,000; notional context: aggregate_commitment_snapshot"
                ),
                "recommended_action": "Persist aggregate commitment snapshot",
                "source_uri": "https://www.sec.gov/example-overlap.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-overlap.htm"]),
                "content_hash": shared_hash,
                "content_hashes": json.dumps([shared_hash]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-overlap.htm",
                            "content_hash": shared_hash,
                            "document_id": "example-overlap.htm",
                            "snippet": (
                                "As of March 31, 2026, Example Parent Corp. had "
                                "aggregate commitments of $5.0 billion that are "
                                "disclosed as a total commitments snapshot."
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

    assert batch.summary.approved_for_metric_use == 2
    assert batch.summary.approved_row_supported_amount_usd == 10_000_000_000
    assert batch.summary.final_metric_supported_amount_usd == 5_000_000_000
    assert batch.summary.final_metric_group_count == 1
    assert {decision.metric_group_id for decision in batch.decisions} == {
        f"source-instrument:hashes:{shared_hash}:amount:5000000000",
        "aggregate-obligation-snapshot:example-parent-corp:high-notional-debt-like-candidate",
    }
    assert {decision.metric_aggregation_policy for decision in batch.decisions} == {
        "max_amount_per_source_instrument",
        "latest_snapshot_per_metric_group",
    }


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


def test_materiality_adjudication_blocks_seller_side_lease_contract_revenue_snapshot(
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
                "entity": "TeraWulf Inc.",
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
    assert decision.metric_use_status == "blocked_pending_extraction"
    assert (
        "separate seller-side contracted revenue from issuer debt obligation"
        in decision.remaining_gap
    )
    assert decision.supported_amount_usd == 0
    assert batch.summary.approved_for_metric_use == 0


def test_hilton_aggregate_total_collapses_to_components(tmp_path: Path) -> None:
    content_hash = "7" * 64
    source_uri = (
        "https://www.sec.gov/Archives/edgar/data/1585689/000119312526113998/d40086dex101.htm"
    )
    component_context = (
        "PRELIMINARY STATEMENTS The Borrower has requested that the Lenders "
        "extend credit to the Borrower in the form of (i) the Initial Term "
        "Loans on the Closing Date in an initial aggregate principal amount of "
        "$7,600,000,000 and (ii) a Revolving Credit Facility in an initial "
        "aggregate principal amount of $1,000,000,000."
    )
    common = {
        "rank": 1,
        "review_id": "review-hilton",
        "review_group_id": "group-hilton",
        "priority": "critical",
        "category": "capital",
        "subcategory": "high_notional_debt_like_candidate",
        "ecosystem_relevance": "not_established",
        "entity": "Hilton Worldwide Holdings Inc.",
        "counterparty": "Deutsche Bank AG New York Branch",
        "source_uri": source_uri,
        "source_uris": json.dumps([source_uri]),
        "content_hash": content_hash,
        "content_hashes": json.dumps([content_hash]),
        "recommended_action": "Confirm component facilities",
    }
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                **common,
                "packet_id": "packet-hilton-title-aggregate",
                "exposure_basis_usd": "8850000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: "
                    "debt_facility; notional $8,850,000,000; notional context: "
                    "transaction_tranche_sum. "
                    f"{component_context}"
                ),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": source_uri,
                            "content_hash": content_hash,
                            "document_id": "d40086dex101.htm",
                            "snippet": (
                                "Among HILTON WORLDWIDE HOLDINGS INC., as Parent, "
                                "HILTON DOMESTIC OPERATING COMPANY INC., as the Borrower, "
                                "THE OTHER GUARANTORS PARTY HERETO FROM TIME TO TIME, "
                                "DEUTSCHE BANK AG NEW YORK BRANCH, as Administrative Agent, "
                                "Collateral Agent, Swing Line Lender and L/C Issuer, and "
                                "THE OTHER LENDERS PARTY HERETO FROM TIME TO TIME."
                            ),
                        }
                    ]
                ),
            },
            {
                **common,
                "packet_id": "packet-hilton-term-loan",
                "exposure_basis_usd": "7600000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: "
                    "debt_facility; notional $7,600,000,000; "
                    "collateral terms present; guarantee scope present"
                ),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": source_uri,
                            "content_hash": content_hash,
                            "document_id": "d40086dex101.htm",
                            "snippet": component_context,
                        }
                    ]
                ),
            },
            {
                **common,
                "packet_id": "packet-hilton-revolver",
                "exposure_basis_usd": "1000000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: "
                    "debt_facility; notional $1,000,000,000; "
                    "collateral terms present; guarantee scope present"
                ),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": source_uri,
                            "content_hash": content_hash,
                            "document_id": "d40086dex101.htm",
                            "snippet": component_context,
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
    aggregate = decisions["packet-hilton-title-aggregate"]
    assert aggregate.metric_use_status == "blocked_pending_extraction"
    assert (
        "split title-bound aggregate facility total from component facilities"
        in aggregate.remaining_gap
    )
    assert decisions["packet-hilton-term-loan"].metric_use_status == "approved_for_metric_use"
    assert decisions["packet-hilton-revolver"].metric_use_status == "approved_for_metric_use"
    assert batch.summary.approved_for_metric_use == 2
    assert batch.summary.approved_row_supported_amount_usd == 8_600_000_000


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
                "source_uris": json.dumps(["https://www.sec.gov/example-upb-issued-notes.htm"]),
                "content_hash": "1" * 64,
                "content_hashes": json.dumps(["1" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": ("https://www.sec.gov/example-upb-issued-notes.htm"),
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


def test_materiality_adjudication_blocks_financial_assets_as_mega_debt(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-loans-held-investment",
                "rank": 1,
                "review_id": "review-loans-held-investment",
                "review_group_id": "group-loans-held-investment",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "not_tagged",
                "entity": "Example Bank Corp.",
                "counterparty": "trustee",
                "exposure_basis_usd": "329200000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: bond; "
                    "notional $329,200,000,000; notional context: transaction_principal"
                ),
                "recommended_action": "Confirm whether amount is debt or assets",
                "source_uri": "https://www.sec.gov/example-bank-assets.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-bank-assets.htm"]),
                "content_hash": "2" * 64,
                "content_hashes": json.dumps(["2" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-bank-assets.htm",
                            "content_hash": "2" * 64,
                            "document_id": "example-bank-assets.htm",
                            "snippet": (
                                "Consolidated loans and leases held for investment "
                                "were $329.2 billion. The notes are unsecured "
                                "obligations under the indenture with the trustee."
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
    assert decision.supported_amount_usd == 0
    assert (
        "split asset, UPB, or financing-capacity disclosure from committed debt"
        in decision.remaining_gap
    )


def test_materiality_adjudication_blocks_mega_boilerplate_as_debt(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-mega-boilerplate",
                "rank": 1,
                "review_id": "review-mega-boilerplate",
                "review_group_id": "group-mega-boilerplate",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "not_tagged",
                "entity": "Example Financial Corp.",
                "counterparty": "trustee",
                "exposure_basis_usd": "156000000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: bond; "
                    "notional $156,000,000,000; notional context: transaction_principal"
                ),
                "recommended_action": "Confirm debt amount",
                "source_uri": "https://www.sec.gov/example-mega-boilerplate.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-mega-boilerplate.htm"]),
                "content_hash": "3" * 64,
                "content_hashes": json.dumps(["3" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": ("https://www.sec.gov/example-mega-boilerplate.htm"),
                            "content_hash": "3" * 64,
                            "document_id": "example-mega-boilerplate.htm",
                            "snippet": (
                                "The notes are not deposits or other obligations of a "
                                "bank and are not insured by the FDIC. The debt "
                                "securities may be senior or subordinated and may "
                                "be secured or unsecured."
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
    assert (
        "split asset, UPB, or financing-capacity disclosure from committed debt"
        in decision.remaining_gap
    )
    assert (
        "confirm mega-obligation amount is committed debt, not assets or capacity"
        in decision.remaining_gap
    )


def test_materiality_adjudication_blocks_source_backed_boilerplate_metric_use(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-forward-looking-boilerplate",
                "rank": 1,
                "review_id": "review-forward-looking-boilerplate",
                "review_group_id": "group-forward-looking-boilerplate",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "not_tagged",
                "entity": "Example Issuer",
                "counterparty": "noteholders",
                "exposure_basis_usd": "3200000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: bond; "
                    "notional $3,200,000,000; notional context: transaction_principal; "
                    "commitment scope: specific_transaction_commitment"
                ),
                "recommended_action": "Confirm debt terms",
                "source_uri": "https://www.sec.gov/example-forward-looking.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-forward-looking.htm"]),
                "content_hash": "9" * 64,
                "content_hashes": json.dumps(["9" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-forward-looking.htm",
                            "content_hash": "9" * 64,
                            "document_id": "example-forward-looking.htm",
                            "snippet": (
                                "These forward-looking statements are not guarantees of "
                                "future performance and involve risks and uncertainties."
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
    assert decision.supported_amount_usd == 0
    assert (
        "confirm source quote contains specific committed obligation terms"
        in decision.remaining_gap
    )


def test_materiality_adjudication_blocks_equity_or_mortgage_production_metric_use(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-equity-production",
                "rank": 1,
                "review_id": "review-equity-production",
                "review_group_id": "group-equity-production",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "not_tagged",
                "entity": "Example Issuer",
                "counterparty": "noteholders",
                "exposure_basis_usd": "12023000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: bond; "
                    "notional $12,023,000,000; notional context: transaction_principal; "
                    "commitment scope: specific_transaction_commitment"
                ),
                "recommended_action": "Confirm debt terms",
                "source_uri": "https://www.sec.gov/example-equity-production.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-equity-production.htm"]),
                "content_hash": "a" * 64,
                "content_hashes": json.dumps(["a" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-equity-production.htm",
                            "content_hash": "a" * 64,
                            "document_id": "example-equity-production.htm",
                            "snippet": (
                                "The bonds convert into Shares of Alibaba Health "
                                "Information Technology Limited."
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
    assert decision.supported_amount_usd == 0
    assert (
        "split equity, share, or mortgage-production disclosure from committed debt"
        in decision.remaining_gap
    )


def test_materiality_adjudication_preserves_convertible_debt_with_share_language(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-convertible-notes",
                "rank": 1,
                "review_id": "review-convertible-notes",
                "review_group_id": "group-convertible-notes",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "not_tagged",
                "entity": "Example Issuer",
                "counterparty": "noteholders",
                "exposure_basis_usd": "1500000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: bond; "
                    "notional $1,500,000,000; notional context: transaction_principal; "
                    "commitment scope: specific_transaction_commitment"
                ),
                "recommended_action": "Confirm debt terms",
                "source_uri": "https://www.sec.gov/example-convertible-notes.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-convertible-notes.htm"]),
                "content_hash": "b" * 64,
                "content_hashes": json.dumps(["b" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-convertible-notes.htm",
                            "content_hash": "b" * 64,
                            "document_id": "example-convertible-notes.htm",
                            "snippet": (
                                "The company issued senior unsecured convertible "
                                "notes with a conversion price for shares of "
                                "common stock."
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
    assert decision.supported_amount_usd == 1_500_000_000
    assert (
        "split equity, share, or mortgage-production disclosure from committed debt"
        not in decision.remaining_gap
    )


def test_materiality_adjudication_allows_source_backed_mega_credit_agreement(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-mega-credit-agreement",
                "rank": 1,
                "review_id": "review-mega-credit-agreement",
                "review_group_id": "group-mega-credit-agreement",
                "priority": "critical",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Mega Borrower Inc.",
                "counterparty": "Example Bank, N.A.",
                "exposure_basis_usd": "60000000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: "
                    "debt_facility; notional $60,000,000,000; notional context: "
                    "transaction_principal; commitment scope: "
                    "specific_transaction_commitment"
                ),
                "recommended_action": "Confirm committed mega facility",
                "source_uri": "https://www.sec.gov/example-mega-credit.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-mega-credit.htm"]),
                "content_hash": "4" * 64,
                "content_hashes": json.dumps(["4" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-mega-credit.htm",
                            "content_hash": "4" * 64,
                            "document_id": "example-mega-credit.htm",
                            "snippet": (
                                "Example Mega Borrower Inc. entered into a credit "
                                "agreement with Example Bank, N.A., as administrative "
                                "agent, providing a $60.0 billion senior secured term "
                                "loan facility. The facility matures in 2030, bears "
                                "interest at SOFR plus a margin, is secured by "
                                "substantially all assets, and is guaranteed by "
                                "subsidiary guarantors."
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
    assert decision.supported_amount_usd == 60_000_000_000
    assert decision.remaining_gap == ""


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
                "source_uris": json.dumps(["https://www.sec.gov/example-unsecured-facility.htm"]),
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
                "source_uris": json.dumps(["https://www.sec.gov/example-security-documents.htm"]),
                "content_hash": "d" * 64,
                "content_hashes": json.dumps(["d" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-security-documents.htm",
                            "content_hash": "d" * 64,
                            "document_id": "example-security-documents.htm",
                            "snippet": (
                                '"Loan Documents" means this Agreement, the Security '
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
    long_intro = "The company described background liquidity and related offering details. " * 14
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
                "source_uris": json.dumps(["https://www.sec.gov/example-late-secured-term.htm"]),
                "content_hash": "e" * 64,
                "content_hashes": json.dumps(["e" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-late-secured-term.htm",
                            "content_hash": "e" * 64,
                            "document_id": "example-late-secured-term.htm",
                            "snippet": (
                                long_intro + "The refinancing replaced prior loans with a term "
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
                "source_uris": json.dumps(["https://www.sec.gov/example-first-mortgage-bond.htm"]),
                "content_hash": "f" * 64,
                "content_hashes": json.dumps(["f" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": ("https://www.sec.gov/example-first-mortgage-bond.htm"),
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


def test_materiality_adjudication_treats_first_lien_notes_as_collateral_scope(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-first-lien-notes",
                "rank": 1,
                "review_id": "review-first-lien-notes",
                "review_group_id": "group-first-lien-notes",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Issuer Inc.",
                "counterparty": "noteholders",
                "exposure_basis_usd": "1730000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: bond; "
                    "notional $1,730,000,000; notional context: transaction_principal; "
                    "commitment scope: specific_transaction_commitment"
                ),
                "recommended_action": "Confirm lien-rank collateral scope",
                "source_uri": "https://www.sec.gov/example-first-lien-notes.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-first-lien-notes.htm"]),
                "content_hash": "d" * 64,
                "content_hashes": json.dumps(["d" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-first-lien-notes.htm",
                            "content_hash": "d" * 64,
                            "document_id": "example-first-lien-notes.htm",
                            "snippet": (
                                "The issuer commenced an offering of $1,730 million "
                                "aggregate principal amount of first lien notes due 2031. "
                                "The notes will be guaranteed by each subsidiary guarantor."
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
    assert "first lien notes" in decision.evidence_quote.lower(), decision
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
                            "source_uri": ("https://www.sec.gov/example-mortgage-bond-summary.htm"),
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
    assert "split aggregate disclosure from specific committed obligation" in decision.remaining_gap
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
                "source_uris": json.dumps(["https://www.sec.gov/example-mortgage-bond-shelf.htm"]),
                "content_hash": "2" * 64,
                "content_hashes": json.dumps(["2" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": ("https://www.sec.gov/example-mortgage-bond-shelf.htm"),
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
    assert "split aggregate disclosure from specific committed obligation" in decision.remaining_gap
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
                "source_uris": json.dumps(["https://www.sec.gov/example-term-note-reference.htm"]),
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


def test_materiality_adjudication_keeps_physical_queue_rows_out_of_metric_use(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-physical-queue-metric",
                "rank": 1,
                "review_id": "review-physical-queue-metric",
                "review_group_id": "group-physical-queue-metric",
                "priority": "high",
                "category": "physical",
                "subcategory": "queue_project_match",
                "ecosystem_relevance": "physical_execution",
                "entity": "Example Data Center LLC",
                "counterparty": "Example Data Center LLC",
                "exposure_basis_usd": "10000000000",
                "reason": (
                    "pending queue-to-project match; match status: strong_match; capacity_mw 1000"
                ),
                "recommended_action": "Confirm queue linkage",
                "source_uri": "https://example.org/interconnection-queue.csv",
                "source_uris": json.dumps(["https://example.org/interconnection-queue.csv"]),
                "content_hash": "b" * 64,
                "content_hashes": json.dumps(["b" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://example.org/interconnection-queue.csv",
                            "content_hash": "b" * 64,
                            "document_id": "interconnection-queue.csv",
                            "snippet": (
                                "Interconnection queue project for Example Data Center LLC "
                                "shows 1000 MW planned capacity."
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
    assert batch.summary.approved_for_metric_use == 0


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


def test_materiality_adjudication_blocks_resale_registration_metric_use(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-resale-registration",
                "rank": 1,
                "review_id": "review-resale-registration",
                "review_group_id": "group-resale-registration",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Issuer Inc.",
                "counterparty": "",
                "exposure_basis_usd": "1000000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: bond; "
                    "notional $1,000,000,000; notional context: transaction_principal"
                ),
                "recommended_action": "Confirm final offering terms",
                "source_uri": "https://www.sec.gov/example-resale-registration.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-resale-registration.htm"]),
                "content_hash": "d" * 64,
                "content_hashes": json.dumps(["d" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": ("https://www.sec.gov/example-resale-registration.htm"),
                            "content_hash": "d" * 64,
                            "document_id": "example-resale-registration.htm",
                            "snippet": (
                                "We will not receive any proceeds from the sale of "
                                "securities by the selling securityholders. The selling "
                                "securityholders may offer these securities from time to time."
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
    assert "distinguish resale registration from committed financing" in decision.remaining_gap
    assert decision.metric_use_status == "blocked_pending_extraction"


def test_materiality_adjudication_does_not_block_primary_note_offering_as_resale(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-primary-note-with-registration-wrapper",
                "rank": 1,
                "review_id": "review-primary-note-with-registration-wrapper",
                "review_group_id": "group-primary-note-with-registration-wrapper",
                "priority": "high",
                "category": "capital",
                "subcategory": "high_notional_debt_like_candidate",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Issuer Inc.",
                "counterparty": "noteholders",
                "exposure_basis_usd": "1000000000",
                "reason": (
                    "pending adjudication status: pending; debt-like deal type: bond; "
                    "notional $1,000,000,000; notional context: transaction_principal; "
                    "commitment scope: specific_transaction_commitment"
                ),
                "recommended_action": "Confirm maturity and pricing terms",
                "source_uri": "https://www.sec.gov/example-primary-note.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-primary-note.htm"]),
                "content_hash": "e" * 64,
                "content_hashes": json.dumps(["e" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-primary-note.htm",
                            "content_hash": "e" * 64,
                            "document_id": "example-primary-note.htm",
                            "snippet": (
                                "Filed pursuant to a registration statement. The company "
                                "issued $1,000,000,000 aggregate principal amount of "
                                "4.50% senior notes due 2035 under an indenture. "
                                "A selling securityholder may sell other registered "
                                "securities covered by the prospectus."
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
    assert "distinguish resale registration" not in decision.remaining_gap
    assert decision.metric_use_status == "approved_for_metric_use"


def test_materiality_adjudication_blocks_contract_resale_registration_metric_use(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-contract-resale-registration",
                "rank": 1,
                "review_id": "review-contract-resale-registration",
                "review_group_id": "group-contract-resale-registration",
                "priority": "high",
                "category": "contract",
                "subcategory": "tranche_counterparty",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Issuer Inc.",
                "counterparty": "",
                "exposure_basis_usd": "2100000000",
                "reason": (
                    "pending contract tranche review; tranche: Notes; "
                    "notional $2,100,000,000; collateral terms present"
                ),
                "recommended_action": "Confirm final note offering terms",
                "source_uri": "https://www.sec.gov/example-contract-resale.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-contract-resale.htm"]),
                "content_hash": "f" * 64,
                "content_hashes": json.dumps(["f" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-contract-resale.htm",
                            "content_hash": "f" * 64,
                            "document_id": "example-contract-resale.htm",
                            "snippet": (
                                "We or the selling securityholders may offer and sell these "
                                "securities through underwriters, brokers, dealers or agents, "
                                "or directly to purchasers on a continuous or delayed basis."
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
    assert "distinguish resale registration from committed financing" in decision.remaining_gap
    assert decision.metric_use_status == "blocked_pending_extraction"


def test_materiality_adjudication_does_not_block_contract_primary_note_issuance_as_resale(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-contract-primary-note-issuance",
                "rank": 1,
                "review_id": "review-contract-primary-note-issuance",
                "review_group_id": "group-contract-primary-note-issuance",
                "priority": "high",
                "category": "contract",
                "subcategory": "tranche_counterparty",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Issuer Inc.",
                "counterparty": "noteholders",
                "exposure_basis_usd": "2100000000",
                "reason": (
                    "pending contract tranche review; tranche: Notes; "
                    "notional $2,100,000,000; collateral terms present"
                ),
                "recommended_action": "Confirm final note offering terms",
                "source_uri": "https://www.sec.gov/example-contract-note.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-contract-note.htm"]),
                "content_hash": "9" * 64,
                "content_hashes": json.dumps(["9" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-contract-note.htm",
                            "content_hash": "9" * 64,
                            "document_id": "example-contract-note.htm",
                            "snippet": (
                                "The issuer completed an offering of $2,100,000,000 "
                                "aggregate principal amount of 5.25% senior notes due "
                                "2034 issued under an indenture. A selling securityholder "
                                "may sell other registered securities under a separate "
                                "prospectus."
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
    assert "distinguish resale registration" not in decision.remaining_gap
    assert decision.metric_use_status == "approved_for_metric_use"


def test_materiality_adjudication_prefers_primary_note_snippet_over_resale_wrapper(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-contract-note-with-separate-resale-wrapper",
                "rank": 1,
                "review_id": "review-contract-note-with-separate-resale-wrapper",
                "review_group_id": "group-contract-note-with-separate-resale-wrapper",
                "priority": "high",
                "category": "contract",
                "subcategory": "tranche_counterparty",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Nebius Group N.V.",
                "counterparty": "U.S. Bank Trust Company",
                "exposure_basis_usd": "3162500000",
                "reason": (
                    "pending contract tranche review; tranche: Convertible Notes; "
                    "notional $3,162,500,000; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm final note offering terms",
                "source_uri": "https://www.sec.gov/nebius-notes.htm",
                "source_uris": json.dumps(["https://www.sec.gov/nebius-notes.htm"]),
                "content_hash": "a" * 64,
                "content_hashes": json.dumps(["a" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/nebius-notes.htm",
                            "content_hash": "a" * 64,
                            "document_id": "nebius-notes.htm",
                            "snippet": (
                                "Nebius Group offered and issued an aggregate of "
                                "$3,162,500,000 in convertible notes, including "
                                "$1,581,250,000 aggregate principal amount of "
                                "1.00% convertible notes due 2030 and "
                                "$1,581,250,000 aggregate principal amount of "
                                "2.75% convertible notes due 2032. The notes were "
                                "issued pursuant to indentures with U.S. Bank "
                                "Trust Company."
                            ),
                        },
                        {
                            "source_uri": "https://www.sec.gov/nebius-notes.htm",
                            "content_hash": "a" * 64,
                            "document_id": "nebius-notes.htm",
                            "snippet": (
                                "We will not receive any proceeds from the sale of "
                                "ordinary shares by the selling securityholders. "
                                "The selling securityholders may offer these "
                                "securities from time to time."
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
    assert "distinguish resale registration" not in decision.remaining_gap
    assert decision.metric_use_status == "approved_for_metric_use"
    assert "selling securityholders" not in decision.evidence_quote
    assert "$3,162,500,000 in convertible notes" in decision.evidence_quote


def test_materiality_adjudication_prefers_public_notes_offering_over_resale_wrapper(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-public-notes-with-separate-resale-wrapper",
                "rank": 1,
                "review_id": "review-public-notes-with-separate-resale-wrapper",
                "review_group_id": "group-public-notes-with-separate-resale-wrapper",
                "priority": "high",
                "category": "contract",
                "subcategory": "tranche_counterparty",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Oracle Example Corp.",
                "counterparty": "noteholders",
                "exposure_basis_usd": "25000000000",
                "reason": (
                    "pending contract tranche review; tranche: Senior Notes; "
                    "notional $25,000,000,000; collateral terms present"
                ),
                "recommended_action": "Confirm final note offering terms",
                "source_uri": "https://www.sec.gov/oracle-notes.htm",
                "source_uris": json.dumps(["https://www.sec.gov/oracle-notes.htm"]),
                "content_hash": "b" * 64,
                "content_hashes": json.dumps(["b" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/oracle-notes.htm",
                            "content_hash": "b" * 64,
                            "document_id": "oracle-notes.htm",
                            "snippet": (
                                "The company announced a public offering of "
                                "$25 billion aggregate principal amount of "
                                "senior notes. The notes will be issued under "
                                "an indenture and will be unsecured senior "
                                "obligations."
                            ),
                        },
                        {
                            "source_uri": "https://www.sec.gov/oracle-notes.htm",
                            "content_hash": "b" * 64,
                            "document_id": "oracle-notes.htm",
                            "snippet": (
                                "This prospectus relates to the sale by selling "
                                "securityholders, and we will not receive any "
                                "proceeds from sales by selling securityholders."
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
    assert "distinguish resale registration" not in decision.remaining_gap
    assert decision.metric_use_status == "approved_for_metric_use"
    assert "will not receive any proceeds" not in decision.evidence_quote
    assert "$25 billion aggregate principal amount" in decision.evidence_quote


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
                "source_uris": json.dumps(["https://www.sec.gov/example-defined-borrower.htm"]),
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
                "source_uris": json.dumps(["https://www.sec.gov/example-together-commitment.htm"]),
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
                "source_uris": json.dumps(["https://www.sec.gov/example-na-serving-agent.htm"]),
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
                "source_uris": json.dumps(["https://www.sec.gov/example-no-with-underwriters.htm"]),
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
    assert (
        "extract named counterparty and role"
        not in decisions["packet-na-serving-agent"].remaining_gap
    )
    assert "Citibank, N.A" in decisions["packet-na-serving-agent"].risk_bearer
    assert (
        "extract named counterparty and role"
        not in decisions["packet-underwriter-representatives"].remaining_gap
    )
    assert "BofA Securities, Inc." in decisions["packet-underwriter-representatives"].risk_bearer
    assert (
        "extract named counterparty and role" not in decisions["packet-trustee-label"].remaining_gap
    )
    assert "U.S. Bank Trust Company" in decisions["packet-trustee-label"].risk_bearer
    assert (
        "extract named counterparty and role"
        not in decisions["packet-borrower-agent"].remaining_gap
    )
    assert "JPMorgan Chase Bank" in decisions["packet-borrower-agent"].risk_bearer
    assert (
        "extract named counterparty and role"
        not in decisions["packet-combined-agent-role"].remaining_gap
    )
    assert "Credit Suisse AG" in decisions["packet-combined-agent-role"].risk_bearer
    assert (
        "extract named counterparty and role"
        not in decisions["packet-no-with-underwriter-reps"].remaining_gap
    )
    assert "PNC Capital Markets LLC" in decisions["packet-no-with-underwriter-reps"].risk_bearer


def test_materiality_adjudication_infers_counterparty_from_live_role_grammar(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-bank-is-agent",
                "rank": 1,
                "review_id": "review-bank-is-agent",
                "review_group_id": "group-bank-is-agent",
                "priority": "high",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Borrower, Inc.",
                "counterparty": "",
                "exposure_basis_usd": "7420000000",
                "reason": (
                    "pending contract tranche review; tranche: Credit Facility; "
                    "notional $7,420,000,000; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm agent and lender roles",
                "source_uri": "https://www.sec.gov/example-bank-is-agent.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-bank-is-agent.htm"]),
                "content_hash": "g" * 64,
                "content_hashes": json.dumps(["g" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-bank-is-agent.htm",
                            "content_hash": "g" * 64,
                            "document_id": "example-bank-is-agent.htm",
                            "snippet": (
                                "Bank of America, N.A. is the Administrative Agent "
                                "and BofA Securities, Inc., PNC Bank, National "
                                "Association, J.P. Morgan Chase Bank, N.A. and "
                                "Barclays Bank PLC served as joint lead arrangers "
                                "for the upsized credit facility."
                            ),
                        }
                    ]
                ),
            },
            {
                "packet_id": "packet-syndication-agents",
                "rank": 2,
                "review_id": "review-syndication-agents",
                "review_group_id": "group-syndication-agents",
                "priority": "high",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example BDC, Inc.",
                "counterparty": "",
                "exposure_basis_usd": "5283000000",
                "reason": (
                    "pending contract tranche review; tranche: Revolving Credit Facility; "
                    "notional $5,283,000,000; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm syndication agents",
                "source_uri": "https://www.sec.gov/example-syndication-agents.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-syndication-agents.htm"]),
                "content_hash": "h" * 64,
                "content_hashes": json.dumps(["h" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-syndication-agents.htm",
                            "content_hash": "h" * 64,
                            "document_id": "example-syndication-agents.htm",
                            "snippet": (
                                "Bank of America, N.A. are syndication agents "
                                "with respect to the Revolving Credit Facility. "
                                "Wells Fargo Securities, LLC is the agent under "
                                "the Revolving Funding Facility."
                            ),
                        }
                    ]
                ),
            },
            {
                "packet_id": "packet-capacity-trustee",
                "rank": 3,
                "review_id": "review-capacity-trustee",
                "review_group_id": "group-capacity-trustee",
                "priority": "high",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "watchlist_entity",
                "entity": "Example Utility, Inc.",
                "counterparty": "",
                "exposure_basis_usd": "10100000000",
                "reason": (
                    "pending contract tranche review; tranche: Secured Notes; "
                    "notional $10,100,000,000; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm trustee and collateral agent",
                "source_uri": "https://www.sec.gov/example-capacity-trustee.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-capacity-trustee.htm"]),
                "content_hash": "i" * 64,
                "content_hashes": json.dumps(["i" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-capacity-trustee.htm",
                            "content_hash": "i" * 64,
                            "document_id": "example-capacity-trustee.htm",
                            "snippet": (
                                "The Bank of New York Mellon Trust Company, National "
                                "Association, in each of its capacities referenced "
                                "herein, including trustee, purchase contract agent, "
                                "collateral agent, custodial agent, securities "
                                "intermediary and paying agent, has not participated "
                                "in preparation of the prospectus."
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
    assert (
        "extract named counterparty and role" not in decisions["packet-bank-is-agent"].remaining_gap
    )
    assert decisions["packet-bank-is-agent"].risk_bearer.startswith("inferred:")
    assert "Bank" in decisions["packet-bank-is-agent"].risk_bearer
    assert (
        "extract named counterparty and role"
        not in decisions["packet-syndication-agents"].remaining_gap
    )
    assert "Bank of America, N.A" in decisions["packet-syndication-agents"].risk_bearer
    assert (
        "extract named counterparty and role"
        not in decisions["packet-capacity-trustee"].remaining_gap
    )
    assert (
        "The Bank of New York Mellon Trust Company"
        in decisions["packet-capacity-trustee"].risk_bearer
    )


def test_materiality_adjudication_blocks_malformed_comma_grouped_amount(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-malformed-comma-amount",
                "rank": 1,
                "review_id": "review-malformed-comma-amount",
                "review_group_id": "group-malformed-comma-amount",
                "priority": "critical",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "not_tagged",
                "entity": "Kadant Example Inc.",
                "counterparty": "lenders party thereto",
                "exposure_basis_usd": "40750000000",
                "reason": (
                    "pending contract tranche review; tranche: Revolving credit facility; "
                    "notional $40,750,000,000; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm malformed source amount",
                "source_uri": "https://www.sec.gov/example-malformed-comma.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-malformed-comma.htm"]),
                "content_hash": "j" * 64,
                "content_hashes": json.dumps(["j" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-malformed-comma.htm",
                            "content_hash": "j" * 64,
                            "document_id": "example-malformed-comma.htm",
                            "snippet": (
                                "The original amount of the Total Revolving Commitments "
                                "on the amendment effective date is $40750,000,000. "
                                "The agreement is among Kadant Example Inc., as "
                                "Borrower, the Lenders from time to time party "
                                "thereto, Citizens Bank, N.A., as Administrative "
                                "Agent and Multicurrency Administrative Agent."
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
    assert "reselect malformed comma-grouped amount before metric use" in decision.remaining_gap
    assert decision.metric_use_status == "blocked_pending_extraction"
    assert decision.supported_amount_usd == 0


def test_materiality_adjudication_blocks_malformed_comma_amount_in_local_source(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    source_uri = (
        "https://www.sec.gov/Archives/edgar/data/123456/000123456726000001/example-credit.htm"
    )
    source_path = (
        tmp_path
        / "data"
        / "edgar_acquisition"
        / "documents"
        / "0000123456"
        / "000123456726000001"
        / "example-credit.htm"
    )
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(
        "The Total Revolving Commitments on the amendment effective date are "
        "$40750,000,000 under the credit agreement."
    )
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-local-source-malformed-comma-amount",
                "rank": 1,
                "review_id": "review-local-source-malformed-comma-amount",
                "review_group_id": "group-local-source-malformed-comma-amount",
                "priority": "critical",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "not_tagged",
                "entity": "Kadant Example Inc.",
                "counterparty": "lenders party thereto",
                "exposure_basis_usd": "40750000000",
                "reason": (
                    "pending contract tranche review; tranche: Revolving credit facility; "
                    "notional $40,750,000,000; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm malformed source amount",
                "source_uri": source_uri,
                "source_uris": json.dumps([source_uri]),
                "content_hash": "l" * 64,
                "content_hashes": json.dumps(["l" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": source_uri,
                            "content_hash": "l" * 64,
                            "document_id": "example-credit.htm",
                            "snippet": (
                                "The agreement is among Kadant Example Inc., as "
                                "Borrower, the Lenders from time to time party "
                                "thereto, Citizens Bank, N.A., as Administrative "
                                "Agent and Multicurrency Administrative Agent."
                            ),
                        }
                    ]
                ),
            }
        ],
    )
    monkeypatch.chdir(tmp_path)

    batch = build_materiality_adjudication_decisions(
        [tmp_path],
        adjudicated_at="2026-06-01T00:00:00+00:00",
    )

    decision = batch.decisions[0]
    assert "reselect malformed comma-grouped amount before metric use" in decision.remaining_gap
    assert decision.metric_use_status == "blocked_pending_extraction"
    assert decision.supported_amount_usd == 0


def test_materiality_adjudication_allows_valid_comma_grouped_amount(
    tmp_path: Path,
) -> None:
    _write_csv(
        tmp_path / "reports" / "materiality_adjudication_packets.csv",
        [
            {
                "packet_id": "packet-valid-comma-amount",
                "rank": 1,
                "review_id": "review-valid-comma-amount",
                "review_group_id": "group-valid-comma-amount",
                "priority": "critical",
                "category": "contract",
                "subcategory": "contract_tranche_terms",
                "ecosystem_relevance": "not_tagged",
                "entity": "Valid Borrower Inc.",
                "counterparty": "lenders party thereto",
                "exposure_basis_usd": "40750000000",
                "reason": (
                    "pending contract tranche review; tranche: Revolving credit facility; "
                    "notional $40,750,000,000; collateral terms present; "
                    "guarantee scope present"
                ),
                "recommended_action": "Confirm committed facility",
                "source_uri": "https://www.sec.gov/example-valid-comma.htm",
                "source_uris": json.dumps(["https://www.sec.gov/example-valid-comma.htm"]),
                "content_hash": "k" * 64,
                "content_hashes": json.dumps(["k" * 64]),
                "evidence_snippets": json.dumps(
                    [
                        {
                            "source_uri": "https://www.sec.gov/example-valid-comma.htm",
                            "content_hash": "k" * 64,
                            "document_id": "example-valid-comma.htm",
                            "snippet": (
                                "The Borrower entered into a senior secured credit "
                                "agreement with the lenders party thereto and "
                                "Citizens Bank, N.A., as Administrative Agent. The "
                                "facility provides total revolving commitments of "
                                "$40,750,000,000 and is guaranteed by subsidiary "
                                "guarantors."
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
    assert "reselect malformed comma-grouped amount before metric use" not in decision.remaining_gap
    assert decision.metric_use_status == "approved_for_metric_use"


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
