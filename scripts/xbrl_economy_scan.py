"""Financials-based fragility scan over the SEC exchange-ticker reference (no LLM agents).

Breaks the deal-corpus dependency: instead of scoring only the ~2,007 entities that appear
in our EDGAR deal extraction, the fresh mode pulls XBRL financial facts for each CIK in
the SEC exchange-ticker reference and computes net-debt/EBITDA (leverage) and
EBITDA/interest (coverage). Ratios avoid direct dependence on deal-notional totals, but
coverage remains limited by ticker inclusion and XBRL tag availability. Pure HTTP to
data.sec.gov + local compute uses ZERO
LLM agents, so it runs fine under an LLM rate-limit cooldown.

In-memory fetch (companyfacts discarded after parse); writes only the ratio table.
Resumable: caches results every 200 filers.

Default output: analysis/economy_xbrl_fragility.{json,md} (legacy cache).
Fresh run: --refresh-date YYYY-MM-DD writes separate dated cache and outputs.
"""

from __future__ import annotations

# ruff: noqa: PERF401, RUF001
import json
import argparse
import hashlib
import os
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from xbrl_net_leverage import (  # noqa: E402
    CASH_TAGS,
    INT_TAGS,
    annual_observations,
    ebitda,
    ebitda_observation,
    fetch_json,
    latest_annual,
    latest_annual_observation,
    latest_instant,
    latest_instant_observation,
    instant_observations,
    total_debt,
    total_debt_observation,
    total_debt_observations,
    UA,
)

SEC_REF = ROOT / "data" / "entity_universe" / "raw" / "sec_company_tickers_exchange.json"
SEC_REF_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
OUT_JSON = ROOT / "analysis" / "economy_xbrl_fragility.json"
OUT_MD = ROOT / "analysis" / "economy_xbrl_fragility.md"
CACHE = ROOT / "data" / "entity_universe" / "xbrl_economy_cache.json"
RATE_S = 0.12
SELECTOR_VERSION = 7  # v7 matches interest to the latest available EBITDA year.
MAX_BALANCE_AGE_DAYS = 186
MAX_ANNUAL_AGE_DAYS = 456


def classify(net_debt, eb, cov):
    if eb is not None and eb <= 0:
        return "negative_ebitda"
    if cov is None or eb is None:
        return "insufficient_data"
    if cov < 1.5:
        return "distressed"
    if net_debt is None:
        return "insufficient_data"
    nd_e = (net_debt / eb) if (net_debt is not None and eb > 0) else None
    if nd_e is not None and nd_e >= 5:
        return "refi_risk"
    return "manageable"


def load_universe(reference_path: Path = SEC_REF) -> list[dict]:
    d = json.loads(reference_path.read_text())
    fields = d["fields"]
    ci, ti, ni = fields.index("cik"), fields.index("ticker"), fields.index("name")
    out = []
    seen = set()
    for row in d["data"]:
        cik = str(row[ci]).zfill(10)
        if cik in seen:
            continue
        seen.add(cik)
        out.append({"cik": cik, "ticker": row[ti], "name": row[ni]})
    return out


def legacy_main() -> None:
    universe = load_universe()
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    print(f"economy XBRL scan: {len(universe)} filers; {len(cache)} cached")
    for i, ent in enumerate(universe, 1):
        cik = ent["cik"]
        if cik in cache:
            continue
        facts = fetch_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")
        time.sleep(RATE_S)
        if not facts:
            cache[cik] = {**ent, "status": "no_xbrl"}
        else:
            debt = total_debt(facts)
            cash = latest_instant(facts, CASH_TAGS)
            eb, _ = ebitda(facts)
            inte = latest_annual(facts, INT_TAGS)
            nd = (debt - (cash or 0)) if debt is not None else None
            cov = (eb / inte) if (eb is not None and inte and inte > 0) else None
            cache[cik] = {
                **ent,
                "status": "ok",
                "debt_b": round(debt / 1e9, 2) if debt is not None else None,
                "net_debt_b": round(nd / 1e9, 2) if nd is not None else None,
                "ebitda_b": round(eb / 1e9, 2) if eb is not None else None,
                "interest_b": round(inte / 1e9, 3) if inte is not None else None,
                "nd_ebitda": round(nd / eb, 1) if (nd is not None and eb and eb > 0) else None,
                "coverage": round(cov, 2) if cov is not None else None,
                "classification": classify(nd, eb, cov),
            }
        if i % 200 == 0:
            CACHE.write_text(json.dumps(cache))
            print(f"  {i}/{len(universe)} pulled")
    CACHE.write_text(json.dumps(cache))

    rows = [v for v in cache.values() if v.get("status") == "ok"]
    dist = Counter(r["classification"] for r in rows)
    distressed = sorted(
        [r for r in rows if r["classification"] == "distressed"],
        key=lambda r: r.get("coverage") if r.get("coverage") is not None else 9,
    )
    out = {
        "filers_scanned": len(cache),
        "with_xbrl": len(rows),
        "distribution": dict(dist),
        "distressed_count": len(distressed),
        "distressed": distressed[:200],
    }
    OUT_JSON.write_text(json.dumps(out, indent=2))
    write_md(out)
    print(f"done: {len(rows)} with XBRL; distribution {dict(dist)}")


