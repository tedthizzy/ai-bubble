from __future__ import annotations

import csv
import json
from typing import TYPE_CHECKING

from bubble.analysis.source_coverage import build_source_coverage_report

if TYPE_CHECKING:
    from pathlib import Path


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    assert rows
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_source_coverage_counts_real_corpora_and_missing_gaps(tmp_path: Path):
    _write_csv(
        tmp_path / "manifests" / "edgar_filing_manifest_20260601.csv",
        [
            {"cik": "0001", "company_name": "A", "form": "10-K"},
            {"cik": "0002", "company_name": "B", "form": "8-K"},
        ],
    )
    _write_csv(
        tmp_path / "edgar" / "edgar_document_inventory.csv",
        [{"cik": "0001", "company_name": "A", "content_hash": "abc"}],
    )
    _write_csv(
        tmp_path / "physical" / "projects.csv", [{"project_id": "p1", "source_uri": "tracker:p1"}]
    )
    _write_csv(tmp_path / "physical" / "queues.csv", [{"queue_id": "q1", "source_uri": "ercot:q1"}])
    _write_csv(
        tmp_path / "physical" / "equipment_records.csv",
        [
            {
                "source_id": "eia",
                "source_uri": "eia:generator",
                "Entity Name": "Generator Owner",
                "Plant Name": "Do Not Count Plant As Entity",
            }
        ],
    )
    _write_csv(
        tmp_path / "physical" / "permits.csv", [{"permit_id": "air1", "source_uri": "deq:air1"}]
    )
    _write_csv(
        tmp_path / "capital" / "deals.csv",
        [
            {
                "deal_id": "lease-1",
                "deal_type": "lease",
                "parties": "A|B",
                "source_uri": "sec:lease",
                "source_type": "sec_edgar",
            },
            {
                "deal_id": "ppa-1",
                "deal_type": "ppa",
                "parties": "A|Utility",
                "source_uri": "puc:ppa",
                "source_type": "state_puc",
            },
        ],
    )
    _write_csv(
        tmp_path / "capital" / "tranches.csv",
        [
            {
                "deal_id": "lease-1",
                "tranche_id": "primary",
                "name": "Primary tranche",
                "notional_usd": "1000000",
                "guarantors": "Guarantor LLC",
                "source_uri": "sec:lease#tranche",
                "source_type": "sec_edgar",
            }
        ],
    )
    _write_csv(
        tmp_path / "source_rows" / "lei_records.csv",
        [
            {
                "LEI": "CHILDLEI1234567890",
                "Entity_LegalName": "Child Compute LLC",
                "source_uri": "https://leidata.gleif.org/api/v1/concatenated-files/lei2/get/1/zip",
                "source_type": "gleif",
            }
        ],
    )
    _write_csv(tmp_path / "ownership_records.csv", [{"entity": "A", "owner": "Parent"}])
    _write_csv(tmp_path / "tracker_records.csv", [{"project_id": "p1", "name": "Campus"}])
    _write_csv(
        tmp_path / "compute" / "depreciation_policies.csv",
        [
            {
                "policy_id": "policy-1",
                "entity": "GPU Cloud Inc",
                "asset_class": "servers and network equipment",
                "accounting_useful_life_years": "5.5",
                "source_uri": "https://www.sec.gov/Archives/edgar/data/1/policy.htm",
                "source_type": "sec_edgar",
                "content_hash": "abc123",
            }
        ],
    )
    _write_csv(
        tmp_path / "compute" / "chip_supply_observations.csv",
        [
            {
                "observation_id": "supply-1",
                "entity": "GPU Supplier Inc",
                "gpu_generation": "BLACKWELL",
                "source_uri": "https://www.sec.gov/Archives/edgar/data/2/supply.htm",
                "source_type": "sec_edgar",
                "content_hash": "def456",
            }
        ],
    )
    _write_csv(
        tmp_path / "compute" / "economic_commitments.csv",
        [
            {
                "commitment_id": "commitment-1",
                "entity": "GPU Buyer Inc",
                "term_type": "datacenter_purchase_commitment",
                "source_uri": "https://www.sec.gov/Archives/edgar/data/3/commitments.htm",
                "source_type": "sec_edgar",
                "content_hash": "ghi789",
            }
        ],
    )
    _write_csv(
        tmp_path / "source_catalog.csv",
        [
            {
                "source_id": "sec-submissions-0001",
                "corpus": "filings",
                "source_uri": "https://data.sec.gov/submissions/CIK0000000001.json",
            },
            {
                "source_id": "pjm-q",
                "corpus": "queue_records",
                "source_uri": "https://example.com/pjm.csv",
            },
        ],
    )
    summary_path = tmp_path / "source_acquisition" / "source_catalog_acquisition.summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(
            {
                "artifacts_attempted": 3,
                "artifacts_acquired": 2,
                "errors": {"sec-submissions-0001": "missing identity"},
            }
        )
    )

    report = build_source_coverage_report([tmp_path])

    assert report.filings == 2
    assert report.entities >= 6
    assert report.source_documents == 1
    assert report.projects == 2
    assert report.queue_records == 1
    assert report.equipment_records == 1
    assert report.permit_records == 1
    assert report.lease_agreements == 1
    assert report.lei_records == 1
    assert report.ppas == 1
    assert report.ownership_records == 1
    assert report.tracker_records == 1
    assert report.compute_economics_rows == 3
    assert report.source_backed_compute_rows == 3
    assert report.depreciation_policies == 1
    assert report.chip_supply_observations == 1
    assert report.economic_commitments == 1
    assert report.extracted_deals == 2
    assert report.source_backed_deals == 2
    assert report.contract_tranches == 1
    assert report.source_backed_contract_tranches == 1
    assert report.catalog_sources == 2
    assert report.catalog_sources_by_corpus == {"filings": 1, "queue_records": 1}
    assert report.catalog_files == [str(tmp_path / "source_catalog.csv")]
    assert report.acquisition_runs == 1
    assert report.acquisition_artifacts_attempted == 3
    assert report.acquisition_artifacts_acquired == 2
    assert report.acquisition_errors == 1
    assert report.acquisition_error_sources == ["sec-submissions-0001"]
    assert "equipment_records" not in report.missing_corpora
    assert "construction_observations" not in report.missing_corpora


