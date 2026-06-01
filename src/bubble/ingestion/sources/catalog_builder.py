"""Build acquisition catalogs from curated real source targets."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bubble.ingestion.edgar.filing_manifest import SEC_SUBMISSIONS_URL
from bubble.ingestion.edgar.seeds import PUBLIC_SEEDS
from bubble.ingestion.sources.catalog import REQUIRED_CATALOG_COLUMNS, load_source_catalog
from bubble.ingestion.sources.eia import latest_eia_860m_catalog_row
from bubble.ingestion.sources.ercot import latest_ercot_gis_catalog_row
from bubble.ingestion.sources.ferc import latest_ferc_entities_to_ppas_catalog_rows
from bubble.ingestion.sources.fractracker import latest_fractracker_data_center_catalog_rows
from bubble.ingestion.sources.gleif import (
    latest_gleif_lei_catalog_row,
    latest_gleif_rr_catalog_row,
)
from bubble.ingestion.sources.iso_ne import latest_iso_ne_public_queue_catalog_row
from bubble.models.base import SourceType

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

VERIFIED_EDGAR_SOURCE_SEEDS: dict[str, dict[str, str]] = {
    "0001045810": {"name": "NVIDIA", "ticker": "NVDA", "type": "ai_pureplay", "tier": "1"},
    "0001652044": {"name": "Alphabet", "ticker": "GOOGL", "type": "hyperscaler", "tier": "1"},
    "0000320193": {"name": "Apple", "ticker": "AAPL", "type": "hyperscaler", "tier": "2"},
    "0000789019": {"name": "Microsoft", "ticker": "MSFT", "type": "hyperscaler", "tier": "1"},
    "0001018724": {"name": "Amazon", "ticker": "AMZN", "type": "hyperscaler", "tier": "1"},
    "0001326801": {"name": "Meta Platforms", "ticker": "META", "type": "hyperscaler", "tier": "1"},
    "0000002488": {"name": "AMD", "ticker": "AMD", "type": "equipment_supplier", "tier": "1"},
    "0000050863": {"name": "Intel", "ticker": "INTC", "type": "equipment_supplier", "tier": "2"},
    "0001341439": {"name": "Oracle", "ticker": "ORCL", "type": "cloud_provider", "tier": "2"},
    "0001561550": {"name": "Datadog", "ticker": "DDOG", "type": "cloud_provider", "tier": "3"},
    "0001571996": {
        "name": "Dell Technologies",
        "ticker": "DELL",
        "type": "equipment_supplier",
        "tier": "2",
    },
    "0001551182": {"name": "Eaton", "ticker": "ETN", "type": "equipment_supplier", "tier": "2"},
    "0001674101": {"name": "Vertiv", "ticker": "VRT", "type": "equipment_supplier", "tier": "1"},
    "0001996810": {
        "name": "GE Vernova",
        "ticker": "GEV",
        "type": "equipment_supplier",
        "tier": "2",
    },
    "0001868275": {
        "name": "Constellation Energy",
        "ticker": "CEG",
        "type": "power_generator",
        "tier": "1",
    },
    "0001101239": {"name": "Equinix", "ticker": "EQIX", "type": "data_center_reit", "tier": "1"},
    "0001297996": {
        "name": "Digital Realty",
        "ticker": "DLR",
        "type": "data_center_reit",
        "tier": "1",
    },
    "0001393818": {"name": "Blackstone", "ticker": "BX", "type": "financier", "tier": "1"},
    "0001404912": {"name": "KKR", "ticker": "KKR", "type": "financier", "tier": "1"},
    "0001858681": {
        "name": "Apollo Global Management",
        "ticker": "APO",
        "type": "financier",
        "tier": "1",
    },
}
VERIFIED_EDGAR_CIKS = list(VERIFIED_EDGAR_SOURCE_SEEDS)
PUBLIC_SOURCE_ROWS: list[dict[str, str]] = [
    {
        "source_id": "caiso-cluster-15-queue-report",
        "corpus": "queue_records",
        "source_uri": "https://www.caiso.com/documents/cluster-15-interconnection-requests.xlsx",
        "source_type": SourceType.GRID_QUEUE.value,
        "parser": "xlsx",
        "document_id": "caiso_cluster_15_interconnection_requests",
        "entity_id": "",
        "project_id": "",
        "filing_accession": "",
        "meta_publisher": "California ISO",
        "meta_title": "Cluster 15 Interconnection Requests Queue Report",
    },
    {
        "source_id": "nyiso-interconnection-queue",
        "corpus": "queue_records",
        "source_uri": "https://www.nyiso.com/documents/20142/1407078/NYISO-Interconnection-Queue.xlsx",
        "source_type": SourceType.GRID_QUEUE.value,
        "parser": "xlsx",
        "document_id": "nyiso_interconnection_queue",
        "entity_id": "",
        "project_id": "",
        "filing_accession": "",
        "meta_publisher": "New York ISO",
        "meta_title": "NYISO Interconnection Queue",
    },
    {
        "source_id": "miso-eras-interconnection-requests",
        "corpus": "queue_records",
        "source_uri": (
            "https://cdn.misoenergy.org/ERAS%20Interconnection%20Requests718482.xlsx"
            "?v=20250925100619"
        ),
        "source_type": SourceType.GRID_QUEUE.value,
        "parser": "xlsx",
        "document_id": "miso_eras_interconnection_requests_20260529",
        "entity_id": "",
        "project_id": "",
        "filing_accession": "",
        "meta_publisher": "MISO",
        "meta_title": "ERAS Interconnection Requests",
        "meta_source_page": (
            "https://www.misoenergy.org/planning/resource-utilization/generator-interconnection/"
        ),
        "meta_xlsx_required_value_columns": "Project Number|Application ID",
    },
    {
        "source_id": "spp-active-generation-interconnection-queue",
        "corpus": "queue_records",
        "source_uri": "https://opsportal.spp.org/Studies/GenerateActiveCSV",
        "source_type": SourceType.GRID_QUEUE.value,
        "parser": "csv",
        "document_id": "spp_active_generation_interconnection_queue",
        "entity_id": "",
        "project_id": "",
        "filing_accession": "",
        "meta_publisher": "Southwest Power Pool",
        "meta_title": "SPP Active Generation Interconnection Queue",
        "meta_source_page": "https://spp.org/engineering/generator-interconnection/",
        "meta_csv_skip_rows": "1",
    },
    {
        "source_id": "pjm-planning-queues-xml",
        "corpus": "queue_records",
        "source_uri": "https://www.pjm.com/pjmfiles/media/planning/queues-data/PlanningQueues.xml",
        "source_type": SourceType.GRID_QUEUE.value,
        "parser": "xml",
        "document_id": "pjm_planning_queues_xml",
        "entity_id": "",
        "project_id": "",
        "filing_accession": "",
        "meta_publisher": "PJM Interconnection",
        "meta_title": "PJM Planning Queues XML",
        "meta_source_page": "https://www.pjm.com/planning/service-requests/interconnection-queues",
    },
    {
        "source_id": "epa-egrid2023-data-rev2",
        "corpus": "equipment_records",
        "source_uri": "https://www.epa.gov/system/files/documents/2025-06/egrid2023_data_rev2.xlsx",
        "source_type": SourceType.EPA.value,
        "parser": "xlsx",
        "document_id": "epa_egrid2023_data_rev2",
        "entity_id": "",
        "project_id": "",
        "filing_accession": "",
        "meta_publisher": "U.S. Environmental Protection Agency",
        "meta_title": "eGRID2023 Data Revision 2",
        "meta_release_date": "2025-06-12",
        "meta_source_page": "https://www.epa.gov/egrid/detailed-data",
        "meta_xlsx_sheet_names": "UNT23|GEN23|PLNT23",
        "meta_xlsx_required_value_columns": "Plant name|DOE/EIA ORIS plant or facility code",
    },
    {
        "source_id": "epa-icis-air-facilities-programs",
        "corpus": "permit_records",
        "source_uri": "https://echo.epa.gov/files/echodownloads/ICIS-AIR_downloads.zip",
        "source_type": SourceType.EPA.value,
        "parser": "zip",
        "document_id": "epa_icis_air_downloads_facilities_programs",
        "entity_id": "",
        "project_id": "",
        "filing_accession": "",
        "meta_publisher": "U.S. Environmental Protection Agency",
        "meta_title": "ICIS-Air Facilities and Programs",
        "meta_source_page": "https://echo.epa.gov/tools/data-downloads",
        "meta_zip_member_names": "ICIS-AIR_FACILITIES.csv|ICIS-AIR_PROGRAMS.csv",
    },
    {
        "source_id": "server-country-all-projects",
        "corpus": "tracker_records",
        "source_uri": "https://servercountry.org/data/all_projects.csv",
        "source_type": SourceType.PROJECT_TRACKER.value,
        "parser": "csv",
        "document_id": "server_country_all_projects",
        "entity_id": "",
        "project_id": "",
        "filing_accession": "",
        "meta_publisher": "Server Country / Michael J. Bommarito II",
        "meta_title": "Server Country Data Center Project Database",
        "meta_source_page": "https://servercountry.org/data/downloads/",
        "meta_scope": "U.S. datacenter projects exceeding $10M investment or 10MW capacity",
    },
]

BASE_CATALOG_FIELDNAMES = [
    "source_id",
    "corpus",
    "source_uri",
    "source_type",
    "parser",
    "document_id",
    "entity_id",
    "project_id",
    "filing_accession",
    "meta_company_name",
    "meta_ticker",
    "meta_entity_type",
    "meta_tier",
    "meta_notes",
]


@dataclass(frozen=True)
class SourceCatalogBuildSummary:
    """Summary for a generated acquisition catalog."""

    output_csv: str
    catalog_rows: int
    edgar_submission_sources: int
    public_sources: int
    curated_sources: int
    corpora: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_seed_source_catalog(
    output_csv: str | Path,
    *,
    ciks: Sequence[str] | None = None,
    limit: int | None = None,
    include_public_sources: bool = True,
    include_dynamic_public_sources: bool = False,
    eia_fetch_text: Callable[[str], str] | None = None,
    eia_url_available: Callable[[str], bool] | None = None,
    ercot_fetch_json: Callable[[str], Mapping[str, Any]] | None = None,
    ferc_fetch_text: Callable[[str], str] | None = None,
    ferc_fetch_json: Callable[[str, Mapping[str, Any]], Mapping[str, Any]] | None = None,
    fractracker_fetch_json: Callable[[str], Mapping[str, Any]] | None = None,
    gleif_fetch_json: Callable[[str], Mapping[str, Any]] | None = None,
    iso_ne_fetch_text: Callable[[str], str] | None = None,
    curated_catalogs: Sequence[str | Path] | None = None,
) -> SourceCatalogBuildSummary:
    """Write a source catalog that can be handed directly to acquisition."""

    selected_ciks = list(ciks or VERIFIED_EDGAR_CIKS)
    if limit is not None:
        selected_ciks = selected_ciks[:limit]

    edgar_rows = [_edgar_submission_row(cik) for cik in selected_ciks]
    public_rows = [dict(row) for row in PUBLIC_SOURCE_ROWS] if include_public_sources else []
    if include_public_sources and include_dynamic_public_sources:
        public_rows.append(
            latest_eia_860m_catalog_row(
                fetch_text=eia_fetch_text,
                url_available=eia_url_available,
            )
        )
        public_rows.append(latest_ercot_gis_catalog_row(fetch_json=ercot_fetch_json))
        public_rows.extend(
            latest_ferc_entities_to_ppas_catalog_rows(
                fetch_text=ferc_fetch_text,
                fetch_json=ferc_fetch_json,
            )
        )
        public_rows.extend(
            latest_fractracker_data_center_catalog_rows(fetch_json=fractracker_fetch_json)
        )
        public_rows.append(latest_gleif_lei_catalog_row(fetch_json=gleif_fetch_json))
        public_rows.append(latest_gleif_rr_catalog_row(fetch_json=gleif_fetch_json))
        public_rows.append(latest_iso_ne_public_queue_catalog_row(fetch_text=iso_ne_fetch_text))
    curated_rows: list[dict[str, str]] = []
    for curated_catalog in curated_catalogs or []:
        curated_rows.extend(_read_validated_catalog(curated_catalog))

    rows = edgar_rows + public_rows + curated_rows
    output = Path(output_csv)
    _write_catalog(output, rows)

    return SourceCatalogBuildSummary(
        output_csv=str(output),
        catalog_rows=len(rows),
        edgar_submission_sources=len(edgar_rows),
        public_sources=len(public_rows),
        curated_sources=len(curated_rows),
        corpora=dict(sorted(Counter(row["corpus"] for row in rows).items())),
    )


def _edgar_submission_row(cik: str) -> dict[str, str]:
    normalized_cik = _normalize_cik(cik)
    meta = VERIFIED_EDGAR_SOURCE_SEEDS.get(normalized_cik) or PUBLIC_SEEDS.get(normalized_cik, {})
    return {
        "source_id": f"sec-submissions-{normalized_cik}",
        "corpus": "filings",
        "source_uri": SEC_SUBMISSIONS_URL.format(cik=normalized_cik),
        "source_type": SourceType.SEC_EDGAR.value,
        "parser": "json",
        "document_id": f"sec-submissions-{normalized_cik}",
        "entity_id": normalized_cik,
        "project_id": "",
        "filing_accession": "",
        "meta_company_name": meta.get("name", f"CIK {normalized_cik}"),
        "meta_ticker": meta.get("ticker", ""),
        "meta_entity_type": meta.get("type", ""),
        "meta_tier": meta.get("tier", ""),
        "meta_notes": meta.get("notes", ""),
    }


def _read_validated_catalog(path: str | Path) -> list[dict[str, str]]:
    load_source_catalog(path)
    with Path(path).open(newline="") as f:
        return [
            {str(key): (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(f)
        ]


def _write_catalog(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(
        dict.fromkeys(
            [
                *BASE_CATALOG_FIELDNAMES,
                *(key for row in rows for key in row if key not in REQUIRED_CATALOG_COLUMNS),
            ]
        )
    )
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _normalize_cik(cik: str) -> str:
    digits = "".join(ch for ch in cik if ch.isdigit())
    if not digits:
        raise ValueError(f"Invalid CIK: {cik}")
    return digits.zfill(10)
