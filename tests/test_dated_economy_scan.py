"""Dated economy scans isolate September inputs and keep provisional claims honest."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import subprocess
import sys
from datetime import date
from typing import TYPE_CHECKING

import pytest
from scripts import run_dated_entity_universe as dated_universe
from scripts.audit_sec_master_index_coverage import audit as audit_sec_index
from scripts.audit_sec_master_index_coverage import read_master
from scripts.economy_wide_signature_scan import scan_deals
from scripts.reextract_edgar_documents_offline import reextract

if TYPE_CHECKING:
    from pathlib import Path


def _csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_dated_universe_only_links_selected_sources_and_never_replaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "sept" / "tracker_records.csv"
    _csv(
        source,
        ["sponsors", "source_uri", "source_type", "retrieved_at", "content_hash"],
        [{"sponsors": "Example Compute Inc", "source_uri": "https://example.org/tracker", "source_type": "manual_curated", "retrieved_at": "2026-09-16", "content_hash": "a" * 64}],
    )
    reference = tmp_path / "sec_reference.json"
    reference.write_text(json.dumps({"fields": ["cik", "name", "ticker", "exchange"], "data": [[1234, "Example Compute Inc", "EXC", "NYSE"]]}))
    monkeypatch.setattr(dated_universe, "SOURCE_MAP", {"source_acquisition/source_rows/tracker_records.csv": source})
    monkeypatch.setattr(dated_universe, "REFERENCE", reference)
    result = dated_universe.run(
        label="test", filings_manifest=None, edgar_deals=None, capital_deals=None,
        input_base=tmp_path / "input", output_base=tmp_path / "output",
    )
    assert result["summary"]["distinct_entities"] == 1
    assert result["summary"]["cik_matches"] == 1
    assert result["summary"]["source_rows_by_path"] == {
        "source_acquisition/source_rows/tracker_records.csv": 1
    }
    assert result["included_entity_source_specs"] == ["source_acquisition/source_rows/tracker_records.csv"]
    assert result["input_files"]["source_acquisition/source_rows/tracker_records.csv"]["path"] == str(source)
    with pytest.raises(FileExistsError, match="dated run already exists"):
        dated_universe.run(
            label="test", filings_manifest=None, edgar_deals=None, capital_deals=None,
            input_base=tmp_path / "input", output_base=tmp_path / "output",
        )

    filings = tmp_path / "sept_filings.csv"
    _csv(
        filings,
        ["cik", "company_name", "source_uri", "accession_number", "provenance_content_hash"],
        [{"cik": "1234", "company_name": "Example Compute Inc", "source_uri": "https://data.sec.gov/submissions/CIK0000001234.json", "accession_number": "0000001234-26-000001", "provenance_content_hash": "b" * 64}],
    )
    with_filings = dated_universe.run(
        label="with_filings", filings_manifest=filings, edgar_deals=None, capital_deals=None,
        input_base=tmp_path / "input", output_base=tmp_path / "output",
    )
    assert with_filings["filing_rows_derived"] == 1
    assert with_filings["summary"]["source_rows_by_path"][
        "source_acquisition/source_rows/filings.csv"
    ] == 1


def test_offline_reextraction_verifies_saved_document_and_corrects_maturity(tmp_path: Path) -> None:
    raw = b"""
        CREDIT AGREEMENT among Example Compute Corp, as Borrower, and the lenders
        party thereto provides a $1.5 billion senior secured term loan facility.
        The term loan matures on June 30, 2028. The validity of this prospectus
        expires on June 11, 2026.
    """
    document = tmp_path / "credit-agreement.htm.gz"
    document.write_bytes(gzip.compress(raw))
    inventory = tmp_path / "inventory.csv"
    _csv(
        inventory,
        ["cik", "company_name", "form", "accession_number", "filing_date", "primary_document", "document_type", "parent_primary_document", "filing_url", "local_path", "content_hash", "byte_count", "relevance_score", "relevance_reasons"],
        [{
            "cik": "0000000123", "company_name": "Example Compute Corp", "form": "8-K",
            "accession_number": "0000000123-26-000001", "filing_date": "2026-09-16",
            "primary_document": "credit-agreement.htm", "document_type": "exhibit",
            "parent_primary_document": "form8k.htm", "filing_url": "https://www.sec.gov/Archives/edgar/data/123/000000012326000001/credit-agreement.htm",
            "local_path": str(document), "content_hash": hashlib.sha256(raw).hexdigest(),
            "byte_count": str(len(raw)), "relevance_score": "180", "relevance_reasons": "form:8-K",
        }],
    )
    manifest = tmp_path / "manifest.csv"
    _csv(
        manifest,
        ["filing_url", "primary_document_description", "company_name", "form", "accession_number", "primary_document", "document_type", "parent_primary_document", "relevance_score", "relevance_reasons"],
        [{
            "filing_url": "https://www.sec.gov/Archives/edgar/data/123/000000012326000001/credit-agreement.htm",
            "primary_document_description": "Credit agreement exhibit", "company_name": "Example Compute Corp",
            "form": "8-K", "accession_number": "0000000123-26-000001", "primary_document": "credit-agreement.htm",
            "document_type": "exhibit", "parent_primary_document": "form8k.htm",
            "relevance_score": "180", "relevance_reasons": "form:8-K",
        }],
    )
    output = tmp_path / "reextracted"
    report = reextract(inventory, output, manifest_csvs=[manifest], progress_interval=0)
    assert report["source_documents_verified"] == 1
    assert report["manifest_metadata_matched_rows"] == 1
    assert report["no_network_calls"] is True
    with (output / "deals.csv").open(newline="") as stream:
        deals = list(csv.DictReader(stream))
    assert len(deals) == 1
    assert deals[0]["maturity_date"] == "2028-06-30"
    assert deals[0]["title"] == "Example Compute Corp - Credit agreement exhibit"
    assert document.read_bytes() == gzip.compress(raw)
    with pytest.raises(FileExistsError, match="Refusing to replace"):
        reextract(inventory, output, manifest_csvs=[manifest], progress_interval=0)


def test_dated_scan_moves_refinancing_window_and_preserves_original_output(tmp_path: Path) -> None:
    capital = tmp_path / "capital.csv"
    edgar = tmp_path / "edgar.csv"
    tranches = tmp_path / "tranches.csv"
    entities = tmp_path / "entities.csv"
    fields = ["deal_id", "deal_type", "title", "primary_party", "counterparty_roles", "notional_amount_usd", "maturity_date", "source_uri"]
    _csv(capital, fields, [])
    _csv(
        edgar, fields,
        [
            {"deal_id": "sept-1", "deal_type": "bond", "title": "AI data center note", "primary_party": "Example Compute", "counterparty_roles": "{}", "notional_amount_usd": "1000000000", "maturity_date": "2028-05-01", "source_uri": "https://example.org/sec"},
            {"deal_id": "sept-2", "deal_type": "bond", "title": "Old offering date misparsed as maturity", "primary_party": "Example Compute", "counterparty_roles": "{}", "notional_amount_usd": "2000000000", "maturity_date": "2026-06-11", "source_uri": "https://example.org/old"},
        ],
    )
    _csv(tranches, ["deal_id", "interest_rate"], [{"deal_id": "sept-1", "interest_rate": "10"}])
    _csv(entities, ["canonical_name", "matched_cik", "matched_ticker", "mention_count"], [{"canonical_name": "Example Compute", "matched_cik": "0000001234", "matched_ticker": "EXC", "mention_count": "2"}])
    output = tmp_path / "economy_wide_fragility_map_2026-09-16"
    command = [
        sys.executable, "scripts/economy_wide_signature_scan.py",
        "--capital-deals", str(capital), "--edgar-deals", str(edgar),
        "--tranches", str(tranches), "--entities", str(entities),
        "--output-prefix", str(output), "--as-of", "2026-09-16",
        "--coverage-status", "partial",
    ]
    run = subprocess.run(command, capture_output=True, text=True, check=True)
    assert "entities scored: 1" in run.stdout
    result = json.loads(output.with_suffix(".json").read_text())
    report = output.with_suffix(".md").read_text()
    assert result["near_term_years"] == ["2026", "2027", "2028"]
    assert result["top_200"][0]["near_term_notional_usd"] == 1_000_000_000
    assert result["top_200"][0]["debt_notional_usd"] == 3_000_000_000
    assert result["top_200"][0]["ticker"] == "EXC"
    assert "machine-ranked discovery screen" in report
    assert "2026-06-13" not in report
    repeat = subprocess.run(command, capture_output=True, text=True, check=False)
    assert repeat.returncode != 0
    assert "dated output already exists" in repeat.stderr


def test_official_master_index_exposes_selected_cik_gap(tmp_path: Path) -> None:
    index = tmp_path / "master.idx"
    index.write_text(
        "Description\nCIK|Company Name|Form Type|Date Filed|Filename\n"
        "-----------------\n"
        "1234|Example Compute|10-Q|2026-08-01|edgar/data/1234/a.txt\n"
        "5678|Unselected Issuer|8-K|2026-09-01|edgar/data/5678/b.txt\n"
        "9999|Old Issuer|10-Q|2026-05-01|edgar/data/9999/c.txt\n"
    )
    selected = tmp_path / "selected.csv"
    manifested = tmp_path / "manifest.csv"
    entities = tmp_path / "entities.csv"
    _csv(selected, ["cik"], [{"cik": "1234"}])
    _csv(manifested, ["cik"], [{"cik": "1234"}])
    _csv(
        entities, ["normalized_name", "mention_count", "source_tables", "source_count"],
        [{"normalized_name": "UNSELECTED ISSUER", "mention_count": "3", "source_tables": '{"queue_records": 3}', "source_count": "1"}],
    )
    result = audit_sec_index(
        index_paths=[index], selected_cik_paths=[selected], manifest_paths=[manifested],
        entities_csv=entities, start=date(2026, 6, 1), end=date(2026, 9, 16),
    )
    assert result["unique_index_filings"] == 2
    assert result["unique_index_ciks"] == 2
    assert result["observed_filing_date_max"] == "2026-09-01"
    assert result["requested_end_date_observed"] is False
    assert result["index_ciks_absent_from_selection"] == 1
    assert result["absent_from_selection"][0]["cik"] == "0000005678"
    assert result["unselected_ai_debt_leads"][0]["lead_reasons"] == [
        "exact_name_in_dated_project_power_or_deal_source"
    ]


def test_blackwell_solar_does_not_get_gpu_sector_tag(tmp_path: Path) -> None:
    capital = tmp_path / "deals.csv"
    other = tmp_path / "empty.csv"
    fields = ["deal_id", "deal_type", "title", "primary_party", "counterparty_roles", "source_uri"]
    _csv(
        capital, fields,
        [
            {"deal_id": "ppa-1", "deal_type": "ppa", "title": "PG&E purchase with Blackwell Solar, LLC", "primary_party": "PG&E", "counterparty_roles": "{}", "source_uri": "https://example.org/solar"},
            {"deal_id": "gpu-1", "deal_type": "bond", "title": "NVIDIA Blackwell GPU capacity note", "primary_party": "Example Issuer", "counterparty_roles": "{}", "source_uri": "https://example.org/gpu"},
        ],
    )
    _csv(other, fields, [])
    scores = {}
    assert scan_deals(scores, [], capital_deals=capital, edgar_deals=other) == 2
    assert scores["pg e"].ai_tagged is False
    assert scores["example issuer"].ai_tagged is True


def test_sec_master_index_rejects_error_page(tmp_path: Path) -> None:
    bad_index = tmp_path / "master.idx"
    bad_index.write_text("Access Denied")
    with pytest.raises(ValueError, match="SEC master index header not found"):
        list(read_master(bad_index, start=date(2026, 6, 1), end=date(2026, 9, 16)))


def test_sec_master_index_reads_official_gzip_layout(tmp_path: Path) -> None:
    index = tmp_path / "master.gz"
    with gzip.open(index, "wt") as stream:
        stream.write(
            "Header\nCIK|Company Name|Form Type|Date Filed|Filename\n-----\n"
            "0000123456|Example AI Cloud|8-K|2026-09-16|edgar/data/123456/abc.txt\n"
        )
    rows = list(read_master(index, start=date(2026, 6, 1), end=date(2026, 9, 16)))
    assert len(rows) == 1
    assert rows[0]["filing_url"] == "https://www.sec.gov/Archives/edgar/data/123456/abc.txt"


def test_sec_master_index_separates_pairs_accessions_and_form_labels(tmp_path: Path) -> None:
    index = tmp_path / "master.idx"
    index.write_text(
        "Header\nCIK|Company Name|Form Type|Date Filed|Filename\n-----\n"
        "1234|Issuer A|SC 13D/A|2026-09-15|edgar/data/1234/0000001234-26-000001.txt\n"
        "1234|Issuer A|SC TO-T/A|2026-09-15|edgar/data/1234/0000001234-26-000001.txt\n"
        "5678|Cofiler B|SC 13D/A|2026-09-15|edgar/data/5678/0000001234-26-000001.txt\n"
    )
    selected = tmp_path / "selected.csv"
    _csv(selected, ["cik"], [{"cik": "1234"}])
    result = audit_sec_index(
        index_paths=[index], selected_cik_paths=[selected], manifest_paths=[selected],
        start=date(2026, 9, 15), end=date(2026, 9, 16),
    )
    assert result["raw_index_rows"] == 3
    assert result["unique_index_cik_accession_pairs"] == 2
    assert result["unique_index_accessions"] == 1
    assert result["repeat_cik_accession_rows"] == 1
    assert result["multi_form_cik_accession_pairs"][0]["additional_form"] == "SC TO-T/A"
    assert result["raw_form_counts"] == {"SC 13D/A": 2, "SC TO-T/A": 1}