BANNER = (ROOT / "analysis" / "economy_wide_fragility_map.md").read_text().split("\n")[2]


def write_md(
    out: dict, output_path: Path = OUT_MD, json_name: str = "economy_xbrl_fragility.json"
) -> None:
    L = []
    if out.get("selector_version") == SELECTOR_VERSION:
        L.append("# XBRL ratio screen: SEC exchange-ticker reference universe")
    else:
        L.append("# Economy-wide XBRL fragility — all public filers, ratio-based (size-bias-free)")
    L.append("")
    if out.get("selector_version") != SELECTOR_VERSION:
        L.append(BANNER)
        L.append("")
    if out.get("selector_version") == SELECTOR_VERSION:
        L.append(
            f"This scan covers **{out['filers_scanned']} CIKs in the SEC exchange-ticker "
            f"reference**, including {out['with_xbrl']} nonempty companyfacts responses. "
            f"The SEC returned {out['without_xbrl_http_404']} HTTP 404 responses and "
            f"{out['without_xbrl_empty_http_200']} empty HTTP 200 JSON objects. The reference "
            "omits filers without exchange tickers. Ratios use XBRL financial facts, separate "
            "from deal-notional totals. These are raw financial screen labels, not "
            "observed distress or an estimate of distress prevalence. "
            f"Distribution: {out['distribution']}. **{out['distressed_count']}** meet "
            "the uncalibrated interest-coverage cutoff below 1.5. The JSON includes all "
            f"{out['filers_scanned']} per-filer results and field definitions. Machine-readable: "
            f"[{json_name}]({json_name})."
        )
    else:
        L.append(
            f"Financials-based scan over **{out['filers_scanned']} SEC filers** "
            f"({out['with_xbrl']} with a companyfacts response), independent of the deal "
            "corpus and immune to gross-notional size-bias (ratio-based: "
            "net-debt/EBITDA + EBITDA/interest). "
            f"Distribution: {out['distribution']}. **{out['distressed_count']} filers show "
            f"interest coverage < 1.5×** (the real distress line). "
            f"Machine-readable: [{json_name}]({json_name})."
        )
    L.append("")
    if out.get("selector_version") == SELECTOR_VERSION:
        L.append("## Lowest positive-EBITDA interest coverage (top 60 screen hits)")
    else:
        L.append("## Most distressed by interest coverage (top 60)")
    L.append("")
    L.append("| entity | ticker | net debt $B | ND/EBITDA | int cov | EBITDA $B |")
    L.append("|---|---|---:|---:|---:|---:|")
    for r in out["distressed"][:60]:
        L.append(
            f"| {r['name'][:34]} | {r.get('ticker', '')} | {r.get('net_debt_b', '—')} | "
            f"{r.get('nd_ebitda', '—')} | {r.get('coverage', '—')} | {r.get('ebitda_b', '—')} |"
        )
    L.append("")
    if out.get("selector_version") == SELECTOR_VERSION:
        L.append(
            f"*Among {out['with_xbrl']} companyfacts responses, the dated scan has "
            f"{out['balance_sheet_period_aligned']} filers with a matched "
            f"debt/cash period ({out['balance_sheet_current']} within {MAX_BALANCE_AGE_DAYS} "
            f"days) and {out['income_period_aligned']} with matched EBITDA/interest years "
            f"({out['income_current']} within {MAX_ANNUAL_AGE_DAYS} days). "
            f"{out['positive_ebitda_coverage']} have positive-EBITDA interest coverage and "
            f"{out['net_debt_to_ebitda_available']} have usable net-debt/EBITDA. Missing, stale or "
            "mismatched components are withheld from the affected ratio. "
            "Annual earnings can still predate the latest quarterly balance sheet. "
            "Banks, insurers, REITs, BDCs and utilities need sector-specific metrics. "
            "Negative EBITDA can reflect startup or accounting effects and is not "
            "evidence that debt service failed. Every screen hit requires company-level review.*"
        )
    else:
        L.append(
            "*Single-period ratios from latest XBRL. Financials/REIT/BDC leverage is not "
            "comparable to corporate (deposits/portfolio debt) — read those by sector. "
            "`distressed` = EBITDA/interest < 1.5×; `negative_ebitda` is tracked separately. "
            "This is the breadth layer; the deal-corpus signature scan + deep agents are the depth layer.*"
        )
    output_path.write_text("\n".join(L) + "\n")


