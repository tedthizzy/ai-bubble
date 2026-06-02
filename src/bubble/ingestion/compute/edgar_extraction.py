"""Deterministic compute economics extraction from acquired EDGAR documents."""

from __future__ import annotations

import csv
import hashlib
import re
import warnings
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from bubble.ingestion.compute.economic_commitments import extract_economic_commitments
from bubble.models.base import HumanReviewStatus, SourceType

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

COMPUTE_RELEVANT_CIKS = {
    "0000002488",  # AMD
    "0000789019",  # Microsoft
    "0001018724",  # Amazon
    "0001045810",  # NVIDIA
    "0001326801",  # Meta
    "0001652044",  # Alphabet
    "0001730168",  # Broadcom
    "0001769628",  # CoreWeave
    "0002042022",  # WhiteFiber / Bit Digital AI infrastructure disclosures
    "0002021728",  # Cerebras
}
COMPUTE_FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A", "S-1", "S-1/A", "8-K", "424B4"}
COMPUTE_METADATA_KEYWORDS = (
    "accelerated computing",
    "ai infrastructure",
    "ai supercomputer",
    "artificial intelligence",
    "blackwell",
    "cerebras",
    "cloud infrastructure",
    "data center",
    "datacenter",
    "gb200",
    "gpu",
    "h100",
    "h200",
    "openai",
    "supercomputer",
)
NUMBER_WORDS = {
    "one": 1.0,
    "two": 2.0,
    "three": 3.0,
    "four": 4.0,
    "five": 5.0,
    "six": 6.0,
    "seven": 7.0,
    "eight": 8.0,
    "nine": 9.0,
    "ten": 10.0,
    "eleven": 11.0,
    "twelve": 12.0,
    "thirty": 30.0,
}
LIFE_RANGE_RE = re.compile(
    r"\b(?P<low>\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirty)"
    r"\s*(?:-|to|and)\s*"
    r"(?P<high>\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirty)"
    r"\s+years\b",
    re.IGNORECASE,
)
LIFE_SINGLE_RE = re.compile(
    r"\b(?P<life>\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirty)"
    r"\s+years\b",
    re.IGNORECASE,
)
PERCENT_RE = re.compile(r"\b\d+(?:\.\d+)?\s*%")
DEPRECIATION_ASSET_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "servers and network equipment",
        (
            "servers and networking equipment",
            "servers and network equipment",
            "servers and network assets",
            "server and network assets",
        ),
    ),
    (
        "data center equipment",
        (
            "cloud service equipment",
            "colocation service equipment",
            "data center equipment",
            "computing equipment utilized in data centers",
        ),
    ),
    ("computer equipment", ("computer equipment", "computing equipment")),
    ("gpu equipment", ("gpu servers", "gpu server", "gpus", "gpu")),
)
MONEY_AMOUNT_PATTERN = r"\d+(?:,\d{3})*(?:\.\d+)?(?![,\d])"
MONEY_RE = re.compile(
    rf"\$\s*(?P<amount>{MONEY_AMOUNT_PATTERN})\s*(?P<unit>billion|million|trillion)?",
    re.IGNORECASE,
)
TAM_RE = re.compile(
    r"\b(?:TAM|total addressable market)\b.{0,220}?\$\s*"
    rf"(?P<amount>{MONEY_AMOUNT_PATTERN})\s*(?P<unit>billion|million|trillion)?",
    re.IGNORECASE,
)
MW_CAPACITY_RE = re.compile(
    r"\b(?P<mw>\d+(?:,\d{3})*(?:\.\d+)?)\s*MW\s+of\s+"
    r"(?P<additional>additional\s+)?Capacity\b",
    re.IGNORECASE,
)
DEPRECIATION_EPS_IMPACT_RE = re.compile(
    r"financial impact of this change in estimate included a\s+"
    r"(?P<depreciation_direction>reduction|increase)\s+in depreciation expense of\s+"
    rf"\$\s*(?P<depreciation_amount>{MONEY_AMOUNT_PATTERN})\s*"
    r"(?P<depreciation_unit>billion|million|trillion)?\s+and an?\s+"
    r"(?P<income_direction>increase|reduction)\s+in net income of\s+"
    rf"\$\s*(?P<income_amount>{MONEY_AMOUNT_PATTERN})\s*"
    r"(?P<income_unit>billion|million|trillion)?"
    rf"(?:,\s+or\s+\$\s*(?P<eps_amount>{MONEY_AMOUNT_PATTERN})\s+per diluted share)?",
    re.IGNORECASE,
)
GPU_GENERATION_PATTERN = r"A100|H100|H200|B200|GB200|GB300|Blackwell|Hopper"
GPU_COUNT_RE = re.compile(
    rf"\b(?P<count>\d+(?:,\d{{3}})*)\s+"
    rf"(?:NVIDIA\s+)?(?P<generation>{GPU_GENERATION_PATTERN})\s+GPUs\b",
    re.IGNORECASE,
)
GPU_SERVER_PURCHASE_RE = re.compile(
    rf"\bpurchase order for\s+(?P<server_count>\d+(?:,\d{{3}})*)\s+"
    rf"(?:NVIDIA\s+)?(?P<generation>{GPU_GENERATION_PATTERN})\s+servers?\s+for\s+"
    rf"(?:approximately\s+)?\$\s*(?P<amount>{MONEY_AMOUNT_PATTERN})\s*"
    rf"(?P<unit>billion|million|trillion)?",
    re.IGNORECASE,
)
PER_GPU_ECONOMICS_RE = re.compile(
    rf"\bcosts?\s+of\s+(?:approximately\s+)?\$\s*"
    rf"(?P<capex>{MONEY_AMOUNT_PATTERN})\s*"
    rf"(?P<capex_unit>billion|million|trillion)?\s+for\s+an?\s+"
    rf"(?:NVIDIA\s+)?(?P<generation>{GPU_GENERATION_PATTERN})\s+GPU\s+"
    rf"that\s+generates\s+(?:approximately\s+)?\$\s*"
    rf"(?P<revenue>{MONEY_AMOUNT_PATTERN})\s*"
    rf"(?P<revenue_unit>billion|million|trillion)?\s+of\s+revenue\s+in\s+year\s+one"
    rf"(?:\s+at\s+an?\s+EBITDA\s+margin\s+between\s+"
    rf"(?P<margin_low>\d+(?:\.\d+)?)%\s+and\s+(?P<margin_high>\d+(?:\.\d+)?)%)?",
    re.IGNORECASE,
)
ANNUALIZED_REVENUE_RE = re.compile(
    r"\b(?:worth|represents|representing)\s+(?:an?\s+)?(?:approximately\s+)?\$\s*"
    rf"(?P<amount>{MONEY_AMOUNT_PATTERN})\s*"
    r"(?P<unit>billion|million|trillion)?\s+of\s+(?:targeted\s+)?annual(?:ized)?\s+revenue\b",
    re.IGNORECASE,
)
CONTRACT_REVENUE_RE = re.compile(
    r"\b(?:contract\s+represents|it\s+represents|represents|representing|total\s+revenue\s+of)"
    r"\s+(?:an?\s+)?(?:aggregate\s+revenue\s+opportunity\s+of|total\s+contracted\s+"
    r"value\s+of|contracted\s+value\s+of|contract\s+value\s+of)?\s*"
    rf"(?:approximately\s+)?\$\s*(?P<amount>{MONEY_AMOUNT_PATTERN})\s*"
    r"(?P<unit>billion|million|trillion)?",
    re.IGNORECASE,
)
MONTHLY_SERVICE_FEE_RE = re.compile(
    rf"\bservice\s+fee\s+is\s+\$\s*(?P<amount>{MONEY_AMOUNT_PATTERN})\s*"
    r"(?P<unit>billion|million|trillion)?\s+per\s+month\b",
    re.IGNORECASE,
)
TERM_MONTH_RE = re.compile(
    r"\b(?P<term>\d+(?:\.\d+)?|six|twelve|eighteen|twenty[- ]?three|"
    r"twenty[- ]?four|twenty[- ]?five)(?:\s*-\s*|\s+)month(?:s)?"
    r"(?:\s+(?:period|term))?\b",
    re.IGNORECASE,
)
SOURCE_FIELDS = [
    "source_uri",
    "source_type",
    "retrieved_at",
    "source_confidence",
    "human_review_status",
    "page_or_section",
    "content_hash",
    "document_id",
    "filing_accession",
]

