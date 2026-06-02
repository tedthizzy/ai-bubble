import csv
import json
import subprocess
import sys
from pathlib import Path

from bubble.ingestion.compute import normalize_debt_service_card_rows, summarize_debt_service_terms

COREWEAVE_CARD_ROWS = [
    {
        "entity": "CoreWeave",
        "facility": "DDTL 3.0",
        "field": "facility_size_usd",
        "value": "$2.6 billion",
        "source_tier": "primary_8k",
        "source": "EDGAR accession 0001769628-25-000033",
    },
    {
        "entity": "CoreWeave",
        "facility": "DDTL 3.0",
        "field": "borrower",
        "value": "CCAC VII (SPV); Parent guarantee",
        "source_tier": "primary_8k",
        "source": "EDGAR accession 0001769628-25-000033",
    },
    {
        "entity": "CoreWeave",
        "facility": "DDTL 3.0",
        "field": "maturity",
        "value": "2030-08-21",
        "source_tier": "primary_8k",
        "source": "EDGAR accession 0001769628-25-000033",
    },
    {
        "entity": "CoreWeave",
        "facility": "DDTL 3.0",
        "field": "rate_floating",
        "value": "daily compounded SOFR + 4.00% (0% floor)",
        "source_tier": "primary_8k",
        "source": "EDGAR accession 0001769628-25-000033",
    },
    {
        "entity": "CoreWeave",
        "facility": "DDTL 3.0",
        "field": "undrawn_fee",
        "value": "0.50% per annum",
        "source_tier": "primary_8k",
        "source": "EDGAR accession 0001769628-25-000033",
    },
    {
        "entity": "CoreWeave",
        "facility": "DDTL 3.0",
        "field": "collateral",
        "value": "substantially all assets of CCAC VII plus 100% equity pledge",
        "source_tier": "primary_8k",
        "source": "EDGAR accession 0001769628-25-000033",
    },
    {
        "entity": "CoreWeave",
        "facility": "DDTL 3.0",
        "field": "recourse",
        "value": "Parent unconditional guarantee",
        "source_tier": "primary_8k",
        "source": "EDGAR accession 0001769628-25-000033",
    },
    {
        "entity": "CoreWeave",
        "facility": "DDTL 3.0",
        "field": "covenant_dscr",
        "value": ">=1.40x beginning April 2027",
        "source_tier": "primary_8k",
        "source": "EDGAR accession 0001769628-25-000033",
    },
]


def test_normalize_coreweave_primary_debt_service_card() -> None:
    terms = normalize_debt_service_card_rows(COREWEAVE_CARD_ROWS)

    assert len(terms) == 1
    term = terms[0]
    assert term.term_id == "coreweave:ddtl-3-0"
    assert term.facility_size_usd == "2600000000"
    assert term.maturity_date == "2030-08-21"
    assert term.rate_type == "floating"
    assert term.rate_index == "SOFR"
    assert term.rate_spread_bps == "400"
    assert term.undrawn_fee_bps == "50"
    assert term.recourse == "Parent unconditional guarantee"
    assert "substantially all assets" in term.collateral
    assert term.verification_status == "primary_verified"
    assert term.filing_accession == "0001769628-25-000033"


def test_press_only_facility_stays_unverified_but_parses_fixed_coupon() -> None:
    terms = normalize_debt_service_card_rows(
        [
            {
                "entity": "CoreWeave",
                "facility": "2031 Notes",
                "field": "facility_size_usd",
                "value": "$2.75B",
                "source_tier": "press_NOT_verified",
                "source": "press mention",
            },
            {
                "entity": "CoreWeave",
                "facility": "2031 Notes",
                "field": "coupon",
                "value": "9.75% senior unsecured notes due 2031-10",
                "source_tier": "press_NOT_verified",
                "source": "press mention",
            },
        ]
    )

    assert len(terms) == 1
    assert terms[0].facility_size_usd == "2750000000"
    assert terms[0].rate_type == "fixed"
    assert terms[0].fixed_coupon_pct == "9.75"
    assert terms[0].verification_status == "unverified_external"


def test_summary_counts_missing_primary_critical_fields() -> None:
    terms = normalize_debt_service_card_rows(
        [
            {
                "entity": "IREN",
                "facility": "Senior secured notes",
                "field": "facility_size_usd",
                "value": "1000000000",
                "source_tier": "primary_8k",
                "source": "EDGAR accession 0000000000-26-000001",
            }
        ]
    )

    summary = summarize_debt_service_terms(terms)
    assert summary["primary_verified_term_count"] == 1
    assert summary["primary_verified_facility_size_usd"] == 1_000_000_000
    assert summary["terms_missing_maturity"] == 1
    assert summary["terms_missing_rate"] == 1
    assert summary["terms_missing_recourse"] == 1
    assert summary["terms_missing_collateral"] == 1


def test_cli_writes_normalized_debt_service_csv(tmp_path: Path) -> None:
    input_path = tmp_path / "card.csv"
    output_path = tmp_path / "normalized.csv"
    with input_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COREWEAVE_CARD_ROWS[0]))
        writer.writeheader()
        writer.writerows(COREWEAVE_CARD_ROWS)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/normalize_debt_service_cards.py",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[2],
        env={"PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )

    summary = json.loads(result.stdout)
    assert summary["term_count"] == 1
    rows = list(csv.DictReader(output_path.open()))
    assert rows[0]["entity"] == "CoreWeave"
    assert rows[0]["rate_spread_bps"] == "400"
