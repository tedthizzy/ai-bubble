import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "check_direct_tier_debt_service_field_coverage.py"
)
SPEC = importlib.util.spec_from_file_location(
    "check_direct_tier_debt_service_field_coverage",
    SCRIPT_PATH,
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load debt-service field coverage checker")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

build_coverage_rows = MODULE.build_coverage_rows
summarize = MODULE.summarize


def test_secured_facility_core_structural_fields_are_verified() -> None:
    rows = [
        {
            "entity": "IREN",
            "facility": "Hardware 3 DDTL",
            "field": "rate_floating",
            "source_tier": "primary_EDGAR",
            "filing_accession": "0001",
            "source_quote": "Borrowings bear interest at term SOFR plus 2.25%.",
        },
        {
            "entity": "IREN",
            "facility": "Hardware 3 DDTL",
            "field": "collateral",
            "source_tier": "primary_EDGAR",
            "filing_accession": "0001",
            "source_quote": "secured by all assets including GPUs and contract cash flows.",
        },
        {
            "entity": "IREN",
            "facility": "Hardware 3 DDTL",
            "field": "recourse",
            "source_tier": "primary_EDGAR",
            "filing_accession": "0001",
            "source_quote": "Parent entered into Limited Parent Guarantees.",
        },
        {
            "entity": "IREN",
            "facility": "Hardware 3 DDTL",
            "field": "covenants",
            "source_tier": "primary_EDGAR",
            "filing_accession": "0001",
            "source_quote": "customary negative covenants.",
        },
    ]

    [coverage] = build_coverage_rows(rows)

    assert coverage.status == "core_structural_fields_verified"
    assert coverage.field_groups_verified == "collateral;covenant;rate;recourse"
    assert coverage.missing_core_groups == ""
    assert summarize([coverage])["primary_edgar_rows"] == 4


def test_unsecured_convertible_does_not_require_collateral() -> None:
    rows = [
        {
            "entity": "CleanSpark",
            "facility": "Nov2025 Conv Notes 2032",
            "field": "security",
            "source_tier": "primary_EDGAR",
            "filing_accession": "0002",
            "source_quote": "The notes are senior unsecured obligations and are not guaranteed.",
        },
        {
            "entity": "CleanSpark",
            "facility": "Nov2025 Conv Notes 2032",
            "field": "recourse",
            "source_tier": "primary_EDGAR",
            "filing_accession": "0002",
            "source_quote": "senior unsecured obligations of the Company.",
        },
    ]

    [coverage] = build_coverage_rows(rows)

    assert coverage.status == "parent_unsecured_recourse_verified"
    assert "collateral" not in coverage.missing_core_groups
    assert coverage.missing_core_groups == "rate;covenant"


def test_aggregate_context_row_is_not_treated_as_missing_facility_terms() -> None:
    rows = [
        {
            "entity": "IREN",
            "facility": "Hardware 3 (aggregate)",
            "field": "aggregate_financing_usd",
            "source_tier": "primary_EDGAR",
            "filing_accession": "0003",
            "source_quote": "aggregate financing of approximately $3.6 billion.",
        }
    ]

    [coverage] = build_coverage_rows(rows)

    assert coverage.status == "aggregate_context_only"
    assert coverage.field_groups_verified == "context"
    assert coverage.missing_core_groups == ""