CSV_FIELDS: dict[str, list[str]] = {
    "compute_assets.csv": [
        "asset_id",
        "entity",
        "project_or_cluster_id",
        "gpu_generation",
        "gpu_count",
        "purchase_date",
        "capex_usd",
        "original_price_per_gpu_usd",
        "accounting_useful_life_years",
        "modeled_economic_life_years",
        "notes",
        *SOURCE_FIELDS,
    ],
    "gpu_price_observations.csv": [
        "observation_id",
        "gpu_generation",
        "observed_date",
        "observed_secondary_price_usd",
        "observed_cloud_rental_rate_usd_per_hour",
        "original_price_usd",
        "peak_price_usd",
        "provider_or_marketplace",
        "region",
        "contract_term",
        *SOURCE_FIELDS,
    ],
    "depreciation_policies.csv": [
        "policy_id",
        "entity",
        "asset_class",
        "accounting_useful_life_years",
        "depreciation_method",
        "effective_date",
        "source_quote",
        *SOURCE_FIELDS,
    ],
    "tam_claims.csv": [
        "claim_id",
        "entity",
        "claimed_market",
        "claim_date",
        "stated_tam_usd",
        "realized_revenue_usd",
        "implied_revenue_capture_assumption_pct",
        "source_quote",
        *SOURCE_FIELDS,
    ],
    "capex_payback_cases.csv": [
        "case_id",
        "entity",
        "project_or_cluster_id",
        "capex_usd",
        "annual_revenue_run_rate_usd",
        "contracted_revenue_usd",
        "utilization_pct",
        "gross_margin_pct",
        "annual_power_cost_usd",
        "annual_debt_service_usd",
        "depreciation_life_years",
        "notes",
        *SOURCE_FIELDS,
    ],
    "eps_depreciation_impacts.csv": [
        "impact_id",
        "entity",
        "fiscal_year",
        "annual_ai_capex_usd",
        "data_center_capex_usd",
        "gpu_capex_estimate_usd",
        "disclosed_depreciation_usd",
        "disclosed_net_income_impact_usd",
        "disclosed_eps_impact_usd",
        "accounting_useful_life_years",
        "modeled_economic_life_years",
        "tax_rate_pct",
        "diluted_shares",
        "reported_eps",
        "impact_direction",
        "source_quote",
        *SOURCE_FIELDS,
    ],
    "chip_supply_observations.csv": [
        "observation_id",
        "entity",
        "project_or_cluster_id",
        "gpu_generation",
        "announced_gpu_count",
        "delivered_gpu_count",
        "announced_mw",
        "disclosed_purchase_commitment_usd",
        "supplier",
        "delivery_window",
        "observed_deployment_date",
        "source_quote",
        *SOURCE_FIELDS,
    ],
    "economic_commitments.csv": [
        "commitment_id",
        "entity",
        "counterparty",
        "term_type",
        "value",
        "unit",
        "binding_tier",
        "double_count_caveat",
        "source_quote",
        *SOURCE_FIELDS,
    ],
}


@dataclass(frozen=True)
class ComputeEdgarExtractionSummary:
    """Summary for one EDGAR compute economics extraction run."""

    inventory_documents: int
    candidate_documents: int
    documents_scanned: int
    compute_assets: int
    depreciation_policies: int
    tam_claims: int
    capex_payback_cases: int
    eps_depreciation_impacts: int
    chip_supply_observations: int
    economic_commitments: int

    def to_dict(self) -> dict[str, int]:
        return {
            "inventory_documents": self.inventory_documents,
            "candidate_documents": self.candidate_documents,
            "documents_scanned": self.documents_scanned,
            "compute_assets": self.compute_assets,
            "depreciation_policies": self.depreciation_policies,
            "tam_claims": self.tam_claims,
            "capex_payback_cases": self.capex_payback_cases,
            "eps_depreciation_impacts": self.eps_depreciation_impacts,
            "chip_supply_observations": self.chip_supply_observations,
            "economic_commitments": self.economic_commitments,
        }