def test_source_coverage_does_not_count_derived_graph_outputs_as_source_rows(
    tmp_path: Path,
):
    gleif_uri = "https://leidata.gleif.org/api/v1/concatenated-files/rr/get/41249/zip"
    _write_csv(
        tmp_path / "source_acquisition" / "source_rows" / "ownership_records.csv",
        [
            {
                "Relationship_StartNode_NodeID": "child-lei",
                "Relationship_EndNode_NodeID": "parent-lei",
                "source_uri": gleif_uri,
                "content_hash": "hash-1",
            }
        ],
    )
    _write_csv(
        tmp_path / "graph" / "ownership_edges.csv",
        [
            {
                "child_id": "child-lei",
                "parent_id": "parent-lei",
                "source_uri": gleif_uri,
                "content_hash": "hash-1",
            }
        ],
    )
    _write_csv(
        tmp_path / "graph" / "ownership_nodes.csv",
        [
            {
                "node_id": "child-lei",
                "source_uris": gleif_uri,
                "content_hashes": "hash-1",
            }
        ],
    )

    report = build_source_coverage_report([tmp_path])

    assert report.ownership_records == 1
    assert report.files_by_corpus["ownership_records"] == [
        str(tmp_path / "source_acquisition" / "source_rows" / "ownership_records.csv")
    ]


