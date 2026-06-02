"""Extract off-balance-sheet AI compute economic commitments.

This module targets the hidden-leverage tier that is deliberately separate from
committed debt: datacenter purchase commitments, not-yet-commenced leases,
seller-side remaining performance obligations, and non-binding lessor revenue
claims. The extractor records the semantic tier rather than folding these
amounts into debt metrics.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any

_TEXT_SPACING_RE = re.compile(r"\s+")
_MONEY_RE = re.compile(
    r"\$\s*(?P<amount>\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*"
    r"(?P<unit>billion|million|trillion|B|M|T)?",
    re.IGNORECASE,
)
_GW_RE = re.compile(r"(?P<value>\d+(?:\.\d+)?)\s*GW\b", re.IGNORECASE)


@dataclass(frozen=True)
class EconomicCommitmentTerm:
    """One extracted off-balance-sheet economic commitment term."""

    term_type: str
    value: str
    unit: str
    binding_tier: str
    quote: str
    source_id: str
    source_uri: str
    document_id: str
    entity: str
    counterparty: str
    confidence: str
    double_count_caveat: str

    def to_row(self) -> dict[str, str]:
        return asdict(self)


def extract_economic_commitments_from_rows(
    rows: list[dict[str, Any]],
) -> list[EconomicCommitmentTerm]:
    """Extract economic-commitment terms from acquired source rows."""

    terms: list[EconomicCommitmentTerm] = []
    for row in rows:
        terms.extend(extract_economic_commitments(row))
    return terms


def extract_economic_commitments(row: dict[str, Any]) -> list[EconomicCommitmentTerm]:
    """Extract one row's AI compute commitment terms.

    Rows are expected to come from source-catalog text acquisition or EDGAR text
    extraction and may carry ``metadata`` JSON. The function is side-effect free.
    """

    text = _normalized_text(row.get("text") or row.get("quote") or row.get("source_quote") or "")
    if not text:
        return []

    terms: list[EconomicCommitmentTerm] = []
    for match in _MONEY_RE.finditer(text):
        quote = _quote(text, match.start(), match.end())
        classification = _classify_money_quote(quote)
        if classification is None:
            continue
        term_type, binding_tier, caveat = classification
        amount = _money_to_usd(match.group("amount"), match.group("unit"))
        if amount is None:
            continue
        terms.append(
            _term(
                row,
                term_type=term_type,
                value=str(amount),
                unit="USD",
                binding_tier=binding_tier,
                quote=quote,
                double_count_caveat=caveat,
            )
        )

    for match in _GW_RE.finditer(text):
        quote = _quote(text, match.start(), match.end())
        if not _is_capacity_only_quote(quote):
            continue
        terms.append(
            _term(
                row,
                term_type="capacity_only_no_dollar",
                value=match.group("value"),
                unit="GW",
                binding_tier="GIGAWATT_ONLY_NO_DOLLAR",
                quote=quote,
                double_count_caveat="capacity-only disclosure; no source-backed dollar obligation",
            )
        )
    return _dedupe_terms(terms)


def _classify_money_quote(quote: str) -> tuple[str, str, str] | None:
    q = quote.lower()
    if _is_negated_commitment_context(q):
        return None

    rules: tuple[tuple[bool, tuple[str, str, str]], ...] = (
        (
            "purchase commitment" in q and _has_datacenter_or_compute_context(q),
            (
                "datacenter_purchase_commitment",
                "BINDING_BLENDED_BUYER",
                "buyer-side commitment; may blend cancellable purchase orders with take-or-pay contracts",
            ),
        ),
        (
            "lease" in q and ("not yet commenced" in q or "not-yet-commenced" in q),
            (
                "not_commenced_datacenter_lease",
                "BINDING_LEASE",
                "lease tier; keep separate from purchase commitments and debt",
            ),
        ),
        (
            ("remaining performance obligation" in q or "rpo" in q) and "take-or-pay" in q,
            (
                "seller_remaining_performance_obligation",
                "BINDING_TAKE_OR_PAY_SELLER_MIRROR",
                "seller-side backlog mirror; do not sum with buyer-side commitments",
            ),
        ),
        (
            "take-or-pay" in q and _has_datacenter_or_compute_context(q),
            (
                "take_or_pay_compute_commitment",
                "BINDING_TAKE_OR_PAY",
                "buyer-side obligation if disclosed by buyer; otherwise verify mirror risk before summing",
            ),
        ),
        (
            ("anticipated rental revenue" in q or "estimated cumulative revenue" in q)
            and ("lease" in q or "hosting" in q or "colocation" in q),
            (
                "lessor_revenue_projection",
                "NON_BINDING_LESSOR_REVENUE",
                "lessor revenue estimate; not a buyer obligation without contract-payment terms",
            ),
        ),
    )
    for matched, result in rules:
        if matched:
            return result
    return None


def _is_negated_commitment_context(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "did not discuss",
            "does not discuss",
            "no purchase commitment",
            "no purchase commitments",
            "no take-or-pay",
            "no datacenter lease",
            "no data center lease",
        )
    )


def _has_datacenter_or_compute_context(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "datacenter",
            "data center",
            "compute",
            "cloud",
            "ai infrastructure",
            "capacity",
            "gpu",
        )
    )


def _is_capacity_only_quote(quote: str) -> bool:
    q = quote.lower()
    return _has_datacenter_or_compute_context(q) and "$" not in quote


def _term(
    row: dict[str, Any],
    *,
    term_type: str,
    value: str,
    unit: str,
    binding_tier: str,
    quote: str,
    double_count_caveat: str,
) -> EconomicCommitmentTerm:
    metadata = _metadata(row)
    return EconomicCommitmentTerm(
        term_type=term_type,
        value=value,
        unit=unit,
        binding_tier=binding_tier,
        quote=quote,
        source_id=str(row.get("source_id") or ""),
        source_uri=str(row.get("source_uri") or ""),
        document_id=str(row.get("document_id") or ""),
        entity=str(row.get("entity") or metadata.get("entity") or ""),
        counterparty=str(row.get("counterparty") or metadata.get("counterparty") or ""),
        confidence="pattern_extracted",
        double_count_caveat=double_count_caveat,
    )


def _money_to_usd(amount: str, unit: str | None) -> int | None:
    clean = amount.replace(",", "")
    try:
        value = float(clean)
    except ValueError:
        return None
    multiplier = {
        "trillion": 1_000_000_000_000,
        "t": 1_000_000_000_000,
        "billion": 1_000_000_000,
        "b": 1_000_000_000,
        "million": 1_000_000,
        "m": 1_000_000,
        None: 1,
        "": 1,
    }.get((unit or "").lower())
    if multiplier is None:
        return None
    return round(value * multiplier)


def _metadata(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("metadata")
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _normalized_text(value: Any) -> str:
    return _TEXT_SPACING_RE.sub(" ", str(value or "")).strip()


def _quote(text: str, start: int, end: int, *, radius: int = 180) -> str:
    quote_start = max(0, start - radius)
    quote_end = min(len(text), end + radius)
    return text[quote_start:quote_end].strip()


def _dedupe_terms(terms: list[EconomicCommitmentTerm]) -> list[EconomicCommitmentTerm]:
    seen: set[tuple[str, str, str, str]] = set()
    deduped: list[EconomicCommitmentTerm] = []
    for term in terms:
        key = (term.term_type, term.value, term.unit, term.quote)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(term)
    return deduped
