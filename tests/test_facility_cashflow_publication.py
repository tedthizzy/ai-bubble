"""Primary-source integrity and explicit payment-table extraction."""

import hashlib
import json
from datetime import date
from pathlib import Path

import pytest
from scripts.build_facility_cashflows import (
    calculation_hashes,
    extract_principal_payments,
    load_calculated_report,
    verify_fact,
)

from bubble.analysis.facility_cashflows import analyze_facility
from bubble.models.facility import FacilityCase, FacilityFact

ROOT = Path(__file__).resolve().parents[1]


def test_extracts_dated_principal_installments_without_redemption_price_table() -> None:
    text = (
        "Section 14.02 Payment Schedule 103 Table of contents "
        "Section 14.02 Payment Schedule Principal Payment Date Installment Amount "
        "May 15, 2028 $ 41,429,039 November 15, 2028 $ 44,959,857 "
        "Section 14.03 Modifications 2028 103.500%"
    )
    rows = extract_principal_payments(text, "indenture", date(2026, 4, 30))
    assert [row["due_on"] for row in rows] == ["2028-05-15", "2028-11-15"]
    assert [row["amount"]["value"] for row in rows] == [41_429_039, 44_959_857]
    for row in rows:
        verify_fact(FacilityFact.model_validate(row["amount"]), {"indenture": text})


def test_missing_table_and_changed_numeric_conversion_stop_publication() -> None:
    with pytest.raises(ValueError, match="explicit principal"):
        extract_principal_payments("Maturity 2030", "source", date(2026, 4, 30))
    fact = FacilityFact(
        value=1_400_000_000,
        unit="USD",
        source_id="source",
        quote="$1.4 billion",
        source_token="1.4",
        multiplier=1e9,
        observed_on=date(2026, 4, 30),
    )
    verify_fact(fact, {"source": "$1.4 billion"})
    with pytest.raises(ValueError, match="conversion"):
        verify_fact(fact.model_copy(update={"value": 14_000_000_000.0}), {"source": "$1.4 billion"})
    with pytest.raises(ValueError, match="quote"):
        verify_fact(fact, {"source": "$1.5 billion"})


def test_clone_loads_matching_calculation_without_raw_corpus_and_rejects_stale_output(
    tmp_path: Path,
) -> None:
    folder = tmp_path / "analysis"
    folder.mkdir()
    inputs = folder / "facility_inputs_2026-10-17.json"
    inputs.write_text('{"as_of":"2026-10-17"}')
    expected = {
        "as_of": "2026-10-17",
        "input_sha256": hashlib.sha256(inputs.read_bytes()).hexdigest(),
        "calculation_source_sha256": calculation_hashes(),
        "cases": [],
    }
    artifact = folder / "facility_cashflows_2026-10-17.json"
    artifact.write_text(json.dumps(expected))
    assert load_calculated_report(tmp_path, "2026-10-17") == expected
    artifact.write_text(json.dumps({**expected, "calculation_source_sha256": {}}))
    with pytest.raises(ValueError, match="Build a current"):
        load_calculated_report(tmp_path, "2026-10-17")
    artifact.write_text(json.dumps(expected))
    inputs.write_text('{"as_of":"2026-10-17", "changed":true}')
    with pytest.raises(ValueError, match="Build a current"):
        load_calculated_report(tmp_path, "2026-10-17")


def test_committed_calculation_reproduces_cases_and_preserves_redacted_unknowns() -> None:
    inputs = json.loads((ROOT / "analysis/facility_inputs_2026-10-17.json").read_text())
    report = load_calculated_report(ROOT, "2026-10-17")
    calculated = [
        analyze_facility(FacilityCase.model_validate(row), date(2026, 10, 17))
        for row in inputs["cases"]
    ]
    assert report["cases"] == calculated
    cases = {row["id"]: row for row in calculated}
    assert all(row["debt_service_coverage_ratio"] is None for row in calculated)
    river = cases["hut-river-bend"]
    assert river["instruments"][0]["scheduled_cash_payments"][0]["interest_usd"] == 109_005_000
    year = next(row for row in river["annual_scheduled_debt_service"] if row["year"] == "2028")
    assert year["debt_service_usd"] == pytest.approx(286_346_252.95)
    assert river["annual_contract_average_usd"] == pytest.approx(7e9 / 15)
    assert cases["hut-beacon-point-phase2"]["instruments"] == []
    iren = cases["iren-horizon-microsoft"]
    assert iren["annual_interest_run_rate_usd"] is None
    assert iren["known_cash_interest_floor_usd"] == 31_290_000
    assert all(
        "[***]" in debt["facts"]["principal_schedule_status"]["quote"]
        for debt in iren["instruments"]
    )
    assert cases["coreweave-ddtl4"]["annual_interest_run_rate_usd"] is None
    assert cases["core-scientific-colocation"]["instruments"] == []
    assert cases["core-scientific-colocation"]["annual_contract_average_usd"] is None
    assert "Abernathy" in report["retired_interests"][0]["project"]


def test_each_facility_is_reachable_from_its_published_entity() -> None:
    graph = json.loads((ROOT / "viz/graph_data.json").read_text())
    entities = {row["id"] for row in graph["nodes"]}
    assert graph["facility_cashflows"]["cases"]
    assert all(row["entity"] in entities for row in graph["facility_cashflows"]["cases"])