def test_source_coverage_counts_unique_rows_across_edgar_manifests(tmp_path: Path):
    _write_csv(
        tmp_path / "manifests" / "edgar_filing_manifest_20260601-010000.csv",
        [
            {
                "cik": "0001",
                "company_name": "Seed A",
                "form": "8-K",
                "accession_number": "0001-26-000001",
                "primary_document": "a.htm",
            }
        ],
    )
    _write_csv(
        tmp_path / "manifests" / "edgar_filing_manifest_20260601-020000.csv",
        [
            {
                "cik": "0001",
                "company_name": "Seed A",
                "form": "8-K",
                "accession_number": "0001-26-000001",
                "primary_document": "a.htm",
            },
            {
                "cik": "0002",
                "company_name": "Delta Seed B",
                "form": "10-K",
                "accession_number": "0002-26-000001",
                "primary_document": "b.htm",
            },
        ],
    )

    report = build_source_coverage_report([tmp_path])

    assert report.filings == 2
    assert report.files_by_corpus["filings"] == [
        str(tmp_path / "manifests" / "edgar_filing_manifest_20260601-010000.csv"),
        str(tmp_path / "manifests" / "edgar_filing_manifest_20260601-020000.csv"),
    ]


def test_source_coverage_counts_ppa_corpus_as_source_backed_deals(tmp_path: Path):
    _write_csv(
        tmp_path / "source_rows" / "ppas.csv",
        [
            {
                "ID": "1",
                "Reporting_Entity_Name": "Seller LLC",
                "Counterparty_Name": "Utility Buyer",
                "source_uri": "https://data.ferc.gov/api/v1/dataset/17/",
                "source_type": "ferc",
            },
            {
                "ID": "2",
                "Entity_Name": "Generator LLC",
                "Counterparty_Name": "Load Serving Entity",
                "source_uri": "https://data.ferc.gov/api/v1/dataset/17/",
                "source_type": "ferc",
            },
        ],
    )

    report = build_source_coverage_report([tmp_path])

    assert report.ppas == 2
    assert report.source_backed_deals == 2
    assert report.deal_types == {"ppa": 2}
    assert report.entities == 4


def test_source_coverage_does_not_count_seed_or_placeholder_deals_as_source_backed(
    tmp_path: Path,
):
    _write_csv(
        tmp_path / "capital" / "deals.csv",
        [
            {
                "deal_id": "seed-lease",
                "deal_type": "lease",
                "parties": "A|B",
                "source_uri": "seed:priority-list",
                "source_type": "manual_curated",
            },
            {
                "deal_id": "placeholder-ppa",
                "deal_type": "ppa",
                "parties": "A|Utility",
                "source_uri": "placeholder:ppa",
                "source_type": "state_puc",
            },
            {
                "deal_id": "real-ppa",
                "deal_type": "ppa",
                "parties": "A|Utility",
                "source_uri": "https://data.ferc.gov/api/v1/dataset/17/",
                "source_type": "ferc",
            },
        ],
    )

    report = build_source_coverage_report([tmp_path])

    assert report.extracted_deals == 3
    assert report.source_backed_deals == 1


def test_source_coverage_dedupes_raw_ppa_and_extracted_deal(tmp_path: Path):
    _write_csv(
        tmp_path / "source_rows" / "ppas.csv",
        [
            {
                "ID": "2179",
                "Entity_Name": "Seller LLC",
                "Counterparty_Name": "Utility Buyer",
                "source_uri": "https://data.ferc.gov/api/v1/dataset/17/",
                "source_type": "ferc",
                "content_hash": "page-hash",
                "record_index": "0",
            }
        ],
    )
    _write_csv(
        tmp_path / "capital" / "deals.csv",
        [
            {
                "deal_id": "ppa:ferc:2179",
                "deal_type": "ppa",
                "parties": "Seller LLC|Utility Buyer",
                "source_uri": "https://data.ferc.gov/api/v1/dataset/17/",
                "source_type": "ferc",
                "content_hash": "page-hash",
            }
        ],
    )

    report = build_source_coverage_report([tmp_path])

    assert report.ppas == 1
    assert report.extracted_deals == 1
    assert report.source_backed_deals == 1
    assert report.deal_types == {"ppa": 1}


