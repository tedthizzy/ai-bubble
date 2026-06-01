"""Source corpus coverage reporting."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bubble.quality.source_invariants import is_source_backed_row

if TYPE_CHECKING:
    from collections.abc import Sequence


CORPUS_BY_EXACT_FILENAME = {
    "edgar_document_inventory.csv": "source_documents",
    "source_artifact_inventory.csv": "source_documents",
    "filings.csv": "filings",
    "source_documents.csv": "source_documents",
    "gpu_price_source_artifacts.csv": "source_documents",
    "projects.csv": "projects",
    "queue_projects.csv": "projects",
    "queues.csv": "queue_records",
    "queue_records.csv": "queue_records",
    "permits.csv": "permit_records",
    "permit_records.csv": "permit_records",
    "equipment.csv": "equipment_records",
    "equipment_records.csv": "equipment_records",
    "observations.csv": "construction_observations",
    "construction_observations.csv": "construction_observations",
    "deals.csv": "extracted_deals",
    "extracted_deals.csv": "extracted_deals",
    "ppas.csv": "ppas",
    "lease_agreements.csv": "lease_agreements",
    "ownership_records.csv": "ownership_records",
    "tracker_records.csv": "tracker_records",
    "compute_assets.csv": "compute_assets",
    "gpu_price_observations.csv": "gpu_price_observations",
    "depreciation_policies.csv": "depreciation_policies",
    "tam_claims.csv": "tam_claims",
    "capex_payback_cases.csv": "capex_payback_cases",
    "eps_depreciation_impacts.csv": "eps_depreciation_impacts",
    "chip_supply_observations.csv": "chip_supply_observations",
}

COMPUTE_CORPORA = {
    "compute_assets",
    "gpu_price_observations",
    "depreciation_policies",
    "tam_claims",
    "capex_payback_cases",
    "eps_depreciation_impacts",
    "chip_supply_observations",
}


@dataclass(frozen=True)
class SourceCoverageReport:
    """Counts proving how much real source corpus has been acquired and extracted."""

    generated_at: str
    data_dirs: list[str]
    filings: int
    entities: int
    source_documents: int
    projects: int
    queue_records: int
    permit_records: int
    equipment_records: int
    construction_observations: int
    ppas: int
    lease_agreements: int
    ownership_records: int
    tracker_records: int
    compute_assets: int
    gpu_price_observations: int
    depreciation_policies: int
    tam_claims: int
    capex_payback_cases: int
    eps_depreciation_impacts: int
    chip_supply_observations: int
    compute_economics_rows: int
    source_backed_compute_rows: int
    extracted_deals: int
    source_backed_deals: int
    catalog_sources: int
    catalog_sources_by_corpus: dict[str, int]
    catalog_files: list[str]
    acquisition_runs: int
    acquisition_artifacts_attempted: int
    acquisition_artifacts_acquired: int
    acquisition_errors: int
    acquisition_error_sources: list[str]
    files_by_corpus: dict[str, list[str]]
    raw_rows_by_corpus: dict[str, int]
    deal_types: dict[str, int]
    missing_corpora: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_source_coverage_report(  # noqa: PLR0912, PLR0915
    data_dirs: Sequence[str | Path],
) -> SourceCoverageReport:
    """Scan acquired source data and extracted rows to quantify coverage."""

    roots = [Path(data_dir) for data_dir in data_dirs]
    files_by_corpus: dict[str, list[str]] = {
        "filings": [],
        "source_documents": [],
        "projects": [],
        "queue_records": [],
        "permit_records": [],
        "equipment_records": [],
        "construction_observations": [],
        "ppas": [],
        "lease_agreements": [],
        "ownership_records": [],
        "tracker_records": [],
        "compute_assets": [],
        "gpu_price_observations": [],
        "depreciation_policies": [],
        "tam_claims": [],
        "capex_payback_cases": [],
        "eps_depreciation_impacts": [],
        "chip_supply_observations": [],
        "extracted_deals": [],
    }
    raw_rows_by_corpus: Counter[str] = Counter()
    entities: set[str] = set()
    deal_type_keys: dict[str, set[str]] = defaultdict(set)
    catalog_sources_by_corpus: Counter[str] = Counter()
    catalog_files: list[str] = []
    acquisition_runs = 0
    acquisition_artifacts_attempted = 0
    acquisition_artifacts_acquired = 0
    acquisition_errors = 0
    acquisition_error_sources: set[str] = set()
    ppa_deal_keys: set[str] = set()
    lease_deal_keys: set[str] = set()
    source_backed_deal_keys: set[str] = set()
    project_keys: set[str] = set()
    queue_record_keys: set[str] = set()
    permit_record_keys: set[str] = set()
    equipment_record_keys: set[str] = set()
    filing_keys: set[str] = set()
    source_backed_compute_row_keys: set[str] = set()

    csv_paths = _csv_files(roots)
    has_project_files = any(_classify_csv(path) == "projects" for path in csv_paths)
    has_tracker_files = any(_classify_csv(path) == "tracker_records" for path in csv_paths)

    for path in csv_paths:
        rows = _read_csv(path)
        if _is_source_catalog(path, rows):
            catalog_files.append(str(path))
            for row in rows:
                target_corpus = (row.get("corpus") or "").strip().lower()
                if target_corpus:
                    catalog_sources_by_corpus[target_corpus] += 1
            continue

        corpus = _classify_csv(path)
        if corpus:
            files_by_corpus[corpus].append(str(path))
            raw_rows_by_corpus[corpus] += len(rows)

        if corpus in {"filings", "source_documents"}:
            _add_cik_or_company_entities(entities, rows)
            if corpus == "filings":
                filing_keys.update(_filing_key(row) for row in rows)
        elif corpus == "extracted_deals":
            deal_scan = _scan_deal_rows(rows, entities)
            ppa_deal_keys.update(deal_scan["ppa_deal_keys"])
            lease_deal_keys.update(deal_scan["lease_deal_keys"])
            source_backed_deal_keys.update(deal_scan["source_backed_deal_keys"])
            for deal_type, keys in deal_scan["deal_type_keys"].items():
                deal_type_keys[deal_type].update(keys)
        elif corpus == "projects":
            project_keys.update(_add_project_entities(entities, rows))
            if not has_tracker_files:
                raw_rows_by_corpus["tracker_records"] += sum(
                    (row.get("source_type") or "").strip().lower() == "project_tracker"
                    for row in rows
                )
        elif corpus == "queue_records":
            queue_record_keys.update(_source_record_key(row) for row in rows)
            project_keys.update(_add_queue_project_entities(entities, rows))
        elif corpus == "equipment_records":
            equipment_record_keys.update(_source_record_key(row) for row in rows)
            _add_equipment_entities(entities, rows)
        elif corpus == "permit_records":
            permit_record_keys.update(_source_record_key(row) for row in rows)
            _add_permit_entities(entities, rows)
        elif corpus == "ppas":
            ppa_rows = [row for row in rows if not _is_probable_test_deal_row(row)]
            ppa_keys = {_deal_key(row, default_type="ppa") for row in ppa_rows}
            ppa_deal_keys.update(ppa_keys)
            deal_type_keys["ppa"].update(ppa_keys)
            source_backed_deal_keys.update(
                _deal_key(row, default_type="ppa") for row in ppa_rows if _is_source_backed(row)
            )
            _add_ppa_entities(entities, rows)
        elif corpus == "lease_agreements":
            lease_keys = {_deal_key(row, default_type="lease") for row in rows}
            lease_deal_keys.update(lease_keys)
            deal_type_keys["lease"].update(lease_keys)
            source_backed_deal_keys.update(
                _deal_key(row, default_type="lease") for row in rows if _is_source_backed(row)
            )
            _add_lease_entities(entities, rows)
        elif corpus == "ownership_records":
            _add_ownership_entities(entities, rows)
        elif corpus == "tracker_records":
            tracker_project_keys = _add_tracker_entities(entities, rows)
            if not has_project_files:
                project_keys.update(tracker_project_keys)
        elif corpus in COMPUTE_CORPORA:
            _add_compute_entities(entities, rows)
            source_backed_compute_row_keys.update(
                _compute_row_key(corpus, row) for row in rows if _is_source_backed(row)
            )

    for path in _summary_json_files(roots):
        summary = _read_json(path)
        if not isinstance(summary, dict):
            continue
        acquisition_runs += 1
        acquisition_artifacts_attempted += _json_int(
            summary, ["artifacts_attempted", "documents_attempted", "sources_attempted"]
        )
        acquisition_artifacts_acquired += _json_int(
            summary, ["artifacts_acquired", "documents_downloaded", "sources_acquired"]
        )
        errors = summary.get("errors")
        if isinstance(errors, dict):
            acquisition_errors += len(errors)
            acquisition_error_sources.update(str(source) for source in errors)

    if project_keys:
        raw_rows_by_corpus["projects"] = len(project_keys)
    if filing_keys:
        raw_rows_by_corpus["filings"] = len(filing_keys)
    if queue_record_keys:
        raw_rows_by_corpus["queue_records"] = len(queue_record_keys)
    if permit_record_keys:
        raw_rows_by_corpus["permit_records"] = len(permit_record_keys)
    if equipment_record_keys:
        raw_rows_by_corpus["equipment_records"] = len(equipment_record_keys)

    counts = {key: raw_rows_by_corpus.get(key, 0) for key in files_by_corpus}
    ppas = len(ppa_deal_keys)
    leases = len(lease_deal_keys)
    compute_economics_rows = sum(counts[corpus] for corpus in COMPUTE_CORPORA)
    deal_types = {deal_type: len(keys) for deal_type, keys in deal_type_keys.items()}
    acquisition_artifacts_attempted = max(
        acquisition_artifacts_attempted,
        counts["source_documents"],
    )
    acquisition_artifacts_acquired = max(
        acquisition_artifacts_acquired,
        counts["source_documents"],
    )
    required_corpora = {
        "filings": counts["filings"],
        "source_documents": counts["source_documents"],
        "projects": counts["projects"],
        "queue_records": counts["queue_records"],
        "permit_records": counts["permit_records"],
        "ppas": ppas,
        "lease_agreements": leases,
        "ownership_records": counts["ownership_records"],
        "tracker_records": counts["tracker_records"],
        "compute_economics": len(source_backed_compute_row_keys),
        "extracted_deals": counts["extracted_deals"],
    }
    missing = [name for name, count in required_corpora.items() if count == 0]

    return SourceCoverageReport(
        generated_at=datetime.now(UTC).isoformat(),
        data_dirs=[str(root) for root in roots],
        filings=counts["filings"],
        entities=len(entities),
        source_documents=counts["source_documents"],
        projects=counts["projects"],
        queue_records=counts["queue_records"],
        permit_records=counts["permit_records"],
        equipment_records=counts["equipment_records"],
        construction_observations=counts["construction_observations"],
        ppas=ppas,
        lease_agreements=leases,
        ownership_records=counts["ownership_records"],
        tracker_records=counts["tracker_records"],
        compute_assets=counts["compute_assets"],
        gpu_price_observations=counts["gpu_price_observations"],
        depreciation_policies=counts["depreciation_policies"],
        tam_claims=counts["tam_claims"],
        capex_payback_cases=counts["capex_payback_cases"],
        eps_depreciation_impacts=counts["eps_depreciation_impacts"],
        chip_supply_observations=counts["chip_supply_observations"],
        compute_economics_rows=compute_economics_rows,
        source_backed_compute_rows=len(source_backed_compute_row_keys),
        extracted_deals=counts["extracted_deals"],
        source_backed_deals=len(source_backed_deal_keys),
        catalog_sources=sum(catalog_sources_by_corpus.values()),
        catalog_sources_by_corpus=dict(sorted(catalog_sources_by_corpus.items())),
        catalog_files=sorted(catalog_files),
        acquisition_runs=acquisition_runs,
        acquisition_artifacts_attempted=acquisition_artifacts_attempted,
        acquisition_artifacts_acquired=acquisition_artifacts_acquired,
        acquisition_errors=acquisition_errors,
        acquisition_error_sources=sorted(acquisition_error_sources),
        files_by_corpus={key: sorted(paths) for key, paths in files_by_corpus.items()},
        raw_rows_by_corpus=dict(sorted(raw_rows_by_corpus.items())),
        deal_types=dict(sorted(deal_types.items())),
        missing_corpora=missing,
    )


def write_source_coverage_report(report: SourceCoverageReport, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return output


def _csv_files(roots: Sequence[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(path for path in root.rglob("*.csv") if path.is_file())
    return sorted(files)


def _summary_json_files(roots: Sequence[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(path for path in root.rglob("*acquisition.summary.json") if path.is_file())
    return sorted(files)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _json_int(summary: dict[str, Any], keys: list[str]) -> int:
    for key in keys:
        value = summary.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip():
            return int(float(value))
    return 0


def _is_source_catalog(path: Path, rows: list[dict[str, str]]) -> bool:
    if not path.name.lower().startswith("source_catalog") or not rows:
        return False
    return {"source_id", "corpus", "source_uri"}.issubset(rows[0])


def _classify_csv(path: Path) -> str | None:
    if "graph" in path.parts:
        return None
    name = path.name.lower()
    classified = CORPUS_BY_EXACT_FILENAME.get(name)
    if classified is None and (
        name.startswith("edgar_filing_manifest") or "filing_manifest" in name
    ):
        classified = "filings"
    if classified is None and "ownership" in name:
        classified = "ownership_records"
    if classified is None and "tracker" in name:
        classified = "tracker_records"
    return classified


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return [
            {key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(f)
        ]


def _is_source_backed(row: dict[str, str]) -> bool:
    return is_source_backed_row(row)


def _add_cik_or_company_entities(entities: set[str], rows: list[dict[str, str]]) -> None:
    for row in rows:
        _add_entity(entities, row.get("cik") or row.get("company_name"))


def _scan_deal_rows(rows: list[dict[str, str]], entities: set[str]) -> dict[str, Any]:
    deal_type_keys: dict[str, set[str]] = defaultdict(set)
    ppa_deal_keys: set[str] = set()
    lease_deal_keys: set[str] = set()
    source_backed_deal_keys: set[str] = set()
    for row in rows:
        deal_type = (row.get("deal_type") or "unknown").strip().lower()
        deal_key = _deal_key(row, default_type=deal_type)
        deal_type_keys[deal_type].add(deal_key)
        if deal_type == "ppa":
            ppa_deal_keys.add(deal_key)
        if deal_type == "lease":
            lease_deal_keys.add(deal_key)
        if _is_source_backed(row):
            source_backed_deal_keys.add(deal_key)
        for party in _split(row.get("parties")):
            _add_entity(entities, party)
    return {
        "ppa_deal_keys": ppa_deal_keys,
        "lease_deal_keys": lease_deal_keys,
        "source_backed_deal_keys": source_backed_deal_keys,
        "deal_type_keys": deal_type_keys,
    }


def _deal_key(row: dict[str, str], *, default_type: str) -> str:
    deal_id = (row.get("deal_id") or row.get("source_deal_id") or "").strip().lower()
    if deal_id:
        if deal_id.startswith(("ppa:", "lease:", "debt:", "bond:", "guarantee:")):
            return deal_id
        return f"deal:{deal_id}"

    source_type = (row.get("source_type") or "").strip().lower()
    ferc_ppa_id = (row.get("ID") or row.get("entities_ppa_id") or "").strip().lower()
    if default_type == "ppa" and source_type == "ferc" and ferc_ppa_id:
        return f"ppa:ferc:{ferc_ppa_id}"

    source_uri = (row.get("source_uri") or "").strip().lower()
    content_hash = (row.get("content_hash") or "").strip().lower()
    record_index = (row.get("record_index") or "").strip().lower()
    if source_uri or content_hash or record_index:
        return f"{default_type}:{source_uri}:{content_hash}:{record_index}"
    return f"{default_type}:row:{json.dumps(row, sort_keys=True)}"


def _source_record_key(row: dict[str, str]) -> str:
    source_uri = (row.get("source_uri") or "").strip().lower()
    content_hash = (row.get("content_hash") or "").strip().lower()
    record_index = (row.get("record_index") or "").strip().lower()
    if not record_index:
        page_or_section = row.get("page_or_section") or ""
        marker = "#record_index="
        if marker in page_or_section:
            record_index = page_or_section.rsplit(marker, maxsplit=1)[-1].strip().lower()
    if source_uri or content_hash or record_index:
        return f"{source_uri}:{content_hash}:{record_index}"
    return json.dumps(row, sort_keys=True)


def _filing_key(row: dict[str, str]) -> str:
    cik = (row.get("cik") or "").strip().lower()
    accession = (row.get("accession_number") or row.get("filing_accession") or "").strip().lower()
    document = (
        (row.get("primary_document") or row.get("document_id") or row.get("filing_url") or "")
        .strip()
        .lower()
    )
    if cik or accession or document:
        return f"{cik}:{accession}:{document}"
    return _source_record_key(row)


def _compute_row_key(corpus: str, row: dict[str, str]) -> str:
    row_id = _first_present(
        row,
        [
            "asset_id",
            "observation_id",
            "policy_id",
            "claim_id",
            "case_id",
            "impact_id",
        ],
    )
    if row_id:
        return f"{corpus}:{row_id.strip().lower()}"
    return f"{corpus}:{_source_record_key(row)}"


def _is_probable_test_deal_row(row: dict[str, str]) -> bool:
    values = [
        row.get("Reporting_Entity_Name", ""),
        row.get("Entity_Name", ""),
        row.get("Counterparty_Name", ""),
        row.get("title", ""),
        row.get("parties", ""),
    ]
    normalized = " ".join(value.lower() for value in values if value)
    compact = normalized.replace(" ", "")
    return any(
        marker in normalized or marker in compact
        for marker in (
            "production test",
            "test company",
            "testcompany",
            "dummy company",
            "dummycompany",
        )
    )


def _add_ppa_entities(entities: set[str], rows: list[dict[str, str]]) -> None:
    for row in rows:
        for entity_key in [
            "Reporting_Entity_Name",
            "reporting_entity_name",
            "Entity_Name",
            "entity_name",
            "Counterparty_Name",
            "counterparty_name",
            "Reporting Entity Name",
            "Entity Name",
            "Counterparty Name",
            "buyer",
            "seller",
            "offtaker",
            "counterparty",
        ]:
            _add_entity(entities, row.get(entity_key))
        for party in _split(row.get("parties")):
            _add_entity(entities, party)


def _add_lease_entities(entities: set[str], rows: list[dict[str, str]]) -> None:
    for row in rows:
        for entity_key in [
            "lessor",
            "lessee",
            "tenant",
            "landlord",
            "counterparty",
            "company_name",
            "Company Name",
            "parties",
        ]:
            if entity_key == "parties":
                for party in _split(row.get(entity_key)):
                    _add_entity(entities, party)
            else:
                _add_entity(entities, row.get(entity_key))


def _add_project_entities(entities: set[str], rows: list[dict[str, str]]) -> set[str]:
    projects: set[str] = set()
    for row in rows:
        project = _first_present(row, ["project_id", "Project ID", "name", "Name", "projectName"])
        if project:
            projects.add(project.strip().lower())
        _add_entity(entities, project)
    return projects


def _add_queue_project_entities(entities: set[str], rows: list[dict[str, str]]) -> set[str]:
    projects: set[str] = set()
    for row in rows:
        project = _first_present(
            row,
            [
                "project_id",
                "project_number",
                "Project Number",
                "queue_id",
                "Project ID",
                "ProjectNumber",
                "Queue Number",
                "INR",
                "Application ID",
                "Generation Interconnection Number",
                "IFS Queue Number",
                "Project Name",
                "project_name",
                "Name",
                "Alternative Name",
                "Position",
            ],
        )
        if project:
            projects.add(project.strip().lower())
        for entity_key in [
            "Interconnecting Entity",
            "Interconnection Customer Name",
            "Interconnection Customer",
            "Developer/Interconnection Customer",
            "Owner/Developer",
            "Transmission Owner",
            "TransmissionOwner",
            "TO at POI",
            "Utility",
            "PTO",
        ]:
            _add_entity(entities, row.get(entity_key))
    return projects


def _add_equipment_entities(entities: set[str], rows: list[dict[str, str]]) -> None:
    for row in rows:
        for entity_key in [
            "Entity Name",
            "Balancing Authority Code",
            "Balancing Authority Name",
            "Plant transmission or distribution system owner name",
            "Utility name",
        ]:
            _add_entity(entities, row.get(entity_key))


def _add_permit_entities(entities: set[str], rows: list[dict[str, str]]) -> None:
    for row in rows:
        for entity_key in [
            "FACILITY_NAME",
            "FAC_NAME",
            "Facility Name",
            "PERMITTEE",
            "OWNER_NAME",
            "PGM_SYS_ID",
        ]:
            _add_entity(entities, row.get(entity_key))


def _add_ownership_entities(entities: set[str], rows: list[dict[str, str]]) -> None:
    for row in rows:
        for entity_key in [
            "Relationship_StartNode_NodeID",
            "Relationship_EndNode_NodeID",
            "start_node_id",
            "end_node_id",
            "parent_entity",
            "child_entity",
            "entity",
            "owner",
            "lei",
            "parent_lei",
        ]:
            _add_entity(entities, row.get(entity_key))


def _add_tracker_entities(entities: set[str], rows: list[dict[str, str]]) -> set[str]:
    projects: set[str] = set()
    for row in rows:
        project = _first_present(
            row,
            [
                "project_id",
                "Project ID",
                "projectName",
                "Project Name",
                "name",
                "Name",
                "facility_id",
                "facility_name",
                "Facility Name",
                "entity",
            ],
        )
        if project:
            projects.add(project.strip().lower())
        _add_entity(entities, project)
        for entity_key in [
            "sponsors",
            "operators",
            "tenants",
            "sponsor",
            "operator",
            "tenant",
            "owner",
            "developer",
            "operator_name",
            "Operator",
            "Tenant",
            "company_name",
            "Company Name",
        ]:
            for entity in _split(row.get(entity_key)):
                _add_entity(entities, entity)
    return projects


def _add_compute_entities(entities: set[str], rows: list[dict[str, str]]) -> None:
    for row in rows:
        for entity_key in [
            "entity",
            "company_name",
            "supplier",
            "provider_or_marketplace",
        ]:
            _add_entity(entities, row.get(entity_key))


def _add_entity(entities: set[str], value: str | None) -> None:
    if value and value.strip():
        entities.add(value.strip().lower())


def _split(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.replace(";", "|").split("|") if part.strip()]


def _first_present(row: dict[str, str], keys: list[str]) -> str | None:
    for key in keys:
        value = row.get(key)
        if value and value.strip():
            return value.strip()
    return None
