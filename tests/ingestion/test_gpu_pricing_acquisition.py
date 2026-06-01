from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from bubble.ingestion.compute.gpu_pricing import (
    GpuPricingSource,
    acquire_gpu_pricing,
    parse_gpu_pricing_snapshot,
)
from bubble.models.base import Provenance

if TYPE_CHECKING:
    from pathlib import Path


LAMBDA_HTML = b"""
<html><body>
<table>
  <thead><tr><th>Plan</th><th>VRAM/GPU</th><th>vCPUs</th><th>RAM</th><th>PRICE/GPU/HR*</th></tr></thead>
  <tbody>
    <tr data-plan="NVIDIA H100 SXM">
      <th>NVIDIA H100 SXM</th><td>80 GB</td><td>208</td><td>1800 GiB</td><td>$3.99</td>
    </tr>
    <tr data-plan="NVIDIA A100 SXM">
      <th>NVIDIA A100 SXM</th><td>80 GB</td><td>240</td><td>1800 GiB</td><td>$2.79</td>
    </tr>
  </tbody>
</table>
</body></html>
"""

RUNPOD_HTML = b"""
<html><body>
Community Cloud Secure Cloud Per hour
H200 141 GB VRAM 276 GB RAM 24 vCPUs $ 4.39 /hr H200
B200 180 GB VRAM 283 GB RAM 28 vCPUs $ 5.89 /hr B200
H100 PCIe 80 GB VRAM 188 GB RAM 16 vCPUs $ 2.89 /hr H100 PCIe
Serverless Cost effective for every inference workload.
</body></html>
"""


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def test_parse_lambda_gpu_pricing_snapshot() -> None:
    content_hash = Provenance.compute_content_hash(LAMBDA_HTML)

    rows = parse_gpu_pricing_snapshot(
        provider="Lambda",
        raw=LAMBDA_HTML,
        source_uri="https://lambda.ai/pricing",
        retrieved_at="2026-06-01T00:00:00+00:00",
        content_hash=content_hash,
    )

    assert [row["gpu_generation"] for row in rows] == ["H100", "A100"]
    assert rows[0]["observed_cloud_rental_rate_usd_per_hour"] == 3.99
    assert rows[0]["source_uri"] == "https://lambda.ai/pricing"
    assert rows[0]["content_hash"] == content_hash
    assert rows[0]["retrieved_at"] == "2026-06-01T00:00:00+00:00"


def test_parse_runpod_gpu_pricing_snapshot() -> None:
    rows = parse_gpu_pricing_snapshot(
        provider="RunPod",
        raw=RUNPOD_HTML,
        source_uri="https://www.runpod.io/pricing",
        retrieved_at="2026-06-01T00:00:00+00:00",
        content_hash=Provenance.compute_content_hash(RUNPOD_HTML),
    )

    assert [row["gpu_generation"] for row in rows] == ["H200", "B200", "H100"]
    assert rows[2]["observed_cloud_rental_rate_usd_per_hour"] == 2.89
    assert rows[2]["contract_term"].startswith("public_pricing_page_default_cloud")


def test_acquire_gpu_pricing_writes_raw_artifacts_and_observations(tmp_path: Path) -> None:
    sources = (
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

    def fetch_bytes(source_uri: str) -> bytes:
        if "lambda" in source_uri:
            return LAMBDA_HTML
        return RUNPOD_HTML

    result = acquire_gpu_pricing(
        output_dir=tmp_path,
        sources=sources,
        fetch_bytes=fetch_bytes,
        max_workers=2,
    )

    assert result.summary.sources_attempted == 2
    assert result.summary.sources_acquired == 2
    assert result.summary.sources_resumed == 0
    assert result.summary.observations_extracted == 5
    assert result.summary.workers == 2
    assert result.summary.other_requests_per_second == 8.0
    assert result.summary.other_domain_concurrency == 4
    assert result.summary.retry_attempts == 3
    assert result.summary.resume_enabled is True
    assert (tmp_path / "raw_gpu_pricing").is_dir()
    assert (tmp_path / "gpu_pricing_acquisition.summary.json").is_file()

    observations = _read_csv(tmp_path / "gpu_price_observations.csv")
    artifacts = _read_csv(tmp_path / "gpu_price_source_artifacts.csv")
    assert len(observations) == 5
    assert len(artifacts) == 2
    assert all(row["source_uri"].startswith("https://") for row in observations)
    assert all(row["content_hash"] for row in observations)
    assert all(row["retrieved_at"] for row in observations)


def test_acquire_gpu_pricing_resumes_existing_raw_artifact(tmp_path: Path) -> None:
    source = GpuPricingSource(
        source_id="lambda-pricing",
        provider="Lambda",
        source_uri="https://lambda.ai/pricing",
    )
    calls = 0

    def fetch_bytes(_source_uri: str) -> bytes:
        nonlocal calls
        calls += 1
        return LAMBDA_HTML

    first = acquire_gpu_pricing(
        output_dir=tmp_path,
        sources=(source,),
        fetch_bytes=fetch_bytes,
        max_workers=4,
        other_requests_per_second=12.0,
        other_domain_concurrency=3,
        retry_attempts=5,
    )
    second = acquire_gpu_pricing(
        output_dir=tmp_path,
        sources=(source,),
        fetch_bytes=fetch_bytes,
        max_workers=4,
    )

    assert calls == 1
    assert first.summary.sources_resumed == 0
    assert second.summary.sources_resumed == 1
    assert second.summary.sources_acquired == 1
    assert second.summary.observations_extracted == 2