def fetch_sec_json(url: str) -> tuple[dict | None, int | None, str | None]:
    """Distinguish missing SEC data from a failed request."""
    request = urllib.request.Request(
        url, headers={"User-Agent": os.environ.get("EDGAR_IDENTITY") or UA}
    )
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            return json.load(response), None, None
    except urllib.error.HTTPError as exc:
        return None, exc.code, f"HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return None, None, f"{type(exc).__name__}: {exc}"[:160]


def load_refresh_cache(path: Path) -> dict[str, dict]:
    """Read the last observation per filer from the append-only, dated run log."""
    rows: dict[str, dict] = {}
    if not path.exists():
        return rows
    with path.open() as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: corrupt refresh record") from exc
            cik = row.get("cik")
            if not isinstance(cik, str) or not cik:
                raise ValueError(f"{path}:{line_number}: missing CIK")
            if (
                row.get("selector_version") == 7
                and row.get("status") == "no_xbrl"
                and "no_xbrl_reason" not in row
            ):
                # Earlier v7 code only assigned no_xbrl after an SEC HTTP 404.
                row["no_xbrl_reason"] = "http_404"
            rows[cik] = row
    return rows


def period_age_days(period_end: str | None, as_of: date) -> int | None:
    if not period_end:
        return None
    try:
        return (as_of - date.fromisoformat(period_end)).days
    except ValueError:
        return None


def current_row(
    ent: dict,
    facts: dict | None,
    status: str,
    source: str,
    error: str | None,
    as_of: date | None = None,
) -> dict:
    """Calculate the existing ratio definitions and attach retrieval provenance."""
    row = {
        **ent,
        "status": status,
        "source_uri": source,
        "fetched_at": datetime.now(UTC).isoformat(),
        "selector_version": SELECTOR_VERSION,
    }
    if error:
        row["fetch_error"] = error
    if facts is None:
        return row
    measurement_date = as_of or datetime.now(UTC).date()
    debt_by_date = total_debt_observations(facts)
    cash_by_date = instant_observations(facts, CASH_TAGS)
    debt_latest = total_debt_observation(facts)
    cash_latest = latest_instant_observation(facts, CASH_TAGS)
    matched_dates = debt_by_date.keys() & cash_by_date.keys()
    balance_date = max(matched_dates) if matched_dates else None
    debt_obs = debt_by_date[balance_date] if balance_date else debt_latest
    cash_obs = cash_by_date[balance_date] if balance_date else cash_latest
    eb_obs = ebitda_observation(facts)
    interest_latest = latest_annual_observation(facts, INT_TAGS)
    interest_by_period = annual_observations(facts, INT_TAGS)
    interest_obs = (
        interest_by_period.get((eb_obs["start"], eb_obs["end"]))
        if eb_obs else interest_latest
    )
    debt = debt_obs["value"] if debt_obs else None
    cash = cash_obs["value"] if cash_obs else None
    balance_age = period_age_days(debt_obs["end"] if debt_obs else None, measurement_date)
    earnings_age = period_age_days(eb_obs["end"] if eb_obs else None, measurement_date)
    same_balance_date = debt_obs and cash_obs and debt_obs["end"] == cash_obs["end"]
    same_fiscal_year = (
        eb_obs
        and interest_obs
        and (eb_obs["start"], eb_obs["end"])
        == (interest_obs["start"], interest_obs["end"])
    )
    balance_current = bool(
        same_balance_date and balance_age is not None and 0 <= balance_age <= MAX_BALANCE_AGE_DAYS
    )
    income_current = bool(
        same_fiscal_year and earnings_age is not None and 0 <= earnings_age <= MAX_ANNUAL_AGE_DAYS
    )
    eb = eb_obs["value"] if (eb_obs and earnings_age is not None and 0 <= earnings_age <= MAX_ANNUAL_AGE_DAYS) else None
    inte = interest_obs["value"] if income_current else None
    nd = debt - cash if balance_current else None
    cov = eb / inte if (eb is not None and eb > 0 and inte is not None and inte > 0) else None
    return {
        **row,
        "debt_b": round(debt / 1e9, 2) if debt is not None else None,
        "debt_period_end": debt_obs["end"] if debt_obs else None,
        "debt_latest_period_end": debt_latest["end"] if debt_latest else None,
        "debt_tag": debt_obs["tag"] if debt_obs else None,
        "cash_period_end": cash_obs["end"] if cash_obs else None,
        "cash_latest_period_end": cash_latest["end"] if cash_latest else None,
        "balance_period_end": balance_date,
        "net_debt_b": round(nd / 1e9, 2) if nd is not None else None,
        "balance_sheet_period_aligned": bool(same_balance_date),
        "balance_sheet_current": balance_current,
        "balance_sheet_age_days": balance_age,
        "ebitda_b": round(eb / 1e9, 2) if eb is not None else None,
        "ebitda_period_end": eb_obs["end"] if eb_obs else None,
        "ebitda_method": eb_obs["method"] if eb_obs else None,
        "earnings_age_days": earnings_age,
        "interest_latest_period_end": interest_latest["end"] if interest_latest else None,
        "interest_period_end": interest_obs["end"] if interest_obs else None,
        "income_period_aligned": bool(same_fiscal_year),
        "income_current": income_current,
        "interest_b": round(inte / 1e9, 3) if inte is not None else None,
        "nd_ebitda": round(nd / eb, 1) if (nd is not None and eb and eb > 0) else None,
        "coverage": round(cov, 2) if cov is not None else None,
        "classification": classify(nd, eb, cov),
    }


