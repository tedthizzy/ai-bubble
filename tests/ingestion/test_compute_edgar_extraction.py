from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from bubble.ingestion.compute.edgar_extraction import extract_compute_economics_from_edgar

if TYPE_CHECKING:
    from pathlib import Path


HASH = "b" * 64


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    assert rows
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def test_extract_compute_economics_from_edgar_writes_source_backed_rows(tmp_path: Path) -> None:
    doc = tmp_path / "nvda.htm"
    doc.write_text(
        """
        <html><body>
        <p>NVIDIA is a data center scale AI infrastructure company.</p>
        <p>Property and equipment are stated at cost less accumulated depreciation.
        Depreciation of property and equipment is computed using the straight-line method
        based on the estimated useful lives of the assets of two to seven years.</p>
        <p>Our total addressable market is approximately $2.4 trillion for AI compute.</p>
        <p>Manufacturing, supply, and capacity commitments reflect data center-scale production.
        As of April 26, 2026, these commitments were $119 billion for which $95 billion
        will be paid in the remainder of fiscal year 2027 and the remaining balance will be
        paid in fiscal years 2028 through 2031. Blackwell continued to account for shipments.</p>
        </body></html>
        """
    )
    inventory = tmp_path / "inventory.csv"
    _write_csv(
        inventory,
        [
            {
                "cik": "0001045810",
                "company_name": "NVIDIA CORP",
                "form": "10-Q",
                "accession_number": "0001045810-26-000052",
                "filing_date": "2026-05-20",
                "primary_document": "nvda.htm",
                "filing_url": "https://www.sec.gov/Archives/edgar/data/1045810/nvda.htm",
                "local_path": str(doc),
                "content_hash": HASH,
                "downloaded_at": "2026-06-01T00:00:00+00:00",
            }
        ],
    )

    summary = extract_compute_economics_from_edgar(
        inventory_csv=inventory,
        output_dir=tmp_path / "compute",
    )

    assert summary.documents_scanned == 1
    assert summary.inventory_documents == 1
    assert summary.candidate_documents == 1
    assert summary.depreciation_policies == 1
    assert summary.tam_claims == 1
    assert summary.eps_depreciation_impacts == 0
    assert summary.chip_supply_observations == 1

    policies = _read_csv(tmp_path / "compute" / "depreciation_policies.csv")
    assert policies[0]["entity"] == "NVIDIA CORP"
    assert policies[0]["accounting_useful_life_years"] == "7.0"
    assert policies[0]["source_uri"].startswith("https://www.sec.gov/")
    assert policies[0]["retrieved_at"] == "2026-06-01T00:00:00+00:00"
    assert policies[0]["content_hash"] == HASH

    tam_claims = _read_csv(tmp_path / "compute" / "tam_claims.csv")
    assert tam_claims[0]["stated_tam_usd"] == "2400000000000.0"

    supply = _read_csv(tmp_path / "compute" / "chip_supply_observations.csv")
    assert supply[0]["gpu_generation"] == "BLACKWELL"
    assert supply[0]["disclosed_purchase_commitment_usd"] == "119000000000.0"


