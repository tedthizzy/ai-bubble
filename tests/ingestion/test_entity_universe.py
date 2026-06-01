from __future__ import annotations

import csv
import json
from typing import TYPE_CHECKING

from bubble.ingestion.entities import build_entity_universe

if TYPE_CHECKING:
    from pathlib import Path


HASH = "c" * 64


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    assert rows
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def test_build_entity_universe_extracts_source_backed_names_and_maps_ciks(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    _write_csv(
        data_dir / "source_acquisition" / "source_rows" / "ppas.csv",
        [
            {
                "Reporting_Entity_Name": "Microsoft Corporation",
                "Entity_Name": "Utility Seller LLC",
                "Counterparty_Name": "Amazon.com, Inc.",
                "source_uri": "https://example.com/ppas.csv",
                "source_type": "ferc",
                "retrieved_at": "2026-06-01T00:00:00+00:00",
                "content_hash": HASH,
                "document_id": "ferc-ppas",
                "record_index": "1",
            }
        ],
    )
    _write_csv(
        data_dir / "edgar_acquisition" / "deals.csv",
        [
            {
                "primary_party": "NVIDIA CORP",
                "parties": json.dumps(["NVIDIA CORP", "Lenders Party Thereto"]),
                "counterparty_roles": json.dumps({"administrative_agent": ["JPMorgan Chase Bank"]}),
                "source_uri": "https://www.sec.gov/Archives/test.htm",
                "source_type": "sec_edgar",
                "retrieved_at": "2026-06-01T00:00:00+00:00",
                "content_hash": HASH,
                "record_index": "2",
            }
        ],
    )
    sec_reference = tmp_path / "sec_company_tickers_exchange.json"
    sec_reference.write_text(
        json.dumps(
            {
                "fields": ["cik", "name", "ticker", "exchange"],
                "data": [
                    [789019, "MICROSOFT CORP", "MSFT", "Nasdaq"],
                    [1018724, "AMAZON COM INC", "AMZN", "Nasdaq"],
                    [1045810, "NVIDIA CORP", "NVDA", "Nasdaq"],
                ],
            }
        )
    )

    summary = build_entity_universe(
        data_dir,
        output_dir=tmp_path / "entity_universe",
        sec_reference_json=sec_reference,
        fetch_sec_reference=False,
    )

    assert summary.mentions_extracted == 6
    assert summary.distinct_entities == 5
    assert summary.cik_matches == 3
    assert summary.expanded_ciks == 3

    entities = _read_csv(tmp_path / "entity_universe" / "entities.csv")
    microsoft = next(row for row in entities if row["canonical_name"] == "Microsoft Corporation")
    assert microsoft["matched_cik"] == "0000789019"
    assert microsoft["cik_match_method"] == "normalized_exact"
    assert microsoft["cik_match_source_uri"].startswith("https://www.sec.gov/")
    assert microsoft["cik_reference_content_hash"]

    expanded = _read_csv(tmp_path / "entity_universe" / "expanded_edgar_ciks.csv")
    assert {row["cik"] for row in expanded} == {
        "0000789019",
        "0001018724",
        "0001045810",
    }

    mentions = _read_csv(tmp_path / "entity_universe" / "entity_mentions.csv")
    assert mentions[0]["source_uri"] == "https://example.com/ppas.csv"
    assert mentions[0]["content_hash"] == HASH


def test_build_entity_universe_requires_sec_reference_when_fetch_disabled(tmp_path: Path) -> None:
    try:
        build_entity_universe(
            tmp_path / "data",
            output_dir=tmp_path / "entity_universe",
            fetch_sec_reference=False,
        )
    except ValueError as exc:
        assert "SEC reference JSON is required" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected missing SEC reference to fail")


def test_build_entity_universe_uses_lei_reference_only_for_observed_ownership_nodes(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    _write_csv(
        data_dir / "source_acquisition" / "source_rows" / "ownership_records.csv",
        [
            {
                "Relationship_StartNode_NodeID": "MSFTLEI1234567890",
                "Relationship_EndNode_NodeID": "PARENTLEI12345678",
                "source_uri": "https://leidata.gleif.org/api/v1/concatenated-files/rr/get/1/zip",
                "source_type": "gleif",
                "retrieved_at": "2026-06-01T00:00:00+00:00",
                "content_hash": HASH,
                "record_index": "1",
            }
        ],
    )
    _write_csv(
        data_dir / "source_acquisition" / "source_rows" / "lei_records.csv",
        [
            {
                "LEI": "MSFTLEI1234567890",
                "Entity_LegalName": "Microsoft Corporation",
                "Entity_EntityStatus": "ACTIVE",
                "Registration_RegistrationStatus": "ISSUED",
                "source_uri": "https://leidata.gleif.org/api/v1/concatenated-files/lei2/get/1/zip",
                "source_type": "gleif",
                "retrieved_at": "2026-06-01T00:00:00+00:00",
                "content_hash": HASH,
                "record_index": "1",
            },
            {
                "LEI": "UNOBSERVEDLEI12345",
                "Entity_LegalName": "Unobserved Holding Company",
                "source_uri": "https://leidata.gleif.org/api/v1/concatenated-files/lei2/get/1/zip",
                "source_type": "gleif",
                "retrieved_at": "2026-06-01T00:00:00+00:00",
                "content_hash": HASH,
                "record_index": "2",
            },
        ],
    )
    sec_reference = tmp_path / "sec_company_tickers_exchange.json"
    sec_reference.write_text(
        json.dumps(
            {
                "fields": ["cik", "name", "ticker", "exchange"],
                "data": [[789019, "MICROSOFT CORP", "MSFT", "Nasdaq"]],
            }
        )
    )

    summary = build_entity_universe(
        data_dir,
        output_dir=tmp_path / "entity_universe",
        sec_reference_json=sec_reference,
        fetch_sec_reference=False,
    )

    assert summary.source_rows_scanned == 2
    assert summary.mentions_extracted == 1
    assert summary.cik_matches == 1

    entities = _read_csv(tmp_path / "entity_universe" / "entities.csv")
    assert [row["canonical_name"] for row in entities] == ["Microsoft Corporation"]
    assert entities[0]["matched_cik"] == "0000789019"

    mentions = _read_csv(tmp_path / "entity_universe" / "entity_mentions.csv")
    assert mentions[0]["source_entity_id"] == "MSFTLEI1234567890"
