#!/usr/bin/env python3
"""Verify quoted facility inputs and publish reproducible, dated cash-flow calculations."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from bubble.analysis.facility_cashflows import analyze_facility
from bubble.models.facility import FacilityCase, FacilityFact, FacilityPrincipalPayment

ROOT = Path(__file__).resolve().parents[1]


def calculation_hashes() -> dict[str, str]:
    return {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in (
            "scripts/build_facility_cashflows.py",
            "src/bubble/models/facility.py",
            "src/bubble/analysis/facility_cashflows.py",
        )
    }


def load_calculated_report(root: Path, as_of: str) -> dict[str, Any]:
    """A clone can rebuild the UI from the committed, matching calculation artifact."""
    inputs = root / "analysis" / f"facility_inputs_{as_of}.json"
    digest = hashlib.sha256(inputs.read_bytes()).hexdigest()
    expected_code = calculation_hashes()
    candidates = []
    for path in sorted((root / "analysis").glob(f"facility_cashflows_{as_of}*.json")):
        value = json.loads(path.read_text())
        if (
            value.get("input_sha256") == digest
            and value.get("as_of") == as_of
            and value.get("calculation_source_sha256") == expected_code
        ):
            candidates.append(value)
    if not candidates:
        raise ValueError(
            "Build a current facility_cashflows calculation artifact before publishing the visualization"
        )
    if any(value != candidates[0] for value in candidates[1:]):
        raise ValueError("Conflicting facility calculation artifacts for identical inputs and code")
    return candidates[0]


def verify_source(record: dict[str, Any], root: Path) -> str:
    raw_path = root / record["source_path"]
    digest = hashlib.sha256()
    opener = gzip.open if raw_path.suffix == ".gz" else open
    with opener(raw_path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != record["source_sha256"]:
        raise ValueError(f"Changed facility primary source: {record['url']}")
    normalized = (root / record["normalized_path"]).read_bytes()
    if hashlib.sha256(normalized).hexdigest() != record["normalized_sha256"]:
        raise ValueError(f"Changed facility normalized source: {record['url']}")
    return " ".join(normalized.decode().replace("\u200b", "").split())


def verify_fact(fact: FacilityFact, sources: dict[str, str]) -> None:
    if fact.source_id not in sources or fact.quote not in sources[fact.source_id]:
        raise ValueError(f"Facility quote not present in verified source: {fact.source_id}")
    if isinstance(fact.value, float):
        if fact.source_token is None or fact.source_token not in fact.quote:
            raise ValueError("Numeric facility fact lacks its quoted source token")
        token = fact.source_token.replace(",", "").replace("$", "")
        words = {
            "one": "1",
            "two": "2",
            "three": "3",
            "four": "4",
            "five": "5",
            "ten": "10",
            "fifteen": "15",
            "twenty": "20",
        }
        expected = Decimal(words.get(token.lower(), token)) * Decimal(str(fact.multiplier))
        if abs(expected - Decimal(str(fact.value))) > Decimal("0.000001"):
            raise ValueError("Facility numeric conversion disagrees with source token")


def extract_principal_payments(text: str, source_id: str, published: date) -> list[dict[str, Any]]:
    """Read only an explicit installment table, excluding optional redemption prices."""
    headings = list(re.finditer(r"Section 14\.02 Payment Schedule", text, re.I))
    if not headings:
        raise ValueError("No explicit principal payment schedule section")
    start = headings[-1].end()
    end = text.index("Section 14.03", start)
    pattern = r"((?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4})\s+\$\s*([\d,]+)"
    payments = []
    for match in re.finditer(pattern, text[start:end]):
        due_on = datetime.strptime(match[1], "%B %d, %Y").date()
        fact = FacilityFact(
            value=float(match[2].replace(",", "")),
            unit="USD",
            source_id=source_id,
            quote=match[0],
            kind="contractual",
            observed_on=published,
            source_token=match[2],
        )
        payments.append(
            FacilityPrincipalPayment(due_on=due_on, amount=fact).model_dump(mode="json")
        )
    if not payments:
        raise ValueError("Principal payment schedule has no dated USD installments")
    return payments


def build(input_path: Path, root: Path = ROOT) -> dict[str, Any]:
    payload = json.loads(input_path.read_text())
    as_of = date.fromisoformat(payload["as_of"])
    sources = payload["sources"]
    if any(date.fromisoformat(row["filing_date"]) > as_of for row in sources.values()):
        raise ValueError("Facility disclosure postdates the calculation cutoff")
    texts = {identifier: verify_source(record, root) for identifier, record in sources.items()}
    cases = [FacilityCase.model_validate(row) for row in payload["cases"]]
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("Duplicate facility identifier")
    instrument_ids = [debt.id for case in cases for debt in case.debts]
    if len(instrument_ids) != len(set(instrument_ids)):
        raise ValueError("One instrument is allocated to multiple facility cases")
    for case in cases:
        for debt in case.debts:
            for payment in debt.principal_payments:
                date_phrase = (
                    payment.due_on.strftime("%B ")
                    + str(payment.due_on.day)
                    + payment.due_on.strftime(", %Y")
                )
                if date_phrase not in payment.amount.quote:
                    raise ValueError("Principal payment date disagrees with its source row")
        for fact in case.evidence():
            verify_fact(fact, texts)
    for interest in payload.get("retired_interests", []):
        verify_fact(FacilityFact.model_validate(interest["fact"]), texts)
    results = [analyze_facility(case, as_of) for case in cases]
    coverage = payload["issuer_coverage"]
    if len({row["ticker"] for row in coverage}) != len(coverage):
        raise ValueError("Duplicate issuer coverage entry")
    for row in coverage:
        expected = sorted(case.id for case in cases if case.ticker == row["ticker"])
        if sorted(row["cases"]) != expected:
            raise ValueError("Issuer coverage disagrees with the facility cases")
    return {
        "as_of": as_of.isoformat(),
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "calculation_source_sha256": calculation_hashes(),
        "source_sha256": {
            identifier: record["source_sha256"] for identifier, record in sources.items()
        },
        "sources": {
            identifier: {
                "source_uri": record["url"],
                "filing_date": record["filing_date"],
                "source_sha256": record["source_sha256"],
            }
            for identifier, record in sources.items()
        },
        "summary": {
            "issuer_count": len(coverage),
            "facility_cases": len(results),
            "issuers_with_cases": len({case.ticker for case in cases}),
            "linked_instruments": len(instrument_ids),
            "cases_with_interest_run_rate": sum(
                row["annual_interest_run_rate_usd"] is not None for row in results
            ),
            "cases_with_contract_average": sum(
                row["annual_contract_average_usd"] is not None for row in results
            ),
            "cases_with_dscr": sum(
                row["debt_service_coverage_ratio"] is not None for row in results
            ),
            "cases_with_complete_original_debt_schedule": sum(
                bool(row["annual_scheduled_debt_service"]) for row in results
            ),
            "verified_principal_installments": sum(
                len(debt.principal_payments) for case in cases for debt in case.debts
            ),
            "cases_with_reported_energized_it_mw": sum(
                "energized_it_mw" in case.facts for case in cases
            ),
        },
        "cases": results,
        "issuer_coverage": coverage,
        "retired_interests": payload.get("retired_interests", []),
        "limits": payload["limits"]
        + [
            "Cash-margin and revenue-factor sensitivities are assumptions, not forecasts or probabilities.",
            "Revenue factors model nonpayment or rollover stress; take-or-pay rent does not mechanically vary with GPU utilization.",
            "Facility principal and issuer carrying balances overlap and must not be summed.",
            "Current DSCR is absent when the cash-flow period, debt perimeter or full payment schedule is missing.",
        ],
    }


def markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        f"# Facility cash flows, {report['as_of']}",
        "",
        f"Reviewed {summary['issuer_count']} issuers; {summary['facility_cases']} cases link disclosed site, contract or financing terms.",
        f"{summary['cases_with_interest_run_rate']} cases have annualized interest on a dated principal snapshot. "
        f"{summary['cases_with_contract_average']} have a base-contract average. "
        f"{summary['cases_with_dscr']} have sufficient matched inputs for DSCR.",
        "",
    ]
    for case in report["cases"]:
        lines.extend([f"## {case['entity']} / {case['project']}", ""])
        for label, key in [
            ("Base contract average per year", "annual_contract_average_usd"),
            ("Annual interest run rate on listed instruments", "annual_interest_run_rate_usd"),
            ("Cash available / complete debt service", "debt_service_coverage_ratio"),
        ]:
            number = case[key]
            if number is not None:
                lines.append(
                    f"- {label}: "
                    + (
                        f"{number:.3f}x"
                        if key == "debt_service_coverage_ratio"
                        else f"${number:,.0f}"
                    )
                )
        threshold = case["thresholds"]["cash_margin_required_for_interest_pct"]
        if threshold is not None:
            lines.append(
                f"- Cash margin required for interest only: {threshold:.2f}% of {case['thresholds']['revenue_basis']}."
            )
        lines.extend(
            f"- {event['event'].replace('_', ' ')}: {event['value']} ({event['kind']})."
            for event in case["timeline"]
        )
        if case["annual_scheduled_debt_service"]:
            lines.append(
                "- Original contractual payments assume no optional redemptions, additional notes or payment-schedule amendments."
            )
            lines.extend(
                f"- {row['year']}: ${row['principal_usd']:,.0f} principal + ${row['interest_usd']:,.2f} interest = ${row['debt_service_usd']:,.2f}."
                for row in case["annual_scheduled_debt_service"]
            )
        lines.extend(f"- {note}" for note in case["notes"])
        lines.append("- Missing: " + "; ".join(case["missing_inputs"]) + ".")
        source_ids = {fact["source_id"] for fact in case["facts"].values()}
        for debt in case["instruments"]:
            source_ids.update(fact["source_id"] for fact in debt["facts"].values())
        lines.append(
            "- Evidence: "
            + ", ".join(
                f"[{sid}]({report['sources'][sid]['source_uri']})" for sid in sorted(source_ids)
            )
        )
        lines.append("")
    lines.extend(["## Issuer coverage", ""])
    lines.extend(
        f"- {row['entity']}: {len(row['cases'])} cases; {row['status'].replace('_', ' ')}."
        for row in report["issuer_coverage"]
    )
    lines.extend(["", "## Retired interests", ""])
    lines.extend(
        f"- {row['entity']} / {row['project']}: {row['fact']['value']}."
        for row in report["retired_interests"]
    )
    lines.extend(["", "## Limits", "", *[f"- {limit}" for limit in report["limits"]], ""])
    return "\n".join(lines)


def public_projection(report: dict[str, Any]) -> dict[str, Any]:
    """Keep quotes in the audit artifact and send compact facts to the browser."""

    def compact(value: Any) -> Any:
        if isinstance(value, list):
            return [compact(item) for item in value]
        if isinstance(value, dict):
            return {
                key: compact(item)
                for key, item in value.items()
                if key not in {"quote", "source_token", "multiplier", "interpretation"}
            }
        return value

    return compact(report)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.input)
    for suffix, content in [
        (".json", json.dumps(result, indent=2, ensure_ascii=True) + "\n"),
        (".md", markdown(result)),
    ]:
        with args.output_prefix.with_suffix(suffix).open("x") as stream:
            stream.write(content)
    print(json.dumps(result["summary"]))


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget(512)
    main()
