"""Extract ratepayer/downside terms from state PUC and utility filings.

The utility/ratepayer downside lane depends on terms that usually live outside
SEC debt tables: large-load tariff thresholds, minimum service commitments,
exit fees, take-or-pay percentages, incremental generation charges, and explicit
ratepayer-protection or cost-shift language. This module converts acquired text
source rows into normalized term-evidence rows without deciding the final
economic exposure.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any

_DOLLAR_PER_KW_RE = re.compile(r"\$(?P<value>\d+(?:\.\d+)?)\s*per\s*kW", re.IGNORECASE)
_EXIT_FEE_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?:%|percent).*?(?:exit|early[- ]exit|termination)",
    re.IGNORECASE | re.DOTALL,
)
_LOAD_FACTOR_RE = re.compile(r"load\s+factor\s+of\s+(?P<value>\d+(?:\.\d+)?)\s*%", re.IGNORECASE)
_MW_THRESHOLD_RE = re.compile(
    r"(?P<value>\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*MW\s*(?P<context>.{0,80})",
    re.IGNORECASE | re.DOTALL,
)
_MW_RANGE_RE = re.compile(
    r"between\s+(?P<low>\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s+and\s+"
    r"(?P<high>\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*MW\s*(?P<context>.{0,80})",
    re.IGNORECASE | re.DOTALL,
)
_TAKE_OR_PAY_RE = re.compile(
    r"take[- ]or[- ]pay(?:\s+provision)?(?:\s+set\s+at)?\s+(?P<value>\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)
_TERM_YEARS_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?:-|\s)?year[s]?(?:\s+or\s+more|\s+minimum|\s+term|\s+contract)",
    re.IGNORECASE,
)
_TEXT_SPACING_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class RegulatoryRatepayerTerm:
    """One extracted ratepayer/downside term from a regulatory source row."""

    term_type: str
    value: str
    unit: str
    quote: str
    source_id: str
    source_uri: str
    document_id: str
    utility_family: str
    jurisdiction: str
    regulator: str
    docket_or_filing: str
    confidence: str

    def to_row(self) -> dict[str, str]:
        return asdict(self)


def extract_ratepayer_terms_from_rows(
    rows: list[dict[str, Any]],
) -> list[RegulatoryRatepayerTerm]:
    """Extract normalized ratepayer terms from acquired source rows."""

    terms: list[RegulatoryRatepayerTerm] = []
    for row in rows:
        terms.extend(extract_ratepayer_terms(row))
    return terms


def extract_ratepayer_terms(row: dict[str, Any]) -> list[RegulatoryRatepayerTerm]:
    """Extract large-load/ratepayer term evidence from one acquired text row."""

    text = _normalized_text(row.get("text") or row.get("quote") or row.get("source_quote") or "")
    if not text:
        return []

    terms: list[RegulatoryRatepayerTerm] = []
    terms.extend(_numeric_terms(row, text))
    terms.extend(_boolean_terms(row, text))
    return _dedupe_terms(terms)


def _numeric_terms(row: dict[str, Any], text: str) -> list[RegulatoryRatepayerTerm]:
    terms: list[RegulatoryRatepayerTerm] = []
    for match in _MW_RANGE_RE.finditer(text):
        context = match.group("context")
        if not _mw_context_is_ratepayer_relevant(context):
            continue
        quote = _quote(text, match.start(), match.end())
        terms.append(
            _term(row, "large_load_threshold_mw", _clean_number(match.group("low")), "MW", quote)
        )
        terms.append(
            _term(row, "large_load_threshold_mw", _clean_number(match.group("high")), "MW", quote)
        )

    for match in _MW_THRESHOLD_RE.finditer(text):
        context = match.group("context")
        if not _mw_context_is_ratepayer_relevant(context):
            continue
        value = _clean_number(match.group("value"))
        if "load growth" in context.lower() or "load forecast" in context.lower():
            term_type = "load_growth_mw"
        else:
            term_type = "large_load_threshold_mw"
        terms.append(_term(row, term_type, value, "MW", _quote(text, match.start(), match.end())))

    terms.extend(
        _regex_numeric_terms(
            row,
            text,
            _TERM_YEARS_RE,
            term_type="minimum_contract_term_years",
            unit="years",
        )
    )

    terms.extend(
        _regex_numeric_terms(
            row,
            text,
            _TAKE_OR_PAY_RE,
            term_type="take_or_pay_pct",
            unit="pct",
        )
    )

    terms.extend(
        _regex_numeric_terms(
            row,
            text,
            _EXIT_FEE_RE,
            term_type="exit_fee_pct",
            unit="pct",
        )
    )

    terms.extend(
        _regex_numeric_terms(
            row,
            text,
            _LOAD_FACTOR_RE,
            term_type="load_factor_pct",
            unit="pct",
        )
    )

    terms.extend(
        _regex_numeric_terms(
            row,
            text,
            _DOLLAR_PER_KW_RE,
            term_type="incremental_generation_charge_per_kw",
            unit="USD_per_kW",
        )
    )
    return terms


def _boolean_terms(row: dict[str, Any], text: str) -> list[RegulatoryRatepayerTerm]:
    terms: list[RegulatoryRatepayerTerm] = []
    boolean_patterns = [
        (
            "ratepayer_subsidy_protection",
            re.compile(
                r"(?:prevent(?:ing)?|protect(?:ing)?|insulat(?:e|ing)|shield(?:ing)?).{0,120}"
                r"(?:ratepayers|customers|general body of customers|subsidiz)",
                re.IGNORECASE,
            ),
        ),
        (
            "ratepayer_subsidy_risk",
            re.compile(
                r"(?:risk|at risk|subsidiz).{0,120}"
                r"(?:ratepayers|customers|general body of customers|everyday customer)",
                re.IGNORECASE,
            ),
        ),
        (
            "dedicated_infrastructure_cost_recovery",
            re.compile(
                r"(?:transmission lines|substations|interconnection upgrades|new electric generation capacity|"
                r"infrastructure upgrades|specific transmission).{0,160}(?:cost|cover|pay|recover|needed)",
                re.IGNORECASE,
            ),
        ),
        (
            "separate_customer_class",
            re.compile(
                r"(?:separate|dedicated).{0,80}(?:customer|rate).{0,40}class", re.IGNORECASE
            ),
        ),
        (
            "bring_your_own_generation",
            re.compile(r"(?:bring your own generation|BYOG)", re.IGNORECASE),
        ),
        (
            "data_center_load_driver",
            re.compile(
                r"(?:data center|data centers|Meta|Laidley|Google|hyperscale|large-scale data)",
                re.IGNORECASE,
            ),
        ),
    ]
    for term_type, pattern in boolean_patterns:
        for match in pattern.finditer(text):
            terms.append(
                _term(row, term_type, "present", "flag", _quote(text, match.start(), match.end()))
            )
            break
    return terms


def _mw_context_is_ratepayer_relevant(context: str) -> bool:
    context_lower = context.lower()
    markers = (
        "or greater",
        "or more",
        "threshold",
        "large",
        "data center",
        "anticipated",
        "peak",
        "incremental",
        "between",
        "customer",
        "tariff",
        "load growth",
        "load forecast",
        "winter",
    )
    return any(marker in context_lower for marker in markers)


def _term(
    row: dict[str, Any],
    term_type: str,
    value: str,
    unit: str,
    quote: str,
) -> RegulatoryRatepayerTerm:
    metadata = _metadata(row)
    return RegulatoryRatepayerTerm(
        term_type=term_type,
        value=value,
        unit=unit,
        quote=quote,
        source_id=str(row.get("source_id") or ""),
        source_uri=str(row.get("source_uri") or ""),
        document_id=str(row.get("document_id") or ""),
        utility_family=str(row.get("utility_family") or metadata.get("utility_family") or ""),
        jurisdiction=str(row.get("jurisdiction") or metadata.get("jurisdiction") or ""),
        regulator=str(row.get("regulator") or metadata.get("regulator") or ""),
        docket_or_filing=str(row.get("docket_or_filing") or metadata.get("docket_or_filing") or ""),
        confidence="pattern_extracted",
    )


def _regex_numeric_terms(
    row: dict[str, Any],
    text: str,
    pattern: re.Pattern[str],
    *,
    term_type: str,
    unit: str,
) -> list[RegulatoryRatepayerTerm]:
    return [
        _term(
            row,
            term_type,
            _clean_number(match.group("value")),
            unit,
            _quote(text, match.start(), match.end()),
        )
        for match in pattern.finditer(text)
    ]


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


def _quote(text: str, start: int, end: int, *, radius: int = 120) -> str:
    quote_start = max(0, start - radius)
    quote_end = min(len(text), end + radius)
    return text[quote_start:quote_end].strip()


def _clean_number(value: str) -> str:
    return value.replace(",", "").strip()


def _dedupe_terms(terms: list[RegulatoryRatepayerTerm]) -> list[RegulatoryRatepayerTerm]:
    seen: set[tuple[str, str, str, str]] = set()
    deduped: list[RegulatoryRatepayerTerm] = []
    for term in terms:
        key = (term.term_type, term.value, term.unit, term.quote)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(term)
    return deduped