@dataclass(frozen=True)
class _DocumentExtraction:
    scanned: bool
    compute_assets: list[dict[str, Any]]
    depreciation_policies: list[dict[str, Any]]
    tam_claims: list[dict[str, Any]]
    capex_payback_cases: list[dict[str, Any]]
    eps_depreciation_impacts: list[dict[str, Any]]
    chip_supply_observations: list[dict[str, Any]]
    economic_commitments: list[dict[str, Any]]


@dataclass
class _ExtractionRows:
    documents_scanned: int = 0
    compute_assets: list[dict[str, Any]] = field(default_factory=list)
    depreciation_policies: list[dict[str, Any]] = field(default_factory=list)
    tam_claims: list[dict[str, Any]] = field(default_factory=list)
    capex_payback_cases: list[dict[str, Any]] = field(default_factory=list)
    eps_depreciation_impacts: list[dict[str, Any]] = field(default_factory=list)
    chip_supply_observations: list[dict[str, Any]] = field(default_factory=list)
    economic_commitments: list[dict[str, Any]] = field(default_factory=list)


def extract_compute_economics_from_edgar(
    *,
    inventory_csv: str | Path = "data/edgar_acquisition/edgar_document_inventory.csv",
    output_dir: str | Path = "data/compute",
    max_workers: int = 32,
) -> ComputeEdgarExtractionSummary:
    """Extract source-backed compute economics rows from local EDGAR documents."""

    inventory_path = Path(inventory_csv)
    rows = _read_csv(inventory_path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    candidate_rows = [row for row in rows if _is_candidate_document(row)]
    worker_count = max(1, max_workers)
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        document_results = executor.map(_extract_document, candidate_rows)
        extracted = _collect_extraction_rows(document_results)

    asset_rows_to_write = _merge_rows_by_id(
        _read_optional_csv(output / "compute_assets.csv"),
        extracted.compute_assets,
        "asset_id",
    )
    payback_rows_to_write = _merge_rows_by_id(
        _read_optional_csv(output / "capex_payback_cases.csv"),
        extracted.capex_payback_cases,
        "case_id",
    )

    # Preserve source-specific rows owned by other acquisition pipelines while
    # replacing EDGAR-owned extraction outputs with the current deterministic run.
    _write_csv(output / "compute_assets.csv", asset_rows_to_write)
    _write_csv(output / "depreciation_policies.csv", extracted.depreciation_policies)
    _write_csv(output / "tam_claims.csv", extracted.tam_claims)
    _write_csv(output / "capex_payback_cases.csv", payback_rows_to_write)
    _write_csv(output / "eps_depreciation_impacts.csv", extracted.eps_depreciation_impacts)
    _write_csv(output / "chip_supply_observations.csv", extracted.chip_supply_observations)
    _write_csv(output / "economic_commitments.csv", extracted.economic_commitments)
    return ComputeEdgarExtractionSummary(
        inventory_documents=len(rows),
        candidate_documents=len(candidate_rows),
        documents_scanned=extracted.documents_scanned,
        compute_assets=len(asset_rows_to_write),
        depreciation_policies=len(extracted.depreciation_policies),
        tam_claims=len(extracted.tam_claims),
        capex_payback_cases=len(payback_rows_to_write),
        eps_depreciation_impacts=len(extracted.eps_depreciation_impacts),
        chip_supply_observations=len(extracted.chip_supply_observations),
        economic_commitments=len(extracted.economic_commitments),
    )


def _collect_extraction_rows(
    document_results: Any,
) -> _ExtractionRows:
    extracted = _ExtractionRows()
    seen_keys: set[tuple[str, ...]] = set()
    for result in document_results:
        if not result.scanned:
            continue
        extracted.documents_scanned += 1
        _append_unique(
            extracted.compute_assets,
            result.compute_assets,
            seen_keys,
            _asset_dedupe_key,
        )
        _append_unique(
            extracted.depreciation_policies,
            result.depreciation_policies,
            seen_keys,
            _policy_dedupe_key,
        )
        _append_unique(extracted.tam_claims, result.tam_claims, seen_keys, _tam_dedupe_key)
        _append_unique(
            extracted.capex_payback_cases,
            result.capex_payback_cases,
            seen_keys,
            _payback_dedupe_key,
        )
        _append_unique(
            extracted.eps_depreciation_impacts,
            result.eps_depreciation_impacts,
            seen_keys,
            _eps_dedupe_key,
        )
        _append_unique(
            extracted.chip_supply_observations,
            result.chip_supply_observations,
            seen_keys,
            _chip_supply_dedupe_key,
        )
        _append_unique(
            extracted.economic_commitments,
            result.economic_commitments,
            seen_keys,
            _economic_commitment_dedupe_key,
        )
    return extracted


def _append_unique(
    target: list[dict[str, Any]],
    items: list[dict[str, Any]],
    seen_keys: set[tuple[str, ...]],
    key_fn: Any,
) -> None:
    for item in items:
        key = key_fn(item)
        if key in seen_keys:
            continue
        target.append(item)
        seen_keys.add(key)


def _dedupe_text(value: str) -> str:
    return re.sub(r"[^a-z0-9$%.]+", " ", value.lower()).strip()


def _asset_dedupe_key(asset: dict[str, Any]) -> tuple[str, ...]:
    return (
        "asset",
        str(asset["entity"]),
        str(asset["gpu_generation"]),
        str(asset["gpu_count"]),
        str(asset["capex_usd"]),
        _dedupe_text(str(asset["notes"]))[:220],
    )


def _policy_dedupe_key(policy: dict[str, Any]) -> tuple[str, ...]:
    return (
        "policy",
        str(policy["entity"]),
        str(policy["asset_class"]),
        str(policy["accounting_useful_life_years"]),
        str(policy["source_uri"]),
    )


def _tam_dedupe_key(claim: dict[str, Any]) -> tuple[str, ...]:
    return (
        "tam",
        str(claim["entity"]),
        str(claim["source_quote"])[:180],
    )


def _payback_dedupe_key(case: dict[str, Any]) -> tuple[str, ...]:
    return (
        "payback",
        str(case["entity"]),
        str(case["project_or_cluster_id"]),
        str(case["capex_usd"]),
        str(case["annual_revenue_run_rate_usd"]),
        str(case["contracted_revenue_usd"]),
        str(case["gross_margin_pct"]),
    )


def _eps_dedupe_key(impact: dict[str, Any]) -> tuple[str, ...]:
    return (
        "eps",
        str(impact["entity"]),
        str(impact["fiscal_year"]),
        str(impact["disclosed_depreciation_usd"]),
        str(impact["disclosed_net_income_impact_usd"]),
        str(impact["source_uri"]),
    )


def _chip_supply_dedupe_key(observation: dict[str, Any]) -> tuple[str, ...]:
    return (
        "chip_supply",
        str(observation["entity"]),
        str(observation["gpu_generation"]),
        str(observation["announced_mw"]),
        str(observation["disclosed_purchase_commitment_usd"]),
        str(observation["delivery_window"]),
        str(observation["source_quote"])[:160],
    )


def _economic_commitment_dedupe_key(commitment: dict[str, Any]) -> tuple[str, ...]:
    return (
        "economic_commitment",
        str(commitment["entity"]),
        str(commitment["term_type"]),
        str(commitment["value"]),
        str(commitment["unit"]),
        str(commitment["binding_tier"]),
        str(commitment["source_quote"])[:180],
    )


def _extract_document(row: dict[str, str]) -> _DocumentExtraction:
    local_path = Path(row.get("local_path", ""))
    if not local_path.is_file():
        return _empty_document_extraction()
    text = _html_text(local_path)
    if not _is_compute_relevant_text(text):
        return _empty_document_extraction()
    source = _source_row(row)
    return _DocumentExtraction(
        scanned=True,
        compute_assets=_extract_compute_assets(row, text, source),
        depreciation_policies=_extract_depreciation_policies(row, text, source),
        tam_claims=_extract_tam_claims(row, text, source),
        capex_payback_cases=_extract_capex_payback_cases(row, text, source),
        eps_depreciation_impacts=_extract_eps_depreciation_impacts(row, text, source),
        chip_supply_observations=_extract_chip_supply_observations(row, text, source),
        economic_commitments=_extract_economic_commitment_terms(row, text, source),
    )


def _empty_document_extraction() -> _DocumentExtraction:
    return _DocumentExtraction(
        scanned=False,
        compute_assets=[],
        depreciation_policies=[],
        tam_claims=[],
        capex_payback_cases=[],
        eps_depreciation_impacts=[],
        chip_supply_observations=[],
        economic_commitments=[],
    )


def _is_candidate_document(row: dict[str, str]) -> bool:
    cik = row.get("cik", "")
    form = row.get("form", "")
    if form not in COMPUTE_FORMS:
        return False
    if cik in COMPUTE_RELEVANT_CIKS:
        return True
    return _metadata_is_compute_relevant(row)


def _metadata_is_compute_relevant(row: dict[str, str]) -> bool:
    metadata = " ".join(
        row.get(field, "")
        for field in (
            "company_name",
            "primary_document",
            "primary_document_description",
            "relevance_reasons",
            "filing_url",
        )
    ).lower()
    return any(keyword in metadata for keyword in COMPUTE_METADATA_KEYWORDS) or bool(
        re.search(r"\bai\b", metadata)
    )


def _is_compute_relevant_text(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in (
            "data center",
            "gpu",
            "ai infrastructure",
            "ai supercomputer",
            "artificial intelligence",
            "accelerated computing",
            "cloud infrastructure",
            "datacenter",
            "compute capacity",
            "server and network equipment",
        )
    )


def _extract_economic_commitment_terms(
    row: dict[str, str],
    text: str,
    source: dict[str, str],
) -> list[dict[str, Any]]:
    terms = extract_economic_commitments(
        {
            "source_id": row.get("accession_number", ""),
            "source_uri": source["source_uri"],
            "document_id": source["document_id"],
            "entity": row.get("company_name", ""),
            "text": text,
        }
    )
    rows: list[dict[str, Any]] = []
    for term in terms:
        commitment_id = _stable_id(
            "edgar-economic-commitment",
            row,
            term.term_type,
            term.value,
            term.binding_tier,
            term.quote,
        )
        rows.append(
            {
                "commitment_id": commitment_id,
                "entity": term.entity or row.get("company_name", ""),
                "counterparty": term.counterparty,
                "term_type": term.term_type,
                "value": term.value,
                "unit": term.unit,
                "binding_tier": term.binding_tier,
                "double_count_caveat": term.double_count_caveat,
                "source_quote": term.quote,
                "page_or_section": (
                    f"{row.get('form', '')} {row.get('accession_number', '')} "
                    "economic commitment"
                ),
                **source,
            }
        )
    return rows


def _html_text(path: Path) -> str:
    soup = BeautifulSoup(path.read_text(errors="ignore"), "lxml")
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()


def _source_row(row: dict[str, str]) -> dict[str, str]:
    return {
        "source_uri": row.get("filing_url", ""),
        "source_type": SourceType.SEC_EDGAR.value,
        "retrieved_at": row.get("downloaded_at", ""),
        "source_confidence": "0.82",
        "human_review_status": HumanReviewStatus.PENDING.value,
        "content_hash": row.get("content_hash", ""),
        "document_id": row.get("primary_document", ""),
        "filing_accession": row.get("accession_number", ""),
    }


def _extract_compute_assets(
    row: dict[str, str],
    text: str,
    source: dict[str, str],
) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for match in GPU_COUNT_RE.finditer(text):
        quote = _gpu_count_quote(text, match, before=620, after=620)
        generation = _normalize_gpu_generation(match.group("generation"))
        gpu_count = _int_token(match.group("count"))
        if gpu_count is None:
            continue
        original_price_per_gpu = _per_gpu_capex_for_generation(text, match.start(), generation)
        server_purchase_capex = _purchase_capex_for_generation(quote, generation)
        capex = server_purchase_capex
        notes = quote
        if capex is None and original_price_per_gpu is not None:
            capex = round(original_price_per_gpu * gpu_count, 2)
            notes = f"Estimated asset capex from disclosed per-GPU cost and GPU count. {quote}"
        asset_id = _stable_id("edgar-compute-asset", row, generation, str(gpu_count), quote)
        assets.append(
            {
                "asset_id": asset_id,
                "entity": row.get("company_name", ""),
                "project_or_cluster_id": _project_or_cluster_id(generation, row, quote),
                "gpu_generation": generation,
                "gpu_count": gpu_count,
                "purchase_date": "",
                "capex_usd": capex or "",
                "original_price_per_gpu_usd": original_price_per_gpu or "",
                "accounting_useful_life_years": _extract_life_years(quote) or "",
                "modeled_economic_life_years": "",
                "notes": notes,
                "page_or_section": (
                    f"{row.get('form', '')} {row.get('accession_number', '')} GPU count"
                ),
                **source,
            }
        )

    for match in GPU_SERVER_PURCHASE_RE.finditer(text):
        quote = _window(text, match.start(), 620)
        generation = _normalize_gpu_generation(match.group("generation"))
        capex = _money_value(match.group("amount"), match.group("unit"))
        if capex is None:
            continue
        server_count = _int_token(match.group("server_count"))
        asset_id = _stable_id(
            "edgar-compute-asset",
            row,
            generation,
            str(server_count),
            str(capex),
            quote,
        )
        assets.append(
            {
                "asset_id": asset_id,
                "entity": row.get("company_name", ""),
                "project_or_cluster_id": _project_or_cluster_id(generation, row, quote),
                "gpu_generation": generation,
                "gpu_count": "",
                "purchase_date": "",
                "capex_usd": capex,
                "original_price_per_gpu_usd": "",
                "accounting_useful_life_years": _extract_life_years(quote) or "",
                "modeled_economic_life_years": "",
                "notes": f"Server purchase order disclosed {server_count or ''} servers. {quote}",
                "page_or_section": (
                    f"{row.get('form', '')} {row.get('accession_number', '')} GPU server purchase"
                ),
                **source,
            }
        )
    return assets


def _extract_capex_payback_cases(
    row: dict[str, str],
    text: str,
    source: dict[str, str],
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for match in PER_GPU_ECONOMICS_RE.finditer(text):
        quote = _window(text, match.start(), 620)
        generation = _normalize_gpu_generation(match.group("generation"))
        capex = _money_value(match.group("capex"), match.group("capex_unit"))
        revenue = _money_value(match.group("revenue"), match.group("revenue_unit"))
        if capex is None or revenue is None:
            continue
        margin_low = _float_token(match.group("margin_low") or "")
        case_id = _stable_id("edgar-payback", row, generation, str(capex), str(revenue), quote)
        cases.append(
            {
                "case_id": case_id,
                "entity": row.get("company_name", ""),
                "project_or_cluster_id": _project_or_cluster_id(generation, row, quote),
                "capex_usd": capex,
                "annual_revenue_run_rate_usd": revenue,
                "contracted_revenue_usd": "",
                "utilization_pct": "",
                "gross_margin_pct": margin_low or "",
                "annual_power_cost_usd": "",
                "annual_debt_service_usd": "",
                "depreciation_life_years": _extract_life_years(quote) or "",
                "notes": f"Per-GPU economics disclosed for {generation}. {quote}",
                "page_or_section": (
                    f"{row.get('form', '')} {row.get('accession_number', '')} per-GPU economics"
                ),
                **source,
            }
        )

    for match in GPU_COUNT_RE.finditer(text):
        quote = _gpu_count_quote(text, match, before=620, after=920)
        generation = _normalize_gpu_generation(match.group("generation"))
        gpu_count = _int_token(match.group("count"))
        if gpu_count is None:
            continue
        term_months = _term_months_from_quote(quote)
        annual_run_rate = _annualized_revenue_from_quote(quote)
        contracted_revenue = _contracted_revenue_from_quote(quote)
        monthly_fee = _monthly_service_fee_from_quote(quote)
        if monthly_fee is not None:
            annual_run_rate = round(monthly_fee * 12, 2)
            if term_months is not None:
                contracted_revenue = round(monthly_fee * term_months, 2)
        elif annual_run_rate is None and contracted_revenue is not None and term_months is not None:
            annual_run_rate = round(contracted_revenue / (term_months / 12), 2)

        purchase_capex = _purchase_capex_for_generation(quote, generation)
        per_gpu_capex = _per_gpu_capex_for_generation(text, match.start(), generation)
        capex = purchase_capex
        derived_capex = False
        if capex is None and per_gpu_capex is not None:
            capex = round(per_gpu_capex * gpu_count, 2)
            derived_capex = True
        if capex is None or (annual_run_rate is None and contracted_revenue is None):
            continue

        notes_prefix = (
            "Estimated capex from disclosed per-GPU cost and GPU count. "
            if derived_capex
            else "Contract economics matched to disclosed purchase capex. "
        )
        case_id = _stable_id(
            "edgar-payback",
            row,
            generation,
            str(gpu_count),
            str(capex),
            str(annual_run_rate or ""),
            str(contracted_revenue or ""),
            quote,
        )
        cases.append(
            {
                "case_id": case_id,
                "entity": row.get("company_name", ""),
                "project_or_cluster_id": _project_or_cluster_id(generation, row, quote),
                "capex_usd": capex,
                "annual_revenue_run_rate_usd": annual_run_rate or "",
                "contracted_revenue_usd": contracted_revenue or "",
                "utilization_pct": "",
                "gross_margin_pct": _gross_margin_low_from_quote(quote) or "",
                "annual_power_cost_usd": "",
                "annual_debt_service_usd": "",
                "depreciation_life_years": _extract_life_years(quote) or "",
                "notes": f"{notes_prefix}{quote}",
                "page_or_section": (
                    f"{row.get('form', '')} {row.get('accession_number', '')} "
                    "GPU contract economics"
                ),
                **source,
            }
        )
    return cases


def _extract_depreciation_policies(
    row: dict[str, str],
    text: str,
    source: dict[str, str],
) -> list[dict[str, Any]]:
    policies: list[dict[str, Any]] = []
    lowered = text.lower()
    for match in re.finditer(r"useful liv(?:es|e)", lowered):
        quote = _window(text, match.start(), 420)
        quote_lower = quote.lower()
        if "depreciat" not in quote_lower:
            continue
        if not any(
            marker in quote_lower
            for marker in (
                "property and equipment",
                "server",
                "network",
                "data center",
                "software",
                "equipment",
            )
        ):
            continue
        policy = _depreciation_policy_observation(quote)
        if policy is None:
            continue
        asset_class, life = policy
        policy_id = _stable_id("edgar-policy", row, asset_class, str(life), quote)
        policies.append(
            {
                "policy_id": policy_id,
                "entity": row.get("company_name", ""),
                "asset_class": asset_class,
                "accounting_useful_life_years": life,
                "depreciation_method": "straight-line"
                if "straight-line" in quote_lower or "straight line" in quote_lower
                else "",
                "effective_date": row.get("filing_date", ""),
                "source_quote": quote,
                "page_or_section": (
                    f"{row.get('form', '')} {row.get('accession_number', '')} depreciation policy"
                ),
                **source,
            }
        )
    return policies


def _extract_tam_claims(
    row: dict[str, str],
    text: str,
    source: dict[str, str],
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for match in TAM_RE.finditer(text):
        quote = _window(text, match.start(), 360)
        amount = _money_from_match(match)
        if amount is None:
            continue
        claim_id = _stable_id("edgar-tam", row, str(amount), quote)
        claims.append(
            {
                "claim_id": claim_id,
                "entity": row.get("company_name", ""),
                "claimed_market": "AI/data center compute market",
                "claim_date": row.get("filing_date", ""),
                "stated_tam_usd": amount,
                "realized_revenue_usd": "",
                "implied_revenue_capture_assumption_pct": "",
                "source_quote": quote,
                "page_or_section": f"{row.get('form', '')} {row.get('accession_number', '')} TAM claim",
                **source,
            }
        )
    return claims


def _extract_eps_depreciation_impacts(
    row: dict[str, str],
    text: str,
    source: dict[str, str],
) -> list[dict[str, Any]]:
    impacts: list[dict[str, Any]] = []
    for match in DEPRECIATION_EPS_IMPACT_RE.finditer(text):
        quote = _window(text, match.start(), 720)
        quote_lower = quote.lower()
        if "useful lives" not in quote_lower:
            continue
        if "server" not in quote_lower and "network" not in quote_lower:
            continue
        depreciation_amount = _money_value(
            match.group("depreciation_amount"),
            match.group("depreciation_unit"),
        )
        net_income_amount = _money_value(match.group("income_amount"), match.group("income_unit"))
        if depreciation_amount is None or net_income_amount is None:
            continue
        eps_amount = _float_token(match.group("eps_amount") or "")
        life_years = _extract_life_years(quote)
        impact_direction = (
            f"depreciation_{match.group('depreciation_direction').lower()}_"
            f"net_income_{match.group('income_direction').lower()}"
        )
        fiscal_year = _fiscal_year_from_quote_or_row(quote, row)
        impact_id = _stable_id(
            "edgar-eps-impact",
            row,
            str(fiscal_year),
            str(depreciation_amount),
            str(net_income_amount),
            quote,
        )
        impacts.append(
            {
                "impact_id": impact_id,
                "entity": row.get("company_name", ""),
                "fiscal_year": fiscal_year,
                "annual_ai_capex_usd": "",
                "data_center_capex_usd": "",
                "gpu_capex_estimate_usd": "",
                "disclosed_depreciation_usd": depreciation_amount,
                "disclosed_net_income_impact_usd": net_income_amount,
                "disclosed_eps_impact_usd": eps_amount or "",
                "accounting_useful_life_years": life_years or "",
                "modeled_economic_life_years": "",
                "tax_rate_pct": "",
                "diluted_shares": "",
                "reported_eps": "",
                "impact_direction": impact_direction,
                "source_quote": quote,
                "page_or_section": (
                    f"{row.get('form', '')} {row.get('accession_number', '')} "
                    "depreciation EPS impact"
                ),
                **source,
            }
        )
    return impacts


def _extract_chip_supply_observations(
    row: dict[str, str],
    text: str,
    source: dict[str, str],
) -> list[dict[str, Any]]:
    lowered = text.lower()
    observations: list[dict[str, Any]] = []
    patterns = (
        "data center-scale production",
        "datacenter-scale production",
        "manufacturing, supply, and capacity commitments",
        "supply and capacity commitments",
    )
    for marker in patterns:
        start = lowered.find(marker)
        if start < 0:
            continue
        quote = text[start : start + 900].strip()
        commitment = _money_after_commitment_marker(quote) or _first_money(quote)
        observation_id = _stable_id("edgar-chip-supply", row, marker, quote)
        observations.append(
            {
                "observation_id": observation_id,
                "entity": row.get("company_name", ""),
                "project_or_cluster_id": "",
                "gpu_generation": _gpu_generation_from_quote(quote),
                "announced_gpu_count": "",
                "delivered_gpu_count": "",
                "announced_mw": "",
                "disclosed_purchase_commitment_usd": commitment or "",
                "supplier": row.get("company_name", ""),
                "delivery_window": _delivery_window_from_quote(quote),
                "observed_deployment_date": row.get("filing_date", ""),
                "source_quote": quote,
                "page_or_section": (
                    f"{row.get('form', '')} {row.get('accession_number', '')} supply commitments"
                ),
                **source,
            }
        )
        break
    observations.extend(_extract_mw_capacity_observations(row, text, source))
    return observations


def _extract_mw_capacity_observations(
    row: dict[str, str],
    text: str,
    source: dict[str, str],
) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for match in MW_CAPACITY_RE.finditer(text):
        quote = _window(text, match.start(), 640)
        quote_lower = quote.lower()
        if "data center" not in quote_lower and "supercomputer" not in quote_lower:
            continue
        mw = _float_token(match.group("mw"))
        if mw is None:
            continue
        delivery_window = _delivery_window_from_quote(text[match.start() : match.start() + 260])
        observation_id = _stable_id("edgar-chip-supply-mw", row, str(mw), delivery_window, quote)
        observations.append(
            {
                "observation_id": observation_id,
                "entity": row.get("company_name", ""),
                "project_or_cluster_id": "",
                "gpu_generation": _gpu_generation_from_quote(quote),
                "announced_gpu_count": "",
                "delivered_gpu_count": "",
                "announced_mw": mw,
                "disclosed_purchase_commitment_usd": "",
                "supplier": row.get("company_name", ""),
                "delivery_window": delivery_window,
                "observed_deployment_date": row.get("filing_date", ""),
                "source_quote": quote,
                "page_or_section": (
                    f"{row.get('form', '')} {row.get('accession_number', '')} "
                    "compute capacity commitment"
                ),
                **source,
            }
        )
    return observations


def _project_or_cluster_id(generation: str, row: dict[str, str], quote: str) -> str:
    lowered = quote.lower()
    if "initial customer" in lowered:
        return f"{row.get('company_name', '').strip()}:{generation}:initial-customer"
    if "cloud" in lowered or "msa" in lowered:
        return f"{row.get('company_name', '').strip()}:{generation}:cloud-services"
    return ""


def _gpu_count_quote(
    text: str,
    match: re.Match[str],
    *,
    before: int,
    after: int,
) -> str:
    start = max(0, match.start() - before)
    end = min(len(text), match.start() + after)
    previous_match: re.Match[str] | None = None
    for candidate in GPU_COUNT_RE.finditer(text, 0, match.start()):
        previous_match = candidate
    if previous_match:
        prior_boundary = max(
            text.rfind(". ", previous_match.end(), match.start()),
            text.rfind("; ", previous_match.end(), match.start()),
        )
        start = max(start, prior_boundary + 2 if prior_boundary >= 0 else previous_match.end())
    next_match = GPU_COUNT_RE.search(text, match.end())
    if next_match:
        end = min(end, next_match.start())
    return text[start:end].strip()


def _normalize_gpu_generation(value: str) -> str:
    normalized = value.strip().upper()
    if normalized == "BLACKWELL":
        return "B200/BLACKWELL"
    if normalized == "HOPPER":
        return "H100/H200"
    return normalized


def _per_gpu_capex_for_generation(text: str, position: int, generation: str) -> float | None:
    quote = _window(text, position, 900)
    for match in PER_GPU_ECONOMICS_RE.finditer(quote):
        if _normalize_gpu_generation(match.group("generation")) == generation:
            return _money_value(match.group("capex"), match.group("capex_unit"))
    return None


def _purchase_capex_for_generation(quote: str, generation: str) -> float | None:
    for match in GPU_SERVER_PURCHASE_RE.finditer(quote):
        if _normalize_gpu_generation(match.group("generation")) != generation:
            continue
        return _money_value(match.group("amount"), match.group("unit"))
    return None


def _annualized_revenue_from_quote(quote: str) -> float | None:
    match = ANNUALIZED_REVENUE_RE.search(quote)
    if not match:
        return None
    return _money_value(match.group("amount"), match.group("unit"))


def _contracted_revenue_from_quote(quote: str) -> float | None:
    for match in CONTRACT_REVENUE_RE.finditer(quote):
        nearby = quote[max(0, match.start() - 80) : match.end() + 80].lower()
        if "annualized revenue" in nearby:
            continue
        return _money_value(match.group("amount"), match.group("unit"))
    return None


def _monthly_service_fee_from_quote(quote: str) -> float | None:
    match = MONTHLY_SERVICE_FEE_RE.search(quote)
    if not match:
        return None
    return _money_value(match.group("amount"), match.group("unit"))


def _term_months_from_quote(quote: str) -> float | None:
    match = TERM_MONTH_RE.search(quote)
    if not match:
        return None
    return _month_token(match.group("term"))


def _gross_margin_low_from_quote(quote: str) -> float | None:
    match = re.search(
        r"\b(?:EBITDA|gross)\s+margin\s+between\s+"
        r"(?P<low>\d+(?:\.\d+)?)%\s+and\s+(?P<high>\d+(?:\.\d+)?)%",
        quote,
        re.IGNORECASE,
    )
    if match:
        return _float_token(match.group("low"))
    match = re.search(
        r"\b(?:EBITDA|gross)\s+margin\s+of\s+(?P<margin>\d+(?:\.\d+)?)%",
        quote,
        re.IGNORECASE,
    )
    if match:
        return _float_token(match.group("margin"))
    return None


def _extract_life_years(quote: str) -> float | None:
    range_match = LIFE_RANGE_RE.search(quote)
    if range_match:
        return _number_token(range_match.group("high"))
    single_match = LIFE_SINGLE_RE.search(quote)
    if single_match:
        return _number_token(single_match.group("life"))
    return None


def _depreciation_policy_observation(quote: str) -> tuple[str, float] | None:
    bound_policy = _bound_depreciation_life_to_asset_class(quote)
    if bound_policy is not None:
        return bound_policy
    life = _extract_life_years(quote)
    if life is None:
        return None
    quote_lower = quote.lower()
    if life >= 25 and "building" in quote_lower and "server" not in quote_lower:
        return None
    return _asset_class_from_quote(quote), life


def _bound_depreciation_life_to_asset_class(quote: str) -> tuple[str, float] | None:
    lowered = quote.lower()
    for asset_class, terms in DEPRECIATION_ASSET_TERMS:
        for term in terms:
            for match in re.finditer(re.escape(term), lowered):
                segment = _asset_life_segment(quote, match.start())
                life = _extract_nearest_life_years(segment)
                if life is not None:
                    return asset_class, life
    return None


def _asset_life_segment(quote: str, start: int) -> str:
    max_end = min(len(quote), start + 220)
    sentence_end = quote.find(". ", start, max_end)
    if sentence_end >= 0:
        max_end = sentence_end
    return quote[start:max_end].strip()


def _extract_nearest_life_years(segment: str) -> float | None:
    candidates: list[tuple[int, float]] = []
    for match in LIFE_RANGE_RE.finditer(segment):
        life = _number_token(match.group("high"))
        if life is not None:
            candidates.append((match.start(), life))
    for match in LIFE_SINGLE_RE.finditer(segment):
        life = _number_token(match.group("life"))
        if life is not None:
            candidates.append((match.start(), life))
    if not candidates:
        return None
    first_life = min(candidates, key=lambda item: item[0])
    percent_match = PERCENT_RE.search(segment)
    if percent_match is not None and percent_match.start() < first_life[0]:
        return None
    return first_life[1]


def _asset_class_from_quote(quote: str) -> str:
    lowered = quote.lower()
    if "server" in lowered and "network" in lowered:
        return "servers and network equipment"
    if "data center" in lowered:
        return "data center equipment"
    if "software" in lowered:
        return "capitalized software"
    if "property and equipment" in lowered:
        return "property and equipment"
    return "equipment"


def _gpu_generation_from_quote(quote: str) -> str:
    lowered = quote.lower()
    for generation in ("blackwell", "hopper", "h100", "h200", "b200", "gb200", "gb300"):
        if generation in lowered:
            return generation.upper()
    return "UNSPECIFIED"


def _delivery_window_from_quote(quote: str) -> str:
    lowered = quote.lower()
    calendar_match = re.search(
        r"by the end of calendar year \d{4}",
        quote,
        re.IGNORECASE,
    )
    if calendar_match:
        return calendar_match.group(0).strip()
    if "fiscal years" not in lowered and "fiscal year" not in lowered:
        return ""
    match = re.search(r"fiscal years? [^.]{0,90}", quote, re.IGNORECASE)
    return match.group(0).strip() if match else ""


def _first_money(text: str) -> float | None:
    match = MONEY_RE.search(text)
    return _money_from_match(match) if match else None


def _money_after_commitment_marker(text: str) -> float | None:
    lowered = text.lower()
    for marker in ("commitments were", "purchase obligations", "capacity commitments"):
        index = lowered.find(marker)
        if index >= 0:
            return _first_money(text[index:])
    return None


def _money_from_match(match: re.Match[str]) -> float | None:
    raw_amount = match.group("amount")
    if not raw_amount:
        return None
    return _money_value(raw_amount, match.group("unit"))


def _money_value(raw_amount: str, unit: str | None) -> float | None:
    if not raw_amount:
        return None
    if not _has_valid_thousands_grouping(raw_amount):
        return None
    amount = float(raw_amount.replace(",", ""))
    normalized_unit = (unit or "").lower()
    if normalized_unit == "trillion":
        amount *= 1_000_000_000_000
    elif normalized_unit == "billion":
        amount *= 1_000_000_000
    elif normalized_unit == "million":
        amount *= 1_000_000
    return round(amount, 2)


def _has_valid_thousands_grouping(raw_amount: str) -> bool:
    if "," not in raw_amount:
        return True
    integer_part = raw_amount.split(".", 1)[0]
    groups = integer_part.split(",")
    if not groups or not (1 <= len(groups[0]) <= 3):
        return False
    return all(len(group) == 3 for group in groups[1:])


def _int_token(value: str) -> int | None:
    parsed = _float_token(value)
    return int(parsed) if parsed is not None else None


def _number_token(value: str) -> float | None:
    normalized = value.strip().lower()
    if normalized in NUMBER_WORDS:
        return NUMBER_WORDS[normalized]
    return _float_token(normalized)


def _month_token(value: str) -> float | None:
    normalized = value.strip().lower().replace("-", " ")
    month_words = {
        "six": 6.0,
        "twelve": 12.0,
        "eighteen": 18.0,
        "twenty three": 23.0,
        "twenty four": 24.0,
        "twenty five": 25.0,
    }
    if normalized in month_words:
        return month_words[normalized]
    return _float_token(normalized)


def _float_token(value: str) -> float | None:
    normalized = value.strip().lower().replace(",", "")
    if not normalized:
        return None
    try:
        return float(normalized)
    except ValueError:
        return None


def _fiscal_year_from_quote_or_row(quote: str, row: dict[str, str]) -> int:
    for pattern in (
        r"for the year ended [A-Za-z]+ \d{1,2}, (?P<year>20\d{2})",
        r"effective [A-Za-z]+ \d{1,2}, (?P<year>20\d{2})",
    ):
        match = re.search(pattern, quote, re.IGNORECASE)
        if match:
            return int(match.group("year"))
    filing_date = row.get("filing_date", "")
    if len(filing_date) >= 4 and filing_date[:4].isdigit():
        return int(filing_date[:4])
    return 0


def _window(text: str, start: int, radius: int) -> str:
    return text[max(0, start - radius) : start + radius].strip()


def _stable_id(prefix: str, row: dict[str, str], *parts: str) -> str:
    basis = "|".join(
        [
            prefix,
            row.get("cik", ""),
            row.get("accession_number", ""),
            row.get("primary_document", ""),
            *parts,
        ]
    )
    return f"{prefix}:{hashlib.sha256(basis.encode('utf-8')).hexdigest()[:16]}"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return [
            {key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(f)
        ]


def _read_optional_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return _read_csv(path)


def _merge_rows_by_id(
    existing_rows: list[dict[str, str]],
    new_rows: list[dict[str, Any]],
    id_field: str,
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in existing_rows:
        if _is_edgar_owned_row(row, id_field):
            continue
        row_id = str(row.get(id_field, ""))
        if not row_id or row_id in seen:
            continue
        merged.append(row)
        seen.add(row_id)
    for row in new_rows:
        row_id = str(row.get(id_field, ""))
        if not row_id or row_id in seen:
            continue
        merged.append(row)
        seen.add(row_id)
    return merged


def _is_edgar_owned_row(row: dict[str, str], id_field: str) -> bool:
    return row.get("source_type") == SourceType.SEC_EDGAR.value or row.get(id_field, "").startswith(
        "edgar-"
    )


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = CSV_FIELDS[path.name]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
