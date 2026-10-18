#!/usr/bin/env python3
"""Re-card valuation inputs from retained, hash-verified sources at a fixed cutoff."""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import shutil
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

from bubble.ingestion.edgar.document_acquisition import normalize_document_text

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reassess_current_core import require_sequence, source_text

ROOT = Path(__file__).resolve().parents[1]
AS_OF = "2026-10-17"


def read_verified(path: Path, digest: str) -> bytes:
    raw = gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(f"Changed valuation source: {path}")
    return raw


def fact_value(
    facts: dict[str, Any], card: dict[str, Any], start: str, end: str, as_of: str
) -> int:
    if end > as_of:
        raise ValueError("Revenue period postdates the cutoff")
    rows = facts["facts"][card["namespace"]][card["tag"]]["units"]["USD"]
    matches = [
        row
        for row in rows
        if row.get("start") == start
        and row.get("end") == end
        and row["accn"] == card["accession"]
        and row["filed"] <= as_of
    ]
    values = {int(row["val"]) for row in matches}
    if len(values) != 1:
        raise ValueError("Missing or conflicting comparable revenue in the named accession")
    return values.pop()


def market_card(source: dict[str, Any], quote: dict[str, Any]) -> dict[str, Any]:
    text = normalize_document_text(read_verified(ROOT / source["path"], source["sha256"]))
    close = re.search(r"([\d.]+)\s+[+-][\d.]+\s+\([+-]?[\d.]+%\)\s+At close: Oct 16, 2026,", text)
    if not close or quote["date"] != "2026-10-16":
        raise ValueError("Market source does not describe the frozen October 16 close")
    price = Decimal(close.group(1))
    if abs(price - Decimal(str(quote["close"]))) > Decimal("0.005"):
        raise ValueError("Statistics price disagrees with the frozen market quote")

    def billions(label: str) -> float:
        match = re.search(re.escape(label) + r"\s+(-?[\d.]+)([BM])\b", text)
        if match is None:
            raise ValueError(f"Missing market field: {label}")
        amount = Decimal(match.group(1))
        return float(amount / 1000 if match.group(2) == "M" else amount)

    return {
        "ev_usd_b": billions("Enterprise Value"),
        "net_debt_usd_b": -billions("Net Cash"),
        "close_usd": float(price),
        "market_date": quote["date"],
        "source": source,
        "basis": "Provider enterprise value and net debt, including its lease/debt definitions; not pro-forma October 17 issuer balances.",
    }


