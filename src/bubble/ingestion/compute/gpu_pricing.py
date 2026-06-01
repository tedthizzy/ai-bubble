"""Acquire source-backed public GPU rental price observations."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

from bubble.ingestion.concurrency import (
    DomainFetchLimiter,
    FetchConcurrencyConfig,
    fetch_with_retries,
)
from bubble.models.base import HumanReviewStatus, Provenance, SourceType

FetchBytes = Callable[[str], bytes]

DEFAULT_USER_AGENT = "bubble-forensic-gpu-pricing-acquisition/0.1"

GPU_PRICE_FIELDS = [
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

ARTIFACT_FIELDS = [
    "source_id",
    "provider",
    "source_uri",
    "source_type",
    "local_path",
    "retrieved_at",
    "content_hash",
    "byte_count",
    "extracted_rows",
]

GPU_NAME_RE = re.compile(
    r"\b("
    r"B300|GB300|B200|GB200|H200|GH200|H100|A100|V100|A10|L40S|L40|L4|"
    r"RTX\s+PRO\s+6000|RTX\s+6000\s+ADA|RTX\s+A6000|A6000|RTX\s+5090|"
    r"RTX\s+4090|RTX\s+3090|RTX\s+A5000|A40"
    r")\b",
    re.IGNORECASE,
)

RUNPOD_PRICE_RE = re.compile(
    r"(?P<name>"
    r"H200|B200|RTX Pro 6000|H100 NVL|H100 PCIe|H100 SXM|A100 PCIe|A100 SXM|"
    r"L40S|RTX 6000 Ada|A40|L40|RTX A6000|RTX 5090|L4|RTX 3090|RTX 4090|RTX A5000"
    r")\s+"
    r"(?P<vram>\d+)\s+GB\s+VRAM\s+"
    r"(?P<ram>\d+)\s+GB\s+RAM\s+"
    r"(?P<vcpus>\d+)\s+vCPUs\s+"
    r"\$\s*(?P<price>\d+(?:\.\d+)?)\s*/hr",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GpuPricingSource:
    """One public pricing source to snapshot."""

    source_id: str
    provider: str
    source_uri: str


@dataclass(frozen=True)
class GpuPricingArtifact:
    """Raw pricing artifact captured for provenance."""

    source_id: str
    provider: str
    source_uri: str
    source_type: str
    local_path: str
    retrieved_at: str
    content_hash: str
    byte_count: int
    extracted_rows: int

    def to_csv_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GpuPricingAcquisitionSummary:
    """Summary for public GPU pricing acquisition."""

    sources_attempted: int
    sources_acquired: int
    sources_resumed: int
    observations_extracted: int
    workers: int
    other_requests_per_second: float
    other_domain_concurrency: int
    retry_attempts: int
    resume_enabled: bool
    errors: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GpuPricingAcquisitionResult:
    """Acquired raw artifacts and extracted GPU pricing rows."""

    artifacts: list[GpuPricingArtifact]
    observations: list[dict[str, Any]]
    summary: GpuPricingAcquisitionSummary


@dataclass(frozen=True)
class _SourceResult:
    source: GpuPricingSource
    artifact: GpuPricingArtifact | None
    observations: list[dict[str, Any]]
    resumed: bool
    error: str | None


DEFAULT_GPU_PRICING_SOURCES = (
    GpuPricingSource(
        source_id="lambda-pricing",
        provider="Lambda",
        source_uri="https://lambda.ai/pricing",
    ),
    GpuPricingSource(
        source_id="runpod-pricing",
        provider="RunPod",
        source_uri="https://www.runpod.io/pricing",
    ),
)


def acquire_gpu_pricing(
    *,
    output_dir: str | Path = "data/compute",
    sources: Sequence[GpuPricingSource] = DEFAULT_GPU_PRICING_SOURCES,
    fetch_bytes: FetchBytes | None = None,
    max_workers: int = 8,
    other_requests_per_second: float = 8.0,
    other_domain_concurrency: int = 4,
    retry_attempts: int = 3,
    retry_backoff_seconds: float = 0.5,
    resume: bool = True,
) -> GpuPricingAcquisitionResult:
    """Fetch public GPU rental pricing pages and write normalized observations."""

    output = Path(output_dir)
    raw_dir = output / "raw_gpu_pricing"
    raw_dir.mkdir(parents=True, exist_ok=True)
    fetcher = fetch_bytes or _fetch_bytes
    limiter = DomainFetchLimiter(
        FetchConcurrencyConfig(
            max_workers=max_workers,
            other_domain_concurrency=other_domain_concurrency,
            other_requests_per_second=other_requests_per_second,
            retry_attempts=retry_attempts,
            retry_backoff_seconds=retry_backoff_seconds,
        )
    )

    artifacts: list[GpuPricingArtifact] = []
    observations: list[dict[str, Any]] = []
    errors: dict[str, str] = {}
    source_results: list[_SourceResult] = []
    worker_count = max(1, min(max_workers, len(sources) or 1))

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(
                _acquire_one_source,
                source,
                raw_dir,
                fetcher,
                limiter,
                retry_attempts,
                retry_backoff_seconds,
                resume,
            ): source
            for source in sources
        }
        for future in as_completed(futures):
            source_result = future.result()
            source_results.append(source_result)
            if source_result.error:
                errors[source_result.source.source_id] = source_result.error
                continue
            if source_result.artifact is not None:
                artifacts.append(source_result.artifact)
            observations.extend(source_result.observations)

    observations = _dedupe_observations(observations)
    _write_csv(output / "gpu_price_observations.csv", observations, GPU_PRICE_FIELDS)
    _write_csv(
        output / "gpu_price_source_artifacts.csv",
        [artifact.to_csv_row() for artifact in artifacts],
        ARTIFACT_FIELDS,
    )
    summary = GpuPricingAcquisitionSummary(
        sources_attempted=len(sources),
        sources_acquired=len(artifacts),
        sources_resumed=sum(
            1 for result in source_results if result.artifact is not None and result.resumed
        ),
        observations_extracted=len(observations),
        workers=worker_count,
        other_requests_per_second=other_requests_per_second,
        other_domain_concurrency=other_domain_concurrency,
        retry_attempts=retry_attempts,
        resume_enabled=resume,
        errors=errors,
    )
    (output / "gpu_pricing_acquisition.summary.json").write_text(
        json.dumps(summary.to_dict(), indent=2, sort_keys=True)
    )
    return GpuPricingAcquisitionResult(
        artifacts=artifacts,
        observations=observations,
        summary=summary,
    )


def parse_gpu_pricing_snapshot(
    *,
    provider: str,
    raw: bytes,
    source_uri: str,
    retrieved_at: str,
    content_hash: str,
) -> list[dict[str, Any]]:
    """Parse one fetched public pricing artifact into normalized observations."""

    normalized_provider = provider.strip().lower()
    if normalized_provider == "lambda":
        parsed = _parse_lambda_pricing(raw)
    elif normalized_provider == "runpod":
        parsed = _parse_runpod_pricing(raw)
    else:
        parsed = []
    observed_date = retrieved_at[:10]
    rows: list[dict[str, Any]] = []
    for item in parsed:
        observation_id = _stable_id(
            "gpu-price",
            provider,
            item["gpu_generation"],
            str(item["observed_cloud_rental_rate_usd_per_hour"]),
            item["contract_term"],
            item["page_or_section"],
            source_uri,
        )
        rows.append(
            {
                "observation_id": observation_id,
                "gpu_generation": item["gpu_generation"],
                "observed_date": observed_date,
                "observed_secondary_price_usd": "",
                "observed_cloud_rental_rate_usd_per_hour": item[
                    "observed_cloud_rental_rate_usd_per_hour"
                ],
                "original_price_usd": "",
                "peak_price_usd": "",
                "provider_or_marketplace": provider,
                "region": "",
                "contract_term": item["contract_term"],
                "source_uri": source_uri,
                "source_type": SourceType.COMPANY_IR.value,
                "retrieved_at": retrieved_at,
                "source_confidence": "0.82",
                "human_review_status": HumanReviewStatus.PENDING.value,
                "page_or_section": item["page_or_section"],
                "content_hash": content_hash,
                "document_id": item["document_id"],
                "filing_accession": "",
            }
        )
    return rows


def _acquire_one_source(
    source: GpuPricingSource,
    raw_dir: Path,
    fetcher: FetchBytes,
    limiter: DomainFetchLimiter,
    retry_attempts: int,
    retry_backoff_seconds: float,
    resume: bool,
) -> _SourceResult:
    try:
        resumed = False
        local_path = _latest_raw_artifact(raw_dir, source) if resume else None
        if local_path is not None:
            raw = local_path.read_bytes()
            retrieved_at = datetime.fromtimestamp(local_path.stat().st_mtime, UTC).isoformat()
            resumed = True
        else:
            raw = fetch_with_retries(
                lambda: limiter.run(
                    source.source_uri,
                    lambda: fetcher(source.source_uri),
                ),
                attempts=retry_attempts,
                backoff_seconds=retry_backoff_seconds,
            )
            retrieved_at = datetime.now(UTC).isoformat()
            content_hash = Provenance.compute_content_hash(raw)
            local_path = raw_dir / f"{source.source_id}-{content_hash[:12]}.html"
            local_path.write_bytes(raw)
        content_hash = Provenance.compute_content_hash(raw)
        observations = parse_gpu_pricing_snapshot(
            provider=source.provider,
            raw=raw,
            source_uri=source.source_uri,
            retrieved_at=retrieved_at,
            content_hash=content_hash,
        )
        artifact = GpuPricingArtifact(
            source_id=source.source_id,
            provider=source.provider,
            source_uri=source.source_uri,
            source_type=SourceType.COMPANY_IR.value,
            local_path=str(local_path),
            retrieved_at=retrieved_at,
            content_hash=content_hash,
            byte_count=len(raw),
            extracted_rows=len(observations),
        )
        return _SourceResult(
            source=source,
            artifact=artifact,
            observations=observations,
            resumed=resumed,
            error=None,
        )
    except Exception as exc:
        return _SourceResult(
            source=source,
            artifact=None,
            observations=[],
            resumed=False,
            error=str(exc),
        )


def _latest_raw_artifact(raw_dir: Path, source: GpuPricingSource) -> Path | None:
    candidates = sorted(
        raw_dir.glob(f"{source.source_id}-*.html"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _fetch_bytes(source_uri: str) -> bytes:
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    with httpx.Client(timeout=45.0, follow_redirects=True) as client:
        response = client.get(source_uri, headers=headers)
        response.raise_for_status()
        return bytes(response.content)


def _parse_lambda_pricing(raw: bytes) -> list[dict[str, Any]]:
    soup = BeautifulSoup(raw.decode("utf-8", errors="ignore"), "lxml")
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, float, str]] = set()
    for tr in soup.select("tr"):
        cells = [_clean_text(cell.get_text(" ", strip=True)) for cell in tr.select("th,td")]
        if len(cells) < 2:
            continue
        row_text = _clean_text(" ".join(cells))
        price = _price_from_text(row_text)
        if price is None:
            continue
        gpu_name = cells[0]
        generation = _gpu_generation_from_name(gpu_name)
        if not generation:
            continue
        if len(cells) >= 4 and re.search(r"\b(?:week|year)", cells[1], re.IGNORECASE):
            term_parts = [
                "one_click_cluster",
                f"duration={cells[1].replace('\u2013', '-')}",
                f"gpu_count={cells[2]}",
            ]
        else:
            term_parts = ["on_demand"]
        if len(cells) >= 5 and term_parts[0] == "on_demand":
            term_parts.append(f"vcpus={cells[2]}")
            term_parts.append(f"ram={cells[3]}")
        key = (row_text, price, generation)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "gpu_generation": generation,
                "observed_cloud_rental_rate_usd_per_hour": price,
                "contract_term": ";".join(term_parts),
                "page_or_section": f"Lambda pricing row: {row_text[:220]}",
                "document_id": "lambda-pricing-page",
            }
        )
    return rows


def _parse_runpod_pricing(raw: bytes) -> list[dict[str, Any]]:
    soup = BeautifulSoup(raw.decode("utf-8", errors="ignore"), "lxml")
    text = _clean_text(soup.get_text(" ", strip=True))
    section_start = text.find("Community Cloud")
    section_end = text.find("Serverless")
    if section_start >= 0 and section_end > section_start:
        text = text[section_start:section_end]
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, float]] = set()
    for match in RUNPOD_PRICE_RE.finditer(text):
        gpu_name = _clean_text(match.group("name"))
        generation = _gpu_generation_from_name(gpu_name)
        price = float(match.group("price"))
        key = (gpu_name.lower(), price)
        if not generation or key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "gpu_generation": generation,
                "observed_cloud_rental_rate_usd_per_hour": price,
                "contract_term": (
                    "public_pricing_page_default_cloud;"
                    f"vram_gb={match.group('vram')};"
                    f"ram_gb={match.group('ram')};"
                    f"vcpus={match.group('vcpus')}"
                ),
                "page_or_section": (
                    "RunPod pricing row: "
                    f"{gpu_name} {match.group('vram')} GB VRAM "
                    f"{match.group('ram')} GB RAM {match.group('vcpus')} vCPUs "
                    f"${price}/hr"
                ),
                "document_id": "runpod-pricing-page",
            }
        )
    return rows


def _gpu_generation_from_name(name: str) -> str:
    match = GPU_NAME_RE.search(name)
    if not match:
        return ""
    value = match.group(1).upper().replace(" ", "")
    aliases = {
        "A6000": "RTXA6000",
        "RTX6000ADA": "RTX6000ADA",
        "RTXPRO6000": "RTXPRO6000",
        "RTXA6000": "RTXA6000",
        "RTXA5000": "RTXA5000",
    }
    return aliases.get(value, value)


def _price_from_text(text: str) -> float | None:
    match = re.search(r"\$\s*(?P<price>\d+(?:\.\d+)?)", text)
    return float(match.group("price")) if match else None


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _dedupe_observations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for row in rows:
        key = (
            str(row.get("provider_or_marketplace", "")),
            str(row.get("gpu_generation", "")),
            str(row.get("observed_cloud_rental_rate_usd_per_hour", "")),
            str(row.get("contract_term", "")),
            str(row.get("source_uri", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return sorted(
        deduped,
        key=lambda item: (
            str(item.get("provider_or_marketplace", "")),
            str(item.get("gpu_generation", "")),
            float(item.get("observed_cloud_rental_rate_usd_per_hour") or 0.0),
            str(item.get("contract_term", "")),
        ),
    )


def _stable_id(prefix: str, *parts: str) -> str:
    basis = "|".join(parts)
    return f"{prefix}:{hashlib.sha256(basis.encode('utf-8')).hexdigest()[:16]}"


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