def test_extract_compute_economics_from_edgar_extracts_mw_capacity_commitments(
    tmp_path: Path,
) -> None:
    doc = tmp_path / "cerebras_openai.htm"
    doc.write_text(
        """
        <html><body>
        <p>OpenAI develops AI models and Cerebras provides AI supercomputer services.
        OpenAI commits to purchase the Initial Capacity from Cerebras.</p>
        <p>i. 250MW of Capacity by the end of calendar year 2026 with facilities in
        no greater than redacted data centers;</p>
        <p>ii. 250MW of additional Capacity by the end of calendar year 2027
        (such that the total aggregate Capacity equals 500MW) in no greater than
        redacted data centers; and</p>
        <p>iii. 250MW of additional Capacity by the end of calendar year 2028
        (such that the total aggregate Capacity equals 750MW) in no greater than
        redacted data centers.</p>
        </body></html>
        """
    )
    inventory = tmp_path / "inventory.csv"
    _write_csv(
        inventory,
        [
            {
                "cik": "0002021728",
                "company_name": "Cerebras Systems Inc.",
                "form": "S-1",
                "accession_number": "0001628280-26-025762",
                "filing_date": "2026-04-17",
                "primary_document": "exhibit1011-sx1.htm",
                "filing_url": "https://www.sec.gov/Archives/edgar/data/2021728/exhibit1011-sx1.htm",
                "local_path": str(doc),
                "content_hash": HASH,
                "downloaded_at": "2026-06-01T00:00:00+00:00",
            }
        ],
    )

    summary = extract_compute_economics_from_edgar(
        inventory_csv=inventory,
        output_dir=tmp_path / "compute",
    )

    assert summary.documents_scanned == 1
    assert summary.candidate_documents == 1
    assert summary.chip_supply_observations == 3

    supply = _read_csv(tmp_path / "compute" / "chip_supply_observations.csv")
    assert [row["announced_mw"] for row in supply] == ["250.0", "250.0", "250.0"]
    assert [row["delivery_window"] for row in supply] == [
        "by the end of calendar year 2026",
        "by the end of calendar year 2027",
        "by the end of calendar year 2028",
    ]
    assert {row["supplier"] for row in supply} == {"Cerebras Systems Inc."}
    assert all(row["source_uri"].startswith("https://www.sec.gov/") for row in supply)


def test_extract_compute_economics_from_edgar_extracts_disclosed_eps_impacts(
    tmp_path: Path,
) -> None:
    doc = tmp_path / "meta.htm"
    doc.write_text(
        """
        <html><body>
        <p>Meta operates data center and artificial intelligence infrastructure.</p>
        <p>In January 2025, we completed an assessment of the useful lives of property
        and equipment, which resulted in an increase in the estimated useful lives of
        most servers and network assets to 5.5 years, effective January 1, 2025.
        Based on the servers and network assets placed in service as of December 31,
        2024, the financial impact of this change in estimate included a reduction in
        depreciation expense of $2.92 billion and an increase in net income of
        $2.59 billion, or $1.00 per diluted share, for the year ended December 31,
        2025.</p>
        </body></html>
        """
    )
    inventory = tmp_path / "inventory.csv"
    _write_csv(
        inventory,
        [
            {
                "cik": "0001326801",
                "company_name": "Meta Platforms, Inc.",
                "form": "10-K",
                "accession_number": "0001628280-26-003942",
                "filing_date": "2026-01-29",
                "primary_document": "meta-20251231.htm",
                "filing_url": "https://www.sec.gov/Archives/edgar/data/1326801/meta-20251231.htm",
                "local_path": str(doc),
                "content_hash": HASH,
                "downloaded_at": "2026-06-01T00:00:00+00:00",
            }
        ],
    )

    summary = extract_compute_economics_from_edgar(
        inventory_csv=inventory,
        output_dir=tmp_path / "compute",
    )

    assert summary.documents_scanned == 1
    assert summary.eps_depreciation_impacts == 1

    impacts = _read_csv(tmp_path / "compute" / "eps_depreciation_impacts.csv")
    assert impacts[0]["entity"] == "Meta Platforms, Inc."
    assert impacts[0]["fiscal_year"] == "2025"
    assert impacts[0]["disclosed_depreciation_usd"] == "2920000000.0"
    assert impacts[0]["disclosed_net_income_impact_usd"] == "2590000000.0"
    assert impacts[0]["disclosed_eps_impact_usd"] == "1.0"
    assert impacts[0]["accounting_useful_life_years"] == "5.5"
    assert impacts[0]["gpu_capex_estimate_usd"] == ""
    assert impacts[0]["impact_direction"] == "depreciation_reduction_net_income_increase"
    assert impacts[0]["source_uri"].startswith("https://www.sec.gov/")