def refresh_current(run_date: date, requests_per_second: float = 5.0) -> int:
    """Fetch every current filer once, resuming successful same-date requests only."""
    label = run_date.isoformat()
    reference_path = SEC_REF.with_name(f"sec_company_tickers_exchange_{label}.json")
    cache_path = CACHE.with_name(f"xbrl_economy_cache_{label}.jsonl")
    json_path = OUT_JSON.with_name(f"economy_xbrl_fragility_{label}.json")
    md_path = OUT_MD.with_name(f"economy_xbrl_fragility_{label}.md")
    if json_path.exists() or md_path.exists():
        if json_path.exists() and md_path.exists():
            print(f"dated XBRL outputs already exist for {label}; no files changed")
            return 0
        raise FileExistsError(f"incomplete dated output pair for {label}; inspect before retry")

    if not reference_path.exists():
        request_started = time.monotonic()
        reference, http_code, error = fetch_sec_json(SEC_REF_URL)
        if reference is None or "fields" not in reference or "data" not in reference:
            print(
                f"fresh SEC ticker reference unavailable: {error or http_code}; no scan started",
                flush=True,
            )
            return 1
        reference_path.parent.mkdir(parents=True, exist_ok=True)
        with reference_path.open("x") as handle:
            json.dump(reference, handle)
        time.sleep(max(0.0, 1 / requests_per_second - (time.monotonic() - request_started)))
    universe = load_universe(reference_path)
    cache = load_refresh_cache(cache_path)
    current_ciks = {ent["cik"] for ent in universe}
    completed = sum(
        cache.get(cik, {}).get("status") in ("ok", "no_xbrl")
        and cache[cik].get("selector_version") == SELECTOR_VERSION
        for cik in current_ciks
    )
    attempted = 0
    print(
        f"fresh XBRL {label}: {len(universe)} filers; "
        f"{completed} successful same-date requests resumed",
        flush=True,
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("a") as handle:
        pending: dict[Future, tuple[dict, str]] = {}

        def persist(future: Future) -> int | None:
            nonlocal attempted, completed
            ent, url = pending.pop(future)
            cik = ent["cik"]
            try:
                facts, http_code, error = future.result()
            except Exception as exc:
                facts, http_code, error = None, None, f"{type(exc).__name__}: {exc}"[:160]
            empty_http_200 = facts == {} and http_code is None
            if empty_http_200:
                facts = None
            if facts is not None and (
                not isinstance(facts, dict) or not isinstance(facts.get("facts"), dict)
            ):
                facts, error = None, "Invalid SEC companyfacts structure"
            status = (
                "ok" if facts is not None
                else "no_xbrl" if http_code == 404 or empty_http_200
                else "fetch_error"
            )
            row = current_row(ent, facts, status, url, error, run_date)
            if status == "no_xbrl":
                row["no_xbrl_reason"] = "http_404" if http_code == 404 else "empty_http_200"
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
            handle.flush()
            cache[cik] = row
            attempted += 1
            if status in ("ok", "no_xbrl"):
                completed += 1
            if attempted % 100 == 0 or status == "fetch_error":
                print(
                    f"  completed {completed}/{len(universe)}; attempted this run {attempted}; "
                    f"last {cik}: {status}",
                    flush=True,
                )
            return http_code if http_code in (403, 429) else None

        stopped_http_code = None
        next_request_at = time.monotonic()
        with ThreadPoolExecutor(max_workers=16) as pool:
            for ent in universe:
                cik = ent["cik"]
                if (
                    cache.get(cik, {}).get("status") in ("ok", "no_xbrl")
                    and cache[cik].get("selector_version") == SELECTOR_VERSION
                ):
                    continue
                while pending:
                    at_capacity = len(pending) >= 16
                    timeout = None if at_capacity else max(0.0, next_request_at - time.monotonic())
                    done, _ = wait(pending, timeout=timeout, return_when=FIRST_COMPLETED)
                    for future in done:
                        stopped_http_code = persist(future) or stopped_http_code
                    if stopped_http_code or (not at_capacity and not done):
                        break
                if stopped_http_code:
                    break
                time.sleep(max(0.0, next_request_at - time.monotonic()))
                url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
                future = pool.submit(fetch_sec_json, url)
                pending[future] = (ent, url)
                next_request_at = time.monotonic() + 1 / requests_per_second
            while pending:
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    stopped_http_code = persist(future) or stopped_http_code
        if stopped_http_code:
            print(
                f"SEC returned HTTP {stopped_http_code}; stopped after persisting in-flight requests",
                flush=True,
            )

    missing = [
        ent["cik"]
        for ent in universe
        if cache.get(ent["cik"], {}).get("status") not in ("ok", "no_xbrl")
        or cache[ent["cik"]].get("selector_version") != SELECTOR_VERSION
    ]
    if missing:
        print(
            f"incomplete: {len(missing)} filers lack a successful fresh request; "
            "dated report withheld",
            flush=True,
        )
        return 1

    all_results = [cache[ent["cik"]] for ent in universe]
    rows = [row for row in all_results if row["status"] == "ok"]
    dist = Counter(row["classification"] for row in rows)
    distressed = sorted(
        [row for row in rows if row["classification"] == "distressed"],
        key=lambda row: row["coverage"] if row.get("coverage") is not None else 9,
    )
    out = {
        "run_date_label": label,
        "completed_at": datetime.now(UTC).isoformat(),
        "source": "SEC companyfacts responses for each exchange-ticker reference CIK",
        "interpretation": (
            "Raw financial screen labels, not observed distress or prevalence. "
            "The 1.5x coverage and 5x net-debt/EBITDA cutoffs are uncalibrated. "
            "Banks, insurers, REITs, BDCs, utilities and negative-EBITDA issuers "
            "require sector-specific financial and debt-service review."
        ),
        "reference_url": SEC_REF_URL,
        "reference_sha256": hashlib.sha256(reference_path.read_bytes()).hexdigest(),
        "selector_version": SELECTOR_VERSION,
        "max_balance_age_days": MAX_BALANCE_AGE_DAYS,
        "max_annual_age_days": MAX_ANNUAL_AGE_DAYS,
        "reference_path": str(reference_path),
        "cache_path": str(cache_path),
        "filers_in_reference": len(universe),
        "filers_scanned": len(universe),
        "with_xbrl": len(rows),
        "without_xbrl": len(universe) - len(rows),
        "without_xbrl_http_404": sum(
            row.get("no_xbrl_reason") == "http_404" for row in all_results
        ),
        "without_xbrl_empty_http_200": sum(
            row.get("no_xbrl_reason") == "empty_http_200" for row in all_results
        ),
        "debt_tag_available": sum(row.get("debt_period_end") is not None for row in rows),
        "cash_tag_available": sum(row.get("cash_period_end") is not None for row in rows),
        "ebitda_components_available": sum(
            row.get("ebitda_period_end") is not None for row in rows
        ),
        "interest_tag_available": sum(
            row.get("interest_latest_period_end") is not None for row in rows
        ),
        "balance_sheet_period_aligned": sum(
            bool(row.get("balance_sheet_period_aligned")) for row in rows
        ),
        "income_period_aligned": sum(bool(row.get("income_period_aligned")) for row in rows),
        "balance_sheet_current": sum(bool(row.get("balance_sheet_current")) for row in rows),
        "income_current": sum(bool(row.get("income_current")) for row in rows),
        "positive_ebitda_coverage": sum(row.get("coverage") is not None for row in rows),
        "net_debt_to_ebitda_available": sum(
            row.get("nd_ebitda") is not None for row in rows
        ),
        "distribution": dict(dist),
        "distressed_count": len(distressed),
        "distressed": distressed[:200],
        "field_definitions": {
            "status": "ok has nonempty companyfacts; no_xbrl is HTTP 404 or an empty HTTP 200 JSON object. Failed requests prevent publication.",
            "no_xbrl_reason": "http_404 or empty_http_200, retained separately from fetch errors.",
            "source_uri": "Official SEC companyfacts URL requested for this CIK.",
            "fetched_at": "UTC time when this CIK was retrieved for the dated run.",
            "debt_period_end": "Debt observation date selected for the latest debt/cash pair; latest debt date if no pair exists.",
            "cash_period_end": "Cash observation date selected for the latest debt/cash pair; latest cash date if no pair exists.",
            "balance_period_end": "Latest exact date shared by available debt and cash observations; null if none.",
            "debt_latest_period_end": "Latest debt date independently of cash pairing.",
            "cash_latest_period_end": "Latest cash date independently of debt pairing.",
            "balance_sheet_current": "Debt and cash share a date zero to 186 days before run_date_label.",
            "ebitda_period_end": "Latest fiscal-period end with an EBITDA calculation, including stale observations.",
            "interest_latest_period_end": "Latest interest expense annual-period end independently of EBITDA pairing.",
            "interest_period_end": "Interest period aligned to the latest EBITDA period; null if unavailable.",
            "income_current": "Latest EBITDA period has same-period interest and ends zero to 456 days before run_date_label.",
            "debt_b": "Reported aggregate debt or aligned current/noncurrent long-term debt components, USD billions; period in debt_period_end.",
            "net_debt_b": "Debt minus cash from the same balance date no more than 186 days old, USD billions; otherwise null.",
            "ebitda_b": "Latest 330-390-day aligned operating income plus D&A, or net income plus interest, tax and D&A; USD billions; null if older than 456 days.",
            "interest_b": "Annual interest expense from the EBITDA fiscal period, USD billions; null if that period is missing or older than 456 days.",
            "coverage": "Positive EBITDA divided by positive interest from the same current annual period; otherwise null.",
            "nd_ebitda": "Current matched-period net debt divided by positive current annual EBITDA; balance and earnings periods can differ.",
            "classification": "negative_ebitda if current EBITDA is <= 0; distressed if positive-EBITDA coverage < 1.5; refi_risk if coverage >= 1.5 and net-debt/EBITDA >= 5; manageable if both ratios are available below those cutoffs; otherwise insufficient_data.",
        },
        "results": all_results,
    }
    with json_path.open("x") as handle:
        json.dump(out, handle, indent=2)
    write_md(out, md_path, json_path.name)
    print(f"complete: {len(rows)} with XBRL; wrote {json_path} and {md_path}", flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh-date",
        type=date.fromisoformat,
        help="Fetch every current filer into append-only dated cache; preserves legacy outputs.",
    )
    parser.add_argument(
        "--requests-per-second", type=float, default=5.0,
        help="SEC request rate for the fresh scan (default 5; maximum 8).",
    )
    args = parser.parse_args(argv)
    if not 0 < args.requests_per_second <= 8:
        parser.error("--requests-per-second must be greater than 0 and at most 8")
    if args.refresh_date is None:
        legacy_main()
        return 0
    return refresh_current(args.refresh_date, args.requests_per_second)


if __name__ == "__main__":
    sys.exit(main())
