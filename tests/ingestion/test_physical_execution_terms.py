from __future__ import annotations

import json

from bubble.ingestion.physical import extract_physical_execution_terms


def _row(text: str, **metadata: str) -> dict[str, str]:
    return {
        "source_id": "fixture",
        "source_uri": "https://example.test/permit",
        "document_id": "doc-1",
        "metadata": json.dumps(metadata),
        "text": text,
    }


def test_extracts_behind_meter_air_permit_handles() -> None:
    row = _row(
        "Stargate Abilene Longhorn DC is supported by TCEQ Standard Permit "
        "Reg 177263, Project 387309, RN112029079. The project uses behind-the-meter "
        "gas generation of approximately 360 MW for onsite use only and has no ERCOT "
        "interconnection queue INR because it is off-grid by design.",
        project_name="Stargate Abilene",
        operator="Crusoe / OpenAI / Oracle",
        jurisdiction="Texas",
        authority="TCEQ",
        permit_or_docket="Reg 177263",
    )

    terms = extract_physical_execution_terms(row)
    values = {(term.term_type, term.value, term.unit) for term in terms}

    assert ("air_permit_id", "177263", "id") in values
    assert ("air_permit_id", "387309", "id") in values
    assert ("air_permit_id", "112029079", "id") in values
    assert ("onsite_generation_mw", "360", "MW") in values
    assert any(term.term_type == "behind_the_meter_or_off_grid" for term in terms)
    assert any(term.term_type == "queue_bypass_or_no_queue" for term in terms)
    assert any(term.project_name == "Stargate Abilene" for term in terms)


def test_extracts_off_grid_microgrid_queue_bypass_and_litigation() -> None:
    row = _row(
        "Adams Fork Data Center Energy Campus received WV DEP DAQ R13-3714 "
        "and R13-3715 air permits for two OFF-GRID gas microgrid plants, each "
        "larger than 2,400 MW with 117 engines. WV HB 2014 enabled the project "
        "to sidestep PJM's greater than six-year interconnection queue. A federal "
        "lawsuit filed in Dec. 2025 challenges the permits.",
        project_name="Adams Fork",
        operator="TransGas",
        jurisdiction="West Virginia",
        authority="WV DEP DAQ",
    )

    terms = extract_physical_execution_terms(row)
    values = {(term.term_type, term.value, term.unit) for term in terms}

    assert ("air_permit_id", "R13-3714", "id") in values
    assert ("air_permit_id", "R13-3715", "id") in values
    assert ("onsite_generation_mw", "2400", "MW") in values
    assert any(term.term_type == "behind_the_meter_or_off_grid" for term in terms)
    assert any(term.term_type == "queue_bypass_or_no_queue" for term in terms)
    assert any(term.term_type == "permit_litigation_or_enforcement_risk" for term in terms)


def test_extracts_utility_grid_buildout_and_ratepayer_transfer() -> None:
    row = _row(
        "The LPSC approval order approved Entergy Louisiana's Hyperion project "
        "for Meta Richland, including 2,260 MW of new CCGT generation, about "
        "100 miles of 500 kV transmission lines, and substations. If the data "
        "center load does not materialize, ratepayers could bear stranded "
        "rate-base costs through recovery of utility infrastructure.",
        project_name="Meta Richland Hyperion",
        operator="Entergy Louisiana / Meta",
        jurisdiction="Louisiana",
        authority="LPSC",
    )

    terms = extract_physical_execution_terms(row)
    values = {(term.term_type, term.value, term.unit) for term in terms}

    assert ("utility_generation_capacity_mw", "2260", "MW") in values
    assert any(term.term_type == "puc_or_utility_approval" for term in terms)
    assert any(term.term_type == "ratepayer_stranded_asset_transfer" for term in terms)
    assert not any(term.term_type == "queue_bypass_or_no_queue" for term in terms)


def test_ignores_generic_financing_text_without_physical_execution_terms() -> None:
    row = _row(
        "The issuer may offer from time to time senior notes, common stock, "
        "preferred stock, depositary shares, warrants and units under this "
        "registration statement.",
        project_name="Generic issuer",
    )

    assert extract_physical_execution_terms(row) == []