def test_extract_compute_economics_binds_depreciation_life_to_matching_asset_class(
    tmp_path: Path,
) -> None:
    doc = tmp_path / "alphabet.htm"
    doc.write_text(
        """
        <html><body>
        <p>Alphabet operates artificial intelligence and data center infrastructure.</p>
        <p>Assets not yet in service include data center buildings and servers in the
        process of construction or assembly. Property and equipment are stated at cost
        less accumulated depreciation. Depreciation commences once assets are ready for
        their intended use and is recorded using the straight-line method over the
        estimated useful lives of the assets. We depreciate data center and office
        buildings over periods of seven to 40 years. We depreciate servers and network
        equipment generally over a period of six years. We depreciate corporate and
        other assets over periods of two to 25 years.</p>
        </body></html>
        """
    )
    inventory = tmp_path / "inventory.csv"
    _write_csv(
        inventory,
        [
            {
                "cik": "0001652044",
                "company_name": "Alphabet Inc.",
                "form": "10-K",
                "accession_number": "0001652044-26-000018",
                "filing_date": "2026-02-05",
                "primary_document": "goog-20251231.htm",
                "filing_url": "https://www.sec.gov/Archives/edgar/data/1652044/goog.htm",
                "local_path": str(doc),
                "content_hash": HASH,
                "downloaded_at": "2026-06-01T00:00:00+00:00",
            }
        ],
    )

    summary = extract_compute_economics_from_edgar(
        inventory_csv=inventory,
        output_dir=tmp_path / "compute",
    )

    assert summary.depreciation_policies == 1
    policies = _read_csv(tmp_path / "compute" / "depreciation_policies.csv")
    assert policies[0]["asset_class"] == "servers and network equipment"
    assert policies[0]["accounting_useful_life_years"] == "6.0"


def test_extract_compute_economics_binds_table_life_to_cloud_equipment_not_software(
    tmp_path: Path,
) -> None:
    doc = tmp_path / "whitefiber.htm"
    doc.write_text(
        """
        <html><body>
        <p>WhiteFiber provides AI infrastructure and cloud data center services.</p>
        <p>Property, plant, and equipment are recorded at cost and depreciated using
        the straight-line method over the estimated useful lives of the assets.
        Direct costs related to developing or obtaining software for internal use
        are capitalized as property, plant, and equipment. Capitalized software costs
        are amortized over the software's useful life when the software is placed in
        service. The estimated useful lives by asset category are: Estimated Useful
        Life Cloud service equipment 5 years Colocation service equipment 10 to
        15 years Building 30 years Leasehold improvements 15 years Purchased and
        internally developed software 1 to 5 years.</p>
        </body></html>
        """
    )
    inventory = tmp_path / "inventory.csv"
    _write_csv(
        inventory,
        [
            {
                "cik": "0002042022",
                "company_name": "WhiteFiber, Inc.",
                "form": "S-1/A",
                "accession_number": "0001213900-26-034341",
                "filing_date": "2026-03-26",
                "primary_document": "whitefiber.htm",
                "filing_url": "https://www.sec.gov/Archives/edgar/data/2042022/whitefiber.htm",
                "local_path": str(doc),
                "content_hash": HASH,
                "downloaded_at": "2026-06-01T00:00:00+00:00",
            }
        ],
    )

    summary = extract_compute_economics_from_edgar(
        inventory_csv=inventory,
        output_dir=tmp_path / "compute",
    )

    assert summary.depreciation_policies == 1
    policies = _read_csv(tmp_path / "compute" / "depreciation_policies.csv")
    assert policies[0]["asset_class"] == "data center equipment"
    assert policies[0]["accounting_useful_life_years"] == "5.0"


