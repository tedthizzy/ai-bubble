from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from bubble.ingestion.capital import load_capital_evidence
from bubble.ingestion.edgar.document_acquisition import (
    DealCandidate,
    EdgarAcquisitionBatch,
    acquire_edgar_documents_from_manifest,
    extract_collateral_descriptions,
    extract_counterparty_roles,
    extract_deal_candidate,
    extract_deal_notional_usd,
    extract_interest_rate,
    extract_largest_notional_usd,
    extract_maturity_date,
    normalize_document_text,
)
from bubble.models.base import DealType

if TYPE_CHECKING:
    from pathlib import Path


def _write_manifest(path: Path) -> None:
    rows = [
        {
            "cik": "0000000123",
            "company_name": "Example AI Infrastructure Corp",
            "ticker": "AIDC",
            "form": "8-K",
            "accession_number": "0000000000-26-000002",
            "filing_date": "2026-04-10",
            "items": "1.01|2.03|9.01",
            "primary_document": "credit-agreement.htm",
            "document_type": "exhibit",
            "parent_primary_document": "form8k.htm",
            "primary_document_description": "Material definitive agreement - data center credit agreement",
            "filing_url": "https://www.sec.gov/Archives/edgar/data/123/000000000026000002/credit-agreement.htm",
            "relevance_score": "165",
            "relevance_reasons": "form:8-K|item:2.03:direct financial obligation|keyword:credit agreement",
        },
        {
            "cik": "0000000123",
            "company_name": "Example AI Infrastructure Corp",
            "ticker": "AIDC",
            "form": "8-K",
            "accession_number": "0000000000-26-000001",
            "filing_date": "2026-01-01",
            "items": "8.01",
            "primary_document": "minor-event.htm",
            "document_type": "primary",
            "parent_primary_document": "",
            "primary_document_description": "Minor event",
            "filing_url": "https://www.sec.gov/Archives/edgar/data/123/000000000026000001/minor-event.htm",
            "relevance_score": "20",
            "relevance_reasons": "form:8-K",
        },
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_manifest_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _assert_credit_acquisition_summary(batch: EdgarAcquisitionBatch) -> None:
    assert batch.summary.manifest_rows == 2
    assert batch.summary.documents_attempted == 1
    assert batch.summary.documents_downloaded == 1
    assert batch.summary.deal_candidates == 1
    assert batch.summary.tranche_candidates == 1
    assert batch.summary.workers == 1
    assert batch.summary.sec_requests_per_second == 7.5
    assert batch.summary.sec_domain_concurrency == 5
    assert batch.summary.retry_attempts == 5
    assert batch.summary.resume_enabled is True


def _assert_credit_candidate(candidate: DealCandidate) -> None:
    assert candidate.deal_type == DealType.DEBT_FACILITY
    assert candidate.notional_amount_usd == 1_500_000_000
    assert candidate.maturity_date and candidate.maturity_date.isoformat() == "2028-06-30"
    assert candidate.counterparty_roles["borrower"] == ["Example AI Infrastructure Corp"]
    assert candidate.counterparty_roles["lender"] == ["lenders party thereto"]
    assert candidate.counterparty_roles["administrative_agent"] == ["JPMorgan Chase Bank, N.A."]
    assert candidate.counterparty_roles["financier"] == ["JPMorgan Chase Bank, N.A."]
    assert candidate.counterparty_roles["guarantor"] == ["Example Parent LLC"]
    assert candidate.guarantees == ["Example Parent LLC"]
    assert candidate.collateral
    assert candidate.is_non_recourse is True
    assert candidate.key_terms["interest_rate"] == 0.0725
    assert candidate.key_terms["non_recourse"] is True
    assert candidate.key_terms["off_balance_sheet"] is True
    assert candidate.key_terms["notional_context_kind"] == "transaction_facility"
    assert candidate.key_terms["counterparty_extraction_status"] == "role_extracted"
    assert candidate.key_terms["document_type"] == "exhibit"
    assert candidate.key_terms["parent_primary_document"] == "form8k.htm"
    assert candidate.key_terms["requires_llm_adjudication"] is True


def test_acquire_edgar_documents_writes_raw_docs_inventory_and_deal_candidates(tmp_path: Path):
    manifest = tmp_path / "manifest.csv"
    _write_manifest(manifest)
    html = b"""
    <html><body>
    <h1>Credit Agreement</h1>
    This CREDIT AGREEMENT among Example AI Infrastructure Corp, as Borrower,
    the lenders party thereto, and JPMorgan Chase Bank, N.A., as Administrative Agent,
    provides a $1.5 billion senior secured term loan facility for a data center project.
    The term loan matures on June 30, 2028.
    Loans bear interest at 7.25% per annum.
    The obligations are non-recourse and secured by first-priority liens on
    substantially all data center collateral. Example Parent LLC, as Guarantor,
    guarantees the obligations.
    </body></html>
    """

    calls: list[str] = []

    def fake_fetch(url: str) -> bytes:
        calls.append(url)
        return html

    batch = acquire_edgar_documents_from_manifest(
        manifest,
        output_dir=tmp_path / "acquired",
        fetch_bytes=fake_fetch,
        max_workers=12,
        sec_requests_per_second=7.5,
        sec_domain_concurrency=5,
        retry_attempts=5,
    )

    assert calls == [
        "https://www.sec.gov/Archives/edgar/data/123/000000000026000002/credit-agreement.htm"
    ]
    _assert_credit_acquisition_summary(batch)

    document = batch.documents[0]
    assert document.local_path.endswith(
        "documents/0000000123/000000000026000002/credit-agreement.htm"
    )
    assert document.document_type == "exhibit"
    assert document.parent_primary_document == "form8k.htm"
    assert (tmp_path / "acquired" / "deals.csv").exists()
    assert (tmp_path / "acquired" / "edgar_document_inventory.csv").exists()
    assert (tmp_path / "acquired" / "tranches.csv").exists()

    candidate = batch.deal_candidates[0]
    _assert_credit_candidate(candidate)

    capital_batch = load_capital_evidence(tmp_path / "acquired")
    assert len(capital_batch.deals) == 1
    assert capital_batch.deals[0].provenance.source_uri == calls[0]
    assert capital_batch.deals[0].deal_type == DealType.DEBT_FACILITY
    assert len(capital_batch.deals[0].debt_tranches) == 1
    assert capital_batch.deals[0].debt_tranches[0].notional_usd == 1_500_000_000
    assert capital_batch.deals[0].debt_tranches[0].interest_rate == 0.0725
    assert capital_batch.deals[0].debt_tranches[0].maturity.isoformat() == "2028-06-30"
    assert capital_batch.deals[0].is_non_recourse is True
    assert capital_batch.deals[0].guarantees == ["Example Parent LLC"]
    assert capital_batch.deals[0].counterparty_roles["administrative_agent"] == [
        "JPMorgan Chase Bank, N.A."
    ]


def test_acquire_edgar_documents_resume_reuses_downloaded_doc(tmp_path: Path):
    manifest = tmp_path / "manifest.csv"
    _write_manifest(manifest)
    html = b"<html><body>Credit Agreement for a $10 million facility.</body></html>"
    calls = 0

    def fake_fetch(_url: str) -> bytes:
        nonlocal calls
        calls += 1
        return html

    first = acquire_edgar_documents_from_manifest(
        manifest,
        output_dir=tmp_path / "acquired",
        fetch_bytes=fake_fetch,
    )
    second = acquire_edgar_documents_from_manifest(
        manifest,
        output_dir=tmp_path / "acquired",
        fetch_bytes=fake_fetch,
    )

    assert calls == 1
    assert first.summary.documents_resumed == 0
    assert second.summary.documents_resumed == 1


def test_edgar_acquisition_outputs_can_merge_delta_rows(tmp_path: Path):
    first_manifest = tmp_path / "first_manifest.csv"
    second_manifest = tmp_path / "second_manifest.csv"
    base_row = {
        "cik": "0000000123",
        "company_name": "Example AI Infrastructure Corp",
        "ticker": "AIDC",
        "form": "8-K",
        "filing_date": "2026-04-10",
        "items": "1.01|2.03|9.01",
        "document_type": "exhibit",
        "parent_primary_document": "form8k.htm",
        "primary_document_description": "Material definitive agreement - data center credit agreement",
        "relevance_score": "165",
        "relevance_reasons": "form:8-K|item:2.03:direct financial obligation|keyword:credit agreement",
    }
    _write_manifest_rows(
        first_manifest,
        [
            {
                **base_row,
                "accession_number": "0000000000-26-000001",
                "primary_document": "credit-a.htm",
                "filing_url": "https://www.sec.gov/Archives/edgar/data/123/000000000026000001/credit-a.htm",
            }
        ],
    )
    _write_manifest_rows(
        second_manifest,
        [
            {
                **base_row,
                "accession_number": "0000000000-26-000002",
                "primary_document": "credit-b.htm",
                "filing_url": "https://www.sec.gov/Archives/edgar/data/123/000000000026000002/credit-b.htm",
            }
        ],
    )

    html = b"""
    <html><body>
    CREDIT AGREEMENT among Example AI Infrastructure Corp, as Borrower,
    the lenders party thereto, and JPMorgan Chase Bank, N.A., as Administrative Agent,
    provides a $1.5 billion senior secured term loan facility. The term loan matures
    on June 30, 2028.
    </body></html>
    """

    def fake_fetch(_url: str) -> bytes:
        return html

    acquire_edgar_documents_from_manifest(
        first_manifest,
        output_dir=tmp_path / "acquired",
        fetch_bytes=fake_fetch,
    )
    delta = acquire_edgar_documents_from_manifest(
        second_manifest,
        output_dir=tmp_path / "acquired",
        fetch_bytes=fake_fetch,
        write_outputs=False,
    )
    delta.write_outputs(tmp_path / "acquired", merge_existing=True)

    with (tmp_path / "acquired" / "edgar_document_inventory.csv").open(newline="") as f:
        inventory_rows = list(csv.DictReader(f))
    with (tmp_path / "acquired" / "deals.csv").open(newline="") as f:
        deal_rows = list(csv.DictReader(f))

    assert len(inventory_rows) == 2
    assert len(deal_rows) == 2
    assert {row["primary_document"] for row in inventory_rows} == {
        "credit-a.htm",
        "credit-b.htm",
    }


def test_document_text_and_term_extractors_handle_common_sec_language():
    text = normalize_document_text(
        b"<html><body><p>Indenture for $750 million aggregate principal amount of notes due March 1, 2029.</p></body></html>"
    )

    assert "Indenture" in text
    assert extract_largest_notional_usd(text) == 750_000_000
    assert extract_maturity_date(text) and extract_maturity_date(text).isoformat() == "2029-03-01"
    assert extract_interest_rate("The Notes bear interest at 5.875% per annum.") == 0.05875
    assert extract_interest_rate("The 2032 notes bear interest at 1.00% per annum.") == 0.01
    assert (
        extract_interest_rate("Borrowings accrue interest at SOFR plus 2.75% per annum.") == 0.0275
    )
    assert extract_interest_rate("Withholding may apply at a rate of 25% under tax rules.") is None
    assert extract_interest_rate("The notes bear interest at 25.00% per annum.") is None
    assert extract_collateral_descriptions(
        "The facility is senior secured and secured by first-priority liens on collateral."
    )


def test_deal_notional_extractor_ignores_aum_and_selects_contract_amount():
    text = (
        "As of December 31, 2025, we had total Assets Under Management (AUM) of "
        "$938.4 billion. We issued $750 million aggregate principal amount of "
        "senior notes due March 1, 2029 under an indenture."
    )

    assert extract_largest_notional_usd(text) == 938_400_000_000
    assert extract_deal_notional_usd(text, deal_type=DealType.BOND) == 750_000_000


def test_deal_notional_extractor_returns_none_without_deal_amount_context():
    text = (
        "Credit agreement risk factors are described below. As of September 30, 2025, "
        "the issuer had estimated total Assets Under Management (AUM) of approximately "
        "$908 billion."
    )

    assert extract_largest_notional_usd(text) == 908_000_000_000
    assert extract_deal_notional_usd(text, deal_type=DealType.DEBT_FACILITY) is None


def test_deal_candidate_marks_aggregate_lease_obligation_notional(tmp_path: Path):
    candidate = extract_deal_candidate(
        {
            "cik": "0000000123",
            "company_name": "Example Cloud Inc.",
            "form": "424B5",
            "accession_number": "0000000000-26-000011",
            "primary_document": "prospectus.htm",
            "document_type": "primary",
            "filing_url": "https://www.sec.gov/Archives/edgar/data/123/000000000026000011/prospectus.htm",
            "relevance_score": "160",
        },
        (
            "This prospectus includes senior notes language. We have data centers that "
            "have not yet commenced with future lease payments of $75.6 billion, "
            "that are not yet recorded on our consolidated balance sheets."
        ),
        "hash",
        tmp_path / "prospectus.htm",
    )

    assert candidate
    assert candidate.deal_type == DealType.LEASE
    assert candidate.notional_amount_usd == 75_600_000_000
    assert candidate.key_terms["notional_context_kind"] == "aggregate_lease_obligation"
    assert "notional_context:aggregate_lease_obligation" in candidate.key_terms["agreement_reasons"]


def test_deal_notional_extractor_rejects_rpo_fundraising_outstanding_and_snapshot_debt():
    assert (
        extract_deal_notional_usd(
            "Q2 Remaining Performance Obligations $523 billion, up 438% in USD.",
            deal_type=DealType.DEBT_FACILITY,
        )
        is None
    )
    assert (
        extract_deal_notional_usd(
            "The increase of $138.1 billion was primarily driven by commitments to our drawdown funds.",
            deal_type=DealType.DEBT_FACILITY,
        )
        is None
    )
    assert (
        extract_deal_notional_usd(
            "As of March 29, 2025, we had $92.2 billion of unsecured senior notes and "
            "$6.0 billion of unsecured short-term promissory notes outstanding.",
            deal_type=DealType.BOND,
        )
        is None
    )
    assert (
        extract_deal_notional_usd(
            "As of November 2, 2025, the issuer had approximately $60,587 million "
            "aggregate principal amount of indebtedness for borrowed money.",
            deal_type=DealType.DEBT_FACILITY,
        )
        is None
    )
    assert (
        extract_deal_notional_usd(
            "As of November 2, 2025, (i) the issuer had approximately $60,587 million "
            "aggregate principal amount of",
            deal_type=DealType.DEBT_FACILITY,
        )
        is None
    )
    assert (
        extract_deal_notional_usd(
            "The issuer had approximately $59,786 million aggregate principal amount "
            "of indebtedness for borrowed money.",
            deal_type=DealType.DEBT_FACILITY,
        )
        is None
    )
    assert (
        extract_deal_notional_usd(
            "As of June 30, 2025, our subsidiaries had approximately $45.7 billion "
            "aggregate principal amount of",
            deal_type=DealType.DEBT_FACILITY,
        )
        is None
    )
    assert (
        extract_deal_notional_usd(
            "As of September 30, 2025, the company and its subsidiaries had total "
            "consolidated indebtedness of $72.7 billion principal amount.",
            deal_type=DealType.BOND,
        )
        is None
    )
    assert (
        extract_deal_notional_usd(
            "Capital expenditures, including principal payments on finance leases, were "
            "$72.22 billion for the year ended December 31, 2025.",
            deal_type=DealType.LEASE,
        )
        is None
    )
    assert (
        extract_deal_notional_usd(
            "We expect the prospective issuance of $25 billion aggregate principal "
            "amount of notes being offered in the notes offering.",
            deal_type=DealType.BOND,
        )
        == 25_000_000_000
    )


def test_periodic_primary_reports_are_not_treated_as_agreement_candidates(tmp_path: Path):
    candidate = extract_deal_candidate(
        {
            "cik": "0000320193",
            "company_name": "Apple Inc.",
            "form": "10-K",
            "accession_number": "0000320193-25-000079",
            "primary_document": "aapl-20250927.htm",
            "document_type": "primary",
            "filing_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm",
            "relevance_score": "110",
        },
        "Senior notes due May 6, 2044. Aggregate principal amount $100 billion.",
        "hash",
        tmp_path / "aapl-20250927.htm",
    )

    assert candidate is None


def test_bond_agreement_extracts_issuer_trustee_and_noteholder_roles(tmp_path: Path):
    candidate = extract_deal_candidate(
        {
            "cik": "0000000123",
            "company_name": "Example Issuer Inc.",
            "form": "8-K",
            "accession_number": "0000000000-26-000010",
            "items": "8.01|9.01",
            "primary_document": "ex4-1.htm",
            "document_type": "exhibit",
            "filing_url": "https://www.sec.gov/Archives/edgar/data/123/000000000026000010/ex4-1.htm",
            "relevance_score": "160",
        },
        (
            "Indenture by and between Example Issuer Inc., as Issuer, and "
            "U.S. Bank Trust Company, National Association, as Trustee, for "
            "$750 million aggregate principal amount of senior notes due March 1, 2029."
        ),
        "hash",
        tmp_path / "ex4-1.htm",
    )

    assert candidate
    assert candidate.deal_type == DealType.BOND
    assert candidate.counterparty_roles["issuer"] == ["Example Issuer Inc."]
    assert candidate.counterparty_roles["noteholder"] == ["noteholders"]
    assert candidate.counterparty_roles["trustee"] == [
        "U.S. Bank Trust Company, National Association"
    ]
    assert candidate.counterparty_roles["indenture_trustee"] == [
        "U.S. Bank Trust Company, National Association"
    ]


def test_counterparty_roles_strip_generic_lender_party_prefixes():
    roles = extract_counterparty_roles(
        deal_type=DealType.DEBT_FACILITY,
        manifest_row={},
        company_name="Example Borrower Inc.",
        text=(
            "Credit Agreement among Example Borrower Inc., the lenders from time "
            "to time party thereto and Wells Fargo Bank, N.A., as Administrative Agent."
        ),
    )

    assert roles["administrative_agent"] == ["Wells Fargo Bank, N.A."]
    assert roles["financier"] == ["Wells Fargo Bank, N.A."]