def test_source_coverage_excludes_obvious_test_ppa_rows_from_deal_counts(tmp_path: Path):
    _write_csv(
        tmp_path / "source_rows" / "ppas.csv",
        [
            {
                "ID": "1",
                "Entity_Name": "PRODUCTION TESTCOMPANY 7",
                "Counterparty_Name": "PRODUCTION TESTCOMPANY 7",
                "source_uri": "https://data.ferc.gov/api/v1/dataset/17/",
                "source_type": "ferc",
                "content_hash": "page-hash",
                "record_index": "0",
            }
        ],
    )

    report = build_source_coverage_report([tmp_path])

    assert report.raw_rows_by_corpus["ppas"] == 1
    assert report.ppas == 0
    assert report.source_backed_deals == 0
    assert report.deal_types == {"ppa": 0}


def test_source_coverage_dedupes_raw_and_normalized_queue_rows(tmp_path: Path):
    _write_csv(
        tmp_path / "source_rows" / "queue_records.csv",
        [
            {
                "Project Name": "Giga Texas Data Center",
                "source_uri": "https://example.com/ercot.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "queue-hash",
                "record_index": "9",
            }
        ],
    )
    _write_csv(
        tmp_path / "physical" / "queues.csv",
        [
            {
                "project_id": "tracker:giga-texas",
                "queue_id": "ercot:9",
                "source_uri": "https://example.com/ercot.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "queue-hash",
                "page_or_section": "raw/ercot.xlsx#record_index=9",
            }
        ],
    )

    report = build_source_coverage_report([tmp_path])

    assert report.queue_records == 1
    assert report.raw_rows_by_corpus["queue_records"] == 1


def test_source_coverage_counts_queue_derived_projects_as_projects(tmp_path: Path):
    _write_csv(
        tmp_path / "physical" / "queue_projects.csv",
        [
            {
                "project_id": "queue-project:abc",
                "name": "Hudson Valley Data Center",
                "source_uri": "https://example.com/nyiso.xlsx",
                "source_type": "grid_interconnection_queue",
                "content_hash": "queue-hash",
                "record_index": "120",
            }
        ],
    )

    report = build_source_coverage_report([tmp_path])

    assert report.projects == 1
    assert report.raw_rows_by_corpus["projects"] == 1
    assert report.files_by_corpus["projects"] == [str(tmp_path / "physical" / "queue_projects.csv")]


def test_source_coverage_dedupes_raw_and_normalized_permit_and_equipment_rows(
    tmp_path: Path,
):
    _write_csv(
        tmp_path / "source_rows" / "permit_records.csv",
        [
            {
                "PGM_SYS_ID": "AIR-1",
                "FACILITY_NAME": "QTS DEN1",
                "source_uri": "https://example.com/icis.zip",
                "source_type": "epa",
                "content_hash": "permit-hash",
                "record_index": "42",
            }
        ],
    )
    _write_csv(
        tmp_path / "physical" / "permits.csv",
        [
            {
                "project_id": "tracker:qts-den1",
                "permit_id": "AIR-1",
                "source_uri": "https://example.com/icis.zip",
                "source_type": "epa",
                "content_hash": "permit-hash",
                "page_or_section": "raw/icis.zip#record_index=42",
            }
        ],
    )
    _write_csv(
        tmp_path / "source_rows" / "equipment_records.csv",
        [
            {
                "Plant Name": "Equinix Fuel Cell",
                "source_uri": "https://example.com/eia.xlsx",
                "source_type": "eia",
                "content_hash": "equipment-hash",
                "record_index": "9",
            }
        ],
    )
    _write_csv(
        tmp_path / "physical" / "equipment.csv",
        [
            {
                "project_id": "tracker:equinix",
                "equipment_type": "generator",
                "source_uri": "https://example.com/eia.xlsx",
                "source_type": "eia",
                "content_hash": "equipment-hash",
                "page_or_section": "raw/eia.xlsx#record_index=9",
            }
        ],
    )

    report = build_source_coverage_report([tmp_path])

    assert report.permit_records == 1
    assert report.equipment_records == 1
    assert report.raw_rows_by_corpus["permit_records"] == 1
    assert report.raw_rows_by_corpus["equipment_records"] == 1