def test_extract_compute_economics_from_edgar_extracts_gpu_assets_and_payback_cases(
    tmp_path: Path,
) -> None:
    doc = tmp_path / "whitefiber.htm"
    doc.write_text(
        """
        <html><body>
        <p>WhiteFiber provides AI infrastructure and GPU cloud services.</p>
        <p>The economics of our business are based on costs of approximately $42,000
        for a B200 GPU that generates approximately $20,000 of revenue in year one
        at an EBITDA margin between 75% and 80%.</p>
        <p>We executed a new agreement to supply the Initial Customer 464 B200 GPUs
        for an 18 month term beginning on June 30, 2025, worth approximately
        $15 million of targeted annualized revenue assuming the GPUs operate at
        full capacity.</p>
        <p>Under another contract, we are utilizing a total of 576 H200 GPUs over a
        twenty-five month period. It represents an aggregate revenue opportunity of approximately
        $20.2 million. Concurrently, we placed a purchase order for 130 H200
        servers for approximately $30 million.</p>
        <p>A separate service order covered 10 H200 GPU servers, but did not disclose
        the number of individual GPUs.</p>
        </body></html>
        """
    )
    inventory = tmp_path / "inventory.csv"
    _write_csv(
        inventory,
        [
            {
                "cik": "0002042022",
                "company_name": "WhiteFiber, Inc.",
                "form": "S-1/A",
                "accession_number": "0001213900-25-052267",
                "filing_date": "2025-06-13",
                "primary_document": "filename1.htm",
                "filing_url": "https://www.sec.gov/Archives/edgar/data/2042022/filename1.htm",
                "local_path": str(doc),
                "content_hash": HASH,
                "downloaded_at": "2026-06-01T00:00:00+00:00",
            }
        ],
    )

    summary = extract_compute_economics_from_edgar(
        inventory_csv=inventory,
        output_dir=tmp_path / "compute",
    )

    assert summary.documents_scanned == 1
    assert summary.compute_assets == 3
    assert summary.capex_payback_cases == 3

    assets = _read_csv(tmp_path / "compute" / "compute_assets.csv")
    b200_asset = next(row for row in assets if row["gpu_generation"] == "B200")
    assert b200_asset["gpu_count"] == "464"
    assert b200_asset["original_price_per_gpu_usd"] == "42000.0"
    assert b200_asset["capex_usd"] == "19488000.0"
    assert b200_asset["source_uri"].startswith("https://www.sec.gov/")
    assert b200_asset["retrieved_at"] == "2026-06-01T00:00:00+00:00"
    assert b200_asset["content_hash"] == HASH

    h200_count_asset = next(
        row for row in assets if row["gpu_generation"] == "H200" and row["gpu_count"] == "576"
    )
    assert h200_count_asset["capex_usd"] == "30000000.0"
    h200_server_asset = next(
        row for row in assets if row["gpu_generation"] == "H200" and row["gpu_count"] == ""
    )
    assert h200_server_asset["capex_usd"] == "30000000.0"
    assert "130" in h200_server_asset["notes"]

    cases = _read_csv(tmp_path / "compute" / "capex_payback_cases.csv")
    per_gpu_case = next(
        row
        for row in cases
        if row["capex_usd"] == "42000.0" and row["annual_revenue_run_rate_usd"] == "20000.0"
    )
    assert per_gpu_case["gross_margin_pct"] == "75.0"
    assert per_gpu_case["source_type"] == "sec_edgar"

    b200_contract_case = next(row for row in cases if row["capex_usd"] == "19488000.0")
    assert b200_contract_case["annual_revenue_run_rate_usd"] == "15000000.0"
    assert b200_contract_case["contracted_revenue_usd"] == ""
    assert "Estimated capex" in b200_contract_case["notes"]

    h200_contract_case = next(row for row in cases if row["capex_usd"] == "30000000.0")
    assert h200_contract_case["contracted_revenue_usd"] == "20200000.0"
    assert h200_contract_case["annual_revenue_run_rate_usd"] == "9696000.0"
    assert h200_contract_case["source_uri"].startswith("https://www.sec.gov/")