def build() -> dict[str, Any]:  # noqa: PLR0915 - four explicit issuer accounting reconciliations
    run = ROOT / "data" / f"refresh_{AS_OF}"
    panel = json.loads((ROOT / f"analysis/case_zero_financials_{AS_OF}_v4.json").read_text())
    library = json.loads((run / "core_review_v7/manifest.json").read_text())
    records = {row["url"]: row for row in library["filings"] if row["status"] == "hash_verified"}
    market_sources = json.loads((run / "expectations_market_v2/manifest.json").read_text())
    sources = {row["id"].split("-")[0]: row for row in market_sources["sources"]}
    market = json.loads((ROOT / f"analysis/market_snapshot_{AS_OF}.json").read_text())
    quotes = {row["sym"]: row for row in market["live"]["quotes"].values()}
    if panel["as_of"] != AS_OF or market["as_of_pacific"] != AS_OF:
        raise ValueError("Valuation evidence has a different cutoff")
    inputs, evidence = [], {}
    specs = {
        "CRWV": ("CoreWeave", 103.7, 6.5, False, "crwv-20260630.htm"),
        "NBIS": ("Nebius", 37.4906, 5.0, False, "nbis-20260812xex99d2.htm"),
        "IREN": ("IREN", 16.6, 5.0, False, "iren-20260630.htm"),
        "APLD": ("Applied Digital", 36.0, 15.0, True, "apldq127earningsrelease.htm"),
    }
    bases = {
        "CRWV": "$103.7B unsatisfied GAAP RPO at June 30. 41% expected within 24 months, 39% in months 25-48, remainder in months 49-78. Later announced commitments are separate.",
        "NBIS": "$37.4906B unsatisfied RPO at June 30. 36% expected within 24 months, 40% in months 25-48, remainder thereafter. Includes estimated variable consideration; excludes original terms of one year or less. Broader $40B customer commitments are separate.",
        "IREN": "$16.6B company-reported combined June 30 ASC 606 RPO and ASC 842 contracted lease value. Separately rounded components are $5.1B and $11.4B. This combined measure is broader than GAAP RPO.",
        "APLD": "Approximately $36B base-term contracted lease revenue disclosed October 7. Excludes the $86B total conditional on all renewal options. Gross original lease value is not GAAP RPO or an audited remaining rent balance.",
    }
    timing = {
        "CRWV": "6.5-year uniform recognition assumption uses the disclosed final 78-month horizon; actual recognition is earlier-weighted.",
        "NBIS": "Five-year uniform recognition assumption; disclosed recognition is 76% within four years and the remainder thereafter. Final duration is not independently reconciled.",
        "IREN": "Five-year uniform recognition assumption; the stated RPO schedule ends at month 60. The lease component is a separate accounting measure.",
        "APLD": "15-year uniform recognition assumption follows the disclosed new lease base terms. Construction start delays and individual remaining lease schedules are not modeled.",
    }
    for ticker, (name, backlog, tenor, landlord, suffix) in specs.items():
        entity = next(row for row in panel["entities"] if row["ticker"] == ticker)
        source = next(row for url, row in records.items() if url.endswith("/" + suffix))
        if source["filing_date"] > AS_OF:
            raise ValueError("Contract source postdates the cutoff")
        text = source_text(source)
        facts_source = entity["companyfacts_source"]
        facts_path = run / "financial_raw" / f"CIK{entity['cik']}-companyfacts.json.gz"
        facts = json.loads(read_verified(facts_path, facts_source["sha256"]))
        annual = entity["facts"]["revenue"]["annual"]
        annual_value = fact_value(facts, annual, annual["start"], annual["end"], AS_OF)
        if annual_value != annual["value_usd"]:
            raise ValueError("Annual panel revenue differs from its primary fact")
        components: list[dict[str, Any]] = [{"sign": 1, **annual}]
        if ticker in {"CRWV", "APLD"}:
            period = entity["facts"]["revenue"]["year_to_date" if ticker == "CRWV" else "quarter"]
            current = fact_value(facts, period, period["start"], period["end"], AS_OF)
            prior_start = str(int(period["start"][:4]) - 1) + period["start"][4:]
            prior_end = str(int(period["end"][:4]) - 1) + period["end"][4:]
            prior = fact_value(facts, period, prior_start, prior_end, AS_OF)
            if current != period["value_usd"]:
                raise ValueError("Current revenue differs from the primary fact")
            revenue = annual_value + current - prior
            components += [
                {"sign": 1, **period},
                {"sign": -1, **period, "start": prior_start, "end": prior_end, "value_usd": prior},
            ]
            end = period["end"]
        elif ticker == "NBIS":
            if "In millions of U.S. dollars" not in text:
                raise ValueError("Nebius statement units are unverified")
            require_sequence(text, "Revenues", ["105.1", "582.3", "156.0", "981.3"])
            revenue = annual_value + 981_300_000 - 156_000_000
            components += [
                {"sign": 1, "start": "2026-01-01", "end": "2026-06-30", "value_usd": 981_300_000},
                {"sign": -1, "start": "2025-01-01", "end": "2025-06-30", "value_usd": 156_000_000},
            ]
            end = "2026-06-30"
        else:
            revenue, end = annual_value, annual["end"]
        phrases = {
            "CRWV": "103.7 billion of unsatisfied RPO",
            "NBIS": "the amount of unsatisfied RPO was $37,490.6",
            "IREN": "totaled approximately $ 16.6 billion",
            "APLD": "$36 billion of contracted revenue over their initial base terms",
        }
        if phrases[ticker].casefold() not in text.casefold():
            raise ValueError(f"Contract amount is not verified: {ticker}")
        observed = market_card(sources[ticker], quotes[ticker])
        revenue_basis = f"Consolidated trailing 12-month reported revenue through {end}; annual plus current period minus the same prior-year period, or the latest complete fiscal year. Includes any non-AI businesses."
        inputs.append(
            {
                "ticker": ticker,
                "name": name,
                "ev_usd_b": observed["ev_usd_b"],
                "current_annualized_revenue_usd_b": revenue / 1e9,
                "revenue_basis": revenue_basis,
                "backlog_usd_b": backlog,
                "backlog_tenor_years": tenor,
                "backlog_basis": bases[ticker],
                "net_debt_usd_b": observed["net_debt_usd_b"],
                "is_landlord": landlord,
                "notes": timing[ticker]
                + " EV uses the provider's debt and cash definitions. Uniform FCF margins are model assumptions; the uncovered EV share can also depend on new customers or other businesses.",
                "sources": {
                    "market": sources[ticker]["url"],
                    "revenue_companyfacts": facts_source["url"],
                    "contract_and_interim_statement": source["url"],
                },
            }
        )
        evidence[ticker] = {
            "market": observed,
            "revenue_components": components,
            "ttm_revenue_usd": revenue,
            "revenue_period_end": end,
            "companyfacts": {**facts_source, "path": str(facts_path.relative_to(ROOT))},
            "contract_and_interim_statement": source,
            "backlog_basis": bases[ticker],
            "timing_assumption": timing[ticker],
        }
    return {
        "as_of": AS_OF,
        "market_close": "2026-10-16",
        "revenue_basis": "Consolidated reported trailing 12 months for all four issuers.",
        "inputs": inputs,
        "evidence": evidence,
    }


def main() -> None:
    result = build()
    target = ROOT / "src/bubble/expectations" / f"inputs_{AS_OF}.json"
    if target.exists():
        backup = ROOT / ".codex/refresh-2026-10-17" / f"expectations-inputs-{time.time_ns()}"
        backup.mkdir()
        shutil.copy2(target, backup / target.name)
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "as_of": AS_OF,
                "issuers": len(result["inputs"]),
                "ttm_revenue_usd": {k: v["ttm_revenue_usd"] for k, v in result["evidence"].items()},
            }
        )
    )


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget(512)
    main()
