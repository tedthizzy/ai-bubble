"""Normalize source-backed debt-service term cards.

The direct AI/data-center confidence gap is increasingly field-level: coupon or
floating spread, maturity, collateral, recourse, and covenant terms. This module
normalizes long-form evidence cards into one row per facility while preserving
source tier and verification status. It is intentionally separate from the
committed-debt metric so term extraction can improve DSCR/timing confidence
without changing exposure totals.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

PRIMARY_SOURCE_TIERS = {
    "primary_edgar",
    "primary_8k",
    "primary_10k",
    "primary_10q",
    "primary_424b",
    "primary_s1",
}
UNVERIFIED_SOURCE_MARKERS = ("not_verified", "press", "secondary", "rumor")
FACILITY_TERM_FIELDS = {
    "borrower",
    "collateral",
    "coupon",
    "covenant_contract_realization_ratio",
    "covenant_dscr",
    "draw_availability_until",
    "facility_size_usd",
    "fixed_coupon",
    "issuer",
    "maturity",
    "purpose",
    "rate",
    "rate_floating",
    "recourse",
    "security",
    "tranches",
    "type",
    "undrawn_fee",
}

DEBT_SERVICE_TERM_FIELDS = [
    "term_id",
    "entity",
    "facility",
    "facility_size_usd",
    "borrower",
    "purpose",
    "draw_availability_until",
    "maturity_date",
    "rate_type",
    "rate_index",
    "rate_spread_bps",
    "fixed_coupon_pct",
    "undrawn_fee_bps",
    "collateral",
    "recourse",
    "covenant_dscr",
    "covenant_contract_realization_ratio",
    "source_tier",
    "verification_status",
    "source",
    "source_uri",
    "filing_accession",
    "source_quote",
]


@dataclass(frozen=True)
class DebtServiceTerm:
    """One normalized facility-level debt-service term card."""

    term_id: str
    entity: str
    facility: str
    facility_size_usd: str
    borrower: str
    purpose: str
    draw_availability_until: str
    maturity_date: str
    rate_type: str
    rate_index: str
    rate_spread_bps: str
    fixed_coupon_pct: str
    undrawn_fee_bps: str
    collateral: str
    recourse: str
    covenant_dscr: str
    covenant_contract_realization_ratio: str
    source_tier: str
    verification_status: str
    source: str
    source_uri: str
    filing_accession: str
    source_quote: str

    def to_row(self) -> dict[str, str]:
        return asdict(self)


def normalize_debt_service_card_rows(rows: list[dict[str, Any]]) -> list[DebtServiceTerm]:
    """Normalize long-form ``entity, facility, field, value`` card rows."""

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        entity = str(row.get("entity") or "").strip()
        facility = str(row.get("facility") or "").strip()
        if not entity or not facility:
            continue
        grouped.setdefault((entity, facility), []).append(row)

    terms = [
        _term_from_rows(entity, facility, card_rows)
        for (entity, facility), card_rows in grouped.items()
        if _is_facility_card_group(facility, card_rows)
    ]
    return sorted(terms, key=lambda term: (term.entity.lower(), term.facility.lower()))


def summarize_debt_service_terms(terms: list[DebtServiceTerm]) -> dict[str, Any]:
    """Summarize normalized debt-service term coverage."""

    primary_terms = [term for term in terms if term.verification_status == "primary_verified"]
    unverified_terms = [term for term in terms if term.verification_status != "primary_verified"]
    primary_notional = sum(_float(term.facility_size_usd) for term in primary_terms)
    unverified_notional = sum(_float(term.facility_size_usd) for term in unverified_terms)
    return {
        "term_count": len(terms),
        "primary_verified_term_count": len(primary_terms),
        "unverified_term_count": len(unverified_terms),
        "primary_verified_facility_size_usd": round(primary_notional, 2),
        "unverified_facility_size_usd": round(unverified_notional, 2),
        "terms_missing_maturity": sum(1 for term in primary_terms if not term.maturity_date),
        "terms_missing_rate": sum(
            1
            for term in primary_terms
            if not (term.rate_spread_bps or term.fixed_coupon_pct or term.rate_type)
        ),
        "terms_missing_recourse": sum(1 for term in primary_terms if not term.recourse),
        "terms_missing_collateral": sum(1 for term in primary_terms if not term.collateral),
    }


def _term_from_rows(entity: str, facility: str, rows: list[dict[str, Any]]) -> DebtServiceTerm:
    fields = {_field_name(row): _value(row) for row in rows if _field_name(row)}
    source_tiers = {_source_tier(row) for row in rows if _source_tier(row)}
    source_tier = _source_tier(rows[0]) if rows else ""
    verification_status = _verification_status(source_tiers)
    rate_value = fields.get("rate_floating") or fields.get("rate") or ""
    fixed_coupon_value = fields.get("coupon") or ""
    source = _first_nonblank(rows, "source")
    source_uri = _first_nonblank(rows, "source_uri")
    accession = _first_nonblank(rows, "filing_accession") or _accession_from_text(source)
    quote = _first_nonblank(rows, "source_quote") or _source_quote_from_rows(rows)
    return DebtServiceTerm(
        term_id=f"{_slug(entity)}:{_slug(facility)}",
        entity=entity,
        facility=facility,
        facility_size_usd=_amount_usd(fields.get("facility_size_usd", "")),
        borrower=fields.get("borrower", ""),
        purpose=fields.get("purpose", ""),
        draw_availability_until=fields.get("draw_availability_until", ""),
        maturity_date=_date_like(fields.get("maturity", "")),
        rate_type=_rate_type(rate_value, fixed_coupon_value),
        rate_index=_rate_index(rate_value),
        rate_spread_bps=_spread_bps(rate_value),
        fixed_coupon_pct=_coupon_pct(fixed_coupon_value),
        undrawn_fee_bps=_spread_bps(fields.get("undrawn_fee", "")),
        collateral=fields.get("collateral", ""),
        recourse=fields.get("recourse", ""),
        covenant_dscr=fields.get("covenant_dscr", ""),
        covenant_contract_realization_ratio=fields.get("covenant_contract_realization_ratio", ""),
        source_tier=source_tier,
        verification_status=verification_status,
        source=source,
        source_uri=source_uri,
        filing_accession=accession,
        source_quote=quote,
    )


def _is_facility_card_group(facility: str, rows: list[dict[str, Any]]) -> bool:
    facility_key = facility.strip().lower()
    if facility_key in {"total", "disambiguation"}:
        return False
    if any(marker in facility_key for marker in ("not debt", "metric_questionable", "packet")):
        return False
    return any(_field_name(row) in FACILITY_TERM_FIELDS for row in rows)


def _field_name(row: dict[str, Any]) -> str:
    return str(row.get("field") or "").strip().lower()


def _value(row: dict[str, Any]) -> str:
    return str(row.get("value") or "").strip()


def _source_tier(row: dict[str, Any]) -> str:
    return str(row.get("source_tier") or "").strip().lower()


def _verification_status(source_tiers: set[str]) -> str:
    if source_tiers and all(tier in PRIMARY_SOURCE_TIERS for tier in source_tiers):
        return "primary_verified"
    if any(any(marker in tier for marker in UNVERIFIED_SOURCE_MARKERS) for tier in source_tiers):
        return "unverified_external"
    return "unverified_or_secondary"


def _first_nonblank(rows: list[dict[str, Any]], key: str) -> str:
    for row in rows:
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def _source_quote_from_rows(rows: list[dict[str, Any]]) -> str:
    parts = []
    for row in rows:
        field = _field_name(row)
        value = _value(row)
        if field and value:
            parts.append(f"{field}: {value}")
    return " | ".join(parts[:12])


def _rate_type(rate_value: str, fixed_coupon_value: str) -> str:
    text = f"{rate_value} {fixed_coupon_value}".lower()
    if any(marker in text for marker in ("sofr", "base+", "base +", "floating")):
        return "floating"
    if _coupon_pct(fixed_coupon_value or rate_value):
        return "fixed"
    return ""


def _rate_index(rate_value: str) -> str:
    text = rate_value.lower()
    if "sofr" in text:
        return "SOFR"
    if "base" in text:
        return "base_rate"
    return ""


def _spread_bps(value: str) -> str:
    match = re.search(r"(?P<pct>\d+(?:\.\d+)?)\s*%", value)
    if not match:
        return ""
    bps = round(float(match.group("pct")) * 100)
    return str(int(bps))


def _coupon_pct(value: str) -> str:
    match = re.search(r"(?P<pct>\d+(?:\.\d+)?)\s*%", value)
    return match.group("pct") if match else ""


def _date_like(value: str) -> str:
    match = re.search(r"\b(\d{4}-\d{2}(?:-\d{2})?)\b", value)
    return match.group(1) if match else ""


def _amount_usd(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    match = re.search(
        r"(?P<amount>\d+(?:,\d{3})*(?:\.\d+)?)\s*(?P<unit>trillion|billion|million|t|b|m)?\b",
        text,
        re.IGNORECASE,
    )
    if not match:
        return ""
    amount_text = match.group("amount").replace(",", "")
    try:
        amount = float(amount_text)
    except ValueError:
        return ""
    unit = (match.group("unit") or "").lower()
    multiplier = {
        "t": 1_000_000_000_000,
        "trillion": 1_000_000_000_000,
        "b": 1_000_000_000,
        "billion": 1_000_000_000,
        "m": 1_000_000,
        "million": 1_000_000,
    }.get(unit, 1)
    return str(int(amount * multiplier))


def _accession_from_text(value: str) -> str:
    match = re.search(r"\b(\d{10}-\d{2}-\d{6})\b", value)
    if match:
        return match.group(1)
    compact = re.search(r"\b(\d{18})\b", value)
    return compact.group(1) if compact else ""


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _float(value: str) -> float:
    try:
        return float(value or 0)
    except ValueError:
        return 0.0
