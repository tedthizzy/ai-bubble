from __future__ import annotations

import json

from bubble.ingestion.regulatory import extract_ratepayer_terms


def _row(text: str, **metadata: str) -> dict[str, str]:
    return {
        "source_id": "fixture",
        "source_uri": "https://example.test/source",
        "document_id": "doc-1",
        "metadata": json.dumps(metadata),
        "text": text,
    }


def test_extracts_fpl_large_load_tariff_terms() -> None:
    row = _row(
        "FPL's as filed case proposed that the LLCS schedules apply to new or "
        "incremental loads of 25 MW or greater, with a load factor of 85% or "
        "higher, and a take-or-pay provision set at 90%. Customers are also at "
        "risk of subsidizing the increased generation needed to power these "
        "loads if the commission and utilities do not properly insulate the "
        "everyday customer. The SIP Proposal also reduces the Incremental "
        "Generation Charge for LLCS-1 from $28.07 per kW to $12.18 per kW of demand.",
        utility_family="FPL / NextEra",
        jurisdiction="Florida",
        regulator="Florida Public Service Commission",
        docket_or_filing="20250011-EI",
    )

    terms = extract_ratepayer_terms(row)
    values = {(term.term_type, term.value, term.unit) for term in terms}

    assert ("large_load_threshold_mw", "25", "MW") in values
    assert ("load_factor_pct", "85", "pct") in values
    assert ("take_or_pay_pct", "90", "pct") in values
    assert ("incremental_generation_charge_per_kw", "28.07", "USD_per_kW") in values
    assert ("incremental_generation_charge_per_kw", "12.18", "USD_per_kW") in values
    assert any(term.term_type == "ratepayer_subsidy_risk" for term in terms)
    assert any(term.docket_or_filing == "20250011-EI" for term in terms)


def test_extracts_xcel_colorado_customer_protection_terms() -> None:
    row = _row(
        "On April 2, Xcel Energy filed a new Large Load Tariff proposal, "
        "Proceeding No. 26AL-0137E, to address high-demand energy projects, "
        "such as large-scale data centers. Under the proposal, large-load "
        "customers requiring 50 MW or more would be required to cover the costs "
        "of the specific transmission lines, substations, interconnection "
        "upgrades and new electric generation capacity needed to serve them. "
        "New customers using between 20 and 50 MW may also be subject to the "
        "tariff. The proposal includes preventing existing ratepayers from "
        "subsidizing infrastructure upgrades and requiring contracts of 15 "
        "years or more.",
        utility_family="Xcel Energy",
        jurisdiction="Colorado",
        regulator="Colorado Public Utilities Commission",
        docket_or_filing="26AL-0137E",
    )

    terms = extract_ratepayer_terms(row)
    values = {(term.term_type, term.value, term.unit) for term in terms}

    assert ("large_load_threshold_mw", "50", "MW") in values
    assert ("large_load_threshold_mw", "20", "MW") in values
    assert ("minimum_contract_term_years", "15", "years") in values
    assert any(term.term_type == "dedicated_infrastructure_cost_recovery" for term in terms)
    assert any(term.term_type == "ratepayer_subsidy_protection" for term in terms)
    assert any(term.term_type == "data_center_load_driver" for term in terms)


def test_extracts_minnesota_exit_fee_and_customer_class_terms() -> None:
    row = _row(
        "Should the Commission set the demand size threshold for the new tariffs "
        "at 100 MW, or adopt an alternative threshold? Should the Commission "
        "modify the minimum ESA term length? Should the Commission modify the "
        "minimum billing demand and exit fee calculations? Should the Commission "
        "treat super-large customers as a separate customer class and explicitly "
        "require Xcel to provide bring your own generation BYOG avenues? The "
        "approval includes an 80% demand charge fee if a large facility exits "
        "the contract early.",
        utility_family="Xcel Energy",
        jurisdiction="Minnesota",
        regulator="Minnesota Public Utilities Commission",
        docket_or_filing="E022/M-25-289",
    )

    terms = extract_ratepayer_terms(row)
    values = {(term.term_type, term.value, term.unit) for term in terms}

    assert ("large_load_threshold_mw", "100", "MW") in values
    assert ("exit_fee_pct", "80", "pct") in values
    assert any(term.term_type == "separate_customer_class" for term in terms)
    assert any(term.term_type == "bring_your_own_generation" for term in terms)


def test_extracts_georgia_power_irp_load_growth_without_ratepayer_decision() -> None:
    row = _row(
        "Georgia Power maintains active engagement and discussions with large "
        "load customers. The risk-adjusted load forecast reflects approximately "
        "8,200 MW of load growth through the winter of 2030/2031. In the near "
        "term, the Company projects nearly 6,000 MW of load growth as early as "
        "the winter of 2028/2029.",
        utility_family="Southern / Georgia Power",
        jurisdiction="Georgia",
        regulator="Georgia Public Service Commission",
        docket_or_filing="Docket 56002",
    )

    terms = extract_ratepayer_terms(row)
    values = {(term.term_type, term.value, term.unit) for term in terms}

    assert ("load_growth_mw", "8200", "MW") in values
    assert ("load_growth_mw", "6000", "MW") in values
    assert not any(term.term_type == "ratepayer_subsidy_protection" for term in terms)
