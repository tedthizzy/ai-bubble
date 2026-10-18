#!/usr/bin/env python3
"""Reconcile dated core measurements against saved primary financial statements."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def read(path: Path) -> Any:
    return json.loads(path.read_text())


def source_text(record: dict[str, Any]) -> str:
    raw_path = ROOT / record["source_path"]
    opener = gzip.open if raw_path.suffix == ".gz" else open
    digest = hashlib.sha256()
    with opener(raw_path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != record["source_sha256"]:
        raise ValueError(f"Changed primary source: {record['url']}")
    path = ROOT / record["normalized_path"]
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != record["normalized_sha256"]:
        raise ValueError(f"Changed normalized review text: {path}")
    return " ".join(raw.decode().replace("\u200b", "").split())


def verify_debt_card(card: dict[str, Any], source: dict[str, Any], text: str) -> dict[str, Any]:
    if card["filing_date"] != source["filing_date"]:
        raise ValueError(f"Debt card filing date mismatch: {card['ticker']}")
    total = Decimal(0)
    rows = [(True, row) for row in card["components"]]
    rows.extend((False, row) for row in card.get("excluded_components", []))
    for included, component in rows:
        label = re.escape(component["label"]).replace(r"\ ", r"\s+")
        value = re.escape(component["reported_value"])
        # Ignore footnote markers and accounting parentheses, while requiring
        # the named row's first reported column to match the carded amount.
        pattern = label + r"\s*(?:\(\d+\)\s*)*\$?\s*\(?\s*" + value + r"(?![\d.,])"
        if "reported_columns" in component:
            columns = component["reported_columns"]
            index = component["selected_column"]
            if (
                columns[index] != component["reported_value"]
                or card["column_periods"][index] != card["period_end"]
            ):
                raise ValueError("Selected debt column does not match the current period")
            require_sequence(text, component["label"], columns)
        elif re.search(pattern, text, re.I) is None:
            raise ValueError(f"Unverified debt row: {card['ticker']} {component['label']}")
        if included:
            total += Decimal(component["reported_value"].replace(",", "")) * component["sign"]
    amount = total * card["units_usd"]
    if amount != amount.to_integral_value():
        raise ValueError("Debt card is not an integral USD amount")
    return {
        **card,
        "reported_debt_usd": int(amount),
        "source_sha256": source["source_sha256"],
        "verification": "primary_statement_rows",
    }


def require_sequence(text: str, label: str, columns: list[str]) -> None:
    for match in re.finditer(re.escape(label).replace(r"\ ", r"\s+"), text, re.I):
        observed = re.findall(r"\d[\d,]*(?:\.\d+)?", text[match.end() : match.end() + 200])
        if observed[: len(columns)] == columns:
            return
    raise ValueError(f"Unverified financial table columns: {label}")


def reassess(run: Path, manifest: Path, as_of: str) -> dict[str, Any]:
    library = read(manifest)
    records = {row["url"]: row for row in library["filings"] if row["status"] == "hash_verified"}
    cards_path = ROOT / f"analysis/core_debt_cards_{as_of}.json"
    cards = read(cards_path)
    panel_path = ROOT / f"analysis/case_zero_financials_{as_of}_v4.json"
    panel = read(panel_path)
    if cards["as_of"] != as_of or panel["as_of"] != as_of:
        raise ValueError("Dated inputs disagree")
    by_ticker = {entity["ticker"]: entity for entity in panel["entities"]}
    text_by_ticker = {}
    debts = []
    for card in cards["cards"]:
        if card["period_end"] > as_of or card["filing_date"] > as_of:
            raise ValueError("Debt card postdates the observation cutoff")
        source = records[card["source_uri"]]
        text = source_text(source)
        text_by_ticker[card["ticker"]] = text
        debts.append(verify_debt_card(card, source, text))

    nebius = text_by_ticker["NBIS"]
    require_sequence(
        nebius,
        "Net cash provided by / (used in) operating activities",
        ["171.6", "2,246.1", "369.1", "4,504.1"],
    )
    require_sequence(
        nebius,
        "Purchases of property and equipment and intangible assets",
        ["510.6", "5,657.4", "1,054.5", "8,130.3"],
    )
    bitdeer = text_by_ticker["BTDR"]
    require_sequence(
        bitdeer,
        "Net cash used in operating activities",
        ["505,417", "622,025"],
    )
    require_sequence(
        bitdeer,
        "Purchase of property, plant and equipment and intangible assets",
        ["359,740", "157,205"],
    )
    supplements = {
        "NBIS": (4_504_100_000, 8_130_300_000),
        "BTDR": (-505_417_000, 359_740_000),
    }
    observations = []
    for debt in debts:
        ticker = debt["ticker"]
        entity = by_ticker[ticker]
        if ticker in supplements:
            operating, capex = supplements[ticker]
            cashflow = {
                "start": "2026-01-01",
                "end": "2026-06-30",
                "operating_cash_flow_usd": operating,
                "cash_capex_usd": capex,
                "value_usd": operating - capex,
                "capex_definition": "Property, plant/equipment and intangible-asset cash purchases.",
                "source_uri": debt["source_uri"],
                "source_sha256": debt["source_sha256"],
            }
        else:
            cashflow = entity["current_liquidity"].get("cash_after_capex")
            if cashflow and cashflow["end"] != debt["period_end"]:
                raise ValueError(f"Cash-flow period differs from latest statement: {ticker}")
        if (
            cashflow
            and cashflow["value_usd"]
            != cashflow["operating_cash_flow_usd"] - cashflow["cash_capex_usd"]
        ):
            raise ValueError(f"Cash-flow arithmetic failed: {ticker}")
        ratios = {
            key: value
            for key, value in entity["derived"].items()
            if "interest_coverage" in key and value and value.get("end") == debt["period_end"]
        }
        observations.append(
            {
                **debt,
                "cash_after_capex": cashflow,
                "interest_coverage_proxies": ratios,
                "post_report_current_filings": [
                    filing
                    for filing in entity["new_filings_since_june_13"]
                    if filing["filing_date"] > debt["filing_date"]
                    and filing["form"] in {"8-K", "6-K"}
                ],
            }
        )

    crwv = text_by_ticker["CRWV"]
    require_sequence(crwv, "Customer A", ["36", "71", "40", "72"])
    corz = text_by_ticker["CORZ"]
    require_sequence(corz, "Colocation revenue", ["136,669", "10,560", "214,208", "19,133"])
    require_sequence(corz, "Total revenue", ["164,201", "78,628", "279,445", "158,153"])
    for phrase in (
        "Colocation segment revenue is concentrated with a single customer",
        "used to repay in full all outstanding borrowings under the Term Loan Facility",
    ):
        if phrase.casefold() not in corz.casefold():
            raise ValueError(f"Core Scientific source check failed: {phrase}")
    single_customer_pct = 100 * 136_669 / 164_201
    return {
        "as_of": as_of,
        "source_manifest": str(manifest.relative_to(ROOT)),
        "source_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "debt_cards_sha256": hashlib.sha256(cards_path.read_bytes()).hexdigest(),
        "measurement_corrections": cards.get("corrections", []),
        "issuer_observations": observations,
        "reported_issuer_debt_usd": sum(row["reported_debt_usd"] for row in observations),
        "issuer_count": len(observations),
        "cashflow_observations": sum(bool(row["cash_after_capex"]) for row in observations),
        "negative_cash_after_capex": sum(
            bool(row["cash_after_capex"] and row["cash_after_capex"]["value_usd"] < 0)
            for row in observations
        ),
        "current_findings": {
            "financing_dependence": "The selected issuer cohort spends more cash on capital purchases than it generates in operating cash flow. This is a funding requirement, not a default finding.",
            "coreweave_largest_customer": {
                "period": "2026-Q2",
                "share_pct": 36,
                "identity": "anonymized; cannot be assigned to Microsoft",
                "h1_share_pct": 40,
                "source_uri": next(row["source_uri"] for row in debts if row["ticker"] == "CRWV"),
            },
            "core_scientific_single_customer": {
                "period": "2026-Q2",
                "total_revenue_share_pct": single_customer_pct,
                "derivation": "Colocation revenue divided by total revenue; the filing says the colocation segment has one customer.",
                "source_uri": next(row["source_uri"] for row in debts if row["ticker"] == "CORZ"),
            },
            "core_scientific_old_term_loan": "Repaid and terminated in May 2026; do not show the former $1B facility as outstanding.",
            "gpu_economic_life": "Current rental quote pages do not measure asset economic life; the June two-year assumption is not recertified by a new retrieval date.",
            "current_bubble_probability": None,
            "bubble_classification": "Financing dependence and customer concentration are observed. Public measurements do not support a new calibrated bubble probability or an economy-wide bubble classification.",
        },
        "limits": cards["limits"]
        + [
            "Negative cash after capex is common during expansion and does not establish insolvency.",
            "Interest-coverage proxies use their stated earnings definitions; EBIT and EBITDA are not interchangeable.",
            "The cohort is selected and cannot estimate economy-wide prevalence.",
            "Raw extraction candidates still require instrument-level review; their notionals are not summed into this balance-sheet total.",
            "The old committed-debt census and June confidence judgments remain historical artifacts.",
        ],
    }


def markdown(value: dict[str, Any]) -> str:
    lines = [
        f"# Current core review, {value['as_of']}",
        "",
        f"The {value['issuer_count']} selected issuers report ${value['reported_issuer_debt_usd'] / 1e9:.3f}B of USD borrowing and note carrying amounts across their latest financial statements.",
        "These are consolidated issuer balances with their original period ends. They include non-AI businesses. Lease and guarantee amounts are separate.",
        "",
    ]
    for row in value["issuer_observations"]:
        cash = row["cash_after_capex"]
        text = f"- {row['entity']}: ${row['reported_debt_usd'] / 1e9:.3f}B reported debt at {row['period_end']}."
        if cash:
            text += f" Cash after capex {'-' if cash['value_usd'] < 0 else ''}${abs(cash['value_usd']) / 1e9:.3f}B ({cash['start']} to {cash['end']})."
        lines.append(text + f" [Primary statement]({row['source_uri']}).")
    lines += [
        "",
        "The current review corrects the old CoreWeave 67% Microsoft concentration claim. Its Q2 largest customer is 36%, anonymously identified. Core Scientific's single colocation customer represents about 83.2% of total Q2 revenue, so concentrated demand remains a measured risk elsewhere in the cohort.",
        "",
        "Core Scientific repaid and terminated its former $1B term loan in May 2026. The current debt card includes its later note balances.",
        "",
        value["current_findings"]["bubble_classification"],
        "",
        *[
            f"Correction: {row['ticker']} USD-denominated debt is ${row['corrected_debt_usd'] / 1e9:.6f}B. The earlier total included ${row['excluded_crypto_carrying_amount_usd'] / 1e6:.3f}M of Bitcoin-denominated borrowing. That exposure remains separately recorded."
            for row in value.get("measurement_corrections", [])
        ],
        "",
        "Measurement limits:",
        "",
    ]
    lines += ["- " + item for item in value["limits"]]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output-prefix", required=True, type=Path)
    args = parser.parse_args()
    date.fromisoformat(args.as_of)
    value = reassess(args.run.resolve(), args.manifest.resolve(), args.as_of)
    for suffix, content in (
        (".json", json.dumps(value, indent=2) + "\n"),
        (".md", markdown(value)),
    ):
        with args.output_prefix.with_suffix(suffix).open("x") as stream:
            stream.write(content)
    print(
        json.dumps(
            {
                key: value[key]
                for key in [
                    "issuer_count",
                    "reported_issuer_debt_usd",
                    "cashflow_observations",
                    "negative_cash_after_capex",
                ]
            }
        )
    )


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget(512)
    main()
