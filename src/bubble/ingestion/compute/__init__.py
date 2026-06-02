"""Source-backed compute economics ingestion."""

from .debt_service_terms import (
    DEBT_SERVICE_TERM_FIELDS,
    DebtServiceTerm,
    normalize_debt_service_card_rows,
    summarize_debt_service_terms,
)
from .economic_commitments import (
    EconomicCommitmentTerm,
    extract_economic_commitments,
    extract_economic_commitments_from_rows,
)
from .edgar_extraction import ComputeEdgarExtractionSummary, extract_compute_economics_from_edgar
from .gpu_pricing import GpuPricingAcquisitionSummary, acquire_gpu_pricing
from .loader import load_compute_economics

__all__ = [
    "DEBT_SERVICE_TERM_FIELDS",
    "ComputeEdgarExtractionSummary",
    "DebtServiceTerm",
    "EconomicCommitmentTerm",
    "GpuPricingAcquisitionSummary",
    "acquire_gpu_pricing",
    "extract_compute_economics_from_edgar",
    "extract_economic_commitments",
    "extract_economic_commitments_from_rows",
    "load_compute_economics",
    "normalize_debt_service_card_rows",
    "summarize_debt_service_terms",
]
