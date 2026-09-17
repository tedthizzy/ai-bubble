#!/usr/bin/env python3
"""Freeze a dated SEC filing and XBRL financial panel for the AI case-zero cohort.

This is a source-data refresh, not a rerun of the June forensic verdict. It uses
only SEC public JSON endpoints and Python's standard library. Raw responses are
cached under ignored data/issuer_refresh/ so an interrupted run can resume.
Selected facts, their periods, accessions, and gaps are saved under analysis/.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any


BASELINE_DATE = date(2026, 6, 13)
DEFAULT_AS_OF = date(2026, 9, 16)
USER_AGENT = "ai-bubble research ted1508@gmail.com"
FINANCIAL_FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A", "20-F", "20-F/A", "40-F", "6-K"}
PERIODIC_FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A", "20-F", "20-F/A", "40-F"}

# The XBRL tag named "InNextTwelveMonths" is used for the next *annual schedule
# row* in these filings. At a June 30 quarterly report that is calendar 2027,
# after a separate remainder-of-2026 row. Date-specific labels below were
# checked against each issuer's 2026 SEC debt note; future report dates are
# deliberately withheld pending the same check.
VERIFIED_DEBT_BUCKETS = {
    ("CRWV", "2026-06-30"): ("remainder of calendar 2026", "calendar 2027"),
    ("IREN", "2026-06-30"): (None, "fiscal year ending 2027-06-30"),
    ("MARA", "2026-06-30"): ("remainder of calendar 2026", "calendar 2027"),
    ("CIFR", "2026-06-30"): ("remainder of calendar 2026", "calendar 2027"),
    ("MSFT", "2026-06-30"): (None, "fiscal year ending 2027-06-30"),
    ("META", "2026-06-30"): ("remainder of calendar 2026", "calendar 2027"),
    ("SPCX", "2026-06-30"): ("remainder of calendar 2026", "calendar 2027"),
}

# The first 12 names are the June filing-sweep cohort. BTDR appears in the June
# interest-coverage fixture, so it is included as a thirteenth baseline issuer.
# Counterparties are added only where a public SEC CIK is established.
TARGETS = (
    ("CRWV", "0001769628", "issuer"),
    ("WULF", "0001083301", "issuer"),
    ("IREN", "0001878848", "issuer"),
    ("APLD", "0001144879", "issuer"),
    ("HUT", "0001964789", "issuer"),
    ("MARA", "0001507605", "issuer"),
    ("CLSK", "0000827876", "issuer"),
    ("GLXY", "0001859392", "issuer"),
    ("NBIS", "0001513845", "issuer"),
    ("CORZ", "0001839341", "issuer"),
    ("CIFR", "0001819989", "issuer"),
    ("BTBT", "0001710350", "issuer"),
    ("BTDR", "0001899123", "issuer"),
    ("NVDA", "0001045810", "counterparty"),
    ("MSFT", "0000789019", "counterparty"),
    ("AMZN", "0001018724", "counterparty"),
    ("GOOGL", "0001652044", "counterparty"),
    ("META", "0001326801", "counterparty"),
    ("ORCL", "0001341439", "counterparty"),
    ("AMD", "0000002488", "counterparty"),
    ("SPCX", "0001181412", "counterparty"),
    ("WhiteFiber", "0002042022", "counterparty"),
)

# Candidate tags are kept explicit. Every selected value retains its exact tag,
# namespace, accession, filing date, and financial period for review.
DURATION_TAGS = {
    "revenue": (
        ("us-gaap", "Revenues"),
        ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"),
        ("us-gaap", "SalesRevenueNet"),
        ("us-gaap", "RevenueFromContractWithCustomerIncludingAssessedTax"),
        ("ifrs-full", "Revenue"),
        ("ifrs-full", "RevenueFromContractsWithCustomers"),
    ),
    "operating_income": (
        ("us-gaap", "OperatingIncomeLoss"),
        ("ifrs-full", "ProfitLossFromOperatingActivities"),
    ),
    "net_income": (
        ("us-gaap", "NetIncomeLoss"),
        ("us-gaap", "ProfitLoss"),
        ("ifrs-full", "ProfitLoss"),
    ),
    "interest_expense": (
        ("us-gaap", "InterestExpense"),
        ("us-gaap", "InterestExpenseDebt"),
        ("us-gaap", "InterestAndDebtExpense"),
        ("us-gaap", "InterestExpenseNonoperating"),
        ("ifrs-full", "FinanceCosts"),
    ),
    "depreciation_amortization": (
        ("us-gaap", "DepreciationDepletionAndAmortization"),
        ("us-gaap", "DepreciationAmortizationAndAccretionNet"),
        ("us-gaap", "DepreciationAndAmortization"),
        ("ifrs-full", "DepreciationAndAmortisationExpense"),
    ),
    "operating_cash_flow": (
        ("us-gaap", "NetCashProvidedByUsedInOperatingActivities"),
        ("ifrs-full", "CashFlowsFromUsedInOperatingActivities"),
    ),
    "cash_capex": (
        ("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment"),
        ("us-gaap", "PaymentsToAcquireProductiveAssets"),
        ("us-gaap", "PaymentsToAcquireMachineryAndEquipment"),
        ("ifrs-full", "PurchaseOfPropertyPlantAndEquipment"),
    ),
}
INSTANT_TAGS = {
    "cash": (
        ("us-gaap", "CashAndCashEquivalentsAtCarryingValue"),
        ("ifrs-full", "CashAndCashEquivalents"),
    ),
    "total_debt_reported": (
        ("us-gaap", "DebtLongtermAndShorttermCombinedAmount"),
        ("us-gaap", "DebtInstrumentCarryingAmount"),
        ("us-gaap", "LongTermDebtAndCapitalLeaseObligations"),
        ("us-gaap", "LongTermDebt"),
        ("ifrs-full", "Borrowings"),
    ),
    "long_term_debt_noncurrent": (
        ("us-gaap", "LongTermDebtNoncurrent"),
        ("ifrs-full", "NoncurrentBorrowings"),
    ),
    "long_term_debt_current": (
        ("us-gaap", "LongTermDebtCurrent"),
        ("ifrs-full", "CurrentBorrowings"),
    ),
    "first_full_year_principal_schedule": (
        ("us-gaap", "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths"),
    ),
    "remaining_fiscal_year_principal_schedule": (
        ("us-gaap", "LongTermDebtMaturitiesRepaymentsOfPrincipalRemainderOfFiscalYear"),
    ),
}


class RateLimitedSec:
    def __init__(self, requests_per_second: float) -> None:
        self.interval = 1.0 / requests_per_second
        self.next_at = 0.0

    def get(self, url: str) -> bytes:
        for attempt in range(3):
            wait = self.next_at - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self.next_at = time.monotonic() + self.interval
            request = urllib.request.Request(
                url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
            )
            try:
                with urllib.request.urlopen(request, timeout=40) as response:
                    return response.read()
            except urllib.error.HTTPError as exc:
                if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        raise RuntimeError("SEC retry loop exhausted")


def fetch_json(sec: RateLimitedSec, url: str, path: Path) -> tuple[dict[str, Any], str, str]:
    if path.exists():
        raw = gzip.decompress(path.read_bytes())
        state = "cached"
    else:
        raw = sec.get(url)
        # A response is cached only after it parses. No failed or HTML response is
        # allowed to become durable evidence.
        json.loads(raw)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as output:
            output.write(gzip.compress(raw))
        state = "fetched"
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f"SEC response is not a JSON object: {url}")
    return parsed, hashlib.sha256(raw).hexdigest(), state


def filing_url(cik: str, accession: str, document: str = "") -> str:
    base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/"
    return base + document if document else base


def recent_filings(submissions: dict[str, Any], cik: str, as_of: date) -> list[dict[str, str]]:
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    out = []
    for i, form in enumerate(forms):
        try:
            filed = recent["filingDate"][i]
            accession = recent["accessionNumber"][i]
            document = recent["primaryDocument"][i]
        except (IndexError, KeyError):
            continue
        if filed > as_of.isoformat():
            continue
        report_dates = recent.get("reportDate") or []
        out.append(
            {
                "form": form,
                "filing_date": filed,
                "report_date": report_dates[i] if i < len(report_dates) else "",
                "accession": accession,
                "url": filing_url(cik, accession, document),
            }
        )
    return sorted(out, key=lambda x: (x["filing_date"], x["accession"]), reverse=True)


def fact_rows(
    companyfacts: dict[str, Any], tags: tuple[tuple[str, str], ...], as_of: date
) -> list[dict[str, Any]]:
    out = []
    for priority, (namespace, tag) in enumerate(tags):
        node = companyfacts.get("facts", {}).get(namespace, {}).get(tag, {})
        for row in node.get("units", {}).get("USD", []):
            filed, end = row.get("filed", ""), row.get("end", "")
            if not filed or not end or filed > as_of.isoformat() or end > as_of.isoformat():
                continue
            if row.get("form") not in FINANCIAL_FORMS or not isinstance(row.get("val"), (int, float)):
                continue
            entry = {
                "value_usd": row["val"],
                "namespace": namespace,
                "tag": tag,
                "tag_priority": priority,
                "start": row.get("start"),
                "end": end,
                "filed": filed,
                "form": row.get("form"),
                "accession": row.get("accn", ""),
            }
            if entry["start"]:
                try:
                    entry["period_days"] = (
                        date.fromisoformat(end) - date.fromisoformat(entry["start"])
                    ).days + 1
                except ValueError:
                    continue
            out.append(entry)
    return out


def select_latest(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    best = max(
        rows,
        key=lambda x: (x["end"], x["filed"], -x["tag_priority"], x["accession"]),
    )
    return {key: value for key, value in best.items() if key != "tag_priority"}


def select_facts(
    companyfacts: dict[str, Any], as_of: date, latest_report_end: str | None
) -> dict[str, Any]:
    selected: dict[str, Any] = {}
    for metric, tags in DURATION_TAGS.items():
        rows = fact_rows(companyfacts, tags, as_of)
        selected[metric] = {
            "quarter": select_latest([r for r in rows if 65 <= r.get("period_days", 0) <= 110]),
            "year_to_date": select_latest([r for r in rows if 111 <= r.get("period_days", 0) <= 329]),
            "annual": select_latest([r for r in rows if 330 <= r.get("period_days", 0) <= 380]),
        }
    for metric, tags in INSTANT_TAGS.items():
        selected[metric] = select_latest(
            [r for r in fact_rows(companyfacts, tags, as_of) if not r.get("start")]
        )
    for metric, value in selected.items():
        observations = value.values() if metric in DURATION_TAGS else (value,)
        for observation in observations:
            if observation:
                observation["matches_latest_periodic_report"] = (
                    observation["end"] == latest_report_end
                )
    return selected


def same_period(a: dict[str, Any] | None, b: dict[str, Any] | None) -> bool:
    return bool(a and b and a["start"] == b["start"] and a["end"] == b["end"])


def comparable_ratios(facts: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for period in ("quarter", "year_to_date", "annual"):
        op = facts["operating_income"][period]
        interest = facts["interest_expense"][period]
        da = facts["depreciation_amortization"][period]
        ocf = facts["operating_cash_flow"][period]
        capex = facts["cash_capex"][period]
        if same_period(op, interest) and interest["value_usd"] > 0:
            proxy = op["value_usd"]
            method = "operating_income"
            if same_period(op, da):
                proxy += da["value_usd"]
                method = "operating_income_plus_depreciation_amortization"
            out[f"{period}_interest_coverage"] = {
                "value": round(proxy / interest["value_usd"], 3),
                "method": method,
                "start": op["start"],
                "end": op["end"],
                "earnings_proxy_usd": proxy,
                "interest_expense_usd": interest["value_usd"],
            }
        if same_period(ocf, capex):
            out[f"{period}_cash_after_capex"] = {
                "value_usd": ocf["value_usd"] - capex["value_usd"],
                "start": ocf["start"],
                "end": ocf["end"],
                "operating_cash_flow_usd": ocf["value_usd"],
                "cash_capex_usd": capex["value_usd"],
            }
    return out


def current_liquidity(
    ticker: str, facts: dict[str, Any], derived: dict[str, Any], report_end: str | None
) -> dict[str, Any]:
    """Select only facts ending at the latest periodic report, pairing exact cash-flow spans."""
    out: dict[str, Any] = {}
    cash = facts["cash"]
    out["cash"] = cash if cash and cash["end"] == report_end else None
    labels = VERIFIED_DEBT_BUCKETS.get((ticker, report_end), (None, None))
    for metric, bucket in zip(
        ("remaining_fiscal_year_principal_schedule", "first_full_year_principal_schedule"),
        labels,
        strict=True,
    ):
        value = facts[metric]
        out[metric] = (
            {**value, "bucket": bucket}
            if bucket and value and value["end"] == report_end else None
        )

    for span in ("quarter", "year_to_date", "annual"):
        ocf = facts["operating_cash_flow"][span]
        capex = facts["cash_capex"][span]
        if not same_period(ocf, capex) or ocf["end"] != report_end:
            continue
        paired = derived.get(f"{span}_cash_after_capex")
        if paired and paired["start"] == ocf["start"] and paired["end"] == report_end:
            out.update(
                {
                    "cash_flow_span": span,
                    "operating_cash_flow": ocf,
                    "cash_capex": capex,
                    "cash_after_capex": paired,
                }
            )
            return out

    # Preserve current individual observations even where no exact pair exists.
    # A missing or mismatched capex never becomes zero cash spend.
    for metric in ("operating_cash_flow", "cash_capex"):
        out[metric] = next(
            (
                value
                for span in ("quarter", "year_to_date", "annual")
                if (value := facts[metric][span]) and value["end"] == report_end
            ),
            None,
        )
    out["cash_flow_span"] = None
    out["cash_after_capex"] = None
    return out


def refresh_one(
    sec: RateLimitedSec, ticker: str, cik: str, role: str, as_of: date, raw_dir: Path
) -> dict[str, Any]:
    item: dict[str, Any] = {"ticker": ticker, "cik": cik, "role": role, "errors": []}
    submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    for label, url in (("submissions", submissions_url), ("companyfacts", facts_url)):
        try:
            data, digest, state = fetch_json(sec, url, raw_dir / f"CIK{cik}-{label}.json.gz")
            item[f"{label}_source"] = {"url": url, "sha256": digest, "state": state}
            if label == "submissions":
                item["sec_name"] = data.get("name")
                filings = recent_filings(data, cik, as_of)
                item["latest_periodic_filing"] = next(
                    (filing for filing in filings if filing["form"] in PERIODIC_FORMS), None
                )
                item["new_filings_since_june_13"] = [
                    filing for filing in filings if filing["filing_date"] > BASELINE_DATE.isoformat()
                ]
                item["new_filing_count"] = len(item["new_filings_since_june_13"])
            else:
                latest = item.get("latest_periodic_filing") or {}
                item["facts"] = select_facts(data, as_of, latest.get("report_date"))
                item["derived"] = comparable_ratios(item["facts"])
                item["current_liquidity"] = current_liquidity(
                    ticker, item["facts"], item["derived"], latest.get("report_date")
                )
        except (OSError, urllib.error.URLError, ValueError, json.JSONDecodeError) as exc:
            item["errors"].append({"source": label, "error": f"{type(exc).__name__}: {exc}"})
    item["status"] = (
        "complete"
        if "submissions_source" in item and "companyfacts_source" in item
        else "partial" if "submissions_source" in item or "companyfacts_source" in item else "unavailable"
    )
    return item


def render_markdown(panel: dict[str, Any]) -> str:
    def money_billions(amount: float) -> str:
        return f"-${abs(amount) / 1e9:.3f}B" if amount < 0 else f"${amount / 1e9:.3f}B"

    lines = [
        f"# AI case-zero SEC financial snapshot, {panel['as_of']}",
        "",
        "This freezes current SEC submissions and selected XBRL facts for the original issuer cohort and filed counterparties. It does not change the June score or the registered signal thresholds. Dollar values below are USD billions. A missing value means the chosen SEC XBRL tags did not produce a comparable fact by the as-of date.",
        "",
        f"Checked {panel['target_count']} CIKs: {panel['complete_count']} with both SEC endpoints returned, {panel['partial_count']} partial, {panel['unavailable_count']} unavailable. Full filing lists, fact provenance, and errors are in [the JSON]({panel['output_json_name']}).",
        "",
    ]
    for item in panel["entities"]:
        filing = item.get("latest_periodic_filing") or {}
        facts = item.get("facts") or {}
        derived = item.get("derived") or {}
        liquidity = item.get("current_liquidity") or {}
        revenue = next(
            (r for key in ("quarter", "annual")
             if (r := (facts.get("revenue") or {}).get(key)) and r["matches_latest_periodic_report"]),
            None,
        )
        debt = facts.get("total_debt_reported")
        if debt and not debt["matches_latest_periodic_report"]:
            debt = None
        coverage = next(
            (r for key in ("quarter_interest_coverage", "year_to_date_interest_coverage", "annual_interest_coverage")
             if (r := derived.get(key)) and r["end"] == filing.get("report_date")),
            None,
        )
        rev_text = f"${revenue['value_usd'] / 1e9:.3f}B ({revenue['start']} to {revenue['end']}; tag {revenue['tag']})" if revenue else "no current-period XBRL value"
        debt_text = f"${debt['value_usd'] / 1e9:.3f}B ({debt['end']}; tag {debt['tag']})" if debt else "no current-period XBRL value"
        cov_text = f"{coverage['value']:.2f}x ({coverage['start']} to {coverage['end']}; {coverage['method']})" if coverage else "unavailable"
        form_text = f"[{filing['form']} filed {filing['filing_date']}]({filing['url']})" if filing else "no periodic filing found"
        lines += [
            f"**{item['ticker']} ({item['role']})**: {form_text}. Consolidated revenue {rev_text}; debt tag {debt_text}; same-period interest coverage {cov_text}. New filings since June 13: {item.get('new_filing_count', 'unknown')}.",
        ]
        cash = liquidity.get("cash")
        ocf = liquidity.get("operating_cash_flow")
        capex = liquidity.get("cash_capex")
        residual = liquidity.get("cash_after_capex")
        cash_text = money_billions(cash["value_usd"]) if cash else "unavailable"
        def flow_text(value: dict[str, Any] | None) -> str:
            return (
                f"{money_billions(value['value_usd'])} ({value['start']} to {value['end']})"
                if value else "unavailable"
            )
        residual_text = (
            f"{money_billions(residual['value_usd'])} ({residual['start']} to {residual['end']})"
            if residual else "unavailable: no matching current-period cash-flow span"
        )
        debt_buckets = [
            value for metric in (
                "remaining_fiscal_year_principal_schedule", "first_full_year_principal_schedule"
            ) if (value := liquidity.get(metric))
        ]
        maturity_text = (
            ", ".join(f"{value['bucket']} {money_billions(value['value_usd'])}" for value in debt_buckets)
            if debt_buckets else "unavailable"
        )
        lines += [
            f"Cash at report end {cash_text}; operating cash flow {flow_text(ocf)}; cash capex {flow_text(capex)}; cash after capex {residual_text}; verified debt principal schedule {maturity_text}.",
            "",
        ]
        if item["errors"]:
            lines += [f"Source errors: {', '.join(e['error'] for e in item['errors'])}.", ""]
    lines += [
        "Only values ending at the latest periodic report date appear above. Cash after capex is operating cash flow less cash paid to acquire property, productive assets, or equipment only when both facts cover identical start and end dates. Debt principal labels reflect the annual buckets in seven directly checked issuer debt notes. The XBRL tag named `InNextTwelveMonths` can denote the following calendar or fiscal year, rather than the rolling next 12 months; unmapped schedules are withheld. Interest coverage uses operating income plus depreciation and amortization only when both tags have the same start and end dates as interest expense. Otherwise it uses operating income alone. The selected tags may omit issuer-specific debt, leases, noncash capex, segment or non-GAAP items. Galaxy's consolidated revenue includes gross digital-asset trading and is not comparable to cloud rental revenue. Foreign issuer interim 6-K disclosures may lack structured XBRL. These are reviewable source observations, not an automated verdict. Raw SEC JSON responses are retained locally under `data/issuer_refresh/` and their SHA-256 hashes are in the JSON panel.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", type=date.fromisoformat, default=DEFAULT_AS_OF)
    parser.add_argument("--sec-requests-per-second", type=float, default=2.0)
    args = parser.parse_args()
    if args.sec_requests_per_second <= 0 or args.sec_requests_per_second > 2:
        parser.error("SEC request rate must be in (0, 2] requests per second")
    root = Path(__file__).resolve().parent.parent
    raw_dir = root / "data" / "issuer_refresh" / args.as_of.isoformat() / "raw"
    output_stem = root / "analysis" / f"case_zero_financials_{args.as_of.isoformat()}_v4"
    json_path = output_stem.with_suffix(".json")
    md_path = output_stem.with_suffix(".md")
    if json_path.exists() or md_path.exists():
        parser.error("dated analysis output exists; inspect it before another mutating run")
    sec = RateLimitedSec(args.sec_requests_per_second)
    entities = []
    for index, (ticker, cik, role) in enumerate(TARGETS, 1):
        item = refresh_one(sec, ticker, cik, role, args.as_of, raw_dir)
        entities.append(item)
        print(f"{index}/{len(TARGETS)} {ticker} {item['status']} ({len(item['errors'])} errors)", flush=True)
    panel = {
        "as_of": args.as_of.isoformat(),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "baseline_date": BASELINE_DATE.isoformat(),
        "target_count": len(TARGETS),
        "complete_count": sum(e["status"] == "complete" for e in entities),
        "partial_count": sum(e["status"] == "partial" for e in entities),
        "unavailable_count": sum(e["status"] == "unavailable" for e in entities),
        "source_method": "SEC submissions and companyfacts JSON; no paid APIs",
        "raw_dir": str(raw_dir.relative_to(root)),
        "output_json_name": json_path.name,
        "qa_revision": 4,
        "correction_from_v3": "Retained current-period liquidity and expanded capex tags; mapped debt schedule facts to issuer-verified calendar or fiscal-year buckets rather than rolling twelve months. V2 and V3 drafts remain preserved locally.",
        "entities": entities,
    }
    with json_path.open("x") as output:
        json.dump(panel, output, indent=2, sort_keys=True)
        output.write("\n")
    with md_path.open("x") as output:
        output.write(render_markdown(panel))
    print(f"wrote {json_path.relative_to(root)} and {md_path.relative_to(root)}")
    return 0 if panel["complete_count"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
