"""Extract physical execution and stranded-asset terms from source text.

The physical-risk layer cannot rely only on ISO queue IDs. Some flagship
AI/data-center projects are behind-the-meter or off-grid by design, so the
source-backed handle is an air permit, state utility approval, litigation
record, or explicit no-queue/bypass language. This module converts those
physical execution snippets into normalized evidence rows without treating them
as committed-debt metric inputs.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any

_TEXT_SPACING_RE = re.compile(r"\s+")
_MW_RE = re.compile(
    r"(?P<prefix>>|~|approximately|about)?\s*"
    r"(?P<value>\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?P<unit>MW|GW|megawatts?)\b"
    r"(?P<context>.{0,120})",
    re.IGNORECASE | re.DOTALL,
)
_NAMED_UNIT_MW_RE = re.compile(
    r"(?:\b[A-Z][a-z]+\s*)?\(\s*(?P<count_paren>\d+)\s*\)\s*"
    r"(?P<mw>\d+(?:\.\d+)?)\s*MW\b|"
    r"\b(?P<count_word>one|two|three|four|five|six|seven|eight|nine|ten|\d+)"
    r"\s+(?P<mw_word>\d+(?:\.\d+)?)\s*MW\b",
    re.IGNORECASE,
)
_AIR_PERMIT_PATTERNS = [
    re.compile(
        r"(?:TCEQ\s+)?(?:Standard\s+)?Permit\s+(?:Reg(?:istration)?\s*)?"
        r"(?P<value>\d{4,})",
        re.IGNORECASE,
    ),
    re.compile(r"\bR13-\d{4,}\b", re.IGNORECASE),
    re.compile(r"\bProject\s+(?P<value>\d{4,})\b", re.IGNORECASE),
    re.compile(r"\bRN(?P<value>\d{6,})\b", re.IGNORECASE),
]
_PUC_APPROVAL_RE = re.compile(
    r"(?:LPSC|PUC|PSC|Commission).{0,80}(?:approval|approved|order)",
    re.IGNORECASE | re.DOTALL,
)
_BEHIND_METER_RE = re.compile(
    r"(?:behind[- ]the[- ]meter|on[- ]site|onsite|off[- ]grid|microgrid|self[- ]gen)",
    re.IGNORECASE,
)
_QUEUE_BYPASS_RE = re.compile(
    r"(?:sidestep|skip|bypass|avoid)(?:s|ed|ing)?\s+"
    r"(?:the\s+)?(?:PJM|ERCOT|ISO|interconnection|queue)|"
    r"(?:sidestep|skip|bypass|avoid)(?:s|ed|ing)?.{0,80}"
    r"(?:lengthy|multi-year|six-year|6-year).{0,40}(?:interconnection|queue)|"
    r"(?:\bno\b(?!\.)|\bwithout\b).{0,80}(?:ISO|ERCOT|PJM|interconnection).{0,40}"
    r"(?:queue|INR|record)",
    re.IGNORECASE | re.DOTALL,
)
_LITIGATION_RE = re.compile(
    r"(?:lawsuit|litigat|Clean Air Act|NAACP|without an air permit|ran.{0,40}without.{0,40}permit|"
    r"federal suit)",
    re.IGNORECASE | re.DOTALL,
)
_RATEPAYER_TRANSFER_RE = re.compile(
    r"(?:rate[- ]base|ratepayers|customers).{0,120}(?:stranded|recover|bear|risk|cost)|"
    r"(?:stranded|recover|bear|risk|cost).{0,120}(?:rate[- ]base|ratepayers|customers)",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class PhysicalExecutionTerm:
    """One extracted physical-execution term from an acquired source row."""

    term_type: str
    value: str
    unit: str
    quote: str
    source_id: str
    source_uri: str
    document_id: str
    project_name: str
    operator: str
    jurisdiction: str
    authority: str
    permit_or_docket: str
    confidence: str

    def to_row(self) -> dict[str, str]:
        return asdict(self)


def extract_physical_execution_terms_from_rows(
    rows: list[dict[str, Any]],
) -> list[PhysicalExecutionTerm]:
    """Extract normalized physical execution terms from acquired source rows."""

    terms: list[PhysicalExecutionTerm] = []
    for row in rows:
        terms.extend(extract_physical_execution_terms(row))
    return terms


def extract_physical_execution_terms(row: dict[str, Any]) -> list[PhysicalExecutionTerm]:
    """Extract permit, off-grid, queue-bypass, and stranded-risk evidence."""

    text = _normalized_text(row.get("text") or row.get("quote") or row.get("source_quote") or "")
    if not text:
        return []

    terms: list[PhysicalExecutionTerm] = []
    terms.extend(_capacity_terms(row, text))
    terms.extend(_permit_terms(row, text))
    terms.extend(_boolean_terms(row, text))
    return _dedupe_terms(terms)


def _capacity_terms(row: dict[str, Any], text: str) -> list[PhysicalExecutionTerm]:
    terms: list[PhysicalExecutionTerm] = []
    unit_spans: list[tuple[int, int]] = []
    named_unit_total = _named_unit_capacity_mw(text)
    if named_unit_total is not None:
        total, unit_spans = named_unit_total
        terms.append(_term(row, "onsite_generation_mw", f"{total:g}", "MW", text))

    for match in _MW_RE.finditer(text):
        if _inside_any_span(match.start(), unit_spans):
            continue
        context = _quote(text, match.start(), match.end(), radius=100)
        context_lower = context.lower()
        if not _capacity_context_is_relevant(context_lower):
            continue
        value = _clean_number(match.group("value"))
        unit = match.group("unit").upper()
        if match.group("prefix") == ">":
            value = f">{value}"
        if unit.startswith("MEGAWATT"):
            unit = "MW"
        if unit == "GW":
            unit = "MW"
            value = _gw_to_mw(value)

        if any(marker in context_lower for marker in ("ratepayer", "rate-base", "utility", "ccgt")):
            term_type = "utility_generation_capacity_mw"
        elif any(marker in context_lower for marker in ("off-grid", "behind", "onsite", "on-site")):
            term_type = "onsite_generation_mw"
        else:
            term_type = "physical_generation_capacity_mw"
        terms.append(_term(row, term_type, value, unit, context))
    return terms


def _named_unit_capacity_mw(text: str) -> tuple[float, list[tuple[int, int]]] | None:
    text_lower = text.lower()
    if not any(
        marker in text_lower for marker in ("onsite", "on-site", "behind", "off grid", "off-grid")
    ):
        return None
    matches = list(_NAMED_UNIT_MW_RE.finditer(text))
    if len(matches) < 2:
        return None
    total = 0.0
    spans: list[tuple[int, int]] = []
    for match in matches:
        count_text = match.group("count_paren") or match.group("count_word")
        mw_text = match.group("mw") or match.group("mw_word")
        if not count_text or not mw_text:
            continue
        total += _count_value(count_text) * float(mw_text)
        spans.append((match.start(), match.end()))
    return (total, spans) if total else None


def _inside_any_span(start: int, spans: list[tuple[int, int]]) -> bool:
    return any(span_start <= start <= span_end for span_start, span_end in spans)


def _count_value(value: str) -> int:
    words = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
    }
    lowered = value.lower()
    if lowered in words:
        return words[lowered]
    return int(value)


def _permit_terms(row: dict[str, Any], text: str) -> list[PhysicalExecutionTerm]:
    terms: list[PhysicalExecutionTerm] = []
    for pattern in _AIR_PERMIT_PATTERNS:
        for match in pattern.finditer(text):
            value = match.groupdict().get("value") or match.group(0)
            terms.append(
                _term(
                    row,
                    "air_permit_id",
                    value.strip(),
                    "id",
                    _quote(text, match.start(), match.end()),
                )
            )

    terms.extend(
        _term(
            row,
            "puc_or_utility_approval",
            "present",
            "flag",
            _quote(text, match.start(), match.end()),
        )
        for match in _PUC_APPROVAL_RE.finditer(text)
    )
    return terms


def _boolean_terms(row: dict[str, Any], text: str) -> list[PhysicalExecutionTerm]:
    patterns = [
        ("behind_the_meter_or_off_grid", _BEHIND_METER_RE),
        ("queue_bypass_or_no_queue", _QUEUE_BYPASS_RE),
        ("permit_litigation_or_enforcement_risk", _LITIGATION_RE),
        ("ratepayer_stranded_asset_transfer", _RATEPAYER_TRANSFER_RE),
    ]
    terms: list[PhysicalExecutionTerm] = []
    for term_type, pattern in patterns:
        for match in pattern.finditer(text):
            quote = _quote(text, match.start(), match.end())
            if term_type == "permit_litigation_or_enforcement_risk" and _is_negated_litigation(
                quote
            ):
                continue
            terms.append(_term(row, term_type, "present", "flag", quote))
            break
    return terms


def _is_negated_litigation(quote: str) -> bool:
    quote_lower = quote.lower()
    negated_markers = (
        "no lawsuits",
        "no public hearing",
        "no petitions",
        "no documented local opposition",
        "no formal protests",
        "no comments received",
        "no public comment",
        "not located",
        "were located in available sources",
    )
    return any(marker in quote_lower for marker in negated_markers)


def _capacity_context_is_relevant(context_lower: str) -> bool:
    markers = (
        "data center",
        "datacenter",
        "behind",
        "onsite",
        "on-site",
        "off-grid",
        "microgrid",
        "gas",
        "turbine",
        "ccgt",
        "power facility",
        "generation",
        "ratepayer",
        "rate-base",
        "utility",
        "load",
    )
    return any(marker in context_lower for marker in markers)


def _term(
    row: dict[str, Any],
    term_type: str,
    value: str,
    unit: str,
    quote: str,
) -> PhysicalExecutionTerm:
    metadata = _metadata(row)
    return PhysicalExecutionTerm(
        term_type=term_type,
        value=value,
        unit=unit,
        quote=quote,
        source_id=str(row.get("source_id") or ""),
        source_uri=str(row.get("source_uri") or ""),
        document_id=str(row.get("document_id") or ""),
        project_name=str(row.get("project_name") or metadata.get("project_name") or ""),
        operator=str(row.get("operator") or metadata.get("operator") or ""),
        jurisdiction=str(row.get("jurisdiction") or metadata.get("jurisdiction") or ""),
        authority=str(row.get("authority") or metadata.get("authority") or ""),
        permit_or_docket=str(row.get("permit_or_docket") or metadata.get("permit_or_docket") or ""),
        confidence="pattern_extracted",
    )


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


def _gw_to_mw(value: str) -> str:
    if value.startswith(">"):
        return f">{float(value[1:]) * 1000:g}"
    return f"{float(value) * 1000:g}"


def _dedupe_terms(terms: list[PhysicalExecutionTerm]) -> list[PhysicalExecutionTerm]:
    seen: set[tuple[str, str, str, str]] = set()
    deduped: list[PhysicalExecutionTerm] = []
    for term in terms:
        key = (term.term_type, term.value, term.unit, term.quote)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(term)
    return deduped