def test_extract_compute_economics_from_edgar_uses_metadata_compute_keywords(
    tmp_path: Path,
) -> None:
    doc = tmp_path / "openai_compute.htm"
    doc.write_text(
        """
        <html><body>
        <p>OpenAI is expanding AI supercomputer cloud infrastructure.</p>
        <p>20MW of Capacity by the end of calendar year 2026 in dedicated data centers.</p>
        </body></html>
        """
    )
    inventory = tmp_path / "inventory.csv"
    _write_csv(
        inventory,
        [
            {
                "cik": "0000999999",
                "company_name": "OpenAI Compute Infrastructure LLC",
                "form": "8-K",
                "accession_number": "0000999999-26-000001",
                "filing_date": "2026-05-15",
                "primary_document": "openai-compute.htm",
                "filing_url": "https://www.sec.gov/Archives/edgar/data/999999/openai-compute.htm",
                "local_path": str(doc),
                "content_hash": HASH,
                "downloaded_at": "2026-06-01T00:00:00+00:00",
            }
        ],
    )

    summary = extract_compute_economics_from_edgar(
        inventory_csv=inventory,
        output_dir=tmp_path / "compute",
    )

    assert summary.documents_scanned == 1
    assert summary.candidate_documents == 1
    supply = _read_csv(tmp_path / "compute" / "chip_supply_observations.csv")
    assert supply[0]["announced_mw"] == "20.0"


def test_extract_compute_economics_from_edgar_ignores_non_compute_seed_docs(
    tmp_path: Path,
) -> None:
    doc = tmp_path / "utility.htm"
    doc.write_text(
        "<html><body><p>Depreciation useful lives are five to ten years.</p></body></html>"
    )
    inventory = tmp_path / "inventory.csv"
    _write_csv(
        inventory,
        [
            {
                "cik": "0000004904",
                "company_name": "AMERICAN ELECTRIC POWER CO INC",
                "form": "10-Q",
                "accession_number": "0000004904-26-000034",
                "filing_date": "2026-05-05",
                "primary_document": "aep.htm",
                "filing_url": "https://www.sec.gov/Archives/edgar/data/4904/aep.htm",
                "local_path": str(doc),
                "content_hash": HASH,
                "downloaded_at": "2026-06-01T00:00:00+00:00",
            }
        ],
    )

    summary = extract_compute_economics_from_edgar(
        inventory_csv=inventory,
        output_dir=tmp_path / "compute",
    )

    assert summary.documents_scanned == 0
    assert summary.inventory_documents == 1
    assert summary.candidate_documents == 0
    assert _read_csv(tmp_path / "compute" / "depreciation_policies.csv") == []


def test_extract_compute_economics_from_edgar_preserves_external_gpu_pricing(
    tmp_path: Path,
) -> None:
    doc = tmp_path / "nvda.htm"
    doc.write_text(
        """
        <html><body>
        <p>NVIDIA is a data center AI infrastructure company.</p>
        <p>Our total addressable market is approximately $2.4 trillion for AI compute.</p>
        </body></html>
        """
    )
    inventory = tmp_path / "inventory.csv"
    _write_csv(
        inventory,
        [
            {
                "cik": "0001045810",
                "company_name": "NVIDIA CORP",
                "form": "10-Q",
                "accession_number": "0001045810-26-000052",
                "filing_date": "2026-05-20",
                "primary_document": "nvda.htm",
                "filing_url": "https://www.sec.gov/Archives/edgar/data/1045810/nvda.htm",
                "local_path": str(doc),
                "content_hash": HASH,
                "downloaded_at": "2026-06-01T00:00:00+00:00",
            }
        ],
    )
    compute_dir = tmp_path / "compute"
    compute_dir.mkdir()
    _write_csv(
        compute_dir / "gpu_price_observations.csv",
        [
            {
                "observation_id": "gpu-price:existing",
                "gpu_generation": "H100",
                "observed_date": "2026-06-01",
                "observed_cloud_rental_rate_usd_per_hour": 3.0,
                "source_uri": "https://lambda.ai/pricing",
                "content_hash": HASH,
            }
        ],
    )

    extract_compute_economics_from_edgar(
        inventory_csv=inventory,
        output_dir=compute_dir,
    )

    pricing = _read_csv(compute_dir / "gpu_price_observations.csv")
    assert pricing[0]["observation_id"] == "gpu-price:existing"
    assert pricing[0]["source_uri"] == "https://lambda.ai/pricing"
